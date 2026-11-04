import json
import re
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


def test_qsupport_note_is_not_warning(capsys):
    assert main(QS + ["--q", "4.5", "--span", "15"]) == 0
    out = capsys.readouterr().out
    assert "note: chart bolt length is given for ESR = 1" in out and "warning:" not in out
    assert "[Q-Barton1980, Secondary]" in out


def test_no_nanobind_noise():
    r = subprocess.run([sys.executable, "-m", "rockmasspy.cli", "--help"], capture_output=True, text=True)
    assert "leaked" not in r.stderr
    r = subprocess.run([sys.executable, "-m", "rockmasspy.cli", "qsupport", "--q", "4.5", "--span", "15",
                        "--esr-category", "A"], capture_output=True, text=True)
    assert r.returncode == 1 and r.stderr.startswith("error:") and r.stderr.count(chr(10)) == 1


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


def test_classify_esr_sin_numero_dice_a_dos_puntos(tmp_path, tabla, capsys):  # M2
    args = ["classify", str(tramos_xlsx(tmp_path)), "--tables", str(tabla), "-o", str(tmp_path / "r.csv")]
    assert main(args + ["--esr", "A"]) == 1
    assert capsys.readouterr().err == "error: ESR category A covers 3-5; use A:<esr>, e.g. A:4\n"
    assert main(args + ["--esr", "galeria=b"]) == 1
    assert capsys.readouterr().err == "error: ESR category B covers 2-2.5; use B:<esr>, e.g. B:2.5\n"


def test_qsupport_paredes_categoria_7_sale_con_2(capsys):  # M4
    assert main(["qsupport", "--q", "0.12", "--span", "6", "--esr-category", "E", "--edition", "Q-NGI-2015",
                 "--wall-height", "25"]) == 2
    assert "walls category: 7" in capsys.readouterr().out


def test_qsupport_estrella_en_la_lectura_ajustada(tmp_path, monkeypatch, capsys):  # M5
    pytest.importorskip("matplotlib")
    import rockmasspy.viz as viz

    seen = {}
    real = viz.plot_q_chart
    monkeypatch.setattr(viz, "plot_q_chart", lambda *a, **k: seen.update(k) or real(*a, **k))
    main(["qsupport", "--q", "2000", "--span", "6", "--esr-category", "E", "--chart", str(tmp_path / "q.png")])
    assert seen["points"][0][0] == 1000


# --- mathews y mrmr ---

from test_stope_surfaces import CAB as SCAB, FILAS as SFILAS, csv as stope_csv  # noqa: E402

MR = ["mrmr", "--irs", "100", "--rqd", "75", "--spacing", "0.5", "1.0", "3.0", "--jc-large", "straight",
      "--jc-small", "smooth_planar", "--jc-filling", "soft_medium", "--water", "dry", "--weathering", "85",
      "--blasting", "90"]


def test_mathews_summary_files_and_no_leak(tmp_path, capsys):
    p = stope_csv(tmp_path)
    out = tmp_path / "res.csv"
    code = main(["mathews", str(p), "-o", str(out), "--report", str(tmp_path / "x.html"), "--no-figures"])
    cap = capsys.readouterr()
    assert code == 2 and "graph: Mathews-Potvin1988 [Primary]" in cap.out and "surfaces: 6" in cap.out
    assert "stable: 3" in cap.out and "transition: 1" in cap.out and "caved: 2" in cap.out
    assert "warnings: 2" in cap.out and "warning: N' below the graph (0.1): taken as caved (2)" in cap.out
    assert cap.out.rstrip().endswith("the library recommends, the engineer decides")
    assert "SECRETO-123" not in cap.out and not re.search(r"S[1-6]", cap.out + cap.err)
    assert "SECRETO-123" not in cap.err and "SECRETO-123" not in out.read_text(encoding="utf-8")
    assert "L-" not in cap.out + cap.err and "L-" not in out.read_text(encoding="utf-8")  # labor_codigo
    assert len(out.read_text(encoding="utf-8").splitlines()[0].split(",")) == 13
    assert (tmp_path / "x.html").stat().st_size > 0


def test_mathews_chart_exit_codes_and_errors(tmp_path, capsys):
    pytest.importorskip("matplotlib")
    png = tmp_path / "g.png"
    ok = stope_csv(tmp_path, [SFILAS[0], SFILAS[1], SFILAS[4]])
    assert main(["mathews", str(ok), "--chart", str(png)]) == 0 and png.stat().st_size > 0
    assert "warning:" not in capsys.readouterr().out
    bad = stope_csv(tmp_path, ["S1,10,,,,,100,20,45,,90,,130,40,,,L-1,1,SECRETO-123"], nombre="m.csv")
    assert main(["mathews", str(bad)]) == 1
    err = capsys.readouterr().err
    assert err.startswith("error: ") and err.count("\n") == 1 and "row 2" in err and "SECRETO-123" not in err


def test_mrmr_case_and_codes(capsys):
    assert main(MR + ["--orientation", "75"]) == 0
    out = capsys.readouterr().out
    assert "class 3B" in out and "class 4B" in out and "MRMR-Laubscher1990" in out
    assert out.rstrip().endswith("the library recommends, the engineer decides")
    assert main(MR + ["--orientation", "50"]) == 2
    assert "warning:" in capsys.readouterr().out


def test_mrmr_input_errors_and_hr(tmp_path, capsys):
    assert main(MR + ["--ff", "5", "--sets", "2"]) == 1
    assert capsys.readouterr().err.startswith("error: ")
    assert main(["mrmr", "--irs", "100", "--rqd", "75", "--spacing", "1", "--jc", "20", "--jc-large", "straight"]) == 1
    capsys.readouterr()
    assert main(["mrmr", "--irs", "100", "--ff", "4", "--sets", "2", "--jc", "20", "--hr", "10"]) in (0, 2)
    out = capsys.readouterr().out
    assert "Laubscher1994-stability" in out and "zone" in out
    pytest.importorskip("matplotlib")
    png = tmp_path / "m.png"
    main(["mrmr", "--irs", "100", "--ff", "4", "--sets", "2", "--jc", "20", "--hr", "10", "--chart", str(png)])
    assert png.stat().st_size > 0


def test_help_lists_new_commands(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    assert "mathews" in out and "mrmr" in out


def test_mathews_archivo_sin_caras(tmp_path, capsys):  # M4
    p = stope_csv(tmp_path, [], nombre="vacio.csv")
    assert main(["mathews", str(p), "--report", str(tmp_path / "x.html")]) == 1
    assert capsys.readouterr().err == "error: no surfaces in vacio.csv\n"


def test_mrmr_chart_sin_hr(tmp_path, capsys):  # M3
    assert main(MR + ["--chart", str(tmp_path / "g.png")]) == 1
    assert capsys.readouterr().err == "error: --chart needs --hr\n"


@pytest.mark.parametrize("col", ["q_prima", "q_edicion"])
def test_mathews_celda_mala_un_solo_error_sin_el_valor(tmp_path, capsys, col):  # I2 / Foco 5
    cab = SCAB + ",q_edicion"
    fila = ("S1,SECRETO-123,,,,,100,20,45,,90,,100,40,,,L-1,1,x,"
            if col == "q_prima" else "S2,,80,9,1.5,1,100,20,45,gravedad,0,,,,10,20,L-2,1,x,SECRETO-123")
    p = stope_csv(tmp_path, [fila], cab, nombre="m.csv")
    assert main(["mathews", str(p)]) == 1
    cap = capsys.readouterr()
    assert cap.err.startswith("error: ") and cap.err.count("error:") == 1 and cap.err.count("\n") == 1
    assert "SECRETO" not in cap.out + cap.err


# --- verify (2C, tarea 6) ---

from test_design_inputs import csv as design_csv  # noqa: E402

LEAK = "SECRETO-123"
V_EST = (["id_refugio", "tipo", "rmr", "distancia_frente_m", "area_m2", "aforo", "sostenido", "labor_codigo", "este_m",
          "observaciones"],
         [[f"R-{LEAK}", "roca", 65, 400, 30, 20, "", LEAK, 1, LEAK], ["E2", "roca", 55, 400, 30, 20, "", LEAK, 1, LEAK],
          ["E3", "roca", 70, 400, 30, 20, "", LEAK, 1, LEAK]])
V_PEA = (["id_via", "via", "geometria", "espaciado_max_m", "labor_codigo"],
         [["V1", "galeria", "", 40, LEAK], ["V2", "rampa", "curva", 25, LEAK]])
V_QC = (["periodo", "sostenimiento", "instalados", "ensayados"], [["2026-01", "I", 100, 2]])
V_FS = (["id_analisis", "plazo", "fs"], [["A1", "corto", 1.5], ["A2", "largo", 1.5]])
V_AUT = (["tipo_labor", "autosoporte_h"], [["galeria", 30]])
V_OK = (["id_refugio", "tipo", "rmr", "distancia_frente_m", "area_m2", "aforo", "sostenido"],
        [["E1", "roca", 70, 400, 30, 20, ""]])


def verify_inputs(tmp_path, tabla):
    d = tmp_path / "d"
    d.mkdir()
    files = [design_csv(d, f"{n}.csv", *h) for n, h in (
        ("Estaciones_refugio", V_EST), ("Refugios_peatonales", V_PEA), ("Resumen_QC", V_QC),
        ("Factores_seguridad", V_FS), ("Autosoporte", V_AUT))]
    tramos = tramos_xlsx(tmp_path, extra=[["TRZ-5", "galeria", LEAK, "N", 1.0, 2.0, 4.0, 70]])
    surf = stope_csv(tmp_path)
    return ["verify", "--profile", "PE-DS024-2016", "--as-of", "2026-11-02", "--tables", str(tabla), "--tramos", str(tramos),
            "--surfaces", str(surf), "--design", *map(str, files)]


def test_verify_full(tmp_path, tabla, capsys):
    args = verify_inputs(tmp_path, tabla)
    code = main(args)
    cap = capsys.readouterr()
    assert code == 2 and cap.err == ""
    lines = cap.out.splitlines()
    assert lines[0] == "profile: PE-DS024-2016 (as of 2026-11-02)" and lines[1] == "requirements: 24"
    for k in ("complies", "does not comply", "attention", "notes", "not checked", "not verifiable by the library"):
        assert any(l.startswith(f"{k}: ") for l in lines)
    assert "does not comply: Anexo 19, num. 2.1 y 2.2 (art. 151) [law] 1 of 3 " in cap.out
    assert any(l.startswith("attention: ") and "[guide]" in l for l in lines)
    assert lines[-1] == "the library verifies what it can check; it does not replace the signed study"
    full = cap.out + cap.err
    assert LEAK not in full and not re.search(r"\b(E2|E3|V1|V2|A1|A2|TRX-77|TRZ-5|S[1-6])\b", full)
    assert not re.search(r"aprob|aprueb|approv", full, re.I)


def test_verify_no_inputs(capsys):
    assert main(["verify", "--profile", "PE-DS024-2016", "--as-of", "2026-11-02"]) == 0
    out = capsys.readouterr().out
    assert "requirements: 24" in out and "not checked: 15" in out and "not verifiable by the library: 9" in out


def test_verify_compliant_design_only(tmp_path, capsys):
    p = design_csv(tmp_path, "Estaciones_refugio.csv", *V_OK)
    assert main(["verify", "--profile", "PE-DS024-2016", "--design", str(p)]) == 0
    assert "complies: " in capsys.readouterr().out


def test_verify_reports(tmp_path, tabla, capsys):
    args = verify_inputs(tmp_path, tabla)
    h = tmp_path / "x.html"
    assert main([*args, "--report", str(h)]) == 2
    assert f"report: {h}" in capsys.readouterr().out and h.stat().st_size > 0 and LEAK not in h.read_text(encoding="utf-8")
    pytest.importorskip("docx")
    w = tmp_path / "x.docx"
    assert main([*args, "--report", str(w), "--lang", "en"]) == 2 and w.stat().st_size > 0


@pytest.mark.parametrize("extra", [
    ["--profile", "ZZ"], ["--tramos", "t.xlsx"], ["--as-of", "2026-02-30"], ["--as-of", "2026-W01-1"], ["--report", "x.pdf"],
])
def test_verify_input_errors(tmp_path, capsys, extra):
    base = ["verify", "--profile", "PE-DS024-2016"]
    if extra[0] == "--profile":
        base = ["verify"]
    assert main([*base, *extra]) == 1
    cap = capsys.readouterr()
    assert cap.err.count("error:") == 1 and len(cap.err.strip().splitlines()) == 1 and "Traceback" not in cap.err
    if extra == ["--profile", "ZZ"]:
        assert "PE-DS024-2016" in cap.err


def test_verify_design_errors(tmp_path, capsys):
    for name, hoja in (("Refugios.csv", V_OK), ("Estaciones_refugio.csv", (V_OK[0], [["E1", "roca", 70, 400, 30, 2.5, ""]]))):
        p = design_csv(tmp_path, name, *hoja)
        assert main(["verify", "--profile", "PE-DS024-2016", "--design", str(p)]) == 1
        err = capsys.readouterr().err
        assert err.count("error:") == 1 and len(err.strip().splitlines()) == 1 and "2.5" not in err
    assert main(["verify", "--profile", "PE-DS024-2016", "--tramos", "t.xlsx"]) == 1
    assert "--tramos needs --tables" in capsys.readouterr().err


# --- rockmass slope ---

def slope_files(tmp_path, tf=None, jf=None):
    from test_slopes import RIQ, T, fam, tal

    return (tal(tmp_path, tf or [T(id_="T-ZZSENT", tramo="R-ZZSENT")]),
            fam(tmp_path, [r.replace("R1", "R-ZZSENT") for r in (jf or RIQ)]))


def run_slope(tmp_path, capsys, *extra, files=None):
    faces, fams = files or slope_files(tmp_path)
    code = main(["slope", "--faces", str(faces), "--families", str(fams), *extra])
    cap = capsys.readouterr()
    return code, cap.out, cap.err


def test_slope_summary_and_privacy(tmp_path, capsys):
    code, out, err = run_slope(tmp_path, capsys)
    assert code == 2 and err == ""
    for line in ("slopes: 1", "planes: 4", "intersections: 6", "planar sliding: ", "planar sliding (no lateral limits): ",
                 "wedge sliding: ", "flexural toppling: ", "direct toppling: ", "SMR discrete: I ", "SMR continuous: I ",
                 "Q-slope: 0 faces, 0 steeper than beta", "warnings: ", "notes: "):
        assert line in out
    assert out.rstrip().endswith("the library recommends, the engineer decides")
    assert "ZZSENT" not in out + err


def test_slope_quiet_slope_exits_0(tmp_path, capsys):
    from test_slopes import T

    files = slope_files(tmp_path, [T(tramo="R-ZZSENT", buz="30", dir_="180", fr="35", rmr="", exc="")], ["R-ZZSENT,J1,20,090"])
    code, out, err = run_slope(tmp_path, capsys, files=files)
    assert code == 0 and "notes: 0" in out and err == ""


def test_slope_files_and_lateral_limit(tmp_path, capsys):
    res, html, ch = tmp_path / "r.csv", tmp_path / "x.html", tmp_path / "ch"
    files = slope_files(tmp_path, jf=["R1,J1,50,160", "R1,J2,50,133", "R1,J3,60,300"])
    code, out, _ = run_slope(tmp_path, capsys, "--output", str(res), "--report", str(html), "--charts", str(ch), files=files)
    assert code == 2 and res.exists() and html.exists() and (ch / "estereograma_1_density.png").exists()
    assert f"chart: {ch / 'estereograma_1_density.png'}" in out
    text = html.read_text(encoding="utf-8")
    assert "T-ZZSENT" in text and text.count("ZZSENT") == text.count("T-ZZSENT") + text.count("R-ZZSENT")
    planar = lambda o: next(ln for ln in o.splitlines() if ln.startswith("planar sliding: "))
    assert planar(run_slope(tmp_path, capsys, "--lateral-limit", "20", files=files)[1]) != planar(out)


def test_slope_docx(tmp_path, capsys):
    pytest.importorskip("docx")
    code, out, _ = run_slope(tmp_path, capsys, "--report", str(tmp_path / "x.docx"), "--no-figures")
    assert (tmp_path / "x.docx").exists() and "report:" in out


def test_slope_note_alone_keeps_exit_0(tmp_path, capsys):
    from test_slopes import T

    files = slope_files(tmp_path, [T(tramo="R-ZZSENT", buz="30", dir_="180", rmr="", exc="")], ["R-ZZSENT,J1,20,090", "R-ZZSENT,J2,20,090"])
    code, out, _ = run_slope(tmp_path, capsys, files=files)
    assert "notes: 0" not in out and "notes: 1" in out and code == 0


@pytest.mark.parametrize("case", ["dip95", "rmr_sin_excavacion", "pdf", "missing", "lateral"])
def test_slope_input_errors(tmp_path, capsys, case):
    from test_slopes import T

    tf = {"dip95": [T(buz="95")], "rmr_sin_excavacion": [T(exc="")]}.get(case)
    files = slope_files(tmp_path, tf)
    extra = {"pdf": ["--report", "x.pdf"], "lateral": ["--lateral-limit", "95"]}.get(case, [])
    if case == "missing":
        files = (tmp_path / "no_existe.csv", files[1])
    code, out, err = run_slope(tmp_path, capsys, *extra, files=files)
    assert code == 1 and "Traceback" not in err
    assert len(err.strip().splitlines()) == 1 and err.startswith("error: ")
    assert "ZZSENT" not in out + err
    assert case != "dip95" or "95" not in err


def test_slope_empty_faces(tmp_path, capsys):
    from test_slopes import TAL_CAB

    faces = tmp_path / "vacio.csv"
    faces.write_text(TAL_CAB + "\n", encoding="utf-8")
    code, _, err = run_slope(tmp_path, capsys, files=(faces, slope_files(tmp_path)[1]))
    assert code == 1 and err.strip() == "error: no slope faces in vacio.csv"


def test_help_lists_slope(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    assert "slope" in capsys.readouterr().out


def test_slope_oblique_toppling_visible(tmp_path, capsys):
    from test_slopes import T

    files = slope_files(tmp_path, [T(tramo="R-ZZSENT", buz="80", dir_="180", rmr="", exc="")],
                        ["R-ZZSENT,J1,81,254", "R-ZZSENT,J2,79,233"])
    html, ch = tmp_path / "o.html", tmp_path / "ch"
    code, out, _ = run_slope(tmp_path, capsys, "--report", str(html), "--charts", str(ch), files=files)
    assert code == 2 and "oblique 1 of 1 intersections" in out
    assert (ch / "estereograma_1_direct_toppling.png").exists()
    text = html.read_text(encoding="utf-8")
    assert "oblicuo" in text and "0/1" in text and "1/1 (100 %)" in text
    assert "volteo directo oblicuo (1)" in text and text.count("<img") == 2
    from rockmasspy import report as rp
    from rockmasspy.slopes import assess_slopes, load_families, load_slope_faces

    (r,) = assess_slopes(load_slope_faces(files[0]), load_families(files[1]))
    fig = rp.slope_figure(r, "direct_toppling", "en")
    assert any("oblique 1 of 1" in tx.get_text() for tx in fig.texts)  # el conteo crítico incluye el oblicuo


def test_slope_warning_lines_unambiguous(tmp_path, capsys):
    from test_slopes import T

    files = slope_files(tmp_path, [T(tramo="R-ZZSENT", fr="")])
    _, out, _ = run_slope(tmp_path, capsys, files=files)
    assert "warnings: 1 in 1 slope" in out.splitlines() and "(1 slope)" in out


def test_slope_q_warning_without_cell_value(tmp_path, capsys):
    from test_slopes import T

    tf = [T(id_="T1", tramo="R-ZZSENT", q="80,27.3,1.5,1,0.75,0.7", srf="2.5,,"),
          T(id_="T2", tramo="R-ZZSENT", q="80,31.7,1.5,1,0.75,0.7", srf="2.5,,")]
    code, out, err = run_slope(tmp_path, capsys, files=slope_files(tmp_path, tf))
    assert code == 2 and "27.3" not in out + err and "31.7" not in out + err
    assert [ln for ln in out.splitlines() if "jn outside" in ln] == [
        "warning: jn outside the table range [0.5, 20] (2 slopes)"]


def test_slope_kinematics_count_says_what_it_counts(tmp_path, capsys):
    from test_slopes import T

    tf = [T(id_="T1", tramo="R-ZZSENT"), T(id_="T2", tramo="R-ZZSENT", fr="")]
    _, out, _ = run_slope(tmp_path, capsys, files=slope_files(tmp_path, tf))
    assert "kinematics run on 1 of 2 slopes; planes: 4" in out.splitlines()


# --- rockmass slope --blocks ---

def block_files(tmp_path, jf, tf, bf, df=()):
    import test_blocks as tb
    from test_slopes import fam, tal

    out = [tal(tmp_path, tf), fam(tmp_path, jf), tb.blq(tmp_path, bf)]
    return out + ([tb.dis(tmp_path, df)] if df else [])


def run_blocks(capsys, files, *extra):
    faces, fams, blocks, *dists = files
    args = ["slope", "--faces", str(faces), "--families", str(fams), "--blocks", str(blocks)]
    code = main(args + (["--distributions", str(dists[0])] if dists else []) + [str(e) for e in extra])
    cap = capsys.readouterr()
    return code, cap.out, cap.err


def todas_files(tmp_path):
    import test_blocks as tb

    return block_files(tmp_path, *tb._todas(tmp_path))


def test_slope_blocks_summary(tmp_path, capsys):
    code, out, err = run_blocks(capsys, todas_files(tmp_path), "--iterations", 2000, "--seed", 3)
    lines = out.splitlines()
    assert code == 2 and err == ""  # PL-1 tiene FS < 1
    for ln in ("blocks: 5 (planar 2, wedge 1, toppling 1, berm 1)", "blocks formed: 4 of 4",
               "FS at or below 1: 1 of 4 blocks with FS", "probabilistic: 1 block, 2000 iterations, lhs, seed 3",
               "PoF above 0: 1 of 1 block", "berms narrower than required: 1 of 1", "berm reliability evaluated: 1",
               "warnings: 3 in 3 slopes and 0 blocks"):
        assert ln in lines, ln
    assert lines.index("Q-slope: 0 faces, 0 steeper than beta") < lines.index(
        "blocks: 5 (planar 2, wedge 1, toppling 1, berm 1)")
    assert out.rstrip().endswith("the library recommends, the engineer decides")


def quiet_prob_files(tmp_path):
    import test_blocks as tb

    return block_files(tmp_path, tb.J35, [tb.talud(fr="40")], [tb.B(**tb.SMP)], tb.SMP_D)


def test_slope_blocks_pof_does_not_trigger(tmp_path, capsys):
    import test_blocks as tb

    res = tmp_path / "res.csv"
    code, out, _ = run_blocks(capsys, quiet_prob_files(tmp_path), "--iterations", 2000, "--blocks-output", res)
    assert "FS at or below 1: 0 of 1 blocks with FS" in out and "PoF above 0: 1 of 1 block" in out.splitlines()
    assert code == 0  # la PoF no pide atención (R14)
    cab, (f,) = tb.leer(res)
    assert len(cab) == 25 and float(f["pof_pct"]) > 0 and f"blocks results: {res}" in out


def test_slope_blocks_files_charts_report(tmp_path, capsys):
    from rockmasspy.report.texts import t

    res, ch, html = tmp_path / "r.csv", tmp_path / "ch", tmp_path / "x.html"
    code, out, _ = run_blocks(capsys, todas_files(tmp_path), "--iterations", 200, "--blocks-output", res,
                              "--charts", ch, "--report", html)
    assert code == 2 and res.exists()
    for name in ("fs_hist_5.png", "fs_cdf_5.png"):
        assert (ch / name).exists() and f"chart: {ch / name}" in out
    assert not list(ch.glob("fs_*_[1-4].png"))
    text = html.read_text(encoding="utf-8")
    assert t("cap_blocks", "es") in text and t("cap_prob", "es") in text


def test_slope_blocks_same_seed_same_output(tmp_path, capsys):
    import test_blocks as tb

    files = quiet_prob_files(tmp_path)
    res = tmp_path / "r.csv"
    a = run_blocks(capsys, files, "--iterations", 2000, "--blocks-output", res)
    (fa,) = tb.leer(res)[1]
    b = run_blocks(capsys, files, "--iterations", 2000, "--blocks-output", res)
    (fb,) = tb.leer(res)[1]
    assert a == b and fa == fb
    c = run_blocks(capsys, files, "--iterations", 2000, "--blocks-output", res, "--sampling", "monte-carlo")
    (fc,) = tb.leer(res)[1]
    assert "monte-carlo" in c[1] and fc["muestreo"] == "monte_carlo" and fc["pof_pct"] != fa["pof_pct"]


def test_slope_blocks_note_alone_keeps_code(tmp_path, capsys):
    import test_blocks as tb

    files = block_files(tmp_path, ["R1,J1,50,180"], [tb.talud(fr="60")], [tb.B(**tb.PL1)])  # no formado
    code, out, _ = run_blocks(capsys, files)
    assert code == 0 and "blocks formed: 0 of 1" in out and "notes: 1" in out


def _fake_block(fs, warnings=(), notes=()):
    from types import SimpleNamespace

    from rockmasspy import blocks as bk

    det = None if fs is None else SimpleNamespace(factor_of_safety=fs, formed=True)
    return bk.BlockResult("B", "T1", 1, "planar", det, None, None, None, tuple(warnings), tuple(notes), ())


def test_slope_blocks_count_parity(tmp_path, capsys, monkeypatch):
    import test_blocks as tb
    from rockmasspy import blocks as bk
    from rockmasspy.report.texts import t

    fakes = [_fake_block(x) for x in (0.5, 1.0, 1 + 1e-12, 1.2)]
    monkeypatch.setattr(bk, "assess_blocks", lambda *a, **k: fakes)
    files = block_files(tmp_path, tb.J35, [tb.talud(fr="40")], [tb.B(**tb.PL1)])
    res, html = tmp_path / "p.csv", tmp_path / "p.html"
    code, out, _ = run_blocks(capsys, files, "--blocks-output", res, "--report", html, "--no-figures")
    k = bk.block_counts(fakes)["fs_below_1"]
    assert f"FS at or below 1: {k} of 4 blocks with FS" in out.splitlines() and k == 3 and code == 2
    _, filas = tb.leer(res)
    assert sum(f["fs_menor_o_igual_1"] == "si" for f in filas) == k
    tabla = html.read_text(encoding="utf-8").split(t("cap_blocks", "es"))[1].split("</table>")[0]
    assert tabla.count(f"<td>{t('sl_yes', 'es')}</td>") == k


@pytest.mark.parametrize("case", ["fs", "warning", "slope", "note", "quiet"])
def test_slope_blocks_attention_parity(tmp_path, capsys, monkeypatch, case):
    import test_blocks as tb
    from rockmasspy import blocks as bk

    r = {"fs": _fake_block(0.9), "warning": _fake_block(1.5, warnings=("w",)), "slope": _fake_block(1.5),
         "note": _fake_block(1.5, notes=("n",)), "quiet": _fake_block(1.5)}[case]
    monkeypatch.setattr(bk, "assess_blocks", lambda *a, **k: [r])
    tf = [tb.talud(fr="" if case == "slope" else "40")]  # sin fricción: aviso del talud
    html = tmp_path / "a.html"
    code, _, _ = run_blocks(capsys, block_files(tmp_path, tb.J35, tf, [tb.B(**tb.PL1)]), "--report", html,
                            "--no-figures")
    att = "piden atención" in html.read_text(encoding="utf-8")
    assert (code == 2) == att == (case in ("fs", "warning", "slope"))


@pytest.mark.parametrize("case", ["modelo", "dist_sin_blocks", "iter0", "seed", "familia", "media", "muestreada",
                                  "output_sin_blocks", "sampling_sin_blocks"])
def test_slope_blocks_input_errors(tmp_path, capsys, case):
    import test_blocks as tb

    bf, df, extra = [tb.B(**tb.PL1)], (), []
    if case == "modelo":
        bf = [tb.B(**{**tb.PL1, "modelo": "losa"})]
    elif case == "familia":
        bf = [tb.B(**{**tb.PL1, "familia_1": "J9"})]
    elif case == "media":
        df = [tb.D("B1", "kh", "normal", 0.5, 0.01, 0, 0.1)]
    elif case == "muestreada":
        bf = [tb.B(**{**tb.PL1, "dist_grieta_m": 15})]
        df = [tb.D("B1", "buz_plano_grados", "uniforme", "", "", 20, 45)]
    elif case == "iter0":
        extra = ["--iterations", "0"]
    elif case == "seed":
        extra = ["--seed", "-1"]
    files = block_files(tmp_path, tb.J35, [tb.talud()], bf, df)
    if case.endswith("_sin_blocks"):
        d = tb.dis(tmp_path, [tb.D("B1", "kh", "uniforme", "", "", 0, 0.1)])
        flag = {"dist_sin_blocks": ["--distributions", str(d)], "output_sin_blocks": ["--blocks-output", "x.csv"],
                "sampling_sin_blocks": ["--sampling", "lhs"]}[case]
        code = main(["slope", "--faces", str(files[0]), "--families", str(files[1]), *flag])
        cap = capsys.readouterr()
        out, err = cap.out, cap.err
    else:
        code, out, err = run_blocks(capsys, files, *extra)
    assert code == 1 and "Traceback" not in err, err
    assert len(err.strip().splitlines()) == 1 and err.startswith("error: "), err
    assert "Domain error" not in err and "Received" not in err and "losa" not in err and "J9" not in err
    assert case != "media" or ("0.5" not in err and "0.01" not in err)
    assert case != "muestreada" or "during sampling" in err
    assert case != "iter0" or "--iterations" in err


def test_slope_blocks_privacy(tmp_path, capsys):
    docx = pytest.importorskip("docx")
    import test_blocks as tb

    jf = ["R-ZZSENT,J1,35,180"] * 3
    tf = [tb.talud("T-ZZSENT", "R-ZZSENT")]
    bf = [tb.B(**{**tb.SMP, "id_bloque": "B-ZZSENT", "id_talud": "T-ZZSENT"}),
          tb.B(**{**tb.PL1, "id_bloque": "B2-ZZSENT", "id_talud": "T-ZZSENT", "retroanalisis": "si"})]
    df = [tb.D("B-ZZSENT", "friccion_1_grados", "normal", 35, 5, 15, 70)]
    files = block_files(tmp_path, jf, tf, bf, df)
    html, word, ch = tmp_path / "x.html", tmp_path / "x.docx", tmp_path / "ch"
    code, out, err = run_blocks(capsys, files, "--iterations", 200, "--report", html, "--charts", ch)
    assert code == 2 and "ZZSENT" not in out + err
    code, out, err = run_blocks(capsys, files, "--iterations", 200, "--report", word)
    assert "ZZSENT" not in out + err
    d = docx.Document(str(word))
    wtext = "\n".join([p.text for p in d.paragraphs] + [c.text for x in d.tables for row in x.rows for c in row.cells])
    for txt in (html.read_text(encoding="utf-8"), wtext):
        assert "B-ZZSENT" in txt and "T-ZZSENT" in txt
        assert len(re.findall("ZZSENT", txt)) == len(re.findall(r"(?:B2?|T|R)-ZZSENT", txt))


def test_help_lists_block_options(capsys):
    with pytest.raises(SystemExit):
        main(["slope", "--help"])
    out = capsys.readouterr().out
    for opt in ("--blocks", "--sheet-blocks", "--distributions", "--sheet-distributions", "--iterations", "--sampling",
                "--seed", "--blocks-output", "monte-carlo"):
        assert opt in out


# --- ola final de la 3B ---

def test_slope_blocks_constant_fs_no_traceback(tmp_path, capsys):
    # c = 0 y seco: el FS no depende de gamma; sin traceback y con el código de la regla del FS (I1)
    import test_blocks as tb

    fila = dict(id_bloque="B1", id_talud="T1", modelo="planar", altura_m=20, peso_unitario_kn_m3=26,
                familia_1="J1", cohesion_1_kpa=0, friccion_1_grados=40)
    files = block_files(tmp_path, tb.J35, [tb.talud(fr="40")], [tb.B(**fila)],
                        [tb.D("B1", "peso_unitario_kn_m3", "normal", 26, 1, 22, 30)])
    code, out, err = run_blocks(capsys, files, "--iterations", 500)
    assert code == 0 and err == "" and "FS at or below 1: 0 of 1 blocks with FS" in out


def test_slope_blocks_error_prints_nothing_to_stdout(tmp_path, capsys):
    import test_blocks as tb

    files = block_files(tmp_path, tb.J35, [tb.talud()], [tb.B(**{**tb.VO1, "n_bloques": 3e9})])
    code, out, err = run_blocks(capsys, files)
    assert code == 1 and out == "" and err == "error: sheet 'Bloques', row 2, column 'n_bloques': out of range\n"


def test_slope_blocks_output_extension_checked_first(tmp_path, capsys):
    code = main(["slope", "--faces", str(tmp_path / "no.csv"), "--families", str(tmp_path / "no2.csv"),
                 "--blocks", str(tmp_path / "no3.csv"), "--blocks-output", str(tmp_path / "r.txt")])
    cap = capsys.readouterr()
    assert code == 1 and cap.out == "" and cap.err == "error: --blocks-output must end in .csv or .xlsx\n"


def test_slope_blocks_warnings_grouped(tmp_path, capsys):
    import test_blocks as tb

    v = {**tb.VO1, "soporte_kn_m": "", "buz_base_grados": 60}
    bf = [tb.B(**v), tb.B(**{**v, "id_bloque": "V2", "n_bloques": 14})]  # 15 y 13 bloques fallan (8)-(9)
    code, out, _ = run_blocks(capsys, block_files(tmp_path, tb.J35, [tb.talud(fr="40")], bf))
    lines = out.splitlines()
    assert code == 2
    assert "warning: Goodman-Bray conditions (8)-(9) fail in N blocks (2 blocks)" in lines
    assert ("warning: toppling: support is insufficient for any friction coefficient below 1; FS is an upper bound "
            "(2 blocks)") in lines
    assert not any(ln.endswith("(1 block)") for ln in lines)


# --- rockmass le (3C) ---

def le_files(tmp_path, data=None):
    import test_limit_equilibrium as tl

    return tl.hojas(tmp_path, data or tl.merge(tl.fk_data(), tl.acads3b_data(registro="R-ZZSENT", kh=0.05),
                                                {"Sismos": tl.seno()}))


def run_le(capsys, files, *extra):
    args = ["le"]
    if isinstance(files, dict):
        for flag, sheet in (("--geometry", "Geometria"), ("--layers", "Estratos"), ("--materials", "Materiales_LE"),
                            ("--analyses", "Analisis_LE"), ("--records", "Sismos")):
            if sheet in files:
                args += [flag, str(files[sheet])]
    else:
        args += ["--workbook", str(files)]
    code = main([*args, *map(str, extra)])
    cap = capsys.readouterr()
    return code, cap.out, cap.err


_PROGRESS_2 = "analysis 1 of 2...\nanalysis 2 of 2...\n"


def clean_err(err):
    """En éxito, stderr lleva a lo más el avance de `rockmass le` (con más de un análisis): sin `error:` ni traceback."""
    return "error:" not in err and "Traceback" not in err


def fk_kh(kh):
    import test_limit_equilibrium as tl

    d = tl.fk_data()  # sin círculo fijo en la hoja: búsqueda con una malla pequeña alrededor de (120, 90), base 10
    d["Analisis_LE"] = [tl.ana(id_analisis="AFK-ZZSENT", id_seccion="SFK-ZZSENT", metodos="bishop;spencer",
                               superficie="circular", malla_x_min=110, malla_x_max=130, malla_y_min=80,
                               malla_y_max=100, base_modelo_m=10, kh=kh)]
    return d


def test_le_summary_and_privacy(tmp_path, capsys):
    code, out, err = run_le(capsys, le_files(tmp_path))
    lines = out.splitlines()
    assert code == 0 and clean_err(err) and err == _PROGRESS_2  # avance en stderr, sin ids
    for ln in ("analyses: 2 (circular 1, block 0, given 1)", "FS at or below 1: 0 of 2", "Newmark: 1 analysis",
               "warnings: 0 in 0 analyses"):
        assert ln in lines
    low = next(ln for ln in lines if ln.startswith("lowest FS: "))
    assert re.fullmatch(r"lowest FS: \d\.\d{3} \([A-Za-z-]+\)", low)
    assert out.rstrip().endswith("the library recommends, the engineer decides")
    assert "ZZSENT" not in out + err


def test_le_fk_dry_exits_0_and_kh_half_exits_2(tmp_path, capsys):
    from rockmasspy import limit_equilibrium as le

    (tmp_path / "seco").mkdir()
    code, out, _ = run_le(capsys, le_files(tmp_path / "seco", fk_kh("")))
    assert code == 0 and "FS at or below 1: 0 of 1" in out.splitlines()
    files = le_files(tmp_path, fk_kh(0.5))
    code, out, _ = run_le(capsys, files)
    (r,) = le.assess_le(files)
    assert r.fs_min < 1 and code == 2  # F&K con kh = 0.5: FS 0.83 (Bishop)
    assert "FS at or below 1: 1 of 1" in out.splitlines()
    assert f"lowest FS: {r.fs_min:.3f} (Bishop-Simplified)" in out.splitlines()


def test_le_workbook_same_as_csv(tmp_path, capsys):
    import test_limit_equilibrium as tl

    data = tl.merge(tl.fk_data(), tl.acads3b_data(registro="R-ZZSENT", kh=0.05), {"Sismos": tl.seno()})
    a = run_le(capsys, le_files(tmp_path, data))
    b = run_le(capsys, tl.libro(tmp_path, data))
    assert a == b


def test_le_files_charts_report(tmp_path, capsys):
    from rockmasspy.report.texts import t

    res, html, ch = tmp_path / "r.csv", tmp_path / "x.html", tmp_path / "ch"
    code, out, err = run_le(capsys, le_files(tmp_path), "--output", res, "--report", html, "--charts", ch)
    assert code == 0 and clean_err(err) and "ZZSENT" not in out + err
    for p in (res, html, ch / "seccion_le_1.png", ch / "seccion_le_2.png", ch / "newmark_2.png"):
        assert p.exists(), p
    assert f"chart: {ch / 'newmark_2.png'}" in out and f"results: {res}" in out and f"report: {html}" in out
    txt = html.read_text(encoding="utf-8")
    assert t("cap_le", "es") in txt and t("sl_no_slopes", "es") in txt
    assert f"<title>{t('slope_title_le', 'es')}</title>" in txt and t("slope_title", "es") not in txt
    assert len(re.findall("ZZSENT", txt)) == len(re.findall(r"<td>[AS](?:FK|3B)-ZZSENT</td>", txt)) > 0


def test_le_docx(tmp_path, capsys):
    pytest.importorskip("docx")
    code, out, _ = run_le(capsys, le_files(tmp_path), "--report", tmp_path / "x.docx", "--no-figures",
                          "--lang", "en")
    assert code == 0 and (tmp_path / "x.docx").exists() and "report:" in out


def _fake_le(fs, warnings=(), order=1):
    from types import SimpleNamespace

    import rockmasspy as rmp
    from rockmasspy import limit_equilibrium as le

    res = SimpleNamespace(factor_of_safety=fs, method=rmp.LeMethod.Bishop, lambda_=None, converged=fs is not None,
                          info=SimpleNamespace(method_id="Bishop-Simplified"))
    return le.LeAnalysisResult("A", "S", order, "given", (res,), None, None, None, tuple(warnings), (), ())


def test_le_count_parity(tmp_path, capsys, monkeypatch):
    import test_limit_equilibrium as tl
    from rockmasspy import limit_equilibrium as le
    from rockmasspy.report.texts import t

    fakes = [_fake_le(x, order=i) for i, x in enumerate((0.5, 1.0, 1 + 1e-12, 1.2), 1)]
    monkeypatch.setattr(le, "assess_le", lambda *a, **k: fakes)
    res, html = tmp_path / "p.csv", tmp_path / "p.html"
    code, out, _ = run_le(capsys, le_files(tmp_path), "--output", res, "--report", html, "--no-figures")
    k = le.le_counts(fakes)["fs_below_1"]
    assert f"FS at or below 1: {k} of 4" in out.splitlines() and k == 3 and code == 2
    assert "lowest FS: 0.500 (Bishop-Simplified)" in out.splitlines()
    _, filas = tl.leer(res)
    assert sum(f["fs_menor_o_igual_1"] == "si" for f in filas) == k
    tabla = html.read_text(encoding="utf-8").split(t("cap_le", "es"))[1].split("</table>")[0]
    assert tabla.count(f"<td>{t('sl_yes', 'es')}</td>") == k


def test_le_warnings_grouped_and_attention(tmp_path, capsys, monkeypatch):
    from rockmasspy import limit_equilibrium as le

    w = "bishop: m-alpha below 0.2 in {} slices: results may be unreliable"
    fakes = [_fake_le(1.5, (w.format(3),)),
             _fake_le(1.5, (w.format(5), "critical centre on the edge of the search grid"))]
    monkeypatch.setattr(le, "assess_le", lambda *a, **k: fakes)
    code, out, _ = run_le(capsys, le_files(tmp_path))
    lines = out.splitlines()
    assert code == 2 and "FS at or below 1: 0 of 2" in lines and "warnings: 3 in 2 analyses" in lines
    assert f"warning: {w.format('N')} (2 analyses)" in lines
    assert "warning: critical centre on the edge of the search grid (1 analysis)" in lines


@pytest.mark.parametrize("case", ["material", "metodos", "x_creciente", "nan", "workbook_y_csv", "falta_analyses",
                                  "sin_fuente", "report_pdf", "output_txt", "records_con_workbook", "no_existe"])
def test_le_input_errors(tmp_path, capsys, case):
    import test_limit_equilibrium as tl

    d = tl.fk_data()
    if case == "material":
        d["Estratos"] = [tl.L("SFK-ZZSENT", 1, "MX-ZZSENT")]
    elif case == "metodos":
        d["Analisis_LE"] = [d["Analisis_LE"][0].replace("bishop;spencer", "bishop;zzraro")]
    elif case == "x_creciente":
        d["Geometria"] = tl.G("SFK-ZZSENT", "superficie", [(0, 60), (60, 60), (50, 20), (180, 20)])
    elif case == "nan":
        d["Geometria"] = tl.G("SFK-ZZSENT", "superficie", [(0, 60), ("nan", 60), (140, 20), (180, 20)])
    files = le_files(tmp_path, d)
    extra = {"report_pdf": ["--report", "x.pdf"], "output_txt": ["--output", "x.txt"]}.get(case, [])
    if case == "workbook_y_csv":
        extra = ["--workbook", tmp_path / "x.xlsx"]
    elif case == "falta_analyses":
        files = {k: v for k, v in files.items() if k != "Analisis_LE"}
    elif case == "sin_fuente":
        files = {}
    elif case == "records_con_workbook":
        files, extra = tmp_path / "x.xlsx", ["--records", tmp_path / "s.csv"]
    elif case == "no_existe":
        files = tmp_path / "no_existe.xlsx"
    code, out, err = run_le(capsys, files, *extra)
    assert code == 1 and out == "" and "Traceback" not in err, err
    assert len(err.strip().splitlines()) == 1 and err.startswith("error: "), err
    assert "ZZSENT" not in err and "zzraro" not in err and "Domain error" not in err
    if case in ("material", "metodos", "x_creciente"):
        assert "sheet '" in err and "row " in err and "column '" in err


def test_help_lists_le_options(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    assert "le" in capsys.readouterr().out.split()
    with pytest.raises(SystemExit):
        main(["le", "--help"])
    out = capsys.readouterr().out
    for opt in ("--workbook", "--geometry", "--layers", "--materials", "--analyses", "--records", "--output",
                "--report", "--charts", "--lang", "--title", "--author", "--no-figures"):
        assert opt in out


def test_le_one_analysis_no_progress(tmp_path, capsys):
    code, _, err = run_le(capsys, le_files(tmp_path, fk_kh("")))
    assert code == 0 and err == ""


@pytest.mark.parametrize("case", ["base_dada", "base_circular", "sin_records"])
def test_le_base_and_records_errors(tmp_path, capsys, case):
    import test_limit_equilibrium as tl

    if case == "sin_records":
        files = le_files(tmp_path, tl.acads3b_data(registro="R-ZZSENT"))
        files.pop("Sismos", None)
        want = ("error: sheet 'Analisis_LE', row 2, column 'registro': no accelerogram given "
                "(use --records or a Sismos sheet)\n")
    else:
        d = tl.fk_data()
        an = dict(id_analisis="AFK-ZZSENT", id_seccion="SFK-ZZSENT", metodos="bishop", base_modelo_m=70.25)
        if case == "base_dada":
            d["Geometria"] += tl.G("SFK-ZZSENT", "ZZSENTLg", [(40, 60), (90, 32), (130, 22), (150, 20)])
            an.update(superficie="dada", linea_superficie="ZZSENTLg")
        else:
            an.update(superficie="circular", malla_x_min=110, malla_x_max=130, malla_y_min=80, malla_y_max=100)
        d["Analisis_LE"] = [tl.ana(**an)]
        files = le_files(tmp_path, d)
        want = "error: sheet 'Analisis_LE', row 2, column 'base_modelo_m': must be below the ground surface\n"
    code, out, err = run_le(capsys, files)
    assert code == 1 and out == "" and err == want
