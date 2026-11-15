"""El ejemplo 15 corre y imprime el FS del RST Ejemplo 1."""
import os
import subprocess
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parents[2] / "examples" / "15-tuneles-convergencia-confinamiento"


def test_ejemplo_15(tmp_path):
    p = subprocess.run([sys.executable, str(DIR / "main.py"), str(tmp_path)], capture_output=True, text=True,
                       encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"}, timeout=120)
    assert p.returncode == 0, p.stderr
    assert "RST Ejemplo 1: FS 1.84" in p.stdout
    assert "Coherencia Hoek-Brown" in p.stdout and "pares fuera del diagrama" in p.stdout
