"""Análisis probabilístico de bloques: Monte Carlo e hipercubo latino con semilla fija (3B, tarea 5).

El azar sale solo de `random.Random(seed).random()` (secuencia estable entre versiones de Python) y de
`statistics.NormalDist`; el FS de cada muestra lo calcula el núcleo C++. Fuente: Hoek (2023) PRE cap. 9.
Independencia de plataforma: la secuencia de `random()` es exacta; las funciones trascendentes del núcleo C++ (sin,
cos, atan, ...) pueden diferir en 1 ulp entre plataformas, así que un FS puede variar en ~1e-15 relativo.
"""

from __future__ import annotations

import enum
import math
import random
import re
import statistics
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass

from . import _rockmasspy_core as rm

PROBABILISTIC_INFO = rm.MethodInfo(
    "Probabilistic-MC-LHS", rm.Verification.Secondary,
    "Hoek (2023) Practical Rock Engineering ch. 9: PoF = share of F < 1 (p. 12), sample variance with n - 1 "
    "(eq. 2, p. 4), Latin hypercube as stratified sampling (p. 7, Iman et al. 1980 not read); reliability indices "
    "derived for normal and lognormal FS (eq. 5; Velarde & Macciotta 2023 eqs. 7-9)")

_P_EDGE = 1e-15


def _finite(*vals) -> bool:
    return all(v is None or (isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v))
               for v in vals)


@dataclass(frozen=True)
class Distribution:
    kind: str
    minimum: float
    maximum: float
    mean: float | None = None
    sd: float | None = None

    def __post_init__(self):
        k = self.kind
        if k not in ("normal", "exponential", "uniform"):
            raise ValueError("distribution kind must be 'normal', 'exponential' or 'uniform'")
        if not _finite(self.minimum, self.maximum, self.mean, self.sd):
            raise ValueError(f"{k} distribution: all parameters must be finite numbers")
        if self.minimum >= self.maximum:
            raise ValueError(f"{k} distribution: minimum must be below maximum")
        if k == "uniform":
            if self.mean is not None or self.sd is not None:
                raise ValueError("uniform distribution takes no mean or sd")
            return
        if k == "exponential" and self.sd is not None:
            raise ValueError("exponential distribution takes no sd")
        if self.mean is None:
            raise ValueError(f"{k} distribution: mean is required")
        if k == "normal" and (self.sd is None or self.sd <= 0):
            raise ValueError("normal distribution: sd must be positive")
        if k == "exponential" and (self.mean <= 0 or self.minimum < 0):
            raise ValueError("exponential distribution: mean must be positive and minimum not negative")
        if not self.minimum <= self.mean <= self.maximum:
            raise ValueError(f"{k} distribution: mean must lie between minimum and maximum")
        lo, hi = self._cdf_bounds()
        if hi - lo < 1e-12:
            raise ValueError(f"{k} distribution: the truncation range has almost no probability")

    def _cdf_bounds(self) -> tuple[float, float]:
        if self.kind == "normal":
            nd = statistics.NormalDist(self.mean, self.sd)
            return nd.cdf(self.minimum), nd.cdf(self.maximum)
        return -math.expm1(-self.minimum / self.mean), -math.expm1(-self.maximum / self.mean)

    def ppf(self, u: float) -> float:
        if not 0 <= u <= 1:
            raise ValueError("u must be in [0, 1]")
        if self.kind == "uniform":
            x = self.minimum + u * (self.maximum - self.minimum)
        else:
            lo, hi = self._cdf_bounds()
            p = lo + u * (hi - lo)
            if self.kind == "normal":
                x = statistics.NormalDist(self.mean, self.sd).inv_cdf(min(max(p, _P_EDGE), 1 - _P_EDGE))
            else:
                x = -self.mean * math.log1p(-min(p, 1 - _P_EDGE))
        return min(max(x, self.minimum), self.maximum)


def normal(mean: float, sd: float, minimum: float, maximum: float) -> Distribution:
    return Distribution("normal", minimum, maximum, mean, sd)


def exponential(mean: float, minimum: float, maximum: float) -> Distribution:
    """Exponencial de media madre `mean`, truncada en [minimum, maximum] (R12)."""
    return Distribution("exponential", minimum, maximum, mean)


def uniform(minimum: float, maximum: float) -> Distribution:
    return Distribution("uniform", minimum, maximum)


def sample(variables: Mapping[str, Distribution], n: int, *, sampling: str = "lhs",
           seed: int = 1) -> dict[str, tuple[float, ...]]:
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("n must be an integer >= 1")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be an integer >= 0")
    if sampling not in ("lhs", "monte_carlo"):
        raise ValueError("sampling must be 'lhs' or 'monte_carlo'")
    rng = random.Random(seed)
    out = {}
    for name in sorted(variables):
        d = variables[name]
        if sampling == "monte_carlo":
            u = [rng.random() for _ in range(n)]
        else:  # permutación por claves random(): shuffle no tiene secuencia garantizada
            keys = [rng.random() for _ in range(n)]
            u = [(s + rng.random()) / n for s in sorted(range(n), key=keys.__getitem__)]
        out[name] = tuple(d.ppf(x) for x in u)
    return out


def is_failure(fs: float) -> bool:
    """Única regla de falla: el valor justo en 1 toma el lado menos favorable (R13)."""
    return fs < 1 + 1e-9


@dataclass(frozen=True)
class ProbabilisticResult:
    model: str
    sampling: str
    n: int
    seed: int
    variables: tuple[str, ...]
    fs: tuple[float | None, ...]
    n_valid: int
    n_failed: int
    pof: float | None
    fs_mean: float | None
    fs_sd: float | None
    fs_min: float | None
    fs_max: float | None
    reliability_index: float | None
    reliability_index_lognormal: float | None
    info: rm.MethodInfo
    warnings: tuple[str, ...]
    notes: tuple[str, ...]
    excluded: tuple[int, ...] = ()  # índices de muestras con FS acotado (tope o cota superior): fuera de la estadística


def summarize_fs(fs: Sequence[float | None], *, model: str, sampling: str, n: int, seed: int,
                 variables: Sequence[str], extra_warnings: Sequence[str] = (),
                 extra_notes: Sequence[str] | None = None, capped: Collection[int] = (),
                 upper_bounds: Collection[int] = ()) -> ProbabilisticResult:
    """Estadística de las muestras. `capped` y `upper_bounds` son índices de `fs`, y una cota no es un FS: las dos
    salen de la media, la desviación, el mínimo, el máximo y los índices. En la PoF cuentan del lado que se conoce: el
    tope (cota inferior) como estable, como el infinito; la cota superior como falla, el lado menos favorable."""
    valid = [f for f in fs if f is not None]
    if any(math.isnan(f) or f == -math.inf for f in valid):
        raise ValueError("fs: values must not be NaN or -inf")
    capped, upper_bounds = set(capped), set(upper_bounds)
    excluded = capped | upper_bounds
    finite = [f for i, f in enumerate(fs) if f is not None and math.isfinite(f) and i not in excluded]
    failed = sum(i in upper_bounds or is_failure(f) for i, f in enumerate(fs) if f is not None)
    mean = math.fsum(finite) / len(finite) if finite else None
    sd = math.sqrt(math.fsum((f - mean) ** 2 for f in finite) / (len(finite) - 1)) if len(finite) > 1 else None
    beta = beta_ln = None
    notes = []
    if sd is not None and sd <= 1e-12 * abs(mean):  # dispersión de puro redondeo: β sería ±1e15 inventado
        notes.append("FS does not vary with the sampled variables; reliability index undefined")
    elif sd is not None and mean > 0:
        v = sd / mean
        beta = (mean - 1) / sd
        beta_ln = math.log(mean / math.sqrt(1 + v * v)) / math.sqrt(math.log1p(v * v))
    k = len(fs) - len(valid)
    if k and extra_notes is None:  # run_probabilistic da su propia nota con el motivo del núcleo
        notes.append(f"{k} samples did not form a block and were excluded")
    notes = list(extra_notes or ()) + notes
    k = sum(1 for f in valid if math.isinf(f))
    if k:
        notes.append(f"{k} samples with no driving force counted as stable and left out of the FS statistics")
    if capped:
        notes.append(f"{len(capped)} of {n} samples have FS above the cap; excluded from the statistics")
    if upper_bounds:
        notes.append(f"{len(upper_bounds)} of {n} samples have FS only as an upper bound; counted as failures and "
                     "excluded from the statistics")
    if not valid:  # un bloque que nunca se forma es nota, no aviso (R14)
        notes.append("no valid samples")
    return ProbabilisticResult(
        model, sampling, n, seed, tuple(variables), tuple(fs), len(valid), failed,
        failed / len(valid) if valid else None, mean, sd, min(finite) if finite else None,
        max(finite) if finite else None, beta, beta_ln, PROBABILISTIC_INFO, tuple(extra_warnings), tuple(notes),
        tuple(sorted(excluded)))


_MODELS = {"planar": (rm.PlanarInput, rm.planar_fs), "wedge": (rm.WedgeInput, rm.wedge_fs),
           "toppling": (rm.TopplingInput, rm.toppling_fs)}
_JOINT_FIELDS = ("cohesion", "friction_deg", "water_pressure")


def _props(obj):
    return [n for n, v in vars(type(obj)).items() if not n.startswith("_") and isinstance(v, property)]


def _clone(obj):
    """Copia una estructura del núcleo recorriendo sus propiedades públicas (como `_install_reprs`)."""
    if isinstance(obj, list):
        return list(obj)
    if isinstance(obj, enum.Enum) or not type(obj).__module__.startswith("rockmasspy"):
        return obj
    vals = {n: _clone(getattr(obj, n)) for n in _props(obj)}
    try:
        new = type(obj)()
    except TypeError:  # sin constructor vacío (PlaneOrientation, LineOrientation): por nombre
        return type(obj)(**vals)
    for n, v in vals.items():
        setattr(new, n, v)
    return new


def _valid_names(model: str, base) -> list[str]:
    # un opcional vacío (None) se puede muestrear: la muestra aporta el valor
    names = [n for n in _props(base) if isinstance(getattr(base, n), float) or getattr(base, n) is None]
    if model == "wedge":
        names += [f"{j}.{f}" for j in ("joint1", "joint2") for f in _JOINT_FIELDS]
    return sorted(names)


def _assign(work, name: str, value: float) -> None:
    if "." in name:
        joint, field = name.split(".")
        j = getattr(work, joint)
        setattr(j, field, value)
        setattr(work, joint, j)  # vale tanto si el binding devuelve copia como referencia
    else:
        setattr(work, name, value)


def run_probabilistic(model: str, base, variables: Mapping[str, Distribution], *, n: int = 5000,
                      sampling: str = "lhs", seed: int = 1) -> ProbabilisticResult:
    if model not in _MODELS:
        raise ValueError("model must be 'planar', 'wedge' or 'toppling'")
    cls, fn = _MODELS[model]
    if not isinstance(base, cls):
        raise ValueError(f"base must be a {cls.__name__} for model '{model}'")
    valid = _valid_names(model, base)
    for name in variables:
        if name not in valid:
            raise ValueError(f"unknown variable; allowed: {', '.join(valid)}")
    draws = sample(variables, n, sampling=sampling, seed=seed)
    names = tuple(draws)
    work = _clone(base)  # una copia de trabajo: la base no se toca
    fs: list[float | None] = []
    warns: dict[str, int] = {}
    notes: dict[str, int] = {}
    reasons: dict[str, int] = {}
    capped, bounded = [], []
    for i in range(n):
        for name in names:
            _assign(work, name, draws[name][i])
        try:
            r = fn(work)
        except ValueError as e:
            msg = str(e)
            hit = [v for v in names if f"parameter '{v}'" in msg]
            if not hit:  # combinación con un campo fijo: mensaje del núcleo sin el valor
                raise ValueError(msg.split("Received:")[0].strip()) from None
            raise ValueError(f"variable '{hit[0]}': a sampled value is outside the valid range of the model; "
                             "narrow its minimum and maximum") from None
        fs.append(r.factor_of_safety)
        if model == "toppling":
            # la cota tan(phi)/(1 - 1e-9) nunca prueba FS > 1 (el mu requerido es >= 1): cuenta como falla
            if r.fs_bounded:
                bounded.append(i)
            elif r.capped:  # el tope solo trae su nota, que summarize_fs da una vez para todas las muestras
                capped.append(i)
                continue
        for w in set(map(_norm, r.warnings)):
            warns[w] = warns.get(w, 0) + 1
        if r.factor_of_safety is None:  # el motivo de no formarse va en la nota del bloque
            for t in set(map(_norm, r.notes)) or {"no reason given"}:
                reasons[t] = reasons.get(t, 0) + 1
        else:
            for t in set(map(_norm, r.notes)):
                notes[t] = notes.get(t, 0) + 1
    return summarize_fs(
        fs, model=model, sampling=sampling, n=n, seed=seed, variables=names,
        extra_warnings=[f"{t} ({k} of {n} samples)" for t, k in warns.items()],
        extra_notes=[f"{k} of {n} samples do not form a block ({t})" for t, k in reasons.items()]
        + [f"{t} ({k} of {n} samples)" for t, k in notes.items()], capped=capped, upper_bounds=bounded)


def _norm(text: str) -> str:
    """Agrupa textos del núcleo que solo difieren en un conteo («fail in 3 blocks» y «fail in 5 blocks»).

    Solo cambia el entero suelto seguido de una palabra (el conteo); «(8)-(9)», «above 100» y «below 1;» quedan.
    """
    return re.sub(r"(?<![\w(.\-])\d+(?= [A-Za-z])", "N", text)
