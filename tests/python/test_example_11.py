"""El ejemplo 11 corre: criterios de aceptación y Sarma sobre un tajo, un botadero y un pad sintéticos, con los números
y estados que declara su README."""
import csv
import importlib.util
import re
from collections import Counter
from pathlib import Path

import pytest

RUTA = Path(__file__).resolve().parents[2] / "examples" / "11-criterios-sarma" / "criterios.py"


def cargar():
    spec = importlib.util.spec_from_file_location("criterios", RUTA)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_criterios_sarma(tmp_path, capsys):
    r = cargar().main(tmp_path)
    salida = capsys.readouterr().out
    assert (r["cli_le"], r["cli_slope"]) == (0, 2)
    assert r["counts"] == {
        "READ-STACEY-2009": {"checks": 5, "meets": 2, "fails": 1, "not_verifiable": 2},
        "RYAN-PRYOR-2000": {"checks": 1, "meets": 1, "fails": 0, "not_verifiable": 0},
        "Criterios.csv": {"checks": 2, "meets": 1, "fails": 1, "not_verifiable": 0},
        "NDEP-2021": {"checks": 3, "meets": 2, "fails": 1, "not_verifiable": 0},
    }
    assert r["states"] == {
        "READ-STACEY-2009": [("block 1", "slope_fs_static", "meets"), ("block 1", "slope_pof", "fails"),
                             ("le 1", "slope_fs_static", "meets"), ("le 2", "slope_fs_static", "not_verifiable"),
                             ("le 3", "slope_fs_static", "not_verifiable")],
        "RYAN-PRYOR-2000": [("berm 2", "berm_reliability", "meets")],
        "Criterios.csv": [("le 2", "slope_fs_static", "fails"), ("le 2", "slope_fs_pseudostatic", "meets")],
        "NDEP-2021": [("le 3", "slope_fs_static", "meets"), ("le 3", "slope_fs_pseudostatic", "fails"),
                      ("le 3", "deformation_required", "meets")],
    }
    assert r["pe264"] == ["meets"] and r["pof_upper"] == ["meets"]
    assert r["le_attention"] == [[], [], []]  # solo los «no cumple» piden atención en el equilibrio límite
    assert r["kh"] == [0.1, 0.07, 0.16]
    assert r["fs_bloque"] == pytest.approx(1.120, abs=1e-3)
    assert r["pof_bloque"] == pytest.approx(0.282, abs=1e-3)
    assert r["berm_reliability"] == pytest.approx(0.945, abs=1e-3)
    assert r["fs_global_estatico"] == pytest.approx(1.424, abs=1e-3)
    assert r["fs_global"] == pytest.approx(1.229, abs=1e-3)
    assert r["fs_botadero_estatico"] == pytest.approx(1.258, abs=1e-3)
    assert r["fs_botadero"] == pytest.approx(1.059, abs=1e-3)
    assert r["kc_botadero"] == pytest.approx(0.0956, abs=1e-3)
    assert r["sarma_angulos"] == pytest.approx([70.8, 81.5], abs=0.1)
    assert r["fs_pad_estatico"] == pytest.approx(1.516, abs=1e-3)
    assert 1.0 < r["fs_pad"] < 1.05 and r["fs_pad"] == pytest.approx(1.040, abs=1e-3)  # NDEP ítem 7 exige Newmark
    assert r["ky_pad"] == pytest.approx(0.178, abs=1e-3)
    assert r["newmark_pad_m"] == pytest.approx(0.027, abs=1e-3)
    for nombre in r["files"]:
        assert (tmp_path / nombre).stat().st_size > 0, nombre
    for nombre in ("Criterios.csv", "criterios_resultados.csv", "criterios_tajo.html", "criterios_botadero.html",
                   "criterios_pad.html", "criterios_le_cli.csv"):
        assert nombre in r["files"]
    # el archivo trae todos los chequeos (los cuatro perfiles y el art. 264) con los mismos estados
    with open(tmp_path / "criterios_resultados.csv", newline="", encoding="utf-8-sig") as fh:
        filas = list(csv.DictReader(fh))
    assert Counter(f["estado"] for f in filas) == {"cumple": 7, "no_cumple": 3, "no_verificable": 2}
    assert [f["fuerza"] for f in filas if f["criterio"] == "PE-264"] == ["ley"]
    assert {f["marca"] for f in filas if f["id_objeto"] == "A2" and f["criterio"]} == {"user"}
    # paridad: la CLI de `le` escribe los mismos chequeos de Read y Stacey sobre el equilibrio límite
    with open(tmp_path / "criterios_le_cli.csv", newline="", encoding="utf-8-sig") as fh:
        cli_le = [(f["id_objeto"], f["regla"], f["estado"]) for f in csv.DictReader(fh)]
    assert cli_le == [(f["id_objeto"], f["regla"], f["estado"]) for f in filas[:5] if f["tipo_objeto"] == "le"]
    assert "meets: 1, fails: 0, not verifiable: 2" in salida and "PE-264: meets [law]" in salida
    assert "meets: 1, fails: 1, not verifiable: 0" in salida and "fails by rule: slope_pof (1)" in salida
    for nombre in ("criterios_tajo.html", "criterios_botadero.html", "criterios_pad.html"):
        html = (tmp_path / nombre).read_text(encoding="utf-8")
        assert not re.search("aprob", html, re.I), nombre
    # la CLI no imprime ids de fila, de material ni de línea
    assert not re.search(r"\b(BQ[12]|TB1|F01|P1|A[123]|T1|B1|S1|desmonte|arcilla|mineral|interfaz|geomembrana)\b",
                         salida)
