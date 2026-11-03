"""El ejemplo 09 corre: cinco bloques sintéticos, una PoF con semilla 9 y los conteos que declara su README."""
import csv
import importlib.util
import re
from pathlib import Path

import pytest

RUTA = Path(__file__).resolve().parents[2] / "examples" / "09-bloques-probabilistico-berma" / "bloques.py"


def cargar():
    spec = importlib.util.spec_from_file_location("bloques", RUTA)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_bloques(tmp_path):
    r = cargar().main(tmp_path)
    c = r["block_counts"]
    assert r["cli_exit"] == 2
    assert (c["blocks"], c["planar"], c["wedge"], c["toppling"], c["berm"]) == (5, 2, 1, 1, 1)
    assert (c["formed"], c["with_fs"], c["fs_below_1"], c["probabilistic"], c["pof_above_0"]) == (3, 3, 1, 1, 1)
    assert (c["berm_narrower"], c["berm_reliability_evaluated"], c["warnings"], c["notes"]) == (0, 1, 0, 1)
    assert r["pof_planar"] * 100 == pytest.approx(7.0, abs=1.5)  # el README dice «cerca de 7 %»
    assert r["berm_reliability"] * 100 == pytest.approx(95.0, abs=1.5)
    fs = r["fs"]
    assert fs[0] == pytest.approx(1.065, abs=1e-3) and fs[1] == pytest.approx(1.497, abs=1e-3)
    # B3: 0.99986, bajo 1 por 1.4e-4 (el artículo publica 1.0): falla por FS < 1, no por la regla del empate
    assert fs[2] == pytest.approx(0.99986, abs=1e-5) and fs[2] < 1 and fs[3] is None and fs[4] is None
    assert r["retro_phi_c0"] == pytest.approx(50.3, abs=0.1)
    for nombre in r["files"]:
        assert (tmp_path / nombre).stat().st_size > 0, nombre
    for nombre in ("Familias.csv", "Taludes.csv", "Bloques.csv", "Distribuciones.csv", "bloques_resultados.csv",
                   "bloques.html"):
        assert nombre in r["files"]
    with open(tmp_path / "bloques_resultados.csv", newline="", encoding="utf-8-sig") as fh:
        filas = list(csv.DictReader(fh))
    assert len(filas) == 5 and len(filas[0]) == 25 and filas[0]["semilla"] == "9"
    assert [f["formado"] for f in filas] == ["si", "si", "si", "", "no"]
    html = (tmp_path / "bloques.html").read_text(encoding="utf-8")
    assert re.search(r"bloques|blocks", html, re.I)


def test_bloques_privacidad(tmp_path, capsys):
    """Columnas ajenas no se leen ni llegan a consola, figuras o informe; los ids van a la tabla, no a la CLI."""
    mod = cargar()
    mod.escribir_entradas(tmp_path)
    extra = ["codigo_mina", "zona_nivel", "observaciones", "este_m", "norte_m"]
    for nombre in ("Taludes.csv", "Bloques.csv"):
        ruta = tmp_path / nombre
        with open(ruta, newline="", encoding="utf-8-sig") as fh:
            filas = list(csv.reader(fh))
        filas[0] += extra
        for f in filas[1:]:
            f += ["ZZSENT"] * len(extra)
        with open(ruta, "w", newline="", encoding="utf-8-sig") as fh:
            csv.writer(fh).writerows(filas)
    pytest.importorskip("matplotlib")
    from rockmasspy.cli import main

    cod = main(["slope", "--faces", str(tmp_path / "Taludes.csv"), "--families", str(tmp_path / "Familias.csv"),
                "--blocks", str(tmp_path / "Bloques.csv"), "--distributions", str(tmp_path / "Distribuciones.csv"),
                "--seed", "9", "--report", str(tmp_path / "b.html"), "--charts", str(tmp_path / "fig"),
                "--blocks-output", str(tmp_path / "r.csv")])
    salida = capsys.readouterr()
    assert cod == 2
    for texto in (salida.out, salida.err, (tmp_path / "b.html").read_text(encoding="utf-8"),
                  (tmp_path / "r.csv").read_text(encoding="utf-8-sig")):
        assert "ZZSENT" not in texto
    assert not re.search(r"\b(B\d|TL\d|T0\d)\b", salida.out + salida.err)  # la CLI no imprime identificadores de fila
    assert (tmp_path / "fig" / "fs_hist_1.png").stat().st_size > 0
