"""Figuras del análisis por elementos de contorno: contornos de σ1, σ3 o strength factor y σtt en el borde."""

from __future__ import annotations

import math
import os

from .save import save_figure
from .style import Style, footer, new_figure, text

_SF_LEVELS = [0, 0.5, 1, 1.25, 1.5, 2, 3, 5, 10]


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
    ok = [not (i or math.isnan(v)) for i, v in zip(f.inside, z)]
    try:
        import numpy as np
        from matplotlib.tri import Triangulation

        tri = Triangulation(f.x, f.y)
        bad = ~np.array(ok)
        tri.set_mask(bad[tri.triangles].any(axis=1))
        zz = np.where(bad, 0.0, z)
        kw = {"levels": _SF_LEVELS, "extend": "max"} if quantity == "sf" else {"levels": 12}
        cs = ax.tricontourf(tri, zz, cmap="RdYlGn" if quantity == "sf" else "viridis", **kw)
        fig.colorbar(cs, ax=ax, label=text(f"bem_{quantity}", lang))
        if any(f.tension):
            tt = np.array(f.tension, dtype=float)
            ax.tricontourf(Triangulation(f.x, f.y), tt, levels=[0.5, 1.5], colors="none", hatches=["///"])
            from matplotlib.patches import Patch

            ax.legend(handles=[Patch(fill=False, hatch="///", label=text("bem_tension", lang))], fontsize=fs - 1)
    except (RuntimeError, ValueError):  # menos de 3 puntos útiles o todos alineados: sin contornos
        pass
    ax.scatter(result.boundary.x, result.boundary.y, s=2, c="black", zorder=5)
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
