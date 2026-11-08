"""Tabla de clases por rango para RMR, Q y GSI (más valor = mejor calidad).

Cada clase cubre [lo, hi] con su sostenimiento. Un valor justo en un límite cae en dos clases y toma
la de menor `lo` (la peor calidad, criterio conservador). Validar avisa con TableIssue y nunca
bloquea; solo los datos imposibles (límites no finitos o lo >= hi, rótulo vacío, método/edición desconocidos)
lanzan ValueError.
"""

import math
from collections.abc import Iterable
from dataclasses import dataclass

from .issues import TableIssue
from .support import SupportCatalog

# método -> (ediciones permitidas, (mínimo, máximo) del dominio)
RANGE_METHODS = {
    "RMR": (("RMR76", "RMR89", "RMR14"), (0.0, 100.0)),
    "Q": (("Q-NGI-2015", "Q-NGI-2025"), (0.001, 1000.0)),
    "GSI": (("GSI-2013", "GSI-Vallejo-Osinergmin2017"), (0.0, 100.0)),
}

# límites de clase estándar de cada edición (GSI no tiene)
EDITION_BOUNDARIES = {
    "RMR76": (20, 40, 60, 80),
    "RMR89": (20, 40, 60, 80),
    "RMR14": (20, 40, 60, 80),
    "Q-NGI-2025": (0.01, 0.1, 1, 4, 10, 40),
    "Q-NGI-2015": (0.01, 0.1, 1, 4, 10, 40, 100, 400),
}

# P6 (valores provisionales): cercanía a un borde de clase; "points" = diferencia absoluta, "factor" = cociente
NEAR_BOUNDARY = {"RMR": ("points", 3.0), "GSI": ("points", 3.0), "Q": ("factor", 1.25)}
_NEAR_EPS = 1e-9  # a favor de avisar


@dataclass(frozen=True)
class RangeClass:
    lo: float
    hi: float
    label: str
    support: str | None = None

    def __post_init__(self):
        if not (math.isfinite(self.lo) and math.isfinite(self.hi)):
            raise ValueError(f"class limits must be finite, got {self.lo!r}, {self.hi!r}")
        if self.lo >= self.hi:
            raise ValueError(f"class lo must be < hi, got {self.lo:g} >= {self.hi:g}")
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError(f"class label must be a non-empty string, got {self.label!r}")
        object.__setattr__(self, "label", self.label.strip())
        if self.support is not None:  # un código numérico de YAML (support: 3) pasa a texto
            object.__setattr__(self, "support", str(self.support).strip() or None)


class RangeTable:
    def __init__(self, method: str, base_edition: str, classes: Iterable[RangeClass]):
        if method not in RANGE_METHODS:
            raise ValueError(f"unknown method {method!r}; valid methods: {list(RANGE_METHODS)}")
        editions = RANGE_METHODS[method][0]
        if base_edition not in editions:
            raise ValueError(f"unknown edition {base_edition!r} for {method}; valid editions: {list(editions)}")
        self._method, self._edition = method, base_edition
        self._classes = tuple(classes)
        if not self._classes:
            raise ValueError("a range table needs at least one class")

    method = property(lambda self: self._method)
    base_edition = property(lambda self: self._edition)
    classes = property(lambda self: self._classes)

    def __eq__(self, other):
        if not isinstance(other, RangeTable):
            return NotImplemented
        key = lambda c: (c.lo, c.hi, c.label)  # noqa: E731 - el orden de las clases no importa
        return (self._method, self._edition, sorted(self._classes, key=key)) == (
            other._method, other._edition, sorted(other._classes, key=key))

    def lookup(self, value: float) -> RangeClass:
        if math.isnan(value):
            raise ValueError("value must not be NaN")
        hits = [c for c in self._classes if c.lo <= value <= c.hi]
        if not hits:
            raise ValueError(f"value {value:g} is outside every class of the table")
        return min(hits, key=lambda c: c.lo)

    def near_boundary(self, value: float) -> tuple[str, str] | None:
        """Etiquetas (inferior, superior) del borde común más cercano si `value` está dentro de la tolerancia de P6."""
        kind, tol = NEAR_BOUNDARY[self._method]
        if kind == "factor":
            if not value > 0:
                return None
            tol = math.log10(tol)
        cs = sorted(self._classes, key=lambda c: c.lo)
        best = None
        for a, b in zip(cs, cs[1:]):
            if not math.isclose(a.hi, b.lo, rel_tol=1e-9, abs_tol=1e-12):  # un hueco o solape no es un borde
                continue
            d = abs(math.log10(value / b.lo)) if kind == "factor" else abs(value - b.lo)
            if d <= tol + _NEAR_EPS and (best is None or d < best[0]):
                best = (d, a.label, b.label)
        return None if best is None else (best[1], best[2])

    def validate(self, catalog: SupportCatalog | None = None) -> list[TableIssue]:
        ed = self._edition
        out: list[TableIssue] = []
        by_lo = sorted(self._classes, key=lambda c: c.lo)
        dmin, dmax = RANGE_METHODS[self._method][1]
        cursor = dmin
        for c in by_lo:
            if c.lo > cursor:
                out.append(TableIssue("gap", f"{ed} domain {dmin:g}-{dmax:g} not covered between {cursor:g} and {c.lo:g}", ed))
            cursor = max(cursor, c.hi)
        if cursor < dmax:
            out.append(TableIssue("gap", f"{ed} domain {dmin:g}-{dmax:g} not covered between {cursor:g} and {dmax:g}", ed))
        for i, a in enumerate(by_lo):
            for b in by_lo[i + 1:]:
                if b.lo < a.hi:
                    out.append(TableIssue("overlap", f"{ed} classes '{a.label}' and '{b.label}' overlap between {b.lo:g} and {min(a.hi, b.hi):g}", ed))
        for c in by_lo:
            if c.support is None:
                out.append(TableIssue("no_support", f"class '{c.label}' has no support", ed))
            elif catalog is not None and c.support not in catalog:
                out.append(TableIssue("unknown_support", f"class '{c.label}' uses support '{c.support}', which is not in the catalog", ed))
        if catalog is not None:
            known = [(c, catalog.get(c.support).order) for c in by_lo if c.support is not None and c.support in catalog]
            for (worse, w), (better, b) in zip(known, known[1:]):
                if better.lo > worse.lo and b > w:
                    out.append(TableIssue("not_monotonic", f"better class '{better.label}' needs heavier support '{better.support}' than worse class '{worse.label}' ('{worse.support}')", ed))
        edges = [e for c in self._classes for e in (c.lo, c.hi)]
        for x in EDITION_BOUNDARIES.get(ed, ()):
            if not any(math.isclose(x, e, rel_tol=1e-9, abs_tol=1e-12) for e in edges):
                out.append(TableIssue("edition_boundary", f"boundary {x:g} of {ed} classes is not a class boundary", ed))
        return out
