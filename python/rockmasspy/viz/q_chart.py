"""Carta de sostenimiento del sistema Q con los tramos encima.

Solo categorías, colores y marcadores: nunca se rotula un id_tramo ni otro identificador (Foco 5).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from ..batch import TramoResult
from ..q_chart_data import Q_CHART_FRAME, Q_CHARTS
from ._label import _label_point
from .maps import _MARCA_SIN_CLASE, _MARCADORES
from .style import Style, _ink, footer, new_figure, support_color, text

_FUENTE = {"Q-NGI-2025": "NGI (2025), Fig. 4-1", "Q-NGI-2015": "NGI (2015), Fig. 7"}
_N_CAT = 9


def plot_q_chart(edition: str = "Q-NGI-2025", *, results: Sequence[TramoResult] | None = None,
                 points: Sequence[tuple[float, float]] = (), style: Style = Style()):
    """Carta Q (Q en x, De en y, ambos logarítmicos) con las 9 categorías, los tramos y puntos de diseño sueltos."""
    if edition not in Q_CHARTS:
        raise ValueError(f"unknown edition {edition!r}; available: {sorted(Q_CHARTS)}")
    chart = Q_CHARTS[edition]
    for q, de in points:
        if not (math.isfinite(q) and math.isfinite(de) and q > 0 and de > 0):
            raise ValueError(f"points must be finite and > 0, got ({q}, {de})")
    drawn = [r for r in results if r.q_chart is not None] if results is not None else []
    if results is not None and not drawn:
        raise ValueError("none of the sections has a Q chart reference")
    for r in drawn:
        if r.q_chart.edition != edition:
            raise ValueError(f"results were read on {r.q_chart.edition}, not on {edition}")
    lang = style.lang
    fig = new_figure(style)  # primero: si falta matplotlib, el error nombra rockmasspy[viz]
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch, Polygon
    from matplotlib.patheffects import withStroke

    ax = fig.add_axes([0.09, 0.12, 0.6, 0.78])
    for reg in chart.regions:
        color = support_color(reg.key, _N_CAT, style)
        ax.add_patch(Polygon([(10 ** x, 10 ** y) for x, y in reg.polygon], closed=True, facecolor=color,
                             edgecolor="black", linewidth=0.6, zorder=1))
        x, y = _label_point(reg.polygon)
        ink = _ink(color)
        halo = [withStroke(linewidth=2, foreground="white" if ink == "black" else "#222222")]
        ax.text(10 ** x, 10 ** y, str(reg.key), ha="center", va="center", color=ink, fontsize=style.font_size + 3,
                fontweight="bold", zorder=2, path_effects=halo)
    for reg in chart.no_data:  # zonas sin datos empíricos: trama sobre el color de su categoría
        ax.add_patch(Polygon([(10 ** x, 10 ** y) for x, y in reg.polygon], closed=True, fill=False, hatch="//",
                             edgecolor="0.3", linewidth=0, zorder=1.5))
    q0, q1, d0, d1 = Q_CHART_FRAME
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(q0, q1)
    ax.set_ylim(d0, d1)
    ax.set_xlabel(text("q_axis", lang), fontsize=style.font_size)
    ax.set_ylabel(text("de_axis", lang), fontsize=style.font_size)
    ax.set_title(text("q_chart_title", lang), fontsize=style.font_size + 2)

    for r in drawn:  # un scatter por punto, sin rótulo: cada código lleva su forma
        rd = r.q_chart.roof
        if r.support_order is None:
            ax.scatter([rd.q], [rd.de_m], marker=_MARCA_SIN_CLASE, c="0.15", s=60, linewidths=1.8, zorder=4)
        else:
            ax.scatter([rd.q], [rd.de_m], marker=_MARCADORES[(r.support_order - 1) % len(_MARCADORES)],
                       c="white", edgecolors="black", linewidths=0.8, s=60, zorder=4)
    for q, de in points:
        ax.scatter([q], [de], marker="*", c="black", edgecolors="white", linewidths=0.6, s=170, zorder=5)

    cats = [Patch(facecolor=support_color(k, _N_CAT, style), edgecolor="black", label=f"{k}  {text(f'q_cat_{k}', lang)}")
            for k in range(1, _N_CAT + 1)]
    cats.append(Patch(fill=False, hatch="//", edgecolor="0.3", label=text("q_no_data", lang)))
    leg = ax.legend(handles=cats, loc="upper left", bbox_to_anchor=(1.02, 1.0), fontsize=style.font_size - 1)
    ax.add_artist(leg)
    handles = []
    por_orden = {r.support_order: r.support.code for r in drawn if r.support_order and r.support}
    for o, c in sorted(por_orden.items()):
        handles.append(Line2D([], [], ls="", marker=_MARCADORES[(o - 1) % len(_MARCADORES)], markersize=8,
                              markerfacecolor="white", markeredgecolor="black", label=c))
    if any(r.support_order is None for r in drawn):
        handles.append(Line2D([], [], ls="", marker=_MARCA_SIN_CLASE, color="0.15", markersize=8,
                              label=text("unclassified", lang)))
    if points:
        handles.append(Line2D([], [], ls="", marker="*", markerfacecolor="black", markeredgecolor="white",
                              markersize=12, label=text("q_design_point", lang)))
    if handles:
        ax.legend(handles=handles, title=text("support_legend", lang), loc="lower left", bbox_to_anchor=(1.02, 0.0),
                  fontsize=style.font_size - 1)
    footer(fig, " | ".join((text("q_digitized_from", lang).format(src=_FUENTE[edition]), edition,
                            text("engineer_decides", lang))), style)
    return fig
