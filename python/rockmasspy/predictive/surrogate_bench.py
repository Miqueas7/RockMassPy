"""Banco con verdad conocida del sustituto (Fase 8D, tarea 2). Solo es banco: nunca entrena un modelo que se entregue.

Las corridas salen de los modelos del núcleo (planar de la 3B, GRC de la 8B); la verdad de la PoF se compara contra
`probabilistic.run_probabilistic` sobre el mismo modelo. Los grupos son escenarios reales: cada uno fija su geometría (planar) o su excavación (GRC) y dentro se
muestrea el resto, así que dejar un escenario fuera es extrapolar de verdad.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.stats import qmc

from .. import _rockmasspy_core as rm
from .surrogate import SurrogateData

PLANAR_RANGES = {"cohesion": (2.0, 25.0), "friction_deg": (20.0, 45.0), "water_fill": (0.0, 1.0),
                 "plane_dip_deg": (30.0, 45.0), "height_m": (40.0, 70.0)}
_PLANAR_SCENARIO = ("plane_dip_deg", "height_m")  # fijas dentro de cada escenario
GRC_RANGES = {"radius_m": (2.0, 6.0), "p0_mpa": (2.0, 10.0), "e_mpa": (500.0, 5000.0), "c_mpa": (0.5, 3.0),
              "phi_deg": (25.0, 40.0)}
_GRC_SCENARIO = ("p0_mpa",)
N_SCENARIOS = 10


def _lhs(n: int, seed: int, ranges: dict) -> np.ndarray:
    lo, hi = zip(*ranges.values())
    return qmc.scale(qmc.LatinHypercube(d=len(ranges), seed=seed).random(n), lo, hi)


def _scenario_design(n: int, seed: int, ranges: dict, fixed: tuple) -> tuple[np.ndarray, tuple[str, ...]]:
    """Columnas en el orden de `ranges`: las `fixed` valen lo mismo dentro de cada escenario; el resto, LHS dentro."""
    if isinstance(n, bool) or not isinstance(n, int) or n < N_SCENARIOS:
        raise ValueError(f"n: must be an integer >= {N_SCENARIOS}")
    scen = _lhs(N_SCENARIOS, seed, {k: ranges[k] for k in fixed})
    free = {k: v for k, v in ranges.items() if k not in fixed}
    sizes = np.full(N_SCENARIOS, n // N_SCENARIOS)
    sizes[: n % N_SCENARIOS] += 1
    rows, groups = [], []
    for s, m in enumerate(sizes):
        inner = _lhs(int(m), seed * 1000 + s + 1, free)
        for r in inner:
            d = dict(zip(free, r)) | dict(zip(fixed, scen[s]))
            rows.append([d[k] for k in ranges])
            groups.append(f"E{s + 1}")
    return np.array(rows), tuple(groups)


def planar_base():
    i = rm.PlanarInput()
    i.height_m, i.face_dip_deg, i.plane_dip_deg, i.unit_weight, i.water_unit_weight = 60, 50, 35, 2.6, 1.0
    # 5.0 m y no el default (None): 15.3 m no forma bloque con planos de 30-45 grados (la grieta debe cortar el plano)
    i.cohesion, i.friction_deg, i.tension_crack_distance_m = 10, 35, 5.0
    return i


def planar_runs(n: int, *, seed: int, ranges: dict | None = None) -> SurrogateData:
    """n corridas de `planar_fs` (salida FS) en 10 escenarios (inclinación del plano y altura fijas por escenario;
    cohesión, fricción y agua por LHS dentro). Las que no forman bloque o dan FS no finito se descartan."""
    if ranges and not set(ranges) <= set(PLANAR_RANGES):
        raise ValueError("ranges: unknown input name")
    ranges = {**PLANAR_RANGES, **(ranges or {})}
    X, g = _scenario_design(n, seed, ranges, _PLANAR_SCENARIO)
    base, keep, y = planar_base(), [], []
    for i, x in enumerate(X):
        for name, v in zip(ranges, x):
            setattr(base, name, float(v))
        r = rm.planar_fs(base)
        fs = r.factor_of_safety
        if r.formed and fs is not None and math.isfinite(fs):
            keep.append(i)
            y.append(fs)
    return SurrogateData(X[keep], np.array(y), tuple(ranges), tuple(g[i] for i in keep))


def grc_runs(n: int, *, seed: int) -> SurrogateData:
    """n corridas de `grc_mc` (salida `strain_pct` = u_max / R · 100) en 10 escenarios (p0 fijo por escenario)."""
    X, g = _scenario_design(n, seed, GRC_RANGES, _GRC_SCENARIO)
    y = []
    for x in X:
        i = rm.GrcMcInput(radius_m=x[0], p0_mpa=x[1], e_mpa=x[2], nu=0.25, c_mpa=x[3], phi_deg=x[4], psi_deg=0.0)
        y.append(rm.grc_mc(i, 2).u_max_m / x[0] * 100)
    return SurrogateData(X, np.array(y), tuple(GRC_RANGES), g)
