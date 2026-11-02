import pytest

import rockmasspy as rm
import rockmasspy.report as rp

from test_batch import CAT, cell_tab, q_tab, rmr_tab, tr

CORR = rm.CustomCorrelation(name="ajuste sitio", from_="Q", to="RMR89", form=rm.CorrelationForm.LogLinear,
                            a=7.5, b=47.0, valid_min=0.01, valid_max=100.0, source="ajuste sintético")
TABLES = [rm.LaborTable("galería", CAT, rmr_tab(), span_m=(1, 6)),
          rm.LaborTable("crucero", CAT, q_tab(), correlations=(CORR,)),
          rm.LaborTable("rampa", CAT, cell_tab())]


def resultados():
    ts = [tr("T1", rmr_valor=70, progresiva_inicio_m=0, progresiva_fin_m=10),
          tr("T3", labor="crucero", rqd_pct=90, jn=4, jr=3, ja=1, jw=1, srf=15,
             labor_codigo="SECRETO-1", zona_nivel="SECRETO-2"),
          tr("T4", labor="rampa", gsi_celda="F/R")]
    return rm.classify_tramos(ts, TABLES)


def build(**kw):
    kw.setdefault("figures", False)
    return rp.build_anexo39b(resultados(), TABLES, title="Anexo sintético", **kw)


def walk(secs):
    for s in secs:
        yield s
        yield from walk([b for b in s.blocks if isinstance(b, rp.Section)])


def test_numbers_and_titles():
    got = [(s.number, s.title) for s in walk(build().sections)]
    assert got == [
        ("1", "Introducción"), ("2", "Caracterización geomecánica del macizo rocoso"),
        ("2.1", "galería (luz 1-6 m)"), ("2.2", "crucero"), ("2.3", "rampa"),
        ("3", "Condiciones geomecánicas actuales de la labor"), ("4", "Evaluación de estabilidad"),
        ("4.1", "Cálculo empírico"), ("4.2", "Análisis cinemático de cuñas"), ("4.3", "Modelamiento numérico"),
        ("4.3.1", "Recomendación de excavación o explotación"),
        ("4.3.2", "Recomendación de reforzamiento o sostenimiento"),
        ("5", "Conclusiones y recomendaciones"), ("6", "Anexos"),
        ("", "Memoria resumen de parámetros de entrada")]


def test_to_complete_marked():
    marked = {s.number for s in walk(build().sections) if s.to_complete}
    assert marked == {"1", "4.2", "4.3", "4.3.1", "4.3.2", "5", "6"}


def test_english_titles_and_subtitle():
    r = build(lang="en")
    assert r.subtitle == "Structure of Annex 39 B, DS 024-2016-EM (Peru)"
    titles = [s.title for s in walk(r.sections) if not s.number.startswith("2.")]
    assert titles == ["Introduction", "Geomechanical characterization of the rock mass",
                      "Current geomechanical conditions of the excavation", "Stability assessment",
                      "Empirical design", "Kinematic wedge analysis", "Numerical modelling",
                      "Excavation or mining recommendation", "Reinforcement or support recommendation",
                      "Conclusions and recommendations", "Appendices", "Summary of input parameters"]
    assert "—" not in "".join(b.text for s in walk(build().sections) for b in s.blocks if isinstance(b, rp.Paragraph))


def test_labor_type_filters_results_and_tables():
    r = build(labor_type="Galeria")  # sin tilde: igual que el lote
    s41 = next(s for s in walk(r.sections) if s.number == "4.1")
    assert [row[0] for row in s41.blocks[0].rows] == ["T1"]
    assert [s.number for s in walk(r.sections) if s.number.startswith("2.")] == ["2.1"]
    summ = r.sections[-1]
    assert not any(b.caption == "Parámetros del Q usados" for b in summ.blocks)


def test_labor_type_nothing_lists_available():
    with pytest.raises(ValueError, match="crucero.*galería|galería.*crucero"):
        build(labor_type="chimenea")


def test_summary_has_q_params_and_correlations():
    summ = build().sections[-1]
    q = next(b for b in summ.blocks if b.caption == "Parámetros del Q usados")
    assert q.header == ("id_tramo", "RQD", "Jn", "Jr", "Ja", "Jw", "SRF")
    assert q.rows == (("T3", "90", "4", "3", "1", "1", "15"),)
    c = next(b for b in summ.blocks if b.caption == "Correlaciones propias del sitio")
    assert c.rows[0][0] == "ajuste sitio" and "7.5" in c.rows[0] and "47" in c.rows[0]
    assert any(b.caption.startswith("crucero") for b in summ.blocks)


def test_no_q_table_without_q_tramos():
    rs = rm.classify_tramos([tr("T1", rmr_valor=70)], TABLES)
    r = rp.build_anexo39b(rs, TABLES, title="t", figures=False)
    assert not any(getattr(b, "caption", "") == "Parámetros del Q usados" for b in r.sections[-1].blocks)


def test_html_no_stray_number_and_no_identification(tmp_path):
    h = rp.write_html(build(), tmp_path / "a.html").read_text(encoding="utf-8")
    assert "<h2>Memoria resumen de parámetros de entrada" in h and ". Memoria" not in h
    assert "<h2>1. Introducción" in h and "<h4>4.3.1. " in h
    assert "SECRETO" not in h and "T3" in h


def test_docx_empty_number(tmp_path):
    docx = pytest.importorskip("docx")
    p = rp.write_docx(build(), tmp_path / "a.docx")
    heads = [x.text for x in docx.Document(str(p)).paragraphs if x.style.name.startswith("Heading")]
    assert "Memoria resumen de parámetros de entrada" in heads and "4.3.1. Recomendación de excavación o explotación" in heads
    assert not any(h.startswith(".") or h.startswith(" ") for h in heads)


def test_bad_lang():
    with pytest.raises(ValueError):
        rp.build_anexo39b([], TABLES, title="x", lang="fr")
