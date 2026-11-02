"""El ejemplo 04 corre: crea los informes y la CLI da 2 por el tramo sin tabla."""
import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
pytest.importorskip("docx")

RUTA = Path(__file__).resolve().parents[2] / "examples" / "04-informe" / "informe.py"
ARCHIVOS = ["tramos.xlsx", "tramos.csv", "resultados.xlsx", "memoria.html", "memoria.docx", "anexo39b.html",
            "anexo39b.docx", "resultados_cli.csv", "memoria_cli.html"]


def test_informe(tmp_path):
    spec = importlib.util.spec_from_file_location("informe", RUTA)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    r = mod.main(tmp_path)
    assert r["files"] == ARCHIVOS
    for nombre in ARCHIVOS:
        assert (tmp_path / nombre).stat().st_size > 0, nombre
    assert (r["total"], r["classified"], r["unclassified"]) == (12, 11, 1)
    # el tramo cuya labor no tiene tabla queda sin clasificar y la CLI avisa con 2
    assert r["exit_codes"] == {"classify": 2, "report": 2}
    assert "Este documento no reemplaza el estudio geomecánico firmado." in (tmp_path / "memoria.html").read_text(
        encoding="utf-8")
