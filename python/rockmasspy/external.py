"""Resultados de programas externos (Slide2, RS2, FLAC3D...) en un registro largo, y la tabla RocData.

El lector no adivina formatos de programa: lee por alias de encabezado y por `column_map`. Una columna con el nombre
de una magnitud («Factor of Safety (-)») pasa de tabla ancha a filas largas; si el archivo ya trae `magnitud` y
`valor`, se lee tal cual. Las unidades se convierten a la canónica de QUANTITIES (MPa, m, MN, MN·m, %).
Los errores ubican hoja, fila y columna; nunca repiten valores ni ids.
"""

import math
import re
import unicodedata
from dataclasses import dataclass, field, replace
from pathlib import Path

from . import _rockmasspy_core as rm
from .csv_io import _CsvSource
from .excel_io import _num, _open, _text, _where
from .hb_consistency import HbConsistency, check_hoek_brown
from .limit_equilibrium import _METHOD_WORD, le_static_fs

# magnitud -> unidad canónica
QUANTITIES = {
    "fs": "-", "srf": "-", "pof_pct": "%", "strength_factor": "-", "sigma1_mpa": "MPa", "sigma3_mpa": "MPa",
    "u_total_m": "m", "ux_m": "m", "uy_m": "m", "uz_m": "m", "convergence_pct": "%", "convergence_m": "m",
    "yielded": "-", "axial_force_mn": "MN", "moment_mnm": "MN·m", "shear_mn": "MN",
}
OBJECT_KINDS = ("section", "point", "line", "node", "zone", "bolt", "liner", "tunnel")
_T = 0.00980665  # tonelada fuerza -> MN
# unidad (minúsculas) -> (unidad canónica de su dimensión, factor)
_UNITS = {
    "m": ("m", 1.0), "mm": ("m", 1e-3), "cm": ("m", 1e-2),
    "mpa": ("MPa", 1.0), "kpa": ("MPa", 1e-3), "pa": ("MPa", 1e-6),
    "mn": ("MN", 1.0), "kn": ("MN", 1e-3), "t": ("MN", _T),
    "mn·m": ("MN·m", 1.0), "mnm": ("MN·m", 1.0), "kn·m": ("MN·m", 1e-3), "knm": ("MN·m", 1e-3),
    "t·m": ("MN·m", _T), "tm": ("MN·m", _T),
    "%": ("%", 1.0), "-": ("-", 1.0),
}

_FIELDS = {  # alias (ya normalizado) -> campo
    "programa": "program", "program": "program", "version": "version", "modelo": "model", "model": "model",
    "escenario": "scenario", "scenario": "scenario", "etapa": "stage", "stage": "stage",
    "tipo objeto": "object_kind", "object": "object_kind", "object kind": "object_kind",
    "id": "object_id", "object id": "object_id", "x": "x", "y": "y", "z": "z",
    "distancia": "distance", "distance": "distance", "magnitud": "quantity", "quantity": "quantity",
    "metodo": "method", "method": "method", "valor": "value", "value": "value", "unidad": "unit", "unit": "unit",
    "kh": "kh", "escala": "scale", "scale": "scale", "consecuencia": "consequence", "consequence": "consequence",
}
_NUM_FIELDS = ("x", "y", "z", "distance", "kh")
_TEXT_FIELDS = ("program", "version", "model", "scenario", "stage", "object_id", "scale", "consequence")


def _norm(s) -> str:
    """Encabezado sin mayúsculas, tildes, unidades entre paréntesis, guiones bajos ni espacios dobles."""
    s = unicodedata.normalize("NFKD", _text(s) if s is not None else "")
    s = re.sub(r"\(.*?\)", "", "".join(c for c in s if not unicodedata.combining(c)))
    return re.sub(r"\s+", " ", s.replace("_", " ")).strip().lower()


_QTY = {_norm(q): q for q in QUANTITIES}
_QTY.update({
    "factor of safety": "fs", "safety factor": "fs", "critical srf": "srf", "total displacement": "u_total_m",
    "sigma 1": "sigma1_mpa", "sigma 3": "sigma3_mpa", "axial force": "axial_force_mn", "moment": "moment_mnm",
    "shear force": "shear_mn",
})


def _header_unit(h) -> str | None:
    m = re.search(r"\(([^()]*)\)\s*$", _text(h) if h is not None else "")
    return m.group(1).strip() if m else None


def _factor(unit, quantity, where):
    """Factor a la unidad canónica; una unidad desconocida o de otra dimensión es un error sin valores."""
    if unit is None or str(unit).strip() == "":
        return 1.0
    canon, f = _UNITS.get(str(unit).strip().lower(), (None, None))
    if canon is None:
        raise ValueError(f"{where}: unknown unit")
    if canon != QUANTITIES[quantity]:
        raise ValueError(f"{where}: unit is not compatible with the quantity")
    return f


def _rows(path, sheet):
    """(hoja, encabezados, filas, ¿coma decimal?) de un Excel o CSV; el libro se cierra antes de volver."""
    p = Path(path)
    src = _CsvSource({sheet or p.stem: p}) if p.suffix.lower() == ".csv" else _open(p)
    try:
        sheet = sheet or src.sheetnames[0]
        if sheet not in src.sheetnames:
            raise ValueError(src.missing(sheet))
        it = iter(src.rows(sheet))
        header = list(next(it, ()))
        return sheet, header, [list(r) for r in it], src.decimal_comma(sheet)
    finally:
        if hasattr(src, "wb"):
            src.wb.close()


def _blank(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def _number(v, sheet, n, col, dec):
    try:
        return _num(v, sheet, n, col, dec)
    except ValueError:  # _num cita la celda; aquí no se repite el valor
        raise ValueError(f"{_where(sheet, n, col)}: expected a number") from None


@dataclass(frozen=True)
class ExternalRecord:
    object_id: str
    quantity: str
    value: float
    unit: str | None = None
    program: str | None = None
    version: str | None = None
    model: str | None = None
    scenario: str | None = None
    stage: str | None = None
    object_kind: str | None = None
    x: float | None = None
    y: float | None = None
    z: float | None = None
    distance: float | None = None
    method: str | None = None
    kh: float | None = None
    scale: str | None = None
    consequence: str | None = None
    source_file: str | None = None
    row: int | None = None

    def __post_init__(self):
        if self.quantity == "srf":  # E1: un SRF siempre es método «ssr», venga de donde venga el registro
            object.__setattr__(self, "method", "ssr")


@dataclass(frozen=True)
class ExternalSet:
    records: tuple[ExternalRecord, ...]
    warnings: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def objects(self) -> dict[tuple[str, str, str], list[ExternalRecord]]:
        """Registros agrupados por (modelo, escenario, id); lo que falta cuenta como cadena vacía."""
        out: dict = {}
        for r in self.records:
            out.setdefault((r.model or "", r.scenario or "", r.object_id), []).append(r)
        return out


def load_external(path, *, sheet: str = "Resultados_externos", column_map: dict | None = None,
                  defaults: dict | None = None) -> ExternalSet:
    """Lee un Excel (hoja `sheet`) o un CSV en formato largo o ancho.

    column_map {encabezado: campo o magnitud} gana sobre los alias; defaults llena campos ausentes o vacíos.
    """
    sheet, header, rows, dec = _rows(path, sheet)
    cmap = {_norm(k): v for k, v in (column_map or {}).items()}
    fields, wide, ignored = {}, {}, False  # campo -> índice; (índice -> magnitud); ¿columnas sin reconocer?
    for i, h in enumerate(header):
        k = _norm(h)
        t = cmap.get(k) or _FIELDS.get(k) or _QTY.get(k)
        if t in QUANTITIES:
            wide[i] = t
        elif t in _FIELDS.values():
            fields[t] = i
        elif k:
            if t is not None:
                raise ValueError("column_map: unknown field or quantity")
            ignored = True
    name = lambda f: _text(header[fields[f]])  # noqa: E731
    d = dict(defaults or {})
    long = ("quantity" in fields or "quantity" in d) and ("value" in fields or "value" in d)
    if "object_id" not in fields and "object_id" not in d:
        raise ValueError(f"sheet '{sheet}': missing column 'id'")
    if not long and not wide:
        miss = "quantity" if "value" in fields else "value"
        raise ValueError(f"sheet '{sheet}': missing column '{miss}' or a recognized quantity column")
    if not long:
        for i, q in wide.items():  # unidad de un encabezado: se valida una vez, en la fila 1
            _factor(_header_unit(header[i]), q, _where(sheet, 1, _text(header[i])))

    src = Path(path).name
    out = []
    for n, raw in enumerate(rows, start=2):
        if all(_blank(v) for v in raw):
            continue
        cell = lambda f: (raw[fields[f]] if f in fields and fields[f] < len(raw) else None)  # noqa: E731
        vals = {f: (cell(f) if not _blank(cell(f)) else d.get(f)) for f in set(_FIELDS.values())}
        if _blank(vals["object_id"]):
            raise ValueError(f"{_where(sheet, n, name('object_id') if 'object_id' in fields else 'id')}: "
                             "required value is empty")
        common = {"source_file": src, "row": n, "object_id": _text(vals["object_id"])}
        for f in _TEXT_FIELDS:
            if f != "object_id" and not _blank(vals[f]):
                common[f] = _text(vals[f])
        for f in _NUM_FIELDS:
            if not _blank(vals[f]):
                common[f] = _number(vals[f], sheet, n, name(f) if f in fields else f, dec)
        if not _blank(vals["object_kind"]):
            k = _text(vals["object_kind"]).lower()
            if k not in OBJECT_KINDS:
                raise ValueError(f"{_where(sheet, n, name('object_kind') if 'object_kind' in fields else 'object')}: "
                                 "unknown object type")
            common["object_kind"] = k
        if not _blank(vals["method"]):
            common["method"] = _text(vals["method"]).lower()

        items = []  # (magnitud, valor crudo, unidad, columna)
        if long:
            col = name("quantity") if "quantity" in fields else "quantity"
            q = _QTY.get(_norm(vals["quantity"])) if not _blank(vals["quantity"]) else None
            if q is None:
                raise ValueError(f"{_where(sheet, n, col)}: unrecognized quantity")
            vcol = name("value") if "value" in fields else "value"
            if _blank(vals["value"]):
                raise ValueError(f"{_where(sheet, n, vcol)}: required value is empty")
            ucol = name("unit") if "unit" in fields else "unit"
            items.append((q, vals["value"], vals["unit"], vcol, ucol))
        else:
            for i, q in wide.items():
                if i < len(raw) and not _blank(raw[i]):
                    items.append((q, raw[i], _header_unit(header[i]), _text(header[i]), _text(header[i])))
        for q, v, unit, vcol, ucol in items:
            x = _number(v, sheet, n, vcol, dec) * _factor(unit, q, _where(sheet, n, ucol))
            if q == "yielded" and x not in (0.0, 1.0):
                raise ValueError(f"{_where(sheet, n, vcol)}: yielded must be 0 or 1")
            r = replace(ExternalRecord(common["object_id"], q, x, QUANTITIES[q]), **{
                k: w for k, w in common.items() if k != "object_id"})
            out.append(r)  # un srf ya sale con método «ssr» (__post_init__)
    notes = ("unrecognized columns ignored",) if ignored else ()
    return ExternalSet(tuple(out), (), notes)


# --- comparación de métodos (investigación §11.2 regla 5) ---

METHOD_SPREAD = 0.10  # provisional


@dataclass(frozen=True)
class MethodComparison:
    object_id: str = field(repr=False)
    values: dict  # método -> FS estático; los de RockMassPy con el prefijo «rockmasspy:»
    spread: float  # (máx − mín)/mín
    warning: str | None
    model: str = field(default="", repr=False)
    scenario: str = field(default="", repr=False)


def compare_methods(external, le_results=(), *, threshold: float = METHOD_SPREAD) -> list[MethodComparison]:
    """FS estático por método de cada (modelo, escenario, id) externo, más los de un análisis LE de RockMassPy con
    `id_analisis` igual al id. Un objeto con un solo método no se compara. Avisa si spread > threshold."""
    recs = external.records if isinstance(external, ExternalSet) else tuple(external)
    ours: dict = {}
    for r in le_results:
        names = ["sarma"] if r.sarma is not None else [_METHOD_WORD[x.method] for x in r.results]
        ours.setdefault(r.id_analisis, []).extend((f"rockmasspy:{m}", v) for m, v in zip(names, le_static_fs(r)))
    out = []
    for (model, scenario, oid), rows in sorted(ExternalSet(recs).objects().items()):
        pairs = [(r.method or "unspecified", r.value) for r in rows if r.quantity in ("fs", "srf") and not r.kh]
        vals: dict = {}
        for m, v in pairs + ours.get(oid, []):
            if v is not None and math.isfinite(v):
                vals[m] = min(v, vals.get(m, v))  # el mismo método dos veces: el menor
        if len(vals) < 2:
            continue
        lo, hi = min(vals.values()), max(vals.values())
        spread = (hi - lo) / lo if lo > 0 else math.inf
        warning = f"methods differ by more than {threshold * 100:g} %" if spread > threshold else None
        out.append(MethodComparison(oid, vals, spread, warning, model, scenario))
    return out


# --- tabla ancha de RocData / tesis ---

@dataclass(frozen=True)
class HbRow:
    material: str
    gsi: float
    mi: float
    d: float = 0.0
    sigma_ci_mpa: float | None = None
    mb: float | None = None
    s: float | None = None
    a: float | None = None
    erm_mpa: float | None = None
    ei_mpa: float | None = None
    nu: float | None = None
    gamma: float | None = None  # MN/m³


_HB = {
    "material": "material", "lithology": "material", "litologia": "material", "ucs": "sigma_ci_mpa",
    "sigci": "sigma_ci_mpa", "sigma ci": "sigma_ci_mpa", "gsi": "gsi", "mi": "mi", "d": "d", "mb": "mb", "s": "s",
    "a": "a", "erm": "erm_mpa", "ei": "ei_mpa", "poisson's ratio": "nu", "nu": "nu", "unit weight": "gamma",
    "gamma": "gamma", "sigma ci mpa": "sigma_ci_mpa", "erm mpa": "erm_mpa", "ei mpa": "ei_mpa",
}
GAMMA_RANGE_MN_M3 = (0.010, 0.040)


def load_rocdata_table(path, *, sheet: str | None = None) -> list[HbRow]:
    """Lee la tabla ancha de parámetros Hoek-Brown (Excel o CSV); D ausente vale 0 y γ pasa a MN/m³."""
    sheet, header, rows, dec = _rows(path, sheet)
    cols = {_HB[k]: i for i, h in enumerate(header) if (k := _norm(h)) in _HB}
    for need in ("gsi", "mi"):
        if need not in cols:
            raise ValueError(f"sheet '{sheet}': missing column '{need}'")
    gu = _header_unit(header[cols["gamma"]]) if "gamma" in cols else None
    gf = 1e-3 if gu and gu.lower().replace("³", "3").startswith("kn") else 1.0
    out = []
    for n, raw in enumerate(rows, start=2):
        if all(_blank(v) for v in raw):
            continue
        v = {}
        for f, i in cols.items():
            if i < len(raw) and not _blank(raw[i]):
                v[f] = _text(raw[i]) if f == "material" else _number(raw[i], sheet, n, _text(header[i]), dec)
        for need in ("gsi", "mi"):
            if need not in v:
                raise ValueError(f"{_where(sheet, n, _text(header[cols[need]]))}: required value is empty")
        if "gamma" in v:
            v["gamma"] *= gf
        out.append(HbRow(**{"material": "", **v}))
    return out


def check_rocdata(rows) -> list[HbConsistency]:
    """check_hoek_brown por fila; un γ fuera del rango usual agrega el aviso de la errata de unidades."""
    out = []
    for r in rows:
        c = check_hoek_brown(gsi=r.gsi, mi=r.mi, d=r.d, mb=r.mb, s=r.s, a=r.a, erm_mpa=r.erm_mpa, ei_mpa=r.ei_mpa,
                             sigma_ci_mpa=r.sigma_ci_mpa)
        if r.gamma is not None and not GAMMA_RANGE_MN_M3[0] <= r.gamma <= GAMMA_RANGE_MN_M3[1]:
            c = replace(c, notes=c.notes + ("unit weight outside the usual range; check units",))
        out.append(c)
    return out


# --- monitoreo frente al modelo (E7) ---

MONITORING_RATIO_WARN = 1.5  # provisional: medido/modelado por encima de esto pide atención


@dataclass(frozen=True)
class MonitoringComparison:
    object_id: str = field(repr=False)
    stage: str | None
    measured: float
    modeled: float | None
    ratio: float | None  # medido / modelado; None si no hay modelo
    warning: str | None = None
    note: str | None = None


def compare_monitoring(measured, modeled, *, quantity: str = "convergence_pct") -> list[MonitoringComparison]:
    """Razón medido/modelado por (id, etapa). No juzga: avisa si ratio > MONITORING_RATIO_WARN.

    `modeled` es un ExternalSet (se cruza por id y etapa, o por id si el modelo no trae etapa) o un
    {id: TunnelResult}, cuyo valor es strain_eq_pct si hay cruce con el sostenimiento y strain_pct si no.
    """
    if isinstance(modeled, ExternalSet):
        table = {(r.object_id, r.stage): r.value for r in modeled.records if r.quantity == quantity}
        get = lambda oid, st: table.get((oid, st), table.get((oid, None)))  # noqa: E731
    else:
        def get(oid, st):
            t = modeled.get(oid)
            if t is None:
                return None
            return t.interaction.strain_eq_pct if t.interaction is not None and t.interaction.found else t.strain_pct
    out = []
    for r in (r for r in measured.records if r.quantity == quantity):
        m = get(r.object_id, r.stage)
        if m is None or m == 0:
            out.append(MonitoringComparison(r.object_id, r.stage, r.value, None, None, None,
                                            "no model for some measurements"))
            continue
        ratio = r.value / m
        warn = f"measured exceeds model by more than {(MONITORING_RATIO_WARN - 1) * 100:g} %"
        out.append(MonitoringComparison(r.object_id, r.stage, r.value, m, ratio,
                                        warn if ratio > MONITORING_RATIO_WARN else None))
    return out


def lining_forces(external, *, object_id: str | None = None) -> list:
    """rm.LiningForce por (id, etapa) desde axial_force_mn, moment_mnm y shear_mn; sin M ni Q valen 0."""
    recs = external.records if isinstance(external, ExternalSet) else tuple(external)
    groups: dict = {}
    for r in recs:
        if r.quantity in ("axial_force_mn", "moment_mnm", "shear_mn") and object_id in (None, r.object_id):
            groups.setdefault((r.object_id, r.stage), {})[r.quantity] = r.value
    out = []
    for g in groups.values():
        if "axial_force_mn" not in g:
            raise ValueError("lining force without its 'axial_force_mn'")
        f = rm.LiningForce()
        f.n_mn, f.m_mnm, f.q_mn = g["axial_force_mn"], g.get("moment_mnm", 0.0), g.get("shear_mn", 0.0)
        out.append(f)
    return out
