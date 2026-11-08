"""El ejemplo 14 corre y imprime una probabilidad por tramo."""
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("openpyxl")

DIR = Path(__file__).resolve().parents[2] / "examples" / "14-incertidumbre-clasificacion"


def test_ejemplo_14(tmp_path):
    p = subprocess.run([sys.executable, str(DIR / "main.py"), str(tmp_path)], capture_output=True, text=True,
                       encoding="utf-8", env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"}, timeout=120)
    assert p.returncode == 0, p.stderr
    assert p.stdout.count("2000 muestras válidas") == 6
    assert "continuas" in p.stdout and "ZZSENT" not in p.stdout
    assert (tmp_path / "resultados.xlsx").stat().st_size > 0
