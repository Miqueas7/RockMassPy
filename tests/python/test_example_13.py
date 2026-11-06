"""El ejemplo 13 corre: mina sintética base por la auditoría y los niveles 1, 2 y 3, medida contra su verdad."""
import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("openpyxl")
pred = pytest.importorskip("rockmasspy.predictive")

RUTA = Path(__file__).resolve().parents[2] / "examples" / "13-mina-sintetica" / "mina_sintetica.py"


def cargar():
    spec = importlib.util.spec_from_file_location(RUTA.stem, RUTA)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_mina_sintetica(tmp_path, capsys):
    mod = cargar()
    assert mod.CARTA_A_TIPO == pred.synthetic._CATEGORY_TO_TYPE  # la misma equivalencia que el generador
    r = mod.main(tmp_path)
    mod.imprimir(r)
    salida = capsys.readouterr().out
    assert "nivel 3: site" in salida and "demasiado liviano 0.0 %" in salida
    assert r["tramos"] > 700 and r["audit"]["findings"] == 0
    a, ci, estado, a_verdad = r["nivel1"]
    assert estado == "site" and ci[0] <= a_verdad <= ci[1]  # recupera la recta que emerge de los componentes
    assert r["nivel2"][0] == "ready" and r["nivel2"][1]["ln_q"] == "coherent"
    n3 = r["nivel3"]
    assert n3["calibracion"] == "site" and not n3["bloqueos"]
    assert n3["zone_sd_upper"] > n3["zone_sd"] and any("zones" in w for w in n3["avisos"])  # 5 zonas: aviso
    cmp = r["comparacion"]
    assert cmp["modelo"]["n"] > 0 and cmp["modelo"]["liviano"] <= 0.05  # lo que dice el README
    assert cmp["carta_en_elegidos"]["liviano"] > cmp["modelo"]["liviano"]
    assert cmp["carta"]["n"] == cmp["instalado"]["n"] == r["tramos_nuevos"]
    assert sum(r["motivos"].values()) == r["tramos_nuevos"]
    for nombre in r["files"]:
        assert (tmp_path / nombre).stat().st_size > 0, nombre
    assert "T0" not in salida  # solo agregados, nunca ids
    for lit in pred.synthetic.LITHOLOGIES:
        assert lit not in salida
