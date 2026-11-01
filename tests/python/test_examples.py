"""El ejemplo sintético corre y da los valores publicados en su README."""
import importlib.util
from pathlib import Path

import pytest

RUTA = Path(__file__).resolve().parents[2] / "examples" / "01-tramo-sintetico" / "tramo.py"


def test_tramo_sintetico():
    spec = importlib.util.spec_from_file_location("tramo", RUTA)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    r = mod.main()
    assert r["rmr89"] == 53
    assert r["q"] == pytest.approx(5.4167, abs=5e-5)
    assert r["gsi"] == 59.5
    assert r["phi_deg"] == pytest.approx(52.75, abs=0.01)
    assert r["cohesion_mpa"] == pytest.approx(2.633, abs=0.001)
    assert r["erm_mpa"] == pytest.approx(19637.7, abs=0.1)
