"""Informe de RockMassPy: modelo independiente del formato y memoria de cálculo.

No se importa desde `rockmasspy/__init__.py`: se usa con `import rockmasspy.report`.
El informe nunca muestra códigos de identificación (labor_codigo, zona_nivel, codigo_mina, evaluador_codigo,
observaciones); solo el id_tramo (código propio del usuario). El mapa en planta muestra este/norte en sus ejes
como escala.
"""

from __future__ import annotations

import datetime
import io
from collections import Counter
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Callable

from .. import __version__
from .. import _rockmasspy_core as rm
from ..batch import _COLUMNS, _columns, _fila, q_chart_crosstab, summarize
from ..cell_table import CellTable
from ..gsi_charts import GSI_CHARTS
from ..labor_table import LaborTable, _key
from ..q_chart_data import Q_CHARTS
from ..range_table import RangeTable
from .texts import DISCLAIMER, t

if TYPE_CHECKING:  # verify importa a report vía build_anexo39b; evita el ciclo
    from ..verify import VerificationResult


@dataclass(frozen=True)
class Paragraph:
    text: str


@dataclass(frozen=True)
class Table:
    caption: str
    header: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class Figure:
    caption: str
    png: bytes | None
    note: str = ""


@dataclass(frozen=True)
class MethodRef:
    method_id: str
    verification: str
    source: str


@dataclass(frozen=True)
class Section:
    number: str
    title: str
    blocks: tuple = ()  # Paragraph | Table | Figure | Section
    to_complete: bool = False


@dataclass(frozen=True)
class Report:
    title: str
    subtitle: str
    lang: str
    sections: tuple[Section, ...]
    methods: tuple[MethodRef, ...]
    disclaimer: str
    version: str
    date: str


# --- Métodos: la verificación y la fuente salen del `info` del núcleo (se llama cada función una vez) ---

def _rmr89():
    i = rm.Rmr89Input()
    i.ucs_mpa, i.rqd_pct, i.spacing_m, i.joint_condition_rating, i.water = 120, 80, 0.5, 20, rm.Water.Dry
    return rm.rmr89(i).info


def _rmr76():
    i = rm.Rmr76Input()
    i.ucs_mpa, i.rqd_pct, i.spacing_m = 120, 80, 0.5
    i.condition, i.water = rm.JointCondition76.SlightlyRoughSlightlyWeathered, rm.Water76.CompletelyDry
    return rm.rmr76(i).info


def _rmr14():
    i = rm.Rmr14Input()
    i.strength_rating, i.joints_per_m_rating, i.continuity_m, i.id2_pct = 10, 30, 2.0, 90
    i.roughness, i.infilling, i.alteration = rm.Roughness14.Rough, rm.Infilling14.HardUnder5mm, rm.Alteration14.Moderately
    i.water = rm.Water.Damp
    return rm.rmr14(i).info


def _q(edition):
    return lambda: rm.q_value(rm.QInput(60, 9, 1.5, 1, 1, 2.5), edition).info


_CORE_INFO: dict[str, Callable] = {
    "RMR76": _rmr76, "RMR89": _rmr89, "RMR14": _rmr14,
    "Q-NGI-2015": _q(rm.QEdition.NGI2015), "Q-NGI-2025": _q(rm.QEdition.NGI2025),
    "GSI-2013": lambda: rm.gsi_from_jcond89_rqd(15, 60).info,
}
_Q_EDITIONS = ("Q-NGI-2015", "Q-NGI-2025")


def _method_ref(edition: str, lang: str) -> MethodRef:
    if edition in _CORE_INFO:
        i = _CORE_INFO[edition]()
        return MethodRef(i.method_id, i.verification.name, i.source)
    chart = GSI_CHARTS.get(edition)  # cartillas GSI: traen su propia verificación y fuente
    if chart is not None:
        return MethodRef(chart.chart_id, chart.verification.capitalize(), chart.source)
    return MethodRef(edition, "-", t("unknown_method", lang))


def _methods(results, tables, lang) -> tuple[MethodRef, ...]:
    eds: dict[str, None] = {}  # orden de aparición, sin repetidos
    refs: list[MethodRef] = []
    for lt in tables:
        eds[lt.table.chart.chart_id if isinstance(lt.table, CellTable) else lt.table.base_edition] = None
        for c in lt.correlations:
            refs.append(MethodRef(f"site:{c.name}", "UserDefined", c.source or t("user_defined", lang)))
    for r in results:  # Q calculado desde sus parámetros: la edición que usó el lote
        tramo = r.tramo
        if r.method == "Q" and tramo.q_valor is None and r.input_value is not None:
            eds[tramo.q_edicion if tramo.q_edicion in _Q_EDITIONS
                else r.base_edition if r.base_edition in _Q_EDITIONS else "Q-NGI-2025"] = None
    if _q_chart_edition(results):  # la carta digitalizada trae su método; las fórmulas [V2] no van en el lote
        i = next(r.q_chart.roof.info for r in results if r.q_chart)
        refs.append(MethodRef(i.method_id, i.verification.name, i.source))
    out: dict[str, MethodRef] = {}
    for m in [_method_ref(e, lang) for e in eds] + refs:
        out.setdefault(m.method_id, m)
    return tuple(out.values())


# --- Carta Q (referencia) ---

def _q_chart_edition(results) -> str | None:
    """Edición de la carta usada por el lote (una sola, R13); None si ningún tramo trae referencia."""
    eds = sorted({r.q_chart.edition for r in results if r.q_chart})
    if len(eds) > 1:
        raise ValueError(f"the report supports one Q edition per run, got {eds}")
    return eds[0] if eds else None


def _has_q(results) -> bool:
    """Se pidió la referencia de la carta (con o sin éxito); es la misma condición que usa `_columns`."""
    return any(r.q_chart or r.q_chart_warnings for r in results)


def _range(v) -> str:
    return "-" if v is None else f"{v[0]:g}-{v[1]:g}" if v[1] is not None else f">{v[0]:g}"


def _q_chart_blocks(results, lang: str, figures: bool) -> tuple:
    from ..viz import plot_q_chart
    from ..viz.style import Style, text

    edition = _q_chart_edition(results)
    intro = Paragraph(t("qchart_text", lang).format(edition=f" ({edition})" if edition else ""))
    if edition is None:  # se pidió la referencia pero ningún tramo la obtuvo
        return (intro, Paragraph(t("qchart_none", lang)))
    refs = [r for r in results if r.q_chart]
    labors: dict[str, tuple] = {}  # _key -> (rótulo como lo escribió el usuario, categoría ESR, ESR usado)
    for r in refs:
        labors.setdefault(_key(r.tramo.tipo_labor), (r.tramo.tipo_labor, r.q_chart.esr_category, r.q_chart.esr_used))
    ct = q_chart_crosstab(results)
    cats = sorted({c for _, c in ct})
    rows = tuple((s, *(str(ct.get((s, c), 0)) for c in cats))
                 for s in sorted({s for s, _ in ct}, key=lambda s: (s == "unclassified", s)))
    legend = tuple((str(k), text(f"q_cat_{k}", lang), _range(c.shotcrete_mm), _str(c.sfr_energy_j), c.rrs or "-")
                   for k, c in sorted(Q_CHARTS[edition].categories.items()))
    nota = (Paragraph(t("qchart_esr_note", lang)),) if any(r.q_chart.notes for r in refs) else ()
    return (
        intro,
        *nota,
        Table(t("cap_esr", lang), (t("h_labor", lang), t("h_esr_cat", lang), t("h_esr", lang)),
              tuple((a, b, _str(c)) for a, b, c in labors.values())),
        Table(t("cap_crosstab", lang), (t("h_support", lang), *(f"Q {c}" for c in cats)), rows),
        _fig(t("fig_qchart", lang), lambda: plot_q_chart(edition, results=refs, style=Style(lang=lang)), lang, figures),
        Table(t("cap_qlegend", lang), (t("h_qcat", lang), t("h_label", lang), t("h_shotcrete", lang),
                                       t("h_energy", lang), t("h_rrs", lang)), legend),
    )


# --- Figuras ---

def _fig(caption, draw, lang, enabled) -> Figure:
    """PNG en memoria; sin matplotlib (o con figures=False) queda png=None y la nota."""
    if enabled:
        try:
            fig = draw()
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=fig.dpi)
            return Figure(caption, buf.getvalue())
        except ImportError:
            pass
    return Figure(caption, None, t("no_figures", lang))


def _str(v) -> str:
    return "" if v is None else f"{v:g}" if isinstance(v, float) else str(v)


def _label(lt: LaborTable, lang: str) -> str:
    if not lt.span_m:
        return lt.labor_type
    return f"{lt.labor_type} ({t('span', lang)} {lt.span_m[0]:g}-{lt.span_m[1]:g} m)"


def _class_rows(lt: LaborTable) -> tuple[str, tuple]:
    """Edición base y filas (rango o celda, clase, sostenimiento) de una tabla de la labor."""
    tab = lt.table
    if isinstance(tab, CellTable):
        return tab.base_edition, tuple((c.cell, c.label or c.cell, c.support or "") for c in tab.cells)
    return tab.base_edition, tuple((f"{c.lo:g}-{c.hi:g}", c.label, c.support or "")
                                   for c in sorted(tab.classes, key=lambda c: c.lo))


def _tables_section(tables, lang, figures, number="3", title_key="s3") -> Section:
    from ..viz import plot_cartilla
    from ..viz.cartilla import _describe  # descripción de elementos en palabras; no importa matplotlib
    from ..viz.style import Style

    head = (t("h_range", lang), t("h_class", lang), t("h_support", lang))
    subs = []
    for k, lt in enumerate(tables, 1):
        edition, rows = _class_rows(lt)
        cat = tuple((s.code, _describe(s, lang)) for s in lt.catalog.ordered())
        blocks = (
            Paragraph(edition),
            Table(t("cap_classes", lang), head, rows),
            Table(t("cap_catalog", lang), (t("h_support", lang), t("h_description", lang)), cat),
            _fig(f"{t('fig_cartilla', lang)}: {_label(lt, lang)}",
                 lambda lt=lt: plot_cartilla(lt, style=Style(lang=lang, size="cartilla")), lang, figures),
        )
        subs.append(Section(f"{number}.{k}", _label(lt, lang), blocks))
    return Section(number, t(title_key, lang), tuple(subs))


def _summary_section(results, tables, lang, figures) -> Section:
    from ..viz import plot_class_histogram
    from ..viz.style import Style

    s = summarize(results)
    blocks = [
        Table(t("cap_totals", lang), ("", t("h_count", lang)),
              ((t("total", lang), str(s.total)), (t("classified", lang), str(s.classified)),
               (t("unclassified", lang), str(s.unclassified)))),
        Table(t("cap_by_class", lang), (t("h_labor", lang), t("h_class", lang), t("h_count", lang)),
              tuple((a, b, str(n)) for (a, b), n in sorted(s.by_labor_class.items()))),
        Table(t("cap_by_support", lang), (t("h_support", lang), t("h_count", lang)),
              tuple((k, str(n)) for k, n in sorted(s.by_support.items()))),
    ]
    for lt in tables:
        if isinstance(lt.table, RangeTable):  # las tablas de celdas solo llevan los conteos
            vals = [r.input_value for r in results
                    if r.labor_type == lt.labor_type and r.span_m == lt.span_m and r.input_value is not None]
            if vals:
                blocks.append(_fig(
                    f"{t('fig_hist', lang)}: {_label(lt, lang)}",
                    lambda lt=lt, vals=vals: plot_class_histogram(vals, lt.table, catalog=lt.catalog,
                                                                  style=Style(lang=lang)),
                    lang, figures))
    return Section("5", t("s5", lang), tuple(blocks))


def _profile_figs(results, tables, lang, figures) -> list:
    from ..viz import plot_labor_profile
    from ..viz.style import Style

    st = Style(lang=lang)
    cat_of = {}
    for lt in tables:
        cat_of.setdefault(_key(lt.labor_type), lt.catalog)
    blocks = []
    chained = [r for r in results if r.tramo.progresiva_inicio_m is not None and r.tramo.progresiva_fin_m is not None]
    for labor in sorted({r.tramo.tipo_labor for r in chained}):
        blocks.append(_fig(f"{t('fig_profile', lang)}: {labor}",
                           lambda labor=labor: plot_labor_profile(chained, labor_type=labor,
                                                                  catalog=cat_of.get(_key(labor)), style=st),
                           lang, figures))
    return blocks


def _maps_section(results, tables, lang, figures) -> Section:
    from ..viz import plot_plan_map
    from ..viz.style import Style

    st = Style(lang=lang)
    cat_of = {}
    for lt in tables:
        cat_of.setdefault(_key(lt.labor_type), lt.catalog)
    blocks = _profile_figs(results, tables, lang, figures)
    if any(r.tramo.este_m is not None and r.tramo.norte_m is not None for r in results):
        cat = next(iter(cat_of.values())) if len(cat_of) == 1 else None  # varios catálogos: color por orden
        blocks.append(_fig(t("fig_plan", lang), lambda: plot_plan_map(results, catalog=cat, style=st), lang, figures))
        blocks.append(Paragraph(t("plan_note", lang)))
    if not blocks:
        blocks.append(Paragraph(t("no_maps", lang)))
    return Section("6", t("s6", lang), tuple(blocks))


def build_memoria(results, tables, *, title: str, lang: str = "es", author: str = "", date: str = "",
                  figures: bool = True) -> Report:
    """Memoria de cálculo con las 8 secciones; independiente del formato de salida."""
    _check_lang(lang)
    results, tables = list(results), list(tables)
    methods = _methods(results, tables, lang)
    s2 = Section("2", t("s2", lang), (Table(
        t("cap_methods", lang), (t("h_method", lang), t("h_verification", lang), t("h_source", lang)),
        tuple((m.method_id, m.verification, m.source) for m in methods)),))
    cols = _columns(results)
    s4 = Section("4", t("s4", lang), (Table(
        t("cap_results", lang), cols,
        tuple(tuple(_str(v) for v in _fila(r, len(cols) > len(_COLUMNS))) for r in results)),))
    # avisos únicos con la cantidad de tramos que los tienen; nunca qué id_tramo
    counts = Counter(w for r in results for w in set(r.warnings))
    if counts:
        s7_blocks = (Table(t("cap_warnings", lang), (t("h_warning", lang), t("h_count", lang)),
                           tuple((w, str(n)) for w, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))),)
    else:
        s7_blocks = (Paragraph(t("no_warnings", lang)),)
    qw = Counter(w for r in results for w in set(r.q_chart_warnings)) if _has_q(results) else None
    if qw:
        s7_blocks += (Table(t("cap_qwarnings", lang), (t("h_warning", lang), t("h_count", lang)),
                            tuple((w, str(n)) for w, n in sorted(qw.items(), key=lambda kv: (-kv[1], kv[0])))),)
    s5 = _summary_section(results, tables, lang, figures)
    if _has_q(results):
        s5 = replace(s5, blocks=s5.blocks + (Section("5.1", t("s5_qchart", lang),
                                                     _q_chart_blocks(results, lang, figures)),))
    sections = (
        Section("1", t("s1", lang), (Paragraph(t("s1_text", lang)),)),
        s2,
        _tables_section(tables, lang, figures),
        s4,
        s5,
        _maps_section(results, tables, lang, figures),
        Section("7", t("s7", lang), s7_blocks),
        Section("8", t("s8", lang), (Paragraph(t("s8_text", lang)),)),
    )
    return Report(title, _subtitle(t("memoria_title", lang), author, lang), lang, sections, methods, DISCLAIMER[lang], __version__,
                  date or datetime.date.today().isoformat())


def _subtitle(base, author, lang) -> str:
    return f"{base} · {t('prepared_by', lang)} {author}" if author else base


def _check_lang(lang) -> None:
    if lang not in DISCLAIMER:
        raise ValueError(f"lang must be one of 'es', 'en', got {lang!r}")


def _filter_labor(results, tables, labor_type):
    """Deja solo la labor pedida, igualada como lo hace el lote (`_key`); si no hay ninguna, lista las disponibles."""
    if labor_type is None:
        return results, tables
    want = _key(labor_type)
    rs = [r for r in results if _key(r.tramo.tipo_labor) == want]
    ts = [lt for lt in tables if _key(lt.labor_type) == want]
    if not rs and not ts:
        avail = sorted({r.tramo.tipo_labor for r in results} | {lt.labor_type for lt in tables})
        raise ValueError(f"labor_type {labor_type!r} matches nothing; available labor types: {avail}")
    return rs, ts


def _cols(r, names) -> tuple[str, ...]:
    fila = _fila(r)
    return tuple(_str(fila[_COLUMNS.index(n)]) for n in names)


def _input_summary(results, tables, lang) -> Section:
    """Memoria resumen: clases o celdas de cada tabla, parámetros del Q usados y correlaciones propias."""
    head = (t("h_range", lang), t("h_class", lang), t("h_support", lang))
    blocks: list = []
    for lt in tables:
        edition, rows = _class_rows(lt)
        blocks.append(Table(f"{_label(lt, lang)} ({edition})", head, rows))
    q_rows = tuple(
        tuple(_str(v) for v in (r.tramo.id_tramo, r.tramo.rqd_pct, r.tramo.jn, r.tramo.jr, r.tramo.ja,
                                r.tramo.jw, r.tramo.srf))
        for r in results if r.method == "Q" and r.label is not None)
    if q_rows:
        blocks.append(Table(t("cap_q_params", lang), ("id_tramo", "RQD", "Jn", "Jr", "Ja", "Jw", "SRF"), q_rows))
    corr = tuple((c.name, c.from_, c.to, c.form.name, _str(c.a), _str(c.b), _str(c.valid_min), _str(c.valid_max),
                  c.source) for lt in tables for c in lt.correlations)
    if corr:
        blocks.append(Table(t("cap_corr", lang), (t("h_name", lang), t("h_from", lang), t("h_to", lang),
                                                  t("h_form", lang), "a", "b", t("h_valid_min", lang),
                                                  t("h_valid_max", lang), t("h_source", lang)), corr))
    return Section("", t("a_summary", lang), tuple(blocks))


def build_anexo39b(results, tables, *, title: str, labor_type: str | None = None, lang: str = "es",
                   author: str = "", date: str = "", figures: bool = True, stopes=()) -> Report:
    """Informe con la estructura del Anexo 39 B del DS 024-2016-EM; lo que la librería no calcula queda por completar.

    `stopes` (resultados de `assess_stope_surfaces`) agrega las caras de tajeo al final de la 4.1.

    `author` va en el subtítulo, igual que en build_memoria; el autor del Word se pasa a write_docx.
    """
    _check_lang(lang)
    results, tables = _filter_labor(list(results), list(tables), labor_type)
    methods = _methods(results, tables, lang)
    stopes = list(stopes)
    if stopes:
        methods = _merge_methods(methods, stopes)

    def todo(number, key, guide, *subs):
        return Section(number, t(key, lang), (Paragraph(t(guide, lang)), *subs), True)

    cols3 = ("id_tramo", "tipo_labor", "luz_m", "clase", "sostenimiento")
    s3 = Section("3", t("a_s3", lang), (
        Table(t("cap_tramos", lang), cols3, tuple(_cols(r, cols3) for r in results)),
        *_profile_figs(results, tables, lang, figures)))
    cols = _columns(results)
    q_blocks = _q_chart_blocks(results, lang, figures) if _has_q(results) else ()
    s41 = Section("4.1", t("a_s41", lang), (
        Table(t("cap_results", lang), cols,
              tuple(tuple(_str(v) for v in _fila(r, len(cols) > len(_COLUMNS))) for r in results)),
        Table(t("cap_methods", lang), (t("h_method", lang), t("h_verification", lang), t("h_source", lang)),
              tuple((m.method_id, m.verification, m.source) for m in methods)),
        *q_blocks, *(_stope_blocks(stopes, lang, figures) if stopes else ())))
    s4 = Section("4", t("a_s4", lang), (
        s41, todo("4.2", "a_s42", "g42"),
        todo("4.3", "a_s43", "g43", todo("4.3.1", "a_s431", "g431"), todo("4.3.2", "a_s432", "g432"))))
    sections = (
        todo("1", "a_s1", "g1"),
        _tables_section(tables, lang, figures, "2", "a_s2"),
        s3, s4, todo("5", "a_s5", "g5"), todo("6", "a_s6", "g6"),
        _input_summary(results, tables, lang),
    )
    return Report(title, _subtitle(t("a_subtitle", lang), author, lang), lang, sections, methods, DISCLAIMER[lang], __version__,
                  date or datetime.date.today().isoformat())


def _merge_methods(methods, stopes) -> tuple:
    """Suma los métodos de Mathews a `methods` sin repetir el par (method_id, source)."""
    out = {(m.method_id, m.source): m for m in methods}
    for r in stopes:
        for m in r.mathews.methods:
            out.setdefault((m.method_id, m.source), MethodRef(m.method_id, m.verification.name, m.source))
    return tuple(out.values())


def _stope_blocks(results, lang: str, figures: bool) -> tuple:
    """Tabla de caras, conteo por zona y gráfico; la 2C puede reusarlos en el Anexo 39 B."""
    from ..stope_surfaces import stope_zone_counts
    from ..viz import plot_stability_graph
    from ..viz.style import Style

    head = ("id_superficie", "Q'", "A", "B", "C", t("h_mode", lang), "N'", "HR (m)", t("h_zone", lang))
    rows = tuple((r.id_superficie, *(_str(round(v, 4)) for v in (m.q_prime, m.factor_a, m.factor_b, m.factor_c)),
                  m.failure_mode, _str(round(m.n_prime, 4)), _str(round(m.hr_m, 3)),
                  f"{m.reading.zone} {t(f'zone_{m.reading.zone}', lang)}")
                 for r in results for m in (r.mathews,))
    counts = stope_zone_counts(results)
    graph = results[0].mathews.graph
    cases = [(r.mathews.reading.x, r.mathews.reading.y) for r in results]
    return (
        Table(t("cap_surfaces", lang), head, rows),
        Table(t("cap_zones", lang), (t("h_zone", lang), t("h_faces", lang)),
              tuple((f"{z} {t(f'zone_{z}', lang)}", str(n)) for z, n in counts.items())),
        _fig(t("fig_stability", lang),
             lambda: plot_stability_graph(graph, cases=cases, style=Style(lang=lang)), lang, figures),
    )


def build_stope_report(results, *, title: str, lang: str = "es", author: str = "", date: str = "",
                       figures: bool = True) -> Report:
    """Informe de diseño de tajeos (Mathews): alcance, métodos, resultados, avisos y nota."""
    _check_lang(lang)
    results = list(results)
    if not results:
        raise ValueError("results is empty: nothing to report")
    methods = _merge_methods((), results)
    counts = Counter(w for r in results for w in set(r.mathews.warnings))
    s4 = (Table(t("cap_st_warnings", lang), (t("h_warning", lang), t("h_faces", lang)),
                tuple((w, str(n)) for w, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))),
          ) if counts else (Paragraph(t("no_warnings", lang)),)
    sections = (
        Section("1", t("st_s1", lang), (Paragraph(t("st_scope", lang)),)),
        Section("2", t("st_s2", lang), (Table(
            t("cap_methods", lang), (t("h_method", lang), t("h_verification", lang), t("h_source", lang)),
            tuple((m.method_id, m.verification, m.source) for m in methods)),)),
        Section("3", t("st_s3", lang), _stope_blocks(results, lang, figures)),
        Section("4", t("st_s4", lang), s4),
        Section("5", t("st_s5", lang), (Paragraph(DISCLAIMER[lang]),)),
    )
    return Report(title, _subtitle(t("stope_title", lang), author, lang), lang, sections, methods, DISCLAIMER[lang],
                  __version__, date or datetime.date.today().isoformat())


_SLOPE_MODES = ("planar", "wedge", "flexural_toppling", "direct_toppling")


def _slope_critical(r, mode: str) -> tuple[int, int]:
    """(casos críticos, total) del modo en el talud; (0, 0) si no hubo cinemática."""
    k = r.kinematics
    if k is None:
        return 0, 0
    if mode in ("planar", "flexural_toppling"):
        return getattr(k, mode), k.n_planes
    if mode == "wedge":
        return sum(bool(c.wedge_primary or c.wedge_secondary) for c in k.intersections), k.n_intersections
    return k.direct_toppling, k.n_intersections


def slope_modes(r) -> list[str]:
    """Modos con al menos un caso crítico: cada uno lleva su estereograma."""
    k = r.kinematics
    return [m for m in _SLOPE_MODES if _slope_critical(r, m)[0] > 0
            or (m == "direct_toppling" and k is not None and k.direct_toppling_oblique > 0)]


def _attention(r) -> list[str]:
    """Claves de texto de lo que hace que el talud pida atención (las mismas condiciones de `needs_attention`)."""
    k, d, c = r.kinematics, r.smr_discrete, r.smr_continuous
    out = []
    if k is not None:
        out += [f"att_{x}" for x in ("planar", "wedge_primary", "wedge_secondary", "flexural_toppling",
                                     "direct_toppling", "direct_toppling_oblique") if getattr(k, x)]
    if (d is not None and d.discrete.smr_class >= 4) or (c is not None and c.continuous.smr_class >= 4):
        out.append("att_smr")
    if r.face_steeper_than_beta:
        out.append("att_qslope")
    if r.warnings:
        out.append("att_warnings")
    return out


def slope_figure(r, mode: str | None, lang: str, projection: str = "equal_area"):
    """Estereograma del talud: densidad (mode=None) o la zona crítica de un modo."""
    from ..viz import plot_stereonet
    from ..viz.style import Style

    k = r.kinematics
    lines = [rm.plane_intersection(r.planes[a], r.planes[b]) for a, b in zip(k.pair_a, k.pair_b)] if k else []
    return plot_stereonet(
        r.planes, families=[(f.familia, f.mean_plane) for f in r.families], face=r.face,
        friction_deg=k.input.friction_deg if k else None,
        lateral_limit_deg=k.input.lateral_limit_deg if k else None, mode=mode,
        intersections=[x for x in lines if x is not None], projection=projection,
        density=mode is None, style=Style(lang=lang))


def _orient(p) -> str:
    return f"{p.dip_deg:.0f}/{p.dip_direction_deg:03.0f}"


def _kcell(k: int, n: int) -> str:
    return f"{k}/{n} ({100 * k / n:.0f} %)" if n else "-"


def _kappa(v) -> str:
    return "-" if v is None else "∞" if v == float("inf") else f"{v:.1f}"


def _slope_blocks(results, lang: str, figures: bool, projection: str = "equal_area") -> tuple:
    """Tablas de taludes, familias, SMR y Q-slope, y las figuras por talud; la 3D puede reusarlas."""
    from ..viz.style import text

    modes_h = tuple(text(f"stereo_mode_{m}", lang) for m in _SLOPE_MODES)
    slopes = tuple(
        (r.id_talud, r.id_tramo, _orient(r.face),
         *(_str(v) for v in ((r.kinematics.input.friction_deg, r.kinematics.input.lateral_limit_deg)
                             if r.kinematics else ("", ""))),
         *(_kcell(*_slope_critical(r, m)) for m in _SLOPE_MODES),
         _kcell(r.kinematics.direct_toppling_oblique, r.kinematics.n_intersections) if r.kinematics else "-")
        for r in results)
    fams: dict[tuple, tuple] = {}
    for r in results:
        for f in r.families:
            fams.setdefault((r.id_tramo, f.familia), (
                r.id_tramo, f.familia, str(f.n), _orient(f.mean_plane), _kappa(f.fisher.kappa),
                "-" if f.fisher.alpha95_deg is None else f"{f.fisher.alpha95_deg:.1f}"))

    def cls(n):
        return f"{('I', 'II', 'III', 'IV', 'V')[n - 1]} ({t(f'smr_class_{n}', lang)})"

    smr = []
    for r in results:
        for c in r.smr_cases:
            d, k = c.discrete, c.continuous
            a = d.angles
            gov = "+".join(x for x, g in (("D", r.smr_discrete), ("C", r.smr_continuous)) if g is c)
            smr.append((r.id_talud, c.label, t(f"smr_mode_{c.mode}", lang), *(f"{v:.0f}" for v in (a.a_deg, a.b_deg, a.c_deg)),
                        *(f"{getattr(d, f'f{i}'):g} / {getattr(k, f'f{i}'):.2f}" for i in (1, 2, 3, 4)),
                        f"{d.smr:.1f}", cls(d.smr_class), f"{k.smr:.1f}", cls(k.smr_class), gov))
    qs = tuple((r.id_talud, f"{r.q_slope.q_slope:.3g}", f"{r.q_slope.beta_deg:.1f}", f"{r.face.dip_deg:.0f}",
                t("sl_yes" if r.face_steeper_than_beta else "sl_no", lang)) for r in results if r.q_slope)
    figs = []
    for n, r in enumerate(results, 1):
        figs.append(_fig(t("fig_stereo_density", lang).format(n=n),
                         lambda r=r: slope_figure(r, None, lang, projection), lang, figures))
        for m in slope_modes(r):
            figs.append(_fig(t("fig_stereo_mode", lang).format(mode=text(f"stereo_mode_{m}", lang), n=n),
                             lambda r=r, m=m: slope_figure(r, m, lang, projection), lang, figures))

    def tab(key, head, rows):
        return Table(t(key, lang), head, tuple(rows)) if rows else Paragraph(f"{t(key, lang).rstrip('.')}: {t('none_items', lang)}")

    return (
        tab("cap_slopes", ("id_talud", "id_tramo", t("h_face", lang), "φ (°)", "L (°)", *modes_h, t("h_oblique", lang)), slopes),
        tab("cap_families", ("id_tramo", t("h_family", lang), "N", t("h_mean_orientation", lang), "κ", "α95 (°)"),
            fams.values()),
        tab("cap_smr", ("id_talud", t("h_case", lang), t("h_mode_smr", lang), "A", "B", "C", "F1", "F2", "F3", "F4",
                        "SMR D", f"{t('h_class', lang)} D", "SMR C", f"{t('h_class', lang)} C", t("h_governing", lang)),
            smr),
        tab("cap_qslope", ("id_talud", "Q-slope", t("h_beta", lang), t("h_face_dip", lang), t("h_steeper", lang)),
            qs),
        *figs)


def _num(v, fmt: str = ".3f") -> str:
    """Celda numérica: «-» sin dato, «∞» para FS sin fuerza que deslice."""
    if v is None:
        return "-"
    return "∞" if v == float("inf") else format(v, fmt)


def block_figure(r, kind: str, lang: str):
    """Histograma (kind="hist") o curva de PoF ("cdf") de un bloque probabilístico; el título lleva su número de orden."""
    from ..viz import plot_fs_cdf, plot_fs_histogram
    from ..viz.style import Style

    plot = plot_fs_histogram if kind == "hist" else plot_fs_cdf
    return plot(r.probabilistic, title=t(f"fig_fs_{kind}", lang).format(n=r.order), style=Style(lang=lang))


def _block_blocks(blocks, lang: str, figures: bool) -> tuple:
    """Tablas de bloques (R17) en su orden, cada una solo si tiene filas, y las figuras por número de orden."""
    from ..blocks import block_attention, block_mode
    from ..viz.style import text

    def yes(v):
        return t("sl_yes" if v else "sl_no", lang)

    out = [Table(t("cap_blocks", lang),
                 ("id_bloque", "id_talud", t("h_model", lang), t("h_block_mode", lang), t("h_fs", lang),
                  t("h_fs_le1", lang)),
                 tuple((r.id_bloque, r.id_talud, t(f"model_{r.model}", lang),
                        "-" if block_mode(r) is None else t(f"bmode_{block_mode(r)}", lang), _num(r.fs),
                        "-" if r.fs is None else yes("att_fs_below_1" in block_attention(r))) for r in blocks))]
    prob = tuple((r.id_bloque, text("prob_lhs" if p.sampling == "lhs" else "prob_monte_carlo", lang),
                  f"{p.n_valid}/{p.n}", str(p.seed), _num(p.fs_mean), _num(p.fs_sd), _num(p.fs_min), _num(p.fs_max),
                  _num(None if p.pof is None else p.pof * 100, ".1f"), _num(p.reliability_index, ".2f"),
                  _num(p.reliability_index_lognormal, ".2f"))
                 for r in blocks for p in (r.probabilistic,) if p is not None)
    back = tuple((r.id_bloque, _num(phi, "g"), _num(c, ".1f"), _num(b.friction_at_zero_cohesion_deg, ".2f"))
                 for r in blocks for b in (r.back_analysis,) if b is not None
                 for phi, c in zip(b.friction_deg, b.cohesion))
    berms = tuple((r.id_bloque, r.id_talud, _num(b.bench_height_m, ".1f"), _num(b.berm_width_m, ".2f"),
                   _num(b.ritchie.width_m, ".2f"), _num(b.required_width_m, ".2f"), _num(b.interramp_deg, ".1f"),
                   yes(b.narrower_than_required),
                   _num(None if b.reliability is None else b.reliability.reliability * 100, ".1f"),
                   *(("-",) * 3 if b.reliability is None else  # muestreo, n y semilla: la confiabilidad se reproduce
                     (text("prob_lhs" if b.sampling == "lhs" else "prob_monte_carlo", lang), str(b.reliability.n),
                      str(b.seed))))
                  for r in blocks for b in (r.berm,) if b is not None)
    if prob:
        out.append(Table(t("cap_prob", lang), ("id_bloque", t("h_sampling", lang), t("h_valid", lang),
                                               t("h_seed", lang), t("h_mean", lang), t("h_sd", lang),
                                               t("h_min", lang), t("h_max", lang), t("h_pof", lang),
                                               t("h_beta_n", lang), t("h_beta_ln", lang)), prob))
    if back:
        out.append(Table(t("cap_back", lang), ("id_bloque", "φ (°)", "c (kPa)", t("h_phi0", lang)), back))
    for r in blocks:  # una tabla por bloque de volteo, como las Tablas 1 y 2 de Goodman y Bray
        if r.model == "toppling" and r.deterministic is not None:
            out.append(Table(t("cap_topple", lang).format(n=r.order),
                             ("n", "y (m)", t("h_state", lang), "Pt", "Ps", "Pn−1", "R", "S"),
                             tuple((str(k.n), _num(k.height_m, ".2f"), t(f"topple_{k.state.name.lower()}", lang),
                                    *(_num(v, ".1f") for v in (k.p_toppling, k.p_sliding, k.p_lower, k.normal,
                                                               k.shear)))
                                   for k in r.deterministic.forces.blocks)))
    if berms:
        out.append(Table(t("cap_berms", lang), ("id_bloque", "id_talud", t("h_bench_h", lang), t("h_berm_w", lang),
                                                t("h_ritchie", lang), t("h_required", lang), t("h_ira", lang),
                                                t("h_narrower", lang), t("h_berm_rel", lang), t("h_sampling", lang),
                                                "n", t("h_seed", lang)), berms))
    for r in blocks:
        if r.probabilistic is not None:
            for kind in ("hist", "cdf"):
                out.append(_fig(t(f"fig_fs_{kind}", lang).format(n=r.order),
                                lambda r=r, kind=kind: block_figure(r, kind, lang), lang, figures))
    return tuple(out)


def le_figure(r, lang: str):
    """Sección de equilibrio límite de un análisis; el título lleva su número de orden, nunca el id."""
    from ..viz import plot_le_section
    from ..viz.style import Style

    return plot_le_section(r, title=t("fig_le_section", lang).format(n=r.order), style=Style(lang=lang))


def newmark_figure(r, lang: str):
    """Registro escalado, ky y desplazamiento acumulado de un análisis con Newmark."""
    from ..viz import plot_newmark
    from ..viz.style import Style

    return plot_newmark(r.newmark, r.record, r.yield_.ky, title=t("fig_newmark", lang).format(n=r.order),
                        style=Style(lang=lang))


def _le_blocks(le, lang: str, figures: bool) -> tuple:
    """Tabla «Equilibrio límite» (una fila por método, como el archivo), la de la superficie crítica y las figuras."""
    from ..limit_equilibrium import _points, le_static_fs
    from ..probabilistic import is_failure
    from ..viz.style import text

    rows, surf = [], []
    for r in le:
        ky = None if r.yield_ is None else r.yield_.ky
        nm = None if r.newmark is None else r.newmark.displacement_m
        for k, (x, fs0) in enumerate(zip(r.results, le_static_fs(r))):
            fs = x.factor_of_safety
            rows.append((r.id_analisis, r.id_seccion, t(f"le_surf_{r.surface_type}", lang),
                         text(f"le_method_{x.method.name}", lang), _num(r.kh), _num(fs), _num(fs0),
                         "-" if fs is None else t("sl_yes" if is_failure(fs) else "sl_no", lang),
                         # ky y Newmark solo en la fila del primer método, el que los calcula (como el archivo)
                         _num(x.lambda_), *((_num(ky), _num(nm)) if k == 0 else ("-", "-"))))
        c = None if r.surface is None else r.surface.circle
        s = r.search
        surf.append((r.id_analisis, t(f"le_surf_{r.surface_type}", lang),
                     *(("-",) * 3 if c is None else (_num(c.xc, ".2f"), _num(c.yc, ".2f"), _num(c.radius, ".2f"))),
                     _points(r.surface) or "-", "-" if s is None else str(s.evaluated),
                     "-" if s is None else str(s.discarded)))
    out = [Table(t("cap_le", lang), ("id_analisis", "id_seccion", t("h_le_surface", lang), t("h_le_method", lang),
                                     "kh", t("h_fs", lang), t("h_fs_static", lang), t("h_fs_le1", lang),
                                     t("h_lambda", lang), t("h_ky", lang), t("h_newmark", lang)), tuple(rows)),
           Table(t("cap_le_surface", lang), ("id_analisis", t("h_le_surface", lang), "xc (m)", "yc (m)", "R (m)",
                                             t("h_points", lang), t("h_evaluated", lang), t("h_discarded", lang)),
                 tuple(surf))]
    for r in le:
        out.append(_fig(t("fig_le_section", lang).format(n=r.order), lambda r=r: le_figure(r, lang), lang, figures))
        if r.newmark is not None and r.record is not None:
            out.append(_fig(t("fig_newmark", lang).format(n=r.order), lambda r=r: newmark_figure(r, lang), lang,
                            figures))
    return tuple(out)


def _count_table(key, head_key, counts, lang) -> Table:
    return Table(t(key, lang), (t("h_warning", lang), t(head_key, lang)),
                 tuple((w, str(n)) for w, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))))


def build_slope_report(results, *, title: str, lang: str = "es", author: str = "", date: str = "",
                       figures: bool = True, projection: str = "equal_area", blocks=(), le=()) -> Report:
    """Informe de taludes: alcance, métodos, resultados, avisos y nota. `blocks` (de `assess_blocks`) suma la 3B y
    `le` (de `assess_le`) el equilibrio límite de la 3C; con `le`, `results` puede ir vacío."""
    from ..blocks import block_attention, warning_counts
    from ..limit_equilibrium import le_attention, le_warning_counts

    _check_lang(lang)
    results, blocks, le = list(results), list(blocks), list(le)
    if not results and not le:
        raise ValueError("results is empty: nothing to report")
    methods = _dedup_methods(m for r in (*results, *blocks, *le) for m in r.methods)
    counts = Counter(w for r in results for w in set(r.warnings))
    bcounts = warning_counts(blocks)
    lcounts = le_warning_counts(le)
    notes = dict.fromkeys(n for r in (*results, *blocks, *le) for n in r.notes)
    s4 = ((_count_table("cap_sl_warnings", "h_slopes", counts, lang),) if counts else ())
    s4 += ((_count_table("cap_bl_warnings", "h_blocks", bcounts, lang),) if bcounts else ())
    s4 += ((_count_table("cap_le_warnings", "h_analyses", lcounts, lang),) if lcounts else ())
    s4 = s4 or (Paragraph(t("no_warnings", lang)),)
    why = Counter(x for r in results for x in _attention(r))
    n_att = sum(r.needs_attention for r in results)
    if n_att:
        s4 += (Paragraph(t("sl_attention", lang).format(n=n_att, m=len(results), why=", ".join(
            f"{t(k, lang)} ({v})" for k, v in why.items()))),)
    bwhy = Counter(x for r in blocks for x in block_attention(r))  # la misma regla que el código de salida
    b_att = sum(bool(block_attention(r)) for r in blocks)
    if b_att:
        s4 += (Paragraph(t("bl_attention", lang).format(n=b_att, m=len(blocks), why=", ".join(
            f"{t(k, lang)} ({v})" for k, v in bwhy.items()))),)
    lwhy = Counter(x for r in le for x in le_attention(r))  # la misma regla que el código de salida de `rockmass le`
    l_att = sum(bool(le_attention(r)) for r in le)
    if l_att:
        s4 += (Paragraph(t("le_attention", lang).format(n=l_att, m=len(le), why=", ".join(
            f"{t(k, lang)} ({v})" for k, v in lwhy.items()))),)
    if notes:
        s4 += (Paragraph(t("h_notes", lang) + ":"), *(Paragraph(n) for n in notes))
    sections = (
        Section("1", t("sl_s1", lang), ((Paragraph(t("sl_scope", lang)),) if results else ())
                + ((Paragraph(t("le_scope" if results else "le_scope_only", lang)),) if le else ())),
        Section("2", t("sl_s2", lang), (Table(
            t("cap_methods", lang), (t("h_method", lang), t("h_verification", lang), t("h_source", lang)),
            tuple((m.method_id, m.verification, m.source) for m in methods)),)),
        Section("3", t("sl_s3", lang), (_slope_blocks(results, lang, figures, projection) if results
                                        else (Paragraph(t("sl_no_slopes", lang)),))
                + (_block_blocks(blocks, lang, figures) if blocks else ())
                + (_le_blocks(le, lang, figures) if le else ())),
        Section("4", t("sl_s4", lang), s4),
        Section("5", t("sl_s5", lang), (Paragraph(DISCLAIMER[lang]),)),
    )
    return Report(title, _subtitle(t(slope_title_key(bool(results)), lang), author, lang), lang, sections, methods,
                  DISCLAIMER[lang], __version__, date or datetime.date.today().isoformat())


def slope_title_key(rock_slopes: bool) -> str:
    """Título del informe de taludes: «en roca» solo con taludes de la 3A; con solo equilibrio límite, sin «en roca»."""
    return "slope_title" if rock_slopes else "slope_title_le"


def _dedup_methods(methods) -> tuple:
    """Una fila por method_id; si las fuentes difieren, se unen con « · »."""
    out: dict[str, MethodRef] = {}
    for m in methods:
        prev = out.get(m.method_id)
        if prev is None:
            out[m.method_id] = MethodRef(m.method_id, m.verification.name, m.source)
        elif m.source not in prev.source.split(" · "):
            out[m.method_id] = MethodRef(prev.method_id, prev.verification, f"{prev.source} · {m.source}")
    return tuple(out.values())


def build_verification_report(verification: "VerificationResult", *, title: str, lang: str = "es", author: str = "",
                              date: str = "") -> Report:
    """Informe de verificación normativa: alcance, perfil, hallazgos por sección y nota. Sin identificadores de fila."""
    _check_lang(lang)
    prof, as_of = verification.profile, verification.as_of
    by = {s: [f for f in verification.findings if f.status == s]
          for s in ("complies", "does_not_comply", "attention", "note", "not_checked", "not_verifiable")}

    def force(i):
        return t(f"force_{i.force}", lang)

    esr = tuple((i.applies_to[0], str(i.value), force(i), i.source)
                for i in prof.items if i.check == "esr" and i.in_force(as_of))
    s2 = [Table(t("cap_profile", lang), (t("h_field", lang), t("h_value", lang)), (
              (t("h_id", lang), prof.profile_id), (t("h_jurisdiction", lang), prof.jurisdiction),
              (t("h_instruments", lang), "; ".join(prof.instruments)), (t("h_as_of", lang), as_of))),
          Table(t("cap_sources", lang), (t("h_source", lang), t("h_title", lang), "URL"),
                tuple((k, title_, url) for k, (title_, url) in prof.sources.items()))]
    if esr:
        s2.append(Table(t("cap_esr_profile", lang),
                        (t("h_labor", lang), "ESR", t("h_force", lang), t("h_source", lang)), esr))
    def orNone(table):  # una tabla vacía se reemplaza por un párrafo
        return (table,) if table.rows else (Paragraph(t("none_items", lang)),)

    judged = [f for s in ("complies", "does_not_comply", "attention", "note") for f in by[s]]
    counts = verification.counts()
    sections = (
        Section("1", t("vr_s1", lang), (Paragraph(t("vr_scope", lang)),)),
        Section("2", t("vr_s2", lang), tuple(s2)),
        Section("3", t("vr_s3", lang), (
            Table(t("cap_status_counts", lang), (t("h_status", lang), t("h_requirements", lang)),
                  tuple((t(f"st_{s}", lang), str(n)) for s, n in counts.items())),
            *orNone(Table(t("cap_findings", lang),
                  (t("h_status", lang), t("h_article", lang), t("h_page", lang), t("h_force", lang),
                   t("h_mark", lang), t("h_requirement", lang), t("h_detail", lang)),
                  tuple((t(f"st_{f.status}", lang), f.item.article, f.item.page, force(f.item), f.item.verification,
                         f.item.summary[lang], f.message) for f in judged))))),
        Section("4", t("vr_s4", lang), orNone(Table(
            t("cap_not_checked", lang),
            (t("h_article", lang), t("h_force", lang), t("h_requirement", lang), t("h_missing", lang)),
            tuple((f.item.article, force(f.item), f.item.summary[lang], f.message) for f in by["not_checked"])))),
        Section("5", t("vr_s5", lang), orNone(Table(
            t("cap_not_verifiable", lang),
            (t("h_article", lang), t("h_page", lang), t("h_force", lang), t("h_requirement", lang),
             t("h_detail", lang)),
            tuple((f.item.article, f.item.page, force(f.item), f.item.summary[lang], f.message)
                  for f in by["not_verifiable"])))),
        Section("6", t("vr_s6", lang), (Paragraph(DISCLAIMER[lang]),)),
    )
    return Report(title, _subtitle(t("verif_title", lang), author, lang), lang, sections, (), DISCLAIMER[lang],
                  __version__, date or datetime.date.today().isoformat())


from .docx import write_docx  # noqa: E402,F401
from .html import write_html  # noqa: E402,F401
