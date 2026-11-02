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


def fingerprint(rep):
    out = []

    def walk(secs):
        for s in secs:
            out.append((s.number, s.title))
            for b in s.blocks:
                if isinstance(b, rp.Table):
                    out.append((b.caption, b.header))
                elif isinstance(b, rp.Section):
                    walk([b])
    walk(rep.sections)
    return tuple(out)


# Estructura de la 1D (secciones, títulos, leyendas y encabezados de tablas), tomada antes de la carta Q.
FP_MEMORIA = (('1', 'Objetivo y alcance'), ('2', 'Métodos y ediciones'), ('Métodos usados y su verificación', ('Método', 'Verificación', 'Fuente')), ('3', 'Tablas geomecánicas por labor'), ('3.1', 'galería (luz 1-6 m)'), ('Clases y sostenimiento', ('Rango o celda', 'Clase', 'Sostenimiento')), ('Catálogo de sostenimiento', ('Sostenimiento', 'Elementos')), ('3.2', 'crucero'), ('Clases y sostenimiento', ('Rango o celda', 'Clase', 'Sostenimiento')), ('Catálogo de sostenimiento', ('Sostenimiento', 'Elementos')), ('4', 'Resultados por tramo'), ('Resultados de la clasificación', ('id_tramo', 'tipo_labor', 'luz_m', 'tabla_luz_min_m', 'tabla_luz_max_m', 'metodo', 'edicion_base', 'valor_entrada', 'celda', 'clase', 'sostenimiento', 'sostenimiento_orden', 'sost_instalado', 'avisos')), ('5', 'Resumen'), ('Totales', ('', 'Tramos')), ('Tramos por labor y clase', ('Labor', 'Clase', 'Tramos')), ('Tramos por sostenimiento', ('Sostenimiento', 'Tramos')), ('6', 'Mapas'), ('7', 'Avisos'), ('8', 'Limitaciones'))
FP_ANEXO = (('1', 'Introducción'), ('2', 'Caracterización geomecánica del macizo rocoso'), ('2.1', 'galería (luz 1-6 m)'), ('Clases y sostenimiento', ('Rango o celda', 'Clase', 'Sostenimiento')), ('Catálogo de sostenimiento', ('Sostenimiento', 'Elementos')), ('2.2', 'crucero'), ('Clases y sostenimiento', ('Rango o celda', 'Clase', 'Sostenimiento')), ('Catálogo de sostenimiento', ('Sostenimiento', 'Elementos')), ('3', 'Condiciones geomecánicas actuales de la labor'), ('Tramos de la labor, con su clase y su sostenimiento', ('id_tramo', 'tipo_labor', 'luz_m', 'clase', 'sostenimiento')), ('4', 'Evaluación de estabilidad'), ('4.1', 'Cálculo empírico'), ('Resultados de la clasificación', ('id_tramo', 'tipo_labor', 'luz_m', 'tabla_luz_min_m', 'tabla_luz_max_m', 'metodo', 'edicion_base', 'valor_entrada', 'celda', 'clase', 'sostenimiento', 'sostenimiento_orden', 'sost_instalado', 'avisos')), ('Métodos usados y su verificación', ('Método', 'Verificación', 'Fuente')), ('4.2', 'Análisis cinemático de cuñas'), ('4.3', 'Modelamiento numérico'), ('4.3.1', 'Recomendación de excavación o explotación'), ('4.3.2', 'Recomendación de reforzamiento o sostenimiento'), ('5', 'Conclusiones y recomendaciones'), ('6', 'Anexos'), ('', 'Memoria resumen de parámetros de entrada'), ('galería (luz 1-6 m) (RMR89)', ('Rango o celda', 'Clase', 'Sostenimiento')), ('crucero (Q-NGI-2025)', ('Rango o celda', 'Clase', 'Sostenimiento')), ('Parámetros del Q usados', ('id_tramo', 'RQD', 'Jn', 'Jr', 'Ja', 'Jw', 'SRF')))


def test_sin_referencia_es_igual_a_la_1d():
    from rockmasspy.batch import _COLUMNS
    m = rp.build_memoria(base(), TABLES, title="M", date="2026-01-01", figures=False)
    a = rp.build_anexo39b(base(), TABLES, title="A", date="2026-01-01", figures=False)
    assert not any(s.number == "5.1" for s in walk(m.sections))
    assert not any(x.method_id.endswith("-chart") for x in m.methods)
    assert tablas(sec(m, "4"))[0].header == _COLUMNS
    assert fingerprint(m) == FP_MEMORIA and fingerprint(a) == FP_ANEXO


def test_referencia_pedida_sin_ninguna_concedida(tmp_path):
    res = rm.add_q_chart_reference(base(), {"otra": ("A", 4.0)})
    m = rp.build_memoria(res, TABLES, title="M")
    a = rp.build_anexo39b(res, TABLES, title="A")
    for s in (sec(m, "5.1"), sec(a, "4.1")):
        assert any(isinstance(b, rp.Paragraph) and b.text.startswith("Ningún tramo obtuvo") for b in s.blocks)
        assert not any(isinstance(b, rp.Figure) for b in s.blocks)
        assert not any(t.caption == "Tabla cruzada: sostenimiento propio y categoría Q" for t in tablas(s))
    qt = next(x for x in tablas(sec(m, "7")) if x.caption == "Avisos de la carta Q")
    assert ("no ESR for this labor", "4") in qt.rows
    assert "SECRETO-123" not in rp.write_html(m, tmp_path / "m.html").read_text(encoding="utf-8")


def test_leyenda_en_ingles_marca_7_a_9_indicativas():
    r = rp.build_memoria(con_ref(), TABLES, title="M", lang="en", figures=False)
    leg = tablas(sec(r, "5.1"))[2]
    assert all("(indicative)" in leg.rows[k][1] for k in (6, 7, 8))
