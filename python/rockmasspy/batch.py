"""Clasificación en lote de tramos: elige la tabla de cada tramo, clasifica, resume y guarda los resultados.

Un tramo que no se puede clasificar nunca detiene el lote: queda sin clase y con un aviso. Los avisos
no llevan valores de columnas de identificación (solo códigos de sostenimiento, ediciones y mensajes de las tablas).
"""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from . import _rockmasspy_core as rm
from .cell_table import CellTable
from .csv_io import _celda, _system_csv_format
from .labor_table import LaborTable, _key, select_table
from .range_table import RangeTable
from .support import SupportType
from .table_io import _optional
from .tramos import Tramo

_Q_EDITIONS = {"Q-NGI-2015": rm.QEdition.NGI2015, "Q-NGI-2025": rm.QEdition.NGI2025}
_COLUMNS = ("id_tramo", "tipo_labor", "luz_m", "tabla_luz_min_m", "tabla_luz_max_m", "metodo", "edicion_base",
            "valor_entrada", "celda", "clase", "sostenimiento", "sostenimiento_orden", "sost_instalado", "avisos")


@dataclass(frozen=True)
class TramoResult:
    tramo: Tramo
    labor_type: str | None = None
    span_m: tuple[float, float] | None = None
    method: str | None = None
    base_edition: str | None = None
    input_value: float | None = None
    input_cell: str | None = None
    label: str | None = None
    support: SupportType | None = None
    warnings: tuple[str, ...] = ()
    support_order: int | None = None  # posición (1 = primero) del sostenimiento en el catálogo de la tabla


@dataclass(frozen=True)
class BatchSummary:
    total: int
    classified: int
    unclassified: int
    by_labor_class: dict[tuple[str, str], int]
    by_support: dict[str, int]
    warnings_count: int


def _pick_table(tables: list[LaborTable], t: Tramo) -> LaborTable:
    if t.luz_m is not None:
        return select_table(tables, t.tipo_labor, t.luz_m)
    hits = [x for x in tables if _key(x.labor_type) == _key(t.tipo_labor) and x.span_m is None]
    if len(hits) != 1:
        problem = "more than one table" if hits else "no table"
        raise ValueError(f"{problem} without a span for labor_type {t.tipo_labor!r} (the tramo has no span)")
    return hits[0]


def _q_input(t: Tramo, table: RangeTable, warns: list[str]):
    """Valor Q del tramo: el dado o el calculado desde sus parámetros."""
    if t.q_edicion == "Q-1974":
        warns.append("Q-1974 not supported; value used as given")
    if t.q_valor is not None:
        return t.q_valor
    params = (t.rqd_pct, t.jn, t.jr, t.ja, t.jw, t.srf)
    if t.q_edicion == "Q-1974" or any(p is None for p in params):
        return None
    ed = _Q_EDITIONS.get(t.q_edicion) or _Q_EDITIONS.get(table.base_edition) or rm.QEdition.NGI2025
    r = rm.q_value(rm.QInput(*params), ed)
    warns.extend(r.warnings)
    return r.q


def _classify(t: Tramo, lt: LaborTable) -> TramoResult:
    tab = lt.table
    warns: list[str] = []
    base = dict(tramo=t, labor_type=lt.labor_type, span_m=lt.span_m, base_edition=tab.base_edition)
    value = cell = structure = condition = None
    if isinstance(tab, CellTable):
        method, cell = "GSI-cells", t.gsi_celda
    else:
        method = tab.method
        if method == "RMR":
            value = t.rmr_valor
            if t.rmr_edicion and t.rmr_edicion != tab.base_edition:
                warns.append(f"RMR edition {t.rmr_edicion} differs from table edition {tab.base_edition}")
        elif method == "Q":
            try:
                value = _q_input(t, tab, warns)
            except ValueError as e:  # parámetros Q fuera de dominio: solo nombres y números
                return TramoResult(**{**base, "method": method}, warnings=tuple(warns + [str(e)]))
        else:
            value = t.gsi_valor
    base.update(method=method, input_value=value, input_cell=cell)
    if value is None and cell is None:
        return TramoResult(**base, warnings=tuple(warns + [f"missing input for {method}"]))
    try:
        if cell is not None:
            structure, condition = cell.split("/")  # tramos.py ya la normalizó a S/C
        c = lt.classify(value, structure=structure, condition=condition)
    except ValueError as e:
        return TramoResult(**base, warnings=tuple(warns + [str(e)]))
    warns.extend(c.warnings)
    order = None
    if c.support is not None:
        order = [s.code for s in lt.catalog.ordered()].index(c.support.code) + 1
        if t.sost_instalado and t.sost_instalado != c.support.code:
            warns.append(f"installed support {t.sost_instalado} differs from recommended {c.support.code}")
    return TramoResult(**base, label=c.label, support=c.support, warnings=tuple(warns), support_order=order)


def classify_tramos(tramos: Iterable[Tramo], tables: Iterable[LaborTable]) -> list[TramoResult]:
    tables = list(tables)
    if not tables:
        raise ValueError("tables: at least one labor table is required")
    out = []
    for t in tramos:
        try:
            lt = _pick_table(tables, t)
        except ValueError as e:
            out.append(TramoResult(tramo=t, warnings=(f"no table for this labor/span: {e}",)))
            continue
        out.append(_classify(t, lt))
    return out


def summarize(results: Iterable[TramoResult]) -> BatchSummary:
    results = list(results)
    done = [r for r in results if r.label is not None]
    return BatchSummary(
        total=len(results), classified=len(done), unclassified=len(results) - len(done),
        by_labor_class=dict(Counter((r.labor_type, r.label) for r in done)),
        by_support=dict(Counter(r.support.code for r in done if r.support is not None)),
        warnings_count=sum(len(r.warnings) for r in results))


def _fila(r: TramoResult):
    t, s = r.tramo, r.span_m
    return [t.id_tramo, t.tipo_labor, t.luz_m, s[0] if s else None, s[1] if s else None, r.method, r.base_edition,
            r.input_value, r.input_cell, r.label, r.support.code if r.support else None, r.support_order,
            t.sost_instalado, " | ".join(r.warnings)]


def save_results(results: Iterable[TramoResult], path) -> Path:
    """Escribe .xlsx (con [io]) o .csv (en el formato numérico de este computador). Solo lleva id_tramo como identificador."""
    p = Path(path)
    filas = [_fila(r) for r in results]
    ext = p.suffix.lower()
    if ext == ".xlsx":
        openpyxl = _optional("openpyxl")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Resultados"
        ws.append(list(_COLUMNS))
        for c in ws[1]:
            c.font = _optional("openpyxl.styles").Font(bold=True)
        for f in filas:
            ws.append(f)
        wb.save(p)
    elif ext == ".csv":
        import csv

        sep, dec = _system_csv_format()
        with open(p, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh, delimiter=sep)
            w.writerow(_COLUMNS)
            for f in filas:
                w.writerow([_celda(v, dec) for v in f])
    else:
        raise ValueError(f"path: expected a .xlsx or .csv file, got {p.suffix!r}")
    return p
