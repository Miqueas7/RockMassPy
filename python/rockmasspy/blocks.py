"""Bloques de talud: hojas `Bloques` y `Distribuciones` (CSV o Excel), evaluación por bloque y resultados (3B, tarea 6).

Cada fila de `Bloques` es un análisis (planar, cuña, volteo o berma) ligado a un talud de la 3A por `id_talud`: toma la
cara del talud y la orientación media (Fisher) de sus familias; `Taludes` no gana columnas (R15). `Distribuciones` da
las variables aleatorias de cada bloque. Una sola regla de atención (R14): FS determinístico < 1 + 1e-9 o algún aviso.
`id_bloque` e `id_talud` van al archivo de resultados, nunca a un mensaje ni a un repr; los nombres de familia tampoco.
"""

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, fields
from pathlib import Path

from . import _rockmasspy_core as rm
from .batch import write_table
from .excel_io import _where
from .intact_rock import _strip
from .probabilistic import PROBABILISTIC_INFO, Distribution, ProbabilisticResult, is_failure, run_probabilistic, sample
from .slopes import _AXIS_TOL, SlopeResult, _cargar, _delta, _rango, _unique

BLOCKS_SHEET = "Bloques"
DISTRIBUTIONS_SHEET = "Distribuciones"
_MODELS = {"planar": "planar", "cuna": "wedge", "volteo": "toppling", "berma": "berm"}
_SHEET_MODEL = {v: k for k, v in _MODELS.items()}
_EPS = 1e-9
_BACK_FRICTION = [10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0]  # R19
_LATERAL_WARNING = ("planar block: the plane dip direction differs from the face by more than the lateral limit "
                    "(2D analysis)")


# ---------------------------------------------------------------- lectura


@dataclass(frozen=True)
class BlockRow:
    id_bloque: str = field(repr=False)
    id_talud: str = field(repr=False)
    modelo: str
    altura_m: float | None
    peso_unitario_kn_m3: float | None
    peso_agua_kn_m3: float | None
    familia_1: str | None = field(repr=False)
    familia_2: str | None = field(repr=False)
    cohesion_1_kpa: float | None
    friccion_1_grados: float | None
    cohesion_2_kpa: float | None
    friccion_2_grados: float | None
    dist_grieta_m: float | None
    llenado_agua: float | None
    presion_1_kpa: float | None
    presion_2_kpa: float | None
    kh: float | None
    perno_kn_m: float | None
    perno_inclinacion_grados: float | None
    perno_tipo: str | None
    carga_kn: float | None
    carga_angulo_grados: float | None
    carga_tendencia_grados: float | None
    carga_inmersion_grados: float | None
    buz_sup_grados: float | None
    dir_sup_grados: float | None
    ancho_bloque_m: float | None
    buz_base_grados: float | None
    a1_m: float | None
    a2_m: float | None
    b_m: float | None
    n_bloques: float | None
    bloque_cresta: float | None
    soporte_kn_m: float | None
    soporte_inclinacion_grados: float | None
    soporte_altura_m: float | None
    altura_banco_m: float | None
    ancho_berma_m: float | None
    ancho_requerido_m: float | None
    retroanalisis: str | None
    fila: int
    hoja: str = field(default=BLOCKS_SHEET, repr=False, compare=False)


_KINDS = {"normal": "normal", "exponencial": "exponential", "uniforme": "uniform"}


@dataclass(frozen=True)
class DistributionRow:
    id_bloque: str = field(repr=False)
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
        return Distribution(_KINDS[self.distribucion], self.minimo, self.maximo, self.media, self.desviacion)


BLOCK_COLUMNS = tuple(f.name for f in fields(BlockRow) if f.name not in ("fila", "hoja"))
DISTRIBUTION_COLUMNS = tuple(f.name for f in fields(DistributionRow) if f.name not in ("fila", "hoja"))
_BLOCK_TEXT = {"id_bloque", "id_talud", "modelo", "familia_1", "familia_2", "perno_tipo", "retroanalisis"}
_DIST_TEXT = {"id_bloque", "variable", "distribucion"}

_INF = math.inf
# columna: (mínimo, máximo, mínimo abierto, máximo abierto); b_m solo debe ser finito
_RANGES = {
    "altura_m": (0, _INF, True, False), "peso_unitario_kn_m3": (0, _INF, True, False),
    "peso_agua_kn_m3": (0, _INF, True, False), "cohesion_1_kpa": (0, _INF, False, False),
    "cohesion_2_kpa": (0, _INF, False, False), "friccion_1_grados": (0, 90, False, True),
    "friccion_2_grados": (0, 90, False, True), "dist_grieta_m": (0, _INF, False, False),
    "llenado_agua": (0, 1, False, False), "presion_1_kpa": (0, _INF, False, False),
    "presion_2_kpa": (0, _INF, False, False), "kh": (0, 1, False, False), "perno_kn_m": (0, _INF, False, False),
    "perno_inclinacion_grados": (-90, 90, False, False), "carga_kn": (0, _INF, False, False),
    "carga_angulo_grados": (-180, 180, True, False), "carga_tendencia_grados": (0, 360, False, False),
    "carga_inmersion_grados": (0, 90, False, False), "buz_sup_grados": (0, 90, False, False),
    "dir_sup_grados": (0, 360, False, False), "ancho_bloque_m": (0, _INF, True, False),
    "buz_base_grados": (0, 90, True, True), "a1_m": (0, _INF, False, False), "a2_m": (0, _INF, False, False),
    "n_bloques": (1, _INF, False, False), "bloque_cresta": (1, _INF, False, False),
    "soporte_kn_m": (0, _INF, False, False), "soporte_inclinacion_grados": (-90, 90, True, True),
    "soporte_altura_m": (0, _INF, True, False), "altura_banco_m": (0, _INF, True, False),
    "ancho_berma_m": (0, _INF, False, False), "ancho_requerido_m": (0, _INF, False, False),
}
_REQUIRED = {
    "planar": ("altura_m", "peso_unitario_kn_m3", "familia_1", "cohesion_1_kpa", "friccion_1_grados"),
    "wedge": ("altura_m", "peso_unitario_kn_m3", "familia_1", "familia_2", "cohesion_1_kpa", "friccion_1_grados",
              "cohesion_2_kpa", "friccion_2_grados"),
    "toppling": ("peso_unitario_kn_m3", "friccion_1_grados", "ancho_bloque_m", "buz_base_grados", "a1_m", "a2_m",
                 "b_m", "n_bloques", "bloque_cresta"),
    "berm": ("altura_banco_m", "ancho_berma_m"),
}
# con una de estas, las demás (perno, carga, talud superior)
_TOGETHER = {
    "planar": (("perno_kn_m", "perno_inclinacion_grados", "perno_tipo"), ("carga_kn", "carga_angulo_grados")),
    "wedge": (("carga_kn", "carga_tendencia_grados", "carga_inmersion_grados"), ("buz_sup_grados", "dir_sup_grados")),
    "toppling": (), "berm": (),
}
# variable de Distribuciones -> campo del núcleo; el mismo diccionario valida las variables y nombra los errores
_VARS = {
    "planar": {"altura_m": "height_m", "peso_unitario_kn_m3": "unit_weight", "peso_agua_kn_m3": "water_unit_weight",
               "cohesion_1_kpa": "cohesion", "friccion_1_grados": "friction_deg",
               "dist_grieta_m": "tension_crack_distance_m", "llenado_agua": "water_fill", "kh": "kh",
               "perno_kn_m": "bolt_force", "perno_inclinacion_grados": "bolt_plunge_deg", "carga_kn": "external_force",
               "carga_angulo_grados": "external_angle_deg", "buz_cara_grados": "face_dip_deg",
               "buz_plano_grados": "plane_dip_deg"},
    "wedge": {"altura_m": "height_m", "peso_unitario_kn_m3": "unit_weight", "cohesion_1_kpa": "joint1.cohesion",
              "friccion_1_grados": "joint1.friction_deg", "presion_1_kpa": "joint1.water_pressure",
              "cohesion_2_kpa": "joint2.cohesion", "friccion_2_grados": "joint2.friction_deg",
              "presion_2_kpa": "joint2.water_pressure", "kh": "kh", "carga_kn": "external_force"},
    # a1, a2 y b fijan las alturas (ec. 3): muestrearlas sin rehacer las alturas sería otra geometría
    "toppling": {"peso_unitario_kn_m3": "unit_weight", "friccion_1_grados": "friction_deg",
                 "ancho_bloque_m": "block_width_m", "buz_base_grados": "base_dip_deg",
                 "soporte_kn_m": "support_force", "soporte_inclinacion_grados": "support_angle_deg",
                 "soporte_altura_m": "support_height_m"},
    "berm": {"buz_cara_grados": "face_angle_deg", "retroquiebre_m": "retroquiebre_m"},
}


def _word(v):
    return _strip(v).strip().casefold()


def _floats(vals, text):
    """Excel devuelve 10 como int y el CSV como float: todo número queda float para que las dos vías den lo mismo."""
    for c, v in vals.items():
        if c not in text and v is not None:
            vals[c] = float(v)


def _block(vals, n, sheet):
    def bad(c, motivo):
        raise ValueError(f"{_where(sheet, n, c)}: {motivo}")

    _floats(vals, _BLOCK_TEXT)
    vals["modelo"] = _word(vals["modelo"])
    model = _MODELS.get(vals["modelo"])
    if model is None:
        bad("modelo", f"must be one of {', '.join(_MODELS)}")
    for c, (lo, hi, lo_open, hi_open) in _RANGES.items():
        _rango(vals, sheet, n, c, lo, hi, lo_open=lo_open, hi_open=hi_open)
    for c in _REQUIRED[model]:
        if vals[c] is None:
            bad(c, f"required for model '{vals['modelo']}'")
    for group in _TOGETHER[model]:
        if any(vals[c] is not None for c in group):
            for c in group:
                if vals[c] is None:
                    bad(c, f"give {', '.join(group)} together")
    if model == "toppling":
        _rango(vals, sheet, n, "friccion_1_grados", 0, 90, lo_open=True, hi_open=True)
        for c in ("n_bloques", "bloque_cresta"):
            if not float(vals[c]).is_integer():
                bad(c, "must be a whole number")
        if vals["bloque_cresta"] > vals["n_bloques"]:
            bad("bloque_cresta", "must be within [1, n_bloques]")
    for c, allowed in (("perno_tipo", ("activo", "pasivo")), ("retroanalisis", ("si", "no"))):
        if vals[c] is not None:
            vals[c] = _word(vals[c])
            if vals[c] not in allowed:
                bad(c, f"must be one of {', '.join(allowed)}")
    return BlockRow(**vals, fila=n, hoja=sheet)


def _distribution(vals, n, sheet):
    def bad(c, motivo):
        raise ValueError(f"{_where(sheet, n, c)}: {motivo}")

    _floats(vals, _DIST_TEXT)
    vals["distribucion"] = _word(vals["distribucion"])
    vals["variable"] = _word(vals["variable"])
    kind = _KINDS.get(vals["distribucion"])
    if kind is None:
        bad("distribucion", f"must be one of {', '.join(_KINDS)}")
    needs = {"normal": ("media", "desviacion"), "exponential": ("media",), "uniform": ()}[kind]
    for c in ("media", "desviacion"):
        if c in needs and vals[c] is None:
            bad(c, f"required for a {vals['distribucion']} distribution")
        if c not in needs and vals[c] is not None:
            bad(c, f"not used by a {vals['distribucion']} distribution")
    row = DistributionRow(**vals, fila=n, hoja=sheet)
    try:
        row.distribution
    except ValueError as e:  # los mensajes de Distribution no traen valores
        raise ValueError(f"sheet '{sheet}', row {n}: {e}") from None
    return row


def load_blocks(path, *, sheet: str = BLOCKS_SHEET, column_map: Mapping[str, str] | None = None) -> list[BlockRow]:
    """Lee `Bloques` (una fila por análisis). Un .csv toma la hoja del nombre del archivo."""
    return _cargar(path, sheet, column_map, BLOCK_COLUMNS, _BLOCK_TEXT, ("id_bloque", "id_talud", "modelo"),
                   "id_bloque", _block)


def load_distributions(path, *, sheet: str = DISTRIBUTIONS_SHEET,
                       column_map: Mapping[str, str] | None = None) -> list[DistributionRow]:
    """Lee `Distribuciones` (una variable aleatoria por fila); un par (id_bloque, variable) no se repite."""
    rows = _cargar(path, sheet, column_map, DISTRIBUTION_COLUMNS, _DIST_TEXT,
                   ("id_bloque", "variable", "distribucion", "minimo", "maximo"), None, _distribution)
    seen: dict[tuple[str, str], int] = {}
    for d in rows:
        k = (d.id_bloque, d.variable)
        if k in seen:
            raise ValueError(f"{_where(d.hoja, d.fila, 'variable')}: duplicate id_bloque and variable "
                             f"(first in row {seen[k]})")
        seen[k] = d.fila
    return rows


# ---------------------------------------------------------------- evaluación


@dataclass(frozen=True)
class BermResult:
    bench_height_m: float
    berm_width_m: float
    face_angle_deg: float
    interramp_deg: float
    ritchie: rm.RitchieWidth
    required_width_m: float
    narrower_than_required: bool
    reliability: rm.BermReliability | None


@dataclass(frozen=True)
class BlockResult:
    id_bloque: str = field(repr=False)
    id_talud: str = field(repr=False)
    order: int
    model: str  # planar, wedge, toppling o berm
    deterministic: rm.PlanarResult | rm.WedgeResult | rm.TopplingResult | None
    back_analysis: rm.PlanarBackAnalysis | None
    probabilistic: ProbabilisticResult | None
    berm: BermResult | None
    warnings: tuple[str, ...]
    notes: tuple[str, ...]
    methods: tuple[rm.MethodInfo, ...]

    @property
    def fs(self) -> float | None:
        return None if self.deterministic is None else self.deterministic.factor_of_safety

    @property
    def needs_attention(self) -> bool:
        return bool(block_attention(self))


def block_attention(r: BlockResult) -> list[str]:
    """Única regla de atención de un bloque (R14): FS determinístico < 1 + 1e-9 o algún aviso. PoF y berma no cuentan."""
    out = []
    if r.fs is not None and is_failure(r.fs):
        out.append("att_fs_below_1")
    if r.warnings:
        out.append("att_block_warnings")
    return out


class _Located(ValueError):
    """Error ya ubicado con hoja, fila y columna: no se vuelve a envolver."""


def _family(r: BlockRow, s: SlopeResult, col: str) -> rm.PlaneOrientation:
    name = getattr(r, col)
    for f in s.families:
        if f.familia == name:
            return f.mean_plane
    raise _Located(f"{_where(r.hoja, r.fila, col)}: no family with this name in the tramo of the slope")


def _planar(r: BlockRow, s: SlopeResult):
    p = _family(r, s, "familia_1")
    i = rm.PlanarInput()
    i.height_m, i.face_dip_deg, i.unit_weight = r.altura_m, s.face.dip_deg, r.peso_unitario_kn_m3
    i.cohesion, i.friction_deg = r.cohesion_1_kpa, r.friccion_1_grados
    i.water_unit_weight = 9.81 if r.peso_agua_kn_m3 is None else r.peso_agua_kn_m3
    i.tension_crack_distance_m = r.dist_grieta_m
    i.water_fill = r.llenado_agua or 0.0
    i.kh = r.kh or 0.0
    if r.perno_kn_m is not None:
        i.bolt_force, i.bolt_plunge_deg = r.perno_kn_m, r.perno_inclinacion_grados
        i.bolt_mode = rm.BoltMode.Active if r.perno_tipo == "activo" else rm.BoltMode.Passive
    if r.carga_kn is not None:
        i.external_force, i.external_angle_deg = r.carga_kn, r.carga_angulo_grados
    horizontal = p.dip_deg <= _AXIS_TOL  # sin dirección: no hay bloque planar que deslice
    if not horizontal:
        # un plano vertical no aflora: 90 se lleva justo debajo para que el núcleo lo declare no formado
        i.plane_dip_deg = min(p.dip_deg, 90.0 - 1e-12)
    delta = _delta(p.dip_direction_deg, s.face.dip_direction_deg)
    if p.dip_deg >= 90 - _AXIS_TOL:  # eje: el sentido más cercano a la cara es el crítico
        delta = min(delta, 180.0 - delta)
    return i, horizontal, delta


def _wedge(r: BlockRow, s: SlopeResult):
    def joint(plane, c, phi, u):
        j = rm.WedgeJoint()
        j.plane, j.cohesion, j.friction_deg, j.water_pressure = plane, c, phi, u or 0.0
        return j

    p1, p2 = _family(r, s, "familia_1"), _family(r, s, "familia_2")
    i = rm.WedgeInput()
    i.joint1 = joint(p1, r.cohesion_1_kpa, r.friccion_1_grados, r.presion_1_kpa)
    i.joint2 = joint(p2, r.cohesion_2_kpa, r.friccion_2_grados, r.presion_2_kpa)
    i.face = s.face
    i.upper = (rm.PlaneOrientation(r.dir_sup_grados, r.buz_sup_grados) if r.buz_sup_grados is not None
               else rm.PlaneOrientation(s.face.dip_direction_deg, 0.0))
    i.height_m, i.unit_weight, i.kh = r.altura_m, r.peso_unitario_kn_m3, r.kh or 0.0
    if r.carga_kn is not None:
        i.external_force = r.carga_kn
        i.external_direction = rm.LineOrientation(r.carga_tendencia_grados, r.carga_inmersion_grados)
    return i


def _toppling(r: BlockRow):
    i = rm.TopplingInput()
    n, crest = int(r.n_bloques), int(r.bloque_cresta)
    i.heights_m = rm.goodman_bray_heights(n, crest, r.a1_m, r.a2_m, r.b_m)
    i.block_width_m, i.base_dip_deg, i.a1_m, i.a2_m, i.crest_block = r.ancho_bloque_m, r.buz_base_grados, r.a1_m, \
        r.a2_m, crest
    i.unit_weight, i.friction_deg = r.peso_unitario_kn_m3, r.friccion_1_grados
    i.support_force = r.soporte_kn_m or 0.0
    i.support_angle_deg = r.soporte_inclinacion_grados or 0.0
    i.support_height_m = r.soporte_altura_m
    return i


def _berm(r: BlockRow, face_dip: float, dists, iterations, sampling, seed) -> BermResult:
    h, w = r.altura_banco_m, r.ancho_berma_m
    ir = rm.interramp_angle(h, w, face_dip)
    rit = rm.ritchie_berm_width(h)
    req = rit.width_m if r.ancho_requerido_m is None else r.ancho_requerido_m
    rel = None
    if dists:
        (d,) = dists
        x = sample({d.variable: d.distribution}, iterations, sampling=sampling, seed=seed)[d.variable]
        if d.variable == "buz_cara_grados":
            widths = [rm.bench_width(h, ir, f) for f in x]
        else:  # retroquiebre_m: ancho = H cot(interrampa) − retroquiebre
            hc = h / math.tan(math.radians(ir))
            widths = [hc - b for b in x]
        rel = rm.berm_reliability(widths, req)
    return BermResult(h, w, face_dip, ir, rit, req, w <= req + _EPS, rel)


def _assess_one(order, r: BlockRow, s: SlopeResult, dists, iterations, sampling, seed, lateral_limit_deg):
    model = _MODELS[r.modelo]
    warnings, notes, methods = [], [], []
    det = back = prob = berm = None
    variables = {_VARS[model][d.variable]: d.distribution for d in dists}
    if model == "berm":
        berm = _berm(r, s.face.dip_deg, dists, iterations, sampling, seed)
        methods.append(berm.ritchie.info)
        if berm.reliability is not None:
            methods += [berm.reliability.info, PROBABILISTIC_INFO]
    else:
        horizontal = False
        if model == "planar":
            base, horizontal, delta = _planar(r, s)
            fn = rm.planar_fs
        elif model == "wedge":
            base, fn = _wedge(r, s), rm.wedge_fs
        else:
            base, fn = _toppling(r), rm.toppling_fs
        if horizontal:
            notes.append("planar block not formed: the plane is horizontal")
        else:
            det = fn(base)
            warnings += det.warnings
            notes += det.notes
            methods.append(det.info)
            if model == "planar" and r.retroanalisis == "si":
                back = rm.planar_back_analysis(base, _BACK_FRICTION)
                notes += back.notes
                methods.append(back.info)
        if variables and horizontal and "plane_dip_deg" not in variables:
            notes.append("probabilistic analysis not run: the block does not form")
        elif variables:
            prob = run_probabilistic(model, base, variables, n=iterations, sampling=sampling, seed=seed)
            warnings += [f"probabilistic: {w}" for w in prob.warnings]
            notes += [f"probabilistic: {t}" for t in prob.notes]
            methods.append(prob.info)
        if model == "planar" and not horizontal:
            k = s.kinematics
            lim = k.input.lateral_limit_deg if k is not None else lateral_limit_deg
            formed = (det is not None and det.formed) or (prob is not None and prob.n_valid > 0)
            if formed and delta > lim + _EPS:
                warnings.insert(0, _LATERAL_WARNING)
    uniq = {m.method_id: m for m in methods}
    return BlockResult(r.id_bloque, r.id_talud, order, model, det, back, prob, berm, _unique(warnings),
                       _unique(notes), tuple(uniq.values()))


def _int_arg(v, name, lo):
    if isinstance(v, bool) or not isinstance(v, int) or v < lo:
        raise ValueError(f"{name} must be an integer >= {lo}")


def assess_blocks(rows: Iterable[BlockRow], slopes: Iterable[SlopeResult], distributions: Iterable[DistributionRow] = (),
                  *, iterations: int = 5000, sampling: str = "lhs", seed: int = 1,
                  lateral_limit_deg: float = 30.0) -> list[BlockResult]:
    """Evalúa cada bloque con la cara y las familias de su talud. Un dato imposible lanza con hoja, fila y columna."""
    _int_arg(iterations, "iterations", 1)
    _int_arg(seed, "seed", 0)
    if sampling not in ("lhs", "monte_carlo"):
        raise ValueError("sampling must be 'lhs' or 'monte_carlo'")
    if not (isinstance(lateral_limit_deg, (int, float)) and math.isfinite(lateral_limit_deg)
            and 0 < lateral_limit_deg < 90):
        raise ValueError("lateral_limit_deg must be within (0, 90)")
    rows = list(rows)
    by_talud = {s.id_talud: s for s in slopes}
    by_id = {}
    for r in rows:
        if r.modelo not in _MODELS:
            raise ValueError(f"{_where(r.hoja, r.fila, 'modelo')}: must be one of {', '.join(_MODELS)}")
        by_id[r.id_bloque] = r
    per_block: dict[str, list[DistributionRow]] = {}
    for d in distributions:
        r = by_id.get(d.id_bloque)
        if r is None:
            raise ValueError(f"{_where(d.hoja, d.fila, 'id_bloque')}: no block with this id_bloque")
        allowed = _VARS[_MODELS[r.modelo]]
        if d.variable not in allowed:
            raise ValueError(f"{_where(d.hoja, d.fila, 'variable')}: not used by model '{r.modelo}'; allowed: "
                             f"{', '.join(sorted(allowed))}")
        lst = per_block.setdefault(d.id_bloque, [])
        if r.modelo == "berma" and lst:
            raise ValueError(f"{_where(d.hoja, d.fila, 'variable')}: a berm takes exactly one distribution "
                             "(buz_cara_grados or retroquiebre_m)")
        lst.append(d)
    out = []
    for order, r in enumerate(rows, start=1):
        s = by_talud.get(r.id_talud)
        if s is None:
            raise ValueError(f"{_where(r.hoja, r.fila, 'id_talud')}: no slope face with this id_talud")
        try:
            out.append(_assess_one(order, r, s, per_block.get(r.id_bloque, []), iterations, sampling, seed,
                                   lateral_limit_deg))
        except _Located as e:
            raise ValueError(str(e)) from None
        except ValueError as e:
            msg = str(e).split("Received:")[0].strip()
            for col, name in _VARS[_MODELS[r.modelo]].items():  # el campo del núcleo se nombra con su columna
                msg = msg.replace(f"'{name}'", f"'{col}'")
            raise ValueError(f"sheet '{r.hoja}', row {r.fila}: {msg}") from None
    return out


# ---------------------------------------------------------------- conteos y resultados


_WEDGE_MODES = {rm.WedgeMode.TwoPlanes: "dos_planos", rm.WedgeMode.PlaneOne: "plano_1",
                rm.WedgeMode.PlaneTwo: "plano_2", rm.WedgeMode.Lifting: "despegue",
                rm.WedgeMode.NotFormed: "no_formado"}


def _formed(r: BlockResult) -> bool | None:
    d = r.deterministic
    if r.model == "berm":
        return None
    if d is None:
        return False
    if r.model == "planar":
        return bool(d.formed)
    if r.model == "wedge":
        return d.mode != rm.WedgeMode.NotFormed
    return True


def _mode(r: BlockResult) -> str | None:
    if r.model == "wedge" and r.deterministic is not None:
        return _WEDGE_MODES[r.deterministic.mode]
    if r.model == "planar":
        return "planar" if _formed(r) else "no_formado"
    return "volteo" if r.model == "toppling" else None


_COUNTS = ("blocks", "planar", "wedge", "toppling", "berm", "formed", "with_fs", "fs_below_1", "probabilistic",
           "pof_above_0", "berm_narrower", "berm_reliability_evaluated", "warnings", "notes")


def block_counts(results: Iterable[BlockResult]) -> dict[str, int]:
    """Conteos de una sola fuente para la CLI, el informe y las pruebas de paridad."""
    out = dict.fromkeys(_COUNTS, 0)
    for r in results:
        p, b = r.probabilistic, r.berm
        out["blocks"] += 1
        out[r.model] += 1
        out["formed"] += _formed(r) is True
        out["with_fs"] += r.fs is not None
        out["fs_below_1"] += "att_fs_below_1" in block_attention(r)
        out["probabilistic"] += p is not None
        out["pof_above_0"] += p is not None and bool(p.pof)
        out["berm_narrower"] += b is not None and b.narrower_than_required
        out["berm_reliability_evaluated"] += b is not None and b.reliability is not None
        out["warnings"] += len(r.warnings)
        out["notes"] += len(r.notes)
    return out


RESULT_COLUMNS = ("id_bloque", "id_talud", "modelo", "modo", "formado", "fs", "fs_menor_o_igual_1", "muestreo",
                  "iteraciones", "iteraciones_validas", "semilla", "fs_media", "fs_desv", "fs_min", "fs_max",
                  "pof_pct", "indice_confiabilidad", "indice_confiabilidad_lognormal", "phi_c0_grados",
                  "ancho_ritchie_m", "ancho_requerido_m", "angulo_interrampa_grados", "confiabilidad_berma_pct",
                  "avisos", "notas")


def _yes(v):
    return None if v is None else ("si" if v else "no")


def save_block_results(results: Iterable[BlockResult], path) -> Path:
    """Escribe .xlsx (hoja `Bloques_resultados`) o .csv. Lleva id_bloque e id_talud; ninguna otra columna de origen."""
    rows = []
    for r in results:
        p, b, ba = r.probabilistic, r.berm, r.back_analysis
        prob = ([p.sampling, p.n, p.n_valid, p.seed, p.fs_mean, p.fs_sd, p.fs_min, p.fs_max,
                 None if p.pof is None else p.pof * 100, p.reliability_index, p.reliability_index_lognormal]
                if p is not None else [None] * 11)
        berm = ([b.ritchie.width_m, b.required_width_m, b.interramp_deg,
                 None if b.reliability is None else b.reliability.reliability * 100] if b is not None else [None] * 4)
        rows.append([r.id_bloque, r.id_talud, _SHEET_MODEL[r.model], _mode(r), _yes(_formed(r)), r.fs,
                     None if r.fs is None else _yes("att_fs_below_1" in block_attention(r)), *prob,
                     None if ba is None else ba.friction_at_zero_cohesion_deg, *berm,
                     " | ".join(r.warnings), " | ".join(r.notes)])
    return write_table(path, RESULT_COLUMNS, rows, sheet="Bloques_resultados")
