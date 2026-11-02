import pytest

import rockmasspy as rm

CAT = rm.SupportCatalog([rm.SupportType("I", 1), rm.SupportType("II", 2), rm.SupportType("III", 3)])


def rmr_tab():
    return rm.RangeTable("RMR", "RMR89", [rm.RangeClass(0, 40, "poor", "III"), rm.RangeClass(40, 60, "fair", "II"),
                                          rm.RangeClass(60, 100, "good", "I")])


def q_tab():
    return rm.RangeTable("Q", "Q-NGI-2025", [rm.RangeClass(0, 1, "poor", "III"), rm.RangeClass(1, 10, "fair", "II"),
                                             rm.RangeClass(10, 1000, "good", "I")])


def cell_tab():
    return rm.CellTable(rm.GSI_CHARTS["GSI-Vallejo-Osinergmin2017"],
                        [rm.CellClass("F/R", "II", label="fr"), rm.CellClass("F/B", "I", label="fb")])


def lab(labor, table, span=None):
    return rm.LaborTable(labor, CAT, table, span_m=span)


def tr(i="T1", labor="galeria", luz=4.0, **kw):
    d = dict(id_tramo=i, tipo_labor=labor, labor_codigo=None, zona_nivel=None, fecha_evaluacion=None,
             progresiva_inicio_m=None, progresiva_fin_m=None, este_m=None, norte_m=None, cota_m=None, datum=None,
             luz_m=luz, ucs_mpa=None, rqd_pct=None, jn=None, jr=None, ja=None, jw=None, srf=None, rmr_valor=None,
             rmr_edicion=None, q_valor=None, q_edicion=None, gsi_valor=None, gsi_celda=None, sost_recomendado=None,
             sost_instalado=None, fila=2)
    d.update(kw)
    return rm.Tramo(**d)


TABLES = [lab("galería", rmr_tab()), lab("crucero", q_tab()), lab("rampa", cell_tab())]


def one(t, tables=TABLES):
    return rm.classify_tramos([t], tables)[0]


def test_three_kinds():
    r = one(tr(rmr_valor=70))
    assert (r.label, r.support.code, r.method, r.base_edition, r.input_value) == ("good", "I", "RMR", "RMR89", 70)
    assert r.support_order == 1
    r = one(tr(labor="crucero", q_valor=5))
    assert (r.label, r.method) == ("fair", "Q")
    r = one(tr(labor="rampa", gsi_celda="F/R"))
    assert (r.label, r.input_cell, r.support.code) == ("fr", "F/R", "II")


def test_q_computed_and_q1974():
    r = one(tr(labor="crucero", rqd_pct=90, jn=4, jr=3, ja=1, jw=1, srf=15))
    assert r.label == "fair" and abs(r.input_value - 4.5) < 5e-3
    r = one(tr(labor="crucero", q_edicion="Q-1974", q_valor=0.5))
    assert r.label == "poor" and "Q-1974 not supported; value used as given" in r.warnings


def test_rmr_edition_and_installed_support():
    r = one(tr(rmr_valor=70, rmr_edicion="RMR76", sost_instalado="II"))
    assert r.warnings == ("RMR edition RMR76 differs from table edition RMR89",
                          "installed support II differs from recommended I")
    assert one(tr(rmr_valor=70, sost_instalado="I")).warnings == ()


def test_unclassified_do_not_stop_batch():
    ts = [tr("A", labor="tunel", rmr_valor=70), tr("B"), tr("C", rmr_valor=500),
          tr("D", labor="rampa", gsi_celda="LF/MP"), tr("E", rmr_valor=70), tr("F", luz=None, rmr_valor=30)]
    rs = rm.classify_tramos(ts, TABLES)
    assert [r.label for r in rs] == [None, None, None, None, "good", "poor"]
    assert rs[0].warnings[0].startswith("no table for this labor/span: ")
    assert rs[1].warnings == ("missing input for RMR",)
    assert all(r.warnings for r in rs[:4])
    s = rm.summarize(rs)
    assert (s.total, s.classified, s.unclassified) == (6, 2, 4)
    assert s.by_labor_class == {("galería", "good"): 1, ("galería", "poor"): 1}
    assert s.by_support == {"I": 1, "III": 1} and s.warnings_count == 4


def test_span_none_needs_single_table_without_span():
    tabs = [lab("galería", rmr_tab(), (0.5, 5)), lab("galería", rmr_tab(), (5, 9))]
    assert "no table" in one(tr(luz=None, rmr_valor=70), tabs).warnings[0]
    tabs.append(lab("galería", rmr_tab()))
    assert one(tr(luz=None, rmr_valor=70), tabs).label == "good"


def test_empty_tables():
    with pytest.raises(ValueError):
        rm.classify_tramos([tr()], [])


def test_no_identification_in_warnings():
    t = tr(labor="tunel", labor_codigo="SECRETO-123", zona_nivel="SECRETO-123", rmr_valor=500)
    ts = [t, tr(labor_codigo="SECRETO-123", rmr_valor=500), tr(labor_codigo="SECRETO-123")]
    for r in rm.classify_tramos(ts, TABLES):
        assert "SECRETO-123" not in " ".join(r.warnings)


COLS = ["id_tramo", "tipo_labor", "luz_m", "tabla_luz_min_m", "tabla_luz_max_m", "metodo", "edicion_base",
        "valor_entrada", "celda", "clase", "sostenimiento", "sostenimiento_orden", "sost_instalado", "avisos"]


def results():
    return rm.classify_tramos([tr("A", rmr_valor=70, sost_instalado="II"), tr("B", labor="tunel")], TABLES)


def test_save_xlsx(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    p = rm.save_results(results(), tmp_path / "r.xlsx")
    rows = list(openpyxl.load_workbook(p).active.values)
    assert list(rows[0]) == COLS
    assert rows[1][:2] == ("A", "galeria") and rows[1][9:12] == ("good", "I", 1) and rows[1][12] == "II"
    assert "differs from recommended" in rows[1][13]
    assert rows[2][9] is None and "no table" in rows[2][13]


def test_save_csv(tmp_path):
    p = rm.save_results(results(), tmp_path / "r.csv")
    head, a, b = p.read_text(encoding="utf-8-sig").splitlines()
    sep = ";" if ";" in head else ","
    assert head.split(sep) == COLS
    assert a.split(sep)[0] == "A" and b.split(sep)[9] == ""


def test_save_bad_extension(tmp_path):
    with pytest.raises(ValueError):
        rm.save_results(results(), tmp_path / "r.txt")
