"""El ejemplo 03 corre, crea todos los archivos y la ida y vuelta por CSV es exacta."""
import importlib.util
from pathlib import Path

RUTA = Path(__file__).resolve().parents[2] / "examples" / "03-cartillas" / "graficos.py"
ARCHIVOS = ["cartilla_celdas.png", "cartilla_celdas.pdf", "cartilla_rango.png", "gsi_cuantificada.svg",
            "envolventes.png", "correlacion.png", "histograma.png"]


def test_cartillas(tmp_path):
    spec = importlib.util.spec_from_file_location("graficos", RUTA)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    r = mod.main(tmp_path)
    assert r["files"] == ARCHIVOS
    for nombre in ARCHIVOS:
        assert (tmp_path / nombre).stat().st_size > 0, nombre
    assert (tmp_path / "tabla_csv").is_dir()
    assert r["csv_roundtrip_ok"] is True
