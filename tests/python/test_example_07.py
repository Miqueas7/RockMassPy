"""El ejemplo 07 corre: tramos, caras y declaraciones de diseño sintéticos contra el perfil Perú."""
import importlib.util
import re
from pathlib import Path

import pytest

RUTA = Path(__file__).resolve().parents[2] / "examples" / "07-verificacion-normativa-peru" / "verificar.py"


def cargar():
    spec = importlib.util.spec_from_file_location("verificar", RUTA)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_verificar(tmp_path):
    r = cargar().main(tmp_path)
    c = r["counts"]
    assert c == {"complies": 2, "does_not_comply": 7, "attention": 4, "note": 0, "not_checked": 2, "not_verifiable": 9}
    assert r["verify_exit"] == 2 and r["cli_exit"] == 2
    for nombre in r["files"]:
        assert (tmp_path / nombre).stat().st_size > 0, nombre
    for nombre in ("Estaciones_refugio.csv", "Refugios_peatonales.csv", "Resumen_QC.csv", "Factores_seguridad.csv",
                   "Autosoporte.csv", "Tramos.csv", "Superficies.csv"):
        assert nombre in r["files"]
    html = (tmp_path / "verificacion.html").read_text(encoding="utf-8")
    assert not re.search(r"aprob|aprueb|approv", html, re.I) and "SECRETO" not in html
    assert not re.search(r"\b(R\d\d|V\d\d|A\d\d|G\d\d|P\d\d|C\d\d)\b", html)  # sin identificadores de fila
