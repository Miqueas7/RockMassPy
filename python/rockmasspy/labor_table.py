"""Tabla por labor: catálogo + tabla de clases + luz a la que aplica, y selección por labor y luz.

Clasificar nunca lanza por un sostenimiento ausente del catálogo (devuelve support=None y un aviso);
solo lanza ValueError si los argumentos no corresponden al tipo de tabla.
"""

import datetime
import math
import re
from collections.abc import Iterable
from dataclasses import dataclass

from .cell_table import CellTable
from .intact_rock import _strip
from .issues import TableIssue
from .range_table import RangeTable
from .rating_table import RatingTable
from .support import SupportCatalog, SupportType


@dataclass(frozen=True)
class Classification:
    label: str
    support: SupportType | None
    base_edition: str
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class LaborTable:
    labor_type: str
    catalog: SupportCatalog
    table: RangeTable | CellTable
    span_m: tuple[float, float] | None = None
    correlations: tuple = ()  # tuple[rm.CustomCorrelation, ...]
    author: str = ""
    date: str = ""
    notes: str = ""
    rating: RatingTable | None = None  # puntajes propios; None = los de la edición base

    def __post_init__(self):
        if self.span_m is not None:
            lo, hi = self.span_m
            if not (math.isfinite(lo) and math.isfinite(hi) and 0 < lo < hi):
                raise ValueError(f"span_m: must satisfy 0 < lo < hi, got {self.span_m!r}")
            object.__setattr__(self, "span_m", (lo, hi))
        if self.date:
            try:  # la forma exacta y además una fecha que exista (rechaza 2026-13-45)
                ok = re.fullmatch(r"\d{4}-\d{2}-\d{2}", self.date) and datetime.date.fromisoformat(self.date)
            except ValueError:
                ok = False
            if not ok:
                raise ValueError(f"date: expected yyyy-mm-dd, got {self.date!r}")
        object.__setattr__(self, "correlations", tuple(self.correlations))

    def classify(self, value: float | None = None, *, structure: str | None = None,
                 condition: str | None = None) -> Classification:
        if isinstance(self.table, RangeTable):
            if value is None or structure is not None or condition is not None:
                raise ValueError("a range table is classified with 'value' only")
            c = self.table.lookup(value)
            label = c.label
            near = self.table.near_boundary(value)
        else:
            if value is not None or structure is None or condition is None:
                raise ValueError("a cells table is classified with 'structure' and 'condition' only")
            c = self.table.lookup(structure, condition)
            label = c.label or c.cell
        warnings: list[str] = []
        support = None
        if isinstance(self.table, RangeTable) and near is not None:
            warnings.append(f"near the boundary between classes {near[0]} and {near[1]}")
        if c.support is not None and c.support in self.catalog:  # las clases ya guardan el código limpio
            support = self.catalog.get(c.support)
        else:
            warnings.append(f"class {label} has no support type in the catalog")
        return Classification(label, support, self.table.base_edition, tuple(warnings))

    def validate(self) -> list[TableIssue]:
        issues = self.catalog.validate() + self.table.validate(self.catalog)
        return issues + (self.rating.validate() if self.rating is not None else [])


def _key(labor_type: str) -> str:
    return _strip(labor_type).strip().lower()  # «galeria» encuentra «galería»


def select_table(tables: Iterable[LaborTable], labor_type: str, span_m: float) -> LaborTable:
    want = _key(labor_type)
    tables = list(tables)
    hits = [t for t in tables
            if _key(t.labor_type) == want and (t.span_m is None or t.span_m[0] <= span_m <= t.span_m[1])]
    if len(hits) == 1:
        return hits[0]
    if len(hits) == 2 and all(t.span_m is not None for t in hits):
        a, b = sorted(hits, key=lambda t: t.span_m[0])
        if a.span_m[1] == b.span_m[0] == span_m:  # solo se tocan en el límite: la de luces mayores (menos favorable)
            return b
    cands = [(t.labor_type, t.span_m) for t in tables]
    problem = "no table" if not hits else "more than one table"
    raise ValueError(f"{problem} for labor_type {labor_type!r} and span {span_m:g} m; candidates: {cands}")
