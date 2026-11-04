"""Estadística lineal del nivel 1 (Fase 4A, tarea 3): OLS, Deming, bootstrap por grupos y bayesiano conjugado.

Modelo y = a·x + b en todos: quien llama transforma x antes (por ejemplo ln Q). Métodos y por qué, en
`docs/investigacion/MODELOS_SOSTENIMIENTO.md` §2.2: OLS con intervalo de predicción para predecir Y desde una X
medida (Warton et al. 2006); Deming para la relación estructural, solo con la razón de varianzas de error
(Carroll et al. 2006); bootstrap que remuestrea labores y no filas (Efron y Tibshirani 1994); bayesiano que se
encoge hacia la correlación global con pocos datos (Ching et al. 2020).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass
from typing import NamedTuple

import numpy as np
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


class DemingFit(NamedTuple):
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
            or abs(sxy) <= 1e-12 * math.sqrt(sxx * syy):
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

    def percentile_ci(self, level: float = 0.95) -> tuple:
        """IC por percentiles: (inferior, superior), escalares o arreglos según la estadística."""
        lv = _level(level)
        if len(self.replicates) == 0:
            raise ValueError("no valid bootstrap replicates: every resample was degenerate")
        lo, hi = np.quantile(self.replicates, [0.5 - lv / 2, 0.5 + lv / 2], axis=0)
        return (float(lo), float(hi)) if np.ndim(lo) == 0 else (lo, hi)


def group_bootstrap(groups: Sequence[Hashable], statistic: Callable[[np.ndarray], object], *,
                    n_boot: int = 2000, seed: int = 0) -> BootstrapResult:
    """Bootstrap por grupos (labores): remuestrea grupos completos con reemplazo, no filas.

    `groups[i]` es el grupo de la fila i. Cada réplica sortea tantos grupos como hay, concatena los índices de sus
    filas (un grupo repetido aparece repetido) y llama `statistic(indices)`. Si la estadística lanza ValueError,
    FloatingPointError o LinAlgError, o devuelve algo no finito (p. ej. x constante en la réplica), la réplica se
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
    kept, discarded = [], 0
    for _ in range(int(n_boot)):
        pick = rng.integers(0, len(members), size=len(members))
        idx = np.concatenate([members[k] for k in pick])
        try:
            value = np.asarray(statistic(idx), dtype=float)
        except (ValueError, FloatingPointError, np.linalg.LinAlgError):
            discarded += 1
            continue
        if not np.all(np.isfinite(value)):
            discarded += 1
            continue
        kept.append(value)
    reps = np.stack(kept) if kept else np.empty((0,))
    return BootstrapResult(replicates=reps, n_discarded=discarded, n_boot=int(n_boot))


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
