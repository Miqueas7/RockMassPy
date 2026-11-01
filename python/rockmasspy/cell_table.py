"""Tabla de sostenimiento por celda de una cartilla GSI (estructura / condición superficial).

Validar avisa con TableIssue y nunca bloquea. Solo los datos imposibles (celda repetida, código
inexistente, gsi_range inválido, consulta a una celda que no aplica o no está definida) lanzan
ValueError.
"""

import math
from collections.abc import Iterable
from dataclasses import dataclass

from .gsi_charts import GsiChart, normalize_cell
from .issues import TableIssue
from .support import SupportCatalog


@dataclass(frozen=True)
class CellClass:
    cell: str
    support: str | None = None
    gsi_range: tuple[float, float] | None = None
    label: str = ""

    def __post_init__(self):
        object.__setattr__(self, "cell", normalize_cell(self.cell))
        if self.support is not None:  # un código numérico de YAML (support: 3) pasa a texto
            object.__setattr__(self, "support", str(self.support).strip() or None)
        object.__setattr__(self, "label", (self.label or "").strip())
        if self.gsi_range is not None:
            lo, hi = self.gsi_range
            if not (math.isfinite(lo) and math.isfinite(hi) and 0 <= lo < hi <= 100):
                raise ValueError(f"gsi_range must satisfy 0 <= lo < hi <= 100, got {self.gsi_range!r}")


class CellTable:
    def __init__(self, chart: GsiChart, cells: Iterable[CellClass]):
        self._chart = chart
        self._cells = tuple(cells)
        structs = [s for s, _ in chart.structures]
        conds = [c for c, _ in chart.conditions]
        seen: set[str] = set()
        for c in self._cells:
            s, k = c.cell.split("/")
            if s not in structs:
                raise ValueError(f"unknown structure {s!r} in cell {c.cell}; valid structures: {structs}, conditions: {conds}")
            if k not in conds:
                raise ValueError(f"unknown condition {k!r} in cell {c.cell}; valid structures: {structs}, conditions: {conds}")
            if c.cell in seen:
                raise ValueError(f"cell {c.cell} is defined twice")
            seen.add(c.cell)
        self._by_cell = {c.cell: c for c in self._cells}

    chart = property(lambda self: self._chart)
    base_edition = property(lambda self: self._chart.chart_id)
    cells = property(lambda self: self._cells)

    def __eq__(self, other):
        if not isinstance(other, CellTable):
            return NotImplemented
        key = lambda c: c.cell  # noqa: E731 - el orden de las celdas no importa
        return self._chart == other._chart and sorted(self._cells, key=key) == sorted(other._cells, key=key)

    def lookup(self, structure: str, condition: str) -> CellClass:
        code = normalize_cell(f"{structure}/{condition}")
        if code not in self._chart.valid_cells:
            raise ValueError(f"cell {code} is not applicable in {self._chart.chart_id}")
        if code not in self._by_cell:
            raise ValueError(f"cell {code} is not defined in the table")
        return self._by_cell[code]

    def validate(self, catalog: SupportCatalog | None = None) -> list[TableIssue]:
        ed = self._chart.chart_id
        out: list[TableIssue] = []
        for code in sorted(self._chart.valid_cells - self._by_cell.keys()):
            out.append(TableIssue("missing_cell", f"cell {code} of {ed} has no class", ed))
        for c in self._cells:
            if c.cell not in self._chart.valid_cells:
                out.append(TableIssue("invalid_cell", f"cell {c.cell} is not applicable in {ed}", ed))
            if c.support is None:
                out.append(TableIssue("no_support", f"cell {c.cell} has no support", ed))
            elif catalog is not None and c.support not in catalog:
                out.append(TableIssue("unknown_support", f"cell {c.cell} uses support '{c.support}', which is not in the catalog", ed))
        if catalog is not None:
            structs = [s for s, _ in self._chart.structures]
            conds = [k for k, _ in self._chart.conditions]

            def order(code):
                c = self._by_cell.get(code)
                return catalog.get(c.support).order if c and c.support is not None and c.support in catalog else None

            for i, s in enumerate(structs):
                for j, k in enumerate(conds):
                    here = f"{s}/{k}"
                    neighbours = []
                    if j + 1 < len(conds):
                        neighbours.append(f"{s}/{conds[j + 1]}")
                    if i + 1 < len(structs):
                        neighbours.append(f"{structs[i + 1]}/{k}")
                    for n in neighbours:
                        a, b = order(here), order(n)
                        if a is not None and b is not None and b < a:
                            out.append(TableIssue("not_monotonic", f"worse cell {n} ('{self._by_cell[n].support}') needs lighter support than {here} ('{self._by_cell[here].support}')", ed))
        return out
