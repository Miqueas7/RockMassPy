"""Figuras del análisis por elementos de contorno: contornos de σ1, σ3 o strength factor y σtt en el borde."""

from __future__ import annotations

import math
import os

from .save import save_figure
from .style import Style, footer, new_figure, text

_SF_LEVELS = [0, 0.5, 1, 1.25, 1.5, 2, 3, 5, 10]


def _grid_coarse(result) -> bool:
    """True si el paso de la grilla supera 1/10 de la menor dimensión de las excavaciones."""
    xs, ys = result.field.x, result.field.y
    step = math.sqrt((max(xs) - min(xs)) * (max(ys) - min(ys)) / max(len(xs), 1))
    dim = min(min(max(q[0] for q in p) - min(q[0] for q in p), max(q[1] for q in p) - min(q[1] for q in p))
              for p in result.excavations)
    return step > dim / 10


def bem_triangulation(result, z):
    """(Triangulation, z) listo para contornear: se enmascaran solo los triángulos cuyo centroide cae dentro de una
    excavación (o con un vértice sin valor fuera de ellas); los vértices interiores toman el valor del vecino
    exterior más cercano para que el contorno llegue hasta el borde."""
    import numpy as np
    from matplotlib.path import Path
    from matplotlib.tri import Triangulation

    f = result.field
    tri = Triangulation(f.x, f.y)
    inside = np.array(f.inside)
    zv = np.array(z, dtype=float)
    bad = ~inside & ~np.isfinite(zv)
    good = ~inside & ~bad
    if inside.any() and good.any():
        gx, gy = np.array(f.x)[good], np.array(f.y)[good]
        for k in np.nonzero(inside)[0]:
            zv[k] = zv[good][np.argmin((gx - f.x[k]) ** 2 + (gy - f.y[k]) ** 2)]
    zv[bad] = 0.0
    cen = np.column_stack([np.array(f.x)[tri.triangles].mean(axis=1), np.array(f.y)[tri.triangles].mean(axis=1)])
    in_exc = np.zeros(len(cen), dtype=bool)
    for p in result.excavations:
        in_exc |= Path(p).contains_points(cen)
    if not result.excavations:
        in_exc = inside[tri.triangles].any(axis=1)
    tri.set_mask(in_exc | bad[tri.triangles].any(axis=1))
    return tri, zv


def bem_figure(result, *, quantity: str = "sf", lang: str = "es"):
    """Figura (matplotlib) de contornos rellenos; la zona en tracción va rayada y el borde en negro."""
    if quantity not in ("sf", "sigma1", "sigma3"):
        raise ValueError("quantity must be 'sf', 'sigma1' or 'sigma3'")
    style = Style(lang=lang)
    fig = new_figure(style)
    fs = style.font_size
    ax = fig.add_axes([0.1, 0.14, 0.72, 0.76])
    f = result.field
    if quantity == "sf":
        z = [math.nan if v is None or not math.isfinite(v) else v for v in f.sf]
    else:
        z = list(getattr(f, quantity))
    try:
        tri, zz = bem_triangulation(result, z)
        kw = {"levels": _SF_LEVELS, "extend": "max"} if quantity == "sf" else {"levels": 12}
        cs = ax.tricontourf(tri, zz, cmap="RdYlGn" if quantity == "sf" else "viridis", **kw)
        fig.colorbar(cs, ax=ax, label=text(f"bem_{quantity}", lang))
        if any(f.tension):
            import numpy as np
            from matplotlib.patches import Patch

            ax.tricontourf(tri.x, tri.y, np.array(f.tension, dtype=float), levels=[0.5, 1.5], colors="none",
                           hatches=["///"])
            ax.legend(handles=[Patch(fill=False, hatch="///", label=text("bem_tension", lang))], fontsize=fs - 1)
    except (RuntimeError, ValueError):  # menos de 3 puntos útiles o todos alineados: sin contornos
        pass
    if result.excavations:
        for p in result.excavations:
            ax.fill([q[0] for q in p], [q[1] for q in p], facecolor="0.9", edgecolor="black", lw=1, zorder=5)
    else:
        ax.scatter(result.boundary.x, result.boundary.y, s=2, c="black", zorder=5)
    if result.excavations and _grid_coarse(result):
        fig.text(0.5, 0.05, text("bem_coarse_grid", lang), ha="center", fontsize=fs - 1, color="tab:red")
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)", fontsize=fs)
    ax.set_ylabel("y (m)", fontsize=fs)
    ax.set_title(text("bem_title", lang), fontsize=fs + 2)
    footer(fig, f"{result.info.method_id} | {text('engineer_decides', lang)}", style)
    return fig


def plot_bem(result, path: str | os.PathLike, *, quantity: str = "sf", lang: str = "es"):
    return save_figure(bem_figure(result, quantity=quantity, lang=lang), path)


def bem_boundary_figure(result, *, lang: str = "es"):
    """σtt de cada elemento de contorno, en el orden en que se armaron los contornos."""
    style = Style(lang=lang)
    fig = new_figure(style)
    ax = fig.add_axes([0.1, 0.14, 0.85, 0.76])
    b = result.boundary
    ax.plot(range(1, len(b.sigma_tt) + 1), b.sigma_tt, color="black", lw=1.2)
    ax.axhline(0, color="0.5", lw=0.8)
    ax.set_xlabel(text("bem_element", lang), fontsize=style.font_size)
    ax.set_ylabel(text("bem_stt_axis", lang), fontsize=style.font_size)
    ax.set_title(text("bem_boundary", lang), fontsize=style.font_size + 2)
    ax.grid(alpha=0.3)
    footer(fig, f"{result.info.method_id} | {text('engineer_decides', lang)}", style)
    return fig


def plot_bem_boundary(result, path: str | os.PathLike, *, lang: str = "es"):
    return save_figure(bem_boundary_figure(result, lang=lang), path)
