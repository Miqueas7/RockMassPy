"""Histórico geomecánico de la mina (plantilla completa) y su auditoría de ingesta (Fase 4, R2, R3 y R9).

Lee las hojas Tramos, Tipos_sostenimiento y Desempeno de la plantilla (`tools/plantilla_historico.py`), de un .xlsx
o de una carpeta con un CSV por hoja, con el lector genérico de la 1D (`tramos.read_records`): no hay un segundo
parser. `tramos.Tramo` no cambia; el histórico tiene su propio registro con todas las columnas que usan los niveles.
Las columnas de identificación (labor, zona, coordenadas) y el `id_tramo` nunca aparecen en un mensaje de error ni
en el texto de un hallazgo: el `id_tramo` y la fila van como campos, para la tabla de resultados.
"""

import datetime
import math
import re
from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from . import _rockmasspy_core as rm
from .batch import _Q_EDITIONS, write_table
from .csv_io import _CsvSource, _csv_files
from .excel_io import TIPOS, _open, _row, _support_dicts, _where
from .intact_rock import _strip
from .support import SupportType
from .table_io import _optional, support_from_dict
from .tramos import _IDENT, _normalize_gsi_cell, read_records

HISTORY_SHEETS = ("Tramos", "Tipos_sostenimiento", "Desempeno")
INSPECTION_STATES = ("Estable", "Falla", "Reparado", "Abandonado")
FAILURE_STATES = ("Falla", "Reparado")  # Reparado cuenta como falla: se reparó porque falló (por confirmar, R9)

# Mínimos de cada nivel (R6: heurísticas del spec, decisión de diseño; R11 los confirma con simulación)
MIN_PAIRS_LEVEL1 = 30
MIN_LABORS_LEVEL1 = 5
MIN_TRAMOS_PER_TYPE_LEVEL2 = 10
MIN_LABORS_PER_TYPE_LEVEL2 = 5
MIN_EVENTS_PER_PARAMETER_LEVEL3 = 10  # se aplica a la clase menor: min(fallas, no fallas)
LEVEL3_BASE_PARAMETERS = 3  # ln Q, ln De y rango del sostenimiento; la exposición entra como offset (R9); decisión de diseño
MIN_ZONES_LEVEL3 = 3

# Tolerancias de la auditoría (R3). Q en escala logarítmica: |ln Q registrado − ln Q recalculado| > ln(1 + Q_REL_TOL)
# y además |diferencia| > Q_ABS_TOL. El piso absoluto solo cubre el redondeo de un Q escrito con 4 decimales
# (Fase 5B: el piso anterior de 0.005 escondía un Q ×3 con Q < 0.0075)
Q_ABS_TOL = 0.00005
Q_REL_TOL = 0.01
RMR_TOL_POINTS = 1.0

FINDING_KINDS = ("q_mismatch", "rmr_mismatch", "not_recomputed", "overlapping_chainage", "repeated_components",
                 "unknown_support", "unknown_tramo", "inspection_before_installation", "inspection_after_abandonment",
                 "missing_values")


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
                                required=("id_tramo",), ident=_IDENT | {"cota_m"}, id_column="id_tramo",
                                dates=_TRAMO_DATES):
        _check_dates(vals, "Tramos", n, _TRAMO_DATES)
        _normalize_gsi_cell(vals, "Tramos", n)
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
    Los errores de archivo no llevan la ruta ni el nombre: el archivo puede llevar el nombre de la mina.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError("history file not found" if p.suffix else "history folder not found")
    if p.is_dir():
        try:
            src = _CsvSource(_csv_files(p, HISTORY_SHEETS))
            return History(_read_tramos(src, column_map), _read_support_types(src), _read_inspections(src))
        except OSError:  # el OSError de Python trae la ruta completa
            raise OSError("history folder could not be read (in use or no permission)") from None
    if p.suffix.lower() != ".xlsx":
        raise ValueError("unsupported history input; give a .xlsx file or a folder of .csv files")
    try:
        try:
            src = _open(p)
        except ValueError:  # el mensaje de _open (1D) nombra el archivo
            raise ValueError("history file is not a valid .xlsx file") from None
        try:  # read_only: openpyxl sigue leyendo el archivo mientras se recorren las hojas
            return History(_read_tramos(src, column_map), _read_support_types(src), _read_inspections(src))
        finally:
            src.wb.close()
    except OSError:  # abierto en exclusiva (Excel) o sin permiso; el OSError de Python trae la ruta completa
        raise OSError("history file could not be read (in use or no permission)") from None


def check_group_by(group_by: str | None) -> None:
    """`group_by` del nivel 1: None o un atributo de `HistoryTramo` (no `fila`). El mensaje no repite el valor:
    puede venir de la línea de comandos con un nombre de la mina. Vive aquí, sin numpy, para que la CLI valide
    aunque falte el extra [ml]."""
    if group_by is not None and (group_by == "fila" or group_by not in HistoryTramo.__dataclass_fields__):
        raise ValueError("group_by must be None or a column of sheet Tramos")


def _support_row(s: SupportTypeDef) -> dict:
    e = s.elementos
    return {"codigo_tipo": s.codigo_tipo, "orden": s.orden, "descripcion": s.descripcion or None,
            "perno_tipo": e.bolt and e.bolt.kind, "perno_longitud_m": e.bolt and e.bolt.length_m,
            "perno_espaciamiento_m": e.bolt and e.bolt.spacing_m,
            "shotcrete_espesor_mm": e.shotcrete and e.shotcrete.thickness_mm,
            "shotcrete_fibra": e.shotcrete and ("Sí" if e.shotcrete.fiber else "No"), "malla": e.mesh,
            "cimbra": e.arch, "costo_relativo": e.relative_cost}


def save_history_xlsx(history: History, path) -> None:
    """Escribe las hojas Tramos, Tipos_sostenimiento y Desempeno con las columnas de la plantilla, en su orden.

    `load_history` del archivo devuelve el mismo History si las filas (`fila`) son las de la hoja (2, 3, …), como las
    del generador sintético (`rockmasspy.predictive.synthetic_history`), y si cada número tiene a lo sumo 15 cifras
    significativas (openpyxl no guarda más). `codigo_mina`, `evaluador_codigo` y `observaciones` van vacías: el
    histórico no las guarda. Necesita openpyxl (extra `io`), no numpy.
    """
    openpyxl = _optional("openpyxl")
    tramo_cols = ("id_tramo", "codigo_mina", *HISTORY_TRAMO_COLUMNS[1:], "evaluador_codigo", "observaciones")
    sheets = (("Tramos", tramo_cols, [vars(t) for t in history.tramos]),
              ("Tipos_sostenimiento", TIPOS, [_support_row(s) for s in history.support_types]),
              ("Desempeno", (*INSPECTION_COLUMNS, "observaciones"), [vars(i) for i in history.inspections]))
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, cols, rows in sheets:
        ws = wb.create_sheet(name)
        ws.append(list(cols))
        for r in rows:
            ws.append([r.get(c) for c in cols])
    wb.save(path)


# --- nivel 3: resultado por tramo (R9) ---

@dataclass(frozen=True)
class TramoOutcome:
    """Resultado de desempeño de un tramo (R9).

    `exposure_days`: días desde fecha_instalacion (o fecha_evaluacion, con `start_from_evaluation`) hasta la primera
    falla o la última inspección usada. Una exposición de 0 días se recorta a 1 (el nivel 3 usa ln de la exposición).
    None si no hay fecha de inicio o si la inspección es anterior al inicio. Las inspecciones posteriores al primer
    «Abandonado» no cuentan: el tramo queda censurado en esa fecha y sin falla (la auditoría las señala).
    """
    id_tramo: str
    failed: bool
    end_date: str  # primera falla, o la última inspección usada si no falló
    exposure_days: int | None
    start_from_evaluation: bool  # sin fecha_instalacion: se contó desde fecha_evaluacion (aviso en el informe)
    inspections: int  # inspecciones usadas (hasta el primer «Abandonado»)


def _date(s):
    return None if s is None else datetime.date.fromisoformat(s)


def _inspections_by_tramo(history):
    """{id_tramo: (usadas, ignoradas)}, en orden de fecha y fila; se corta en el primer «Abandonado»."""
    by_id = defaultdict(list)
    for i in history.inspections:
        by_id[i.id_tramo].append(i)
    out = {}
    for k, ins in by_id.items():
        ins.sort(key=lambda i: (i.fecha_inspeccion, i.fila))
        cut = next((j + 1 for j, i in enumerate(ins) if i.estado == "Abandonado"), len(ins))
        out[k] = (ins[:cut], ins[cut:])
    return out


def tramo_outcomes(history: History) -> tuple[TramoOutcome, ...]:
    """Un resultado por tramo con inspecciones, en el orden de la hoja Tramos. Un tramo sin inspecciones no entra
    (nunca se asume estable); las inspecciones de un id_tramo que no existe tampoco (las señala la auditoría)."""
    by_id = _inspections_by_tramo(history)
    out = []
    for t in history.tramos:
        insp = by_id.get(t.id_tramo, ((), ()))[0]
        if not insp:
            continue
        fails = [i for i in insp if i.estado in FAILURE_STATES]
        end = (fails or insp[-1:])[0].fecha_inspeccion
        start = t.fecha_instalacion or t.fecha_evaluacion
        days = None if start is None else (_date(end) - _date(start)).days
        out.append(TramoOutcome(t.id_tramo, bool(fails), end, None if days is None or days < 0 else max(days, 1),
                                t.fecha_instalacion is None and start is not None, len(insp)))
    return tuple(out)


# --- auditoría de ingesta (R3) ---

@dataclass(frozen=True)
class HistoryFinding:
    kind: str  # uno de FINDING_KINDS
    message: str  # sin valores de identificación ni id_tramo
    sheet: str
    fila: int | None  # None: el hallazgo es de la hoja entera
    id_tramo: str | None


@dataclass(frozen=True)
class LevelReadiness:
    """Preparación de un nivel: `counts` trae lo usable (filas completas para las variables base) y los totales;
    `minimums` se compara con las claves de lo usable."""
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


# el producto de Q es el mismo en las tres ediciones: Q-1974 se recalcula con NGI2015 (no está en el núcleo)
_Q_ED = {**{k.casefold(): (v, "") for k, v in _Q_EDITIONS.items()},
         "q-1974": (rm.QEdition.NGI2015, "; parameters taken from the 1974 tables")}
_WATER = {"seco": rm.Water.Dry, "humedo": rm.Water.Damp, "mojado": rm.Water.Wet, "goteo": rm.Water.Dripping,
          "flujo": rm.Water.Flowing}  # Bieniawski (1989), condición general: 15, 10, 7, 4 y 0 puntos
_COMPONENTS = ("rqd_pct", "jn", "jr", "ja", "jw", "srf", "ucs_mpa", "espaciamiento_m", "puntaje_condicion_juntas",
               "agua", "gsi_valor")
_PAIRS = {"rmr_from_q": ("rmr_valor", "q_valor"), "gsi_from_rmr": ("gsi_valor", "rmr_valor"),
          "gsi_from_q_prime": ("gsi_valor", "rqd_pct", "jn", "jr", "ja")}
LEVEL1_KINDS = tuple(_PAIRS)
LEVEL1_RMR_EDITIONS = ("RMR76", "RMR89")  # las que tienen correlación global en el núcleo (prior del nivel 1)


def _rmr_edition_key(edicion: str | None) -> str:
    return re.sub(r"[\s-]", "", edicion or "").upper()  # RMR-89, RMR 89 → RMR89


def _q_prime(t: HistoryTramo) -> float:
    """Q′ = RQD/Jn·Jr/Ja del núcleo (RQD < 10 se toma como 10); jw = srf = 1 no entran en q_base. Lanza
    ValueError con componentes fuera de dominio."""
    return rm.q_value(rm.QInput(t.rqd_pct, t.jn, t.jr, t.ja, 1.0, 1.0), rm.QEdition.NGI2025).q_base


def labor_key(t: HistoryTramo) -> tuple[str | None, str] | None:
    """Clave de la labor: (zona_nivel, labor_codigo); sin zona, solo la labor. None sin labor_codigo.
    La comparten la auditoría, la preparación y la validación agrupada de la 4B."""
    return None if t.labor_codigo is None else (t.zona_nivel, t.labor_codigo)


def _finding(kind, message, t, sheet="Tramos"):
    return HistoryFinding(kind, message, sheet, t.fila, t.id_tramo)


def _q_edition(q_edicion):
    """(edición del núcleo, nota para el mensaje); sin edición, NGI2025; una desconocida no se repite en la nota."""
    if q_edicion is None:
        return rm.QEdition.NGI2025, ""
    return _Q_ED.get(q_edicion.strip().casefold(), (rm.QEdition.NGI2025, "; unknown q_edicion, NGI2025 used"))


def _audit_q(t):
    params = (t.rqd_pct, t.jn, t.jr, t.ja, t.jw, t.srf)
    if t.q_valor is None or any(p is None for p in params):
        return None
    ed, note = _q_edition(t.q_edicion)
    try:
        q = rm.q_value(rm.QInput(*params), ed).q
    except ValueError as e:  # parámetros fuera de dominio: el mensaje solo trae nombres y números
        return _finding("not_recomputed", f"Q not recomputed: {e}", t)
    if t.q_valor <= 0 or (abs(math.log(t.q_valor / q)) > math.log1p(Q_REL_TOL) and abs(t.q_valor - q) > Q_ABS_TOL):
        return _finding("q_mismatch", f"recorded Q {t.q_valor:g} differs from Q {q:.4g} recomputed from "
                                      f"RQD, Jn, Jr, Ja, Jw and SRF ({ed.name}{note})", t)
    return None


def _audit_q_prime(t):
    """Q′ del nivel 1 no calculable. Con Q y sus seis parámetros, `_audit_q` ya lo reporta: no se duplica."""
    if any(getattr(t, c) is None for c in ("rqd_pct", "jn", "jr", "ja")) \
            or all(v is not None for v in (t.q_valor, t.jw, t.srf)):
        return None
    try:
        _q_prime(t)
    except ValueError as e:  # el mensaje del núcleo solo trae nombres y números
        return _finding("not_recomputed", f"Q' not computable for level 1: {e}", t)
    return None


def _audit_rmr(t):
    if _rmr_edition_key(t.rmr_edicion) != "RMR89" or t.rmr_valor is None:
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
        if labor_key(t) is not None:
            by_labor[labor_key(t)].append(t)

    def start(t):  # la progresiva puede venir al revés (fin < inicio)
        ps = [p for p in (t.progresiva_inicio_m, t.progresiva_fin_m) if p is not None]
        return (not ps, min(ps, default=0.0), t.fila)

    for ts in by_labor.values():
        ts.sort(key=start)
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
            if sum(v is not None for v in comp) >= 2 and comp ==tuple(getattr(prev, c) for c in _COMPONENTS):
                out.append(_finding("repeated_components", f"same classification components as row {prev.fila}, "
                                                           f"the previous tramo of the same labor; records are not "
                                                           f"independent", t))
    return out


# columnas que usan los niveles (o la auditoría para recalcular Q y RMR) → niveles que las usan
_LEVEL_COLUMNS = {
    **dict.fromkeys(("rqd_pct", "jn", "jr", "ja"), "1"), **dict.fromkeys(("rmr_valor", "rmr_edicion", "gsi_valor"), "1"),
    "q_valor": "1, 2 and 3", **dict.fromkeys(("luz_m", "esr", "sost_instalado", "tipo_labor", "zona_nivel",
                                               "fecha_evaluacion"), "2 and 3"),
    "labor_codigo": "1, 2 and 3", "vida_util": "2", **dict.fromkeys(("profundidad_m", "fecha_instalacion"), "3"),
    **dict.fromkeys(("jw", "srf", "ucs_mpa", "espaciamiento_m", "puntaje_condicion_juntas", "agua"),
                    "the audit (Q and RMR recomputation)")}


def _audit_missing(tramos):
    """Un hallazgo por columna usada que está vacía en algunos tramos (no en todos: una columna que la mina no
    registra ya la reporta la preparación de cada nivel). Solo conteos: nunca valores ni filas."""
    out = []
    for col, levels in _LEVEL_COLUMNS.items():
        n = sum(getattr(t, col) is None for t in tramos)
        if 0 < n < len(tramos):
            used = levels if levels.startswith("the") else f"level{'s' * (len(levels) > 1)} {levels}"
            out.append(HistoryFinding("missing_values", f"column {col} is empty in {n} of {len(tramos)} tramos "
                                      f"(used by {used})", "Tramos", None, None))
    return out


def _audit_coherence(history):
    out = []
    codes = {s.codigo_tipo for s in history.support_types}
    cols = ("sost_recomendado", "sost_instalado")
    if not codes:  # sin hoja (o vacía): un solo hallazgo, no uno por tramo
        n = sum(any(getattr(t, c) is not None for c in cols) for t in history.tramos)
        if n:
            out.append(HistoryFinding("unknown_support", f"sheet Tipos_sostenimiento is missing or empty; {n} tramos "
                                      "give a support code that cannot be checked", "Tipos_sostenimiento", None, None))
        cols = ()
    for t in history.tramos:
        for col in cols:
            code = getattr(t, col)
            if code is not None and code not in codes:
                out.append(_finding("unknown_support", f"{col} '{code}' is not in sheet Tipos_sostenimiento", t))
    by_id = {t.id_tramo: t for t in history.tramos}
    for k, (_, ignored) in _inspections_by_tramo(history).items():
        if k in by_id:
            out += [HistoryFinding("inspection_after_abandonment", "inspection after the first 'Abandonado' of its "
                                   "tramo; ignored for the outcome", "Desempeno", i.fila, i.id_tramo) for i in ignored]
    for i in history.inspections:
        t = by_id.get(i.id_tramo)
        if t is None:
            out.append(HistoryFinding("unknown_tramo", "id_tramo not found in sheet Tramos", "Desempeno", i.fila,
                                      i.id_tramo))
        elif t.fecha_instalacion is not None and i.fecha_inspeccion < t.fecha_instalacion:  # ISO: orden de texto
            out.append(HistoryFinding("inspection_before_installation", "fecha_inspeccion is earlier than the "
                                      "fecha_instalacion of its tramo", "Desempeno", i.fila, i.id_tramo))
    return out


def _pos(x):
    return x is not None and x > 0


def _labors(ts):
    return len({labor_key(t) for t in ts} - {None})


@dataclass(frozen=True)
class Level1Rows:
    """Pares (x, y) del nivel 1 en la x original (Q, RMR o Q′) y cuántas filas completas se excluyeron."""
    tramos: tuple[HistoryTramo, ...]
    x: tuple[float, ...]
    y: tuple[float, ...]
    edition: str | None  # edición de RMR usada (RMR76 o RMR89); None en gsi_from_q_prime o sin edición soportada
    excluded_x: int  # Q ≤ 0 o componentes de Q′ fuera de dominio
    excluded_edition: int  # rmr_edicion vacía, no soportada o distinta de la usada


def level1_rows(history: History, kind: str, *, rmr_edition: str | None = None) -> Level1Rows:
    """Filas del nivel 1 que usan la preparación (`audit_history`) y el ajuste (`fit_site_correlation`).

    Excluye las filas sin x usable (Q ≤ 0; Q′ no calculable) y, en los tipos con RMR, las que no tienen la edición
    usada: `rmr_edition` (RMR76 o RMR89) o, si es None, la mayoritaria entre las soportadas (empate: RMR89).
    """
    if kind not in _PAIRS:
        raise ValueError(f"kind must be one of {', '.join(LEVEL1_KINDS)}")
    if rmr_edition is not None and _rmr_edition_key(rmr_edition) not in LEVEL1_RMR_EDITIONS:
        raise ValueError(f"rmr_edition must be one of {', '.join(LEVEL1_RMR_EDITIONS)}")
    rows, bad_x = [], 0
    for t in history.tramos:
        if any(getattr(t, c) is None for c in _PAIRS[kind]):
            continue
        if kind == "rmr_from_q":
            x, y = (t.q_valor if t.q_valor > 0 else None), t.rmr_valor
        elif kind == "gsi_from_rmr":
            x, y = t.rmr_valor, t.gsi_valor
        else:
            try:
                x = _q_prime(t)
            except ValueError:
                x = None
            y = t.gsi_valor
        if x is None:
            bad_x += 1
        else:
            rows.append((t, float(x), float(y)))
    edition, bad_ed = None, 0
    if kind != "gsi_from_q_prime":
        eds = Counter(_rmr_edition_key(t.rmr_edicion) for t, _, _ in rows)
        if rmr_edition is not None:
            edition = _rmr_edition_key(rmr_edition)
        elif any(e in eds for e in LEVEL1_RMR_EDITIONS):
            edition = max(LEVEL1_RMR_EDITIONS, key=lambda e: (eds[e], e == "RMR89"))
        kept = [r for r in rows if _rmr_edition_key(r[0].rmr_edicion) == edition]
        rows, bad_ed = kept, len(rows) - len(kept)
    return Level1Rows(tuple(r[0] for r in rows), tuple(r[1] for r in rows), tuple(r[2] for r in rows), edition,
                      bad_x, bad_ed)


def level2_rows(history: History) -> tuple[HistoryTramo, ...]:
    """Tramos usables en los niveles 2 y 3: Q, luz y ESR > 0 (se usan ln Q y ln De) y un tipo instalado definido
    en Tipos_sostenimiento. Fuente única para la preparación y los ajustes."""
    codes = {s.codigo_tipo for s in history.support_types}
    return tuple(t for t in history.tramos
                 if t.sost_instalado in codes and _pos(t.q_valor) and _pos(t.luz_m) and _pos(t.esr))


def level3_rows(history: History) -> tuple[tuple[TramoOutcome, HistoryTramo], ...]:
    """(resultado, tramo) usables en el nivel 3: los de `level2_rows` con inspección y exposición conocida."""
    by_id = {t.id_tramo: t for t in level2_rows(history)}
    return tuple((o, by_id[o.id_tramo]) for o in tramo_outcomes(history)
                 if o.exposure_days is not None and o.id_tramo in by_id)


def level3_parameters(rows) -> int:
    """Parámetros del modelo de desempeño: los base, +1 si todas las filas traen profundidad, + (tipos de labor − 1)."""
    labor_types = {t.tipo_labor for _, t in rows} - {None}
    return (LEVEL3_BASE_PARAMETERS + (bool(rows) and all(t.profundidad_m is not None for _, t in rows))
            + (len(labor_types) - 1 if len(labor_types) >= 2 else 0))


def _readiness(history):
    """Solo cuenta filas completas para las variables base de cada nivel; los totales van aparte."""
    out = []
    n_all = len(history.tramos)
    for kind in LEVEL1_KINDS:
        ts = level1_rows(history, kind).tramos  # los mismos pares que usa el ajuste por defecto
        out.append(LevelReadiness(1, kind, {"pairs": len(ts), "labors": _labors(ts), "total": n_all},
                                  {"pairs": MIN_PAIRS_LEVEL1, "labors": MIN_LABORS_LEVEL1}))
    rows2 = level2_rows(history)
    for s in sorted(history.support_types, key=lambda s: s.orden):
        total = [t for t in history.tramos if t.sost_instalado == s.codigo_tipo]
        ts = [t for t in rows2 if t.sost_instalado == s.codigo_tipo]
        out.append(LevelReadiness(2, s.codigo_tipo, {"tramos": len(ts), "labors": _labors(ts), "total": len(total)},
                                  {"tramos": MIN_TRAMOS_PER_TYPE_LEVEL2, "labors": MIN_LABORS_PER_TYPE_LEVEL2}))
    outcomes = tramo_outcomes(history)
    usable = level3_rows(history)
    failures = sum(o.failed for o, _ in usable)
    params = level3_parameters(usable)
    out.append(LevelReadiness(3, "performance", {
        "minority_class": min(failures, len(usable) - failures),
        "zones": len({t.zona_nivel for _, t in usable} - {None}),
        "usable": len(usable),
        "failures": failures,
        "non_failures": len(usable) - failures,
        "parameters": params,
        "failures_total": sum(o.failed for o in outcomes),
        "tramos": n_all,
        "tramos_with_inspections": len(outcomes),
        "tramos_without_inspections": n_all - len(outcomes),  # excluidos: nunca se asumen estables
        "start_from_evaluation": sum(o.start_from_evaluation for o in outcomes),
        "without_exposure": sum(o.exposure_days is None for o in outcomes),
    }, {"minority_class": MIN_EVENTS_PER_PARAMETER_LEVEL3 * params, "zones": MIN_ZONES_LEVEL3}))
    return tuple(out)


def audit_history(history: History) -> HistoryAudit:
    """Auditoría de ingesta: Q y RMR89 recalculados, registros no independientes, coherencia entre hojas, celdas
    vacías por columna (conteos) y preparación de cada nivel (solo conteos). Avisa, nunca bloquea."""
    findings = [f for t in history.tramos for f in (_audit_q(t), _audit_q_prime(t), _audit_rmr(t)) if f is not None]
    findings += _audit_independence(history.tramos) + _audit_coherence(history) + _audit_missing(history.tramos)
    findings.sort(key=lambda f: (HISTORY_SHEETS.index(f.sheet), f.fila or 0, FINDING_KINDS.index(f.kind)))
    return HistoryAudit(tuple(findings), _readiness(history), len(history.tramos), len(history.support_types),
                        len(history.inspections))


FINDING_RESULT_COLUMNS = ("hallazgo", "hoja", "fila", "id_tramo", "mensaje")


def save_history_findings(audit: HistoryAudit, path) -> Path:
    """Escribe .xlsx (hoja `Hallazgos`) o .csv, un hallazgo por fila. Es un archivo de resultados: el id_tramo y la
    fila sí van aquí (nunca en el mensaje)."""
    return write_table(path, FINDING_RESULT_COLUMNS, [(f.kind, f.sheet, f.fila, f.id_tramo, f.message)
                                                      for f in audit.findings], sheet="Hallazgos")


def history_audit_counts(audit: HistoryAudit) -> dict[str, int]:
    """Conteos de una sola fuente para la CLI, el informe y las pruebas de paridad."""
    c = Counter(f.kind for f in audit.findings)
    return {"tramos": audit.tramos, "support_types": audit.support_types, "inspections": audit.inspections,
            "findings": len(audit.findings), **{k: c.get(k, 0) for k in FINDING_KINDS},
            "items_ready": sum(r.ready for r in audit.readiness)}
