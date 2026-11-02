import hashlib

import pytest

import rockmasspy as rm
import rockmasspy.report as rp

from test_batch import CAT, q_tab, rmr_tab, tr

TABLES = [rm.LaborTable("galería", CAT, rmr_tab(), span_m=(1, 6)), rm.LaborTable("crucero", CAT, q_tab())]


def base():
    ts = [tr("T1", rmr_valor=70, q_valor=0.4, labor_codigo="SECRETO-123", zona_nivel="NIVEL-SECRETO"),
          tr("T2", rmr_valor=30, q_valor=4.5, luz=5.0),
          tr("T3", labor="Crucero", q_valor=30.0, luz=3.0),
          tr("T4", labor="crucero", q_valor=0.05, luz=3.5)]
    return rm.classify_tramos(ts, TABLES)


def con_ref(**kw):
    return rm.add_q_chart_reference(base(), {"galeria": ("A", 4.0), "*": "C"}, **kw)


def walk(secs):
    for s in secs:
        yield s
        yield from walk([b for b in s.blocks if isinstance(b, rp.Section)])


def sec(rep, n):
    return next(s for s in walk(rep.sections) if s.number == n)


def tablas(s):
    return [b for b in s.blocks if isinstance(b, rp.Table)]


def test_memoria_51_con_cruzada_figura_y_leyenda():
    r = rp.build_memoria(con_ref(), TABLES, title="M", date="2026-01-01")
    s = sec(r, "5.1")
    assert s.title == "Carta de sostenimiento Q (referencia)"
    assert sec(r, "5").blocks[-1] is s
    tabs = tablas(s)
    assert len(tabs) == 3  # ESR por labor, cruzada, leyenda
    esr, cruz, leyenda = tabs
    assert {row[0] for row in esr.rows} == {"galeria", "Crucero"} and len(esr.rows) == 2
    assert cruz.header[0] == "Sostenimiento" and sum(int(c) for row in cruz.rows for c in row[1:]) == 4
    assert len(leyenda.rows) == 9 and "referencial" in leyenda.rows[6][1]
    assert any(isinstance(b, rp.Figure) and b.png for b in s.blocks)
    assert isinstance(s.blocks[0], rp.Paragraph)
    assert sec(r, "4").blocks[0].header[-1] == "q_carta_avisos"


def test_metodos_trae_la_carta_digitalizada():
    r = rp.build_memoria(con_ref(), TABLES, title="M", figures=False)
    m = next(m for m in r.methods if m.method_id == "Q-NGI-2025-chart")
    assert m.verification == "Primary" and "digitized" in m.source
    r15 = rp.build_memoria(con_ref(edition="Q-NGI-2015"), TABLES, title="M", figures=False)
    assert any(m.method_id == "Q-NGI-2015-chart" for m in r15.methods)


def test_avisos_de_la_carta_se_cuentan_sin_id_tramo():
    ts = [tr("T9", labor="otra", q_valor=1.0)] + [t.tramo for t in base()]
    res = rm.add_q_chart_reference(rm.classify_tramos(ts, TABLES), {"galeria": ("A", 4.0)})
    r = rp.build_memoria(res, TABLES, title="M", figures=False)
    t = tablas(sec(r, "7"))
    qt = next(x for x in t if x.caption == "Avisos de la carta Q")
    assert ("no ESR for this labor", "3") in qt.rows
    assert "T9" not in repr(qt)


def test_anexo_41_trae_la_cruzada():
    r = rp.build_anexo39b(con_ref(), TABLES, title="A", figures=False)
    s = sec(r, "4.1")
    assert any(t.caption == "Tabla cruzada: sostenimiento propio y categoría Q" for t in tablas(s))
    assert any(m.method_id == "Q-NGI-2025-chart" for m in r.methods)


def test_html_sin_secreto_y_ingles(tmp_path):
    r = rp.build_memoria(con_ref(), TABLES, title="M", lang="en")
    assert sec(r, "5.1").title == "Q support chart (reference)"
    h = rp.write_html(r, tmp_path / "m.html").read_text(encoding="utf-8")
    assert "SECRETO-123" not in h and "NIVEL-SECRETO" not in h and "Q support chart (reference)" in h


def test_word_con_cruzada(tmp_path):
    docx = pytest.importorskip("docx")
    p = rp.write_docx(rp.build_memoria(con_ref(), TABLES, title="M", figures=False), tmp_path / "m.docx")
    doc = docx.Document(str(p))
    assert any("Tabla cruzada" in p.text for p in doc.paragraphs)


def test_ediciones_mezcladas_fallan():
    a, b = con_ref(), con_ref(edition="Q-NGI-2015")
    with pytest.raises(ValueError, match="one Q edition"):
        rp.build_memoria([a[0], b[1]], TABLES, title="M")


def test_sin_referencia_es_igual_a_la_1d():
    m = rp.build_memoria(base(), TABLES, title="M", date="2026-01-01", figures=False)
    a = rp.build_anexo39b(base(), TABLES, title="A", date="2026-01-01", figures=False)
    assert not any(s.number == "5.1" for s in walk(m.sections))
    assert not any(x.method_id.endswith("-chart") for x in m.methods)
    assert HASHES == (hashlib.sha256(repr(m).encode()).hexdigest(), hashlib.sha256(repr(a).encode()).hexdigest())


HASHES = ("477e183b6fdd9b5f1e96837f882aad9b971d4bc111b4bcd9acf021b26d875b88",
          "c18cae78101cf306da3b9fb02c2c9a98baa9e6f55a9e7cfa67706608134ab28a")
