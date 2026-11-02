"""El ejemplo 06 corre: caras sintéticas, Mathews, gráfico, informe, MRMR y CLI."""
import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
pytest.importorskip("openpyxl")

RUTA = Path(__file__).resolve().parents[2] / "examples" / "06-tajeos-mathews-mrmr" / "tajeos.py"


def test_tajeos(tmp_path):
    spec = importlib.util.spec_from_file_location("tajeos", RUTA)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    r = mod.main(tmp_path)
    assert r["zones"] == {1: 4, 2: 1, 3: 1} and len(r["n_prime"]) == 6
    assert (r["mrmr_class"], r["mrmr"]) == ("4B", pytest.approx(26.594443, abs=1e-6))
    assert r["exit_codes"]["mrmr"] == 0 and r["exit_codes"]["mathews"] == 2
    for nombre in r["files"]:
        assert (tmp_path / nombre).stat().st_size > 0, nombre
    assert "SECRETO-123" in (tmp_path / "Superficies.csv").read_text(encoding="utf-8")  # la columna ajena existe
    for nombre in ("informe.html", "resultados.csv"):
        assert "SECRETO" not in (tmp_path / nombre).read_text(encoding="utf-8"), nombre
