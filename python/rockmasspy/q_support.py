"""Lectura de la carta de sostenimiento Q y recomendación para techo y paredes (NGI 2025 / NGI 2015).

La categoría sale de los polígonos digitalizados (`q_chart_data`); las fórmulas clásicas [V2] vienen del núcleo.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from . import _rockmasspy_core as rm
from .chart_regions import locate
from .q_chart_data import ESR_TABLES, Q_CHARTS

_ENUM = {"Q-NGI-2025": rm.QEdition.NGI2025, "Q-NGI-2015": rm.QEdition.NGI2015}
_SPANS = (5.0, 10.0, 20.0)


@dataclass(frozen=True)
class QChartReading:
    edition: str
    q: float
    de_m: float
    category: int
    label: str
    shotcrete_mm: tuple[float, float | None] | None
    sfr_energy_j: int | None
    bolt_spacing_with_sfr_m: tuple[float, float] | None
    bolt_spacing_without_sfr_m: tuple[float, float] | None
    bolt_length_chart_m: tuple[float, float] | None
    rrs: str | None
    rrs_spacing_m: tuple[float, float] | None
    rrs_spec: str | None
    no_empirical_data: bool
    warnings: tuple[str, ...]
    info: rm.MethodInfo


@dataclass(frozen=True)
class QSupportResult:
    edition: str
    esr_category: str
    esr_used: float
    roof: QChartReading
    walls: QChartReading | None
    wall_q: float | None
    max_unsupported_span: rm.SupportFormulaResult
    bolt_length_formula: rm.SupportFormulaResult
    roof_pressure: rm.SupportFormulaResult | None
    warnings: tuple[str, ...]
    methods: tuple[rm.MethodInfo, ...]
    notes: tuple[str, ...] = ()


def _check(value, name):
    if not (isinstance(value, (int, float)) and math.isfinite(value) and value > 0):
        raise ValueError(f"{name} must be finite and > 0, got {value!r}")


def _chart(edition):
    if edition not in Q_CHARTS:
        raise ValueError(f"unknown edition {edition!r}; available: {sorted(Q_CHARTS)}")
    return Q_CHARTS[edition]


def _bracket(ticks, x):
    """Valores de las dos marcas vecinas; en una marca (v, v); fuera de las marcas, la extrema (sin extrapolar)."""
    if x <= ticks[0][0]:
        return (ticks[0][1],) * 2
    if x >= ticks[-1][0]:
        return (ticks[-1][1],) * 2
    for (x0, v0), (x1, v1) in zip(ticks, ticks[1:]):
        if x0 <= x <= x1:
            return (v1, v1) if x == x1 else (v0, v0) if x == x0 else (v0, v1)
    raise AssertionError("unreachable")


def read_q_chart(q: float, de_m: float, *, edition: str = "Q-NGI-2025",
                 span_m: float | None = None) -> QChartReading:
    """Lee la categoría de sostenimiento en (Q, De); fuera del marco se lee del lado menos favorable (R4)."""
    _check(q, "q")
    _check(de_m, "de_m")
    if span_m is not None:
        _check(span_m, "span_m")
    ch = _chart(edition)
    warns: list[str] = []
    if q < 0.001 or de_m > 100:
        cat_n = 9
        warns.append("point outside the chart (Q < 0.001 or De > 100)")
    else:
        if de_m < 1:
            warns.append("De below the chart (1 m); read at De = 1")
            de_m = 1.0
        if q > 1000:
            warns.append("Q above the chart (1000); read at Q = 1000")
            q = 1000.0
        cat_n = locate(math.log10(q), math.log10(de_m), ch.regions)
        if cat_n is None:  # no debería pasar: las regiones cubren todo el marco
            raise RuntimeError(f"point (Q={q}, De={de_m}) not covered by the chart regions")
    cat = ch.categories[cat_n]
    inside = cat_n != 9
    pt = (math.log10(q), math.log10(de_m))
    no_data = inside and any(locate(*pt, [r]) is not None for r in ch.no_data)
    if no_data:
        warns.append("point in a dashed area of the chart (no empirical data)")
    if edition == "Q-NGI-2025" and cat_n >= 7:
        warns.append("categories 7-9 are indicative; a separate engineering assessment is needed (NGI 2025, 4.7)")
    if cat_n == 9:
        warns.append("special evaluation")

    has_rrs = inside and 6 <= cat_n <= 8
    rrs_spacing = rrs_spec = None
    if has_rrs:
        rrs_spacing = _bracket(ch.rrs_spacing, q)
        if span_m is not None:
            col = next((s for s in _SPANS if s >= span_m), None)
            rrs_spec = ch.rrs_specs[cat.rrs][col] if col else None
            if rrs_spec is None:
                warns.append(f"no RRS specification for {cat.rrs} at span {span_m:g} m")
    return QChartReading(
        edition, q, de_m, cat_n, cat.label, cat.shotcrete_mm, cat.sfr_energy_j,
        _bracket(ch.spacing_with_sfr, q) if inside else None,
        _bracket(ch.spacing_without_sfr, q) if inside else None,
        _bracket(ch.bolt_length, de_m) if inside else None,
        cat.rrs if has_rrs else None, rrs_spacing, rrs_spec, no_data, tuple(warns), ch.info)


def recommend_q_support(q: float, span_m: float, *, esr_category: str, esr: float | None = None,
                        edition: str = "Q-NGI-2025", wall_height_m: float | None = None,
                        high_stress: bool = False, jn: float | None = None,
                        jr: float | None = None) -> QSupportResult:
    """Recomendación con la carta Q para el techo y, si hay `wall_height_m`, para las paredes."""
    _check(q, "q")
    _check(span_m, "span_m")
    if wall_height_m is not None:
        _check(wall_height_m, "wall_height_m")
    _chart(edition)
    ed = _ENUM[edition]
    cat = str(esr_category).upper()
    if cat not in ESR_TABLES[edition]:
        raise ValueError(f"esr_category must be one of A-G, got {esr_category!r}")
    lo, hi, _ = ESR_TABLES[edition][cat]
    warns: list[str] = []
    if esr is None:
        if lo != hi:
            raise ValueError(f"ESR category {cat} covers {lo:g}-{hi:g}; pass esr")
        esr = lo
    else:
        _check(esr, "esr")
        if not lo <= esr <= hi:
            warns.append(f"ESR {esr:g} outside category {cat} range {lo:g}-{hi:g} (NGI Table 4-1)")

    dim = span_m
    if edition == "Q-NGI-2025" and wall_height_m is not None and wall_height_m > span_m:
        dim = wall_height_m
        warns.append("wall height exceeds span: roof read with wall height (NGI 2025, 4.1)")
    ed_roof = rm.equivalent_dimension(dim, esr, q, cat, ed)
    esr_used = ed_roof.esr_used
    warns += ed_roof.warnings
    roof = read_q_chart(q, ed_roof.de_m, edition=edition, span_m=span_m)
    warns += roof.warnings
    infos = [ed_roof.info, roof.info]

    walls = wq = None
    if wall_height_m is not None:
        w = rm.wall_q(q, wall_height_m, span_m, high_stress, ed)
        ed_wall = rm.equivalent_dimension(wall_height_m, esr, q, cat, ed)  # Q real, no el de pared (R12)
        walls = read_q_chart(w.q_wall, ed_wall.de_m, edition=edition, span_m=span_m)
        wq = w.q_wall
        warns += list(ed_wall.warnings) + list(walls.warnings)
        infos += [w.info, walls.info]

    span_f = rm.max_unsupported_span(q, esr_used)
    bolt_f = rm.bolt_length_barton1980(span_m, esr_used)
    press = rm.roof_pressure_grimstad_barton(q, jn, jr) if jn is not None and jr is not None else None
    for f in (span_f, bolt_f, press):
        if f is not None:
            warns += f.warnings
            infos.append(f.info)
    notes = ("chart bolt length is given for ESR = 1",) if esr_used != 1 else ()  # nota, no aviso (ruling 9)

    methods, seen = [], set()
    for i in infos:
        if (i.method_id, i.source) not in seen:
            seen.add((i.method_id, i.source))
            methods.append(i)
    return QSupportResult(edition, cat, esr_used, roof, walls, wq, span_f, bolt_f, press,
                          tuple(dict.fromkeys(warns)), tuple(methods), notes)
