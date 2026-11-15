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


def test_ejemplo_15_sin_sostenimiento_y_rigidez(tmp_path):
    p = subprocess.run([sys.executable, str(DIR / "main.py"), str(tmp_path)], capture_output=True, text=True,
                       encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"}, timeout=120)
    assert "sin sostenimiento: FS sin sostenimiento" in p.stdout and "sin cruce" not in p.stdout
    assert "gobierna" in p.stdout
    assert ";-3.5;" in (tmp_path / "capacidades.csv").read_text(encoding="utf-8")  # σt negativa por convención
