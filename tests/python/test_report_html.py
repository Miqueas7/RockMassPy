import re

import pytest

import rockmasspy as rm
import rockmasspy.report as rp

from test_batch import CAT, cell_tab, q_tab, rmr_tab, tr

TABLES = [rm.LaborTable("galería", CAT, rmr_tab(), span_m=(1, 6)), rm.LaborTable("crucero", CAT, q_tab()),
          rm.LaborTable("rampa", CAT, cell_tab())]


def resultados():
    ts = [tr("T1", rmr_valor=70, progresiva_inicio_m=0, progresiva_fin_m=10, este_m=1.0, norte_m=2.0,
             labor_codigo="SECRETO-123", zona_nivel="NIVEL-SECRETO"),
          tr("T2", rmr_valor=30, progresiva_inicio_m=10, progresiva_fin_m=20, este_m=5.0, norte_m=6.0),
          tr("T3", labor="crucero", rqd_pct=90, jn=4, jr=3, ja=1, jw=1, srf=15),
          tr("T4", labor="rampa", gsi_celda="F/R"),
          tr("T5", labor="otra")]
    return rm.classify_tramos(ts, TABLES)


def build(**kw):
    return rp.build_memoria(resultados(), TABLES, title="Memoria sintética", **kw)


def test_eight_sections_and_methods():
    r = build()
    assert [s.number for s in r.sections] == [str(i) for i in range(1, 9)]
    ids = {m.method_id for m in r.methods}
    assert {"RMR89", "Q-NGI-2025", "GSI-Vallejo-Osinergmin2017"} <= ids
    q = next(m for m in r.methods if m.method_id == "Q-NGI-2025")
    assert q.verification == "Primary" and "NGI" in q.source
    assert r.version == rm.__version__


def test_results_table_matches_save_results_columns():
    from rockmasspy.batch import _COLUMNS
    t = next(b for b in build().sections[3].blocks if isinstance(b, rp.Table))
    assert t.header == _COLUMNS and len(t.rows) == 5


def test_html_disclaimer_twice_images_and_escape(tmp_path):
    rs = resultados()
    rs[0] = rm.classify_tramos([tr("T<b>1", labor="galería", rmr_valor=70)], TABLES)[0]
    r = rp.build_memoria(rs, TABLES, title="Memoria <i>x</i>")
    p = rp.write_html(r, tmp_path / "m.html")
    h = p.read_text(encoding="utf-8")
    assert h.count(r.disclaimer) == 2
    assert "data:image/png;base64," in h
    assert "<b>1" not in h and "T&lt;b&gt;1" in h and "<i>x</i>" not in h
    assert '<html lang="es">' in h and "<thead>" in h
    assert "SECRETO-123" not in h and "NIVEL-SECRETO" not in h


def test_no_figures(tmp_path):
    r = build(figures=False)
    h = rp.write_html(r, tmp_path / "m.html").read_text(encoding="utf-8")
    assert "<img" not in h and "figuras no disponibles: instala rockmasspy[viz]" in h


def test_english(tmp_path):
    r = build(lang="en", figures=False)
    assert r.sections[0].title == "Purpose and scope" and r.sections[7].title == "Limitations"
    assert "The library recommends, the engineer decides." in r.disclaimer
    h = rp.write_html(r, tmp_path / "m.html").read_text(encoding="utf-8")
    assert '<html lang="en">' in h and "figures not available" in h


def test_warnings_counts_without_ids():
    sec = build(figures=False).sections[6]
    rows = [row for b in sec.blocks if isinstance(b, rp.Table) for row in b.rows]
    assert rows and all(re.fullmatch(r"\d+", row[1]) for row in rows)


def test_to_complete_marked(tmp_path):
    r = rp.Report("t", "", "es", (rp.Section("1", "x", (), to_complete=True),), (), "d", "0", "2026-01-01")
    assert "A completar por el ingeniero" in rp.write_html(r, tmp_path / "a.html").read_text(encoding="utf-8")


def test_bad_lang():
    with pytest.raises(ValueError):
        rp.build_memoria([], TABLES, title="x", lang="fr")


def test_labor_type_tag_escaped(tmp_path):
    lt = rm.LaborTable("<b>x</b>", CAT, rmr_tab())
    rs = rm.classify_tramos([tr("A", labor="<b>x</b>", rmr_valor=70)], [lt])
    h = rp.write_html(rp.build_memoria(rs, [lt], title="t", figures=False), tmp_path / "m.html").read_text(encoding="utf-8")
    assert "<b>x</b>" not in h and "&lt;b&gt;x&lt;/b&gt;" in h
