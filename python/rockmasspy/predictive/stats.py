"""Estadística del modelo predictivo: la lineal del nivel 1 (Fase 4A, tarea 3) y la de clasificación al final.

Lineal: OLS, Deming, bootstrap por grupos y bayesiano conjugado. Clasificación (tareas 8 y 11): logit ordinal,
logística MAP con cotas de signo y métricas de validación.

En la lineal, el modelo es y = a·x + b en todos: quien llama transforma x antes (por ejemplo ln Q). Métodos y
por qué, en `docs/investigacion/MODELOS_SOSTENIMIENTO.md` §2.2: OLS con intervalo de predicción para predecir
Y desde una X medida (Warton et al. 2006); Deming para la relación estructural, solo con la razón de varianzas de error
(Carroll et al. 2006); bootstrap que remuestrea labores y no filas (Efron y Tibshirani 1994); bayesiano que se
encoge hacia la correlación global con pocos datos (Ching et al. 2020).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import linprog, minimize
from scipy.special import expit
from scipy.stats import gamma as gamma_dist
from scipy.stats import norm, rankdata
from scipy.stats import t as student_t


def _vector(name: str, values, min_n: int) -> np.ndarray:
    try:
        arr = np.asarray(values, dtype=float)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a sequence of numbers") from None
    if arr.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} must contain only finite numbers (no NaN or inf)")
    if arr.size < min_n:
        raise ValueError(f"{name} needs at least {min_n} values, got {arr.size}")
    return arr


def _xy(x, y, min_n: int) -> tuple[np.ndarray, np.ndarray]:
    xa, ya = _vector("x", x, 0), _vector("y", y, 0)
    if xa.size != ya.size:
        raise ValueError(f"x and y must have the same length ({xa.size} != {ya.size})")
    if xa.size < min_n:
        raise ValueError(f"x and y need at least {min_n} pairs, got {xa.size}")
    return xa, ya


def _positive(name: str, value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, np.integer, np.floating)) \
            or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a positive finite number")
    return float(value)


def _level(level) -> float:
    if isinstance(level, bool) or not isinstance(level, (int, float, np.integer, np.floating)) or not 0 < level < 1:
        raise ValueError("level must be strictly between 0 and 1")
    return float(level)


def _x0(x0) -> np.ndarray:
    try:
        arr = np.asarray(x0, dtype=float)
    except (TypeError, ValueError):
        raise ValueError("x0 must be a number or a sequence of numbers") from None
    if not np.all(np.isfinite(arr)):
        raise ValueError("x0 must contain only finite numbers (no NaN or inf)")
    return arr


def _constant(sdev: float, mean: float, n: int) -> bool:
    # suma de desvíos² ~0 frente a la escala del dato: el redondeo de la media no cuenta como variación
    return sdev <= (1e-12 * max(1.0, abs(mean))) ** 2 * n


def _interval(center: np.ndarray, half: np.ndarray):
    # escalar entra, escalar sale; un arreglo devuelve arreglos
    if center.ndim == 0:
        return float(center), float(center - half), float(center + half)
    return center, center - half, center + half


@dataclass(frozen=True)
class OlsFit:
    """Mínimos cuadrados de y sobre x. `dof` = n − 2; `sigma` = desviación residual con n − 2."""

    a: float
    b: float
    se_a: float
    se_b: float
    sigma: float
    r2: float
    n: int
    dof: int
    x_mean: float
    sxx: float  # suma de (x − x̄)², para el intervalo de predicción

    def predict(self, x0, level: float = 0.95):
        """Intervalo de PREDICCIÓN de una observación nueva en x0: (ŷ, inferior, superior)."""
        lv, xa = _level(level), _x0(x0)
        fit = self.a * xa + self.b
        se = self.sigma * np.sqrt(1.0 + 1.0 / self.n + (xa - self.x_mean) ** 2 / self.sxx)
        return _interval(fit, student_t.ppf(0.5 + lv / 2, self.dof) * se)


def ols_fit(x, y) -> OlsFit:
    xa, ya = _xy(x, y, 3)
    n = xa.size
    xm, ym = xa.mean(), ya.mean()
    dx, dy = xa - xm, ya - ym
    sxx = float(dx @ dx)
    if _constant(sxx, xm, n):
        raise ValueError("x must not be constant")
    a = float(dx @ dy) / sxx
    b = float(ym - a * xm)
    resid = ya - (a * xa + b)
    ssr, sst = float(resid @ resid), float(dy @ dy)
    sigma = math.sqrt(ssr / (n - 2))
    # y constante: ajuste perfecto pero R² sin definir (0/0)
    r2 = 1.0 - ssr / sst if sst > 0 else math.nan
    return OlsFit(a=a, b=b, se_a=sigma / math.sqrt(sxx), se_b=sigma * math.sqrt(1.0 / n + xm * xm / sxx),
                  sigma=sigma, r2=r2, n=n, dof=n - 2, x_mean=float(xm), sxx=sxx)


@dataclass(frozen=True)
class DemingFit:
    a: float
    b: float


def deming_fit(x, y, ratio: float) -> DemingFit:
    """Regresión de Deming, fórmula cerrada.

    `ratio` = δ = var(error de medición en y) / var(error de medición en x): la varianza del error de y va en el
    NUMERADOR. δ = 1 es la regresión ortogonal; δ → ∞ (x sin error) tiende a la OLS de y sobre x; δ → 0 (y sin
    error) tiende a la inversa de la OLS de x sobre y. Pendiente: a = (d + √(d² + 4δ·sxy²)) / (2·sxy), con
    d = syy − δ·sxx; b = ȳ − a·x̄.
    """
    d_ratio = _positive("ratio", ratio)
    xa, ya = _xy(x, y, 2)
    dx, dy = xa - xa.mean(), ya - ya.mean()
    sxx, syy, sxy = float(dx @ dx), float(dy @ dy), float(dx @ dy)
    if _constant(sxx, xa.mean(), xa.size) or _constant(syy, ya.mean(), ya.size) \
            or abs(sxy) <= 1e-12 * math.sqrt(sxx) * math.sqrt(syy):  # por separado: sxx·syy se desborda
        raise ValueError("x and y are uncorrelated (or one is constant): the Deming slope is undefined")
    d = syy - d_ratio * sxx
    s = math.hypot(d, 2.0 * math.sqrt(d_ratio) * abs(sxy))
    # con d < 0 la forma directa resta números casi iguales; (d + s)(s − d) = 4δ·sxy² da la forma estable
    a = (d + s) / (2.0 * sxy) if d >= 0 else 2.0 * d_ratio * sxy / (s - d)
    return DemingFit(a=a, b=float(ya.mean() - a * xa.mean()))


@dataclass(frozen=True)
class BootstrapResult:
    """Réplicas válidas (filas) del bootstrap por grupos y cuántas se descartaron por degeneradas."""

    replicates: np.ndarray  # (réplicas válidas,) o (réplicas válidas, k)
    n_discarded: int
    n_boot: int
    # última excepción de la estadística: si todas fallan, distingue un error del usuario de réplicas degeneradas
    last_error: Exception | None = field(default=None, repr=False, compare=False)

    def percentile_ci(self, level: float = 0.95) -> tuple:
        """IC por percentiles: (inferior, superior), escalares o arreglos según la estadística."""
        lv = _level(level)
        if len(self.replicates) == 0:
            e = self.last_error
            detail = f"; last error from statistic: {type(e).__name__}: {e}" if e is not None else ""
            raise ValueError("no valid bootstrap replicates: every resample was degenerate" + detail) from e
        lo, hi = np.quantile(self.replicates, [0.5 - lv / 2, 0.5 + lv / 2], axis=0)
        return (float(lo), float(hi)) if np.ndim(lo) == 0 else (lo, hi)


def group_bootstrap(groups: Sequence[Hashable], statistic: Callable[[np.ndarray], object], *,
                    n_boot: int = 2000, seed: int = 0) -> BootstrapResult:
    """Bootstrap por grupos (labores): remuestrea grupos completos con reemplazo, no filas.

    `groups[i]` es el grupo de la fila i. Cada réplica sortea tantos grupos como hay, concatena los índices de sus
    filas (un grupo repetido aparece repetido) y llama `statistic(indices)`. Si la estadística lanza ValueError,
    ArithmeticError o LinAlgError, o devuelve algo no finito (p. ej. x constante en la réplica), la réplica se
    descarta y se cuenta. Misma semilla → mismas réplicas (`numpy.random.default_rng`).
    """
    if isinstance(n_boot, bool) or not isinstance(n_boot, (int, np.integer)) or n_boot < 1:
        raise ValueError("n_boot must be a positive integer")
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)):
        raise ValueError("seed must be an integer")
    rows: dict = {}
    try:
        for i, g in enumerate(groups):
            rows.setdefault(g, []).append(i)
    except TypeError:
        raise ValueError("groups must be a sequence of hashable labels") from None
    if len(rows) < 2:
        raise ValueError(f"groups needs at least 2 distinct groups, got {len(rows)}")
    # orden de primera aparición: reproducible sin ordenar etiquetas de tipos mezclados
    members = [np.asarray(v, dtype=np.intp) for v in rows.values()]
    rng = np.random.default_rng(seed)
    kept, discarded, last_error = [], 0, None
    for _ in range(int(n_boot)):
        pick = rng.integers(0, len(members), size=len(members))
        idx = np.concatenate([members[k] for k in pick])
        try:
            value = np.asarray(statistic(idx), dtype=float)
        except (ValueError, ArithmeticError, np.linalg.LinAlgError) as e:
            discarded, last_error = discarded + 1, e
            continue
        if not np.all(np.isfinite(value)):
            discarded += 1
            continue
        kept.append(value)
    reps = np.stack(kept) if kept else np.empty((0,))
    return BootstrapResult(replicates=reps, n_discarded=discarded, n_boot=int(n_boot), last_error=last_error)


@dataclass(frozen=True)
class BayesLinearFit:
    """Posterior normal–gamma inversa de (a, b, σ²).

    β = (a, b) | σ² ~ N(β̂, σ²·Λn⁻¹); σ² ~ IG(alpha, beta). La marginal de β es t de Student con 2·alpha grados
    de libertad, centro β̂ y escala (beta/alpha)·Λn⁻¹.
    """

    a: float
    b: float
    precision: tuple[tuple[float, float], tuple[float, float]]  # Λn, en el orden (a, b)
    alpha: float
    beta: float
    n: int

    def predict(self, x0, level: float = 0.95):
        """Intervalo predictivo posterior (t de Student, 2·alpha gl) de una observación nueva: (ŷ, inf., sup.)."""
        lv, xa = _level(level), _x0(x0)
        cov = np.linalg.inv(np.array(self.precision))
        quad = cov[0, 0] * xa * xa + 2.0 * cov[0, 1] * xa + cov[1, 1]  # x̃'Λn⁻¹x̃ con x̃ = (x0, 1)
        scale = np.sqrt(self.beta / self.alpha * (1.0 + quad))
        return _interval(self.a * xa + self.b, student_t.ppf(0.5 + lv / 2, 2.0 * self.alpha) * scale)


def bayes_linear_fit(x, y, *, prior_mean: tuple[float, float], prior_sd: tuple[float, float],
                     prior_sigma: float, prior_strength: float = 2.0) -> BayesLinearFit:
    """Regresión lineal bayesiana conjugada con la correlación global como *prior*.

    Prior: β | σ² ~ N(m0, σ²·Λ0⁻¹), σ² ~ IG(α0, β0), con m0 = prior_mean, Λ0 = diag(s²/sa², s²/sb²) (s =
    prior_sigma, (sa, sb) = prior_sd: con σ = s la desviación a priori de a y b es sa y sb), α0 = prior_strength
    (> 1) y β0 = s²·(α0 − 1) (media a priori de σ² = s²). Acepta n pequeño, incluso 0: entonces queda el prior.
    """
    try:
        m0 = np.array([float(prior_mean[0]), float(prior_mean[1])])
        sa, sb = prior_sd
    except (TypeError, ValueError, IndexError):
        raise ValueError("prior_mean and prior_sd must be pairs of numbers (a, b)") from None
    if len(prior_mean) != 2 or len(prior_sd) != 2:
        raise ValueError("prior_mean and prior_sd must be pairs of numbers (a, b)")
    if not np.all(np.isfinite(m0)):
        raise ValueError("prior_mean must be finite")
    sa, sb = _positive("prior_sd[0]", sa), _positive("prior_sd[1]", sb)
    s2 = _positive("prior_sigma", prior_sigma) ** 2
    a0 = _positive("prior_strength", prior_strength)
    if a0 <= 1:
        raise ValueError("prior_strength must be greater than 1 (so the prior mean of sigma^2 exists)")
    xa, ya = _xy(x, y, 0)
    lam0 = np.diag([s2 / sa ** 2, s2 / sb ** 2])
    X = np.column_stack([xa, np.ones_like(xa)])
    lam_n = X.T @ X + lam0
    mean = np.linalg.solve(lam_n, X.T @ ya + lam0 @ m0)
    resid, shift = ya - X @ mean, mean - m0
    # forma por residuos de β_n: equivalente a y'y + m0'Λ0m0 − mn'Λn·mn sin la cancelación
    beta_n = s2 * (a0 - 1.0) + 0.5 * (float(resid @ resid) + float(shift @ lam0 @ shift))
    return BayesLinearFit(a=float(mean[0]), b=float(mean[1]),
                          precision=((float(lam_n[0, 0]), float(lam_n[0, 1])),
                                     (float(lam_n[1, 0]), float(lam_n[1, 1]))),
                          alpha=a0 + xa.size / 2.0, beta=beta_n, n=int(xa.size))


# ---------------------------------------------------------------------------------------------------------------
# Clasificación (Fase 4B, tarea 8, y 4C, tarea 11): logit ordinal, logística MAP y métricas. Métodos en
# `docs/investigacion/MODELOS_SOSTENIMIENTO.md` §3.3 y §4; decisiones R7, R8 y R10 del plan de la Fase 4.
# ---------------------------------------------------------------------------------------------------------------

def _matrix(name: str, values, n_cols: int | None = None) -> np.ndarray:
    try:
        arr = np.asarray(values, dtype=float)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a 2-D array of numbers") from None
    if arr.ndim != 2:
        raise ValueError(f"{name} must be two-dimensional (n rows, p columns), got {arr.ndim} dimension(s)")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} must contain only finite numbers (no NaN or inf)")
    if n_cols is not None and arr.shape[1] != n_cols:
        raise ValueError(f"{name} must have {n_cols} columns, got {arr.shape[1]}")
    return arr


def _n_classes(n_classes) -> int:
    if isinstance(n_classes, bool) or not isinstance(n_classes, (int, np.integer)) or n_classes < 2:
        raise ValueError("n_classes must be an integer >= 2")
    return int(n_classes)


def _classes(name: str, values, n_classes: int) -> np.ndarray:
    arr = _vector(name, values, 1)
    if np.any(arr != np.round(arr)) or arr.min() < 0 or arr.max() > n_classes - 1:
        raise ValueError(f"{name} must contain integer classes between 0 and {n_classes - 1}")
    return arr.astype(np.intp)


def _binary(name: str, values) -> np.ndarray:
    arr = _vector(name, values, 1)
    if not np.all((arr == 0) | (arr == 1)):
        raise ValueError(f"{name} must contain only 0 and 1")
    return arr


def _probability(name: str, values) -> np.ndarray:
    arr = _vector(name, values, 1)
    if np.any(arr < 0) or np.any(arr > 1):
        raise ValueError(f"{name} must contain probabilities between 0 and 1")
    return arr


def _same_length(a: np.ndarray, b: np.ndarray, na: str, nb: str) -> None:
    if a.size != b.size:
        raise ValueError(f"{na} and {nb} must have the same length ({a.size} != {b.size})")


def _log_sigmoid(z):
    return -np.logaddexp(0.0, -z)  # log σ(z) sin desborde; +inf da 0 y −inf da −inf


def _log_interval(a, b):
    # log(σ(a) − σ(b)) con b < a, sin restar dos números casi iguales: σ(a) − σ(b) = σ(a)·σ(−b)·(1 − e^(b−a))
    return _log_sigmoid(a) + _log_sigmoid(-b) + np.log1p(-np.exp(b - a))


def _information_cov(h: np.ndarray) -> tuple[np.ndarray, str]:
    """Inversa de la matriz de información `h` (hessiano de −log L o de −log posterior), o NaN con el motivo."""
    eig = np.linalg.eigvalsh(h) if np.all(np.isfinite(h)) else np.array([np.nan])
    if not np.all(np.isfinite(eig)) or eig[0] <= 1e-10 * max(eig[-1], 1e-300):
        return np.full(h.shape, np.nan), ("the information matrix is singular at the optimum: the data may be "
                                         "separated or the columns of X collinear (or one constant)")
    return np.linalg.inv(h), ""


@dataclass(frozen=True)
class OrdinalLogitFit:
    """Logit acumulado de odds proporcionales: P(y ≤ k | x) = σ(cuts[k] − x·coef), k = 0..K−2.

    `cov` es la inversa del hessiano de −log L en el óptimo, en el orden (coef..., cuts...). Si `converged` es
    False, `message` dice por qué (separación, colinealidad, iteraciones) y `cov` es NaN: no se usa.
    """

    coef: np.ndarray
    cuts: np.ndarray
    cov: np.ndarray
    converged: bool
    n: int
    n_classes: int
    loglik: float
    message: str = ""

    def predict_proba(self, X) -> np.ndarray:
        """Probabilidad de cada clase, (n, K); cada fila suma 1."""
        eta = _matrix("X", X, self.coef.size) @ self.coef
        ext = np.concatenate([[-np.inf], self.cuts, [np.inf]])
        return np.exp(_log_interval(ext[None, 1:] - eta[:, None], ext[None, :-1] - eta[:, None]))

    def predict(self, X) -> np.ndarray:
        """Clase más probable de cada fila."""
        return np.argmax(self.predict_proba(X), axis=1)


def _ordinal_loglik(beta, theta, X, y, K, *, hessian: bool = False):
    """log L, su gradiente en (β, θ) y, si se pide, su hessiano en (β, θ)."""
    ext = np.concatenate([[-np.inf], theta, [np.inf]])
    eta = X @ beta
    a, b = ext[y + 1] - eta, ext[y] - eta  # P(y_i) = σ(a) − σ(b)
    logp = _log_interval(a, b)
    with np.errstate(invalid="ignore"):  # a o b infinitos: log f = −inf y el cociente es 0, no NaN
        ga = np.nan_to_num(np.exp(_log_sigmoid(a) + _log_sigmoid(-a) - logp))  # f(a)/P
        gb = np.nan_to_num(np.exp(_log_sigmoid(b) + _log_sigmoid(-b) - logp))  # f(b)/P
    up, low = y < K - 1, y > 0  # filas con a finito (corte y) y con b finito (corte y − 1)
    g_theta = (np.bincount(y[up], weights=ga[up], minlength=K - 1)
               - np.bincount(y[low] - 1, weights=gb[low], minlength=K - 1))
    grad = np.concatenate([-X.T @ (ga - gb), g_theta])
    if not hessian:
        return float(logp.sum()), grad, None
    # ℓ = log(F(a) − F(b)) con F logística: f' = f·(1 − 2F)
    laa = ga * (1.0 - 2.0 * expit(a)) - ga * ga
    lbb = -gb * (1.0 - 2.0 * expit(b)) - gb * gb
    lab = ga * gb
    eye = np.eye(K - 1)
    da = np.column_stack([-X, np.where(up[:, None], eye[np.minimum(y, K - 2)], 0.0)])
    db = np.column_stack([-X, np.where(low[:, None], eye[np.maximum(y - 1, 0)], 0.0)])
    cross = da.T @ (lab[:, None] * db)
    hess = da.T @ (laa[:, None] * da) + db.T @ (lbb[:, None] * db) + cross + cross.T
    return float(logp.sum()), grad, hess


def _ordinal_separated(X, y, K) -> bool:
    """¿Hay separación (completa o cuasi completa)? Es decir, ¿existe una dirección d = (dβ, dθ), con dθ no
    decreciente, en la que log L nunca baja y sube en alguna fila? Entonces el MLE no existe (Albert y Anderson
    1984, extendido a los cortes). Programa lineal: max Σ términos con cada término ≥ 0 y |d| ≤ 1."""
    n, p = X.shape
    eye = np.eye(K - 1)
    up, low = y < K - 1, y > 0
    # a_i = θ_y − x·β no debe bajar y b_i = θ_{y−1} − x·β no debe subir: filas de A·d ≤ 0
    rows = [np.column_stack([X[up], -eye[y[up]]]), np.column_stack([-X[low], eye[y[low] - 1]])]
    order = np.zeros((K - 2, p + K - 1))
    for k in range(1, K - 1):
        order[k - 1, p + k - 1], order[k - 1, p + k] = 1.0, -1.0  # dθ_{k−1} − dθ_k ≤ 0
    A = np.vstack(rows)
    res = linprog(A.sum(axis=0), A_ub=np.vstack([A, order]), b_ub=np.zeros(A.shape[0] + K - 2),
                  bounds=[(-1.0, 1.0)] * (p + K - 1), method="highs")
    return bool(res.status == 0 and -res.fun > 1e-7 * (1.0 + float(np.abs(X).max(initial=0.0))) * n)


def ordinal_logit_fit(X, y, *, n_classes: int) -> OrdinalLogitFit:
    """Logit ordinal (odds proporcionales) por máxima verosimilitud (Bürkner y Vuorre 2019).

    `X` es (n, p) sin columna de unos; `y` son clases enteras 0..n_classes−1 y cada una tiene que aparecer al menos
    una vez. Los cortes se parametrizan como θ_0 y θ_k = θ_{k−1} + exp(δ_k), así quedan crecientes; el óptimo se
    busca con región de confianza y gradiente y hessiano analíticos. Sin penalización: con separación el MLE no
    existe y el resultado sale con `converged=False` y el motivo.
    """
    K = _n_classes(n_classes)
    Xa = _matrix("X", X)
    ya = _classes("y", y, K)
    n, p = Xa.shape
    if ya.size != n:
        raise ValueError(f"X and y must have the same number of rows ({n} != {ya.size})")
    counts = np.bincount(ya, minlength=K)
    missing = [k for k in range(K) if counts[k] == 0]
    if missing:
        raise ValueError(f"class(es) {missing} have no observations in the training data: the cut points "
                         "around them cannot be estimated (merge classes or lower n_classes)")

    def theta_of(u):
        return u[p] + np.concatenate([[0.0], np.cumsum(np.exp(u[p + 1:]))])

    def jacobian(u):  # ∂(β, θ)/∂u
        J = np.eye(p + K - 1)
        for m in range(1, K - 1):
            J[p + m:, p + m] = np.exp(u[p + m])
        return J

    # se minimiza −log L / n: con la suma, la precisión de máquina de log L (≈ n·ε) frena a trust-exact con un
    # gradiente que crece con n («bad approximation» con n ≈ 5000 sin separación; banco de la Fase 5, §8)
    def objective(u):
        ll, g, _ = _ordinal_loglik(u[:p], theta_of(u), Xa, ya, K)
        return -ll / n, jacobian(u).T @ -g / n

    def hess(u):
        _, g, h = _ordinal_loglik(u[:p], theta_of(u), Xa, ya, K, hessian=True)
        J = jacobian(u)
        hu = J.T @ -h @ J
        # término de segundo orden de θ(u): ∂²θ_k/∂δ_m² = exp(δ_m) para m ≤ k
        tail = np.cumsum(-g[p:][::-1])[::-1]  # Σ_{k ≥ m} ∂(−ℓ)/∂θ_k
        for m in range(1, K - 1):
            hu[p + m, p + m] += np.exp(u[p + m]) * tail[m]
        return hu / n

    cum = np.cumsum(counts)[:-1] / n
    start = np.log(cum / (1.0 - cum))
    u0 = np.concatenate([np.zeros(p), start[:1], np.log(np.diff(start))])
    with np.errstate(over="ignore"):  # con separación exp(δ) puede desbordar: se detecta abajo
        res = minimize(objective, u0, jac=True, hess=hess, method="trust-exact",
                       options={"gtol": 1e-10, "maxiter": 500})
        beta, theta = res.x[:p].copy(), theta_of(res.x)
    cov = np.full((p + K - 1, p + K - 1), np.nan)
    ll, h = -math.inf, None
    if np.all(np.isfinite(beta)) and np.all(np.isfinite(theta)):
        ll, _, h = _ordinal_loglik(beta, theta, Xa, ya, K, hessian=True)
    if _ordinal_separated(Xa, ya, K):
        converged, message = False, ("the classes are separated by X (complete or quasi-complete separation): the "
                                     "maximum likelihood estimate does not exist; merge classes, drop columns or "
                                     "use a penalized model")
    elif not math.isfinite(ll):
        converged, message = False, f"the optimizer reached non-finite values: {res.message}"
    # trust-exact a veces termina con «bad approximation» ya en el óptimo (precisión de máquina): se juzga por el
    # gradiente y no por res.success
    elif (grad := float(np.max(np.abs(res.jac), initial=0.0))) > 1e-6:  # gradiente de −log L / n
        # no hay separación (se probó arriba): el mensaje no la culpa
        converged, message = False, (f"optimizer did not converge: {res.message} (largest gradient of the mean "
                                     f"log-likelihood {grad:.1e}; try rescaling the columns of X)")
    else:
        cov, message = _information_cov(-h)
        converged = not message
    return OrdinalLogitFit(coef=beta, cuts=theta, cov=cov, converged=converged, n=n, n_classes=K, loglik=ll,
                           message=message)


def _eta_interval(fit, X, level):
    """(η, inferior, superior) del predictor lineal de un ajuste MAP (logística o tasa de falla): método delta con
    el factor de normal truncada en las columnas con cota de signo (ver `LogisticMapFit.predict_interval`)."""
    lv = _level(level)
    Xa, eta = fit._eta(X)
    p = fit.coef.size
    u = 0.5 + lv / 2
    z = norm.ppf(u)
    # a la escala estandarizada, donde vive la cota: γ = β·escala, α = b + Σ β·media
    Ainv = np.eye(p + 1)
    Ainv[:p, :p] = np.diag(fit.x_scale)
    Ainv[p, :p] = fit.x_mean
    cov_w = Ainv @ fit.cov @ Ainv.T
    factor = np.ones(p + 1)
    for j, s in enumerate(fit.signs):
        if s != 0:
            sd = math.sqrt(cov_w[j, j])
            r = abs(fit.coef[j] * fit.x_scale[j]) / sd  # distancia a la cota, en desviaciones
            # cuantil u de N(r, 1) truncada en 0, medido desde r: Φ⁻¹(1 − (1 − u)·Φ(r))
            factor[j] = max(1.0, norm.ppf(1.0 - (1.0 - u) * norm.cdf(r)) / z)
    Zt = np.column_stack([(Xa - fit.x_mean) / fit.x_scale, np.ones(Xa.shape[0])]) * factor
    # con covarianza agrupada (`df` = conglomerados − 1) el cuantil es el de la t; el factor de la truncada se mide
    # en la normal
    df = getattr(fit, "df", None)
    zq = z if df is None else float(student_t.ppf(u, df))
    half = zq * np.sqrt(np.einsum("ij,jk,ik->i", Zt, cov_w, Zt))
    return eta, eta - half, eta + half


@dataclass(frozen=True)
class LogisticMapFit:
    """Logística bayesiana por MAP con *prior* Cauchy (Gelman et al. 2008) y covarianza de Laplace.

    `coef`, `intercept` y `cov` están en la escala ORIGINAL de X; `cov` va en el orden (coef..., intercept) y es
    la de Laplace pura (inversa del hessiano en el MAP). `x_mean` y `x_scale` son la estandarización interna:
    z = (x − media)/escala, con escala = 2·desviación (ddof 0) en las continuas y escala = máximo − mínimo en las
    binarias (exactamente dos valores distintos), que solo se centran (Gelman et al. 2008).

    `active_bounds` son las columnas cuya cota de signo quedó activa (su coef es 0). Ahí el posterior real es una
    normal truncada en 0: toda su masa queda del lado permitido y su cola es más larga que la de la normal
    simétrica de Laplace, así que Laplace SUBESTIMA el límite del lado permitido. Lo mismo pasa, menos, con una
    cota casi activa. `predict_interval` lo corrige; `cov` no.
    """

    coef: np.ndarray
    intercept: float
    cov: np.ndarray
    active_bounds: tuple[int, ...]
    converged: bool
    n: int
    loglik: float  # log-verosimilitud (sin el prior) en el MAP
    x_mean: np.ndarray
    x_scale: np.ndarray
    message: str = ""
    signs: tuple[int, ...] = ()  # cotas de signo usadas en el ajuste, una por columna (0 = libre)

    def _eta(self, X):
        Xa = _matrix("X", X, self.coef.size)
        return Xa, Xa @ self.coef + self.intercept

    def predict_proba(self, X) -> np.ndarray:
        """P(y = 1) de cada fila, (n,)."""
        return expit(self._eta(X)[1])

    def predict_interval(self, X, level: float = 0.9):
        """(central, inferior, superior) de P(y = 1): método delta en la escala logit y luego σ.

        En cada columna con cota de signo, la desviación de su coeficiente estandarizado γ se agranda hasta que el
        intervalo simétrico alcance el cuantil (1 + level)/2 de la normal truncada N(γ, σ²)·[γ del lado
        permitido], σ = desviación de Laplace. En la cota (γ = 0) es la seminormal: factor
        Φ⁻¹((3 + level)/4) / Φ⁻¹((1 + level)/2), 1.19 al 90 %; lejos de la cota, factor 1. Con la cota activa el
        óptimo sin cota cae del lado prohibido y la truncada real es más angosta que la seminormal: conservador.
        El límite del lado prohibido también se ensancha (no importa para elegir con el superior).
        """
        eta, lo, hi = _eta_interval(self, X, level)
        return expit(eta), expit(lo), expit(hi)


def _map_design(Xa, signs, prior_scale, intercept_scale):
    """Signos, estandarización (continuas a desviación 0.5; binarias solo centradas, escala = rango) y escalas²
    del prior Cauchy; comunes a `logistic_map_fit` y `exponential_hazard_map_fit`."""
    n, p = Xa.shape
    s, s0 = _positive("prior_scale", prior_scale), _positive("intercept_scale", intercept_scale)
    sg = np.zeros(p, dtype=int)
    if signs is not None:
        try:
            sa = np.asarray(signs, dtype=float)
        except (TypeError, ValueError):
            raise ValueError("signs must be a sequence of +1, -1 or 0") from None
        if sa.ndim != 1 or sa.size != p or not np.all(np.isin(sa, (-1, 0, 1))):
            raise ValueError(f"signs must be a sequence of {p} values, each +1, -1 or 0")
        sg = sa.astype(int)
    mean, sd = Xa.mean(axis=0), Xa.std(axis=0)
    for j in range(p):
        if _constant(sd[j] ** 2 * n, mean[j], n):
            raise ValueError(f"column {j} of X is constant: it cannot be standardized")
    # binaria rara con 2·sd: escala chica y prior efectivo mucho más ancho (Cauchy(0, 8) o más); Gelman usa el rango
    binary = np.array([np.unique(Xa[:, j]).size == 2 for j in range(p)], dtype=bool)
    scale = np.where(binary, Xa.max(axis=0, initial=-np.inf) - Xa.min(axis=0, initial=np.inf), 2.0 * sd)
    Z = np.column_stack([(Xa - mean) / scale, np.ones(n)])
    scales2 = np.concatenate([np.full(p, s), [s0]]) ** 2
    return sg, mean, scale, Z, scales2


def _map_solve(Z, sg, scales2, nll, nll_hessian, w0, n):
    """MAP con prior Cauchy y cotas de signo (L-BFGS-B) y covarianza de Laplace en la escala estandarizada.

    `nll(w)` = (−log verosimilitud, gradiente); `nll_hessian(w)` su hessiano. Devuelve (w, cov_w, at_bound,
    converged, message)."""
    p = sg.size

    def objective(w):  # −log posterior (sin constantes) y su gradiente
        v, g = nll(w)
        return float(v + np.sum(np.log1p(w * w / scales2))), g + 2.0 * w / (scales2 + w * w)

    def neg_hessian(w):
        return nll_hessian(w) + np.diag(2.0 * (scales2 - w * w) / (scales2 + w * w) ** 2)

    bounds = [(0.0, None) if g > 0 else (None, 0.0) if g < 0 else (None, None) for g in sg] + [(None, None)]
    res = minimize(objective, w0, jac=True, method="L-BFGS-B", bounds=bounds,
                   options={"maxiter": 5000, "ftol": 1e-15, "gtol": 1e-10})
    w = res.x
    grad = objective(w)[1]
    signs_all = np.concatenate([sg, [0]])
    # en una cota solo cuenta el gradiente que empuja hacia adentro; L-BFGS-B a veces termina «ABNORMAL» ya en el
    # óptimo (precisión de máquina), por eso se juzga por el gradiente proyectado y no por res.success
    at_bound = (signs_all != 0) & (w == 0.0)
    pg = np.where(at_bound, np.where(signs_all > 0, np.minimum(grad, 0.0), np.maximum(grad, 0.0)), grad)
    converged = bool(np.all(np.isfinite(w))) and float(np.max(np.abs(pg))) <= 1e-6 * max(1.0, math.sqrt(n))
    message = "" if converged else f"optimizer did not converge: {res.message}"
    cov_w = np.full((p + 1, p + 1), np.nan)
    if converged:
        cov_w, message = _information_cov(neg_hessian(w))
        converged = not message
    return w, cov_w, at_bound, converged, message


def _map_original(w, cov_w, mean, scale):
    """A la escala original: β = γ/escala y b = α − Σ γ·media/escala; la covarianza con ese jacobiano."""
    p = mean.size
    A = np.eye(p + 1)
    A[:p, :p] = np.diag(1.0 / scale)
    A[p, :p] = -mean / scale
    orig = A @ w
    return orig[:p], float(orig[p]), A @ cov_w @ A.T


def logistic_map_fit(X, y, *, prior_scale: float = 2.5, intercept_scale: float = 10.0,
                     signs: Sequence[int] | None = None) -> LogisticMapFit:
    """Logística MAP: cada columna continua de X se estandariza a media 0 y desviación 0.5, y cada binaria (dos
    valores distintos) solo se centra, con escala = máximo − mínimo (Gelman et al. 2008). Cauchy(0, prior_scale)
    en los coeficientes estandarizados y Cauchy(0, intercept_scale) en el intercepto.

    `signs[j]` = +1 impone β_j ≥ 0, −1 impone β_j ≤ 0 y 0 lo deja libre (cotas de L-BFGS-B; la escala positiva
    conserva el signo). Con separación completa el MAP es finito porque el prior es propio. `y` necesita al menos
    un 0 y un 1: es solo una guarda, el mínimo real de fallas lo aplica la preparación del nivel 3.
    """
    Xa = _matrix("X", X)
    n, p = Xa.shape
    ya = _binary("y", y)
    if ya.size != n:
        raise ValueError(f"X and y must have the same number of rows ({n} != {ya.size})")
    _both_classes(ya, "logistic_map_fit")
    sg, mean, scale, Z, scales2 = _map_design(Xa, signs, prior_scale, intercept_scale)

    def nll(w):  # −log verosimilitud (sin constantes) y su gradiente
        eta = Z @ w
        return np.sum(np.logaddexp(0.0, eta) - ya * eta), Z.T @ (expit(eta) - ya)

    def nll_hessian(w):
        pr = expit(Z @ w)
        return Z.T @ ((pr * (1.0 - pr))[:, None] * Z)

    w, cov_w, at_bound, converged, message = _map_solve(Z, sg, scales2, nll, nll_hessian, np.zeros(p + 1), n)
    coef, intercept, cov = _map_original(w, cov_w, mean, scale)
    return LogisticMapFit(coef=coef, intercept=intercept, cov=cov,
                          active_bounds=tuple(int(j) for j in np.nonzero(at_bound[:p])[0]), converged=converged,
                          n=n, loglik=-float(nll(w)[0]), x_mean=mean, x_scale=scale, message=message,
                          signs=tuple(int(g) for g in sg))


@dataclass(frozen=True)
class ExponentialHazardFit:
    """Tasa de falla constante (exponencial) por MAP: evento_i ~ Poisson(λ_i·t_i), log λ = intercepto + X·β, con λ
    por día si t va en días. Mismos campos y misma estandarización que `LogisticMapFit`; `loglik` es la
    log-verosimilitud de Poisson sin el término constante Σ d·log t ni el prior. El intervalo usa el mismo factor
    de normal truncada con cota activa (`_eta_interval`).
    """

    coef: np.ndarray
    intercept: float
    cov: np.ndarray
    active_bounds: tuple[int, ...]
    converged: bool
    n: int
    loglik: float
    x_mean: np.ndarray
    x_scale: np.ndarray
    message: str = ""
    signs: tuple[int, ...] = ()
    n_events: int = 0

    def _eta(self, X):
        Xa = _matrix("X", X, self.coef.size)
        return Xa, Xa @ self.coef + self.intercept

    def rate(self, X) -> np.ndarray:
        """λ de cada fila (eventos por unidad de exposición)."""
        return np.exp(self._eta(X)[1])

    def prob_within(self, X, days) -> np.ndarray:
        """P(falla dentro de `days`) = 1 − exp(−λ·days); `days` escalar o uno por fila."""
        return -np.expm1(-self.rate(X) * _exposure_days(days))

    def prob_interval(self, X, days, level: float = 0.9):
        """(central, inferior, superior) de P(falla dentro de `days`): método delta en η y luego la transformación
        monótona 1 − exp(−e^η·days)."""
        d = _exposure_days(days)
        return tuple(-np.expm1(-np.exp(e) * d) for e in _eta_interval(self, X, level))


def _exposure_days(days) -> np.ndarray:
    d = np.asarray(days, dtype=float)
    if not np.all(np.isfinite(d)) or np.any(d <= 0):
        raise ValueError("days must be positive finite numbers")
    return d


def exponential_hazard_map_fit(X, events, exposure, *, prior_scale: float = 2.5, intercept_scale: float = 10.0,
                               signs: Sequence[int] | None = None) -> ExponentialHazardFit:
    """Tasa de falla constante por MAP: −log L = Σ (λ_i·t_i − d_i·η_i) (Poisson con offset log t; equivale a la
    exponencial con censura a la derecha). Misma maquinaria que `logistic_map_fit`: estandarización (binarias
    solo centradas), Cauchy(0, prior_scale) en los coeficientes estandarizados, Cauchy(0, intercept_scale) en el
    intercepto, cotas de signo por L-BFGS-B y covarianza de Laplace. `events` es 0/1 por fila (a lo más una falla
    por tramo) y necesita al menos un evento y un no evento; `exposure` > 0.
    """
    Xa = _matrix("X", X)
    n, p = Xa.shape
    d = _binary("events", events)
    t = _vector("exposure", exposure, 1)
    if d.size != n or t.size != n:
        raise ValueError(f"X, events and exposure must have the same number of rows ({n}, {d.size}, {t.size})")
    if np.any(t <= 0):
        raise ValueError("exposure must be positive")
    if d.min() == d.max():
        raise ValueError("exponential_hazard_map_fit needs at least one event and one non-event")
    sg, mean, scale, Z, scales2 = _map_design(Xa, signs, prior_scale, intercept_scale)
    log_t = np.log(t)

    def mu(w):  # λ·t, con η recortado para que una línea de búsqueda lejana no desborde
        return np.exp(np.minimum(Z @ w + log_t, 700.0))

    def nll(w):
        m = mu(w)
        return np.sum(m - d * (Z @ w)), Z.T @ (m - d)

    def nll_hessian(w):
        return Z.T @ (mu(w)[:, None] * Z)

    w0 = np.zeros(p + 1)
    w0[p] = math.log(d.sum() / t.sum())  # arranca en la tasa global: el intercepto de un λ por día es ~ −7
    w, cov_w, at_bound, converged, message = _map_solve(Z, sg, scales2, nll, nll_hessian, w0, n)
    coef, intercept, cov = _map_original(w, cov_w, mean, scale)
    return ExponentialHazardFit(coef=coef, intercept=intercept, cov=cov,
                                active_bounds=tuple(int(j) for j in np.nonzero(at_bound[:p])[0]),
                                converged=converged, n=n, loglik=-float(nll(w)[0]), x_mean=mean, x_scale=scale,
                                message=message, signs=tuple(int(g) for g in sg), n_events=int(d.sum()))


# ---------- tasa de falla con fragilidad gamma compartida (nivel 3) ----------

@dataclass(frozen=True)
class FrailtyHazardFit:
    """Tasa de falla constante con fragilidad gamma compartida por grupo (labor), por MAP sobre la verosimilitud
    marginal: λ_i·Z_g, Z_g ~ Gamma(media 1, varianza θ). Mismos campos que `ExponentialHazardFit` más `theta`.

    `cov` (escala original, orden (coef..., intercepto)) es la sándwich agrupada por conglomerado (zona) si
    `cov_kind == "cluster"`, con `df` = conglomerados − 1 para el cuantil t; si no, la de Laplace (`df` None).
    `log_theta_sd` = desviación de log θ con esa misma covarianza. `loglik` = log-verosimilitud marginal sin las
    constantes Σ d·log t ni el prior.
    """

    coef: np.ndarray
    intercept: float
    cov: np.ndarray
    active_bounds: tuple[int, ...]
    converged: bool
    n: int
    loglik: float
    x_mean: np.ndarray
    x_scale: np.ndarray
    message: str = ""
    signs: tuple[int, ...] = ()
    n_events: int = 0
    theta: float = 0.0
    log_theta_sd: float = math.nan
    cov_kind: str = "laplace"
    n_clusters: int = 0
    df: int | None = None
    n_groups: int = 0

    def _eta(self, X):
        Xa = _matrix("X", X, self.coef.size)
        return Xa, Xa @ self.coef + self.intercept

    def rate(self, X) -> np.ndarray:
        """λ de cada fila para Z = 1 (la media de la fragilidad)."""
        return np.exp(self._eta(X)[1])

    def prob_within(self, X, days) -> np.ndarray:
        """1 − exp(−λ·days): P(falla) con Z = 1. Su −log(1 − P) = λ·days es la media marginal de eventos."""
        return -np.expm1(-self.rate(X) * _exposure_days(days))

    def _marginal(self, lam, d):
        # transformada de Laplace de la gamma: E[exp(−Z·λ·d)] = (1 + θλd)^(−1/θ)
        if self.theta < 1e-12:
            return -np.expm1(-lam * d)
        return -np.expm1(-np.log1p(self.theta * lam * d) / self.theta)

    def prob_marginal(self, X, days) -> np.ndarray:
        """P(falla dentro de `days`) para una labor NUEVA: 1 − (1 + θλ·days)^(−1/θ)."""
        return self._marginal(self.rate(X), _exposure_days(days))

    def theta_upper(self, level: float) -> float:
        """Cota superior de θ: exp(log θ̂ + z·sd(log θ)), z = cuantil `level` de la normal. Sin desviación finita
        (Laplace singular), θ̂."""
        lv = _level(level)
        if self.theta < 1e-12 or not math.isfinite(self.log_theta_sd):
            return self.theta
        return float(math.exp(math.log(self.theta) + norm.ppf(lv) * self.log_theta_sd))

    def frailty_quantile(self, level: float) -> float:
        """Cuantil `level` de la Gamma(media 1, varianza θ_sup), con θ_sup = `theta_upper(level)`; 1 con θ = 0.
        Conservador por diseño: con pocas labores θ̂ puede salir bajo, y un θ chico angosta la cola de Z."""
        lv = _level(level)
        th = self.theta_upper(lv)
        return 1.0 if th < 1e-12 else float(gamma_dist.ppf(lv, 1.0 / th, scale=th))

    def prob_interval(self, X, days, level: float = 0.9):
        """(central, inferior, superior) de P(falla dentro de `days`) para una labor NUEVA.

        Central = la media marginal con λ̂ y θ̂; inferior = la media marginal con la cota inferior de η. Superior =
        1 − exp(−λ_sup·days·Z_q), con λ_sup = la cota superior de η al nivel (con `cov` y el ajuste por cota activa)
        y Z_q = el cuantil `level` de la fragilidad con la cota superior de θ: conservador por diseño (tres cotas a
        la vez: η, θ y Z)."""
        d = _exposure_days(days)
        eta, lo, hi = _eta_interval(self, X, level)
        return (self._marginal(np.exp(eta), d), self._marginal(np.exp(lo), d),
                -np.expm1(-np.exp(hi) * d * self.frailty_quantile(level)))


def _group_codes(name, values, n):
    vals = list(values)
    if len(vals) != n:
        raise ValueError(f"{name} must have one label per row ({len(vals)} != {n})")
    seen: dict = {}
    try:
        return np.array([seen.setdefault(v, len(seen)) for v in vals], dtype=np.intp), len(seen)
    except TypeError:
        raise ValueError(f"{name} must hold hashable labels") from None


def _sum_by_count(d_g, k, kind):
    """Σ_{j<d_g} f(j) por grupo, exacto para d entero: kind 0 → log1p(j/k) (= lnΓ(k+d) − lnΓ(k) − d·ln k, sin la
    cancelación de restar dos lnΓ enormes cuando θ → 0); kind 1 → j/(k + j)."""
    jmax = int(d_g.max(initial=0))
    if jmax == 0:
        return np.zeros(d_g.size)
    j = np.arange(jmax, dtype=float)
    f = np.log1p(j / k) if kind == 0 else j / (k + j)
    return np.concatenate([[0.0], np.cumsum(f)])[d_g]


def frailty_hazard_map_fit(X, events, exposure, groups, *, clusters=None, prior_scale: float = 2.5,
                           intercept_scale: float = 10.0, signs: Sequence[int] | None = None,
                           log_theta_sd: float = 2.0, min_clusters: int = 5) -> FrailtyHazardFit:
    """Tasa de falla con fragilidad gamma compartida por `groups` (labores), por MAP sobre la marginal cerrada.

    Para el grupo g, con d_g fallas y Λ_g = Σ λ_i·t_i, la verosimilitud marginal es
    Γ(k + d_g)/Γ(k) · k^k/(k + Λ_g)^(k + d_g) · Π λ_i^(d_i), k = 1/θ. β y log θ se estiman juntos con los priors
    de `exponential_hazard_map_fit` (Cauchy en β estandarizados, binarias solo centradas, cotas de signo) y, para
    log θ, una normal(0, `log_theta_sd` = 2): débil, cubre θ entre 0.02 y 50 al 95 % y deja que los datos
    decidan; con θ → 0 el modelo es el exponencial.

    `clusters` (zonas): si trae ≥ `min_clusters` conglomerados, la covarianza es la sándwich agrupada (los scores
    de la marginal sumados por conglomerado, corrección C/(C − 1)) y los intervalos usan la t con C − 1 grados de
    libertad; si no, la de Laplace (`cov_kind = "laplace"`). Un grupo tiene que caer entero en un conglomerado
    (las labores van dentro de su zona).
    """
    Xa = _matrix("X", X)
    n, p = Xa.shape
    d = _binary("events", events)
    t = _vector("exposure", exposure, 1)
    if d.size != n or t.size != n:
        raise ValueError(f"X, events and exposure must have the same number of rows ({n}, {d.size}, {t.size})")
    if np.any(t <= 0):
        raise ValueError("exposure must be positive")
    if d.min() == d.max():
        raise ValueError("frailty_hazard_map_fit needs at least one event and one non-event")
    _positive("log_theta_sd", log_theta_sd)
    gc, G = _group_codes("groups", groups, n)
    sg, mean, scale, Z, scales2 = _map_design(Xa, signs, prior_scale, intercept_scale)
    Zs, log_t = Z[:, :p], np.log(t)
    d_g = np.bincount(gc, weights=d, minlength=G).astype(np.intp)
    s2_phi = float(log_theta_sd) ** 2
    # w = (γ…, φ = log θ, α): el prior normal de φ va dentro de nll; su Cauchy de _map_solve queda anulada
    sg_w = np.concatenate([sg, [0]])
    scales2_w = np.concatenate([scales2[:p], [1e100], scales2[p:]])

    def group_terms(w):
        """(ℓ_g por grupo, ∂ℓ/∂η_i por fila, ∂ℓ_g/∂φ por grupo)."""
        eta = Zs @ w[:p] + w[p + 1]
        mu = np.exp(np.minimum(eta + log_t, 700.0))
        lam_g = np.bincount(gc, weights=mu, minlength=G)
        k = math.exp(min(-w[p], 700.0))
        ell = (_sum_by_count(d_g, k, 0) - (k + d_g) * np.log1p(lam_g / k)
               + np.bincount(gc, weights=d * eta, minlength=G))
        r = d - ((k + d_g) / (k + lam_g))[gc] * mu
        dphi = _sum_by_count(d_g, k, 1) + k * np.log1p(lam_g / k) - (k + d_g) * lam_g / (k + lam_g)
        return ell, r, dphi

    def nll(w):
        ell, r, dphi = group_terms(w)
        g = np.concatenate([-(Zs.T @ r), [-dphi.sum() + w[p] / s2_phi], [-r.sum()]])
        return -ell.sum() + w[p] ** 2 / (2 * s2_phi), g

    def nll_hessian(w):  # diferencias centrales del gradiente analítico, simetrizadas
        h = 1e-5 * np.maximum(1.0, np.abs(w))
        H = np.array([(nll(w + e)[1] - nll(w - e)[1]) / (2 * e[j]) for j, e in enumerate(np.diag(h))])
        return (H + H.T) / 2

    w0 = np.zeros(p + 2)
    w0[p], w0[p + 1] = math.log(0.5), math.log(d.sum() / t.sum())
    w, cov_w, at_bound, converged, message = _map_solve(Z, sg_w, scales2_w, nll, nll_hessian, w0, n)
    cov_kind, n_clusters, df = "laplace", 0, None
    if clusters is not None:
        cc, n_clusters = _group_codes("clusters", clusters, n)
        if converged and n_clusters >= min_clusters:
            _, r, dphi = group_terms(w)
            # scores (γ, α) por fila y φ por grupo; el φ de cada grupo va al conglomerado de su primera fila
            first = np.full(G, -1, dtype=np.intp)
            first[gc[::-1]] = np.arange(n)[::-1]
            S = np.zeros((n_clusters, p + 2))
            np.add.at(S, cc, np.column_stack([Zs * r[:, None], np.zeros(n), r]))
            np.add.at(S[:, p], cc[first], dphi)
            cov_w = cov_w @ (n_clusters / (n_clusters - 1) * (S.T @ S)) @ cov_w
            cov_kind, df = "cluster", n_clusters - 1
    keep = np.r_[np.arange(p), p + 1]
    coef, intercept, cov = _map_original(w[keep], cov_w[np.ix_(keep, keep)], mean, scale)
    return FrailtyHazardFit(coef=coef, intercept=intercept, cov=cov,
                            active_bounds=tuple(int(j) for j in np.nonzero(at_bound[:p])[0]), converged=converged,
                            n=n, loglik=float(group_terms(w)[0].sum()), x_mean=mean, x_scale=scale, message=message,
                            signs=tuple(int(g) for g in sg), n_events=int(d.sum()), theta=float(math.exp(w[p])),
                            log_theta_sd=float(math.sqrt(cov_w[p, p])) if np.isfinite(cov_w[p, p]) else math.nan,
                            cov_kind=cov_kind, n_clusters=int(n_clusters), df=df, n_groups=G)


# ---------- métricas de clasificación (R7) ----------

def _labels_pair(y, yhat, n_classes):
    K = _n_classes(n_classes)
    ya, yh = _classes("y", y, K), _classes("yhat", yhat, K)
    _same_length(ya, yh, "y", "yhat")
    return ya, yh, K


def _confusion(ya, yh, K) -> np.ndarray:
    return np.bincount(ya * K + yh, minlength=K * K).reshape(K, K)  # filas = verdadera, columnas = predicha


def recall_per_class(y, yhat, n_classes: int) -> np.ndarray:
    """Sensibilidad de cada clase 0..K−1. Una clase ausente en `y` da NaN (0/0): es la ÚNICA métrica que devuelve
    NaN, a propósito, para distinguir «no hubo casos» de «no acertó ninguno»."""
    C = _confusion(*_labels_pair(y, yhat, n_classes))
    support = C.sum(axis=1)
    out = np.full(C.shape[0], np.nan)
    out[support > 0] = np.diag(C)[support > 0] / support[support > 0]
    return out


def balanced_accuracy(y, yhat, n_classes: int) -> float:
    """Exactitud balanceada: promedio de las sensibilidades de las clases presentes en `y`."""
    return float(np.nanmean(recall_per_class(y, yhat, n_classes)))


def f1_macro(y, yhat, n_classes: int) -> float:
    """F1 macro sobre las clases presentes en `y` o en `yhat` (como scikit-learn sin `labels`); F1 = 2TP/(2TP+FP+FN)."""
    C = _confusion(*_labels_pair(y, yhat, n_classes))
    denom = C.sum(axis=0) + C.sum(axis=1)  # 2TP + FP + FN
    seen = denom > 0
    return float(np.mean(2.0 * np.diag(C)[seen] / denom[seen]))


def quadratic_weighted_kappa(y, yhat, n_classes: int) -> float:
    """Kappa de Cohen con pesos (i − j)² sobre la escala completa 0..K−1 (una clase ausente igual cuenta su
    distancia). Si el desacuerdo esperado es 0 (y e yhat constantes en la misma clase), kappa no está definido y
    lanza ValueError."""
    ya, yh, K = _labels_pair(y, yhat, n_classes)
    C = _confusion(ya, yh, K).astype(float)
    i = np.arange(K)
    W = (i[:, None] - i[None, :]) ** 2.0
    den = float((W * np.outer(C.sum(axis=1), C.sum(axis=0))).sum()) / C.sum()
    if den == 0:
        raise ValueError("quadratic weighted kappa is undefined: y and yhat are constant in the same class")
    return 1.0 - float((W * C).sum()) / den


def _y_p(y, p):
    ya, pa = _binary("y", y), _probability("p", p)
    _same_length(ya, pa, "y", "p")
    return ya, pa


def _both_classes(ya: np.ndarray, what: str) -> None:
    if ya.min() == ya.max():
        raise ValueError(f"{what} needs both classes (0 and 1) in y")


def brier(y, p) -> float:
    """Error de Brier: media de (p − y)²."""
    ya, pa = _y_p(y, p)
    return float(np.mean((pa - ya) ** 2))


def _logit_mle(Z: np.ndarray, y: np.ndarray, offset: np.ndarray) -> np.ndarray:
    """MLE de la logística y ~ Z·w + offset, sin prior."""
    def objective(w):
        eta = Z @ w + offset
        return float(np.sum(np.logaddexp(0.0, eta) - y * eta)), Z.T @ (expit(eta) - y)

    def hess(w):
        pr = expit(Z @ w + offset)
        return Z.T @ ((pr * (1.0 - pr))[:, None] * Z)

    res = minimize(objective, np.zeros(Z.shape[1]), jac=True, hess=hess, method="trust-exact",
                   options={"gtol": 1e-10, "maxiter": 200})
    # como en el ordinal: se juzga por el gradiente; quien llama ya descartó la separación
    if not np.all(np.isfinite(res.x)) or np.max(np.abs(res.jac)) > 1e-6 * max(1.0, math.sqrt(y.size)):
        raise ValueError(f"the calibration regression did not converge: {res.message}")
    return res.x


def calibration_intercept_slope(y, p) -> tuple[float, float]:
    """(intercepto, pendiente) de calibración (Van Calster et al. 2019).

    Pendiente: b de la logística sin *prior* y ~ a + b·logit(p), de 2 parámetros (ideal 1). Intercepto: a de
    y ~ a + offset(logit(p)), con la pendiente fija en 1 (calibración en el total; ideal 0). Exige `p`
    estrictamente entre 0 y 1 (logit finito) e `y` con las dos clases.
    """
    ya, pa = _y_p(y, p)
    if np.any(pa <= 0) or np.any(pa >= 1):
        raise ValueError("p must be strictly between 0 and 1 for the calibration regression (logit(p) finite)")
    _both_classes(ya, "calibration_intercept_slope")
    lp = np.log(pa) - np.log1p(-pa)
    pos, neg = lp[ya == 1], lp[ya == 0]
    if neg.max() <= pos.min() or pos.max() <= neg.min():
        # con una sola variable, separación (aun cuasi completa) = los rangos de p de las dos clases no se cruzan
        raise ValueError("the calibration slope is undefined: p separates the two classes (the slope diverges)")
    ones = np.ones((ya.size, 1))
    intercept = _logit_mle(ones, ya, lp)[0]
    slope = _logit_mle(np.column_stack([ones, lp]), ya, np.zeros_like(lp))[1]
    return float(intercept), float(slope)


def calibration_curve(y, p, n_bins: int = 10) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Curva de calibración por cuantiles de p (deciles con n_bins = 10): (p media, y media, n) de cada bin no
    vacío. Bordes como scikit-learn `calibration_curve(strategy="quantile")`: con empates, los bins repetidos
    quedan vacíos y se omiten."""
    ya, pa = _y_p(y, p)
    if isinstance(n_bins, bool) or not isinstance(n_bins, (int, np.integer)) or n_bins < 1:
        raise ValueError("n_bins must be a positive integer")
    nb = int(n_bins)
    # percentile(q·100) y no quantile(q): con empates exactos el redondeo cambia el bin y así coincide con sklearn
    ids = np.searchsorted(np.percentile(pa, np.linspace(0.0, 1.0, nb + 1) * 100)[1:-1], pa)
    count = np.bincount(ids, minlength=nb)
    keep = count > 0
    return (np.bincount(ids, weights=pa, minlength=nb)[keep] / count[keep],
            np.bincount(ids, weights=ya, minlength=nb)[keep] / count[keep], count[keep])


def roc_auc(y, p) -> float:
    """Área bajo la curva ROC por rangos (Mann–Whitney), con los empates en el rango promedio."""
    ya, pa = _y_p(y, p)
    _both_classes(ya, "roc_auc")
    pos = ya == 1
    n1, n0 = int(pos.sum()), int((~pos).sum())
    return float((rankdata(pa)[pos].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def average_precision(y, p) -> float:
    """Precisión promedio (definición de scikit-learn): Σ (R_k − R_{k−1})·P_k sobre los umbrales distintos de p,
    de mayor a menor, sin interpolar. Necesita al menos un positivo."""
    ya, pa = _y_p(y, p)
    if ya.sum() == 0:
        raise ValueError("average_precision needs at least one positive (y = 1)")
    order = np.argsort(-pa, kind="mergesort")
    ps, ys = pa[order], ya[order]
    last = np.r_[np.nonzero(np.diff(ps))[0], ps.size - 1]  # última fila de cada bloque de empates
    tp = np.cumsum(ys)[last]
    recall = tp / tp[-1]
    return float(np.sum(np.diff(np.r_[0.0, recall]) * tp / (last + 1.0)))
