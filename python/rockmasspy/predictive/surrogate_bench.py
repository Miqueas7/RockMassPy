"""Banco con verdad conocida del sustituto (Fase 8D, tarea 2). Solo es banco: nunca entrena un modelo que se entregue.

Las corridas salen de los modelos del núcleo (planar de la 3B, GRC de la 8B); la verdad de la PoF se compara contra
`probabilistic.run_probabilistic` sobre el mismo modelo. Los grupos son escenarios: bloques consecutivos de corridas.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.stats import qmc

from .. import _rockmasspy_core as rm
from .surrogate import SurrogateData

PLANAR_RANGES = {"cohesion": (2.0, 25.0), "friction_deg": (20.0, 45.0), "water_fill": (0.0, 1.0),
                 "plane_dip_deg": (30.0, 45.0)}
GRC_RANGES = {"radius_m": (2.0, 6.0), "p0_mpa": (2.0, 10.0), "e_mpa": (500.0, 5000.0), "c_mpa": (0.5, 3.0),
              "phi_deg": (25.0, 40.0)}
N_SCENARIOS = 6


def _design(n: int, seed: int, ranges: dict) -> np.ndarray:
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n: must be an integer >= 2")
    lo, hi = zip(*ranges.values())
    return qmc.scale(qmc.LatinHypercube(d=len(ranges), seed=seed).random(n), lo, hi)


def _scenarios(n: int) -> tuple[str, ...]:
    return tuple(f"E{i * N_SCENARIOS // n + 1}" for i in range(n))


def planar_base():
    i = rm.PlanarInput()
    i.height_m, i.face_dip_deg, i.plane_dip_deg, i.unit_weight, i.water_unit_weight = 60, 50, 35, 2.6, 1.0
    i.cohesion, i.friction_deg, i.tension_crack_distance_m = 10, 35, 5.0
    return i


def planar_runs(n: int, *, seed: int, ranges: dict | None = None) -> SurrogateData:
    """n corridas LHS de `planar_fs` (salida FS). Las que no forman bloque o dan FS no finito se descartan."""
    ranges = {**PLANAR_RANGES, **(ranges or {})}
    X = _design(n, seed, ranges)
    base, rows, y = planar_base(), [], []
    for x in X:
        for name, v in zip(ranges, x):
            setattr(base, name, float(v))
        r = rm.planar_fs(base)
        fs = r.factor_of_safety
        if r.formed and fs is not None and math.isfinite(fs):
            rows.append(x)
            y.append(fs)
    return SurrogateData(np.array(rows), np.array(y), tuple(ranges), _scenarios(len(y)))


def grc_runs(n: int, *, seed: int) -> SurrogateData:
    """n corridas LHS de `grc_mc` (salida `strain_pct` = u_max / R · 100)."""
    X = _design(n, seed, GRC_RANGES)
    y = []
    for x in X:
        i = rm.GrcMcInput(radius_m=x[0], p0_mpa=x[1], e_mpa=x[2], nu=0.25, c_mpa=x[3], phi_deg=x[4], psi_deg=0.0)
        y.append(rm.grc_mc(i, 2).u_max_m / x[0] * 100)
    return SurrogateData(X, np.array(y), tuple(GRC_RANGES), _scenarios(n))
