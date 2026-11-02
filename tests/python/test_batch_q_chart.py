import csv

import pytest

import rockmasspy as rm
from rockmasspy.batch import _COLUMNS, _Q_COLUMNS

from test_batch import TABLES, tr


def _cabecera(p):
    sep = rm.csv_io._system_csv_format()[0]  # el separador depende del computador
    return next(csv.reader(open(p, encoding="utf-8-sig"), delimiter=sep))


def tramos():
    out = []
    for i, labor in enumerate(["galeria", "galería"]):
        for j, q in enumerate([0.05, 0.4, 4.5, 30.0]):
            out.append(tr(f"T{i}{j}", labor, 4.0 + j, q_valor=q))
    return out


def classify(ts=None):
    return rm.classify_tramos(ts or tramos(), TABLES)


def test_referencia_con_q_valor_y_mapeo_con_acentos():
    res = rm.add_q_chart_reference(classify(), {"galeria": ("A", 4.0), "*": "C"})
    assert len(res) == 8 and all(r.q_chart is not None for r in res)  # galeria == galería por _key
    assert {r.q_chart.esr_used for r in res} == {4.0}
    assert all(r.q_chart.edition == "Q-NGI-2025" and r.q_chart.walls is None for r in res)


def test_asterisco_y_spec_suelto():
    a = rm.add_q_chart_reference(classify(), {"galeria": "C", "*": "D"})
    b = rm.add_q_chart_reference(classify(), "C")
    assert all(r.q_chart.esr_category == "C" for r in b)
    assert a[0].q_chart.esr_used == b[0].q_chart.esr_used


def test_q_calculado_desde_parametros():
    t = tr("P", q_valor=None, rqd_pct=80, jn=9, jr=1.5, ja=1, jw=1, srf=2.5)
    [r] = rm.add_q_chart_reference(classify([t]), "C")
    assert r.q_chart is not None and r.q_chart.roof.q == pytest.approx(80 / 9 * 1.5 / 1 * 1 / 2.5, rel=1e-6)


@pytest.mark.parametrize("t, spec, msg", [
    (tr(q_valor=1.0), {"crucero": "C"}, "no ESR for this labor"),
    (tr(luz=None, q_valor=1.0), "C", "missing span (luz_m)"),
    (tr(), "C", "missing Q"),
    (tr(q_valor=1.0, q_edicion="Q-1974"), "C", "Q-1974 not supported"),
    (tr(q_valor=1.0, q_edicion="Q-NGI-2015"), "C", "Q edition Q-NGI-2015 differs from chart edition Q-NGI-2025"),
    (tr(q_valor=1.0), ("B", 9.0), "ESR 9 outside category B"),
])
def test_avisos_por_tramo(t, spec, msg):
    [r] = rm.add_q_chart_reference(classify([t]), spec)
    assert any(msg in w for w in r.q_chart_warnings)
    if "outside" not in msg:
        assert r.q_chart is None


def test_valueerror_de_recommend_se_vuelve_aviso():
    [r] = rm.add_q_chart_reference(classify([tr(q_valor=1.0, luz=1e400)]), "C")  # luz infinita
    assert r.q_chart is None and r.q_chart_warnings


@pytest.mark.parametrize("spec", ["Z", ("A", float("nan")), "A", {"*": "Z"}])
def test_esr_invalido_lanza_antes(spec):
    with pytest.raises(ValueError):
        rm.add_q_chart_reference(iter(tramos()), spec)


def test_edicion_desconocida():
    with pytest.raises(ValueError):
        rm.add_q_chart_reference(classify(), "C", edition="Q-1999")


def test_summarize_igual_y_clasificacion_intacta():
    base = classify()
    res = rm.add_q_chart_reference(base, "C")
    assert rm.summarize(res) == rm.summarize(base)
    assert [(r.label, r.support, r.warnings) for r in res] == [(r.label, r.support, r.warnings) for r in base]


def test_crosstab():
    res = rm.add_q_chart_reference(classify(), "C")
    ct = rm.q_chart_crosstab(res)
    assert sum(ct.values()) == 8
    assert ct == rm.q_chart_crosstab(res + [r for r in rm.add_q_chart_reference(classify([tr(q_valor=1)]), {"x": "C"})])
    assert all(isinstance(k[1], int) for k in ct)


def test_csv_y_excel_con_columnas_q(tmp_path):
    res = rm.add_q_chart_reference(classify(), "C")
    p = rm.save_results(res, tmp_path / "r.csv")
    cab = _cabecera(p)
    assert tuple(cab) == _COLUMNS + _Q_COLUMNS and len(_Q_COLUMNS) == 12
    openpyxl = pytest.importorskip("openpyxl")
    x = rm.save_results(res, tmp_path / "r.xlsx")
    ws = openpyxl.load_workbook(x).active
    assert tuple(c.value for c in ws[1]) == _COLUMNS + _Q_COLUMNS and ws.max_row == 9


def test_sin_referencias_columnas_de_la_1d(tmp_path):
    p = rm.save_results(classify(), tmp_path / "r.csv")
    cab = _cabecera(p)
    assert tuple(cab) == _COLUMNS


def test_espaciamiento_por_categoria():
    res = rm.add_q_chart_reference(classify(), "C")
    from rockmasspy.batch import _fila
    for r in res:
        cat = r.q_chart.roof.category
        f = _fila(r, True)
        sp = (r.q_chart.roof.bolt_spacing_without_sfr_m if cat <= 2 else r.q_chart.roof.bolt_spacing_with_sfr_m)
        assert f[len(_COLUMNS) + 6] == (sp[0] if sp else None)


def test_mismo_q_otra_edicion_sin_referencia_foco3():
    [r] = rm.add_q_chart_reference(classify([tr(q_valor=0.4, q_edicion="Q-NGI-2015")]), "C")
    assert r.q_chart is None


def test_sin_secreto_en_avisos_foco5():
    ts = [tr(f"T{i}", q_valor=q, labor_codigo="SECRETO-123", luz=l)
          for i, (q, l) in enumerate([(0.01, 3.0), (5000.0, 2.0), (1.0, 40.0)])]
    res = rm.add_q_chart_reference(classify(ts), ("A", 5.0))
    assert not any("SECRETO-123" in w for r in res for w in r.q_chart_warnings)


def test_avisos_del_q_calculado_en_tramos_por_tabla_rmr():  # M1
    t = tr("P", q_valor=None, rmr_valor=70, rqd_pct=100, jn=0.5, jr=4, ja=0.75, jw=1, srf=0.5)
    [r] = rm.add_q_chart_reference(classify([t]), "C")
    assert r.method != "Q" and r.q_chart_warnings[0] == "Q outside 0.001-1000"
    assert len(set(r.q_chart_warnings)) == len(r.q_chart_warnings)
