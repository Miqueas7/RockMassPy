import json
import shutil
import subprocess
import sys

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
    exe = shutil.which("rockmass", path=str(__import__("pathlib").Path(sys.executable).parent))
    if exe:
        assert subprocess.run([exe, "--help"], capture_output=True).returncode == 0
