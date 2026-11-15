"""Modelo sustituto de corridas costosas (Fase 8D, tarea 1): datos, superficie cuadrática, RBF y dominio.

El sustituto NO extrapola: fuera del dominio de entrenamiento `predict` devuelve NaN y lo marca. Un punto está en el
dominio si cada variable cae en [mín, máx] ampliado `DOMAIN_BOX_MARGIN` del rango Y su distancia de Mahalanobis al
centro (X estandarizadas, pseudoinversa si la covarianza es singular) cumple d² <= chi2(p, DOMAIN_CHI2_LEVEL).
La caja sola deja pasar esquinas nunca vistas cuando las entradas están correlacionadas; la Mahalanobis las saca.
Los errores nombran columnas o `runs`, nunca valores.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
from scipy.interpolate import RBFInterpolator
from scipy.stats import chi2

from .. import _rockmasspy_core as rm
from ..external import _blank, _number, _rows

# decisiones de diseño (por confirmar, S3): margen de la caja y nivel de la chi cuadrada
DOMAIN_BOX_MARGIN = 0.05
DOMAIN_CHI2_LEVEL = 0.99
KINDS = ("poly2", "rbf")
_INFO = {
    "poly2": rm.MethodInfo("Surrogate-poly2", rm.Verification.Secondary,
                           "Quadratic response surface (linear, squares, cross products) by least squares on "
                           "standardized inputs; own numerical method, not a published formula"),
    "rbf": rm.MethodInfo("Surrogate-RBF", rm.Verification.Secondary,
                         "Thin-plate-spline RBF with linear tail (scipy RBFInterpolator) on standardized inputs; "
                         "own numerical method, not a published formula"),
}


@dataclass(frozen=True)
class SurrogateData:
    """Corridas: X (n, p), salida y (n,), nombres de las p entradas y grupo (escenario) opcional por corrida."""

    X: np.ndarray
    y: np.ndarray
    names: tuple[str, ...]
    groups: tuple | None = None
    notes: tuple[str, ...] = field(default=())

    def __post_init__(self):
        X, y = np.asarray(self.X, dtype=float), np.asarray(self.y, dtype=float)
        if X.ndim != 2 or y.shape != (X.shape[0],) or len(self.names) != X.shape[1]:
            raise ValueError("runs: X must be (n, p), y (n,) and names one per input column")
        if len(set(self.names)) != len(self.names):
            raise ValueError("names: duplicate input names")
        if self.groups is not None and len(self.groups) != X.shape[0]:
            raise ValueError("groups: expected one group per run")
        object.__setattr__(self, "X", X)
        object.__setattr__(self, "y", y)
        object.__setattr__(self, "names", tuple(self.names))


def load_runs(path, *, sheet: str = "Corridas", output: str, group: str | None = None,
              inputs: Sequence[str] | None = None) -> SurrogateData:
    """Lee corridas de un CSV (coma decimal incluida) o un Excel. `inputs=None`: todas las columnas numéricas
    menos la salida y el grupo. Las filas con la salida vacía o no finita se descartan con una nota."""
    sheet, header, rows, dec = _rows(path, sheet)
    col = {str(h).strip(): i for i, h in enumerate(header) if not _blank(h)}
    if output not in col:
        raise ValueError(f"sheet '{sheet}': missing output column")
    if group is not None and group not in col:
        raise ValueError(f"sheet '{sheet}': missing group column")
    rows = [r for r in rows if not all(_blank(v) for v in r)]
    cell = lambda r, i: r[i] if i < len(r) else None  # noqa: E731

    def numeric(i):
        vals = [cell(r, i) for r in rows if not _blank(cell(r, i))]
        try:
            for v in vals:
                _number(v, sheet, 0, "", dec)
        except ValueError:
            return False
        return bool(vals)

    if inputs is None:
        inputs = [h for h, i in col.items() if h not in (output, group) and numeric(i)]
    else:
        inputs = list(inputs)
        if any(h not in col for h in inputs):
            raise ValueError(f"sheet '{sheet}': missing input column")
    if not inputs:
        raise ValueError(f"sheet '{sheet}': no numeric input columns")

    X, y, g, dropped = [], [], [], False
    for n, r in enumerate(rows, start=2):
        v = cell(r, col[output])
        try:
            yv = None if _blank(v) else _number(v, sheet, n, output, dec)
        except ValueError:
            yv = None
        if yv is None or not math.isfinite(yv):
            dropped = True
            continue
        row = []
        for h in inputs:
            v = cell(r, col[h])
            if _blank(v):
                raise ValueError(f"sheet '{sheet}', row {n}, column '{h}': empty input value")
            row.append(_number(v, sheet, n, h, dec))
        X.append(row)
        y.append(yv)
        if group is not None:
            g.append(str(cell(r, col[group])).strip())
    notes = ("runs without a finite output ignored",) if dropped else ()
    return SurrogateData(np.array(X, dtype=float).reshape(len(y), len(inputs)), np.array(y), tuple(inputs),
                         tuple(g) if group is not None else None, notes)


def _poly2(Z: np.ndarray) -> np.ndarray:
    p = Z.shape[1]
    cols = [np.ones(len(Z))] + [Z[:, i] for i in range(p)]
    cols += [Z[:, i] * Z[:, j] for i in range(p) for j in range(i, p)]  # cuadrados y cruzados
    return np.column_stack(cols)


@dataclass(frozen=True)
class SurrogatePrediction:
    """`y` es NaN donde `in_domain` es falso; `distance` = d² de Mahalanobis (informativa)."""

    y: np.ndarray
    in_domain: np.ndarray
    distance: np.ndarray


@dataclass(frozen=True)
class Surrogate:
    names: tuple[str, ...]
    kind: str
    info: object
    mean: np.ndarray = field(repr=False)
    std: np.ndarray = field(repr=False)
    lo: np.ndarray = field(repr=False)
    hi: np.ndarray = field(repr=False)
    cov_pinv: np.ndarray = field(repr=False)
    chi2_limit: float = 0.0
    _model: object = field(default=None, repr=False)

    def predict(self, X) -> SurrogatePrediction:
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(1, -1)
        if X.ndim != 2 or X.shape[1] != len(self.names):
            raise ValueError("X: expected one column per surrogate input")
        Z = (X - self.mean) / self.std
        with np.errstate(invalid="ignore"):
            in_box = np.all((X >= self.lo) & (X <= self.hi), axis=1)  # NaN queda fuera
            d2 = np.einsum("ij,jk,ik->i", Z, self.cov_pinv, Z)
            ok = in_box & (d2 <= self.chi2_limit)
        y = np.full(len(X), np.nan)
        if ok.any():
            y[ok] = self._model(Z[ok])
        return SurrogatePrediction(y, ok, d2)


def fit_surrogate(data: SurrogateData, *, kind: str = "rbf", smoothing: float = 0.0) -> Surrogate:
    if kind not in KINDS:
        raise ValueError(f"kind: must be one of {', '.join(KINDS)}")
    X, y = data.X, data.y
    n, p = X.shape
    if kind == "poly2" and n < (p + 1) * (p + 2) // 2 + 1:  # al menos un grado de libertad tras los coeficientes
        raise ValueError("runs: too few runs for a quadratic response surface")
    if n < 2 * p + 2:
        raise ValueError("runs: too few runs for the number of inputs (need at least 2p + 2)")
    if not (np.all(np.isfinite(X)) and np.all(np.isfinite(y))):
        raise ValueError("runs: inputs and output must be finite")
    mean, std = X.mean(axis=0), X.std(axis=0)
    for j, h in enumerate(data.names):
        if std[j] == 0:
            raise ValueError(f"column '{h}': constant input, remove it or vary it")
    Z = (X - mean) / std
    if kind == "poly2":
        beta = np.linalg.lstsq(_poly2(Z), y, rcond=None)[0]
        model = lambda Zq: _poly2(Zq) @ beta  # noqa: E731
    else:
        if smoothing == 0 and len(np.unique(X, axis=0)) < n:  # scipy no siempre detecta la matriz singular
            raise ValueError("runs: duplicate or collinear inputs; use smoothing > 0")
        try:
            model = RBFInterpolator(Z, y, kernel="thin_plate_spline", degree=1, smoothing=smoothing)
        except np.linalg.LinAlgError:
            raise ValueError("runs: duplicate or collinear inputs; use smoothing > 0") from None
    lo, hi = X.min(axis=0), X.max(axis=0)
    cov = np.atleast_2d(np.cov(Z, rowvar=False))
    return Surrogate(data.names, kind, _INFO[kind], mean, std, lo - DOMAIN_BOX_MARGIN * (hi - lo),
                     hi + DOMAIN_BOX_MARGIN * (hi - lo), np.linalg.pinv(cov),
                     float(chi2.ppf(DOMAIN_CHI2_LEVEL, p)), model)


# ---------- validación agrupada (Fase 8D, tarea 2) ----------

# decisión de diseño (por confirmar, S4): el sustituto es útil si su RMSE fuera de pliegue es menor que esta fracción
# del RMSE del modelo «media»
USEFUL_RMSE_RATIO = 0.5
OOD_WARN_FRACTION = 0.05


@dataclass(frozen=True)
class SurrogateValidation:
    """Métricas fuera de pliegue con las predicciones fuera del dominio EXCLUIDAS (se cuentan en `ood_fraction`)."""

    kind: str
    folds_kind: str
    n_folds: int
    rmse: float
    mae: float
    max_abs_error: float
    r2: float
    ood_fraction: float
    rmse_mean_model: float
    useful: bool
    warnings: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


def validate_surrogate(data: SurrogateData, *, kind: str = "rbf", k: int = 5, seed: int = 0,
                       smoothing: float = 0.0) -> SurrogateValidation:
    from .validation import group_kfold, leave_one_group_out, random_kfold

    n = len(data.y)
    notes: list[str] = []
    n_groups = len(set(data.groups)) if data.groups is not None else 0
    if n_groups < 2:
        folds, folds_kind = random_kfold(n, k=k, seed=seed), "random_kfold"
        notes.append("no groups given: random folds overestimate accuracy" if n_groups == 0
                     else "a single group: random folds used")
    elif n_groups >= k:
        folds, folds_kind = group_kfold(data.groups, k=k, seed=seed), "group_kfold"
    else:
        folds, folds_kind = leave_one_group_out(data.groups), "leave_one_group_out"
    err, base_err, y_all, n_ood = [], [], [], 0
    for f in folds:
        try:  # el error de un pliegue nombra `runs`, nunca el pliegue ni sus filas
            s = fit_surrogate(SurrogateData(data.X[f.train], data.y[f.train], data.names), kind=kind,
                              smoothing=smoothing)
        except ValueError as e:
            if str(e).startswith("runs:"):
                raise  # conserva el mensaje específico (p. ej. "use smoothing > 0")
            raise ValueError("runs: a training fold is degenerate for this surrogate; use fewer folds or "
                             "more runs") from None
        pred = s.predict(data.X[f.test])
        ok = pred.in_domain
        n_ood += int((~ok).sum())
        yt = data.y[f.test][ok]
        err.append(pred.y[ok] - yt)
        base_err.append(data.y[f.train].mean() - yt)
        y_all.append(yt)
    e, b, yt = np.concatenate(err), np.concatenate(base_err), np.concatenate(y_all)
    if e.size == 0:
        raise ValueError("runs: no fold prediction fell inside the surrogate domain")
    rmse, rmse0 = float(np.sqrt(np.mean(e ** 2))), float(np.sqrt(np.mean(b ** 2)))
    sst = float(np.sum((yt - yt.mean()) ** 2))
    ood = n_ood / n
    warns = ("many fold predictions outside the surrogate domain; the metrics cover only the in-domain part",) \
        if ood > OOD_WARN_FRACTION else ()
    return SurrogateValidation(kind, folds_kind, len(folds), rmse, float(np.mean(np.abs(e))),
                               float(np.max(np.abs(e))), 1 - float(np.sum(e ** 2)) / sst if sst > 0 else math.nan,
                               ood, rmse0, bool(rmse < USEFUL_RMSE_RATIO * rmse0), warns, tuple(notes))


# ---------- PoF con el sustituto (Fase 8D, tarea 3) ----------

@dataclass(frozen=True)
class SurrogatePof:
    """`pof` = fracción de muestras válidas (dentro del dominio) con FS < umbral; las `n_out_of_domain` se excluyen.

    Es condicional al dominio del sustituto y puede quedar del lado inseguro (las colas excluidas suelen fallar más):
    `pof_lower` (las excluidas no fallan) y `pof_upper` (todas fallan) acotan la PoF de la distribución completa.
    """

    pof: float
    n: int
    n_valid: int
    n_out_of_domain: int
    fs_mean: float
    fs_p05: float
    fs_p50: float
    fs_p95: float
    warnings: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    pof_lower: float = math.nan
    pof_upper: float = math.nan


def surrogate_pof(surrogate: Surrogate, variables, *, n: int = 20000, sampling: str = "lhs", seed: int = 1,
                  threshold: float = 1.0) -> SurrogatePof:
    from ..probabilistic import sample

    if not (isinstance(threshold, (int, float)) and not isinstance(threshold, bool) and math.isfinite(threshold)):
        raise ValueError("threshold: must be a finite number")
    from ..probabilistic import Distribution
    if not all(isinstance(d, Distribution) for d in variables.values()):
        raise ValueError("variables: every value must be a Distribution")
    if not set(variables) <= set(surrogate.names):
        raise ValueError("variables: every name must be an input of the surrogate")
    if not variables:
        raise ValueError("variables: at least one input must be sampled")
    draws = sample(variables, n, sampling=sampling, seed=seed)
    X = np.tile(surrogate.mean, (n, 1))  # las no muestreadas quedan en la media de entrenamiento
    for name, v in draws.items():
        X[:, surrogate.names.index(name)] = v
    pred = surrogate.predict(X)
    fs = pred.y[pred.in_domain]
    n_valid = len(fs)
    if n_valid == 0:
        raise ValueError("variables: no sample fell inside the surrogate domain")
    n_ood = n - n_valid
    notes = ("unsampled inputs fixed at their training mean",) if len(variables) < len(surrogate.names) else ()
    if n_ood:
        notes += ("PoF conditional on the surrogate domain; see pof_lower and pof_upper",)
    if surrogate.kind == "poly2":
        notes += ("a quadratic surface can bias the PoF near the threshold; check it with kind='rbf'",)
    warns = ("many samples outside the surrogate domain; the PoF covers only the surrogate domain",)         if n_ood / n > OOD_WARN_FRACTION else ()
    n_fail = int(np.sum(fs < threshold))
    p05, p50, p95 = np.percentile(fs, [5, 50, 95])
    return SurrogatePof(n_fail / n_valid, n, n_valid, n_ood, float(fs.mean()), float(p05), float(p50),
                        float(p95), warns, notes, n_fail / n, (n_fail + n_ood) / n)


# ---------- lectores para la CLI (Fase 8D, tarea 4) ----------

def load_points(path, names: Sequence[str], *, sheet: str = "Predicciones") -> np.ndarray:
    """Puntos a predecir: una columna por entrada del sustituto (el orden del archivo no importa)."""
    sheet, header, rows, dec = _rows(path, sheet)
    col = {str(h).strip(): i for i, h in enumerate(header) if not _blank(h)}
    if any(h not in col for h in names):
        raise ValueError(f"sheet '{sheet}': missing input column")
    rows = [r for r in rows if not all(_blank(v) for v in r)]
    if not rows:
        raise ValueError(f"sheet '{sheet}': no points")
    out = []
    for n, r in enumerate(rows, start=2):
        row = []
        for h in names:
            v = r[col[h]] if col[h] < len(r) else None
            if _blank(v):
                raise ValueError(f"sheet '{sheet}', row {n}, column '{h}': empty input value")
            row.append(_number(v, sheet, n, h, dec))
        out.append(row)
    return np.array(out, dtype=float)


def load_variables(path, names: Sequence[str], *, sheet: str = "Distribuciones") -> dict:
    """Hoja `Distribuciones` de la 3B (variable, distribucion, media, desviacion, minimo, maximo) -> {entrada: Distribution}.

    Reusa el lector común (validación de la 3B); el enlace es la propia `variable`, que debe ser una entrada del sustituto.
    """
    from ..blocks import _KINDS, _check_distribution, load_distribution_rows
    from ..probabilistic import Distribution

    by_fold = {n.casefold(): n for n in names}  # el lector normaliza la variable a minúsculas

    @dataclass(frozen=True)
    class _Row:
        variable: str
        distribucion: str
        media: float | None
        desviacion: float | None
        minimo: float
        maximo: float
        fila: int
        hoja: str

    def build(vals, n, sh):
        _check_distribution(vals, n, sh, "variable", set(by_fold), {})
        return _Row(**vals, fila=n, hoja=sh)

    rows = load_distribution_rows(path, sheet, None, "variable",
                                  ("variable", "distribucion", "media", "desviacion", "minimo", "maximo"), build)
    return {by_fold[r.variable]: Distribution(_KINDS[r.distribucion], r.minimo, r.maximo, r.media, r.desviacion)
            for r in rows}
