"""Puntajes propios por parámetro (rangos y pesos), con RMR89 como tabla por defecto.

Un valor justo en el límite de dos intervalos toma el de menos puntos (criterio conservador); un
intervalo puntual [x, x] gana cuando el valor es exactamente x (p. ej. apertura 0 puntúa 6). Validar
avisa con TableIssue y nunca bloquea; rate() sí lanza ValueError ante datos imposibles.
"""

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from .issues import TableIssue

# Máximos por parámetro de RMR89 (comparación de validate)
_RMR89_MAX = {"ucs_mpa": 15, "rqd_pct": 20, "spacing_m": 20, "persistence_m": 6, "aperture_mm": 6,
              "roughness": 6, "infilling": 6, "weathering": 6, "water": 15}
# Techo del dominio de un parámetro numérico para detectar tramos sin cubrir
_DOMAIN_HI = {"rqd_pct": 100.0}


@dataclass(frozen=True)
class RatingBin:
    lo: float
    hi: float
    points: float

    def __post_init__(self):
        if math.isnan(self.lo) or math.isnan(self.hi) or math.isnan(self.points):
            raise ValueError("bin values must not be NaN")
        if self.lo > self.hi:
            raise ValueError(f"bin lo must be <= hi, got {self.lo:g} > {self.hi:g}")


@dataclass(frozen=True)
class NumericParam:
    name: str
    unit: str
    bins: tuple[RatingBin, ...]
    better: str

    def __post_init__(self):
        if self.better not in ("higher", "lower"):
            raise ValueError(f"better must be 'higher' or 'lower', got {self.better!r}")
        object.__setattr__(self, "bins", tuple(self.bins))


@dataclass(frozen=True)
class CategoricalParam:
    name: str
    points: Mapping[str, float]

    def __post_init__(self):
        object.__setattr__(self, "points", MappingProxyType(dict(self.points)))


@dataclass(frozen=True)
class RatingResult:
    total: float
    points: dict[str, float]
    adjustment: float
    base_edition: str
    warnings: list[str] = field(default_factory=list)


def _bins(*rows):
    return tuple(RatingBin(*r) for r in rows)


class RatingTable:
    def __init__(self, base_edition: str, params: Iterable[NumericParam | CategoricalParam],
                 adjustments: Mapping[str, float] | None = None):
        self._edition = base_edition
        self._params = tuple(params)
        names = [p.name for p in self._params]
        if len(set(names)) != len(names):
            raise ValueError(f"duplicate parameter names: {sorted({n for n in names if names.count(n) > 1})}")
        self._adjustments = MappingProxyType(dict(adjustments or {}))

    base_edition = property(lambda self: self._edition)
    params = property(lambda self: self._params)
    adjustments = property(lambda self: self._adjustments)

    @classmethod
    def rmr89_default(cls) -> "RatingTable":
        inf = math.inf
        return cls("RMR89", [
            NumericParam("ucs_mpa", "MPa", _bins((0, 1, 0), (1, 5, 1), (5, 25, 2), (25, 50, 4), (50, 100, 7),
                                                 (100, 250, 12), (250, inf, 15)), "higher"),
            NumericParam("rqd_pct", "%", _bins((0, 25, 3), (25, 50, 8), (50, 75, 13), (75, 90, 17), (90, 100, 20)),
                         "higher"),
            NumericParam("spacing_m", "m", _bins((0, 0.06, 5), (0.06, 0.2, 8), (0.2, 0.6, 10), (0.6, 2, 15),
                                                 (2, inf, 20)), "higher"),
            NumericParam("persistence_m", "m", _bins((0, 1, 6), (1, 3, 4), (3, 10, 2), (10, 20, 1), (20, inf, 0)),
                         "lower"),
            NumericParam("aperture_mm", "mm", _bins((0, 0, 6), (0, 0.1, 5), (0.1, 1, 4), (1, 5, 1), (5, inf, 0)),
                         "lower"),
            CategoricalParam("roughness", {"VeryRough": 6, "Rough": 5, "SlightlyRough": 3, "Smooth": 1,
                                           "Slickensided": 0}),
            CategoricalParam("infilling", {"None": 6, "HardUnder5mm": 4, "HardOver5mm": 2, "SoftUnder5mm": 2,
                                           "SoftOver5mm": 0}),
            CategoricalParam("weathering", {"Unweathered": 6, "Slightly": 5, "Moderately": 3, "Highly": 1,
                                            "Decomposed": 0}),
            CategoricalParam("water", {"Dry": 15, "Damp": 10, "Wet": 7, "Dripping": 4, "Flowing": 0}),
        ], {"VeryFavourable": 0, "Favourable": -2, "Fair": -5, "Unfavourable": -10, "VeryUnfavourable": -12})

    def rate(self, values: Mapping[str, float | str], adjustment: str | None = None) -> RatingResult:
        names = {p.name for p in self._params}
        for k in values:
            if k not in names:
                raise ValueError(f"unknown parameter '{k}'")
        points: dict[str, float] = {}
        for p in self._params:
            if p.name not in values:
                raise ValueError(f"{p.name}: value is required")
            v = values[p.name]
            if isinstance(p, CategoricalParam):
                if v not in p.points:
                    raise ValueError(f"{p.name}: unknown category {v!r}; valid categories: {list(p.points)}")
                points[p.name] = p.points[v]
                continue
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                raise ValueError(f"{p.name}: value must be a finite number, got {v!r}")
            hits = [b for b in p.bins if b.lo <= v <= b.hi]
            if not hits:
                raise ValueError(f"{p.name}: value {v:g} is outside every bin")
            exact = [b for b in hits if b.lo == b.hi]  # el intervalo puntual gana
            points[p.name] = exact[0].points if exact else min(b.points for b in hits)

        warnings: list[str] = []
        adj = 0.0
        if adjustment is not None:
            if adjustment not in self._adjustments:
                raise ValueError(f"unknown adjustment {adjustment!r}; valid adjustments: {list(self._adjustments)}")
            adj = self._adjustments[adjustment]
        elif self._adjustments:
            warnings.append("no adjustment applied: total is the basic rating")
        return RatingResult(sum(points.values()) + adj, points, adj, self._edition, warnings)

    def validate(self) -> list[TableIssue]:
        out: list[TableIssue] = []
        ed = self._edition

        def issue(kind, msg):
            out.append(TableIssue(kind, msg, ed))

        for p in self._params:
            if not isinstance(p, NumericParam):
                continue
            bins = sorted(p.bins, key=lambda b: (b.lo, b.hi))
            top = _DOMAIN_HI.get(p.name, math.inf)
            cursor = 0.0
            for b in bins:
                if b.lo > cursor:
                    issue("gap", f"{p.name}: no bin covers [{cursor:g}, {b.lo:g}]")
                cursor = max(cursor, b.hi)
            if cursor < top:
                issue("gap", f"{p.name}: no bin covers [{cursor:g}, {top:g}]")
            pts = [b.points for b in bins]
            sign = 1 if p.better == "higher" else -1
            if any(sign * (b - a) < 0 for a, b in zip(pts, pts[1:])):
                issue("not_monotonic", f"{p.name}: points do not {'increase' if sign > 0 else 'decrease'} "
                                       f"with the value (better={p.better})")
        if ed == "RMR89":
            total = 0.0
            for p in self._params:
                vals = [b.points for b in p.bins] if isinstance(p, NumericParam) else list(p.points.values())
                mx = max(vals, default=0)
                total += mx
                ref = _RMR89_MAX.get(p.name)
                if ref is not None and mx != ref:
                    issue("max_points", f"{p.name}: maximum is {mx:g}, RMR89 uses {ref}")
            if total != 100:
                issue("max_points", f"total of maximum points is {total:g}, RMR89 totals 100")
        else:  # esquema propio del usuario: se permite, pero no hay máximos contra qué comparar
            issue("no_reference", f"no reference maxima for edition '{ed}'; max_points not checked")
        return out
