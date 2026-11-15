"""El ejemplo 17 corre y termina en 0."""
import os
import subprocess
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parents[2] / "examples" / "17-elementos-de-contorno"


def test_ejemplo_17(tmp_path):
    p = subprocess.run([sys.executable, str(DIR / "main.py"), str(tmp_path)], capture_output=True, text=True,
                       encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"}, timeout=300)
    assert p.returncode == 0, p.stderr
    for caso in ("Caso a", "Caso b", "Caso c: pilar, malla gruesa", "Caso c: pilar, malla fina", "Caso d"):
        assert caso in p.stdout
    assert len(list(tmp_path.glob("*.png"))) == 4
