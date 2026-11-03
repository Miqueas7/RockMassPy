"""Análisis probabilístico de bloques: Monte Carlo e hipercubo latino con semilla fija (3B, tarea 5).

El azar sale solo de `random.Random(seed).random()` (secuencia estable entre versiones de Python) y de
`statistics.NormalDist`; el FS de cada muestra lo calcula el núcleo C++. Fuente: Hoek (2023) PRE cap. 9.
"""

from __future__ import annotations

import enum
import math
import random
import statistics
from collections.abc import Mapping, Sequence
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
            return
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


def summarize_fs(fs: Sequence[float | None], *, model: str, sampling: str, n: int, seed: int,
                 variables: Sequence[str]) -> ProbabilisticResult:
    valid = [f for f in fs if f is not None]
    if any(math.isnan(f) for f in valid):
        raise ValueError("FS values must not be NaN")
    finite = [f for f in valid if math.isfinite(f)]
    failed = sum(is_failure(f) for f in valid)
    mean = math.fsum(finite) / len(finite) if finite else None
    sd = math.sqrt(math.fsum((f - mean) ** 2 for f in finite) / (len(finite) - 1)) if len(finite) > 1 else None
    beta = beta_ln = None
    if sd and mean > 0:
        v = sd / mean
        beta = (mean - 1) / sd
        beta_ln = math.log(mean / math.sqrt(1 + v * v)) / math.sqrt(math.log(1 + v * v))
    notes, k = [], len(fs) - len(valid)
    if k:
        notes.append(f"{k} samples did not form a block and were excluded")
    k = len(valid) - len(finite)
    if k:
        notes.append(f"{k} samples with no driving force counted as stable and left out of the FS statistics")
    return ProbabilisticResult(
        model, sampling, n, seed, tuple(variables), tuple(fs), len(valid), failed,
        failed / len(valid) if valid else None, mean, sd, min(finite) if finite else None,
        max(finite) if finite else None, beta, beta_ln, PROBABILISTIC_INFO,
        () if valid else ("no valid samples",), tuple(notes))


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
    except TypeError:  # sin constructor vacío (PlaneOrientation, LineOrientation): argumentos en orden
        return type(obj)(*vals.values())
    for n, v in vals.items():
        setattr(new, n, v)
    return new


def _valid_names(model: str, base) -> list[str]:
    names = [n for n in _props(base) if isinstance(getattr(base, n), float)]
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
            raise ValueError(f"unknown variable '{name}' for model '{model}'; valid names: {', '.join(valid)}")
    draws = sample(variables, n, sampling=sampling, seed=seed)
    names = tuple(draws)
    work = _clone(base)  # una copia de trabajo: la base no se toca
    fs: list[float | None] = []
    for i in range(n):
        for name in names:
            _assign(work, name, draws[name][i])
        try:
            fs.append(fn(work).factor_of_safety)
        except ValueError as e:
            msg = str(e)
            hit = [v for v in names if f"'{v.split('.')[-1]}'" in msg]
            if not hit:  # no viene de una variable muestreada: mensaje del núcleo sin el valor
                raise ValueError(msg.split("Received:")[0].strip()) from None
            who = "' or '".join(hit)
            raise ValueError(f"variable '{who}': a sampled value is outside the valid range of the model; "
                             "narrow its minimum and maximum") from None
    return summarize_fs(fs, model=model, sampling=sampling, n=n, seed=seed, variables=names)
