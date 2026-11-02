"""Gráficos de estabilidad digitalizados por RockMassPy: Potvin (1988) y Laubscher (1994).

Fuentes:
- Potvin (1988) *Empirical open stope design in Canada*, tesis PhD, UBC, Fig. 7.22, p. 206 impresa (228 física):
  gráfico de estabilidad modificado, N′ logarítmico de 0.1 a 1000 contra radio hidráulico lineal de 0 a 25 m.
- Laubscher (1994) *Cave mining - the state of the art*, J. SAIMM 94(10) 279-293, Fig. 1, p. 282 impresa (4 física):
  MRMR de 0 a 100 contra radio hidráulico de 0 a 80 m.

Ninguna de las dos láminas tiene ecuación: las dos fronteras de cada una (estable|transición y
transición|hundimiento) son nuestra digitalización. No se digitalizaron los casos dibujados ni se copiaron sus
rótulos (resolución R28). El plano del gráfico es (HR, log10 N′) en Potvin y (HR, MRMR) en Laubscher.

Cómo se digitalizó (como `q_chart_data.py`; el script y las imágenes quedan fuera del repo):
1. Se renderizó a 250 dpi con PyMuPDF, en gris: la tesis de Potvin, pág. física 228 (1913×2696 px; es un escaneo
   de unos 300 dpi), y laub_v094n10p279.pdf, pág. física 4 (1938×2796 px).
2. Las rayas de la cuadrícula se ubicaron sumando píxeles oscuros por columna y por fila, y cada raya se ajustó
   como recta (mínimos cuadrados con descarte de cruces) para medir el giro del escaneo:
   - Potvin: HR = 0, 5 … 25 en x = 309.0, 597.5, 881.0, 1172.4, 1459.5, 1748.4; N′ = 1000, 100, 10, 1, 0.1 en
     y = 580.6, 922.5, 1264.4, 1603.5, 1939.5. Giro: las horizontales caen entre +0.01° y +0.10° y las verticales
     entre −0.04° y +0.04°, con ondulaciones de ±1.5 px (no es un giro rígido).
   - Laubscher: HR = 0, 10 … 80 en x = 275.0, 382.9, 490.5, 599.5, 707.5, 815.0, 924.0, 1031.4, 1138.0;
     MRMR = 100, 90 … 0 en y = 258.9, 345.0, 432.0, 519.5, 606.1, 692.5, 779.5, 865.5, 953.0, 1039.8, 1125.5.
     Giro: las horizontales caen −0.08° de media; las verticales interiores, +0.20° a +0.27°, y las del marco
     (0 y 80 m) solo +0.03° y +0.07°: el papel cuadriculado está cizallado unos 0.16° respecto del marco.
   Corrección del giro: cada píxel se pasa a valor con las rectas ajustadas, no con posiciones fijas. La x sale
   de las dos rayas verticales vecinas evaluadas en la fila del píxel, y la y, de las dos horizontales vecinas
   evaluadas en su columna. El paso es lineal entre rayas vecinas (en log10 para N′). Con eso el giro y la
   cizalla quedan absorbidos.
3. Cada frontera se trazó siguiendo el centro de la tinta. Primero se enmascararon todas las rayas, mayores y
   menores (±4 px en Potvin; ±3 px en Laubscher y ±4.5 px en sus rayas gruesas). Luego se borraron los componentes
   chicos: los puntos del relleno de la banda en Potvin (< 40 px) y las motas en Laubscher (< 8 px). La tinta se
   barrió por columnas donde la curva es tendida y por filas donde es empinada. En Potvin el relleno toca la línea
   por dentro, así que el centro se mide desde el borde limpio (el del lado estable en la frontera superior y el
   del lado de hundimiento en la inferior) más media cuerda de referencia (percentil 25 de las cuerdas vecinas).
   En Laubscher, sin relleno, es el punto medio de la cuerda, o el borde libre más media cuerda mediana si una
   punta toca una raya. Se quitaron:
   - las astillas de rayas (< 3 px);
   - los puntos a más de 1.2 px de una parábola local: rótulos, casos dibujados y relleno pegado.
   Quedaron 1114 y 928 puntos (Potvin, superior e inferior) y 371 y 442 (Laubscher). La traza se suavizó con una
   regresión lineal local y se simplificó con Douglas-Peucker (tolerancia 0.005 paso de cuadrícula). Los extremos
   son el cruce con el marco de la recta ajustada al final de la tinta. Los píxeles de cada vértice van en su
   comentario. Los tramos de tinta tapados por rayas (a lo más 0.32 paso seguido) se revisaron en la
   superposición.
4. Dónde pasan a trazos las fronteras de Potvin: la superior es continua hasta HR = 13.67 m (px 1095, 926) y la
   inferior hasta HR = 13.48 m (px 1084, 1052). La franja `no_data` va de HR = 13.48 m (el menor de los dos) hasta
   25 m, a toda altura. Las partes a trazos se digitalizaron igual que las continuas, trazo por trazo.
5. Empalmes con el marco:
   - Potvin: las dos fronteras tocan el borde inferior (N′ = 0.1) con tinta hasta él, en HR = 1.36 y 3.12 m.
     Junto al borde derecho la tinta acaba antes: el último trazo está en HR = 24.2 m (superior) y 23.8 m
     (inferior). El extremo en HR = 25 m sale de una recta ajustada a la tinta desde HR = 21.5 m. La Fig. 8.3
     (p. 234 / 256), cuyos trazos sí llegan al marco, da con el mismo ajuste extremos a 0.008 y 0.007 paso de los
     nuestros, y a 0.005 y 0.014 paso si se extrapola solo su último trazo.
   - Laubscher: la superior nace en el borde izquierdo (MRMR = 11.6) y las dos acaban en el borde superior
     (HR = 59.7 y 74.3 m). La inferior corta el borde inferior en HR = 0.13 m, a 0.013 paso de la esquina; se deja
     el cruce medido, sin llevarlo a la esquina.
6. Error: distancia perpendicular de cada punto de tinta a la polilínea, en pasos de cuadrícula (resolución R26;
   Potvin: 5 m en x y 1 década en y; Laubscher: 10 m y 10 puntos), con los empalmes incluidos:
   - Potvin: 0.007 paso sobre la tinta, contando los empalmes con el borde inferior. Con el empalme derecho
     (comparado con la Fig. 8.3), 0.014. Se declara 0.014.
   - Laubscher: 0.009 paso, con los empalmes.
   Aparte, la ubicación de la cuadrícula: con el paso lineal entre rayas mayores, las rayas menores de Potvin
   quedan a menos de 0.004 década de su valor. En Laubscher quedan a menos de 0.008 paso en y y de 0.016 paso en
   x; este máximo está en las celdas de 0–10 m y 70–80 m, junto al marco, y donde pasan las fronteras llega a
   0.011 paso.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ._rockmasspy_core import MethodInfo, Verification
from .chart_regions import Region, locate

Point = tuple[float, float]
Line = tuple[Point, ...]


@dataclass(frozen=True)
class StabilityGraph:
    graph_id: str
    info: MethodInfo
    x_name: str
    y_name: str
    x_range: tuple[float, float]
    y_range: tuple[float, float]
    y_log: bool
    boundaries: tuple[Line, Line]  # estable|transición y transición|hundimiento, en el plano del gráfico
    regions: tuple[Region, ...]
    no_data: tuple[Region, ...]
    zone_labels: dict[int, str]


@dataclass(frozen=True)
class GraphReading:
    graph_id: str
    x: float
    y: float
    zone: int
    zone_label: str
    extrapolated: bool
    warnings: tuple[str, ...]
    info: MethodInfo


def _ring(*parts):
    pts = [p for part in parts for p in part]
    out = [p for k, p in enumerate(pts) if k == 0 or p != pts[k - 1]]
    return tuple(out[:-1] if out[0] == out[-1] else out)


def _regions(up: Line, low: Line, frame: tuple[float, float, float, float]) -> tuple[Region, ...]:
    """Zonas 1-3 armadas con las dos fronteras y el marco. Cada frontera va de un borde del marco a otro."""
    x0, x1, y0, y1 = frame
    corners = {1: (x1, y0), 2: (x1, y1), 3: (x0, y1), 0: (x0, y0)}

    def s(p):  # posición sobre el marco en sentido antihorario desde la esquina inferior izquierda, en [0, 4)
        x, y = p
        if y == y0:
            return (x - x0) / (x1 - x0)
        if x == x1:
            return 1 + (y - y0) / (y1 - y0)
        if y == y1:
            return 2 + (x1 - x) / (x1 - x0)
        if x == x0:
            return 3 + (y1 - y) / (y1 - y0)
        raise ValueError(f"boundary end {p} is not on the graph frame")

    def walk(a, b):  # esquinas del marco entre a y b, en sentido antihorario
        sa, sb = s(a), s(b)
        if sb <= sa:
            sb += 4
        return [corners[k % 4] for k in range(1, 8) if sa < k < sb]

    return (
        Region(1, _ring(up, walk(up[-1], up[0]))),
        Region(2, _ring(low, walk(low[-1], up[-1]), up[::-1], walk(up[0], low[0]))),
        Region(3, _ring([low[0]], walk(low[0], low[-1]), low[::-1])),
    )


# ---------------------------------------------------------------- Potvin (1988), Fig. 7.22
# Puntos en (HR m, log10 N′).
_POTVIN_UPPER = (  # estable | transición
    (1.3607, -1.0),  # px (387.3, 1937.5)
    (1.7946, -0.5861),  # px (412.4, 1799.2)
    (2.2401, -0.25),  # px (438.1, 1686.9)
    (2.6622, 0.0198),  # px (462.4, 1596.6)
    (3.1946, 0.2607),  # px (493.1, 1514.9)
    (3.7719, 0.4904),  # px (526.4, 1436.9)
    (4.4607, 0.708),  # px (566.2, 1363.1)
    (5.1539, 0.8733),  # px (606.0, 1307.0)
    (6.0865, 1.0357),  # px (659.0, 1251.9)
    (8.1328, 1.3286),  # px (775.1, 1151.9)
    (10.3916, 1.6105),  # px (903.9, 1055.7)
    (12.4718, 1.8551),  # px (1025.0, 972.2)
    (13.6059, 1.9747),  # px (1091.1, 931.3), fin de la línea continua
    (14.0866, 2.0121),  # px (1119.1, 918.5), primer trazo
    (14.3402, 2.0461),  # px (1133.9, 906.9)
    (17.4351, 2.3209),  # px (1312.0, 813.0)
    (18.3928, 2.3942),  # px (1367.0, 788.0)
    (19.2816, 2.4469),  # px (1418.0, 770.0)
    (19.6649, 2.4849),  # px (1440.0, 757.0)
    (20.538, 2.5315),  # px (1490.3, 741.1)
    (20.8812, 2.5664),  # px (1510.1, 729.2)
    (21.8161, 2.6186),  # px (1564.0, 711.3)
    (22.2528, 2.651),  # px (1589.2, 700.3)
    (22.841, 2.6705),  # px (1623.1, 693.6)
    (23.2059, 2.7086),  # px (1644.1, 680.6)
    (24.1734, 2.754),  # px (1699.9, 665.1), último trazo
    (25.0, 2.805),  # px (1747.6, 647.7), extrapolado (empalme 5)
)
_POTVIN_LOWER = (  # transición | hundimiento
    (3.1158, -1.0),  # px (488.4, 1937.7)
    (3.697, -0.5071),  # px (521.9, 1772.9)
    (3.9856, -0.3211),  # px (538.6, 1710.8)
    (4.465, -0.0612),  # px (566.2, 1623.9)
    (5.0841, 0.2164),  # px (601.9, 1530.0)
    (5.6491, 0.4257),  # px (634.0, 1458.9)
    (6.3064, 0.6148),  # px (671.4, 1394.8)
    (6.932, 0.759),  # px (706.9, 1345.9)
    (7.6727, 0.8931),  # px (749.0, 1300.5)
    (8.8567, 1.0717),  # px (816.2, 1239.8)
    (11.0815, 1.3532),  # px (944.0, 1143.7)
    (13.0885, 1.5827),  # px (1060.9, 1065.3)
    (13.2618, 1.6244),  # px (1071.0, 1051.1), cerca del fin de la línea continua
    (14.7558, 1.7469),  # px (1158.0, 1009.3)
    (15.2573, 1.8045),  # px (1187.0, 989.6)
    (15.691, 1.8289),  # px (1211.9, 981.3)
    (18.3061, 2.0695),  # px (1362.0, 899.1)
    (18.6916, 2.0916),  # px (1384.2, 891.5)
    (21.8832, 2.327),  # px (1567.9, 811.1)
    (22.1081, 2.3332),  # px (1580.8, 809.0)
    (25.0, 2.5042),  # px (1747.6, 750.6), extrapolado (empalme 5)
)
_POTVIN_FRAME = (0.0, 25.0, -1.0, 3.0)
_POTVIN_DASHED_FROM = 13.48  # HR donde la frontera inferior pasa a trazos, px (1084, 1052)

# ---------------------------------------------------------------- Laubscher (1994), Fig. 1
# Puntos en (HR m, MRMR).
_LAUBSCHER_UPPER = (  # estable | transicional
    (0.0, 11.639),  # px (275.3, 1025.5)
    (3.133, 21.632),  # px (309.1, 939.0)
    (5.124, 27.474),  # px (330.5, 888.0)
    (5.743, 29.071),  # px (337.2, 874.1)
    (6.807, 32.423),  # px (348.6, 845.0)
    (9.075, 38.564),  # px (372.8, 792.0)
    (9.495, 39.361),  # px (377.3, 785.1)
    (10.596, 42.366),  # px (389.1, 759.1)
    (10.885, 42.956),  # px (392.2, 753.9)
    (11.39, 44.459),  # px (397.7, 740.9)
    (11.686, 44.914),  # px (400.9, 737.0)
    (13.64, 49.408),  # px (421.8, 698.0)
    (15.615, 53.468),  # px (443.1, 662.9)
    (17.297, 56.356),  # px (461.1, 638.0)
    (19.291, 59.488),  # px (482.6, 611.0)
    (20.504, 61.101),  # px (495.6, 597.0)
    (21.355, 62.382),  # px (504.8, 585.9)
    (21.796, 62.819),  # px (509.6, 582.1)
    (22.99, 64.441),  # px (522.5, 568.0)
    (25.572, 67.55),  # px (550.4, 541.0)
    (34.991, 78.419),  # px (652.0, 445.9)
    (37.506, 80.984),  # px (679.0, 423.5)
    (38.801, 82.434),  # px (692.9, 410.9)
    (43.644, 87.12),  # px (745.1, 370.1)
    (47.532, 90.556),  # px (787.1, 340.2)
    (51.147, 93.579),  # px (826.1, 314.2)
    (54.837, 96.516),  # px (865.9, 288.9)
    (59.657, 100.0),  # px (917.9, 258.9)
)
_LAUBSCHER_LOWER = (  # transicional | hundimiento
    (0.13, 0.0),  # px (276.8, 1126.0)
    (3.029, 7.632),  # px (308.2, 1060.0)
    (7.615, 19.11),  # px (357.6, 960.9)
    (12.813, 31.599),  # px (413.5, 852.0)
    (15.233, 37.03),  # px (439.5, 805.2)
    (18.498, 43.637),  # px (474.6, 748.0)
    (21.318, 48.807),  # px (505.0, 703.0)
    (23.746, 52.755),  # px (531.2, 668.9)
    (26.279, 56.455),  # px (558.5, 637.0)
    (27.856, 58.538),  # px (575.5, 619.0)
    (29.516, 60.508),  # px (593.5, 602.0)
    (33.654, 65.162),  # px (638.0, 561.5)
    (38.857, 70.456),  # px (694.0, 515.5)
    (43.137, 74.429),  # px (740.1, 480.7)
    (43.675, 74.811),  # px (745.9, 477.3)
    (44.328, 75.488),  # px (752.9, 471.4)
    (45.541, 76.499),  # px (766.0, 462.5)
    (47.569, 78.393),  # px (787.9, 445.9)
    (48.961, 79.424),  # px (802.9, 436.8)
    (50.546, 80.892),  # px (820.0, 424.0)
    (51.478, 81.568),  # px (830.1, 418.1)
    (52.409, 82.478),  # px (840.1, 410.2)
    (57.691, 86.85),  # px (897.1, 372.2)
    (58.319, 87.463),  # px (903.9, 366.9)
    (71.083, 97.633),  # px (1041.1, 279.1)
    (74.3, 100.0),  # px (1075.7, 258.7)
)
_LAUBSCHER_FRAME = (0.0, 80.0, 0.0, 100.0)

STABILITY_GRAPHS: dict[str, StabilityGraph] = {
    "Mathews-Potvin1988": StabilityGraph(
        graph_id="Mathews-Potvin1988",
        info=MethodInfo("Mathews-Potvin1988", Verification.Primary,
                        "Potvin (1988) Empirical open stope design in Canada, PhD thesis UBC, Fig. 7.22, p. 206; "
                        "boundaries digitized by RockMassPy (error <= 0.014 grid cell)"),
        x_name="hydraulic radius",
        y_name="N'",
        x_range=(0.0, 25.0),
        y_range=(0.1, 1000.0),
        y_log=True,
        boundaries=(_POTVIN_UPPER, _POTVIN_LOWER),
        regions=_regions(_POTVIN_UPPER, _POTVIN_LOWER, _POTVIN_FRAME),
        no_data=(Region(1, ((_POTVIN_DASHED_FROM, -1.0), (25.0, -1.0), (25.0, 3.0), (_POTVIN_DASHED_FROM, 3.0))),),
        zone_labels={1: "stable", 2: "transition", 3: "caved"},
    ),
    "Laubscher1994-stability": StabilityGraph(
        graph_id="Laubscher1994-stability",
        info=MethodInfo("Laubscher1994-stability", Verification.Primary,
                        "Laubscher (1994) Cave mining - the state of the art, J. SAIMM 94(10) 279-293, Fig. 1, "
                        "p. 282; boundaries digitized by RockMassPy (error <= 0.009 grid cell)"),
        x_name="hydraulic radius",
        y_name="MRMR",
        x_range=(0.0, 80.0),
        y_range=(0.0, 100.0),
        y_log=False,
        boundaries=(_LAUBSCHER_UPPER, _LAUBSCHER_LOWER),
        regions=_regions(_LAUBSCHER_UPPER, _LAUBSCHER_LOWER, _LAUBSCHER_FRAME),
        no_data=(),
        zone_labels={1: "stable", 2: "transitional", 3: "caving"},
    ),
}


def read_stability_graph(graph_id: str, x: float, y: float) -> GraphReading:
    """Zona del punto (x, y) en el gráfico; fuera del marco se lee del lado menos favorable, con aviso (R8)."""
    g = STABILITY_GRAPHS.get(graph_id)
    if g is None:
        raise ValueError(f"unknown stability graph {graph_id!r}; available: {', '.join(STABILITY_GRAPHS)}")
    if not math.isfinite(x) or x <= 0:
        raise ValueError(f"{g.x_name} must be finite and > 0, got {x}")
    if not math.isfinite(y) or (y <= 0 if g.y_log else y < 0):
        raise ValueError(f"{g.y_name} must be finite and {'> 0' if g.y_log else '>= 0'}, got {y}")
    (_, x_max), (y_min, y_max) = g.x_range, g.y_range
    worst = g.zone_labels[3]
    warns: list[str] = []
    zone = None
    if y > y_max:
        warns.append(f"{g.y_name} above the graph ({y_max:g}); read at {y_max:g}")
        y = y_max
    if y < y_min:
        warns.append(f"{g.y_name} below the graph ({y_min:g}): taken as {worst}")
        zone = 3
    if x > x_max:
        warns.append(f"{g.x_name} beyond the graph ({x_max:g} m): taken as {worst}")
        zone = 3
    extrapolated = False
    if zone is None:
        py = math.log10(y) if g.y_log else y
        zone = locate(x, py, g.regions)
        if zone is None:  # no debería pasar: las regiones cubren todo el marco
            raise RuntimeError(f"point ({x}, {y}) not covered by the regions of {graph_id}")
        extrapolated = locate(x, py, g.no_data) is not None
        if extrapolated:
            warns.append("point where the graph boundaries are dashed (extrapolated)")
    return GraphReading(graph_id, x, y, zone, g.zone_labels[zone], extrapolated, tuple(warns), g.info)
