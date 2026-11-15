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


def fit_surrogate(data: SurrogateData, *, kind: str = "poly2", smoothing: float = 0.0) -> Surrogate:
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
