"""`rockmass recommend`: argumentos obligatorios, códigos 0/1/2, una línea por tramo sin ids y el centinela ZZSENT."""
import csv
import dataclasses
import re

import pytest

import rockmasspy as rm
from rockmasspy.batch import write_table
from rockmasspy.cli import main
from rockmasspy.history import HISTORY_TRAMO_COLUMNS

pytest.importorskip("openpyxl")
pred = pytest.importorskip("rockmasspy.predictive")

SENT = "ZZSENT"
N_BOOT = 100  # la CLI no mide la precisión del IC


def _sent(ts):
    return tuple(dataclasses.replace(t, labor_codigo=f"{SENT}-{t.labor_codigo}", zona_nivel=f"{SENT}-{t.zona_nivel}",
                                     litologia=f"{SENT}-{t.litologia}") for t in ts)


@pytest.fixture(scope="module")
def casos(tmp_path_factory):
    """Modelo «site» (histórico grande) y modelo no «site» (chico), y tramos nuevos en .xlsx y .csv con ZZSENT
    también en el id_tramo: el id solo puede aparecer en el archivo de resultados."""
    d = tmp_path_factory.mktemp(f"{SENT}-carpeta")
    grande, _ = pred.synthetic_history(seed=0, n_zones=8, labors_per_zone=12, tramos_per_labor=15)
    grande = rm.History(_sent(grande.tramos), grande.support_types, grande.inspections)
    rm.save_history_xlsx(grande, d / "historico.xlsx")
    chico, _ = pred.synthetic_history(seed=1, n_zones=2, labors_per_zone=3, tramos_per_labor=5)
    site = pred.fit_performance(grande, n_boot=N_BOOT)
    assert site.calibration == "site", site.calibration_reason
    pred.save_model(site, d / "site.json")
    no_site = pred.fit_performance(chico, n_boot=N_BOOT)
    assert no_site.calibration != "site"
    pred.save_model(no_site, d / "no_site.json")
    nuevos = tuple(dataclasses.replace(t, id_tramo=f"{SENT}-N{i}") for i, t in enumerate(grande.tramos[:5], 1))
    rm.save_history_xlsx(rm.History(nuevos, (), ()), d / "nuevos.xlsx")
    write_table(d / "nuevos.csv", HISTORY_TRAMO_COLUMNS,
                [[getattr(t, c) for c in HISTORY_TRAMO_COLUMNS] for t in nuevos], sheet="Tramos")
    return d


def run(capsys, *args):
    code = main(["recommend", *map(str, args)])
    cap = capsys.readouterr()
    assert SENT not in cap.out and SENT not in cap.err  # ni ids, ni labor, ni zona, ni la carpeta
    return code, cap


def _tramo_lines(out):
    return [x for x in out.splitlines() if re.match(r"tramo \d+: ", x)]


def test_one_line_per_tramo_and_exit_code(casos, capsys, tmp_path):
    out_csv = tmp_path / "rec.csv"
    code, cap = run(capsys, casos / "nuevos.xlsx", "--model", casos / "site.json", "--threshold", 0.6,
                    "--exposure-days", 365, "-o", out_csv)
    lines = _tramo_lines(cap.out)
    assert [x.split(":")[0] for x in lines] == [f"tramo {i}" for i in range(1, 6)]
    assert all("; calibration site" in x and "; alerts: " in x for x in lines)
    assert "model: calibration site, threshold 0.6, exposure 365 days, interval 0.9" in cap.out
    blocked = [x for x in lines if "no recommendation: " in x or "alerts: none" not in x]
    assert code == (2 if blocked else 0)
    assert f"recommended: {sum('no recommendation' not in x for x in lines)} of 5" in cap.out
    assert "results: rec.csv" in cap.out and "the library recommends, the engineer decides" in cap.out
    with open(out_csv, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    assert tuple(rows[0]) == pred.RECOMMENDATION_COLUMNS
    ids = {r[0] for r in rows[1:]}
    assert ids == {f"{SENT}-N{i}" for i in range(1, 6)}  # los ids van solo en el archivo
    dec, mot = rows[0].index("decision_ingeniero"), rows[0].index("motivo")
    assert all(r[dec] == "" and r[mot] == "" for r in rows[1:])


def test_threshold_nobody_meets_exit_2(casos, capsys):
    code, cap = run(capsys, casos / "nuevos.xlsx", "--model", casos / "site.json", "--threshold", 0.001,
                    "--exposure-days", 365)
    assert code == 2
    assert all("no recommendation: " in x for x in _tramo_lines(cap.out))
    assert "recommended: 0 of 5" in cap.out


def test_model_not_site_never_chooses(casos, capsys):
    code, cap = run(capsys, casos / "nuevos.xlsx", "--model", casos / "no_site.json", "--threshold", 0.9,
                    "--exposure-days", 365)
    assert code == 2
    lines = _tramo_lines(cap.out)
    assert len(lines) == 5 and all("no recommendation: " in x and "site" not in x.split("calibration ")[-1]
                                   for x in lines)


def test_csv_input_same_lines(casos, capsys):
    args = ("--model", casos / "site.json", "--threshold", 0.5, "--exposure-days", 200)
    _, xlsx = run(capsys, casos / "nuevos.xlsx", *args)
    _, csv_ = run(capsys, casos / "nuevos.csv", *args)
    assert _tramo_lines(xlsx.out) == _tramo_lines(csv_.out)


def test_practice_from_adds_the_conformal_set(casos, capsys):
    _, cap = run(capsys, casos / "nuevos.xlsx", "--model", casos / "site.json", "--threshold", 0.5,
                 "--exposure-days", 365, "--practice-from", casos / "historico.xlsx")
    assert all("; practice set " in x for x in _tramo_lines(cap.out))


def test_practice_from_with_other_type_codes_exit_1(casos, capsys, tmp_path):
    """Un histórico con otros códigos de tipo que el modelo: error (decisión), código 1 y sin valores ni ruta."""
    h = rm.load_history(casos / "historico.xlsx")
    otro = tmp_path / f"{SENT}-otro.xlsx"
    rm.save_history_xlsx(rm.History(h.tramos, h.support_types[:-1], h.inspections), otro)
    code, cap = run(capsys, casos / "nuevos.xlsx", "--model", casos / "site.json", "--threshold", 0.5,
                    "--exposure-days", 365, "--practice-from", otro)
    assert code == 1 and cap.out == ""
    assert cap.err == "error: --practice-from: its support type codes do not match the model's\n"


@pytest.mark.parametrize("falta, args", [
    ("--threshold", ["--model", "M", "--exposure-days", "365"]),
    ("--exposure-days", ["--model", "M", "--threshold", "0.3"]),
    ("--model", ["--threshold", "0.3", "--exposure-days", "365"])])
def test_required_arguments_exit_1(capsys, falta, args):
    """Umbral, horizonte y modelo son obligatorios: argparse sale con 1 (_Parser) y no lee nada."""
    with pytest.raises(SystemExit) as e:
        main(["recommend", "nuevos.xlsx", *args])
    assert e.value.code == 1
    err = capsys.readouterr().err
    assert f"error: the following arguments are required: {falta}" in err


def test_values_and_outputs_checked_before_reading(casos, capsys, monkeypatch, tmp_path):
    def no_leer(*a, **k):
        raise AssertionError("the model was read before checking the arguments")

    monkeypatch.setattr(pred, "load_model", no_leer)
    base = [casos / "nuevos.xlsx", "--model", casos / "site.json"]
    errs = []
    for extra in (["--threshold", 1.5, "--exposure-days", 365], ["--threshold", 0, "--exposure-days", 365],
                  ["--threshold", 0.3, "--exposure-days", 0],
                  ["--threshold", 0.3, "--exposure-days", 365, "-o", tmp_path / f"{SENT}.txt"],
                  ["--threshold", 0.3, "--exposure-days", 365, "-o", tmp_path / SENT / "rec.csv"]):
        code, cap = run(capsys, *base, *extra)
        assert code == 1 and cap.out == ""
        errs.append(cap.err.strip())
    assert errs == ["error: --threshold must be a probability strictly between 0 and 1"] * 2 + [
        "error: --exposure-days must be greater than 0", "error: --output must end in .csv or .xlsx",
        "error: --output: its folder does not exist"]


def test_bad_or_missing_model_exit_1_without_path(casos, capsys, tmp_path):
    malo = tmp_path / f"{SENT}-modelo.json"
    malo.write_text('{"schema_version": 1}', encoding="utf-8")
    args = (casos / "nuevos.xlsx", "--threshold", 0.3, "--exposure-days", 365)
    code, cap = run(capsys, args[0], "--model", malo, *args[1:])
    assert code == 1 and cap.err.startswith("error: ")
    code, cap = run(capsys, args[0], "--model", tmp_path / f"{SENT}-no.json", *args[1:])
    assert code == 1 and cap.err == "error: model file could not be read (missing, in use or no permission)\n"
    code, cap = run(capsys, tmp_path / f"{SENT}.csv", "--model", casos / "site.json", *args[1:])
    assert code == 1 and cap.err == "error: tramos file not found\n"
