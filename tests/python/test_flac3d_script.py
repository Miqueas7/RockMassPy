"""El guion de FLAC3D corre con un `itasca` falso y escribe un CSV que `load_external` lee (Fase 8A, Tarea 5)."""
import re
import runpy
import sys
import types
from pathlib import Path

import numpy as np
import pytest

from rockmasspy.external import QUANTITIES, load_external

SCRIPT = Path(__file__).resolve().parents[2] / "examples" / "16-resultados-externos" / "flac3d_exportar.py"


def _fake(monkeypatch, stress, state=None):
    gp = types.SimpleNamespace(pos=lambda: np.array([[0., 0, 0], [1, 0, 0]]),
                               disp=lambda: np.array([[0.003, 0, 0.004], [0, 0, 0]]))
    za = types.SimpleNamespace(pos=lambda: np.array([[0.5, 0, 0]]), stress=lambda: stress)
    if state is not None:
        za.state = lambda: state
    monkeypatch.setitem(sys.modules, "itasca", types.SimpleNamespace(gridpointarray=gp, zonearray=za))


def _run(tmp_path, **ajustes):
    """Corre una copia del guion con las variables de arriba cambiadas (como las edita el usuario en FLAC3D)."""
    out = tmp_path / "o.csv"
    ajustes = {"SALIDA": str(out), "UNIDAD_ESFUERZO": "MPa", **ajustes}
    texto = SCRIPT.read_text(encoding="utf-8")
    for k, v in ajustes.items():
        texto, n = re.subn(rf"^{k} = .*$", lambda _: f"{k} = {v!r}", texto, flags=re.M)
        assert n == 1
    copia = tmp_path / "copia.py"
    copia.write_text(texto, encoding="utf-8")
    runpy.run_path(str(copia))
    return load_external(out)


def test_flac3d_script_roundtrip(tmp_path, monkeypatch):
    _fake(monkeypatch, np.array([[-3.0, -2.0, -1.0, 0, 0, 0]]))  # tracción positiva: 3, 2, 1 MPa de compresión
    ext = _run(tmp_path)
    q = {(r.object_id, r.quantity): r.value for r in ext.records}
    assert {r.quantity for r in ext.records} <= set(QUANTITIES) and all(r.program == "FLAC3D" for r in ext.records)
    assert q[("N1", "u_total_m")] == pytest.approx(0.005) and q[("N1", "uz_m")] == pytest.approx(0.004)
    assert q[("Z1", "sigma1_mpa")] == pytest.approx(3.0) and q[("Z1", "sigma3_mpa")] == pytest.approx(1.0)
    assert not any(r.quantity == "yielded" for r in ext.records)


def test_flac3d_script_tensor_and_yielded(tmp_path, monkeypatch):
    _fake(monkeypatch, -np.diag([4.0, 2.0, 1.0])[None], state=np.array([2]))
    ext = _run(tmp_path, FUNCION_FLUENCIA="state", UNIDAD_ESFUERZO="kPa")
    q = {(r.object_id, r.quantity): r.value for r in ext.records}
    assert q[("Z1", "sigma1_mpa")] == pytest.approx(0.004) and q[("Z1", "yielded")] == 1.0
