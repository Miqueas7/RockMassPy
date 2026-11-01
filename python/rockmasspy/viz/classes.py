"""Histograma de valores por clase de una RangeTable (una barra por clase, regla del límite incluida)."""

from __future__ import annotations

import math
from collections.abc import Sequence

from ..range_table import RangeTable
from ..support import SupportCatalog
from .style import Style, footer, new_figure, support_color, text

_NEUTRAL = "#9E9E9E"


def plot_class_histogram(values: Sequence[float], table: RangeTable, *, catalog: SupportCatalog | None = None,
                         style: Style = Style()):
    """Cuenta los valores por clase con `lookup`; los que caen fuera de toda clase se anotan aparte."""
    for i, v in enumerate(values):
        if not math.isfinite(v):
            raise ValueError(f"values[{i}] must be finite, got {v!r}")
    classes = sorted(table.classes, key=lambda c: c.lo)
    counts = {c.label: 0 for c in classes}
    outside = 0
    for v in values:
        try:
            counts[table.lookup(v).label] += 1
        except ValueError:
            outside += 1

    rank, n = {}, 0
    if catalog is not None:
        ordered = catalog.ordered()
        n = len(ordered)
        rank = {t.code: i + 1 for i, t in enumerate(ordered)}  # el color sale de la posición, como en la cartilla
    colors = [support_color(rank[c.support], n, style) if c.support in rank else _NEUTRAL for c in classes]

    fig = new_figure(style)
    ax = fig.add_axes([0.1, 0.14, 0.85, 0.76])
    ax.bar([c.label for c in classes], [counts[c.label] for c in classes], color=colors, edgecolor="0.3")
    ax.set_ylabel(text("count_axis", style.lang), fontsize=style.font_size)
    ax.set_title(text("class_hist_title", style.lang), fontsize=style.font_size + 3, fontweight="bold")
    ax.tick_params(labelsize=style.font_size - 1)
    ax.text(0.98, 0.95, f"{text('outside_classes', style.lang)}: {outside}", transform=ax.transAxes, ha="right",
            va="top", fontsize=style.font_size, bbox=dict(boxstyle="round", facecolor="white", edgecolor="0.5"))
    footer(fig, table.base_edition, style)
    return fig
