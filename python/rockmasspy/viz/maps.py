"""Mapas de clase por labor: perfil a lo largo de la progresiva y vista en planta.

Solo colores, clases y el nombre de la labor (una categoría): nunca se rotula un id_tramo ni otro identificador.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..batch import TramoResult
from ..support import SupportCatalog
from .style import Style, _ink, footer, new_figure, support_color, text

_GRIS = "#BDBDBD"
_MARCADORES = ("o", "s", "^", "D", "v", "P", "X")  # uno por rango, para leer la planta en blanco y negro
_MARCA_SIN_CLASE = "x"


def _omitidos(key: str, n: int, lang: str) -> str:
    return text(key if n != 1 else key + "_1", lang).format(n=n)


def _n_types(results, catalog):
    if catalog is not None:
        return len(catalog)
    return max((r.support_order for r in results if r.support_order), default=1)


def _color(r: TramoResult, n: int, style: Style) -> str:
    return _GRIS if r.support_order is None else support_color(r.support_order, n, style)


def _legend(ax, drawn, n, style, marcadores=False):
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    por_orden = {r.support_order: r.support.code for r in drawn if r.support_order and r.support}
    if marcadores:  # planta: la forma también distingue la clase
        handles = [Line2D([], [], ls="", marker=_MARCADORES[(o - 1) % len(_MARCADORES)], markerfacecolor=support_color(o, n, style),
                          markeredgecolor="black", markersize=8, label=c) for o, c in sorted(por_orden.items())]
        if any(r.support_order is None for r in drawn):
            handles.append(Line2D([], [], ls="", marker=_MARCA_SIN_CLASE, color="0.45", markersize=8,
                                  label=text("unclassified", style.lang)))
    else:
        handles = [Patch(facecolor=support_color(o, n, style), edgecolor="black", label=c)
                   for o, c in sorted(por_orden.items())]
        if any(r.support_order is None for r in drawn):
            handles.append(Patch(facecolor=_GRIS, edgecolor="black", label=text("unclassified", style.lang)))
    ax.legend(handles=handles, title=text("support_legend", style.lang), loc="upper left",
              bbox_to_anchor=(1.01, 1.0), fontsize=style.font_size - 1)


def plot_labor_profile(results: Sequence[TramoResult], *, labor_type: str | None = None,
                       catalog: SupportCatalog | None = None, style: Style = Style()):
    """Una franja por labor, con cada tramo de su progresiva de inicio a la de fin.

    El color sale de `support_order` y del tamaño del catálogo. Sin `catalog`, el tamaño es el mayor
    `support_order` de los resultados: si las labores vienen de catálogos distintos, el mismo color
    puede significar sostenimientos distintos entre labores (pasa `catalog` para evitarlo).
    """
    if labor_type is not None:
        results = [r for r in results if r.tramo.tipo_labor == labor_type]
    drawn = [r for r in results if r.tramo.progresiva_inicio_m is not None and r.tramo.progresiva_fin_m is not None]
    if not drawn:
        raise ValueError("no section with chainage to draw")
    n = _n_types(drawn, catalog)
    labors = sorted({r.tramo.tipo_labor for r in drawn})
    from matplotlib.patheffects import withStroke

    fig = new_figure(style)
    ax = fig.add_axes([0.12, 0.15, 0.62, 0.75])
    xs = [v for r in drawn for v in (r.tramo.progresiva_inicio_m, r.tramo.progresiva_fin_m)]
    rango = (max(xs) - min(xs)) or 1.0
    for r in drawn:
        a, b = r.tramo.progresiva_inicio_m, r.tramo.progresiva_fin_m
        y = labors.index(r.tramo.tipo_labor)
        color = _color(r, n, style)
        ax.barh(y, b - a, left=a, height=0.6, color=color, edgecolor="black", linewidth=0.5)
        rotulo = r.label if r.support_order is not None and r.label else text("unclassified", style.lang)
        if (b - a) / rango > 0.012 * len(rotulo):  # solo si cabe dentro de la barra
            ink = _ink(color)
            halo = [withStroke(linewidth=2, foreground="white" if ink == "black" else "#222222")]
            ax.text((a + b) / 2, y, rotulo, ha="center", va="center", color=ink, fontsize=style.font_size - 2,
                    zorder=5, path_effects=halo)
    ax.set_yticks(range(len(labors)), labors)
    ax.set_xlabel(text("chainage_axis", style.lang), fontsize=style.font_size)
    ax.set_title(text("profile_title", style.lang), fontsize=style.font_size + 2)
    _legend(ax, drawn, n, style)
    omitidos = len(results) - len(drawn)
    if omitidos:
        fig.text(0.12, 0.07, _omitidos("omitted_chainage", omitidos, style.lang), fontsize=style.font_size - 1)
    ediciones = ", ".join(sorted({r.base_edition for r in drawn if r.base_edition}))
    footer(fig, text("editions_label", style.lang).format(e=ediciones), style)
    return fig


def plot_plan_map(results: Sequence[TramoResult], *, catalog: SupportCatalog | None = None,
                  style: Style = Style()):
    """Puntos este/norte coloreados por sostenimiento, a escala igual y sin rótulos por punto.

    Mismo criterio de color que el perfil: sin `catalog`, el tamaño es el mayor `support_order`.
    Cada rango lleva además su propia forma de marcador (y los sin clasificar una «x» gris).
    Los valores de las marcas de los ejes este/norte se aceptan como la escala del gráfico.
    """
    drawn = [r for r in results if r.tramo.este_m is not None and r.tramo.norte_m is not None]
    if not drawn:
        raise ValueError("no section with coordinates to draw")
    n = _n_types(drawn, catalog)
    fig = new_figure(style)
    ax = fig.add_axes([0.1, 0.12, 0.62, 0.58])
    for r in drawn:  # un scatter por punto: cada rango lleva su forma (la planta también se lee en blanco y negro)
        xy = ([r.tramo.este_m], [r.tramo.norte_m])
        if r.support_order is None:
            ax.scatter(*xy, marker=_MARCA_SIN_CLASE, c="0.45", s=40, linewidths=1.5)
        else:
            ax.scatter(*xy, marker=_MARCADORES[(r.support_order - 1) % len(_MARCADORES)], c=[_color(r, n, style)],
                       edgecolors="black", linewidths=0.5, s=40)
    ax.set_aspect("equal")
    ax.set_anchor("S")  # el gráfico queda pegado al pie
    ax.set_xlabel(text("east_axis", style.lang), fontsize=style.font_size)
    ax.set_ylabel(text("north_axis", style.lang), fontsize=style.font_size)
    ax.set_title(text("plan_title", style.lang), fontsize=style.font_size + 2)
    _legend(ax, drawn, n, style, marcadores=True)
    omitidos = len(results) - len(drawn)
    if omitidos:
        fig.text(0.1, 0.07, _omitidos("omitted_coords", omitidos, style.lang), fontsize=style.font_size - 1)
    datums = {r.tramo.datum for r in drawn}
    if len(datums) > 1:
        pie = text("mixed_datums", style.lang)
    else:
        pie = text("datum_label", style.lang).format(d=datums.pop() or "")
    footer(fig, pie, style)
    return fig
