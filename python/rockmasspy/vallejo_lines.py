"""Líneas RMR′ y Q′ de la cartilla GSI modificada de Vallejo, digitalizadas. [V2], digitalizado.

Fuente: Osinergmin (2017), Anexo A.17, láminas «Correlación GSI modificado y Q′» (pág. física 216 de la guía) y
«… y RMR′» (pág. física 217); la cartilla es de C. Vallejo, 2011. Verificación secundaria [V2]: los valores salen
de leer la figura impresa, no de una tabla del autor. Error declarado: ±0.02 en fracción de la cuadrícula.

Coordenadas: fracciones de la cuadrícula 5×5 de la cartilla. x va de 0 (borde izquierdo de MB) a 1 (borde derecho
de MP); y va de 0 (borde superior de LF) a 1 (borde inferior de T). (x0, y0) es el extremo inferior izquierdo de
la línea y (x1, y1) el superior derecho: los dos extremos visibles en la lámina, cortados al borde de la cuadrícula.

Cómo se digitalizó (páginas renderizadas a 250 dpi con PyMuPDF):
1. Las rayas de la cuadrícula se ubicaron sumando píxeles oscuros por columna y por fila. Bordes medidos (px):
   - RMR′ (pág. 217): columnas MB|B|R|P|MP en x = 917.5, 1065, 1213, 1360.5, 1507.5, 1655;
     filas LF|F|MF|IF|T en y = 1115, 1352, 1587, 1824, 2059.5, 2296.
   - Q′ (pág. 216): columnas en x = 963.5, 1112, 1260.5, 1409, 1557.5, 1705;
     filas en y = 1118, 1355, 1593, 1829.5, 2067.5, 2304.
2. Se borraron las rayas y cada tramo diagonal de cada celda se ajustó como recta (ajuste robusto). Los tramos
   colineales se unieron en una sola línea, se volvió a ajustar con todos sus píxeles (95 % de los píxeles a menos
   de 2 px de la recta) y cada extremo se prolongó mientras hubo tinta, hasta la raya donde termina.
3. Cada rótulo va arriba a la izquierda de su línea; el orden de las líneas coincide con el de los rótulos.
4. Paso a fracciones por tramos: dentro de cada columna y cada fila, lineal entre sus dos rayas; la cartilla de
   la librería dibuja celdas iguales. Las celdas medidas son casi iguales (147.5–148.5 px de ancho, 235–237 px de
   alto), así que la recta en píxeles sigue siendo recta en fracciones.
Los píxeles de cada extremo van en el comentario de cada línea. Una superposición de las rectas sobre la lámina
dio errores menores de 0.005 en fracción.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .gsi_charts import GSI_CHARTS, normalize_cell

VALLEJO_LINES_SOURCE = "digitized from Osinergmin (2017), Annex A.17 (Vallejo chart, 2011)"


@dataclass(frozen=True)
class ChartLine:
    value: float
    x0: float
    y0: float
    x1: float
    y1: float


# shortcut: la línea es un segmento recto entre sus extremos; si una lámina trae líneas quebradas, pasar a polilíneas.
RMR_PRIME_LINES: tuple[ChartLine, ...] = (
    ChartLine(90, 0.000, 0.055, 0.077, 0.000),  # px (917.5, 1179.8)-(974.5, 1115.0)
    ChartLine(85, 0.000, 0.136, 0.201, 0.000),  # px (917.5, 1276.7)-(1065.4, 1115.0)
    ChartLine(80, 0.000, 0.236, 0.309, 0.000),  # px (917.5, 1394.9)-(1146.0, 1115.0)
    ChartLine(75, 0.000, 0.373, 0.432, 0.000),  # px (917.5, 1555.7)-(1236.8, 1115.0)
    ChartLine(70, 0.080, 0.400, 0.558, 0.000),  # px (976.5, 1587.0)-(1329.5, 1115.0)
    ChartLine(65, 0.198, 0.400, 0.691, 0.000),  # px (1063.4, 1587.0)-(1427.3, 1115.0)
    ChartLine(60, 0.200, 0.521, 0.801, 0.000),  # px (1065.0, 1730.3)-(1508.1, 1115.0)
    ChartLine(55, 0.234, 0.600, 0.800, 0.087),  # px (1089.8, 1824.0)-(1507.5, 1218.5)
    ChartLine(50, 0.339, 0.600, 0.800, 0.179),  # px (1168.0, 1824.0)-(1507.5, 1327.5)
    ChartLine(45, 0.400, 0.672, 0.895, 0.200),  # px (1213.0, 1909.3)-(1577.3, 1352.0)
    ChartLine(40, 0.400, 0.784, 0.989, 0.200),  # px (1213.0, 2041.1)-(1646.6, 1352.0)
    ChartLine(35, 0.496, 0.800, 1.000, 0.317),  # px (1283.5, 2059.5)-(1655.0, 1489.5)
    ChartLine(30, 0.600, 0.811, 1.000, 0.441),  # px (1360.5, 2072.0)-(1655.0, 1635.0)
    ChartLine(25, 0.600, 0.893, 1.000, 0.537),  # px (1360.5, 2169.8)-(1655.0, 1749.3)
    ChartLine(20, 0.604, 1.000, 1.000, 0.634),  # px (1363.4, 2296.0)-(1655.0, 1864.0)
    ChartLine(15, 0.716, 1.000, 1.000, 0.743),  # px (1445.9, 2296.0)-(1655.0, 1991.9)
    ChartLine(10, 0.821, 1.000, 1.000, 0.848),  # px (1522.9, 2296.0)-(1655.0, 2115.8)
    ChartLine(5, 0.905, 1.000, 1.000, 0.922),  # px (1584.9, 2296.0)-(1655.0, 2204.2)
)

Q_PRIME_LINES: tuple[ChartLine, ...] = (
    ChartLine(100, 0.000, 0.091, 0.104, 0.000),  # px (963.5, 1225.6)-(1040.5, 1118.0)
    ChartLine(75, 0.000, 0.189, 0.193, 0.000),  # px (963.5, 1341.9)-(1107.2, 1118.0)
    ChartLine(50, 0.000, 0.327, 0.327, 0.000),  # px (963.5, 1505.8)-(1205.9, 1118.0)
    ChartLine(20, 0.056, 0.400, 0.456, 0.000),  # px (1004.8, 1593.0)-(1301.8, 1118.0)
    ChartLine(5, 0.200, 0.400, 0.600, 0.000),  # px (1111.9, 1593.0)-(1409.0, 1118.0)
    ChartLine(3, 0.200, 0.545, 0.744, 0.000),  # px (1112.0, 1764.4)-(1516.0, 1118.0)
    ChartLine(1, 0.299, 0.600, 0.800, 0.098),  # px (1185.8, 1829.5)-(1557.5, 1234.7)
    ChartLine(0.5, 0.400, 0.652, 0.852, 0.200),  # px (1260.5, 1891.3)-(1595.7, 1355.0)
    ChartLine(0.1, 0.400, 0.800, 1.000, 0.201),  # px (1260.3, 2067.5)-(1705.0, 1355.8)
    ChartLine(0.05, 0.544, 0.800, 1.000, 0.344),  # px (1367.1, 2067.5)-(1705.0, 1526.9)
    ChartLine(0.01, 0.600, 0.891, 1.000, 0.491),  # px (1409.0, 2174.8)-(1705.0, 1701.1)
    ChartLine(0.005, 0.640, 1.000, 1.000, 0.665),  # px (1438.8, 2304.0)-(1705.0, 1907.3)
    ChartLine(0.001, 0.812, 1.000, 1.000, 0.838),  # px (1566.1, 2304.0)-(1705.0, 2112.1)
)

_CHART = GSI_CHARTS["GSI-Vallejo-Osinergmin2017"]
# Un tramo más corto que esto dentro de la celda (rozar una esquina) no cuenta como cruce: es la mitad del error.
_MIN_INSIDE = 0.01


def _cell_rect(cell: str) -> tuple[float, float, float, float]:
    code = normalize_cell(cell)
    if code not in _CHART.valid_cells:
        raise ValueError(f"cell {code!r} is not a valid cell of {_CHART.chart_id}; valid cells: {sorted(_CHART.valid_cells)}")
    s, c = code.split("/")
    r = [k for k, _ in _CHART.structures].index(s)
    k = [k for k, _ in _CHART.conditions].index(c)
    ns, nc = len(_CHART.structures), len(_CHART.conditions)
    return k / nc, r / ns, (k + 1) / nc, (r + 1) / ns


def _inside_length(ln: ChartLine, rect) -> float:
    """Largo del tramo de la línea dentro del rectángulo (recorte de Liang-Barsky)."""
    xa, ya, xb, yb = rect
    dx, dy = ln.x1 - ln.x0, ln.y1 - ln.y0
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, ln.x0 - xa), (dx, xb - ln.x0), (-dy, ln.y0 - ya), (dy, yb - ln.y0)):
        if p == 0:
            if q < 0:
                return 0.0
        elif p < 0:
            t0 = max(t0, q / p)
        else:
            t1 = min(t1, q / p)
    return max(0.0, t1 - t0) * math.hypot(dx, dy)


def _side(ln: ChartLine, x: float, y: float) -> float:
    """Distancia con signo del punto a la recta prolongada (positiva arriba a la izquierda)."""
    dx, dy = ln.x1 - ln.x0, ln.y1 - ln.y0
    return (dx * (ln.y0 - y) - dy * (ln.x0 - x)) / math.hypot(dx, dy)


def _range_in(lines, rect, log: bool) -> tuple[float, float]:
    hits = [ln.value for ln in lines if _inside_length(ln, rect) > _MIN_INSIDE]
    if hits:
        return min(hits), max(hits)
    # ninguna línea cruza: se interpola entre las dos vecinas evaluadas en el centro de la celda
    cx, cy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
    d = [(_side(ln, cx, cy), ln.value) for ln in lines]
    above = [t for t in d if t[0] > 0]
    below = [t for t in d if t[0] <= 0]
    if not above or not below:  # fuera de todas las líneas: el valor de la más cercana, sin extrapolar
        v = min(d, key=lambda t: abs(t[0]))[1]
        return v, v
    (da, va), (db, vb) = min(above), max(below)
    f = da / (da - db)
    if log:
        v = 10 ** (math.log10(va) + f * (math.log10(vb) - math.log10(va)))
    else:
        v = va + f * (vb - va)
    return v, v


def rmr_prime_range(cell: str) -> tuple[float, float]:
    """Menor y mayor RMR′ de las líneas que cruzan la celda de la cartilla de Vallejo. [V2], digitalizado.

    Si ninguna línea cruza, devuelve (v, v) con v interpolado entre las dos vecinas en el centro de la celda.
    Lanza ValueError si la celda no existe o la cartilla la marca con raya.
    """
    return _range_in(RMR_PRIME_LINES, _cell_rect(cell), log=False)


def q_prime_range(cell: str) -> tuple[float, float]:
    """Como rmr_prime_range con las líneas Q′; la interpolación va en log10. [V2], digitalizado."""
    return _range_in(Q_PRIME_LINES, _cell_rect(cell), log=True)
