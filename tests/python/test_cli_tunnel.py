import pytest

from rockmasspy.cli import main

# Ejemplo 1 de RocSupport (RST): HB, perno de 34 mm cada 1 m, Chern 1998, modo rocsupport3
RST1 = ["tunnel", "--radius", "6", "--p0", "1.62", "--nu", "0.3", "--criterion", "HB", "--sigci", "7", "--gsi", "15",
        "--mi", "10", "--d", "0", "--support", "34 mm rockbolt:1.0", "--eps-sm", "0.002", "--install-distance", "3",
        "--ldp", "CHERN1998", "--combination", "rocsupport3"]


def test_rst1_summary(capsys):
    assert main(RST1) == 0
    out = capsys.readouterr().out
    assert "FS 1.84" in out and "squeezing: B" in out and "GRC-HB-equivalent-MC" in out


def test_k_ratio_warns_exit_2(capsys):
    assert main(RST1 + ["--k-ratio", "0.5"]) == 2
    assert "warning: analytical GRC assumes a hydrostatic field (K = 1)" in capsys.readouterr().out


def test_mc_without_c_is_input_error(capsys):
    argv = ["tunnel", "--radius", "6", "--p0", "1.62", "--nu", "0.3", "--criterion", "MC", "--phi", "30", "--e", "5000"]
    assert main(argv) == 1
    cap = capsys.readouterr()
    assert cap.out == "" and cap.err.startswith("error: ") and cap.err.count("\n") == 1


def test_unknown_support_is_input_error(capsys):
    assert main(RST1[:RST1.index("--support")] + ["--support", "nope:1"] + RST1[RST1.index("--eps-sm"):]) == 1
    cap = capsys.readouterr()
    assert cap.out == "" and cap.err.startswith("error: ")


def test_chart_and_report(tmp_path, capsys):
    pytest.importorskip("matplotlib")
    png, html = tmp_path / "t.png", tmp_path / "t.html"
    assert main(RST1 + ["--chart", str(png), "--report", str(html), "--lang", "en"]) == 0
    assert png.stat().st_size > 0 and "data:image/png" in html.read_text(encoding="utf-8")


def test_capacity_sheet(tmp_path, capsys):
    csv = tmp_path / "cap.csv"
    csv.write_text("codigo,tipo,psm_mpa,eps_sm\nB1,bolt,0.354,0.002\n", encoding="utf-8")
    argv = RST1[:RST1.index("--support")] + ["--capacity", str(csv), "--support-code", "B1"] + \
        RST1[RST1.index("--install-distance"):]
    assert main(argv) == 0 and "FS 1.84" in capsys.readouterr().out


def test_diameter_changes_fs(capsys):
    base = RST1[:RST1.index("--support")] + ["--support", "Concrete or shotcrete lining 50 mm 28 days 35 MPa",
                                            "--install-distance", "3"]
    main(base)
    a = capsys.readouterr().out
    main(base + ["--diameter", "10"])
    assert capsys.readouterr().out.split("FS ")[1][:4] != a.split("FS ")[1][:4]


def test_eps_sm_only_for_items_without_published_value(capsys):
    base = RST1[:RST1.index("--support")] + ["--support", "Concrete or shotcrete lining 50 mm 28 days 35 MPa",
                                            "--install-distance", "3"]
    main(base)
    a = capsys.readouterr().out
    main(base + ["--eps-sm", "0.005"])  # el shotcrete de 50 mm a 28 días conserva su εsm publicada (0.001)
    assert capsys.readouterr().out.split("FS ")[1][:4] == a.split("FS ")[1][:4]
    bolt = RST1[:RST1.index("--support")] + ["--support", "25 mm rockbolt:1.0", "--install-distance", "3"]
    assert main(bolt) == 1 and "eps_sm" in capsys.readouterr().err  # sin εsm publicada: --eps-sm sí hace falta
    assert main(bolt + ["--eps-sm", "0.002"]) in (0, 2) and "FS " in capsys.readouterr().out


def test_input_errors_do_not_repeat_values(capsys):
    argv = RST1[:RST1.index("--gsi")] + ["--gsi", "777.7"] + RST1[RST1.index("--mi"):]
    assert main(argv) == 1
    err = capsys.readouterr().err
    assert err.startswith("error: ") and "gsi" in err and "777.7" not in err


def test_phi_90_is_input_error(capsys):
    argv = ["tunnel", "--radius", "3", "--p0", "10", "--nu", "0.3", "--criterion", "MC", "--e", "2000", "--c", "0.5",
            "--phi", "90"]
    assert main(argv) == 1
    cap = capsys.readouterr()
    assert cap.err.startswith("error: ") and "phi_deg" in cap.err and "Traceback" not in cap.err
