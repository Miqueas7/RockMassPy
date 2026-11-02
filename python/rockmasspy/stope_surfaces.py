"""Archivo de caras de tajeo (hoja `Superficies`, CSV o Excel): lectura, evaluación con Mathews y resultados.

Reutiliza el lector de `tramos` y el escritor de `batch`. Solo se leen las columnas de `SURFACE_COLUMNS`
(las demás, como códigos de labor o coordenadas, ni se abren). El único identificador es `id_superficie`.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, fields
from pathlib import Path

from . import _rockmasspy_core as rm
from .batch import write_table
from .csv_io import _CsvSource
from .excel_io import _open, _where
from .mathews import MathewsResult, mathews_stability
from .tramos import read_records

SHEET = "Superficies"
_Q_EDITIONS = {"Q-NGI-2025": rm.QEdition.NGI2025, "Q-NGI-2015": rm.QEdition.NGI2015}
_MODOS = {"gravedad": "gravity", "deslizamiento": "sliding"}
_PARAMS_Q = ("rqd_pct", "jn", "jr", "ja")
_GEOM = ("area_m2", "perimetro_m", "ancho_m", "largo_m")


@dataclass(frozen=True)
class StopeSurface:
    id_superficie: str
    q_prima: float | None
    rqd_pct: float | None
    jn: float | None
    jr: float | None
    ja: float | None
    q_edicion: str
    ucs_mpa: float | None
    sigma1_mpa: float | None
    dif_buz_junta_deg: float | None
    dif_rumbo_junta_deg: float | None
    modo_falla: str
    inclinacion_cara_deg: float | None
    buz_junta_deg: float | None
    area_m2: float | None
    perimetro_m: float | None
    ancho_m: float | None
    largo_m: float | None
    fila: int  # fila de origen (la cabecera es la 1)


SURFACE_COLUMNS = tuple(f.name for f in fields(StopeSurface) if f.name != "fila")
_TEXTO = {"id_superficie", "q_edicion", "modo_falla"}


def _fila(vals, n):
    """Valida una fila ya leída (obligatorias y combinaciones) y pone los valores por defecto."""
    def falta(c, motivo="required value is empty"):
        raise ValueError(f"{_where(SHEET, n, c)}: {motivo}")

    def hay(c):
        return vals[c] is not None

    for c in ("ucs_mpa", "sigma1_mpa", "dif_buz_junta_deg"):
        if not hay(c):
            falta(c)
    n_par = sum(hay(c) for c in _PARAMS_Q)
    if hay("q_prima"):
        if n_par:
            falta("q_prima", "give q_prima or rqd_pct, jn, jr and ja, not both")
    elif n_par != len(_PARAMS_Q):
        falta(next(c for c in _PARAMS_Q if not hay(c)), "q_prima or all of rqd_pct, jn, jr, ja is required")
    modo = (vals["modo_falla"] or "gravedad").casefold()
    if modo not in _MODOS:
        falta("modo_falla", "must be 'gravedad' or 'deslizamiento'")
    if modo == "gravedad" and not hay("inclinacion_cara_deg"):
        falta("inclinacion_cara_deg")
    if modo == "deslizamiento" and not hay("buz_junta_deg"):
        falta("buz_junta_deg")
    par_ap, par_al = hay("area_m2") or hay("perimetro_m"), hay("ancho_m") or hay("largo_m")
    if par_ap and par_al:
        falta("ancho_m" if hay("ancho_m") else "largo_m", "give area_m2 and perimetro_m, or ancho_m and largo_m, not both")
    if not par_ap and not par_al:
        falta("area_m2", "geometry is required: area_m2 and perimetro_m, or ancho_m and largo_m")
    for a, b in (("area_m2", "perimetro_m"), ("ancho_m", "largo_m")):
        for c, otro in ((a, b), (b, a)):
            if hay(c) and not hay(otro):
                falta(otro)
    for c in _GEOM:
        if hay(c) and vals[c] <= 0:
            falta(c, "must be > 0")
    vals = {**vals, "modo_falla": modo, "q_edicion": vals["q_edicion"] or "Q-NGI-2025"}
    if vals["dif_rumbo_junta_deg"] is None:
        vals["dif_rumbo_junta_deg"] = 0.0
    return StopeSurface(**vals, fila=n)


def _leer(src, sheet, column_map):
    recs = read_records(src, sheet, column_map, columns=SURFACE_COLUMNS, text=_TEXTO, required=("id_superficie",),
                        ident=set(), id_column="id_superficie")
    return [_fila(v, n) for n, v in recs]


def load_stope_surfaces(path, *, sheet: str = SHEET, column_map: Mapping[str, str] | None = None) -> list[StopeSurface]:
    """Lee las caras de un .xlsx (hoja `sheet`) o de un .csv (la hoja es el archivo)."""
    p = Path(path)
    if p.suffix.lower() == ".csv":
        return _leer(_CsvSource({p.stem: p}), p.stem, column_map)
    if p.suffix.lower() != ".xlsx":
        raise ValueError(f"{p.name}: unsupported file type '{p.suffix}'; save it as .xlsx or .csv")
    wb = _open(p)
    try:
        return _leer(wb, sheet, column_map)
    finally:
        wb.wb.close()


@dataclass(frozen=True)
class StopeSurfaceResult:
    id_superficie: str
    mathews: MathewsResult


def _evaluar(s: StopeSurface, graph: str) -> MathewsResult:
    if s.q_prima is not None:
        q, info = s.q_prima, None
    else:
        if s.q_edicion not in _Q_EDITIONS:
            raise ValueError(f"q_edicion must be one of {sorted(_Q_EDITIONS)}, got {s.q_edicion!r}")
        r = rm.q_value(rm.QInput(s.rqd_pct, s.jn, s.jr, s.ja, 1.0, 1.0), _Q_EDITIONS[s.q_edicion])
        q, info = r.q_base, r.info
    hr = (rm.hydraulic_radius(s.area_m2, s.perimetro_m) if s.area_m2 is not None
          else rm.hydraulic_radius_rect(s.ancho_m, s.largo_m))
    return mathews_stability(q, hr, ucs_mpa=s.ucs_mpa, sigma1_mpa=s.sigma1_mpa,
                             dip_difference_deg=s.dif_buz_junta_deg, strike_difference_deg=s.dif_rumbo_junta_deg,
                             failure_mode=_MODOS[s.modo_falla], surface_inclination_deg=s.inclinacion_cara_deg,
                             joint_dip_deg=s.buz_junta_deg, q_info=info, graph=graph)


def assess_stope_surfaces(surfaces: Iterable[StopeSurface], *, graph: str = "Mathews-Potvin1988") -> list[StopeSurfaceResult]:
    """N′ y zona de cada cara. Es un archivo de diseño: un dato malo detiene la corrida, con su fila."""
    out = []
    for s in surfaces:
        try:
            out.append(StopeSurfaceResult(s.id_superficie, _evaluar(s, graph)))
        except ValueError as e:
            raise ValueError(f"sheet '{SHEET}', row {s.fila}: {e}") from None
    return out


def stope_zone_counts(results: Iterable[StopeSurfaceResult]) -> dict[int, int]:
    counts = dict.fromkeys((1, 2, 3), 0)
    for r in results:
        counts[r.mathews.reading.zone] += 1
    return counts


_RESULT_COLUMNS = ("id_superficie", "grafico", "q_prima", "factor_a", "factor_b", "factor_c", "modo_falla", "n_prima",
                   "radio_hidraulico_m", "zona", "zona_nombre", "extrapolado", "avisos")


def save_stope_results(results: Iterable[StopeSurfaceResult], path) -> Path:
    """Escribe .xlsx (hoja `Superficies_resultados`) o .csv. Solo lleva id_superficie como identificador."""
    rows = []
    for r in results:
        m = r.mathews
        rows.append([r.id_superficie, m.graph, m.q_prime, m.factor_a, m.factor_b, m.factor_c, m.failure_mode,
                     m.n_prime, m.hr_m, m.reading.zone, m.reading.zone_label, "si" if m.reading.extrapolated else "no",
                     " | ".join(m.warnings)])
    return write_table(path, _RESULT_COLUMNS, rows, sheet="Superficies_resultados")
