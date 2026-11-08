"""Clasificación en lote de tramos: elige la tabla de cada tramo, clasifica, resume y guarda los resultados.

Un tramo que no se puede clasificar nunca detiene el lote: queda sin clase y con un aviso. Los avisos
no llevan valores de columnas de identificación (solo códigos de sostenimiento, ediciones y mensajes de las tablas).
"""

from collections import Counter
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Union

from . import _rockmasspy_core as rm
from .cell_table import CellTable
from .csv_io import _celda, _system_csv_format
from .q_chart_data import ESR_TABLES, Q_CHARTS
from .q_support import QSupportResult, recommend_q_support
from .excel_io import _where
from .labor_table import LaborTable, _key, select_table
from .probabilistic import Distribution, sample_model
from .range_table import RangeTable
from .support import SupportType
from .table_io import _optional
from .tramos import Tramo

_Q_EDITIONS = {"Q-NGI-2015": rm.QEdition.NGI2015, "Q-NGI-2025": rm.QEdition.NGI2025}
_COLUMNS = ("id_tramo", "tipo_labor", "luz_m", "tabla_luz_min_m", "tabla_luz_max_m", "metodo", "edicion_base",
            "valor_entrada", "celda", "clase", "sostenimiento", "sostenimiento_orden", "sost_instalado", "avisos")
_Q_COLUMNS = ("q_carta_edicion", "q_carta_esr", "q_carta_de_m", "q_carta_categoria", "q_carta_shotcrete_min_mm",
              "q_carta_shotcrete_max_mm", "q_carta_espaciamiento_min_m", "q_carta_espaciamiento_max_m",
              "q_carta_longitud_min_m", "q_carta_longitud_max_m", "q_carta_rrs", "q_carta_avisos")
_P_COLUMNS = ("clase_probable", "prob_clase_probable", "prob_clase", "probabilidades", "n_validas")
_Q_PARAMS = ("rqd_pct", "jn", "jr", "ja", "jw", "srf")
TRAMO_DISTRIBUTION_VARIABLES = ("rmr_valor", "gsi_valor", "q_valor") + _Q_PARAMS
_METHOD_VARIABLES = {"RMR": {"rmr_valor"}, "GSI": {"gsi_valor"}, "Q": {"q_valor", *_Q_PARAMS}}
TRAMO_DISTRIBUTION_COLUMNS = ("id_tramo", "variable", "distribucion", "media", "desviacion", "minimo", "maximo")
DISTRIBUTIONS_SHEET = "Distribuciones"
TRAMOS_SHEET = "Tramos"
EsrSpec = Union[str, tuple[str, float]]  # "C" o ("A", 4.0)


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
    q_chart: QSupportResult | None = None  # referencia de la carta Q (solo techo); no altera la clasificación propia
    q_chart_warnings: tuple[str, ...] = ()
    probabilities: dict[str, float] | None = None  # clase de la tabla -> fracción de las muestras (solo con distribuciones)
    n_valid: int | None = None


@dataclass(frozen=True)
class TramoDistributionRow:
    id_tramo: str = field(repr=False)
    variable: str
    distribucion: str
    media: float | None
    desviacion: float | None
    minimo: float
    maximo: float
    fila: int
    hoja: str = field(default=DISTRIBUTIONS_SHEET, repr=False, compare=False)

    @property
    def distribution(self) -> Distribution:
        from .blocks import _KINDS

        return Distribution(_KINDS[self.distribucion], self.minimo, self.maximo, self.media, self.desviacion)


def _tramo_distribution(vals, n, sheet):
    from .blocks import _check_distribution

    # sin rango propio: el dominio lo decide el núcleo al muestrear (error que nombra la variable)
    _check_distribution(vals, n, sheet, "id_tramo", TRAMO_DISTRIBUTION_VARIABLES, {})
    return TramoDistributionRow(**vals, fila=n, hoja=sheet)


def load_tramo_distributions(path, *, sheet: str = DISTRIBUTIONS_SHEET,
                             column_map: Mapping[str, str] | None = None) -> list[TramoDistributionRow]:
    """Lee `Distribuciones` por `id_tramo` (una variable aleatoria por fila); un par (id_tramo, variable) no se repite."""
    from .blocks import load_distribution_rows

    return load_distribution_rows(path, sheet, column_map, "id_tramo", TRAMO_DISTRIBUTION_COLUMNS, _tramo_distribution)


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


def _tramo_q(t: Tramo, edition: str | None, warns: list[str]):
    """Valor Q del tramo: el dado o el calculado desde sus parámetros (en su edición, o en `edition`). Nunca por correlación."""
    if t.q_edicion == "Q-1974":
        warns.append("Q-1974 not supported; value used as given")
    if t.q_valor is not None:
        return t.q_valor
    params = (t.rqd_pct, t.jn, t.jr, t.ja, t.jw, t.srf)
    if t.q_edicion == "Q-1974" or any(p is None for p in params):
        return None
    ed = _Q_EDITIONS.get(t.q_edicion) or _Q_EDITIONS.get(edition) or rm.QEdition.NGI2025
    r = rm.q_value(rm.QInput(*params), ed)
    warns.extend(r.warnings)
    return r.q


def _q_input(t: Tramo, table: RangeTable, warns: list[str]):
    return _tramo_q(t, table.base_edition, warns)


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


def _check_distributions(tramos: list[Tramo], distributions, sheet: str = TRAMOS_SHEET) -> dict[str, list[TramoDistributionRow]]:
    """Cruza `Distribuciones` con `Tramos` antes de muestrear: los errores nombran hoja, fila y columna, nunca el id."""
    by_id = {t.id_tramo: t for t in tramos}
    per: dict[str, list[TramoDistributionRow]] = {}
    for d in distributions:
        d = _tramo_distribution({c: getattr(d, c) for c in TRAMO_DISTRIBUTION_COLUMNS}, d.fila, d.hoja)
        t = by_id.get(d.id_tramo)
        if t is None:
            raise ValueError(f"{_where(d.hoja, d.fila, 'id_tramo')}: no tramo with this id_tramo")
        if d.variable in _Q_PARAMS and t.q_valor is not None:
            raise ValueError(f"{_where(d.hoja, d.fila, 'variable')}: {d.variable} cannot be sampled when q_valor is given")
        if getattr(t, d.variable) is None:  # sin el valor, el resultado determinístico correría otro modelo
            raise ValueError(f"{_where(sheet, t.fila, d.variable)}: required because it is sampled in {d.hoja}")
        per.setdefault(d.id_tramo, []).append(d)
    return per


def _int_arg(v, name, lo):
    if isinstance(v, bool) or not isinstance(v, int) or v < lo:
        raise ValueError(f"{name} must be an integer >= {lo}")


def _with_probabilities(r: TramoResult, lt: LaborTable, rows, iterations, sampling, seed, sheet=TRAMOS_SHEET) -> TramoResult:
    t, tab = r.tramo, lt.table
    for d in rows:
        if d.variable not in _METHOD_VARIABLES.get(r.method, ()):
            raise ValueError(f"{_where(d.hoja, d.fila, 'variable')}: not used by method {r.method}")
    counts: Counter = Counter()

    def one(draw):
        if tab.method == "Q":
            v = draw["q_valor"] if "q_valor" in draw else _tramo_q(replace(t, **draw), tab.base_edition, [])
        else:
            v = draw["rmr_valor" if tab.method == "RMR" else "gsi_valor"]
        try:
            counts[lt.classify(v).label] += 1
        except ValueError:
            raise ValueError("a sampled result falls outside every class of the table; "
                             "widen the table or narrow the variables") from None
        return {"value": v}, []

    try:
        ms = sample_model(one, {d.variable: d.distribution for d in rows}, n=iterations, sampling=sampling, seed=seed)
    except ValueError as e:
        raise ValueError(f"sheet '{sheet}', row {t.fila}: {e}") from None
    k = ms.n_valid
    labels = dict.fromkeys(c.label for c in sorted(tab.classes, key=lambda c: c.lo))  # empate: gana la de menor lo
    return replace(r, probabilities={lb: counts[lb] / k for lb in labels}, n_valid=k)


def classify_tramos(tramos: Iterable[Tramo], tables: Iterable[LaborTable], *,
                    distributions: Iterable[TramoDistributionRow] | None = None, iterations: int = 2000,
                    sampling: str = "lhs", seed: int = 1, tramos_sheet: str = TRAMOS_SHEET) -> list[TramoResult]:
    """Clasifica cada tramo. Con `distributions` agrega, a los tramos que las tienen, la probabilidad de cada clase de su
    tabla (Monte Carlo o LHS sobre la clasificación de cada muestra); la clase determinística no cambia."""
    tables, tramos = list(tables), list(tramos)
    if not tables:
        raise ValueError("tables: at least one labor table is required")
    per: dict[str, list[TramoDistributionRow]] = {}
    if distributions is not None:
        _int_arg(iterations, "iterations", 1)
        _int_arg(seed, "seed", 0)
        if sampling not in ("lhs", "monte_carlo"):
            raise ValueError("sampling must be 'lhs' or 'monte_carlo'")
        per = _check_distributions(tramos, distributions, tramos_sheet)
    out = []
    for t in tramos:
        try:
            lt = _pick_table(tables, t)
        except ValueError as e:
            out.append(TramoResult(tramo=t, warnings=(f"no table for this labor/span: {e}",)))
            continue
        r = _classify(t, lt)
        if t.id_tramo in per and r.label is not None:
            r = _with_probabilities(r, lt, per[t.id_tramo], iterations, sampling, seed, tramos_sheet)
        out.append(r)
    return out


def summarize(results: Iterable[TramoResult]) -> BatchSummary:
    results = list(results)
    done = [r for r in results if r.label is not None]
    return BatchSummary(
        total=len(results), classified=len(done), unclassified=len(results) - len(done),
        by_labor_class=dict(Counter((r.labor_type, r.label) for r in done)),
        by_support=dict(Counter(r.support.code for r in done if r.support is not None)),
        warnings_count=sum(len(r.warnings) for r in results))


def _percent_text(probs: dict[str, float]) -> str:
    """`III 59 %; IV 41 %`: de mayor a menor, enteros que suman 100 (resto repartido por mayor fracción)."""
    items = [(lb, p) for lb, p in probs.items() if p >= 0.005]
    tiny = [lb for lb, p in probs.items() if 0 < p < 0.005]
    pct = {lb: int(p * 100 + 1e-9) for lb, p in items}
    for lb, _ in sorted(items, key=lambda x: x[1] * 100 - pct[x[0]], reverse=True)[:100 - sum(pct.values())]:
        pct[lb] += 1
    return "; ".join([f"{lb} {pct[lb]} %" for lb, _ in sorted(items, key=lambda x: -x[1])] + [f"{lb} <1 %" for lb in tiny])


def _fila_p(r: TramoResult):
    if r.probabilities is None:
        return [None] * 5
    top, p = max(r.probabilities.items(), key=lambda x: x[1])
    return [top, p, r.probabilities.get(r.label), _percent_text(r.probabilities), r.n_valid]


def _fila(r: TramoResult, with_q: bool = False, with_p: bool = False):
    t, s = r.tramo, r.span_m
    fila = [t.id_tramo, t.tipo_labor, t.luz_m, s[0] if s else None, s[1] if s else None, r.method, r.base_edition,
            r.input_value, r.input_cell, r.label, r.support.code if r.support else None, r.support_order,
            t.sost_instalado, " | ".join(r.warnings)]
    if with_q:
        fila += _fila_q(r)
    if with_p:
        fila += _fila_p(r)
    return fila


def _fila_q(r: TramoResult):
    c = r.q_chart
    avisos = " | ".join(r.q_chart_warnings)
    if c is None:
        return [None] * 11 + [avisos]
    rd = c.roof
    # Con Sfr en las categorías 3 a 8; sin Sfr en la 1 y la 2.
    sp = rd.bolt_spacing_without_sfr_m if rd.category <= 2 else rd.bolt_spacing_with_sfr_m
    sh, ln = rd.shotcrete_mm, rd.bolt_length_chart_m
    return [c.edition, c.esr_used, rd.de_m, rd.category, sh[0] if sh else None, sh[1] if sh else None,
            sp[0] if sp else None, sp[1] if sp else None, ln[0] if ln else None, ln[1] if ln else None, rd.rrs, avisos]


def _columns(results: Iterable[TramoResult]) -> tuple[str, ...]:
    return _COLUMNS + _Q_COLUMNS if any(r.q_chart or r.q_chart_warnings for r in results) else _COLUMNS


def parse_esr_spec(value: str) -> EsrSpec:
    """`C` -> "C"; `A:4` -> ("A", 4.0). La categoría se valida después, en `_validar_esr`."""
    cat, colon, num = str(value).strip().partition(":")
    if not cat.strip() or (colon and not num.strip()):
        raise ValueError(f"invalid ESR {value!r}: expected C or A:4")
    cat = cat.strip().upper()
    if not colon:
        return cat
    try:
        return (cat, float(num))
    except ValueError:
        raise ValueError(f"invalid ESR {value!r}: expected C or A:4") from None


def _validar_esr(spec, edition: str) -> tuple[str, float | None]:
    cat, esr = spec if isinstance(spec, tuple) else (spec, None)
    cat = str(cat).upper()
    if cat not in ESR_TABLES[edition]:
        raise ValueError(f"esr_category must be one of A-G, got {cat!r}")
    lo, hi, _ = ESR_TABLES[edition][cat]
    if esr is None and lo != hi:
        raise ValueError(f"ESR category {cat} covers {lo:g}-{hi:g}; pass (category, esr)")
    if esr is not None and not (isinstance(esr, (int, float)) and math.isfinite(esr) and esr > 0):
        raise ValueError(f"esr must be finite and > 0, got {esr!r}")
    return cat, esr


def add_q_chart_reference(results: Iterable[TramoResult], esr: "EsrSpec | Mapping[str, EsrSpec]", *,
                          edition: str = "Q-NGI-2025") -> list[TramoResult]:
    """Agrega la referencia de la carta Q (solo techo, solo con el Q del tramo) sin tocar la clasificación propia."""
    if edition not in Q_CHARTS:
        raise ValueError(f"unknown edition {edition!r}; available: {sorted(Q_CHARTS)}")
    mapa = esr if isinstance(esr, Mapping) else {"*": esr}
    specs = {(k if k == "*" else _key(k)): _validar_esr(v, edition) for k, v in mapa.items()}
    out = []
    for r in results:
        t = r.tramo
        spec = specs.get(_key(t.tipo_labor), specs.get("*"))
        out.append(_con_carta(r, spec, edition))
    return out


def _con_carta(r: TramoResult, spec, edition: str) -> TramoResult:
    t = r.tramo
    if spec is None:
        return replace(r, q_chart_warnings=("no ESR for this labor",))
    if t.luz_m is None:
        return replace(r, q_chart_warnings=("missing span (luz_m)",))
    if t.q_edicion == "Q-1974":
        return replace(r, q_chart_warnings=("Q-1974 not supported",))
    if t.q_edicion is not None and t.q_edicion != edition:
        return replace(r, q_chart_warnings=(f"Q edition {t.q_edicion} differs from chart edition {edition}",))
    qw: list[str] = []  # avisos del Q calculado; con tabla de Q ya están en r.warnings
    try:
        q = _tramo_q(t, edition, qw if r.method != "Q" else [])
        if q is None:
            return replace(r, q_chart_warnings=("missing Q",))
        c = recommend_q_support(q, t.luz_m, esr_category=spec[0], esr=spec[1], edition=edition)
    except ValueError as e:  # solo nombres y números; nunca columnas de identificación
        return replace(r, q_chart_warnings=tuple(dict.fromkeys((*qw, str(e)))))
    # los avisos del Q calculado van primero (los del Q-1974 ya se descartaron arriba)
    return replace(r, q_chart=c, q_chart_warnings=tuple(dict.fromkeys((*qw, *c.warnings))))


def q_chart_crosstab(results: Iterable[TramoResult]) -> dict[tuple[str, int], int]:
    """Cuenta (código de sostenimiento propio o 'unclassified', categoría Q) de los tramos con referencia."""
    return dict(Counter((r.support.code if r.support else "unclassified", r.q_chart.roof.category)
                        for r in results if r.q_chart))


def write_table(path, columns: Sequence[str], rows: Sequence[Sequence], *, sheet: str = "Resultados") -> Path:
    """Escribe una tabla en .xlsx (con [io]) o .csv (en el formato numérico de este computador)."""
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".xlsx":
        openpyxl = _optional("openpyxl")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = sheet
        ws.append(list(columns))
        for c in ws[1]:
            c.font = _optional("openpyxl.styles").Font(bold=True)
        for f in rows:
            ws.append(list(f))
        wb.save(p)
    elif ext == ".csv":
        import csv

        sep, dec = _system_csv_format()
        with open(p, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh, delimiter=sep)
            w.writerow(columns)
            for f in rows:
                w.writerow([_celda(v, dec) for v in f])
    else:
        raise ValueError(f"path: expected a .xlsx or .csv file, got {p.suffix!r}")
    return p


def save_results(results: Iterable[TramoResult], path) -> Path:
    """Escribe .xlsx (con [io]) o .csv (en el formato numérico de este computador). Solo lleva id_tramo como identificador."""
    results = list(results)
    cols = _columns(results)
    with_q, with_p = len(cols) > len(_COLUMNS), any(r.probabilities is not None for r in results)
    return write_table(path, cols + (_P_COLUMNS if with_p else ()), [_fila(r, with_q, with_p) for r in results])
