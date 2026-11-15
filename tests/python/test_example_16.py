"""El ejemplo 16 corre, imprime solo conteos y no filtra ids."""
import os
import subprocess
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parents[2] / "examples" / "16-resultados-externos"


def test_ejemplo_16(tmp_path):
    p = subprocess.run([sys.executable, str(DIR / "main.py"), str(tmp_path)], capture_output=True, text=True,
                       encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"}, timeout=120)
    assert p.returncode == 0, p.stderr
    assert "Registros leídos: Slide2 4, RS2 3" in p.stdout
    assert "Chequeos: 6" in p.stdout and "Monitoreo: 1" in p.stdout and "RocData: 2 filas, 1 con" in p.stdout
    assert "ZZSENT" not in p.stdout + p.stderr
