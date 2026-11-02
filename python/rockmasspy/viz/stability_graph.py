"""Gráfico de estabilidad (Mathews/Potvin y Laubscher) con los casos encima.

Solo círculos y estrellas: nunca se rotula un id_superficie ni otro identificador (Foco 5).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from ..stability_graphs import STABILITY_GRAPHS
from ._label import _label_point
from .style import Style, _ink, footer, new_figure, support_color, text

_TITULO = {"Mathews-Potvin1988": "stab_title_mathews", "Laubscher1994-stability": "stab_title_laubscher"}
_Y_AXIS = {"Mathews-Potvin1988": "nprime_axis", "Laubscher1994-stability": "mrmr_axis"}
_FUENTE = {"Mathews-Potvin1988": "stab_digitized_mathews", "Laubscher1994-stability": "stab_digitized_laubscher"}


def _check(name, pairs, y_log):
    for x, y in pairs:
        if not (math.isfinite(x) and math.isfinite(y) and x > 0 and (y > 0 if y_log else y >= 0)):
            raise ValueError(f"{name} must be finite with x > 0 and y {'> 0' if y_log else '>= 0'}, got ({x}, {y})")


def plot_stability_graph(graph_id: str = "Mathews-Potvin1988", *, cases: Sequence[tuple[float, float]] = (),
                         points: Sequence[tuple[float, float]] = (), style: Style = Style()):
    """Gráfico de estabilidad con sus tres zonas, los casos (x = HR, y = N′ o MRMR) y puntos de diseño sueltos."""
    g = STABILITY_GRAPHS.get(graph_id)
    if g is None:
        raise ValueError(f"unknown stability graph {graph_id!r}; available: {', '.join(STABILITY_GRAPHS)}")
    _check("cases", cases, g.y_log)
    _check("points", points, g.y_log)
    lang = style.lang
    fig = new_figure(style)  # primero: si falta matplotlib, el error nombra rockmasspy[viz]
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch, Polygon
    from matplotlib.patheffects import withStroke

    def yv(v):  # el plano del gráfico guarda log10 N′ en el de Potvin
        return 10 ** v if g.y_log else v

    def poly(p):
        return [(x, yv(y)) for x, y in p]

    ax = fig.add_axes([0.09, 0.12, 0.62, 0.78])
    for reg in g.regions:
        color = support_color(reg.key, 3, style)
        ax.add_patch(Polygon(poly(reg.polygon), closed=True, facecolor=color, edgecolor="none", zorder=1))
        x, y = _label_point(reg.polygon)
        ink = _ink(color)
        halo = [withStroke(linewidth=2, foreground="white" if ink == "black" else "#222222")]
        ax.text(x, yv(y), text(f"stab_zone_{reg.key}", lang), ha="center", va="center", color=ink,
                fontsize=style.font_size + 2, fontweight="bold", zorder=2, path_effects=halo)
    for reg in g.no_data:
        ax.add_patch(Polygon(poly(reg.polygon), closed=True, fill=False, hatch="//", edgecolor="0.3", linewidth=0,
                             zorder=1.5))
    dash_x = min((x for r in g.no_data for x, _ in r.polygon), default=None)
    for line in g.boundaries:  # continua hasta la franja sin datos y a trazos dentro de ella
        k = len(line) if dash_x is None else next((i for i, p in enumerate(line) if p[0] >= dash_x), len(line))
        for seg, ls in ((line[:k + 1], "-"), (line[max(k - 1, 0):] if k < len(line) else (), "--")):
            if len(seg) > 1:
                ax.plot([p[0] for p in seg], [yv(p[1]) for p in seg], color="black", lw=1.2, ls=ls, zorder=3)
    (x0, x1), (y0, y1) = g.x_range, g.y_range
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    if g.y_log:
        ax.set_yscale("log")
    ax.set_xlabel(text("hr_axis", lang), fontsize=style.font_size)
    ax.set_ylabel(text(_Y_AXIS[graph_id], lang), fontsize=style.font_size)
    ax.set_title(text(_TITULO[graph_id], lang), fontsize=style.font_size + 2)

    for x, y in cases:  # sin rótulo: círculo blanco con borde negro, legible sobre cualquier relleno y en B/N
        ax.scatter([x], [y], marker="o", c="white", edgecolors="black", linewidths=0.9, s=55, zorder=4)
    for x, y in points:
        ax.scatter([x], [y], marker="*", c="black", edgecolors="white", linewidths=0.6, s=170, zorder=5)

    zonas = [Patch(facecolor=support_color(k, 3, style), edgecolor="black", label=text(f"stab_zone_{k}", lang))
             for k in (1, 2, 3)]
    if g.no_data:
        zonas.append(Patch(fill=False, hatch="//", edgecolor="0.3", label=text("stab_dashed", lang)))
    ax.add_artist(ax.legend(handles=zonas, loc="upper left", bbox_to_anchor=(1.02, 1.0), fontsize=style.font_size - 1))
    handles = []
    if cases:
        handles.append(Line2D([], [], ls="", marker="o", markersize=8, markerfacecolor="white",
                              markeredgecolor="black", label=text("stab_case", lang)))
    if points:
        handles.append(Line2D([], [], ls="", marker="*", markerfacecolor="black", markeredgecolor="white",
                              markersize=12, label=text("q_design_point", lang)))
    if handles:
        ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(1.02, 0.0), fontsize=style.font_size - 1)
    footer(fig, " | ".join((text(_FUENTE[graph_id], lang), graph_id, text("engineer_decides", lang))), style)
    return fig
