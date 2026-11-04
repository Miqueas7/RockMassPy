"""El ejemplo 10 corre: un tajo de dos estratos y un botadero sintéticos, con los números que declara su README."""
import csv
import importlib.util
import re
from pathlib import Path

import pytest

RUTA = Path(__file__).resolve().parents[2] / "examples" / "10-equilibrio-limite-newmark" / "equilibrio.py"


def cargar():
    spec = importlib.util.spec_from_file_location("equilibrio", RUTA)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_equilibrio(tmp_path, capsys):
    r = cargar().main(tmp_path)
    salida = capsys.readouterr().out
    assert r["cli_exit"] == 0
    assert r["le_counts"] == {"analyses": 2, "with_fs": 2, "fs_below_1": 0, "circular": 1, "block": 1, "given": 0,
                              "with_newmark": 1, "warnings": 0, "notes": 3}
    assert r["attention"] == [[], []]
    tajo, botadero = r["fs"]
    assert tajo["Bishop-Simplified"] == pytest.approx(1.485, abs=1e-3)
    assert tajo["Morgenstern-Price-GLE"] == pytest.approx(1.480, abs=1e-3)
    assert botadero["Spencer"] == pytest.approx(1.108, abs=1e-3)  # con kh = 0.1
    assert botadero["Morgenstern-Price-GLE"] == pytest.approx(1.106, abs=1e-3)
    assert r["fs_min"] == [pytest.approx(1.480, abs=1e-3), pytest.approx(1.106, abs=1e-3)]
    assert r["fs_static_botadero"] == pytest.approx(1.315, abs=1e-3)
    assert r["ky"] == pytest.approx(0.156, rel=0.01)
    assert r["newmark_m"] == pytest.approx(0.046, rel=0.01)
    for nombre in r["files"]:
        assert (tmp_path / nombre).stat().st_size > 0, nombre
    for nombre in ("Geometria.csv", "Estratos.csv", "Materiales_LE.csv", "Analisis_LE.csv", "Sismos.csv",
                   "equilibrio_resultados.csv", "equilibrio.html"):
        assert nombre in r["files"]
    with open(tmp_path / "equilibrio_resultados.csv", newline="", encoding="utf-8-sig") as fh:
        filas = list(csv.DictReader(fh))
    assert [(f["id_analisis"], f["metodo"]) for f in filas] == [("A1", "bishop"), ("A1", "gle"), ("A2", "spencer"),
                                                                 ("A2", "gle")]
    assert [f["fs_menor_o_igual_1"] for f in filas] == ["no"] * 4
    html = (tmp_path / "equilibrio.html").read_text(encoding="utf-8")
    assert re.search(r"equilibrio límite", html, re.I)
    # la CLI no imprime ids de fila ni de material
    assert not re.search(r"\b(A[12]|T1|B1|S1|residual|roca|desmonte|arcilla|fundacion)\b", salida)
