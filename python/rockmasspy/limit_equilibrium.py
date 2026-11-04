"""Equilibrio límite 2D: hojas `Geometria`, `Estratos`, `Materiales_LE`, `Analisis_LE` y `Sismos` (un .xlsx o un CSV
por hoja), evaluación por análisis y resultados (3C, tarea 6).

Cada fila de `Analisis_LE` es un análisis sobre una sección. La superficie crítica sale de `search_circular` (malla de la
fila, 20 × 20 intervalos y 11 radios), de `search_block` (sobre `linea_debil`) o es la polilínea `linea_superficie`
(`dada`); el primer método de `metodos` busca y los demás se evalúan sobre esa superficie. Con `kh` > 0 o con `registro`
se calcula ky con el primer método por vueltas (R17): búsqueda con kh = 0 y su ky, búsqueda con kh = ese ky y su ky,
hasta 4 vueltas o hasta que ky cambie menos de 1e-4; se informa el menor ky con su superficie (`yield_surface`) y los
avisos de cada búsqueda. Con superficie `dada`, ky sobre ella. Con `registro`, el Newmark de bloque rígido en los dos
sentidos con ese ky. Una piezométrica que no cubre la superficie lanza (hoja `Geometria`, columna `linea`) si el
análisis busca. Los mensajes de cada método llevan la palabra de la hoja («ordinario: ...») sin el prefijo del núcleo
y no se repiten entre métodos. Hoek-Brown: `sigma_ci_mpa` pasa a
kPa (× 1000), porque la sección va en kN y m. Una sola regla de atención (R14): FS < 1 + 1e-9 o algún aviso.
Privacidad: `id_seccion`, `id_analisis`, `material`, `registro` y los nombres de línea nunca van a un mensaje, a un aviso
ni a un repr; el archivo de resultados lleva solo `id_analisis` e `id_seccion`. Las columnas ajenas no se leen.
"""

import math
import re
from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field, fields
from pathlib import Path

from . import _rockmasspy_core as rm
from .batch import write_table
from .blocks import _floats, _word, _yes
from .csv_io import _CsvSource
from .excel_io import _open, _where
from .probabilistic import _norm, is_failure
from .slopes import _leer, _rango, _unique

GEOMETRY_SHEET = "Geometria"
LAYERS_SHEET = "Estratos"
MATERIALS_SHEET = "Materiales_LE"
ANALYSES_SHEET = "Analisis_LE"
RECORDS_SHEET = "Sismos"
LE_SHEETS = (GEOMETRY_SHEET, LAYERS_SHEET, MATERIALS_SHEET, ANALYSES_SHEET, RECORDS_SHEET)

_METHODS = {"ordinario": rm.LeMethod.Ordinary, "bishop": rm.LeMethod.Bishop, "janbu": rm.LeMethod.JanbuSimplified,
            "janbu_corregido": rm.LeMethod.JanbuCorrected, "spencer": rm.LeMethod.Spencer,
            "gle": rm.LeMethod.MorgensternPrice}
_METHOD_WORD = {v: k for k, v in _METHODS.items()}
_SURFACES = {"circular": "circular", "bloque": "block", "dada": "given"}
_SHEET_SURFACE = {v: k for k, v in _SURFACES.items()}
_FUNCTIONS = {"medio_seno": rm.InterSliceFunction.HalfSine, "constante": rm.InterSliceFunction.Constant}
_MODELS = ("mohr_coulomb", "hoek_brown")
_GROUND, _PIEZO = "superficie", "piezometrica"
_INF = math.inf


# ---------------------------------------------------------------- filas


@dataclass(frozen=True)
class GeometryRow:
    id_seccion: str = field(repr=False)
    linea: str = field(repr=False)
    x_m: float
    y_m: float
    fila: int
    hoja: str = field(default=GEOMETRY_SHEET, repr=False, compare=False)


@dataclass(frozen=True)
class LayerRow:
    id_seccion: str = field(repr=False)
    orden: int
    material: str = field(repr=False)
    linea_base: str | None = field(repr=False)
    fila: int
    hoja: str = field(default=LAYERS_SHEET, repr=False, compare=False)


@dataclass(frozen=True)
class MaterialRow:
    material: str = field(repr=False)
    modelo: str
    peso_unitario_kn_m3: float
    cohesion_kpa: float | None
    friccion_grados: float | None
    sigma_ci_mpa: float | None
    gsi: float | None
    mi: float | None
    d: float | None
    mb: float | None
    s: float | None
    a: float | None
    ru: float | None
    fila: int
    hoja: str = field(default=MATERIALS_SHEET, repr=False, compare=False)


@dataclass(frozen=True)
class AnalysisRow:
    id_analisis: str = field(repr=False)
    id_seccion: str = field(repr=False)
    metodos: str  # normalizado: palabras de la hoja separadas por ';', sin repetir
    superficie: str
    malla_x_min: float | None
    malla_x_max: float | None
    malla_y_min: float | None
    malla_y_max: float | None
    linea_debil: str | None = field(repr=False)
    linea_superficie: str | None = field(repr=False)
    base_modelo_m: float | None
    kh: float | None
    peso_agua_kn_m3: float | None
    grieta_m: float | None
    grieta_llenado: float | None
    funcion: str | None
    tajadas: float | None
    registro: str | None = field(repr=False)
    escala_registro: float | None
    fila: int
    hoja: str = field(default=ANALYSES_SHEET, repr=False, compare=False)


@dataclass(frozen=True)
class RecordRow:
    registro: str = field(repr=False)
    t_s: float
    a_g: float
    fila: int
    hoja: str = field(default=RECORDS_SHEET, repr=False, compare=False)


def _columns(cls):
    return tuple(f.name for f in fields(cls) if f.name not in ("fila", "hoja"))


GEOMETRY_COLUMNS, LAYER_COLUMNS, MATERIAL_COLUMNS, ANALYSIS_COLUMNS, RECORD_COLUMNS = (
    _columns(c) for c in (GeometryRow, LayerRow, MaterialRow, AnalysisRow, RecordRow))
_GEO_TEXT = {"id_seccion", "linea"}
_LAYER_TEXT = {"id_seccion", "material", "linea_base"}
_MAT_TEXT = {"material", "modelo"}
_AN_TEXT = {"id_analisis", "id_seccion", "metodos", "superficie", "linea_debil", "linea_superficie", "funcion",
            "registro"}
_REC_TEXT = {"registro"}

# columna: (mínimo, máximo, mínimo abierto, máximo abierto)
_MAT_RANGES = {
    "peso_unitario_kn_m3": (0, _INF, True, False), "cohesion_kpa": (0, _INF, False, False),
    "friccion_grados": (0, 90, False, True), "sigma_ci_mpa": (0, _INF, True, False), "gsi": (0, 100, True, False),
    "mi": (0, _INF, True, False), "d": (0, 1, False, False), "mb": (0, _INF, True, False), "s": (0, 1, False, False),
    "a": (0, 1, True, False), "ru": (0, 1, False, True),
}
_AN_RANGES = {
    "kh": (0, 1, False, False), "peso_agua_kn_m3": (0, _INF, True, False), "grieta_m": (0, _INF, True, False),
    "grieta_llenado": (0, 1, False, False), "tajadas": (5, _INF, False, False),
    "escala_registro": (0, _INF, True, False),
}
_AN_REQUIRED = {"circular": ("malla_x_min", "malla_x_max", "malla_y_min", "malla_y_max"),
                "bloque": ("linea_debil",), "dada": ("linea_superficie",)}


def _ranges(vals, sheet, n, ranges):
    for c, (lo, hi, lo_open, hi_open) in ranges.items():
        _rango(vals, sheet, n, c, lo, hi, lo_open=lo_open, hi_open=hi_open)


def _geometry(vals, n, sheet):
    _floats(vals, _GEO_TEXT, sheet, n)
    return GeometryRow(**vals, fila=n, hoja=sheet)


def _layer(vals, n, sheet):
    _floats(vals, _LAYER_TEXT, sheet, n)
    if not vals["orden"].is_integer() or vals["orden"] < 1:
        raise ValueError(f"{_where(sheet, n, 'orden')}: must be a whole number >= 1")
    vals["orden"] = int(vals["orden"])
    return LayerRow(**vals, fila=n, hoja=sheet)


def _material(vals, n, sheet):
    def bad(c, motivo):
        raise ValueError(f"{_where(sheet, n, c)}: {motivo}")

    _floats(vals, _MAT_TEXT, sheet, n)
    vals["modelo"] = _word(vals["modelo"])
    if vals["modelo"] not in _MODELS:
        bad("modelo", f"must be one of {', '.join(_MODELS)}")
    _ranges(vals, sheet, n, _MAT_RANGES)
    if vals["modelo"] == "mohr_coulomb":
        for c in ("cohesion_kpa", "friccion_grados"):
            if vals[c] is None:
                bad(c, "required for model 'mohr_coulomb'")
    else:
        if vals["sigma_ci_mpa"] is None:
            bad("sigma_ci_mpa", "required for model 'hoek_brown'")
        by_gsi = any(vals[c] is not None for c in ("gsi", "mi", "d"))
        by_constants = any(vals[c] is not None for c in ("mb", "s", "a"))
        if by_gsi and by_constants:
            bad("mb", "give either gsi and mi (and d) or mb, s and a, not both")
        if not by_gsi and not by_constants:
            bad("gsi", "required for model 'hoek_brown': give gsi and mi, or mb, s and a")
        for c in ("gsi", "mi") if by_gsi else ("mb", "s", "a"):
            if vals[c] is None:
                bad(c, "give gsi and mi together" if by_gsi else "give mb, s and a together")
    return MaterialRow(**vals, fila=n, hoja=sheet)


def _analysis(vals, n, sheet):
    def bad(c, motivo):
        raise ValueError(f"{_where(sheet, n, c)}: {motivo}")

    _floats(vals, _AN_TEXT, sheet, n)
    words = [_word(w) for w in vals["metodos"].split(";")]
    if any(w not in _METHODS for w in words):
        bad("metodos", f"must be a ';'-separated list of {', '.join(_METHODS)}")
    vals["metodos"] = ";".join(dict.fromkeys(words))
    vals["superficie"] = _word(vals["superficie"])
    if vals["superficie"] not in _SURFACES:
        bad("superficie", f"must be one of {', '.join(_SURFACES)}")
    _ranges(vals, sheet, n, _AN_RANGES)
    for c in _AN_REQUIRED[vals["superficie"]]:
        if vals[c] is None:
            bad(c, f"required for superficie '{vals['superficie']}'")
    if vals["superficie"] == "circular":
        for a, b in (("malla_x_min", "malla_x_max"), ("malla_y_min", "malla_y_max")):
            if vals[b] <= vals[a]:
                bad(b, f"must be greater than {a}")
    if vals["tajadas"] is not None and not vals["tajadas"].is_integer():
        bad("tajadas", "must be a whole number")
    if vals["grieta_llenado"] is not None and vals["grieta_m"] is None:
        bad("grieta_m", "required when grieta_llenado is given")
    if vals["escala_registro"] is not None and vals["registro"] is None:
        bad("registro", "required when escala_registro is given")
    if vals["funcion"] is not None:
        vals["funcion"] = _word(vals["funcion"])
        if vals["funcion"] not in _FUNCTIONS:
            bad("funcion", f"must be one of {', '.join(_FUNCTIONS)}")
    return AnalysisRow(**vals, fila=n, hoja=sheet)


def _record(vals, n, sheet):
    _floats(vals, _REC_TEXT, sheet, n)
    return RecordRow(**vals, fila=n, hoja=sheet)


# ---------------------------------------------------------------- lectura y cruces


@dataclass(frozen=True)
class Accelerogram:
    """Registro de aceleraciones (en g) con paso constante; la primera muestra está en t = 0."""

    dt_s: float
    acceleration_g: tuple[float, ...]

    @property
    def time_s(self) -> tuple[float, ...]:
        return tuple(i * self.dt_s for i in range(len(self.acceleration_g)))


@dataclass(frozen=True)
class LeInputs:
    """Filas validadas de las cinco hojas (los cruces entre hojas ya revisados)."""

    geometry: tuple[GeometryRow, ...]
    layers: tuple[LayerRow, ...]
    materials: tuple[MaterialRow, ...]
    analyses: tuple[AnalysisRow, ...]
    records: tuple[RecordRow, ...] = ()


def _group(rows, key):
    out: dict = {}
    for r in rows:
        out.setdefault(key(r), []).append(r)
    return out


def _accelerograms(records, count_column: str = "registro") -> dict[str, Accelerogram]:
    """Un registro por id, en el orden de las filas: t empieza en 0, crece y con paso constante (1e-6·dt).

    `count_column` es la columna del error «at least two samples» (`t_s` en un CSV de dos columnas, sin `registro`).
    """
    out = {}
    for name, rows in _group(records, lambda r: r.registro).items():
        def bad(r, c, motivo):
            raise ValueError(f"{_where(r.hoja, r.fila, c)}: {motivo}")

        if rows[0].t_s != 0:
            bad(rows[0], "t_s", "the first time of a record must be 0")
        if len(rows) < 2:
            bad(rows[0], count_column, "a record needs at least two samples")
        dt = rows[1].t_s - rows[0].t_s
        for prev, r in zip(rows, rows[1:]):
            step = r.t_s - prev.t_s
            if step <= 0:
                bad(r, "t_s", "times must increase")
            if abs(step - dt) > 1e-6 * dt:
                bad(r, "t_s", "the time step must be constant")
        out[name] = Accelerogram((rows[-1].t_s - rows[0].t_s) / (len(rows) - 1), tuple(r.a_g for r in rows))
    return out


@dataclass
class _Section:
    lines: dict  # nombre -> [Point2]
    rows: dict = field(default_factory=dict)  # nombre -> filas de Geometria (para los errores)
    ground: str | None = None
    piezometric: str | None = None
    layers: list = field(default_factory=list)


def _index(inp: LeInputs):
    """Cruces entre hojas, todos antes de evaluar: secciones, materiales y registros listos para el núcleo."""
    sections: dict[str, _Section] = {}
    for (sec, name), rows in _group(inp.geometry, lambda r: (r.id_seccion, r.linea)).items():
        if len(rows) < 2:
            raise ValueError(f"{_where(rows[0].hoja, rows[0].fila, 'linea')}: a line needs at least two vertices")
        for prev, r in zip(rows, rows[1:]):
            if r.x_m <= prev.x_m:
                raise ValueError(f"{_where(r.hoja, r.fila, 'x_m')}: x must increase along the line")
        s = sections.setdefault(sec, _Section({}))
        s.lines[name] = [rm.Point2(r.x_m, r.y_m) for r in rows]
        s.rows[name] = rows
        word = _word(name)
        if word == _GROUND:
            s.ground = name
        elif word == _PIEZO:
            s.piezometric = name
    materials = {m.material: m for m in inp.materials}
    for sec, rows in _group(inp.layers, lambda r: r.id_seccion).items():
        def bad(r, c, motivo):
            raise ValueError(f"{_where(r.hoja, r.fila, c)}: {motivo}")

        s = sections.get(sec)
        if s is None:
            bad(rows[0], "id_seccion", "no section with this id in Geometria")
        rows = sorted(rows, key=lambda r: r.orden)
        for k, r in enumerate(rows, start=1):
            if r.orden != k:
                bad(r, "orden", "layers of a section must be numbered 1, 2, ... without gaps or repeats")
            if r.material not in materials:
                bad(r, "material", "no material with this name in Materiales_LE")
            if r.linea_base is None:
                if k != len(rows):
                    bad(r, "linea_base", "required except in the last layer")
            elif r.linea_base not in s.lines:
                bad(r, "linea_base", "no line with this name in Geometria for this id_seccion")
        s.layers = rows
    accs = _accelerograms(inp.records)
    for a in inp.analyses:
        def bad(c, motivo):
            raise ValueError(f"{_where(a.hoja, a.fila, c)}: {motivo}")

        s = sections.get(a.id_seccion)
        if s is None or s.ground is None:
            bad("id_seccion", "no 'superficie' line in Geometria for this id_seccion")
        if not s.layers:
            bad("id_seccion", "no layers in Estratos for this id_seccion")
        for c in ("linea_debil", "linea_superficie"):
            if getattr(a, c) is not None and getattr(a, c) not in s.lines:
                bad(c, "no line with this name in Geometria for this id_seccion")
        if a.registro is not None and a.registro not in accs:
            bad("registro", "no record with this id in Sismos")
        if a.base_modelo_m is not None and a.base_modelo_m >= min(p.y for p in s.lines[s.ground]):
            bad("base_modelo_m", "must be below the ground surface")
        if a.superficie != "dada" and s.piezometric is not None:
            # una piezométrica corta descartaría en silencio las superficies que la cruzan (como en el núcleo)
            g, p = s.lines[s.ground], s.lines[s.piezometric]
            short_start = p[0].x > g[0].x + 1e-9
            if short_start or p[-1].x < g[-1].x - 1e-9:
                r = s.rows[s.piezometric][0 if short_start else -1]
                raise ValueError(f"{_where(r.hoja, r.fila, 'linea')}: the piezometric line must cover the x range of "
                                 "the ground surface for a slip surface search")
    return sections, materials, accs


def _source(source, sheets):
    """(fuente de hojas, {hoja: nombre en la fuente}, cierre)."""
    if isinstance(source, Mapping):
        unknown = sorted(set(source) - set(LE_SHEETS))
        if unknown:
            raise ValueError(f"source: unknown sheet {unknown[0]!r}; expected some of {', '.join(LE_SHEETS)}")
        for s, p in source.items():
            if Path(p).suffix.lower() != ".csv":
                raise ValueError(f"source: the file for sheet '{s}' must be a .csv")
        return _CsvSource({s: Path(p) for s, p in source.items()}), {s: s for s in LE_SHEETS}, None
    p = Path(source)
    if p.suffix.lower() != ".xlsx":
        raise ValueError(f"{p.name}: expected a .xlsx workbook or a dict {{sheet: csv path}}")
    names = {s: s for s in LE_SHEETS}
    for k, v in (sheets or {}).items():
        if k not in names:
            raise ValueError(f"sheets: unknown sheet {k!r}; expected some of {', '.join(LE_SHEETS)}")
        names[k] = v
    wb = _open(p)
    return wb, names, wb.wb.close


def load_le_inputs(source, *, sheets: Mapping[str, str] | None = None) -> LeInputs:
    """Lee y valida las cinco hojas: un .xlsx (con `sheets` para otros nombres de hoja) o un dict {hoja: ruta .csv}.

    `Sismos` solo hace falta si algún análisis nombra un `registro`. Un dato mal escrito lanza con hoja, fila y columna.
    """
    src, names, close = _source(source, sheets)
    try:
        def leer(sheet, columns, text, required, id_column, build):
            return tuple(_leer(src, names[sheet], None, columns, text, required, id_column, build))

        geo = leer(GEOMETRY_SHEET, GEOMETRY_COLUMNS, _GEO_TEXT, GEOMETRY_COLUMNS, None, _geometry)
        lay = leer(LAYERS_SHEET, LAYER_COLUMNS, _LAYER_TEXT, ("id_seccion", "orden", "material"), None, _layer)
        mat = leer(MATERIALS_SHEET, MATERIAL_COLUMNS, _MAT_TEXT, ("material", "modelo", "peso_unitario_kn_m3"),
                   "material", _material)
        an = leer(ANALYSES_SHEET, ANALYSIS_COLUMNS, _AN_TEXT, ("id_analisis", "id_seccion", "metodos", "superficie"),
                  "id_analisis", _analysis)
        rec = ()
        need = next((a for a in an if a.registro is not None), None)
        if need is not None and names[RECORDS_SHEET] not in src.sheetnames:
            raise ValueError(f"{_where(need.hoja, need.fila, 'registro')}: no accelerogram given "
                             "(use --records or a Sismos sheet)")
        if need is not None or names[RECORDS_SHEET] in src.sheetnames:
            rec = leer(RECORDS_SHEET, RECORD_COLUMNS, _REC_TEXT, RECORD_COLUMNS, None, _record)
    finally:
        if close is not None:
            close()
    inp = LeInputs(geo, lay, mat, an, rec)
    _index(inp)
    return inp


def read_accelerogram(path, *, sheet: str = RECORDS_SHEET) -> dict[str, Accelerogram]:
    """Registros de `Sismos` ({registro: Accelerogram}) de un .xlsx o un .csv.

    Un .csv sin columna `registro` (solo `t_s` y `a_g`) es un único registro con el nombre del archivo sin .csv. Una
    hoja sin muestras (solo la cabecera) lanza.
    """
    def some(out, name):
        if not out:
            raise ValueError(f"sheet '{name}': no samples (only the header)")
        return out

    p = Path(path)
    if p.suffix.lower() == ".csv":
        src = _CsvSource({p.stem: p})
        head = {str(h).strip().casefold() for h in (src.rows(p.stem) or [[]])[0]}
        if "registro" not in head:
            rows = _leer(src, p.stem, None, ("t_s", "a_g"), set(), ("t_s", "a_g"), None,
                         lambda v, n, s: _record({"registro": p.stem, **v}, n, s))
            return some(_accelerograms(rows, count_column="t_s"), p.stem)
        return some(_accelerograms(_leer(src, p.stem, None, RECORD_COLUMNS, _REC_TEXT, RECORD_COLUMNS, None, _record)),
                    p.stem)
    if p.suffix.lower() != ".xlsx":
        raise ValueError(f"{p.name}: unsupported file type '{p.suffix}'; save it as .xlsx or .csv")
    wb = _open(p)
    try:
        return some(_accelerograms(_leer(wb, sheet, None, RECORD_COLUMNS, _REC_TEXT, RECORD_COLUMNS, None, _record)),
                    sheet)
    finally:
        wb.wb.close()


# ---------------------------------------------------------------- evaluación


@dataclass(frozen=True)
class LeAnalysisResult:
    id_analisis: str = field(repr=False)
    id_seccion: str = field(repr=False)
    order: int
    surface_type: str  # circular, block o given
    results: tuple  # rm.LeResult, uno por método, sobre la superficie crítica del primero
    search: "rm.SearchResult | None"
    yield_: "rm.YieldResult | None"
    newmark: "rm.NewmarkResult | None"
    warnings: tuple[str, ...]
    notes: tuple[str, ...]
    methods: tuple
    surface: "rm.SlipSurface | None" = field(default=None, repr=False)  # la crítica (para la figura)
    section: "rm.LeSection | None" = field(default=None, repr=False)
    record: "Accelerogram | None" = field(default=None, repr=False)  # el registro escalado que usó Newmark
    yield_surface: "rm.SlipSurface | None" = field(default=None, repr=False)  # la de ky (R17), si se calculó
    # con kh > 0: los mismos métodos con kh = 0 sobre `surface`, paralelo a `results`; con kh = 0, vacío
    static_results: tuple = field(default=(), repr=False)

    @property
    def kh(self) -> float | None:
        return None if self.section is None else self.section.kh

    @property
    def ky_on_critical(self) -> bool:
        """ky se calculó sobre la superficie crítica (la que se dibuja); con R17 puede ser otra, la crítica sísmica."""
        return _same_surface(self.yield_surface, self.surface)

    @property
    def fs_min(self) -> float | None:
        fs = [r.factor_of_safety for r in self.results if r.factor_of_safety is not None]
        return min(fs) if fs else None

    @property
    def needs_attention(self) -> bool:
        return bool(le_attention(self))


def le_attention(r: LeAnalysisResult) -> list[str]:
    """Única regla de atención (R14): el menor FS < 1 + 1e-9 o algún aviso. ky y Newmark se informan sin juzgar."""
    out = []
    if r.fs_min is not None and is_failure(r.fs_min):
        out.append("att_le_fs_below_1")
    if r.warnings:
        out.append("att_le_warnings")
    return out


def _le_material(m: MaterialRow, methods: list, warnings: list) -> "rm.LeMaterial":
    x = rm.LeMaterial()
    x.unit_weight, x.ru = m.peso_unitario_kn_m3, m.ru or 0.0
    if m.modelo == "mohr_coulomb":
        x.cohesion, x.friction_deg = m.cohesion_kpa, m.friccion_grados
        return x
    hb = (rm.hb_params(m.gsi, m.mi, m.d or 0.0) if m.gsi is not None
          else rm.hb_params_from_constants(m.mb, m.s, m.a))
    x.model, x.hb, x.sigma_ci = rm.StrengthModel.HoekBrown, hb, m.sigma_ci_mpa * 1000.0  # MPa -> kPa
    methods.append(hb.info)
    warnings += [f"Hoek-Brown: {w}" for w in hb.warnings]
    return x


def _section(s: _Section, a: AnalysisRow, materials, kh, methods, warnings) -> "rm.LeSection":
    sec = rm.LeSection()
    sec.surface = s.lines[s.ground]
    index, mats, layers = {}, [], []
    for r in s.layers:
        if r.material not in index:
            index[r.material] = len(mats)
            mats.append(_le_material(materials[r.material], methods, warnings))
        lay = rm.LeLayer()
        lay.bottom, lay.material = (s.lines[r.linea_base] if r.linea_base is not None else []), index[r.material]
        layers.append(lay)
    sec.layers, sec.materials = layers, mats
    sec.model_base_y = a.base_modelo_m
    if s.piezometric is not None:
        sec.piezometric = s.lines[s.piezometric]
    sec.water_unit_weight = 9.81 if a.peso_agua_kn_m3 is None else a.peso_agua_kn_m3
    sec.kh = kh
    if a.grieta_m is not None:
        c = rm.LeTensionCrack()
        c.depth_m, c.water_fill = a.grieta_m, a.grieta_llenado or 0.0
        sec.crack = c
    return sec


def _search(a: AnalysisRow, s: _Section, sec, options):
    if a.superficie == "circular":
        g = rm.CircularGrid()
        g.x_min, g.x_max, g.y_min, g.y_max = a.malla_x_min, a.malla_x_max, a.malla_y_min, a.malla_y_max
        g.nx, g.ny, g.n_radii = 20, 20, 11
        return rm.search_circular(sec, g, options)
    b = rm.BlockSearch()
    b.weak_line = s.lines[a.linea_debil]
    return rm.search_block(sec, b, options)


def _has_surface(f) -> bool:
    return f is not None and (f.circle is not None or f.polyline is not None)


def _same_surface(a, b) -> bool:
    if a is None or b is None:
        return a is b
    if a.circle is not None or b.circle is not None:
        return (a.circle is not None and b.circle is not None
                and (a.circle.xc, a.circle.yc, a.circle.radius) == (b.circle.xc, b.circle.yc, b.circle.radius))
    return [(p.x, p.y) for p in a.polyline or []] == [(p.x, p.y) for p in b.polyline or []]


# prefijos de método: el del núcleo («Ordinary: ...») y el de la hoja («ordinario: ...»)
_CORE_NAMES = "Ordinary|Bishop|Janbu simplified|Janbu corrected|Spencer|Morgenstern-Price"
_CORE_PREFIX = re.compile(rf"^({_CORE_NAMES}): ")
_CORE_NAMED = re.compile(rf"^({_CORE_NAMES}) ")  # «Spencer did not converge»: ya nombra su método
_WORD_PREFIX = re.compile(rf"^({'|'.join(_METHODS)}): ")


def _add_messages(out: list, word: str, messages) -> None:
    """Agrega «<método>: mensaje» sin el prefijo del núcleo, si el mensaje sin prefijo no está ya (de otro método o de
    la búsqueda). Un mensaje que ya empieza con el nombre de su método va tal cual, sin la palabra de la hoja."""
    seen = {_WORD_PREFIX.sub("", x) for x in out}
    for m in messages:
        m = _CORE_PREFIX.sub("", m)
        if m not in seen:
            out.append(m if _CORE_NAMED.match(m) else f"{word}: {m}")
            seen.add(m)


def _ky(msg: str) -> str:
    return f"ky: {msg.removeprefix('ky ')}"  # «ky: ky not found: ...» -> «ky: not found: ...»


_KY_ROUNDS, _KY_CHANGE = 4, 1e-4
_KY_OTHER_NOTE = "ky computed on a different slip surface (the one with the lowest ky), not on the critical one shown"
_KY_ROUNDS_NOTE = ("ky: up to 4 rounds, searching first with kh = 0 and then with kh = the last ky, until ky changes "
                   "by less than 1e-4; the lowest ky found and its slip surface are reported")


def _yield_rounds(a, s, materials, static, so, opts, method, surface, warnings, *, searched):
    """ky por vueltas (R17): la crítica estática no es la de menor ky, así que se busca con kh = 0, se calcula ky, se
    busca otra vez con kh = ky y se recalcula, hasta 4 vueltas o hasta que ky cambie menos de 1e-4. Devuelve el menor ky
    con su superficie. `surface` es la crítica con kh = 0 si `searched` (la búsqueda principal ya fue sin sismo)."""
    def search(kh):
        found = _search(a, s, _section(s, a, materials, kh, [], []) if kh else static, so)
        warnings.extend(f"ky search: {w}" for w in found.warnings if w not in warnings)  # sin repetir la principal
        return found.surface if _has_surface(found.surface) else None

    best = best_surface = prev = None
    kh = 0.0
    for k in range(_KY_ROUNDS):
        if k or not searched:
            surface = search(kh)
        if surface is None:
            break
        y = rm.le_yield_coefficient(static, surface, method, opts)
        warnings.extend(_ky(w) for w in y.warnings)
        if best is None or (y.ky is not None and (best.ky is None or y.ky < best.ky)):
            best, best_surface = y, surface
        if y.ky is None or y.ky <= 0 or (prev is not None and abs(y.ky - prev) < _KY_CHANGE):
            break
        prev = kh = y.ky
    return best, best_surface


def _assess_one(order, a: AnalysisRow, s: _Section, materials, accs):
    methods_le = [_METHODS[w] for w in a.metodos.split(";")]
    first = methods_le[0]
    warnings, notes, methods = [], [], []
    kh = a.kh or 0.0
    sec = _section(s, a, materials, kh, methods, warnings)
    opts = rm.LeOptions()
    opts.n_slices = 50 if a.tajadas is None else int(a.tajadas)
    opts.function = _FUNCTIONS[a.funcion or "medio_seno"]
    so = rm.SearchOptions()
    so.method, so.le = first, opts

    search = None
    if a.superficie == "dada":
        surface = rm.SlipSurface()
        surface.polyline = s.lines[a.linea_superficie]
    else:
        search = _search(a, s, sec, so)
        surface = search.surface if _has_surface(search.surface) else None
        warnings += search.warnings
        notes += search.notes
        methods.append(search.info)
    if surface is None:  # la búsqueda no encontró ninguna superficie válida: solo queda su resultado vacío
        results = (search.best,)
    else:
        results = tuple(rm.le_factor_of_safety(sec, surface, m, opts) for m in methods_le)
    for m, r in zip(methods_le, results):
        _add_messages(warnings, _METHOD_WORD[m], r.warnings)
        _add_messages(notes, _METHOD_WORD[m], r.notes)
        methods.append(r.info)

    yld = nm = record = ysurf = None
    static_results = ()
    if kh > 0 or a.registro is not None:
        static = _section(s, a, materials, 0.0, [], [])  # le_yield_coefficient reemplaza el kh de la sección
        if kh > 0 and surface is not None:  # el FS sin sismo sobre la misma superficie, con cada método
            static_results = tuple(rm.le_factor_of_safety(static, surface, m, opts) for m in methods_le)
            for m, r in zip(methods_le, static_results):
                _add_messages(warnings, _METHOD_WORD[m], r.warnings)
        if search is None:  # superficie dada: ky sobre ella
            ysurf = surface
            yld = rm.le_yield_coefficient(static, surface, first, opts)
            warnings += [_ky(w) for w in yld.warnings]
        else:
            yld, ysurf = _yield_rounds(a, s, materials, static, so, opts, first, surface, warnings, searched=kh == 0)
            if yld is not None and yld.ky is not None:
                notes.append(_KY_ROUNDS_NOTE)
                if not _same_surface(ysurf, surface):
                    notes.append(_KY_OTHER_NOTE)
        if yld is None:
            notes.append("ky not computed: no valid static slip surface")
        else:
            notes += [_ky(t) for t in yld.notes]
            methods.append(yld.info)
    if a.registro is not None:
        if yld is None or yld.ky is None:
            notes.append("Newmark not run: ky not found")
        elif yld.ky <= 0:
            notes.append("Newmark not run: ky is 0 (static factor of safety at or below 1)")
        else:
            acc = accs[a.registro]
            ni = rm.NewmarkInput()
            ni.dt_s, ni.acceleration_g, ni.ky = acc.dt_s, list(acc.acceleration_g), yld.ky
            ni.scale = 1.0 if a.escala_registro is None else a.escala_registro
            ni.both_directions = True
            nm = rm.newmark_rigid_block(ni)
            record = Accelerogram(acc.dt_s, tuple(ni.scale * x for x in acc.acceleration_g))
            warnings += [f"newmark: {w}" for w in nm.warnings]
            notes += [f"newmark: {t}" for t in nm.notes]
            methods.append(nm.info)
    uniq = {m.method_id: m for m in methods}
    return LeAnalysisResult(a.id_analisis, a.id_seccion, order, _SURFACES[a.superficie], results, search, yld, nm,
                            _unique(warnings), _unique(notes), tuple(uniq.values()), surface, sec, record, ysurf,
                            static_results)


# nombres del núcleo que pueden salir en un error -> columna de Analisis_LE
_ERR_NAMES = {"model_base_y": "base_modelo_m", "water_unit_weight": "peso_agua_kn_m3", "crack.depth_m": "grieta_m",
              "crack.water_fill": "grieta_llenado", "n_slices": "tajadas", "weak_line": "linea_debil",
              "polyline": "linea_superficie", "slip_surface": "linea_superficie", "grid.x_min": "malla_x_min",
              "grid.x_max": "malla_x_max",
              "grid.y_min": "malla_y_min", "grid.y_max": "malla_y_max", "scale": "escala_registro"}


def _clean(msg: str) -> str:
    """Mensaje del núcleo para el usuario: sin «Received:», sin el prefijo del núcleo y con las columnas de la hoja."""
    msg = msg.split("Received:")[0].strip()
    msg = re.sub(r"Domain error \[RockMassPy\]:\s*(parameter\s+)?", "", msg)
    pat = "|".join(re.escape(k) for k in sorted(_ERR_NAMES, key=len, reverse=True))
    return re.sub(rf"(?<![\w.])({pat})(?![\w])", lambda m: _ERR_NAMES[m.group(1)], msg)


def assess_le(source, *, sheets: Mapping[str, str] | None = None,
              progress: Callable[[int, int], None] | None = None) -> list[LeAnalysisResult]:
    """Evalúa cada fila de `Analisis_LE` (ver la cabecera del módulo). Un dato imposible lanza con hoja y fila.

    `progress(k, n)` se llama antes de evaluar el análisis k de n (con las hojas ya validadas).
    """
    inp = load_le_inputs(source, sheets=sheets)
    sections, materials, accs = _index(inp)
    out = []
    for order, a in enumerate(inp.analyses, start=1):
        if progress is not None:
            progress(order, len(inp.analyses))
        try:
            out.append(_assess_one(order, a, sections[a.id_seccion], materials, accs))
        except ValueError as e:
            raise ValueError(f"sheet '{a.hoja}', row {a.fila}: {_clean(str(e))}") from None
    return out


# ---------------------------------------------------------------- conteos y resultados


_COUNTS = ("analyses", "with_fs", "fs_below_1", "circular", "block", "given", "with_newmark", "warnings", "notes")


def le_counts(results: Iterable[LeAnalysisResult]) -> dict[str, int]:
    """Conteos de una sola fuente para la CLI, el informe y las pruebas de paridad."""
    out = dict.fromkeys(_COUNTS, 0)
    for r in results:
        out["analyses"] += 1
        out["with_fs"] += r.fs_min is not None
        out["fs_below_1"] += "att_le_fs_below_1" in le_attention(r)
        out[r.surface_type] += 1
        out["with_newmark"] += r.newmark is not None
        out["warnings"] += len(r.warnings)
        out["notes"] += len(r.notes)
    return out


def le_warning_counts(results: Iterable[LeAnalysisResult]) -> Counter:
    """Avisos agrupados entre análisis (sin el conteo del núcleo), para la CLI y el informe."""
    return Counter(w for r in results for w in {_norm(x) for x in r.warnings})


RESULT_COLUMNS = ("id_analisis", "id_seccion", "superficie", "metodo", "kh", "fs", "fs_estatico",
                  "fs_menor_o_igual_1", "lambda", "convergio", "xc_m", "yc_m", "radio_m", "puntos_superficie",
                  "evaluadas", "descartadas", "ky", "desplazamiento_newmark_m", "avisos", "notas")


def _points(f) -> str | None:
    if f is None or f.polyline is None:
        return None
    return "; ".join(f"{p.x:.3f} {p.y:.3f}" for p in f.polyline)


def le_static_fs(r: LeAnalysisResult) -> list:
    """FS sin sismo de cada método, paralelo a `results`: con kh > 0 el de `static_results`; con kh = 0, el mismo FS."""
    return [x.factor_of_safety for x in (r.static_results or r.results)]


def save_le_results(results: Iterable[LeAnalysisResult], path) -> Path:
    """Escribe .xlsx (hoja `Analisis_LE_resultados`) o .csv, una fila por método. Lleva id_analisis e id_seccion.

    ky y el desplazamiento de Newmark van solo en la fila del primer método, que es el que los calcula.
    """
    rows = []
    for r in results:
        c = r.surface.circle if r.surface is not None else None
        s, y, nm = r.search, r.yield_, r.newmark
        ky_nm = [None if y is None else y.ky, None if nm is None else nm.displacement_m]
        for k, (x, fs0) in enumerate(zip(r.results, le_static_fs(r))):
            fs = x.factor_of_safety
            rows.append([r.id_analisis, r.id_seccion, _SHEET_SURFACE[r.surface_type], _METHOD_WORD[x.method], r.kh,
                         fs, fs0, None if fs is None else _yes(is_failure(fs)), x.lambda_, _yes(x.converged),
                         None if c is None else c.xc, None if c is None else c.yc, None if c is None else c.radius,
                         _points(r.surface), None if s is None else s.evaluated, None if s is None else s.discarded,
                         *(ky_nm if k == 0 else [None, None]), " | ".join(r.warnings), " | ".join(r.notes)])
    return write_table(path, RESULT_COLUMNS, rows, sheet="Analisis_LE_resultados")
