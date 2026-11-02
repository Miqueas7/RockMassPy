"""El ejemplo 05 corre: caso de Hoek, ediciones, lote con referencia de la carta Q, figura, memoria y CLI."""
import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
pytest.importorskip("docx")
pytest.importorskip("openpyxl")

RUTA = Path(__file__).resolve().parents[2] / "examples" / "05-sostenimiento-q" / "sostenimiento.py"


def test_sostenimiento(tmp_path):
    spec = importlib.util.spec_from_file_location("sostenimiento", RUTA)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    r = mod.main(tmp_path)
    # la carta digitalizada fiel da 3 para Hoek (su 4 viene de una carta anterior, ver el CHANGELOG)
    assert r["hoek_category"] == 3
    assert (r["walls_q_2015"], r["walls_q_2025"]) == (1.0, 0.4)
    assert r["tramos"] == 8 and r["con_referencia"] == 8
    assert r["exit_codes"] == {"qsupport": 0, "classify": 0}
    for nombre in r["files"]:
        assert (tmp_path / nombre).stat().st_size > 0, nombre
    html = (tmp_path / "memoria.html").read_text(encoding="utf-8")
    assert "5.1" in html and "SECRETO" not in html
