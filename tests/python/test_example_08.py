"""El ejemplo 08 corre: tres taludes sintéticos con cinemática, SMR y Q-slope, y los conteos que declara su README."""
import csv
import importlib.util
import re
from pathlib import Path

import pytest

RUTA = Path(__file__).resolve().parents[2] / "examples" / "08-taludes-cinematica-smr-qslope" / "taludes.py"


def cargar():
    spec = importlib.util.spec_from_file_location("taludes", RUTA)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_taludes(tmp_path):
    r = cargar().main(tmp_path)
    c = r["counts"]
    assert r["cli_exit"] == 2
    assert (c["slopes"], c["n_planes"], c["n_intersections"]) == (3, 225, 5625)
    assert (c["planar"], c["planar_no_limits"], c["wedge_primary"], c["wedge_secondary"]) == (25, 25, 597, 173)
    assert (c["flexural_toppling"], c["direct_toppling"], c["direct_toppling_oblique"]) == (49, 406, 225)
    assert (c["smr_d_1"], c["smr_d_3"], c["smr_d_5"], c["smr_c_1"], c["smr_c_3"], c["smr_c_5"]) == (1,) * 6
    assert (c["q_slope_evaluated"], c["face_steeper_than_beta"], c["warnings"], c["notes"]) == (2, 1, 0, 0)
    for nombre in r["files"]:
        assert (tmp_path / nombre).stat().st_size > 0, nombre
    for nombre in ("Familias.csv", "Taludes.csv", "resultados.csv", "taludes.html"):
        assert nombre in r["files"]
    with open(tmp_path / "resultados.csv", newline="", encoding="utf-8-sig") as fh:
        filas = list(csv.DictReader(fh))
    assert len(filas) == 3 and len(filas[0]) == 26 and "smr_caso_continuo" in filas[0]
    # la cara 3 no tiene nada crítico; las caras 1 y 2 sí
    crit = ("planar", "cuna_primaria", "cuna_secundaria", "volteo_flexural", "volteo_directo", "volteo_directo_oblicuo")
    assert [sum(int(f[k]) for k in crit) for f in filas][2] == 0 and all(
        sum(int(f[k]) for k in crit) > 0 for f in filas[:2])
    html = (tmp_path / "taludes.html").read_text(encoding="utf-8")
    assert re.search(r"factibilidad|feasib", html, re.I)


def test_taludes_privacidad(tmp_path, capsys):
    """Columnas ajenas (códigos, coordenadas, observaciones) no se leen ni llegan a consola, figuras o informe."""
    mod = cargar()
    mod.escribir_entradas(tmp_path)
    ruta = tmp_path / "Taludes.csv"
    with open(ruta, newline="", encoding="utf-8-sig") as fh:
        filas = list(csv.reader(fh))
    extra = ["codigo_mina", "zona_nivel", "observaciones", "este_m", "norte_m"]
    filas[0] += extra
    for f in filas[1:]:
        f += ["ZZSENT"] * len(extra)
    with open(ruta, "w", newline="", encoding="utf-8-sig") as fh:
        csv.writer(fh).writerows(filas)
    pytest.importorskip("matplotlib")
    from rockmasspy.cli import main

    cod = main(["slope", "--faces", str(ruta), "--families", str(tmp_path / "Familias.csv"),
                "--report", str(tmp_path / "t.html"), "--charts", str(tmp_path / "fig"), "-o", str(tmp_path / "r.csv")])
    salida = capsys.readouterr()
    assert cod == 2
    for texto in (salida.out, salida.err, (tmp_path / "t.html").read_text(encoding="utf-8"),
                  (tmp_path / "r.csv").read_text(encoding="utf-8-sig")):
        assert "ZZSENT" not in texto
    assert not re.search(r"\b(TL\d|T0\d)\b", salida.out + salida.err)  # la CLI no imprime identificadores de fila
