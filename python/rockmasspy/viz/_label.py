"""Punto de rótulo dentro de un polígono, compartido por los gráficos de regiones."""

from __future__ import annotations

from ..chart_regions import _classify


def _centroid(poly):
    """Centroide del área del polígono (en el plano que se le dé)."""
    a = cx = cy = 0.0
    for i in range(len(poly)):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % len(poly)]
        c = x0 * y1 - x1 * y0
        a += c
        cx += (x0 + x1) * c
        cy += (y0 + y1) * c
    return cx / (3 * a), cy / (3 * a)


def _label_point(poly):
    """Centroide en log; si cae fuera del polígono, el punto medio de la cuerda horizontal más larga por su De."""
    cx, cy = _centroid(poly)
    if _classify(cx, cy, poly) > 0:
        return cx, cy
    xs = sorted(a[0] + (cy - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
                for a, b in zip(poly, poly[1:] + poly[:1]) if (a[1] > cy) != (b[1] > cy))
    a, b = max(zip(xs[::2], xs[1::2]), key=lambda c: c[1] - c[0])
    return (a + b) / 2, cy
