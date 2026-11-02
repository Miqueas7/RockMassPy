"""El ejemplo 06 corre: caras sintéticas, Mathews, gráfico, informe, MRMR y CLI."""
import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
pytest.importorskip("docx")
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
    html = (tmp_path / "informe.html").read_text(encoding="utf-8")
    assert "SECRETO" not in html
