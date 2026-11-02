"""Taludes en roca: hojas `Familias` y `Taludes` (CSV o Excel), evaluación por talud y resultados.

Por talud: cinemática de Markland (varios planos), familias de Fisher, SMR (discreto y continuo) y Q-slope.
Solo se leen las columnas de `JOINT_COLUMNS` y `FACE_COLUMNS` (códigos de labor, coordenadas y observaciones ni se abren).
`id_talud` e `id_tramo` pueden ir al archivo de resultados, nunca a un mensaje ni a un repr.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, fields
from pathlib import Path

from . import _rockmasspy_core as rm
from .batch import write_table
from .csv_io import _CsvSource
from .excel_io import _open, _where
from .tramos import read_records

JOINTS_SHEET = "Familias"
FACES_SHEET = "Taludes"
_EXCAVATIONS = {
    "natural": rm.SlopeExcavation.NaturalSlope, "precorte": rm.SlopeExcavation.Presplitting,
    "voladura_suave": rm.SlopeExcavation.SmoothBlasting,
    "voladura_normal": rm.SlopeExcavation.NormalBlastingOrMechanical,
    "mecanica": rm.SlopeExcavation.NormalBlastingOrMechanical,
    "voladura_deficiente": rm.SlopeExcavation.DeficientBlasting,
}
_CRITICAL = ("planar", "wedge_primary", "wedge_secondary", "flexural_toppling", "direct_toppling",
             "direct_toppling_oblique")
_Q_FIELDS = ("rqd_pct", "jn", "jr_a", "ja_a", "o_a", "jwice")
_SET_B = ("jr_b", "ja_b", "o_b")
_SRF = ("srf_a", "srf_b", "srf_c")
_EPS = 1e-9


# ---------------------------------------------------------------- lectura


@dataclass(frozen=True)
class JointRecord:
    id_tramo: str = field(repr=False)
    familia: str | None
    dip_deg: float
    dip_direction_deg: float
    fila: int
    hoja: str = field(default=JOINTS_SHEET, repr=False, compare=False)


@dataclass(frozen=True)
class SlopeFace:
    id_talud: str = field(repr=False)
    id_tramo: str = field(repr=False)
    buz_cara_grados: float
    dir_buz_cara_grados: float
    friccion_grados: float | None
    limite_lateral_grados: float | None
    rmr_basico: float | None
    excavacion: str | None
    rqd_pct: float | None
    jn: float | None
    jr_a: float | None
    ja_a: float | None
    o_a: float | None
    jwice: float | None
    jr_b: float | None
    ja_b: float | None
    o_b: float | None
    srf_a: float | None
    srf_b: float | None
    srf_c: float | None
    fila: int
    hoja: str = field(default=FACES_SHEET, repr=False, compare=False)


JOINT_COLUMNS = ("id_tramo", "familia", "buzamiento_grados", "dir_buzamiento_grados")
FACE_COLUMNS = tuple(f.name for f in fields(SlopeFace) if f.name not in ("fila", "hoja"))


def _rango(vals, sheet, n, c, lo, hi, *, lo_open=False, hi_open=False):
    v = vals[c]
    if v is not None and (v < lo or v > hi or (lo_open and v == lo) or (hi_open and v == hi)):
        raise ValueError(f"{_where(sheet, n, c)}: out of range")


def _joint(vals, n, sheet):
    _rango(vals, sheet, n, "buzamiento_grados", 0, 90)
    _rango(vals, sheet, n, "dir_buzamiento_grados", 0, 360)
    for c in ("buzamiento_grados", "dir_buzamiento_grados"):
        if vals[c] is None:
            raise ValueError(f"{_where(sheet, n, c)}: required value is empty")
    return JointRecord(vals["id_tramo"], vals["familia"], vals["buzamiento_grados"],
                       vals["dir_buzamiento_grados"], n, sheet)


def _face(vals, n, sheet):
    def falta(c, motivo="required value is empty"):
        raise ValueError(f"{_where(sheet, n, c)}: {motivo}")

    for c in ("buz_cara_grados", "dir_buz_cara_grados"):
        if vals[c] is None:
            falta(c)
    _rango(vals, sheet, n, "buz_cara_grados", 0, 90, lo_open=True)
    _rango(vals, sheet, n, "dir_buz_cara_grados", 0, 360)
    _rango(vals, sheet, n, "friccion_grados", 0, 90, lo_open=True, hi_open=True)
    _rango(vals, sheet, n, "limite_lateral_grados", 0, 90, lo_open=True, hi_open=True)
    _rango(vals, sheet, n, "rmr_basico", 0, 100)
    if vals["rmr_basico"] is not None:
        if vals["excavacion"] is None:
            falta("excavacion")
    if vals["excavacion"] is not None:
        exc = vals["excavacion"].strip().casefold()
        if exc not in _EXCAVATIONS:
            falta("excavacion", f"must be one of {sorted(_EXCAVATIONS)}")
        vals["excavacion"] = exc
    if any(vals[c] is not None for c in _Q_FIELDS + _SET_B + _SRF):
        for c in _Q_FIELDS:
            if vals[c] is None:
                falta(c, "required for Q-slope (rqd_pct, jn, jr_a, ja_a, o_a, jwice and one srf)")
        if all(vals[c] is None for c in _SRF):
            falta("srf_a", "give at least one of srf_a, srf_b, srf_c")
        if any(vals[c] is not None for c in _SET_B):
            for c in _SET_B:
                if vals[c] is None:
                    falta(c, "set B needs jr_b, ja_b and o_b together")
    return SlopeFace(**vals, fila=n, hoja=sheet)


def _leer(src, sheet, column_map, columns, text, required, id_column, build):
    recs = read_records(src, sheet, column_map, columns=columns, text=text, required=required,
                        ident=set(columns) - {"excavacion"}, id_column=id_column)
    return [build(v, n, sheet) for n, v in recs]


def _cargar(path, sheet, column_map, *args):
    p = Path(path)
    if p.suffix.lower() == ".csv":
        return _leer(_CsvSource({p.stem: p}), p.stem, column_map, *args)
    if p.suffix.lower() != ".xlsx":
        raise ValueError(f"{p.name}: unsupported file type '{p.suffix}'; save it as .xlsx or .csv")
    wb = _open(p)
    try:
        return _leer(wb, sheet, column_map, *args)
    finally:
        wb.wb.close()


def load_families(path, *, sheet: str = JOINTS_SHEET, column_map: Mapping[str, str] | None = None) -> list[JointRecord]:
    """Lee los planos de `Familias` (una fila por plano; una familia puede repetirse)."""
    return _cargar(path, sheet, column_map, JOINT_COLUMNS, {"id_tramo", "familia"}, ("id_tramo",), None, _joint)


def load_slope_faces(path, *, sheet: str = FACES_SHEET, column_map: Mapping[str, str] | None = None) -> list[SlopeFace]:
    """Lee las caras de `Taludes` (una fila por cara)."""
    return _cargar(path, sheet, column_map, FACE_COLUMNS, {"id_talud", "id_tramo", "excavacion"},
                   ("id_talud", "id_tramo", "buz_cara_grados", "dir_buz_cara_grados"), "id_talud", _face)


# ---------------------------------------------------------------- evaluación


@dataclass(frozen=True)
class FamilyStats:
    familia: str
    n: int
    mean_plane: rm.PlaneOrientation
    fisher: rm.FisherStats


@dataclass(frozen=True)
class SmrCase:
    label: str
    mode: str  # planar, toppling o wedge
    discrete: rm.SmrResult
    continuous: rm.SmrResult


@dataclass(frozen=True)
class SlopeResult:
    id_talud: str = field(repr=False)
    id_tramo: str = field(repr=False)
    face: rm.PlaneOrientation
    planes: tuple[rm.PlaneOrientation, ...]
    plane_families: tuple[str | None, ...]
    families: tuple[FamilyStats, ...]
    kinematics: rm.KinematicResult | None
    smr_cases: tuple[SmrCase, ...]
    smr_discrete: SmrCase | None
    smr_continuous: SmrCase | None
    q_slope: rm.QSlopeResult | None
    face_steeper_than_beta: bool | None
    warnings: tuple[str, ...]
    notes: tuple[str, ...]
    methods: tuple[rm.MethodInfo, ...]

    @property
    def needs_attention(self) -> bool:
        k = self.kinematics
        return bool(self.warnings or (k is not None and any(getattr(k, c) for c in _CRITICAL))
                    or any(c is not None and c.discrete.smr_class >= 4 for c in (self.smr_discrete,))
                    or any(c is not None and c.continuous.smr_class >= 4 for c in (self.smr_continuous,))
                    or self.face_steeper_than_beta)


def _first_min(cases, key):
    best = None
    for c in cases:
        if best is None or key(c).smr < key(best).smr:
            best = c
    return best


def _delta(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def _smr_cases(f: SlopeFace, planes, labels, face):
    """Un caso por plano medio (familia) o fila suelta, y uno de cuña por cada par con intersección."""
    exc = _EXCAVATIONS[f.excavacion]

    def caso(label, mode, d, dip):
        ang = rm.smr_angles(mode, d, dip, face)
        return SmrCase(label, {rm.SmrMode.Planar: "planar", rm.SmrMode.Toppling: "toppling",
                               rm.SmrMode.Wedge: "wedge"}[mode],
                       rm.smr(f.rmr_basico, mode, rm.SmrFunctions.Discrete, exc, ang),
                       rm.smr(f.rmr_basico, mode, rm.SmrFunctions.Continuous, exc, ang))

    out = []
    for p, lab in zip(planes, labels):
        dd = _delta(p.dip_direction_deg, face.dip_direction_deg)
        modes = ([rm.SmrMode.Planar] if dd < 90 - _EPS else [rm.SmrMode.Toppling] if dd > 90 + _EPS
                 else [rm.SmrMode.Planar, rm.SmrMode.Toppling])
        out.append(_first_min([caso(lab, m, p.dip_direction_deg, p.dip_deg) for m in modes],
                              lambda c: c.discrete))
    for i in range(len(planes)):
        for j in range(i + 1, len(planes)):
            line = rm.plane_intersection(planes[i], planes[j])
            if line is not None and _delta(line.trend_deg, face.dip_direction_deg) <= 90 + _EPS:
                out.append(caso(f"{labels[i]}×{labels[j]}", rm.SmrMode.Wedge, line.trend_deg, line.plunge_deg))
    return out


def _unique(items):
    return tuple(dict.fromkeys(items))


def _assess_one(f: SlopeFace, joints, lateral_limit_deg):
    face = rm.PlaneOrientation(f.dir_buz_cara_grados, f.buz_cara_grados)
    planes = tuple(rm.PlaneOrientation(j.dip_direction_deg, j.dip_deg) for j in joints)
    fams = tuple(j.familia for j in joints)
    names = list(dict.fromkeys(x for x in fams if x is not None))
    warnings, notes, methods = [], [], []
    stats = []
    for name in names:
        ps = [p for p, x in zip(planes, fams) if x == name]
        fs = rm.fisher_stats([rm.pole_of(p) for p in ps])
        stats.append(FamilyStats(name, fs.n, rm.plane_of(fs.mean), fs))
        warnings += fs.warnings
        methods.append(fs.info)
    kin = None
    if not joints:
        warnings.append("no Familias rows for this id_tramo")
    elif f.friccion_grados is None:
        warnings.append("kinematics not run: friccion_grados is empty")
    else:
        lim = f.limite_lateral_grados if f.limite_lateral_grados is not None else lateral_limit_deg
        kin = rm.kinematic_analysis(list(planes), [names.index(x) if x is not None else -1 for x in fams],
                                    rm.KinematicInput(face, f.friccion_grados, lim))
        notes += kin.notes
        methods += kin.methods
    cases = []
    if joints and f.rmr_basico is not None:
        sp = [s.mean_plane for s in stats]
        labels = [s.familia for s in stats]
        for j, p in zip(joints, planes):
            if j.familia is None:
                sp.append(p)
                labels.append(f"row {j.fila}")
        cases = _smr_cases(f, sp, labels, face)
        for c in cases:
            warnings += c.discrete.warnings + c.continuous.warnings
            methods += [c.discrete.info, c.continuous.info]
    q, steeper = None, None
    if f.rqd_pct is not None:
        qi = rm.QSlopeInput()
        for k, v in dict(rqd_pct=f.rqd_pct, jn=f.jn, jr_a=f.jr_a, ja_a=f.ja_a, o_factor_a=f.o_a, jwice=f.jwice,
                         jr_b=f.jr_b, ja_b=f.ja_b, o_factor_b=f.o_b, srf_a=f.srf_a, srf_b=f.srf_b,
                         srf_c=f.srf_c).items():
            if v is not None:
                setattr(qi, k, v)
        q = rm.q_slope(qi)
        steeper = bool(f.buz_cara_grados >= q.beta_deg)
        warnings += q.warnings
        notes += q.notes
        methods.append(q.info)
    uniq = {(m.method_id, m.source): m for m in methods}
    return SlopeResult(f.id_talud, f.id_tramo, face, planes, fams, tuple(stats), kin, tuple(cases),
                       _first_min(cases, lambda c: c.discrete), _first_min(cases, lambda c: c.continuous),
                       q, steeper, _unique(warnings), _unique(notes), tuple(uniq.values()))


def assess_slopes(faces: Iterable[SlopeFace], joints: Iterable[JointRecord], *,
                  lateral_limit_deg: float = 30.0) -> list[SlopeResult]:
    """Evalúa cada talud con los planos de `Familias` de su `id_tramo`. Un dato imposible lanza con hoja y fila."""
    por_tramo: dict[str, list[JointRecord]] = {}
    for j in joints:
        por_tramo.setdefault(j.id_tramo, []).append(j)
    out = []
    for f in faces:
        try:
            out.append(_assess_one(f, por_tramo.get(f.id_tramo, []), lateral_limit_deg))
        except ValueError as e:
            raise ValueError(f"sheet '{f.hoja}', row {f.fila}: {e}") from None
    return out


_COUNTS = ("n_planes", "n_intersections", "n_parallel_pairs") + _CRITICAL + ("planar_no_limits",)


def slope_counts(results: Iterable[SlopeResult]) -> dict[str, int]:
    out = dict.fromkeys(_COUNTS, 0)
    out.update({f"smr_{m}_{k}": 0 for m in "dc" for k in range(1, 6)})
    out.update(slopes=0, q_slope_evaluated=0, face_steeper_than_beta=0, warnings=0, notes=0)
    for r in results:
        out["slopes"] += 1
        if r.kinematics is not None:
            for c in _COUNTS:
                out[c] += getattr(r.kinematics, c)
        for m, case in (("d", r.smr_discrete), ("c", r.smr_continuous)):
            if case is not None:
                out[f"smr_{m}_{(case.discrete if m == 'd' else case.continuous).smr_class}"] += 1
        out["q_slope_evaluated"] += r.q_slope is not None
        out["face_steeper_than_beta"] += bool(r.face_steeper_than_beta)
        out["warnings"] += len(r.warnings)
        out["notes"] += len(r.notes)
    return out


_RESULT_COLUMNS = ("id_talud", "id_tramo", "buz_cara", "dir_cara", "friccion", "limite_lateral", "n_planos",
                   "n_intersecciones", "planar", "planar_sin_limites", "cuna_primaria", "cuna_secundaria",
                   "volteo_flexural", "volteo_directo", "volteo_directo_oblicuo", "smr_discreto",
                   "smr_clase_discreto", "smr_continuo", "smr_clase_continuo", "smr_caso", "q_slope",
                   "beta_grados", "cara_mas_empinada_que_beta", "avisos", "notas")


def save_slope_results(results: Iterable[SlopeResult], path) -> Path:
    """Escribe .xlsx (hoja `Taludes_resultados`) o .csv. Lleva id_talud e id_tramo; ninguna otra columna de origen."""
    rows = []
    for r in results:
        k = r.kinematics
        d, c = r.smr_discrete, r.smr_continuous
        kin = ([k.input.friction_deg, k.input.lateral_limit_deg, k.n_planes, k.n_intersections, k.planar,
                k.planar_no_limits, k.wedge_primary, k.wedge_secondary, k.flexural_toppling, k.direct_toppling,
                k.direct_toppling_oblique] if k is not None else [None] * 11)
        rows.append([r.id_talud, r.id_tramo, r.face.dip_deg, r.face.dip_direction_deg, *kin,
                     d.discrete.smr if d else None, d.discrete.smr_class if d else None,
                     c.continuous.smr if c else None, c.continuous.smr_class if c else None,
                     d.label if d else None, r.q_slope.q_slope if r.q_slope else None,
                     r.q_slope.beta_deg if r.q_slope else None,
                     None if r.face_steeper_than_beta is None else ("si" if r.face_steeper_than_beta else "no"),
                     " | ".join(r.warnings), " | ".join(r.notes)])
    return write_table(path, _RESULT_COLUMNS, rows, sheet="Taludes_resultados")
