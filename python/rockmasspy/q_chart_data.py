"""Tabla ESR y carta de sostenimiento del sistema Q (NGI 2025 y 2015), digitalizada por RockMassPy.

Fuentes: NGI (2025) *Using the Q-system*, Tabla 4-1 (ESR) y Fig. 4-1, pp. 31-32 impresas (35-36 físicas);
NGI (2015, rev. 2022), Tabla 7 y Fig. 7, pp. 34-35 (el ábaco revisado de 2019, resolución R9). El ábaco no tiene
ecuaciones: las fronteras entre categorías son nuestra digitalización, en el plano (log10 Q, log10 De). Los rótulos
de la leyenda y de la tabla ESR están escritos con palabras propias.

Cómo se digitalizó (como `vallejo_lines.py`; el script y las imágenes quedan fuera del repo):
1. Se renderizó a 250 dpi con PyMuPDF: q2025.pdf pág. física 35 (2363×1674 px) y q2015u2022.pdf pág. física 34,
   girada 90° en sentido horario antes de medir (1674×2363 → 2363×1674 px). La lámina de 2015 es una imagen de
   973×660 px dentro del PDF, así que 1 px de la imagen original son unos 1.65 px del render.
2. Las rayas de década se ubicaron sumando píxeles grises por columna y por fila (el borde derecho, negro, aparte).
   Paso a valores: lineal en log10 entre dos rayas de década vecinas.
   - 2025: Q = 0.001 … 1000 en x = 366.5, 632.5, 899.1, 1164.1, 1430.5, 1697.1, 1963.5;
     De = 1, 10, 100 en y = 1278.5, 878.0, 478.0.
   - 2015: x = 374.5, 649.2, 922.5, 1195.3, 1469.7, 1743.5, 2017.0; y = 1255.5, 843.5, 431.7.
3. Las fronteras se separaron por color (el granate de las líneas) y cada una se siguió columna a columna, tomando
   el centro de la tinta. Se quitaron los puntos contaminados por cruces, rayas y rótulos (más de 1.2 px en 2025 o
   2 px en 2015 de su recta local). Cada tramo entre quiebres se ajustó como recta (mínimos cuadrados totales) y
   cada vértice es el cruce de dos tramos vecinos; los extremos son el cruce con el marco o con la otra frontera.
   Las verticales de Q = 40 y Q = 100 se midieron aparte. Los píxeles de cada vértice van en su comentario.
4. Error: distancia perpendicular, en décadas del plano log-log, de cada punto medido de la tinta a la polilínea,
   sin contar los puntos a menos de 20 px de un empalme (allí la tinta de dos líneas se funde). Máximo medido:
   0.005 década en 2025 y 0.008 en 2015. Con los empalmes incluidos sube a 0.017 (2025, el empalme de la frontera
   3|4 con la inferior, a trazos) y 0.008 (2015). La ubicación de las rayas de década agrega unos ±0.002.
5. Las fronteras a trazos (bajo el corte De = 3 y más allá de Q = 400) se digitalizaron como las demás: las
   categorías siguen sus líneas a trazos hasta De = 1 y Q = 1000 (resolución R5). Esas zonas van en `no_data`:
   el rectángulo bajo De = 3 a la izquierda del cruce de la frontera inferior con De = 3 (allí todas las fronteras
   son a trazos) y la franja de Q = 400 a 1000, donde la lámina ya no tiene relleno. Las líneas de energía a trazos
   (E = 500/700/1000 J) no se digitalizan como datos: la energía sale de la leyenda (resolución R17).
6. Marcas: las rayas de espaciamiento (con Sfr sobre la frontera superior, sin Sfr bajo la inferior) se midieron
   por su columna de píxeles negros; caen sobre las líneas de la cuadrícula. Los rótulos de longitud de perno
   (eje derecho) y los de RRS c/c no tienen raya: se toma la línea de la cuadrícula junto a la que están (sus
   centros medidos quedan a menos de 0.015 década de ella).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ._rockmasspy_core import MethodInfo, Verification
from .chart_regions import Region

_ESR = {
    "A": (3.0, 5.0, "temporary mine openings"),
    "B": (2.0, 2.5, "vertical shafts: 2.5 circular, 2.0 rectangular or square"),
    "C": (1.6, 1.6, "permanent mine openings, water tunnels, pilot and large advance headings"),
    "D": (1.3, 1.3, "minor road and railway tunnels, surge chambers, access tunnels, sewers"),
    "E": (1.0, 1.0, "power stations, storage rooms, treatment plants, major road and railway tunnels, portals"),
    "F": (0.8, 0.8, "underground nuclear plants, stations, public and sports facilities, factories"),
    "G": (0.5, 0.5, "very important caverns with a life of about 100 years or no maintenance access"),
}
# Mismos valores en 2025 (Tabla 4-1) y 2015 (Tabla 7); 2015 los escribe como aproximados («ca.»).
ESR_TABLES: dict[str, dict[str, tuple[float, float, str]]] = {"Q-NGI-2025": dict(_ESR), "Q-NGI-2015": dict(_ESR)}

Q_CHART_FRAME = (0.001, 1000.0, 1.0, 100.0)  # Q mínimo, Q máximo, De mínimo, De máximo


@dataclass(frozen=True)
class QChartCategory:
    number: int
    label: str
    shotcrete_mm: tuple[float, float | None] | None
    sfr_energy_j: int | None
    rrs: str | None


@dataclass(frozen=True)
class QChartData:
    edition: str
    info: MethodInfo
    regions: tuple[Region, ...]
    no_data: tuple[Region, ...]
    spacing_with_sfr: tuple[tuple[float, float], ...]
    spacing_without_sfr: tuple[tuple[float, float], ...]
    rrs_spacing: tuple[tuple[float, float], ...]
    bolt_length: tuple[tuple[float, float], ...]
    rrs_specs: dict[str, dict[float, str | None]]
    categories: dict[int, QChartCategory]


def _path(line, a, b):
    """Tramo de la polilínea entre los vértices a y b, en ese sentido."""
    i, j = line.index(a), line.index(b)
    return line[i:j + 1] if i <= j else line[j:i + 1][::-1]


def _ring(*parts):
    pts = [p for part in parts for p in part]
    out = [p for k, p in enumerate(pts) if k == 0 or p != pts[k - 1]]
    return tuple(out[:-1] if out[0] == out[-1] else out)


def _x_at(line, y):
    """x de la polilínea (creciente en x e y) a la altura y."""
    for (x0, y0), (x1, y1) in zip(line, line[1:]):
        if y0 <= y <= y1:
            return x0 if y1 == y0 else x0 + (x1 - x0) * (y - y0) / (y1 - y0)
    raise ValueError("height outside the line")


_BL, _BR, _TR, _TL = (-3.0, 0.0), (3.0, 0.0), (3.0, 2.0), (-3.0, 2.0)


def _regions(up, low, b78, b67, b56, b45, b34, b23):
    """Polígonos 1-9 armados con las fronteras compartidas (la misma topología en 2025 y 2015).

    La superior va del borde izquierdo al superior; la inferior, del borde inferior al derecho; 7|8 y 6|7 empiezan
    en el borde izquierdo; 5|6 y 4|5, en el inferior; 3|4 y 2|3, sobre la inferior; todas terminan en la superior.
    """
    j78, j67, j56, j45, j34, j23 = b78[-1], b67[-1], b56[-1], b45[-1], b34[-1], b23[-1]
    k34, k23 = b34[0], b23[0]
    rings = {
        9: _ring(up, [_TL]),
        8: _ring(b78, _path(up, j78, up[0])),
        7: _ring(b67, _path(up, j67, j78), _path(b78, j78, b78[0])),
        6: _ring([_BL], b56, _path(up, j56, j67), _path(b67, j67, b67[0])),
        5: _ring(b45, _path(up, j45, j56), _path(b56, j56, b56[0])),
        4: _ring(_path(low, low[0], k34), b34, _path(up, j34, j45), _path(b45, j45, b45[0])),
        3: _ring(_path(low, k34, k23), b23, _path(up, j23, j34), _path(b34, j34, k34)),
        2: _ring(_path(low, k23, low[-1]), [_TR], _path(up, up[-1], j23), _path(b23, j23, k23)),
        1: _ring(low, [_BR]),
    }
    return tuple(Region(k, rings[k]) for k in range(1, 10))


def _no_data(low, lq400):
    """Zonas a trazos: bajo De = 3 a la izquierda del cruce de la inferior con De = 3, y de Q = 400 a 1000."""
    l3 = math.log10(3.0)
    q3 = _x_at(low, l3)
    return (Region(1, (_BL, (q3, 0.0), (q3, l3), (-3.0, l3))),
            Region(2, ((lq400, 0.0), _BR, _TR, (lq400, 2.0))))


def _categories(e4, e6, rrs, cat8):
    sfr = "fibre-reinforced shotcrete"
    return {
        1: QChartCategory(1, "no support or spot bolting", None, None, None),
        2: QChartCategory(2, "spot bolting", None, None, None),
        3: QChartCategory(3, f"systematic bolting with {sfr}, 50-60 mm", (50, 60), None, None),
        4: QChartCategory(4, f"{sfr} 60-90 mm with bolting", (60, 90), e4, None),
        5: QChartCategory(5, f"{sfr} 90-120 mm with bolting", (90, 120), 700, None),
        6: QChartCategory(6, f"{sfr} 120-150 mm with sprayed-concrete ribs {rrs[0]} and bolting", (120, 150), e6,
                          rrs[0]),
        7: QChartCategory(7, f"{sfr} over 150 mm with sprayed-concrete ribs {rrs[1]} and bolting (indicative)",
                          (150, 250), 1000, rrs[1]),
        8: QChartCategory(8, cat8, (250, None), 1000, rrs[2]),
        9: QChartCategory(9, "special evaluation (indicative)", None, None, None),
    }


_RRS_2025 = {
    "RRS-A": {5.0: None, 10.0: "Si30/6 Ø16-20", 20.0: "D40/6+4 Ø16-20"},
    "RRS-B": {5.0: "Si35/6 Ø16-20", 10.0: "D45/6+4 Ø16-20", 20.0: "D55/6+4 Ø20"},
    "RRS-C": {5.0: "D40/6+4 Ø16-20", 10.0: "D55/6+4 Ø20", 20.0: None},  # 20 m: evaluación especial
}
_RRS_2015 = {
    "RRS I": {**_RRS_2025["RRS-A"], 20.0: "D40/6+2 Ø16-20"},
    "RRS II": {**_RRS_2025["RRS-B"], 10.0: "D45/6+2 Ø16-20"},
    "RRS III": dict(_RRS_2025["RRS-C"]),
}

# Longitud de perno (eje derecho, ESR = 1): (De, m). Centros medidos de los rótulos, en px (y):
# 2025: 1156.5, 1037.5, 875.0, 764.0, 690.0, 592.0, 483.5; 2015: 1130, 1007, 840, 725, 649, 550, 437.
_BOLT_LENGTH = ((2.0, 1.5), (4.0, 2.4), (10.0, 3.0), (20.0, 5.0), (30.0, 7.0), (50.0, 11.0), (100.0, 20.0))
# RRS c/c: (Q, m) en la raya gruesa de la cuadrícula junto a cada rótulo (px x: 2025 366.5, 526.9, 632.5,
# 792.9, 899.1; 2015 374.5, 540.3, 649.2, 813.4, 922.5).
_RRS_SPACING = ((0.001, 1.0), (0.004, 1.7), (0.01, 2.3), (0.04, 2.9), (0.1, 4.0))

# ---------------------------------------------------------------- 2025 (Fig. 4-1)
# Puntos en (log10 Q, log10 De). Los empalmes _J van una sola vez y los comparten las dos fronteras que se tocan.
_J25_7_8 = (-0.5152, 1.5757)  # px (1027.6, 647.7)
_J25_6_7 = (0.0048, 1.6687)  # px (1165.4, 610.5)
_J25_5_6 = (0.7766, 1.8075)  # px (1371.0, 555.0)
_J25_4_5 = (1.4913, 1.8969)  # px (1561.5, 519.3)
_J25_3_4 = (1.6039, 1.9069)  # px (1591.5, 515.2)
_J25_2_3 = (1.9977, 1.9282)  # px (1696.5, 506.7)
_J25_LOW_3_4 = (-0.561, 0.1641)  # px (1015.4, 1212.8)
_J25_LOW_2_3 = (1.438, 0.905)  # px (1547.3, 916.1)
_B25_UPPER = (
    (-3.0, 1.1296),  # px (366.5, 826.1)
    _J25_7_8,
    _J25_6_7,
    _J25_5_6,
    (1.0604, 1.8585),  # px (1446.6, 534.6)
    _J25_4_5,
    _J25_3_4,
    _J25_2_3,
    (2.9671, 2.0),  # px (1954.7, 478.0)
)
_B25_LOWER = (
    (-1.0288, 0.0),  # px (891.4, 1278.5)
    _J25_LOW_3_4,
    (0.5252, 0.5609),  # px (1304.0, 1053.8)
    (1.0543, 0.7636),  # px (1445.0, 972.7)
    _J25_LOW_2_3,
    (3.0, 1.4807),  # px (1963.5, 685.7)
)
_B25_7_8 = (
    (-3.0, 0.6002),  # px (366.5, 1038.1)
    (-2.4522, 0.8275),  # px (512.2, 947.1)
    (-2.0121, 0.9952),  # px (629.3, 879.9)
    (-1.3977, 1.2185),  # px (793.1, 790.6)
    (-1.0081, 1.3728),  # px (896.9, 728.9)
    _J25_7_8,
)
_B25_6_7 = (
    (-3.0, 0.0142),  # px (366.5, 1272.8)
    (-2.406, 0.2728),  # px (524.5, 1169.2)
    (-1.9969, 0.4841),  # px (633.3, 1084.6)
    (-1.7434, 0.5989),  # px (700.9, 1038.6)
    (-1.0246, 0.9902),  # px (892.6, 881.9)
    (-0.8508, 1.0916),  # px (938.6, 841.4)
    (-0.568, 1.2789),  # px (1013.6, 766.4)
    _J25_6_7,
)
_B25_5_6 = (
    (-2.2445, 0.0),  # px (567.5, 1278.5)
    (-1.9991, 0.1163),  # px (632.7, 1231.9)
    (-1.6623, 0.2999),  # px (722.5, 1158.4)
    (-1.4078, 0.449),  # px (790.4, 1098.7)
    (-0.4023, 1.0691),  # px (1057.5, 850.4)
    (-0.0071, 1.3418),  # px (1162.2, 741.3)
    (0.4895, 1.6496),  # px (1294.5, 618.2)
    _J25_5_6,
)
_B25_4_5 = (
    (-1.6457, 0.0),  # px (727.0, 1278.5)
    (-1.3893, 0.1174),  # px (795.3, 1231.5)
    (-0.9969, 0.3257),  # px (899.9, 1148.0)
    (-0.4168, 0.6963),  # px (1053.7, 999.6)
    (0.662, 1.4286),  # px (1340.4, 706.6)
    (1.122, 1.7052),  # px (1463.0, 595.9)
    _J25_4_5,
)
_B25_3_4 = (
    _J25_LOW_3_4,
    (-0.3428, 0.3482),  # px (1073.3, 1139.0)
    (-0.0002, 0.6261),  # px (1164.0, 1027.8)
    (0.6994, 1.1403),  # px (1350.4, 821.9)
    (0.9425, 1.309),  # px (1415.2, 754.4)
    (1.3158, 1.5454),  # px (1514.7, 659.8)
    (1.4022, 1.6081),  # px (1537.7, 634.8)
    (1.6039, 1.7425),  # px (1591.5, 581.0)
    _J25_3_4,
)
_B25_2_3 = (
    _J25_LOW_2_3,
    (1.9977, 1.6263),  # px (1696.5, 627.5)
    _J25_2_3,
)

Q_CHARTS: dict[str, QChartData] = {}
Q_CHARTS["Q-NGI-2025"] = QChartData(
    edition="Q-NGI-2025",
    info=MethodInfo("Q-NGI-2025-chart", Verification.Primary,
                    "NGI (2025) Using the Q-system, Fig. 4-1, pp. 31-32; boundaries digitized by RockMassPy "
                    "(error <= 0.017 decade)"),
    regions=_regions(_B25_UPPER, _B25_LOWER, _B25_7_8, _B25_6_7, _B25_5_6, _B25_4_5, _B25_3_4, _B25_2_3),
    no_data=_no_data(_B25_LOWER, 2.6006),  # Q = 400 en x = 1857.1 px
    # rayas sobre la frontera superior, px x: 632.5, 793.0, 899.0, 1059.0, 1165.0, 1325.0, 1431.0, 1511.0
    spacing_with_sfr=((0.01, 1.0), (0.04, 1.2), (0.0999, 1.3), (0.401, 1.5), (1.01, 1.7), (4.02, 2.1), (10.0, 2.3),
                      (20.0, 2.5)),
    # rayas bajo la frontera inferior, px x: 1325.0, 1430.1, 1591.6, 1697.0
    spacing_without_sfr=((4.02, 1.6), (9.97, 2.0), (40.2, 3.0), (99.9, 4.0)),
    rrs_spacing=_RRS_SPACING,
    bolt_length=_BOLT_LENGTH,
    rrs_specs=_RRS_2025,
    categories=_categories(700, 1000, ("RRS-A", "RRS-B", "RRS-C"),
                           "fibre-reinforced shotcrete over 250 mm with double-layer sprayed-concrete ribs RRS-C "
                           "and bolting (indicative)"),
)

# ---------------------------------------------------------------- 2015, rev. 2022 (Fig. 7, ábaco de 2019)
_J15_7_8 = (-0.5074, 1.5765)  # px (1056.9, 606.1)
_J15_6_7 = (0.0049, 1.6681)  # px (1196.7, 568.4)
_J15_5_6 = (0.7719, 1.806)  # px (1407.1, 511.6)
_J15_4_5 = (1.4894, 1.8956)  # px (1603.7, 474.7)
_J15_3_4 = (1.6019, 1.9054)  # px (1634.5, 470.7)
_J15_2_3 = (2.0, 1.9282)  # px (1743.5, 461.3)
_J15_LOW_3_4 = (-0.5701, 0.1633)  # px (1039.8, 1188.2)
_J15_LOW_2_3 = (1.434, 0.9015)  # px (1588.5, 884.1)
_B15_UPPER = (
    (-3.0, 1.1295),  # px (374.5, 790.2)
    _J15_7_8,
    _J15_6_7,
    _J15_5_6,
    (1.0658, 1.8588),  # px (1487.7, 489.9)
    _J15_4_5,
    _J15_3_4,
    _J15_2_3,
    (2.9945, 2.0),  # px (2015.5, 431.7)
)
_B15_LOWER = (
    (-1.0289, 0.0),  # px (914.6, 1255.5)
    _J15_LOW_3_4,
    (-0.1935, 0.2974),  # px (1142.5, 1133.0)
    _J15_LOW_2_3,
    (2.2393, 1.2002),  # px (1809.0, 761.1)
    (3.0, 1.4794),  # px (2017.0, 646.1)
)
_B15_7_8 = (
    (-3.0, 0.6002),  # px (374.5, 1008.2)
    (-2.4155, 0.8437),  # px (535.1, 907.9)
    (-2.1334, 0.9502),  # px (612.6, 864.0)
    (-1.2909, 1.2588),  # px (843.0, 736.9)
    _J15_7_8,
)
_B15_6_7 = (
    (-3.0, 0.0149),  # px (374.5, 1249.3)
    (-2.4118, 0.2722),  # px (536.1, 1143.4)
    (-2.0087, 0.4802),  # px (646.8, 1057.6)
    (-1.7524, 0.596),  # px (716.9, 1010.0)
    (-1.2394, 0.8735),  # px (857.1, 895.6)
    (-0.8352, 1.0969),  # px (967.5, 803.6)
    _J15_6_7,
)
_B15_5_6 = (
    (-2.2421, 0.0),  # px (582.7, 1255.5)
    (-1.9642, 0.1386),  # px (659.0, 1198.4)
    (-1.6471, 0.3104),  # px (745.6, 1127.6)
    (-1.3801, 0.4673),  # px (818.6, 1063.0)
    (-0.4178, 1.06),  # px (1081.3, 818.8)
    (0.022, 1.36),  # px (1201.3, 695.2)
    (0.4777, 1.6418),  # px (1326.4, 579.2)
    _J15_5_6,
)
_B15_4_5 = (
    (-1.6503, 0.0),  # px (744.8, 1255.5)
    (-1.3897, 0.1186),  # px (816.0, 1206.6)
    (-0.9884, 0.3314),  # px (925.7, 1119.0)
    (-0.425, 0.6918),  # px (1079.4, 970.5)
    (0.6806, 1.4406),  # px (1382.1, 662.1)
    (1.1207, 1.704),  # px (1502.8, 553.6)
    _J15_4_5,
)
_B15_3_4 = (
    _J15_LOW_3_4,
    (-0.0038, 0.6242),  # px (1194.3, 998.3)
    (0.6773, 1.1251),  # px (1381.2, 792.0)
    (0.7867, 1.2013),  # px (1411.2, 760.6)
    (1.6019, 1.7391),  # px (1634.5, 539.1)
    _J15_3_4,
)
_B15_2_3 = (
    _J15_LOW_2_3,
    (2.0, 1.628),  # px (1743.5, 584.9)
    _J15_2_3,
)

Q_CHARTS["Q-NGI-2015"] = QChartData(
    edition="Q-NGI-2015",
    info=MethodInfo("Q-NGI-2015-chart", Verification.Primary,
                    "NGI (2015, rev. 2022) Using the Q-system, Fig. 7, pp. 34-35; boundaries digitized by "
                    "RockMassPy (error <= 0.008 decade)"),
    regions=_regions(_B15_UPPER, _B15_LOWER, _B15_7_8, _B15_6_7, _B15_5_6, _B15_4_5, _B15_3_4, _B15_2_3),
    no_data=_no_data(_B15_LOWER, 2.6015),  # Q = 400 en x = 1908.0 px
    # px x: 648.5, 814.5, 923.5, 1088.0, 1195.5, 1360.6, 1470.5, 1551.7
    spacing_with_sfr=((0.00994, 1.0), (0.0403, 1.2), (0.101, 1.3), (0.404, 1.5), (1.0, 1.7), (4.0, 2.1),
                      (10.1, 2.3), (19.9, 2.5)),
    # px x: 1360.5, 1469.6, 1635.4, 1743.5
    spacing_without_sfr=((4.0, 1.6), (9.99, 2.0), (40.3, 3.0), (100.0, 4.0)),
    rrs_spacing=_RRS_SPACING,
    bolt_length=_BOLT_LENGTH,
    rrs_specs=_RRS_2015,
    categories=_categories(500, 700, ("RRS I", "RRS II", "RRS III"),
                           "cast concrete lining, or fibre-reinforced shotcrete over 250 mm with sprayed-concrete "
                           "ribs RRS III and bolting (indicative)"),
)
