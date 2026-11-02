"""Estabilidad de caras de tajeo por el método de Mathews, versión de Potvin (1988): N′ = Q′·A·B·C sobre el gráfico.

Los factores A y C y el radio hidráulico viven en C++ (`rockmasspy`); aquí está el factor B, que es una familia de
curvas sin ecuación (Potvin, tesis PhD, UBC, Fig. 7.19, p. 201 impresa, 223 física), y la evaluación completa.

Cómo se digitalizó la Fig. 7.19 (como `stability_graphs.py`; el script y las imágenes quedan fuera del repo):
1. Se renderizó la página física 223 a 250 dpi con PyMuPDF, en gris (1894×2681 px).
2. Las marcas del eje x (10 … 90°) se ubicaron en x = 494.0, 623.0, 752.0, 880.0, 1004.0, 1132.5, 1261.0, 1390.0,
   1519.0 px y las del eje y (0.1 … 0.7) en y = 1814.5, 1687.5, 1562.0, 1435.0, 1307.0, 1180.5, 1051.5 px. Cada
   píxel se pasa a valor con interpolación lineal entre marcas (x) y con la recta ajustada a las marcas (y); los
   residuos de esa recta son de ±1.3 px.
3. Cada curva es una poligonal: cada tramo se ajustó como recta (mínimos cuadrados totales, con descarte iterativo
   de lo que queda a más de 2.5 desviaciones, para ignorar rótulos) con la tinta a ±10 px del tramo, sin 18 px en
   cada punta ni 45 px junto a la punta de flecha de 90°. Los vértices son la intersección de tramos vecinos; donde
   el giro es < 3° (curvas casi rectas) son el promedio de los dos ajustes en el x del vértice.
4. La curva continua se midió igual y se comparó con los valores del texto (0.3, 0.2, 0.2, 0.8, 1.0): difiere hasta
   0.007 en B (0.199, 0.197, 0.795 y 0.993 en 10°, 30°, 60° y 90°); sus vértices quedan con los valores del texto.
5. Empalmes: las curvas a trazos de 30°, 45° y 60° nacen en 10° (la de 30° en el vértice de la continua, 0.2) y
   llegan a la punta de flecha de 90°, donde las cuatro curvas convergen; se fijó en (90, 1.0), y el ajuste da
   0.993 a 0.996. La de 30° se junta con la continua cerca de 75.5° y sigue sobre ella hasta 90°: ahí se tomó el
   valor de la continua sobre la recta del texto (0.9033), no el medido (0.896). La de 90° es la horizontal en 1.0 (el ajuste da
   1.004 a 0.997).
6. Error: distancia perpendicular de la tinta a la poligonal, en unidades de B (127.55 px = 0.1), contando los
   empalmes y la diferencia de la continua con el texto. Tinta a 8 px o menos de alguna curva: media 0.001,
   p99 0.006, máximo 0.006 (la continua, contra los valores del texto); empalmes hasta 0.007. Se declara 0.007.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from . import _rockmasspy_core as rm
from .stability_graphs import GraphReading, read_stability_graph

# Claves: diferencia de rumbo (°). Pares: (diferencia de buzamiento °, B), en buzamiento creciente.
JOINT_ORIENTATION_CURVES: dict[float, tuple[tuple[float, float], ...]] = {
    0: ((0, 0.3), (10, 0.2), (30, 0.2), (60, 0.8), (90, 1.0)),  # continua: valores del texto
    30: ((10, 0.2), (30.2, 0.394), (45.1, 0.571), (60.6, 0.834), (75.5, 0.8 + 0.2 * 15.5 / 30), (90, 1.0)),  # empalme: sobre la continua
    45: ((10, 0.5), (30.5, 0.597), (45.8, 0.798), (60, 0.856), (76.5, 0.924), (90, 1.0)),
    60: ((10, 0.8), (30.9, 0.82), (45.7, 0.847), (60, 0.896), (76, 0.952), (90, 1.0)),
    90: ((10, 1.0), (90, 1.0)),
}

FACTOR_B_INFO = rm.MethodInfo(
    "Mathews-Potvin1988", rm.Verification.Primary,
    "Potvin (1988) Empirical open stope design in Canada, PhD thesis UBC: Fig. 7.19, p. 201, text pp. 198-200 and "
    "229-231; strike-difference curves digitized by RockMassPy (error <= 0.007 in B)")


def _check_angle(name: str, v: float) -> None:
    if not math.isfinite(v) or not 0 <= v <= 90:
        raise ValueError(f"{name} must be a finite angle in [0, 90] degrees, got {v}")


def _on_curve(pts: tuple[tuple[float, float], ...], d: float) -> float:
    if d <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if d <= x1:
            return y0 + (y1 - y0) * (d - x0) / (x1 - x0)
    return pts[-1][1]


def factor_b(dip_difference_deg: float, strike_difference_deg: float = 0.0) -> float:
    """Factor B de orientación de la junta crítica (Potvin 1988, Fig. 7.19).

    Entre curvas no se interpola: B es el máximo de las curvas con diferencia de rumbo <= la dada (R5), así que
    nunca baja al subir el rumbo. Error de digitalización: 0.007 en B, con empalmes.
    """
    _check_angle("dip_difference_deg", dip_difference_deg)
    _check_angle("strike_difference_deg", strike_difference_deg)
    return max(_on_curve(p, dip_difference_deg) for k, p in JOINT_ORIENTATION_CURVES.items()
               if k <= strike_difference_deg)


@dataclass(frozen=True)
class MathewsResult:
    graph: str
    q_prime: float
    factor_a: float
    factor_b: float
    factor_c: float
    failure_mode: str
    n_prime: float
    hr_m: float
    reading: GraphReading
    warnings: tuple[str, ...]
    methods: tuple[rm.MethodInfo, ...]


def mathews_stability(q_prime: float, hr_m: float, *, ucs_mpa: float, sigma1_mpa: float,
                      dip_difference_deg: float, strike_difference_deg: float = 0.0,
                      failure_mode: str = "gravity", surface_inclination_deg: float | None = None,
                      joint_dip_deg: float | None = None, q_info: rm.MethodInfo | None = None,
                      graph: str = "Mathews-Potvin1988") -> MathewsResult:
    """N′ = Q′·A·B·C y su lectura en el gráfico de estabilidad. `q_info` es el `info` del `q_value` que dio Q′."""
    for name, v in (("q_prime", q_prime), ("hr_m", hr_m)):
        if not math.isfinite(v) or v <= 0:
            raise ValueError(f"{name} must be finite and > 0, got {v}")
    if failure_mode not in ("gravity", "sliding"):
        raise ValueError(f"failure_mode must be 'gravity' or 'sliding', got {failure_mode!r}")
    a = rm.mathews_factor_a(ucs_mpa, sigma1_mpa)
    b = factor_b(dip_difference_deg, strike_difference_deg)
    if failure_mode == "gravity":
        if surface_inclination_deg is None:
            raise ValueError("surface_inclination_deg is required for failure_mode='gravity'")
        c = rm.mathews_factor_c_gravity(surface_inclination_deg)
    else:
        if joint_dip_deg is None:
            raise ValueError("joint_dip_deg is required for failure_mode='sliding'")
        c = rm.mathews_factor_c_sliding(joint_dip_deg)
    n_prime = q_prime * a.value * b * c.value
    reading = read_stability_graph(graph, hr_m, n_prime)
    methods = [reading.info, a.info, FACTOR_B_INFO, c.info]
    if q_info is not None:
        methods.append(q_info)
    uniq: list[rm.MethodInfo] = []
    for m in methods:
        if all((m.method_id, m.source) != (u.method_id, u.source) for u in uniq):
            uniq.append(m)
    return MathewsResult(graph, q_prime, a.value, b, c.value, failure_mode, n_prime, hr_m, reading,
                         reading.warnings, tuple(uniq))
