"""Carta de sostenimiento del sistema Q con los tramos encima.

Solo categorías, colores y marcadores: nunca se rotula un id_tramo ni otro identificador (Foco 5).
"""

from __future__ import annotations

from collections.abc import Sequence

from ..batch import TramoResult
from ..chart_regions import _classify
from ..q_chart_data import Q_CHART_FRAME, Q_CHARTS
from .maps import _MARCA_SIN_CLASE, _MARCADORES
from .style import Style, _ink, footer, new_figure, support_color, text

_FUENTE = {"Q-NGI-2025": "NGI (2025), Fig. 4-1", "Q-NGI-2015": "NGI (2015), Fig. 7"}
_N_CAT = 9


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


def plot_q_chart(edition: str = "Q-NGI-2025", *, results: Sequence[TramoResult] | None = None,
                 points: Sequence[tuple[float, float]] = (), style: Style = Style()):
    """Carta Q (Q en x, De en y, ambos logarítmicos) con las 9 categorías, los tramos y puntos de diseño sueltos."""
    if edition not in Q_CHARTS:
        raise ValueError(f"unknown edition {edition!r}; available: {sorted(Q_CHARTS)}")
    chart = Q_CHARTS[edition]
    drawn = [r for r in results if r.q_chart is not None] if results is not None else []
    if results is not None and not drawn:
        raise ValueError("none of the sections has a Q chart reference")
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

    n = max((r.support_order for r in drawn if r.support_order), default=1)
    for r in drawn:  # un scatter por punto, sin rótulo: cada código lleva su forma
        rd = r.q_chart.roof
        if r.support_order is None:
            ax.scatter([rd.q], [rd.de_m], marker=_MARCA_SIN_CLASE, c="0.15", s=60, linewidths=1.8, zorder=4)
        else:
            ax.scatter([rd.q], [rd.de_m], marker=_MARCADORES[(r.support_order - 1) % len(_MARCADORES)],
                       c=[support_color(r.support_order, n, style)], edgecolors="black", linewidths=0.8, s=60, zorder=4)
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
                              markerfacecolor=support_color(o, n, style), markeredgecolor="black", label=c))
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
