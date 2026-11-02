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
    ["--profile", "ZZ"], ["--tramos", "t.xlsx"], ["--as-of", "2026-02-30"], ["--report", "x.pdf"],
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
