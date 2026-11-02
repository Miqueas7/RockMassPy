import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import rockmasspy as rm
from rockmasspy.cli import main

from test_batch import CAT, q_tab, rmr_tab

openpyxl = pytest.importorskip("openpyxl")

CAB = ["id_tramo", "tipo_labor", "labor_codigo", "zona_nivel", "este_m", "norte_m", "luz_m", "rmr_valor"]
SECRETOS = ["SECRETO-123", "NIVEL-SECRETO", "512345.678", "8765432.1", "TRX-77", "TRY-88"]


def tramos_xlsx(tmp_path, extra=(), cab=CAB, name="tramos.xlsx"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Tramos"
    ws.append(cab)
    ws.append(["TRX-77", "galeria", "SECRETO-123", "NIVEL-SECRETO", 512345.678, 8765432.1, 4.0, 70])
    for f in extra:
        ws.append(f)
    p = tmp_path / name
    wb.save(p)
    return p


@pytest.fixture
def tabla(tmp_path):
    p = tmp_path / "galeria.json"
    rm.save_json(rm.LaborTable("galería", CAT, rmr_tab(), span_m=(1, 6)), p)
    return p


MALO = ["TRY-88", "otra", "SECRETO-123", "NIVEL-SECRETO", 512345.678, 8765432.1, 4.0, 30]


def sin_fuga(capsys):
    cap = capsys.readouterr()
    for s in SECRETOS:
        assert s not in cap.out and s not in cap.err
    return cap


def test_load_table_dispatch(tmp_path, tabla):
    assert rm.load_table(tabla).labor_type == "galería"
    csvdir = tmp_path / "csv"
    rm.save_csv_dir(rm.load_table(tabla), csvdir)
    assert rm.load_table(csvdir).labor_type == "galería"
    with pytest.raises(ValueError, match=r"\.json"):
        rm.load_table(tmp_path / "x.txt")


def test_check_ok_and_issues(tmp_path, tabla, capsys):
    assert main(["check", str(tabla)]) == 2  # la tabla sintética no tiene elementos de sostenimiento
    assert "issue(s)" in capsys.readouterr().out
    bolt = rm.Bolt("grouted", 2.0, 1.5)
    limpia = rm.LaborTable("galería", rm.SupportCatalog([rm.SupportType("I", 1, bolt=bolt)]), rm.RangeTable(
        "RMR", "RMR89", [rm.RangeClass(lo, lo + 20, f"c{lo}", "I") for lo in range(0, 100, 20)]))
    pl = tmp_path / "limpia.json"
    rm.save_json(limpia, pl)
    assert main(["check", str(pl)]) == 0
    assert "0 issue(s)" in capsys.readouterr().out
    # RMR con un hueco entre clases: el validador avisa
    raro = rm.LaborTable("crucero", CAT, rm.RangeTable("RMR", "RMR89", [
        rm.RangeClass(0, 30, "poor", "III"), rm.RangeClass(50, 100, "good", "I")]))
    p = tmp_path / "raro.json"
    rm.save_json(raro, p)
    assert main(["check", str(p)]) == 2
    out = capsys.readouterr().out
    assert out.startswith("raro.json:") and "issue(s)" in out and "0 issue(s)" not in out


def test_classify_ok_and_unclassified(tmp_path, tabla, capsys):
    out = tmp_path / "res.csv"
    assert main(["classify", str(tramos_xlsx(tmp_path)), "--tables", str(tabla), "-o", str(out)]) == 0
    cap = sin_fuga(capsys)
    assert "total: 1" in cap.out and "classified: 1" in cap.out and "good: 1" in cap.out and out.exists()
    p2 = tramos_xlsx(tmp_path, [MALO], name="t2.xlsx")
    assert main(["classify", str(p2), "--tables", str(tabla), "-o", str(tmp_path / "r2.xlsx")]) == 2
    cap = sin_fuga(capsys)
    assert "unclassified: 1" in cap.out


def test_column_map(tmp_path, tabla, capsys):
    cab = [("RMR" if c == "rmr_valor" else c) for c in CAB]
    p = tramos_xlsx(tmp_path, cab=cab)
    mp = tmp_path / "m.json"
    mp.write_text(json.dumps({"RMR": "rmr_valor"}), encoding="utf-8")
    args = ["classify", str(p), "--tables", str(tabla), "-o", str(tmp_path / "r.csv")]
    assert main(args + ["--column-map", str(mp)]) == 0
    mp.write_text("[1]", encoding="utf-8")
    assert main(args + ["--column-map", str(mp)]) == 1
    assert capsys.readouterr().err.startswith("error: ")


def test_report_html_and_codes(tmp_path, tabla, capsys):
    p = tramos_xlsx(tmp_path)
    out = tmp_path / "i.html"
    assert main(["report", str(p), "--tables", str(tabla), "-o", str(out), "--no-figures", "--lang", "en"]) == 0
    sin_fuga(capsys)
    assert "<html" in out.read_text(encoding="utf-8")
    p2 = tramos_xlsx(tmp_path, [MALO], name="t2.xlsx")
    out2 = tmp_path / "i2.html"
    assert main(["report", str(p2), "--tables", str(tabla), "-o", str(out2), "--template", "anexo39b",
                 "--labor", "galería", "--no-figures"]) == 2
    sin_fuga(capsys)
    assert out2.exists()


def test_report_docx(tmp_path, tabla, capsys):
    pytest.importorskip("docx")
    out = tmp_path / "i.docx"
    assert main(["report", str(tramos_xlsx(tmp_path)), "--tables", str(tabla), "-o", str(out),
                 "--author", "Ing. Prueba", "--no-figures"]) == 0
    assert out.exists()


def test_report_input_errors(tmp_path, tabla, capsys):
    base = ["report", str(tramos_xlsx(tmp_path)), "--tables", str(tabla)]
    assert main(base + ["-o", str(tmp_path / "a.html"), "--labor", "galería"]) == 1
    assert main(base + ["-o", str(tmp_path / "a.pdf")]) == 1
    err = capsys.readouterr().err.strip().splitlines()
    assert len(err) == 2 and all(line.startswith("error: ") for line in err)


def test_error_one_line_and_debug(tmp_path, tabla, capsys):
    assert main(["classify", str(tmp_path / "no.xlsx"), "--tables", str(tabla), "-o", str(tmp_path / "r.csv")]) == 1
    err = capsys.readouterr().err
    assert err.startswith("error: ") and err.count("\n") == 1 and "Traceback" not in err
    with pytest.raises(FileNotFoundError):
        main(["--debug", "classify", str(tmp_path / "no.xlsx"), "--tables", str(tabla), "-o", str(tmp_path / "r.csv")])


def test_cartilla(tmp_path, tabla, capsys):
    pytest.importorskip("matplotlib")
    out = tmp_path / "c.png"
    assert main(["cartilla", str(tabla), "-o", str(out), "--lang", "en", "--size", "A4", "--brand", "X",
                 "--title", "T", "--no-lines"]) == 0
    assert out.stat().st_size > 0


def test_no_subcommand_prints_help(capsys):
    assert main([]) == 1
    assert "usage: rockmass" in capsys.readouterr().out


def test_entry_points():
    r = subprocess.run([sys.executable, "-m", "rockmasspy.cli", "--help"], capture_output=True, text=True)
    assert r.returncode == 0 and "rockmass" in r.stdout
    exe = shutil.which("rockmass", path=str(Path(sys.executable).parent))
    if exe:
        assert subprocess.run([exe, "--help"], capture_output=True).returncode == 0


def test_usage_errors_exit_one(capsys):
    for argv in (["classify"], ["bogus"]):
        with pytest.raises(SystemExit) as e:
            main(argv)
        assert e.value.code == 1
    assert "error:" in capsys.readouterr().err
    with pytest.raises(SystemExit) as e:
        main(["--help"])
    assert e.value.code == 0


def test_output_is_directory_exit_one(tmp_path, tabla, capsys):
    out = tmp_path / "out.xlsx"
    out.mkdir()
    assert main(["classify", str(tramos_xlsx(tmp_path)), "--tables", str(tabla), "-o", str(out)]) == 1
    err = capsys.readouterr().err
    assert err.startswith("error: ") and err.count("\n") == 1


# ---- Fase 2A: --esr y qsupport ----

QS = ["qsupport", "--esr-category", "C"]


def test_qsupport_hoek_case(capsys):
    # Categoría 3 y no 4: la lectura publicada de Hoek (4) viene de la carta de 1993 (xfail estricto en test_q_support).
    assert main(QS + ["--q", "4.5", "--span", "15", "--jn", "4", "--jr", "3"]) == 2  # la presión lleva aviso de unidad
    out = capsys.readouterr().out
    assert "category: 3" in out and "Q-NGI-2025-chart" in out and "Secondary" in out
    assert "the library recommends, the engineer decides" in out and "pressure" in out


def test_qsupport_exit_codes(tmp_path, capsys):
    assert main(["qsupport", "--esr-category", "E", "--q", "10", "--span", "5"]) == 0  # ESR 1: sin aviso
    assert "warning:" not in capsys.readouterr().out
    assert main(QS + ["--q", "10", "--span", "5", "--esr", "1.5"]) == 2  # ESR fuera de la categoría
    assert "warning:" in capsys.readouterr().out
    assert main(QS + ["--q", "0", "--span", "5"]) == 1
    assert capsys.readouterr().err.startswith("error: ")


def test_qsupport_esr_category_needs_esr(capsys):
    assert main(["qsupport", "--q", "4", "--span", "5", "--esr-category", "A"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("error: ") and err.count("\n") == 1 and "Traceback" not in err


def test_qsupport_chart_and_walls(tmp_path, capsys):
    pytest.importorskip("matplotlib")
    png = tmp_path / "q.png"
    main(QS + ["--q", "4.5", "--span", "6", "--wall-height", "8", "--high-stress", "--chart", str(png),
               "--lang", "en", "--edition", "Q-NGI-2015"])
    out = capsys.readouterr().out
    assert png.stat().st_size > 0 and "walls" in out and "Q-NGI-2015" in out


def test_help_lists_qsupport(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    assert "qsupport" in capsys.readouterr().out


def test_classify_esr_adds_reference(tmp_path, tabla, capsys):
    p = tramos_xlsx(tmp_path, [MALO], name="t2.xlsx")
    # el tramo sintético no trae Q: la referencia queda sin lectura, pero las columnas y la línea van
    out = tmp_path / "res.csv"
    code = main(["classify", str(p), "--tables", str(tabla), "-o", str(out), "--esr", "galeria=C", "*=A:4"])
    cap = sin_fuga(capsys)
    assert code == 2  # el 2 viene de 'unclassified', no de la carta (R14)
    assert "q chart (Q-NGI-2025): 0 with reference, 2 without" in cap.out
    assert "q_carta_" in out.read_text(encoding="utf-8-sig").splitlines()[0]
    assert cap.out.index("q chart") < cap.out.index("results:")


def test_classify_esr_crosstab_lines(tmp_path, tabla, capsys):
    cab = CAB + ["q_valor"]
    p = tramos_xlsx(tmp_path, cab=cab)
    wb = openpyxl.load_workbook(p)
    ws = wb.active
    ws["I2"] = 4.5
    wb.save(p)
    out = tmp_path / "res.csv"
    code = main(["classify", str(p), "--tables", str(tabla), "-o", str(out), "--esr", "galeria=C"])
    cap = sin_fuga(capsys)
    assert code == 0
    assert "q chart (Q-NGI-2025): 1 with reference, 0 without" in cap.out and " / Q cat " in cap.out


def test_report_esr_no_leak(tmp_path, tabla, capsys):
    out = tmp_path / "i.html"
    assert main(["report", str(tramos_xlsx(tmp_path)), "--tables", str(tabla), "-o", str(out), "--no-figures",
                 "--esr", "C", "--q-edition", "Q-NGI-2015"]) == 0
    cap = sin_fuga(capsys)
    assert "q chart (Q-NGI-2015)" in cap.out


@pytest.mark.parametrize("bad", ["Z", "A:x", "=C", "galeria="])
def test_esr_bad_spec_exit_one(tmp_path, tabla, capsys, bad):
    args = ["classify", str(tramos_xlsx(tmp_path)), "--tables", str(tabla), "-o", str(tmp_path / "r.csv")]
    assert main(args + ["--esr", bad]) == 1
    err = capsys.readouterr().err
    assert err.startswith("error: ") and err.count("\n") == 1
