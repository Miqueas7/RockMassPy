"""El ejemplo 18 corre y termina en 0."""
import os
import subprocess
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parents[2] / "examples" / "18-modelo-sustituto"


def test_ejemplo_18(tmp_path):
    p = subprocess.run([sys.executable, str(DIR / "main.py"), str(tmp_path)], capture_output=True, text=True,
                       encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"}, timeout=300)
    assert p.returncode == 0, p.stderr
    for t in ("agrupada", "aleatoria", "PoF de verdad", "poly2", "FS = nan"):
        assert t in p.stdout
    assert (tmp_path / "corridas.csv").exists()
