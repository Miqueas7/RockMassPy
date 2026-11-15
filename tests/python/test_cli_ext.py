"""CLI `rockmass ext` (Fase 8A, Tarea 4)."""
import pytest

from rockmasspy.cli import main
from rockmasspy.criteria import _threshold
from rockmasspy.normative import get_profile

RS = get_profile("READ-STACEY-2009")
FS_REQ = _threshold(RS.version("RS-FS-global-alta", "2026-11-14"), RS.range_policy)[0]
S = "ZZSENT"
A = f"A-{S}"
HEAD = "programa,version,modelo,escenario,tipo_objeto,id,magnitud,metodo,valor,escala,consecuencia"


def _csv(tmp_path, rows, name="r.csv"):
    p = tmp_path / name
    p.write_text(HEAD + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
    return str(p)


def _srf(v, oid=A):
    return f"RS2,2025,M1,est,section,{oid},srf,,{v},global,alta"


def test_ext_srf_in_band_exits_2_with_counts(tmp_path, capsys):
    p = _csv(tmp_path, [_srf(FS_REQ)])
    assert main(["ext", "--results", p, "--criteria", "READ-STACEY-2009"]) == 2
    out = capsys.readouterr().out
    assert "records: 1" in out and "meets: 1" in out and "objects needing attention: 1" in out


def test_ext_accept_far_from_threshold_exits_0(tmp_path, capsys):
    p = _csv(tmp_path, [_srf(FS_REQ + 0.5)])
    assert main(["ext", "--results", p, "--criteria", "READ-STACEY-2009", "--ssr-policy", "accept"]) == 0
    assert "objects needing attention: 0" in capsys.readouterr().out


def test_cli_ext_no_ids_in_output(tmp_path, capsys):
    p = _csv(tmp_path, [_srf(FS_REQ), f"Slide2,9,M1,est,section,{A},fs,bishop,{FS_REQ + 0.6},global,alta"])
    out_csv = tmp_path / "o.csv"
    crit = tmp_path / "c.csv"
    rep = tmp_path / "r.html"
    assert main(["ext", "--results", p, "--criteria", "READ-STACEY-2009", "--output", str(out_csv),
                 "--criteria-output", str(crit), "--report", str(rep)]) == 2
    cap = capsys.readouterr()
    assert S not in cap.out and S not in cap.err
    assert S in out_csv.read_text(encoding="utf-8") and S in crit.read_text(encoding="utf-8")


def test_ext_map_and_defaults(tmp_path, capsys):
    p = tmp_path / "m.csv"
    p.write_text(f"id,fs\n{A},1.9\n", encoding="utf-8")
    assert main(["ext", "--results", str(p), "--map", "fs=fs", "--program", "Slide2", "--version", "9"]) == 0
    p.write_text(f"id,FoS\n{A},1.9\n", encoding="utf-8")
    assert main(["ext", "--results", str(p), "--map", "FoS=fs"]) == 0
    assert "records: 1" in capsys.readouterr().out


@pytest.mark.parametrize("bad", ["FoS", "=fs", "FoS="])
def test_ext_bad_map_is_input_error(tmp_path, capsys, bad):
    p = _csv(tmp_path, [_srf(1.8)])
    assert main(["ext", "--results", p, "--map", bad]) == 1
    cap = capsys.readouterr()
    assert cap.out == "" and cap.err.startswith("error: ") and cap.err.count("\n") == 1


def test_ext_missing_file_and_criteria_flags(tmp_path, capsys):
    assert main(["ext", "--results", str(tmp_path / "no.csv")]) == 1
    p = _csv(tmp_path, [_srf(1.8)])
    assert main(["ext", "--results", p, "--ssr-policy", "accept"]) == 1  # sin --criteria no hay política que aplicar
    assert capsys.readouterr().out == ""


ROC = """Material,UCS (MPa),GSI,mi,mb,s,a,Erm (MPa),Poisson's ratio,Unit Weight (MN/m3)
SPP,45,53,21.22,3.961,0.0054,0.505,11920,0.25,{g}
"""


def test_ext_rocdata_gamma_warns(tmp_path, capsys):
    p = _csv(tmp_path, [_srf(2.5)])
    ok = tmp_path / "ok.csv"
    ok.write_text(ROC.format(g="0.027"), encoding="utf-8")
    assert main(["ext", "--results", p, "--rocdata", str(ok)]) == 0
    bad = tmp_path / "bad.csv"
    bad.write_text(ROC.format(g="0.042"), encoding="utf-8")
    assert main(["ext", "--results", p, "--rocdata", str(bad)]) == 2
    assert "unit weight outside the usual range; check units" in capsys.readouterr().out


def test_ext_method_spread_and_monitoring(tmp_path, capsys):
    p = _csv(tmp_path, [f"Slide2,9,M1,est,section,{A},fs,bishop,1.5,global,alta",
                        f"Slide2,9,M1,est,section,{A},fs,spencer,2.0,global,alta",
                        f"FLAC3D,7,M1,est,tunnel,{A},convergence_pct,,0.5,,"])
    assert main(["ext", "--results", p]) == 2
    out = capsys.readouterr().out
    assert "methods differ by more than 10 %" in out and S not in out
    meas = _csv(tmp_path, [f"x,1,M1,est,tunnel,{A},convergence_pct,,2.0,,"], "mon.csv")
    q = _csv(tmp_path, [f"FLAC3D,7,M1,est,tunnel,{A},convergence_pct,,0.5,,"], "q.csv")
    assert main(["ext", "--results", q, "--monitoring", meas]) == 2
    assert "measured exceeds model by more than 50 %" in capsys.readouterr().out


@pytest.mark.parametrize("lang", ["es", "en"])
@pytest.mark.parametrize("ext", ["html", "docx"])
def test_ext_report_files(tmp_path, capsys, lang, ext):
    if ext == "docx":
        pytest.importorskip("docx")
    p = _csv(tmp_path, [_srf(FS_REQ)])
    out = tmp_path / f"o.{ext}"
    assert main(["ext", "--results", p, "--criteria", "READ-STACEY-2009", "--report", str(out), "--lang", lang]) == 2
    assert out.exists()
    if ext == "html":
        txt = out.read_text(encoding="utf-8")
        assert f'lang="{lang}"' in txt
        if lang == "en":
            assert "Criterios" not in txt and "Alcance" not in txt


def test_ext_bad_report_extension(tmp_path, capsys):
    p = _csv(tmp_path, [_srf(1.8)])
    assert main(["ext", "--results", p, "--report", str(tmp_path / "x.pdf")]) == 1
    assert capsys.readouterr().out == ""
