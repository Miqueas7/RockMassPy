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
from typing import Callable

from .. import __version__
from .. import _rockmasspy_core as rm
from ..batch import _COLUMNS, _columns, _fila, q_chart_crosstab, summarize
from ..cell_table import CellTable
from ..gsi_charts import GSI_CHARTS
from ..labor_table import LaborTable, _key
from ..q_chart_data import Q_CHARTS
from ..range_table import RangeTable
from .texts import DISCLAIMER, t


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
                   author: str = "", date: str = "", figures: bool = True) -> Report:
    """Informe con la estructura del Anexo 39 B del DS 024-2016-EM; lo que la librería no calcula queda por completar.

    `author` va en el subtítulo, igual que en build_memoria; el autor del Word se pasa a write_docx.
    """
    _check_lang(lang)
    results, tables = _filter_labor(list(results), list(tables), labor_type)
    methods = _methods(results, tables, lang)

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
        *q_blocks))
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
    out: dict[tuple[str, str], MethodRef] = {}
    for r in results:
        for m in r.mathews.methods:
            out.setdefault((m.method_id, m.source), MethodRef(m.method_id, m.verification.name, m.source))
    methods = tuple(out.values())
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


from .docx import write_docx  # noqa: E402,F401
from .html import write_html  # noqa: E402,F401
