import re

import pytest

pytest.importorskip("scipy")

from rockmasspy.cli import main
from rockmasspy.predictive.surrogate_bench import planar_runs


@pytest.fixture(scope="module")
def runs_csv(tmp_path_factory):
    d = planar_runs(120, seed=3)
    f = tmp_path_factory.mktemp("sg") / "Corridas.csv"
    lines = [",".join([*d.names, "fs", "escenario"])]
    for x, y, g in zip(d.X, d.y, d.groups):
        lines.append(",".join([*(repr(float(v)) for v in x), repr(float(y)), g]))
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f, d


BASE = ["surrogate", "--output", "fs", "--group", "escenario"]


def test_validate_prints_rmse(runs_csv, capsys):
    f, _ = runs_csv
    code = main([*BASE, "--runs", str(f), "--validate"])
    out = capsys.readouterr().out
    assert code in (0, 2) and "rmse:" in out and "rmse mean model:" in out
    assert (code == 2) == ("useful: no" in out)


def test_predict_out_of_domain_exits_2(runs_csv, tmp_path, capsys):
    f, d = runs_csv
    inside = d.X.mean(axis=0)
    outside = inside.copy()
    outside[d.names.index("friction_deg")] = 80.0
    pts = tmp_path / "Predicciones.csv"
    pts.write_text(",".join(d.names) + "\n" + "\n".join(",".join(repr(float(v)) for v in r)
                                                         for r in (inside, outside)) + "\n", encoding="utf-8")
    out_csv = tmp_path / "pred.csv"
    code = main([*BASE, "--runs", str(f), "--predict", str(pts), "--predict-output", str(out_csv)])
    assert code == 2 and "outside domain: 1" in capsys.readouterr().out
    lines = out_csv.read_text(encoding="utf-8-sig").splitlines()
    assert lines[0].endswith("fs,in_domain" ) or lines[0].split(re.search("[;,]", lines[0]).group())[-2:] == ["fs", "in_domain"]
    sep = re.search("[;,]", lines[0]).group()
    first, second = lines[1].split(sep), lines[2].split(sep)
    assert first[-1] == "1" and first[-2] != ""
    assert second[-1] == "0" and second[-2] == ""


def test_distributions_prints_pof(runs_csv, tmp_path, capsys):
    f, _ = runs_csv
    dist = tmp_path / "Distribuciones.csv"
    dist.write_text("variable,distribucion,media,desviacion,minimo,maximo\n"
                    "cohesion,normal,12,3,2,25\nfriction_deg,normal,32,4,20,45\n", encoding="utf-8")
    code = main([*BASE, "--runs", str(f), "--distributions", str(dist), "--n", "2000"])
    out = capsys.readouterr().out
    assert code in (0, 2) and "pof:" in out and "n_out_of_domain:" in out


def test_report_written(runs_csv, tmp_path, capsys):
    f, _ = runs_csv
    rep = tmp_path / "r.html"
    code = main([*BASE, "--runs", str(f), "--report", str(rep), "--lang", "en"])
    assert code in (0, 2) and rep.exists()


def test_errors_one_line_empty_stdout(runs_csv, tmp_path, capsys):
    f, _ = runs_csv
    assert main([*BASE[:1], "--output", "nope", "--runs", str(f)]) == 1
    cap = capsys.readouterr()
    assert cap.out == "" and cap.err.startswith("error:") and cap.err.count("\n") == 1
    few = tmp_path / "poca.csv"
    few.write_text("a,b,fs\n1,2,3\n2,3,4\n3,5,6\n", encoding="utf-8")
    assert main(["surrogate", "--runs", str(few), "--output", "fs"]) == 1
    cap = capsys.readouterr()
    assert cap.out == "" and "runs" in cap.err
