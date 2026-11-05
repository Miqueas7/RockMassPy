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

    return plot_newmark(r.newmark, r.record, r.ky, title=t("fig_newmark", lang).format(n=r.order),
                        style=Style(lang=lang))


def _le_blocks(le, lang: str, figures: bool) -> tuple:
    """Tabla «Equilibrio límite» (una fila por método, como el archivo), la de la superficie crítica y las figuras."""
    from ..limit_equilibrium import _points, le_static_fs
    from ..probabilistic import is_failure
    from ..viz.style import text

    rows, surf = [], []
    for r in le:
        ky = r.ky
        nm = None if r.newmark is None else r.newmark.displacement_m
        if r.sarma is not None:  # una fila, como el archivo: FS, FS estático, Kc como ky y Newmark
            fs, fs0 = r.sarma.factor_of_safety, le_static_fs(r)[0]
            rows.append((r.id_analisis, r.id_seccion, t("le_surf_sarma", lang), text("le_method_sarma", lang),
                         _num(r.kh), _num(fs), _num(fs0),
                         "-" if fs is None else t("sl_yes" if is_failure(fs) else "sl_no", lang), "-", _num(ky),
                         _num(nm)))
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
                       figures: bool = True, projection: str = "equal_area", blocks=(), le=(), criteria=None,
                       criteria_profile=None, range_policy: str | None = None, profile_checks=None) -> Report:
    """Informe de taludes: alcance, métodos, resultados, avisos y nota. `blocks` (de `assess_blocks`) suma la 3B y
    `le` (de `assess_le`) el equilibrio límite de la 3C; con `le`, `results` puede ir vacío.

    `criteria` (los chequeos de `assess_criteria`, con su `criteria_profile` y la `range_policy` usada; None = la del
    perfil) o `profile_checks` (los del perfil normativo, p. ej. el art. 264) dan el informe completo de la 3D:
    resumen ejecutivo, alcance y criterios, cinemática, bloques, equilibrio límite y Sarma, verificación, normativa,
    avisos y métodos. Sin ninguno de los dos, el informe es el de la 3C."""
    from ..blocks import block_attention, warning_counts
    from ..limit_equilibrium import le_attention, le_warning_counts

    _check_lang(lang)
    results, blocks, le = list(results), list(blocks), list(le)
    if not results and not le:
        raise ValueError("results is empty: nothing to report")
    if criteria is not None and criteria_profile is None:
        raise ValueError("criteria needs criteria_profile")
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
    if criteria is not None or profile_checks is not None:
        sections = _criteria_sections(results, blocks, le, lang, figures, projection, methods, s4, notes,
                                      criteria, criteria_profile, range_policy, profile_checks)
        return Report(title, _subtitle(t(slope_title_key(bool(results)), lang), author, lang), lang, sections,
                      methods, DISCLAIMER[lang], __version__, date or datetime.date.today().isoformat())
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


_CMP = {">=": "≥", "<=": "≤", ">": ">", "<": "<"}
_PCT_RULES = ("slope_pof", "berm_reliability")


def _crit_required(c, lang) -> str:
    if c.required is None:
        return "-"
    unit = (" %" if c.rule in _PCT_RULES
            else " " + t("years", lang) if c.rule == "pseudostatic_analysis_present" else "")
    return f"{_CMP[c.comparison]} {c.required:g}{unit}"


def _crit_rows(checks, lang) -> tuple:
    """Una fila por chequeo: objeto, id, criterio, regla, estado, requerido, obtenido, rango, razón y su respaldo."""
    return tuple((t(f"kind_{c.object_kind}", lang), c.object_id or "-", c.item_id or "-", t(f"rule_{c.rule}", lang),
                  t(f"cr_{c.status}", lang), _crit_required(c, lang),
                  _num(c.obtained, ".1f" if c.rule in _PCT_RULES else ".3f"), c.range_used or "-", c.reason or "-",
                  c.source or "-", t(f"force_{c.force}", lang), c.verification) for c in checks)


def _crit_summary(blocks, le, checks, lang) -> Table:
    """Una fila por objeto con sus resultados (los mismos valores que compara `assess_criteria`) y su estado por regla."""
    from ..criteria import _block_value, _le_value

    rules = list(dict.fromkeys(c.rule for c in checks))
    status: dict = {}
    for c in checks:
        status.setdefault((c.object_kind, c.object_id), {}).setdefault(c.rule, []).append(t(f"cr_{c.status}", lang))
    objs = [("berm" if r.model == "berm" else "block", r.id_bloque, r) for r in blocks]
    objs += [("le", r.id_analisis, r) for r in le]
    objs += [("le_set", "", None)] if any(c.object_kind == "le_set" for c in checks) else []
    rows = []
    for kind, oid, r in objs:
        if r is None:
            vals = ("-",) * 6
        elif kind == "le":
            vals = (r.escala or "-", r.consecuencia or "-", _num(_le_value("slope_fs_static", r)[0]),
                    _num(_le_value("slope_fs_pseudostatic", r)[0]), "-",
                    _num(None if r.newmark is None else r.newmark.displacement_m))
        else:
            pof = _block_value("slope_pof", r)[0]
            pseudo = _block_value("slope_fs_pseudostatic", r)[0] if r.kh > 0 else None  # con kh, el FS va aquí
            vals = (r.escala or "-", r.consecuencia or "-", _num(_block_value("slope_fs_static", r)[0]), _num(pseudo),
                    _num(None if pof is None else float(pof), ".1f"), "-")
        st = status.get((kind, oid), {})
        rows.append((t(f"kind_{kind}", lang), oid or "-", *vals, *(" / ".join(st.get(x, ["-"])) for x in rules)))
    return Table(t("cap_crit_summary", lang),
                 (t("h_object", lang), t("h_id_object", lang), t("h_scale", lang), t("h_consequence", lang),
                  t("h_fs_static", lang), t("h_fs_pseudo", lang), t("h_pof", lang), t("h_newmark", lang),
                  *(t(f"rule_{x}", lang) for x in rules)), tuple(rows))


def _crit_source(profile, key) -> str:
    """Título de la fuente con su URL y su `url_note` entre paréntesis (lo que haya)."""
    title_, url = profile.sources[key]
    extra = "; ".join(x for x in (url, profile.source_notes.get(key, "")) if x)
    return f"{title_} ({extra})" if extra else title_


def _why(att, lang) -> str:
    return ", ".join(f"{t(f'rule_{k}', lang)} ({v})" for k, v in sorted(att.items(), key=lambda kv: (-kv[1], kv[0])))


def _criteria_sections(results, blocks, le, lang, figures, projection, methods, s4, notes, criteria, profile,
                       range_policy, profile_checks) -> tuple:
    """Las nueve secciones del informe completo (3D). Conteos y atención salen de `criteria_counts` y
    `criteria_attention`, como la CLI; los ids solo van en celdas de tabla."""
    from ..criteria import criteria_attention, criteria_counts, profile_marks

    checks, pchecks = list(criteria or ()), list(profile_checks or ())
    counts, att = criteria_counts(checks), criteria_attention(checks)
    p_fails = sum(c.needs_attention for c in pchecks)
    att_paras = [Paragraph(t("crit_attention", lang).format(why=_why(att, lang)))] if att else []
    if p_fails:
        att_paras.append(Paragraph(t("crit_normative_fails", lang).format(n=p_fails)))

    if criteria is None:
        s1 = [Paragraph(t("crit_profile_only", lang)), *att_paras]
    else:
        s1 = [Paragraph(t("crit_counts", lang).format(n=counts["checks"], **counts)), *att_paras,
              _crit_summary(blocks, le, checks, lang)]

    s2 = [Paragraph(t("crit_scope", lang))]
    if criteria is None:
        s2.append(Paragraph(t("crit_profile_only", lang)))
    else:
        marks, forces = profile_marks(profile)
        policy = profile.range_policy if range_policy is None else range_policy
        s2.append(Table(t("cap_crit_profile", lang), (t("h_field", lang), t("h_value", lang)), (
            (t("h_id", lang), profile.profile_id), (t("h_name", lang), profile.name[lang]),
            (t("h_instruments", lang), "; ".join(profile.instruments)),
            (t("h_source", lang), "; ".join(dict.fromkeys(_crit_source(profile, k) for k in profile.sources))),
            (t("h_force", lang), "/".join(t(f"force_{f}", lang) for f in forces.split("/"))),
            (t("h_mark", lang), marks), (t("h_range_policy", lang), t(f"policy_{policy}", lang)))))
        s2 += [Paragraph(t(f"crit_mark_{m}", lang)) for m in ("V2", "user") if m in marks.split("/")]

    head = (t("h_object", lang), t("h_id_object", lang), t("h_criterion", lang), t("h_rule", lang),
            t("h_status", lang), t("h_crit_required", lang), t("h_obtained", lang), t("h_range_used", lang),
            t("h_reason", lang), t("h_source", lang), t("h_force", lang), t("h_mark", lang))
    if criteria is None:
        s6 = (Paragraph(t("crit_profile_only", lang)),)
    elif checks:
        s6 = (Table(t("cap_crit_checks", lang), head, _crit_rows(checks, lang)),)
    else:
        s6 = (Paragraph(t("none_items", lang)),)
    s7 = ((Table(t("cap_crit_normative", lang), head, _crit_rows(pchecks, lang)),) if pchecks
          else (Paragraph(t("crit_no_profile", lang)),))

    s8 = s4 + tuple(att_paras)
    if counts["not_verifiable"]:
        s8 += (Paragraph(t("crit_not_verifiable", lang).format(n=counts["not_verifiable"])),)
    if notes:
        s8 += (Paragraph(t("h_notes", lang) + ":"), *(Paragraph(n) for n in notes))
    return (
        Section("1", t("sx_1", lang), tuple(s1)),
        Section("2", t("sx_2", lang), tuple(s2)),
        Section("3", t("sx_3", lang), _slope_blocks(results, lang, figures, projection) if results
                else (Paragraph(t("sl_no_slopes", lang)),)),
        Section("4", t("sx_4", lang), _block_blocks(blocks, lang, figures) if blocks
                else (Paragraph(t("crit_no_blocks", lang)),)),
        Section("5", t("sx_5", lang), _le_blocks(le, lang, figures) if le else (Paragraph(t("crit_no_le", lang)),)),
        Section("6", t("sx_6", lang), s6),
        Section("7", t("sx_7", lang), s7),
        Section("8", t("sx_8", lang), s8),
        Section("9", t("sx_9", lang), (Table(
            t("cap_methods", lang), (t("h_method", lang), t("h_verification", lang), t("h_source", lang)),
            tuple((m.method_id, m.verification, m.source) for m in methods)), Paragraph(DISCLAIMER[lang]))),
    )


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


# --- histórico de la mina (Fase 4A: datos, auditoría de ingesta, preparación por nivel y nivel 1) ---

_FORMS = {"rmr_from_q": "RMR = a·ln Q + b", "gsi_from_rmr": "GSI = a·RMR + b", "gsi_from_q_prime": "GSI = a·ln Q′ + b"}


def site_fits(result) -> tuple:
    """La mina y luego cada dominio, en el orden D1, D2…"""
    return (result.mine, *result.domains.values())


def _years(dates) -> str:
    ys = sorted({d[:4] for d in dates if d})
    return f"{ys[0]}–{ys[-1]} ({len(ys)})" if ys else "-"


def _ci(v, ci) -> str:
    return f"{v:.4g}" + ("" if ci is None else f" ({ci[0]:.4g}; {ci[1]:.4g})")


def _prior_info(method_id: str):
    """(Correlation del núcleo, info) del prior; (None, None) si el núcleo no lo tiene."""
    c = getattr(rm.Correlation, method_id, None)
    if c is None:
        return None, None
    return c, rm.correlate(c, 1.0 if "FromQ" in c.name else 50.0)


def history_correlation_figure(result, history, lang: str):
    """Pares del sitio, la recta de la mina, su intervalo de predicción y la global (si va en los mismos ejes)."""
    from ..history import level1_rows
    from ..viz import plot_correlation
    from ..viz.style import Style

    f = result.mine
    # los mismos pares del ajuste: la edición de RMR del ajuste (x o y, según el par)
    ed = next((e for e in (f.x_from, f.y_to) if e.startswith("RMR")), None)
    sel = level1_rows(history, result.kind, rmr_edition=ed)
    c, r = _prior_info(result.prior_correlation)
    # la global del GSI va en RMR′ (sin agua ni orientación): en otros ejes que el RMR registrado, no se dibuja
    glob = [c] if c is not None and (r.from_, r.to) == (f.x_from, f.y_to) else []
    site = [s for s in (f.to_custom_correlation(),) if s is not None]  # None: un solo valor de x
    return plot_correlation(list(zip(sel.x, sel.y)), x=f.x_from, y=f.y_to, global_correlations=glob,
                            site=site, bands=[f], style=Style(lang=lang))


def _hist_data(audit, history, lang) -> Section:
    perf = next((r for r in audit.readiness if r.level == 3), None)
    w = perf.counts.get("tramos_with_inspections") if perf else None
    rows = [(t("hd_tramos", lang), str(audit.tramos)), (t("hd_types", lang), str(audit.support_types)),
            (t("hd_inspections", lang), str(audit.inspections)),
            (t("hd_with_insp", lang), "-" if w is None else str(w)),
            (t("hd_without_insp", lang), "-" if w is None else str(audit.tramos - w))]
    if history is not None:
        rows += [(t("hd_years_eval", lang), _years(x.fecha_evaluacion for x in history.tramos)),
                 (t("hd_years_insp", lang), _years(i.fecha_inspeccion for i in history.inspections))]
    return Section("1", t("hs_1", lang), (Paragraph(t("hist_scope", lang)),
                                         Table(t("cap_hist_data", lang), (t("h_item", lang), t("h_value", lang)),
                                               tuple(rows))))


def _hist_audit(audit, lang) -> Section:
    from ..history import FINDING_KINDS, history_audit_counts

    c = history_audit_counts(audit)
    blocks = [Paragraph(t("hist_audit_text", lang)),
              Table(t("cap_hist_kinds", lang), (t("h_kind", lang), t("h_findings", lang)),
                    tuple((k, str(c[k])) for k in FINDING_KINDS))]
    if audit.findings:  # el id_tramo y la fila van en celdas de tabla; el mensaje nunca los repite
        blocks.append(Table(t("cap_hist_findings", lang), (t("h_kind", lang), t("h_sheet", lang), t("h_row", lang),
                                                           "id_tramo", t("h_message", lang)),
                            tuple((f.kind, f.sheet, _str(f.fila), f.id_tramo or "-", f.message)
                                  for f in audit.findings)))
    else:
        blocks.append(Paragraph(t("hist_no_findings", lang)))
    return Section("2", t("hs_2", lang), tuple(blocks))


def _hist_readiness(audit, lang) -> Section:
    def kv(d):
        return "; ".join(f"{k} {v}" for k, v in d.items())

    rows = tuple((str(r.level), r.item, kv({k: r.counts.get(k, 0) for k in r.minimums}), kv(r.minimums),
                  kv(r.missing), t("ready_yes" if r.ready else "ready_no", lang)) for r in audit.readiness)
    return Section("3", t("hs_3", lang), (
        Paragraph(t("hist_readiness_text", lang)),
        Table(t("cap_hist_readiness", lang), (t("h_level", lang), t("h_item", lang), t("h_available", lang),
                                              t("h_minimum_dd", lang), t("h_lacking", lang), t("h_ready", lang)),
              rows)))


def _hist_kind(k, result, history, lang, figures) -> Section:
    if isinstance(result, tuple):  # (tipo, razón): el par no se pudo ajustar
        kind, reason = result
        return Section(f"4.{k}", _FORMS.get(kind, kind), (Paragraph(t("hist_not_fitted", lang).format(
            reason=reason.rstrip("."))),))
    form = _FORMS[result.kind]
    mark = result.prior_verification
    blocks = [Paragraph(t("hist_prior", lang).format(
        method=result.prior_correlation, mark=mark, a=result.prior_mean[0], b=result.prior_mean[1],
        sd_a=result.prior_sd[0], sd_b=result.prior_sd[1], sigma=result.prior_sigma))]
    fits = site_fits(result)
    blocks.append(Table(t("cap_hist_fits", lang).format(form=form),
                        (t("h_fit", lang), "n", t("h_labors", lang), t("h_status", lang), t("h_method", lang),
                         t("h_a_ci", lang), t("h_b_ci", lang)),
                        tuple((t("fit_mine", lang) if f.label == "mine" else f.label, str(f.n), str(f.n_labors),
                               t(f"fit_{f.status}", lang), t(f"method_{f.method.lower()}", lang),
                               _ci(f.a, f.a_ci if f.method == "OLS" else None),
                               _ci(f.b, f.b_ci if f.method == "OLS" else None)) for f in fits)))
    m = result.mine
    blocks.append(Paragraph(t("hist_deming", lang).format(a=m.deming.a, b=m.deming.b) if m.deming is not None
                            else t("hist_no_deming", lang).format(reason=(m.deming_reason or "-").rstrip("."))))
    warns = Counter(result.warnings * len(fits)) + Counter(w for f in fits for w in set(f.warnings))
    if warns:
        blocks.append(_count_table("cap_hist_warnings", "h_fits", warns, lang))
    if history is not None:
        blocks.append(_fig(t("fig_hist_corr", lang).format(form=form),
                           lambda: history_correlation_figure(result, history, lang), lang, figures))
    return Section(f"4.{k}", form, tuple(blocks))


def _hist_methods(results, lang) -> tuple[Table, tuple[MethodRef, ...]]:
    dd = t("hm_dd", lang)
    fitted = [r for r in results if not isinstance(r, tuple)]
    n_boot = sorted({f.bootstrap.n_boot for r in fitted for f in site_fits(r) if f.bootstrap is not None})
    stats = (MethodRef(t("hm_ols", lang), "V2", "Warton et al. (2006)"),
             MethodRef(t("hm_boot", lang).format(n_boot="/".join(map(str, n_boot)) or "-"), "V2",
                       "Efron y Tibshirani (1994); Roberts et al. (2017)"
                       if lang == "es" else "Efron and Tibshirani (1994); Roberts et al. (2017)"),
             MethodRef(t("hm_deming", lang), "V2", "Carroll et al. (2006)"),
             MethodRef(t("hm_bayes", lang), "V2", f"Ching et al. (2020); {t('hm_prior_strength', lang)}: {dd}"))
    priors = {}
    for r in fitted:
        _, info = _prior_info(r.prior_correlation)
        priors.setdefault(r.prior_correlation, MethodRef(
            r.prior_correlation, info.info.verification.name if info else r.prior_verification,
            info.info.source if info else "-"))
    # la marca [V2] es de la investigación (MODELOS_SOSTENIMIENTO.md); Primary/Secondary es la del núcleo (R14)
    rows = (*((m.method_id, t("hm_role_stat", lang), f"[{m.verification}]", "-", m.source) for m in stats),
            *((m.method_id, t("hm_role_prior", lang), "-", m.verification, m.source) for m in priors.values()))
    return (Table(t("cap_hist_methods", lang), (t("h_method", lang), t("h_role", lang), t("h_research_mark", lang),
                                                t("h_core_verification", lang), t("h_source", lang)), rows),
            (*stats, *priors.values()))


# --- niveles 2 y 3 (Fase 4B y 4C): solo conteos, coeficientes y códigos de tipo; el id_tramo solo en tablas ---

_PARTITIONS = ("labor", "zone", "temporal", "random")
_VERDICT_KEYS = {"coherent": "verdict_coherent", "not significant": "verdict_not_significant",
                 "practice incoherent with rock quality": "verdict_rock",
                 "practice incoherent with span": "verdict_span", "not estimable": "verdict_not_estimable"}


def _f(v, fmt: str = ".3f") -> str:
    """Celda numérica; «-» sin dato o no finita."""
    return "-" if v is None or not (v == v and abs(v) != float("inf")) else format(v, fmt)


def _gain(i, fmt: str = ".3f") -> str:
    return f"{_f(i.value, fmt)} ({_f(i.ci_low, fmt)}; {_f(i.ci_high, fmt)})"


def _blockers_cell(partition, c, lang) -> str:
    """Cómo pesa la partición en la decisión: labor y zona por superioridad (sus motivos para no recomendar), la
    temporal por no inferioridad (mejora puntual ≥ 0) y la aleatoria no cuenta."""
    if partition == "temporal":
        return t("noninf_met" if all(i.value >= 0 for i in c.improvements.values()) else "noninf_not", lang)
    if partition == "random":
        return t("random_no_weight", lang)
    return "; ".join(c.blockers) or "-"


def _validation_table(caption_key, report, refs, fmt, lang) -> list:
    """Una fila por partición (métricas, mejoras con IC y motivos para no recomendar) y los avisos de la validación.
    `refs`: los nombres de las referencias en el orden de las columnas."""
    main = next((c.main for c in report.results.values()), "-")
    head = (t("h_partition", lang), t("h_rows", lang), t("h_groups", lang), main, *refs,
            *(t("h_gain_vs", lang).format(ref=r) for r in refs), t("h_blockers", lang))
    rows = []
    for p in _PARTITIONS:
        c = report.results.get(p)
        if c is not None:
            rows.append((t(f"part_{p}", lang), str(c.n_rows), str(c.n_groups),
                         *(_f(c.metrics[m], fmt) for m in (c.main, *refs)),
                         *(_gain(c.improvements[r], fmt) for r in refs), _blockers_cell(p, c, lang)))
        elif p in report.skipped:
            rows.append((t(f"part_{p}", lang), "-", "-", *("-" for _ in range(2 * len(refs) + 1)),
                         t("part_skipped", lang).format(reason=report.skipped[p])))
    out = [Table(t(caption_key, lang), head, tuple(rows))]
    if report.warnings:
        out.append(Table(t("cap_val_warnings", lang), (t("h_warning", lang),), tuple((w,) for w in report.warnings)))
    return out


def _warnings_table(warnings, lang) -> list:
    return [Table(t("cap_level_warnings", lang), (t("h_warning", lang),), tuple((w,) for w in warnings))] \
        if warnings else []


def _dd_table(rows, lang) -> Table:
    return Table(t("cap_dd", lang), (t("h_item", lang), t("h_value", lang)), tuple(rows))


def _practice_section(number, a, lang) -> Section:
    from ..history import MIN_LABORS_PER_TYPE_LEVEL2, MIN_TRAMOS_PER_TYPE_LEVEL2
    from ..predictive.validation import MAX_DISCARDED_FRACTION_DECISION

    none = t("none", lang)
    blocks = [Paragraph(t("l2_text", lang)),
              Table(t("cap_l2_data", lang), (t("h_item", lang), t("h_value", lang)), (
                  (t("l2_n", lang), str(a.n)), (t("l2_labors", lang), str(a.labors)),
                  (t("l2_types", lang), ", ".join(a.types)),
                  (t("l2_status", lang), t("l2_ready" if a.status == "ready" else "l2_insufficient", lang)),
                  (t("l2_missing", lang), ", ".join(a.missing_types) or none),
                  (t("l2_dropped", lang), ", ".join(a.dropped_columns) or none))),
              Table(t("cap_l2_coef", lang), (t("h_variable", lang), t("h_coef", lang), t("h_se", lang),
                                             t("h_ci95", lang), t("h_verdict", lang)),
                    tuple((name, _f(c.value), _f(c.se), f"{_f(c.ci_low)}; {_f(c.ci_high)}",
                           t(_VERDICT_KEYS[a.verdicts[name]], lang) if name in a.verdicts else "-")
                          for name, c in a.coefficients.items())
                    + tuple((name, "-", "-", "-", t(_VERDICT_KEYS[v], lang)) for name, v in a.verdicts.items()
                            if name not in a.coefficients)),
              Paragraph(t("l2_val_text", lang)),
              *_validation_table("cap_l2_val", a.validation, ("dummy", "ngi"), ".3f", lang),
              Paragraph(t("l2_beyond_yes" if a.beyond_chart else "l2_beyond_no", lang))]
    cc = a.concordance
    if cc is None:
        blocks.append(Paragraph(t("l2_conc_none", lang)))
    else:
        blocks += [Paragraph(t("l2_conc_text", lang).format(n=cc.n, kappa=_f(cc.kappa))),
                   Table(t("cap_l2_conc", lang), (t("h_recommended_installed", lang), *cc.types),
                         tuple((r, *map(str, cc.matrix[i])) for i, r in enumerate(cc.types)))]
    n_sets = sum(x.conformal_set is not None for x in a.tramos)
    blocks.append(Paragraph(t("l2_conformal", lang).format(level=a.conformal_level, q=_f(a.conformal_threshold),
                                                            cov=_f(_coverage(a)), k=len(a.outside_set), n=n_sets)))
    outside = [x for x in a.tramos if x.outside]
    blocks.append(Table(t("cap_l2_outside", lang), ("id_tramo", t("h_installed", lang), t("h_most_probable", lang),
                                                    t("h_conformal_set", lang)),
                        tuple((x.id_tramo, x.installed, x.most_probable or "-", ", ".join(x.conformal_set))
                              for x in outside)) if outside else Paragraph(t("l2_none_outside", lang)))
    blocks.append(_dd_table((
        (t("dd_l2_min", lang), t("dd_l2_min_v", lang).format(t=MIN_TRAMOS_PER_TYPE_LEVEL2,
                                                              l=MIN_LABORS_PER_TYPE_LEVEL2)),
        (t("dd_conformal", lang), f"{a.conformal_level:.0%}"),
        (t("dd_gain_ci", lang), t("dd_gain_ci_v", lang)),
        (t("dd_discarded", lang), f"≤ {MAX_DISCARDED_FRACTION_DECISION:.0%}")), lang))
    blocks += _warnings_table(a.warnings, lang)
    return Section(number, t("hs_l2", lang), tuple(blocks))


def _coverage(a) -> float:
    """Cobertura del conjunto conforme; el campo puede llamarse `coverage` o `calibration_coverage`."""
    return getattr(a, "coverage", getattr(a, "calibration_coverage", float("nan")))


def _iso_blocks(m, history, exposure_days, lang, figures) -> list:
    """Una figura por tipo en el plano Q–De, dentro del rango de entrenamiento, con los tramos de ese tipo si hay
    histórico. Horizonte: `exposure_days` o, sin él, la mediana de la exposición del histórico."""
    import math
    import statistics

    from ..history import level3_rows
    from ..predictive.performance import isoprobability_grid
    from ..viz.style import Style

    if m.quality != "q":
        return [Paragraph(t("l3_iso_rmr", lang))]
    rows = level3_rows(history) if history is not None else ()
    days = exposure_days or (statistics.median(o.exposure_days for o, _ in rows) if rows else None)
    if days is None:
        return [Paragraph(t("l3_iso_no_horizon", lang))]
    iq, idx = m.features.index("ln_q"), m.features.index("ln_de")
    q_range = (math.exp(m.train_min[iq]), math.exp(m.train_max[iq]))
    de_range = (math.exp(m.train_min[idx]), math.exp(m.train_max[idx]))
    pts = {}
    for o, x in rows:
        pts.setdefault((x.sost_instalado, o.failed), []).append((x.q_valor, x.luz_m / x.esr))
    out = [Paragraph(t("l3_iso_text", lang).format(days=days))]
    for code, _ in m.support_types:
        def draw(code=code):
            from ..viz import plot_isoprobability  # sin matplotlib: ImportError y _fig deja la nota

            g = isoprobability_grid(m, support_code=code, exposure_days=days, q_range=q_range, de_range=de_range)
            return plot_isoprobability(g, stable=pts.get((code, False), ()), failed=pts.get((code, True), ()),
                                       style=Style(lang=lang))
        out.append(_fig(t("fig_l3_iso", lang).format(code=code), draw, lang, figures))
    return out


def _performance_section(number, m, history, threshold, exposure_days, lang, figures) -> Section:
    from ..history import MIN_EVENTS_PER_PARAMETER_LEVEL3, MIN_ZONES_LEVEL3
    from ..predictive.performance import MAHALANOBIS_PERCENTILE
    from ..predictive.validation import MAX_DISCARDED_FRACTION_DECISION
    from ..viz.style import Style

    c = m.counts
    blocks = [Paragraph(t("l3_text", lang)), Paragraph(t("l3_rule_val", lang)),
              Table(t("cap_l3_state", lang), (t("h_item", lang), t("h_value", lang)), (
                  (t("l3_calibration", lang), t(f"cal_{m.calibration}", lang)),
                  (t("l3_reason", lang), m.calibration_reason),
                  (t("l3_quality", lang), "ln Q" if m.quality == "q" else "RMR"),
                  (t("l3_tramos", lang), str(c["tramos"])), (t("l3_failures", lang), str(c["failures"])),
                  (t("l3_non_failures", lang), str(c["non_failures"])), (t("l3_labors", lang), str(c["labors"])),
                  (t("l3_zones", lang), str(c["zones"])), (t("l3_params", lang), str(c["parameters"])),
                  (t("l3_minority", lang), f"{c['minority_class']} / {c['minority_class_minimum']}")))]
    if not m.coefficients:
        blocks.append(Paragraph(t("l3_no_fit", lang)))
    else:
        sign = {1: "sign_up", -1: "sign_down", 0: "sign_free"}
        blocks.append(Table(t("cap_l3_coef", lang), (t("h_variable", lang), t("h_coef", lang), t("h_ci95", lang),
                                                     t("h_sign", lang), t("h_bound_active", lang)),
                            tuple((name, _f(m.coefficients[name], ".4g"), f"{_f(lo, '.4g')}; {_f(hi, '.4g')}",
                                   t(sign[s], lang), t("yes" if name in m.active_bounds else "no", lang))
                                  for name, (lo, hi), s in zip(m.features, m.coef_ci, m.signs))))
    if m.validation is not None:
        blocks += _validation_table("cap_l3_val", m.validation, ("dummy", "baseline_ngi"), ".4f", lang)
    mt = m.metrics
    if mt.get("n"):
        blocks.append(Table(t("cap_l3_oof", lang), (t("h_item", lang), t("h_value", lang)), (
            ("n", str(mt["n"])), (t("m_brier", lang), _f(mt.get("brier"), ".4f")),
            (t("m_auc", lang), _f(mt.get("auc"))), (t("m_ap", lang), _f(mt.get("average_precision"))),
            (t("m_cal_a", lang), _f(mt.get("calibration_intercept"))),
            (t("m_cal_b", lang), _f(mt.get("calibration_slope"))))))
    if m.calibration_curve:
        from ..viz import plot_calibration

        blocks.append(_fig(t("fig_l3_cal", lang), lambda: plot_calibration(m.calibration_curve, metrics=mt,
                                                                           style=Style(lang=lang)), lang, figures))
    if m.coefficients:
        blocks += _iso_blocks(m, history, exposure_days, lang, figures)
    blocks += [Paragraph(t("l3_rule", lang)),
               Paragraph(t("l3_threshold_none", lang) if threshold is None
                         else t("l3_threshold", lang).format(thr=threshold)),
               _dd_table((
                   (t("dd_l3_min", lang), t("dd_l3_min_v", lang).format(e=MIN_EVENTS_PER_PARAMETER_LEVEL3,
                                                                         z=MIN_ZONES_LEVEL3)),
                   (t("dd_signs", lang), t("dd_signs_v", lang)), (t("dd_baseline", lang), t("dd_baseline_v", lang)),
                   (t("dd_gain_ci", lang), t("dd_gain_ci_v", lang)), (t("dd_temporal", lang), t("dd_temporal_v", lang)),
                   (t("dd_discarded", lang), f"≤ {MAX_DISCARDED_FRACTION_DECISION:.0%}"),
                   (t("dd_interval", lang), t("dd_interval_v", lang)),
                   (t("dd_maha", lang), t("dd_maha_v", lang).format(p=MAHALANOBIS_PERCENTILE)),
                   (t("dd_threshold", lang), t("dd_threshold_v", lang))), lang)]
    blocks += _warnings_table(m.warnings, lang)
    return Section(number, t("hs_l3", lang), tuple(blocks))


def _tripod_section(number, lang) -> Section:
    from .texts import TRIPOD_ITEMS

    return Section(number, t("hs_tripod", lang), (
        Paragraph(t("tripod_text", lang)),
        Table(t("cap_tripod", lang), (t("h_tripod_item", lang), t("h_tripod_covered", lang),
                                      t("h_tripod_where", lang)),
              tuple((txt[lang][0], t(f"tr_{status}", lang), txt[lang][1]) for status, txt in TRIPOD_ITEMS))))


def _level_methods(practice, performance, lang) -> tuple[MethodRef, ...]:
    es = lang == "es"
    out = []
    if practice is not None:
        out += [MethodRef("ordinal logit (proportional odds)", "V2", "Bürkner y Vuorre (2019)" if es
                          else "Bürkner and Vuorre (2019)"),
                MethodRef("quadratic weighted kappa", "V2", "Cohen (1968)"),
                MethodRef("grouped conformal set", "V2", "Angelopoulos y Bates (2023)" if es
                          else "Angelopoulos and Bates (2023)")]
    if performance is not None:
        out += [MethodRef("MAP logistic, Cauchy prior, Laplace", "V2", "Gelman et al. (2008)"),
                MethodRef("calibration curve, intercept and slope", "V2", "Van Calster et al. (2019)"),
                MethodRef("isoprobability contours", "V2", "Mawdesley et al. (2001)")]
    out += [MethodRef("grouped cross-validation", "V2", "Roberts et al. (2017)"),
            MethodRef("TRIPOD+AI", "V2", "Collins et al. (2024)")]
    return tuple(out)


def build_history_report(audit, correlations=(), *, history=None, practice=None, performance=None,
                         threshold: float | None = None, exposure_days: float | None = None,
                         title: str | None = None, lang: str = "es",
                         author: str = "", date: str = "", figures: bool = True) -> Report:
    """Informe del histórico: datos, auditoría de ingesta, preparación por nivel, nivel 1, niveles 2 y 3 (si se
    pasan), TRIPOD+AI (con algún nivel 2 o 3) y limitaciones.

    - `audit`: el `HistoryAudit` de `audit_history`.
    - `correlations`: los `SiteCorrelationResult` de `fit_site_correlation`; un par que no se pudo ajustar va como
      la tupla (tipo, razón). Vacío: la sección del nivel 1 dice que no se pidieron.
    - `history`: el `History` leído; da los años cubiertos y los puntos de las figuras (sin él no van).
    - `practice`: el `PracticeAudit` de `audit_practice` (nivel 2: describe la práctica, no recomienda).
    - `performance`: el `PerformanceModel` de `fit_performance` (nivel 3).
    - `threshold`: el umbral de P(falla) que fijó el ingeniero, si lo hay; solo se cita (no tiene valor por defecto).
    - `exposure_days`: el horizonte de las isoprobabilidades; sin él, la mediana de la exposición del histórico.
    Nunca lleva el nombre del archivo, la labor, la zona ni la litología: los dominios van como D1, D2…; el
    `id_tramo` solo en la tabla de hallazgos y en la de tramos fuera del conjunto conforme.
    """
    _check_lang(lang)
    if threshold is not None and not 0 < threshold < 1:
        raise ValueError("threshold must be a probability strictly between 0 and 1")
    if exposure_days is not None and not exposure_days > 0:
        raise ValueError("exposure_days must be a positive number of days")
    correlations = list(correlations)
    if correlations:
        methods_table, methods = _hist_methods(correlations, lang)
        s4 = (Paragraph(t("hist_l1_text", lang)), methods_table,
              *(_hist_kind(k, r, history, lang, figures) for k, r in enumerate(correlations, 1)))
    else:
        s4, methods = (Paragraph(t("hist_l1_none", lang)),), ()
    sections = [
        _hist_data(audit, history, lang),
        _hist_audit(audit, lang),
        _hist_readiness(audit, lang),
        Section("4", t("hs_4", lang), s4),
    ]
    levels = practice is not None or performance is not None
    if practice is not None:
        sections.append(_practice_section(str(len(sections) + 1), practice, lang))
    if performance is not None:
        sections.append(_performance_section(str(len(sections) + 1), performance, history, threshold,
                                                 exposure_days, lang, figures))
    if levels:
        sections.append(_tripod_section(str(len(sections) + 1), lang))
        methods = (*methods, *_level_methods(practice, performance, lang))
    sections.append(Section(str(len(sections) + 1), t("hs_5", lang), (
        Paragraph(t("hist_limits", lang)), Paragraph(t("hist_limits_l23" if levels else "hist_limits_none", lang)),
        Paragraph(DISCLAIMER[lang]))))
    subtitle = t("hist_subtitle_full" if levels else "hist_subtitle", lang)
    return Report(title or t("hist_title", lang), _subtitle(subtitle, author, lang), lang, tuple(sections),
                  methods, DISCLAIMER[lang], __version__, date or datetime.date.today().isoformat())


from .docx import write_docx  # noqa: E402,F401
from .html import write_html  # noqa: E402,F401
