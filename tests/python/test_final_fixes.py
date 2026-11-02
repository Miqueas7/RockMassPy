"""Correcciones de la revisión final de la 1D (I1, I2, M1 a M10). Solo datos sintéticos."""
import dataclasses
import re
import os
import subprocess
import sys

import pytest

import rockmasspy as rm
import rockmasspy.report as rp
from rockmasspy.cli import main
from rockmasspy.report.texts import REPORT_TEXTS, t

from test_batch import CAT, lab, q_tab, rmr_tab, tr
from test_cli import tabla, tramos_xlsx  # noqa: F401  (fixture tabla)
from test_report_html import TABLES, resultados

openpyxl = pytest.importorskip("openpyxl")


# --- I1 ---
@pytest.mark.parametrize("suffix", [".xls", ".txt", ".xlsm"])
def test_load_tramos_unsupported_suffix(tmp_path, suffix):
    p = tmp_path / f"tramos{suffix}"
    p.write_bytes(b"\xd0\xcf\x11\xe0 basura")
    with pytest.raises(ValueError, match="unsupported file type") as e:
        rm.load_tramos(p)
    assert str(e.value) == f"tramos{suffix}: unsupported file type '{suffix}'; save it as .xlsx or .csv"


def test_garbage_xlsx_is_value_error(tmp_path):
    p = tmp_path / "malo.xlsx"
    p.write_bytes(b"esto no es un zip")
    with pytest.raises(ValueError, match="malo.xlsx: not a valid .xlsx file"):
        rm.load_tramos(p)
    with pytest.raises(ValueError, match="malo.xlsx: not a valid .xlsx file"):
        rm.load_table(p)


@pytest.mark.parametrize("nombre,datos", [("t.xls", b"abc"), ("t.xlsx", b"no zip")])
def test_cli_unreadable_one_line(tmp_path, tabla, capsys, nombre, datos):
    p = tmp_path / nombre
    p.write_bytes(datos)
    assert main(["classify", str(p), "--tables", str(tabla), "-o", str(tmp_path / "r.csv")]) == 1
    cap = capsys.readouterr()
    assert cap.err.startswith("error:") and len(cap.err.strip().splitlines()) == 1
    assert "Traceback" not in cap.err and "Traceback" not in cap.out


def test_cli_unreadable_table_one_line(tmp_path, capsys):
    xt = tramos_xlsx(tmp_path)
    bad = tmp_path / "tabla.xlsx"
    bad.write_bytes(b"no zip")
    assert main(["check", str(bad)]) == 1
    cap = capsys.readouterr()
    assert cap.err.startswith("error:") and len(cap.err.strip().splitlines()) == 1 and "Traceback" not in cap.err
    assert main(["classify", str(xt), "--tables", str(bad), "-o", str(tmp_path / "r.csv")]) == 1


# --- I2 ---
@pytest.mark.parametrize("lang", ["es", "en"])
@pytest.mark.parametrize("which", ["memoria", "anexo"])
def test_author_subtitle(tmp_path, lang, which):
    def build(**kw):
        if which == "memoria":
            return rp.build_memoria(resultados(), TABLES, title="X", lang=lang, figures=False, **kw), "memoria_title"
        return rp.build_anexo39b(resultados(), TABLES, title="X", lang=lang, figures=False, **kw), "a_subtitle"

    r, key = build()
    base = t(key, lang)
    assert r.subtitle == base
    r, _ = build(author="Ing. Ejemplo")
    assert r.subtitle == f"{base} · {t('prepared_by', lang)} Ing. Ejemplo"
    assert t("prepared_by", lang) == {"es": "Elaborado por", "en": "Prepared by"}[lang]
    html = rp.write_html(r, tmp_path / "a.html").read_text(encoding="utf-8")
    assert "Ing. Ejemplo" in html


# --- M1 ---
def test_default_title_localized(tmp_path, tabla):
    xt = tramos_xlsx(tmp_path)
    for lang, title in (("es", "Informe geomecánico"), ("en", "Geomechanical report")):
        out = tmp_path / f"{lang}.html"
        main(["report", str(xt), "--tables", str(tabla), "-o", str(out), "--lang", lang, "--no-figures"])
        assert f"<title>{title}</title>" in out.read_text(encoding="utf-8")


# --- M2 ---
def test_cli_ascii_stdout(tmp_path, tabla):
    xt = tramos_xlsx(tmp_path)
    env = {**os.environ, "PYTHONIOENCODING": "ascii"}
    r = subprocess.run([sys.executable, "-m", "rockmasspy.cli", "classify", str(xt), "--tables", str(tabla),
                        "-o", str(tmp_path / "r.csv")], capture_output=True, text=True, env=env)
    assert r.returncode in (0, 2), r.stderr
    assert "warnings:" in r.stdout


# --- M3 ---
def test_docx_properties(tmp_path):
    docx = pytest.importorskip("docx")
    p = rp.write_docx(rp.build_memoria(resultados(), TABLES, title="X", figures=False), tmp_path / "m.docx")
    cp = docx.Document(str(p)).core_properties
    for name in ("comments", "title", "subject", "keywords", "category", "author", "last_modified_by"):
        assert "python-docx" not in str(getattr(cp, name))
    assert cp.created.year >= 2026 and cp.modified.year >= 2026


# --- M4 ---
def test_english_texts_clean():
    for key, d in REPORT_TEXTS.items():
        assert "(s)" not in d["en"], key
    prose = " ".join(v["en"] for k, v in REPORT_TEXTS.items() if k != "h_labor")
    assert "labor" not in re.sub(r"\w+_\w+", "", prose)


# --- M6 ---
def test_column_map_error_shows_original_key(tmp_path):
    p = tmp_path / "t.csv"
    p.write_text("id_tramo,tipo_labor\nT1,galeria\n", encoding="utf-8")
    with pytest.raises(ValueError, match="column 'RMR Total'"):
        rm.load_tramos(p, column_map={"RMR Total": "rmr_valor"})


# --- M7 ---
def test_tramo_repr_hides_identification():
    x = tr("T1", labor_codigo="SECRETO-A", zona_nivel="SECRETO-B", este_m=111222.5, norte_m=999888.5)
    s = repr(x) + repr(rm.classify_tramos([x], TABLES)[0])
    for v in ("SECRETO-A", "SECRETO-B", "111222.5", "999888.5"):
        assert v not in s
    assert x == dataclasses.replace(x) and x != dataclasses.replace(x, este_m=1.0)
    hidden = {f.name for f in dataclasses.fields(rm.Tramo) if not f.repr}
    assert {"labor_codigo", "zona_nivel", "este_m", "norte_m"} <= hidden


# --- M8 ---
def test_malformed_gsi_cell_does_not_stop_batch():
    tables = [lab("rampa", __import__("test_batch").cell_tab())]
    res = rm.classify_tramos([tr("A", labor="rampa", gsi_celda="FR"), tr("B", labor="rampa", gsi_celda="F/R")],
                             tables)
    assert res[0].label is None and res[0].warnings
    assert res[1].label == "fr"


# --- M9 ---
def test_profile_catalog_matches_labor_like_batch(monkeypatch):
    import rockmasspy.viz as viz

    seen = {}
    monkeypatch.setattr(viz, "plot_labor_profile", lambda *a, catalog=None, **k: seen.setdefault("c", catalog))
    monkeypatch.setattr(rp, "_fig", lambda cap, fn, lang, figures: fn())
    tables = [lab("galería", rmr_tab())]
    res = rm.classify_tramos([tr("T1", labor="Galeria", rmr_valor=70, progresiva_inicio_m=0,
                                 progresiva_fin_m=5)], tables)
    rp._profile_figs(res, tables, "es", True)
    assert seen["c"] is tables[0].catalog
