"""Cartillas GSI cualitativas (estructura x condición superficial) y su normalización de celdas.

Una cartilla es un dato: el usuario puede crear su propia `GsiChart` y agregarla a GSI_CHARTS.
Los rótulos están escritos con palabras propias; no se copia el texto de la fuente.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GsiChart:
    chart_id: str
    source: str
    verification: str
    structures: tuple[tuple[str, str], ...]  # de mejor a peor
    conditions: tuple[tuple[str, str], ...]  # de mejor a peor
    valid_cells: frozenset[str]


def normalize_cell(code: str) -> str:
    """' f / r ' -> 'F/R'. Lanza ValueError si no tiene forma X/Y."""
    parts = [p.strip().upper() for p in str(code).split("/")]
    if len(parts) != 2 or not all(parts):
        raise ValueError(f"cell code must look like 'S/C' (e.g. 'F/R'), got {code!r}")
    return "/".join(parts)


_STRUCTURES = (
    ("LF", "slightly fractured"), ("F", "moderately fractured"), ("MF", "very fractured"),
    ("IF", "intensely fractured"), ("T", "crushed"),
)
_CONDITIONS = (
    ("MB", "very good"), ("B", "good"), ("R", "fair"), ("P", "poor"), ("MP", "very poor"),
)
# Celdas que la cartilla marca con raya (no aplican)
_VALLEJO_DASHED = {"LF/MP", "MF/MB", "IF/MB", "IF/B", "T/MB", "T/B", "T/R"}

# Carta clásica de Hoek y Marinos (2000): Hoek, Practical Rock Engineering, cap. 11, Tabla 5 (pre11.pdf, pág. física 13;
# el texto que la introduce está en la 11). Contrastada con la misma carta en gsi2013.pdf (pág. 3, Figura 2): mismas 6 filas
# y mismas 4 celdas N/A, sin diferencias. La fila LAMINATED/SHEARED (LS) sí está en ambas fuentes.
# Celdas N/A: IM/P, IM/VP (roca masiva con superficies pobres no ocurre) y LS/VG, LS/G (lo laminado no tiene buena superficie).
_HM_STRUCTURES = (
    ("IM", "intact or massive"), ("B", "blocky"), ("VB", "very blocky"),
    ("BD", "blocky, disturbed or seamy"), ("D", "disintegrated"), ("LS", "laminated or sheared"),
)
_HM_CONDITIONS = (
    ("VG", "very good"), ("G", "good"), ("F", "fair"), ("P", "poor"), ("VP", "very poor"),
)
_HM_NA = {"IM/P", "IM/VP", "LS/VG", "LS/G"}

GSI_CHARTS = {
    "GSI-Vallejo-Osinergmin2017": GsiChart(
        chart_id="GSI-Vallejo-Osinergmin2017",
        source="Vallejo (2002), chart as reproduced in Osinergmin (2017), Annex A.17 (chart dated 2011)",
        verification="secondary",
        structures=_STRUCTURES,
        conditions=_CONDITIONS,
        valid_cells=frozenset(f"{s}/{c}" for s, _ in _STRUCTURES for c, _ in _CONDITIONS) - _VALLEJO_DASHED,
    ),
    "GSI-Hoek-Marinos": GsiChart(
        chart_id="GSI-Hoek-Marinos",
        source="Hoek, Practical Rock Engineering, ch. 11, GSI chart (after Marinos & Hoek 2000)",
        verification="secondary",
        structures=_HM_STRUCTURES,
        conditions=_HM_CONDITIONS,
        valid_cells=frozenset(f"{s}/{c}" for s, _ in _HM_STRUCTURES for c, _ in _HM_CONDITIONS) - _HM_NA,
    ),
}
