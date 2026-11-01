"""El ejemplo 02 corre y da los valores publicados en su README."""
import importlib.util
from pathlib import Path

RUTA = Path(__file__).resolve().parents[2] / "examples" / "02-tabla-por-labor" / "tabla.py"


def test_tabla_por_labor(tmp_path):
    spec = importlib.util.spec_from_file_location("tabla", RUTA)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    r = mod.main(tmp_path)
    assert r == {"galeria_rmr53": "III", "tajeo_MF/R": "III", "issues_galeria": 0, "issues_tajeo": 0,
                 "roundtrip_ok": True}
