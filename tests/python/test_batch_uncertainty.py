import csv
import re

import pytest

import rockmasspy as rm
from rockmasspy.cli import main

from test_batch import CAT, lab, tr

openpyxl = pytest.importorskip("openpyxl")

TABLE = rm.RangeTable("RMR", "RMR89", [rm.RangeClass(0, 40, "IV", "III"), rm.RangeClass(40, 100, "III", "II")])
QTABLE = rm.RangeTable("Q", "Q-NGI-2025", [rm.RangeClass(0, 1, "poor", "III"), rm.RangeClass(1, 10, "fair", "II"),
                                           rm.RangeClass(10, 1000, "good", "I")])
TABLES = [lab("galeria", TABLE), lab("crucero", QTABLE)]
Q_OK = dict(rqd_pct=90, jn=4, jr=3, ja=1, jw=1, srf=15)  # Q = 4.5


def drow(i="T1", var="rmr_valor", dist="normal", media=41.0, sd=4.0, lo=30.0, hi=55.0, fila=2):
    return rm.TramoDistributionRow(i, var, dist, media, sd, lo, hi, fila)


def run(tramos, dists, tables=TABLES, **kw):
    return rm.classify_tramos(tramos, tables, distributions=dists, **kw)


def test_probabilities_by_class():
    (r,) = run([tr(rmr_valor=41)], [drow()], iterations=2000, seed=3)
    assert r.label == "III" and r.n_valid == 2000
    assert set(r.probabilities) == {"IV", "III"} and abs(sum(r.probabilities.values()) - 1) < 1e-12
    assert 0.55 < r.probabilities["III"] < 0.63  # P(X >= 40) con N(41, 4) truncada a [30, 55]


def test_columns_and_probability_text(tmp_path):
    rs = run([tr(rmr_valor=41), tr("T2", rmr_valor=70)], [drow()], iterations=2000, seed=3)
    out = tmp_path / "r.csv"
    rm.save_results(rs, out)
    text = out.read_text(encoding="utf-8-sig")
    rows = list(csv.reader(text.splitlines(), delimiter=";" if ";" in text.splitlines()[0] else ","))
    head = rows[0]
    assert head[-5:] == ["clase_probable", "prob_clase_probable", "prob_clase", "probabilidades", "n_validas"]
    f = dict(zip(head, rows[1]))
    assert re.fullmatch(r"III \d+ %; IV \d+ %", f["probabilidades"])
    assert sum(int(x) for x in re.findall(r"(\d+) %", f["probabilidades"])) == 100
    assert f["clase_probable"] == "III" and f["n_validas"] == "2000"
    g = dict(zip(head, rows[2]))  # sin distribución: celdas vacías
    assert g["probabilidades"] == "" and g["n_validas"] == ""


def test_q_from_parameters_with_jn_sampled():
    (r,) = run([tr(labor="crucero", **Q_OK)], [drow(var="jn", media=4.0, sd=0.5, lo=3.0, hi=6.0)], iterations=500)
    assert r.label == "fair" and set(r.probabilities) <= {"poor", "fair", "good"} and r.n_valid == 500
    assert r.probabilities["fair"] > 0.5


def test_q_given_and_jn_sampled_is_an_error():
    with pytest.raises(ValueError) as e:
        run([tr(labor="crucero", q_valor=4.5, **{k: v for k, v in Q_OK.items() if k == "jn"})],
            [drow(var="jn", media=4.0, sd=0.5, lo=3.0, hi=6.0, fila=7)])
    assert str(e.value) == "sheet 'Distribuciones', row 7, column 'variable': jn cannot be sampled when q_valor is given"


def test_sampled_column_empty_in_tramos():
    with pytest.raises(ValueError, match=r"row 2, column 'rmr_valor': required because it is sampled in Distribuciones"):
        run([tr(rmr_valor=None)], [drow()])


def test_unknown_id_tramo_names_row_not_id():
    with pytest.raises(ValueError) as e:
        run([tr(rmr_valor=41)], [drow(i="ZZSENT-9", fila=5)])
    assert str(e.value) == "sheet 'Distribuciones', row 5, column 'id_tramo': no tramo with this id_tramo"


def test_no_distributions_same_as_plain():
    ts = [tr(rmr_valor=41), tr("T2", rmr_valor=70), tr("T3", labor="otra", rmr_valor=5)]
    a, b = rm.classify_tramos(ts, TABLES), rm.classify_tramos(ts, TABLES, distributions=None)
    assert a == b and all(r.probabilities is None and r.n_valid is None for r in a)


def test_tramo_without_table_does_not_stop_batch():
    ts = [tr("T1", labor="tunel", rmr_valor=41), tr("T2", rmr_valor=41)]
    rs = run(ts, [drow("T1"), drow("T2", fila=3)], iterations=200)
    assert rs[0].label is None and rs[0].warnings[0].startswith("no table for this labor/span")
    assert rs[0].probabilities is None and rs[1].probabilities is not None


def test_sample_outside_core_domain_names_the_variable():
    ts = [tr(labor="crucero", **Q_OK)]
    with pytest.raises(ValueError) as e:
        run(ts, [drow(var="rqd_pct", media=90.0, sd=10.0, lo=60.0, hi=150.0)], iterations=300)
    assert "variable 'rqd_pct'" in str(e.value) and "narrow its minimum and maximum" in str(e.value)
    assert not re.search(r"\d{3}", str(e.value).replace("300", ""))


def test_variable_not_used_by_the_method():
    with pytest.raises(ValueError, match=r"row 4, column 'variable': not used by method RMR"):
        run([tr(rmr_valor=41, gsi_valor=50)], [drow(var="gsi_valor", fila=4)])


def test_exact_edge_value_keeps_less_favourable_class_and_boundary_warning():
    (r,) = run([tr(rmr_valor=40)], [drow(media=40.0, sd=3.0, lo=30.0, hi=50.0)], iterations=200)
    assert r.label == "IV" and any("near the boundary between classes" in w for w in r.warnings)


def test_load_tramo_distributions_roundtrip_and_errors(tmp_path):
    p = tmp_path / "d.csv"
    p.write_text("id_tramo,variable,distribucion,media,desviacion,minimo,maximo\n"
                 "ZZSENT-1,rmr_valor,normal,41,4,30,55\nZZSENT-1,rmr_valor,uniforme,,,30,55\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"row 3, column 'variable': duplicate id_tramo and variable") as e:
        rm.load_tramo_distributions(p, sheet="d")
    assert "ZZSENT" not in str(e.value)
    p.write_text("id_tramo,variable,distribucion,media,desviacion,minimo,maximo\n"
                 "ZZSENT-1,rmr_valor,normal,41,4,30,55\n", encoding="utf-8")
    (row,) = rm.load_tramo_distributions(p)
    assert (row.id_tramo, row.variable, row.fila) == ("ZZSENT-1", "rmr_valor", 2) and "ZZSENT" not in repr(row)
    p.write_text("id_tramo,variable,distribucion,media,desviacion,minimo,maximo\n"
                 "ZZSENT-1,peso,normal,41,4,30,55\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"row 2, column 'variable': unknown variable"):
        rm.load_tramo_distributions(p)


def test_bad_iterations_and_sampling():
    with pytest.raises(ValueError, match="iterations"):
        run([tr(rmr_valor=41)], [drow()], iterations=0)
    with pytest.raises(ValueError, match="sampling"):
        run([tr(rmr_valor=41)], [drow()], sampling="x")


# --- informe ---

def test_report_has_class_probability_table_only_with_probabilities():
    from rockmasspy import report as rp

    rs = run([tr(rmr_valor=41)], [drow()], iterations=300)
    for lang, cap in (("es", "Probabilidad de clase por tramo"), ("en", "Class probability by tramo")):
        rep = rp.build_memoria(rs, TABLES, title="x", lang=lang)
        s4 = next(s for s in rep.sections if s.number == "4")
        caps = [b.caption for b in s4.blocks if hasattr(b, "caption")]
        assert cap in caps
        tab = next(b for b in s4.blocks if getattr(b, "caption", None) == cap)
        assert tab.rows[0][0] == "T1" and re.fullmatch(r"III \d+ %; IV \d+ %", tab.rows[0][4])
        assert re.fullmatch(r"\d+%", tab.rows[0][2]) and re.fullmatch(r"\d+%", tab.rows[0][3])
    plain = rp.build_memoria(rm.classify_tramos([tr(rmr_valor=41)], TABLES), TABLES, title="x")
    s4 = next(s for s in plain.sections if s.number == "4")
    assert len(s4.blocks) == 1


# --- CLI ---

def xlsx(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Tramos"
    ws.append(["id_tramo", "tipo_labor", "luz_m", "rmr_valor"])
    ws.append(["ZZSENT-1", "galeria", 4.0, 41])
    ws.append(["ZZSENT-2", "galeria", 4.0, 70])
    wd = wb.create_sheet("Distribuciones")
    wd.append(["id_tramo", "variable", "distribucion", "media", "desviacion", "minimo", "maximo"])
    wd.append(["ZZSENT-1", "rmr_valor", "normal", 41, 4, 30, 55])
    p = tmp_path / "T.xlsx"
    wb.save(p)
    t = tmp_path / "galeria.json"
    rm.save_json(lab("galeria", TABLE), t)
    return p, t


def test_cli_classify_with_distributions(tmp_path, capsys):
    p, t = xlsx(tmp_path)
    out = tmp_path / "r.csv"
    code = main(["classify", str(p), "--tables", str(t), "--distributions", str(p), "-o", str(out),
                 "--iterations", "500", "--seed", "3"])
    cap = capsys.readouterr()
    assert code == 0 and cap.err == ""
    assert "probabilistic: 1 of 2 tramos with distributions" in cap.out.splitlines()
    assert "ZZSENT" not in cap.out
    assert "probabilidades" in out.read_text(encoding="utf-8-sig").splitlines()[0]


def test_cli_bad_distribution_exit_1_and_empty_stdout(tmp_path, capsys):
    p, t = xlsx(tmp_path)
    wb = openpyxl.load_workbook(p)
    wb["Distribuciones"]["C2"] = "gamma"
    wb.save(p)
    code = main(["classify", str(p), "--tables", str(t), "--distributions", str(p), "-o", str(tmp_path / "r.csv")])
    cap = capsys.readouterr()
    assert code == 1 and cap.out == "" and cap.err.startswith("error: ") and cap.err.count("\n") == 1
    assert "ZZSENT" not in cap.err


def test_cli_iterations_need_distributions(tmp_path, capsys):
    p, t = xlsx(tmp_path)
    code = main(["classify", str(p), "--tables", str(t), "-o", str(tmp_path / "r.csv"), "--iterations", "10"])
    cap = capsys.readouterr()
    assert code == 1 and "--iterations needs --distributions" in cap.err and cap.out == ""


# --- ronda final (I1, M2, M6) ---

@pytest.mark.parametrize("seed", [1, 2, 3])
@pytest.mark.parametrize("worst_first", [True, False])
def test_probability_tie_goes_to_less_favourable_class(seed, worst_first):
    from rockmasspy.batch import _fila_p
    cls = [rm.RangeClass(0, 40, "IV", "III"), rm.RangeClass(40, 100, "III", "II")]
    t = rm.RangeTable("RMR", "RMR89", cls if worst_first else cls[::-1])
    (r,) = run([tr(rmr_valor=40)], [drow(media=40.0, sd=4.0, lo=30.0, hi=50.0)], tables=[lab("galeria", t)],
               iterations=2000, seed=seed)
    assert r.probabilities["IV"] == r.probabilities["III"] == 0.5
    assert r.label == "IV" and _fila_p(r)[0] == "IV"


def test_tiny_probability_shows_less_than_one_percent():
    from rockmasspy.batch import _percent_text
    assert _percent_text({"III": 0.999, "IV": 0.001, "V": 0.0}) == "III 100 %; IV <1 %"
    assert _percent_text({"III": 0.6, "IV": 0.4}) == "III 60 %; IV 40 %"


def test_error_names_the_real_tramos_sheet():
    with pytest.raises(ValueError, match=r"sheet 'Hoja1', row 5"):
        run([tr("T2", rmr_valor=41, fila=5)], [drow("T2", media=95.0, sd=30.0, lo=-50.0, hi=200.0)],
            tramos_sheet="Hoja1")


def test_cli_error_names_real_sheet(tmp_path, capsys):
    p, t = xlsx(tmp_path)
    wb = openpyxl.load_workbook(p)
    wb["Tramos"].title = "Hoja1"
    wb["Hoja1"]["D2"] = None
    wb["Distribuciones"]["D2"] = 41
    wb.save(p)
    code = main(["classify", str(p), "--tables", str(t), "--sheet", "Hoja1", "--distributions", str(p),
                 "-o", str(tmp_path / "r.csv")])
    cap = capsys.readouterr()
    assert code == 1 and "sheet 'Hoja1', row 2" in cap.err and "ZZSENT" not in cap.err


def test_probability_between_half_and_one_percent_shows_less_than_one():
    """Entre 0.5 y 1 % salía «0 %» (hallazgo del notebook, 0.2.1)."""
    from rockmasspy.batch import _percent_text
    assert _percent_text({"III": 0.497, "IV": 0.497, "V": 0.006}) == "III 50 %; IV 49 %; V <1 %"


def test_each_tramo_gets_its_own_samples():
    """Dos tramos con la misma distribución no comparten las muestras (semilla propia por tramo, 0.2.1)."""
    from rockmasspy.batch import _tramo_seed
    assert _tramo_seed(3, "T1") != _tramo_seed(3, "T2") and _tramo_seed(3, "T1") == _tramo_seed(3, "T1")
    a, b = run([tr(rmr_valor=41), tr("T2", rmr_valor=41)], [drow(), drow("T2", fila=3)], iterations=300, seed=3,
               sampling="monte_carlo")
    assert a.probabilities != b.probabilities
