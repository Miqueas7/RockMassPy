"""Histórico geomecánico de la mina (plantilla completa) y su auditoría de ingesta (Fase 4, R2, R3 y R9).

Lee las hojas Tramos, Tipos_sostenimiento y Desempeno de la plantilla (`tools/plantilla_historico.py`), de un .xlsx
o de una carpeta con un CSV por hoja, con el lector genérico de la 1D (`tramos.read_records`): no hay un segundo
parser. `tramos.Tramo` no cambia; el histórico tiene su propio registro con todas las columnas que usan los niveles.
Las columnas de identificación (labor, zona, coordenadas) y el `id_tramo` nunca aparecen en un mensaje de error ni
en el texto de un hallazgo: el `id_tramo` y la fila van como campos, para la tabla de resultados.
"""

import datetime
import re
from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from . import _rockmasspy_core as rm
from .csv_io import _CsvSource, _csv_files
from .excel_io import _open, _row, _support_dicts, _where
from .gsi_charts import normalize_cell
from .intact_rock import _strip
from .support import SupportType
from .table_io import support_from_dict
from .tramos import _IDENT, read_records

HISTORY_SHEETS = ("Tramos", "Tipos_sostenimiento", "Desempeno")
INSPECTION_STATES = ("Estable", "Falla", "Reparado", "Abandonado")
FAILURE_STATES = ("Falla", "Reparado")  # Reparado cuenta como falla: se reparó porque falló (por confirmar, R9)

# Mínimos de cada nivel (R6: heurísticas del spec, decisión de diseño; R11 los confirma con simulación)
MIN_PAIRS_LEVEL1 = 30
MIN_LABORS_LEVEL1 = 5
MIN_TRAMOS_PER_TYPE_LEVEL2 = 10
MIN_LABORS_PER_TYPE_LEVEL2 = 5
MIN_FAILURES_PER_PARAMETER_LEVEL3 = 10
LEVEL3_BASE_PARAMETERS = 4  # ln Q, ln De, rango del sostenimiento y ln exposición (R9); decisión de diseño
MIN_ZONES_LEVEL3 = 3

# Tolerancias de la auditoría (R3)
Q_ABS_TOL = 0.005
Q_REL_TOL = 0.01
RMR_TOL_POINTS = 1.0

FINDING_KINDS = ("q_mismatch", "rmr_mismatch", "not_recomputed", "overlapping_chainage", "repeated_components",
                 "unknown_support", "unknown_tramo", "inspection_before_installation")


@dataclass(frozen=True)
class HistoryTramo:
    id_tramo: str
    zona_nivel: str | None = field(repr=False)
    labor_codigo: str | None = field(repr=False)
    tipo_labor: str | None
    fecha_evaluacion: str | None
    progresiva_inicio_m: float | None
    progresiva_fin_m: float | None
    este_m: float | None = field(repr=False)
    norte_m: float | None = field(repr=False)
    cota_m: float | None
    datum: str | None
    profundidad_m: float | None
    ancho_m: float | None
    alto_m: float | None
    luz_m: float | None
    esr: float | None
    rumbo_labor_grados: float | None
    vida_util: str | None
    metodo_excavacion: str | None
    litologia: str | None = field(repr=False)
    alteracion: str | None
    ucs_mpa: float | None
    metodo_ucs: str | None
    rqd_pct: float | None
    jv: float | None
    num_familias: float | None
    espaciamiento_m: float | None
    puntaje_condicion_juntas: float | None
    agua: str | None
    jn: float | None
    jr: float | None
    ja: float | None
    jw: float | None
    srf: float | None
    rmr_valor: float | None
    rmr_edicion: str | None
    q_valor: float | None
    q_edicion: str | None
    gsi_valor: float | None
    gsi_tabla: str | None
    gsi_celda: str | None
    sost_recomendado: str | None
    sost_instalado: str | None
    fecha_instalacion: str | None
    tiempo_sin_sostener_h: float | None
    fila: int  # fila de origen (la cabecera es la 1)


@dataclass(frozen=True)
class SupportTypeDef:
    codigo_tipo: str
    orden: int
    descripcion: str
    elementos: SupportType  # perno, shotcrete, malla, cimbra y costo, validados como en la 1B
    fila: int


@dataclass(frozen=True)
class Inspection:
    id_tramo: str
    fecha_inspeccion: str
    estado: str  # uno de INSPECTION_STATES
    tipo_falla: str | None
    volumen_m3: float | None
    sobreexcavacion_pct: float | None
    convergencia_mm: float | None
    reparacion_tipo: str | None
    fila: int


@dataclass(frozen=True)
class History:
    tramos: tuple[HistoryTramo, ...]
    support_types: tuple[SupportTypeDef, ...]
    inspections: tuple[Inspection, ...]


HISTORY_TRAMO_COLUMNS = tuple(n for n in HistoryTramo.__dataclass_fields__ if n != "fila")
INSPECTION_COLUMNS = tuple(n for n in Inspection.__dataclass_fields__ if n != "fila")
_TRAMO_TEXT = {"id_tramo", "zona_nivel", "labor_codigo", "tipo_labor", "fecha_evaluacion", "datum", "vida_util",
               "metodo_excavacion", "litologia", "alteracion", "metodo_ucs", "agua", "rmr_edicion", "q_edicion",
               "gsi_tabla", "gsi_celda", "sost_recomendado", "sost_instalado", "fecha_instalacion"}
_TRAMO_DATES = ("fecha_evaluacion", "fecha_instalacion")
_INSP_TEXT = {"id_tramo", "fecha_inspeccion", "estado", "tipo_falla", "reparacion_tipo"}


def _check_dates(vals, sheet, n, cols):
    for c in cols:
        v = vals[c]
        if v is None:
            continue
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
                raise ValueError
            datetime.date.fromisoformat(v)
        except ValueError:
            raise ValueError(f"{_where(sheet, n, c)}: expected a date yyyy-mm-dd, got '{v}'") from None


def _read_tramos(src, column_map):
    out = []
    for n, vals in read_records(src, "Tramos", column_map, columns=HISTORY_TRAMO_COLUMNS, text=_TRAMO_TEXT,
                                required=("id_tramo",), ident=_IDENT, id_column="id_tramo", dates=_TRAMO_DATES):
        _check_dates(vals, "Tramos", n, _TRAMO_DATES)
        if vals["gsi_celda"] is not None:
            try:
                vals["gsi_celda"] = normalize_cell(vals["gsi_celda"])
            except ValueError as e:
                raise ValueError(f"{_where('Tramos', n, 'gsi_celda')}: {e}") from None
        out.append(HistoryTramo(**vals, fila=n))
    return tuple(out)


def _read_support_types(src):
    sheet = "Tipos_sostenimiento"
    if sheet not in src.sheetnames:
        return ()
    out, codes, orders = [], {}, {}
    for n, d in _support_dicts(src, sheet):
        st = _row(sheet, n, support_from_dict, d)
        if not float(d["order"]).is_integer():
            raise ValueError(f"{_where(sheet, n, 'orden')}: expected an integer, got '{d['order']:g}'")
        for seen, key, col in ((codes, st.code, "codigo_tipo"), (orders, int(d["order"]), "orden")):
            if key in seen:
                raise ValueError(f"sheet '{sheet}': duplicate {col} in rows {seen[key]} and {n}")
            seen[key] = n
        out.append(SupportTypeDef(st.code, int(d["order"]), st.description, st, n))
    return tuple(out)


def _read_inspections(src):
    sheet = "Desempeno"
    if sheet not in src.sheetnames:
        return ()
    canon = {s.casefold(): s for s in INSPECTION_STATES}
    out = []
    for n, vals in read_records(src, sheet, None, columns=INSPECTION_COLUMNS, text=_INSP_TEXT,
                                required=("id_tramo", "fecha_inspeccion", "estado"), ident=(), id_column=None,
                                dates=("fecha_inspeccion",)):
        _check_dates(vals, sheet, n, ("fecha_inspeccion",))
        estado = canon.get(vals["estado"].casefold())
        if estado is None:
            raise ValueError(f"{_where(sheet, n, 'estado')}: expected one of {', '.join(INSPECTION_STATES)}, "
                             f"got '{vals['estado']}'")
        out.append(Inspection(**{**vals, "estado": estado}, fila=n))
    return tuple(out)


def load_history(path, *, column_map: Mapping[str, str] | None = None) -> History:
    """Lee el histórico de un .xlsx o de una carpeta con Tramos.csv, Tipos_sostenimiento.csv y Desempeno.csv.

    Tramos es obligatoria; si faltan Tipos_sostenimiento o Desempeno, su tupla queda vacía. `column_map` va de la
    columna del usuario a la de la plantilla, como en `load_tramos`, y se aplica solo a la hoja Tramos (las otras dos
    se llenan con la plantilla tal cual). No se leen `codigo_mina`, `evaluador_codigo` ni `observaciones`.
    """
    p = Path(path)
    if p.is_dir():
        src = _CsvSource(_csv_files(p, HISTORY_SHEETS))
        return History(_read_tramos(src, column_map), _read_support_types(src), _read_inspections(src))
    if p.suffix.lower() != ".xlsx":
        raise ValueError(f"{p.name}: unsupported input; give a .xlsx file or a folder of .csv files")
    src = _open(p)
    try:
        return History(_read_tramos(src, column_map), _read_support_types(src), _read_inspections(src))
    finally:
        src.wb.close()


# --- nivel 3: resultado por tramo (R9) ---

@dataclass(frozen=True)
class TramoOutcome:
    id_tramo: str
    failed: bool
    end_date: str  # primera falla, o la última inspección si no falló
    exposure_days: int | None  # None sin fecha de inicio o si la inspección es anterior al inicio
    start_from_evaluation: bool  # sin fecha_instalacion: se contó desde fecha_evaluacion (aviso en el informe)
    inspections: int


def _date(s):
    return None if s is None else datetime.date.fromisoformat(s)


def tramo_outcomes(history: History) -> tuple[TramoOutcome, ...]:
    """Un resultado por tramo con inspecciones, en el orden de la hoja Tramos. Un tramo sin inspecciones no entra
    (nunca se asume estable); las inspecciones de un id_tramo que no existe tampoco (las señala la auditoría)."""
    by_id = defaultdict(list)
    for i in history.inspections:
        by_id[i.id_tramo].append(i)
    out = []
    for t in history.tramos:
        insp = sorted(by_id.get(t.id_tramo, ()), key=lambda i: i.fecha_inspeccion)
        if not insp:
            continue
        fails = [i for i in insp if i.estado in FAILURE_STATES]
        end = (fails or insp[-1:])[0].fecha_inspeccion
        start = t.fecha_instalacion or t.fecha_evaluacion
        days = None if start is None else (_date(end) - _date(start)).days
        out.append(TramoOutcome(t.id_tramo, bool(fails), end, None if days is None or days < 0 else days,
                                t.fecha_instalacion is None and start is not None, len(insp)))
    return tuple(out)


# --- auditoría de ingesta (R3) ---

@dataclass(frozen=True)
class HistoryFinding:
    kind: str  # uno de FINDING_KINDS
    message: str  # sin valores de identificación ni id_tramo
    sheet: str
    fila: int
    id_tramo: str | None


@dataclass(frozen=True)
class LevelReadiness:
    level: int
    item: str  # nivel 1: tipo de par; nivel 2: código del tipo instalado; nivel 3: "performance"
    counts: dict[str, int]
    minimums: dict[str, int]

    @property
    def missing(self) -> dict[str, int]:
        return {k: max(0, m - self.counts.get(k, 0)) for k, m in self.minimums.items()}

    @property
    def ready(self) -> bool:
        return not any(self.missing.values())


@dataclass(frozen=True)
class HistoryAudit:
    findings: tuple[HistoryFinding, ...]
    readiness: tuple[LevelReadiness, ...]
    tramos: int
    support_types: int
    inspections: int


_Q_EDITIONS = {"Q-NGI-2015": rm.QEdition.NGI2015, "Q-NGI-2025": rm.QEdition.NGI2025}
_WATER = {"seco": rm.Water.Dry, "humedo": rm.Water.Damp, "mojado": rm.Water.Wet, "goteo": rm.Water.Dripping,
          "flujo": rm.Water.Flowing}  # Bieniawski (1989), condición general: 15, 10, 7, 4 y 0 puntos
_COMPONENTS = ("rqd_pct", "jn", "jr", "ja", "jw", "srf", "ucs_mpa", "espaciamiento_m", "puntaje_condicion_juntas",
               "agua", "gsi_valor")
_PAIRS = {"rmr_from_q": ("rmr_valor", "q_valor"), "gsi_from_rmr": ("gsi_valor", "rmr_valor"),
          "gsi_from_q_prime": ("gsi_valor", "rqd_pct", "jn", "jr", "ja")}


def _finding(kind, message, t, sheet="Tramos"):
    return HistoryFinding(kind, message, sheet, t.fila, t.id_tramo)


def _audit_q(t):
    params = (t.rqd_pct, t.jn, t.jr, t.ja, t.jw, t.srf)
    if t.q_valor is None or any(p is None for p in params):
        return None
    if t.q_edicion == "Q-1974":  # el núcleo no tiene esa edición (como en el lote de la 1D)
        return _finding("not_recomputed", "Q-1974 is not supported; Q not recomputed", t)
    ed = _Q_EDITIONS.get(t.q_edicion, rm.QEdition.NGI2025)
    try:
        q = rm.q_value(rm.QInput(*params), ed).q
    except ValueError as e:  # parámetros fuera de dominio: el mensaje solo trae nombres y números
        return _finding("not_recomputed", f"Q not recomputed: {e}", t)
    if abs(t.q_valor - q) > max(Q_ABS_TOL, Q_REL_TOL * q):
        return _finding("q_mismatch", f"recorded Q {t.q_valor:g} differs from Q {q:.4g} recomputed from "
                                      f"RQD, Jn, Jr, Ja, Jw and SRF ({ed.name})", t)
    return None


def _audit_rmr(t):
    if (t.rmr_edicion or "").strip().upper() != "RMR89" or t.rmr_valor is None:
        return None
    if any(v is None for v in (t.ucs_mpa, t.rqd_pct, t.espaciamiento_m, t.puntaje_condicion_juntas, t.agua)):
        return None
    water = _WATER.get(_strip(t.agua).strip().lower())
    if water is None:
        return _finding("not_recomputed", "RMR89 not recomputed: agua must be one of Seco, Húmedo, Mojado, Goteo "
                                          "or Flujo", t)
    i = rm.Rmr89Input()
    i.ucs_mpa, i.rqd_pct, i.spacing_m = t.ucs_mpa, t.rqd_pct, t.espaciamiento_m
    i.joint_condition_rating, i.water = t.puntaje_condicion_juntas, water
    try:
        basic = rm.rmr89(i).basic
    except ValueError as e:
        return _finding("not_recomputed", f"RMR89 not recomputed: {e}", t)
    if abs(t.rmr_valor - basic) > RMR_TOL_POINTS:
        return _finding("rmr_mismatch", f"recorded RMR {t.rmr_valor:g} differs from basic RMR89 {basic:g} by more "
                                        f"than {RMR_TOL_POINTS:g} point; it may include the orientation adjustment", t)
    return None


def _audit_independence(tramos):
    """Mismas labores: progresivas que se solapan o mismos componentes en tramos consecutivos (R3)."""
    out = []
    by_labor = defaultdict(list)
    for t in tramos:
        if t.labor_codigo is not None:
            by_labor[t.labor_codigo].append(t)
    for ts in by_labor.values():
        ts.sort(key=lambda t: (t.progresiva_inicio_m is None, t.progresiva_inicio_m or 0.0, t.fila))
        widest = None  # el tramo que llega más lejos hasta ahora: atrapa también solapes no contiguos
        for t in ts:
            if t.progresiva_inicio_m is None or t.progresiva_fin_m is None:
                continue
            lo, hi = sorted((t.progresiva_inicio_m, t.progresiva_fin_m))
            if widest is not None and lo < widest[1]:
                out.append(_finding("overlapping_chainage", f"chainage overlaps row {widest[0].fila} of the same "
                                                            f"labor; records are not independent", t))
            if widest is None or hi > widest[1]:
                widest = (t, hi)
        for prev, t in zip(ts, ts[1:]):
            comp = tuple(getattr(t, c) for c in _COMPONENTS)
            if any(v is not None for v in comp) and comp == tuple(getattr(prev, c) for c in _COMPONENTS):
                out.append(_finding("repeated_components", f"same classification components as row {prev.fila}, "
                                                           f"the previous tramo of the same labor; records are not "
                                                           f"independent", t))
    return out


def _audit_coherence(history):
    out = []
    codes = {s.codigo_tipo for s in history.support_types}
    for t in history.tramos:
        for col in ("sost_recomendado", "sost_instalado"):
            code = getattr(t, col)
            if code is not None and code not in codes:
                out.append(_finding("unknown_support", f"{col} '{code}' is not in sheet Tipos_sostenimiento", t))
    by_id = {t.id_tramo: t for t in history.tramos}
    for i in history.inspections:
        t = by_id.get(i.id_tramo)
        if t is None:
            out.append(HistoryFinding("unknown_tramo", "id_tramo not found in sheet Tramos", "Desempeno", i.fila,
                                      i.id_tramo))
        elif t.fecha_instalacion is not None and i.fecha_inspeccion < t.fecha_instalacion:  # ISO: orden de texto
            out.append(HistoryFinding("inspection_before_installation", "fecha_inspeccion is earlier than the "
                                      "fecha_instalacion of its tramo", "Desempeno", i.fila, i.id_tramo))
    return out


def _readiness(history):
    out = []
    for kind, cols in _PAIRS.items():
        ts = [t for t in history.tramos if all(getattr(t, c) is not None for c in cols)]
        out.append(LevelReadiness(1, kind, {"pairs": len(ts), "labors": len({t.labor_codigo for t in ts} - {None})},
                                  {"pairs": MIN_PAIRS_LEVEL1, "labors": MIN_LABORS_LEVEL1}))
    used = [s.codigo_tipo for s in sorted(history.support_types, key=lambda s: s.orden)]
    used += sorted({t.sost_instalado for t in history.tramos} - set(used) - {None})
    for code in used:
        ts = [t for t in history.tramos if t.sost_instalado == code]
        out.append(LevelReadiness(2, code, {"tramos": len(ts), "labors": len({t.labor_codigo for t in ts} - {None})},
                                  {"tramos": MIN_TRAMOS_PER_TYPE_LEVEL2, "labors": MIN_LABORS_PER_TYPE_LEVEL2}))
    outcomes = tramo_outcomes(history)
    zone = {t.id_tramo: t.zona_nivel for t in history.tramos}
    out.append(LevelReadiness(3, "performance", {
        "failures": sum(o.failed for o in outcomes),
        "zones": len({zone[o.id_tramo] for o in outcomes} - {None}),
        "tramos_with_inspections": len(outcomes),
        "tramos_without_inspections": len(history.tramos) - len(outcomes),  # excluidos: nunca se asumen estables
        "start_from_evaluation": sum(o.start_from_evaluation for o in outcomes),
        "without_exposure": sum(o.exposure_days is None for o in outcomes),
    }, {"failures": MIN_FAILURES_PER_PARAMETER_LEVEL3 * LEVEL3_BASE_PARAMETERS, "zones": MIN_ZONES_LEVEL3}))
    return tuple(out)


def audit_history(history: History) -> HistoryAudit:
    """Auditoría de ingesta: Q y RMR89 recalculados, registros no independientes, coherencia entre hojas y
    preparación de cada nivel (solo conteos). Avisa, nunca bloquea."""
    findings = [f for t in history.tramos for f in (_audit_q(t), _audit_rmr(t)) if f is not None]
    findings += _audit_independence(history.tramos) + _audit_coherence(history)
    findings.sort(key=lambda f: (f.sheet != "Tramos", f.fila, FINDING_KINDS.index(f.kind)))
    return HistoryAudit(tuple(findings), _readiness(history), len(history.tramos), len(history.support_types),
                        len(history.inspections))


def history_audit_counts(audit: HistoryAudit) -> dict[str, int]:
    """Conteos de una sola fuente para la CLI, el informe y las pruebas de paridad."""
    c = Counter(f.kind for f in audit.findings)
    return {"tramos": audit.tramos, "support_types": audit.support_types, "inspections": audit.inspections,
            "findings": len(audit.findings), **{k: c.get(k, 0) for k in FINDING_KINDS},
            "levels_ready": sum(r.ready for r in audit.readiness)}
