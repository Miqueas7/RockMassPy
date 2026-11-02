"""Ubicar un punto en regiones poligonales de un ábaco (carta Q, y en la 2B Laubscher).

Cada región es un polígono simple con su clave entera. Por convención la clave mayor es la menos favorable, así
que un punto sobre una arista o un vértice compartido toma la mayor (regla del límite de toda la Fase 1).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

_EDGE_TOL = 1e-12


@dataclass(frozen=True)
class Region:
    key: int
    polygon: tuple[tuple[float, float], ...]


def _on_segment(x: float, y: float, a: tuple[float, float], b: tuple[float, float]) -> bool:
    dx, dy = b[0] - a[0], b[1] - a[1]
    n2 = dx * dx + dy * dy
    t = 0.0 if n2 == 0 else max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / n2))
    return math.hypot(a[0] + t * dx - x, a[1] + t * dy - y) <= _EDGE_TOL


def _classify(x: float, y: float, polygon: Sequence[tuple[float, float]]) -> int:
    """1 si el punto está dentro, 0 si está sobre una arista y -1 si está fuera (cruce de rayos)."""
    n = len(polygon)
    inside = False
    for i in range(n):
        a, b = polygon[i], polygon[(i + 1) % n]
        if _on_segment(x, y, a, b):
            return 0
        if (a[1] > y) != (b[1] > y) and x < a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1]):
            inside = not inside
    return 1 if inside else -1


def locate(x: float, y: float, regions: Sequence[Region]) -> int | None:
    """Clave de la región que contiene (x, y); en una arista o vértice compartido, la mayor; None si ninguna."""
    if not (math.isfinite(x) and math.isfinite(y)):
        raise ValueError(f"point must be finite, got ({x}, {y})")
    keys = [r.key for r in regions if _classify(x, y, r.polygon) >= 0]
    return max(keys) if keys else None
