import re

import pytest

from rockmasspy.cli import main

BASE = ["bem", "--sigma1", "30", "--sigma3", "15", "--e", "10000", "--nu", "0.2", "--criterion", "MC", "--c", "5",
        "--phi", "30"]
CIRCLE = BASE + ["--circle", "3", "--grid=-9:9:-9:9:20:20"]


def test_circle_prints_min_sf(capsys):
    code = main(CIRCLE)
    out = capsys.readouterr().out
    assert code in (0, 2) and "min SF" in out and "tension points" in out
    m = re.search(r"min SF: ([0-9.]+)", out)
    assert (code == 2) == (float(m.group(1)) < 1 or "tension points: 0" not in out)


def test_excavation_ids_never_printed(tmp_path, capsys):
    f = tmp_path / "Excavaciones.csv"
    # separador ';' y coma decimal; el orden de las filas no manda, manda `orden`
    f.write_text("id;orden;x;y\nZZSENT;2;4,0;0\nZZSENT;1;0;0\nZZSENT;3;4,0;4,0\nZZSENT;4;0;4,0\n",
                 encoding="utf-8")
    out_csv = tmp_path / "campo.csv"
    code = main(BASE + ["--excavations", str(f), "--grid=-8:12:-8:12:10:10", "--output", str(out_csv)])
    cap = capsys.readouterr()
    assert code in (0, 2)
    assert "ZZSENT" not in cap.out + cap.err
    txt = out_csv.read_text(encoding="utf-8-sig")
    assert "ZZSENT" not in txt and not re.search(r"inf|nan", txt, re.I)


def test_self_crossing_polygon_is_input_error(tmp_path, capsys):
    f = tmp_path / "e.csv"
    f.write_text("id,orden,x,y\nZZSENT,1,0,0\nZZSENT,2,4,4\nZZSENT,3,4,0\nZZSENT,4,0,4\n", encoding="utf-8")
    assert main(BASE + ["--excavations", str(f)]) == 1
    cap = capsys.readouterr()
    assert cap.out == "" and cap.err.startswith("error: ") and cap.err.count("\n") == 1
    assert "ZZSENT" not in cap.err


def test_geometry_is_required_and_exclusive(capsys):
    assert main(BASE) == 1
    assert main(BASE + ["--circle", "3", "--horseshoe", "4:3"]) == 1
    assert capsys.readouterr().out == ""


def test_chart_and_report(tmp_path, capsys):
    pytest.importorskip("matplotlib")
    png, html = tmp_path / "c.png", tmp_path / "r.html"
    code = main(CIRCLE + ["--chart", str(png), "--report", str(html), "--lang", "en"])
    assert code in (0, 2) and png.stat().st_size > 0 and html.stat().st_size > 0
    out = capsys.readouterr().out
    assert "elastic analysis" in out.lower()


def test_horseshoe_runs(capsys):
    assert main(BASE + ["--horseshoe", "5:3", "--grid=-8:8:-6:10:12:12"]) in (0, 2)


def test_grid_help_documents_equals_form(capsys):
    with pytest.raises(SystemExit):
        main(["bem", "--help"])
    assert "--grid=XMIN:XMAX" in capsys.readouterr().out


@pytest.mark.parametrize("extra,opt", [(["--circle", "0"], "--circle"), (["--circle", "-2"], "--circle"),
                                       (["--horseshoe", "4:0"], "--horseshoe"),
                                       (["--circle", "3", "--grid=-9:9:-9:9:20.5:20"], "--grid")])
def test_invalid_geometry_options(extra, opt, capsys):
    assert main(BASE + extra) == 1
    cap = capsys.readouterr()
    assert cap.out == "" and cap.err.startswith("error: ") and opt in cap.err and cap.err.count("\n") == 1


def test_duplicate_orden_is_input_error(tmp_path, capsys):
    f = tmp_path / "e.csv"
    f.write_text("id,orden,x,y\nZZSENT,1,0,0\nZZSENT,1,4,0\nZZSENT,3,4,4\nZZSENT,4,0,4\n", encoding="utf-8")
    assert main(BASE + ["--excavations", str(f)]) == 1
    cap = capsys.readouterr()
    assert cap.out == "" and "'orden'" in cap.err and "ZZSENT" not in cap.err


def test_output_has_coarse_and_corrected_columns(tmp_path, capsys):
    out_csv = tmp_path / "campo.csv"
    main(CIRCLE + ["--output", str(out_csv)])
    capsys.readouterr()
    head = out_csv.read_text(encoding="utf-8-sig").splitlines()[0]
    assert "coarse" in head and "corrected" in head


def test_core_runtime_error_is_single_error_line(monkeypatch, capsys):
    import rockmasspy.bem as bem

    def boom(*a, **k):
        raise RuntimeError("singular matrix")

    monkeypatch.setattr(bem, "analyze_bem", boom)
    assert main(CIRCLE) == 1
    cap = capsys.readouterr()
    assert cap.err.startswith("error:") and "Traceback" not in cap.err
