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

GSI_CHARTS = {
    "GSI-Vallejo-Osinergmin2017": GsiChart(
        chart_id="GSI-Vallejo-Osinergmin2017",
        source="Vallejo (2002), chart as reproduced in Osinergmin (2017), Annex A.17 (chart dated 2011)",
        verification="secondary",
        structures=_STRUCTURES,
        conditions=_CONDITIONS,
        valid_cells=frozenset(f"{s}/{c}" for s, _ in _STRUCTURES for c, _ in _CONDITIONS) - _VALLEJO_DASHED,
    ),
}
