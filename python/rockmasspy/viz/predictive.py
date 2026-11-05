"""Gráficos del nivel 3 (Fase 4C): isoprobabilidades de falla en el plano Q–De y curva de calibración.

Reciben lo que ya calculó `predictive.performance` (la malla y la curva); no recalculan nada. Sin ids (R13).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from .style import Style, footer, new_figure, text

_LEVELS = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)


def _points(name, pts):
    out = []
    for i, (q, de) in enumerate(pts):
        if not (math.isfinite(q) and math.isfinite(de) and q > 0 and de > 0):
            raise ValueError(f"{name}[{i}] must be two finite numbers > 0 (Q, De)")
        out.append((q, de))
    return out


def plot_isoprobability(grid, *, stable: Sequence[tuple[float, float]] = (),
                        failed: Sequence[tuple[float, float]] = (), levels: Sequence[float] = _LEVELS,
                        title: str = "", style: Style = Style()):
    """Contornos de P(falla) de un `IsoprobabilityGrid` en ejes log Q – log De, al estilo de Mawdesley et al.
    (2001). `stable` y `failed`: puntos (Q, De) de los tramos con ese tipo instalado, si se quieren ver."""
    lv = sorted(levels)
    if not lv or any(not 0 < x < 1 for x in lv):
        raise ValueError("levels must be probabilities strictly between 0 and 1")
    stable, failed = _points("stable", stable), _points("failed", failed)
    fig = new_figure(style)
    ax = fig.add_axes([0.09, 0.12, 0.86, 0.78])
    ax.set_xscale("log")
    ax.set_yscale("log")
    cs = ax.contour(10.0 ** grid.log10_q, 10.0 ** grid.log10_de, grid.p_failure, levels=lv, cmap="viridis_r",
                    linewidths=1.3)
    ax.clabel(cs, fmt=lambda v: f"{v:.1f}", fontsize=style.font_size - 1)
    if stable:
        ax.scatter(*zip(*stable), s=14, facecolors="none", edgecolors="0.3", label=text("iso_stable", style.lang),
                   zorder=3)
    if failed:
        ax.scatter(*zip(*failed), s=16, marker="x", color="#BC1A40", label=text("iso_failed", style.lang), zorder=3)
    if stable or failed:
        ax.legend(fontsize=style.font_size - 1, loc="upper right")
    ax.set_xlim(10.0 ** grid.log10_q.min(), 10.0 ** grid.log10_q.max())
    ax.set_ylim(10.0 ** grid.log10_de.min(), 10.0 ** grid.log10_de.max())
    from matplotlib.ticker import FuncFormatter

    for f in (ax.yaxis.set_major_formatter, ax.yaxis.set_minor_formatter):  # De cubre menos de una década
        f(FuncFormatter(lambda v, _: f"{v:g}"))
    ax.set_xlabel(text("iso_q_axis", style.lang), fontsize=style.font_size)
    ax.set_ylabel(text("iso_de_axis", style.lang), fontsize=style.font_size)
    ax.set_title(title or text("iso_title", style.lang).format(code=grid.support_code),
                 fontsize=style.font_size + 2, fontweight="bold")
    ax.grid(alpha=0.3, which="both")
    ax.tick_params(labelsize=style.font_size - 1)
    footer(fig, text("iso_source", style.lang).format(days=grid.exposure_days), style)
    return fig


def plot_calibration(curve: Sequence[tuple[float, float, int]], *, metrics: dict | None = None, title: str = "",
                     style: Style = Style()):
    """Curva de calibración fuera de pliegue: (eventos esperados medios, observados medios, n) por decil de λ, como
    `PerformanceModel.calibration_curve`, con la diagonal ideal. `metrics` (p. ej. `PerformanceModel.metrics`)
    agrega devianza de Poisson, observados/esperados y pendiente de calibración si están."""
    curve = list(curve)
    if not curve:
        raise ValueError("curve must not be empty")
    fig = new_figure(style)
    ax = fig.add_axes([0.1, 0.12, 0.85, 0.78])
    xs, ys, ns = zip(*curve)
    top_xy = max(1.0, *xs, *ys)  # los esperados λ·t pueden pasar de 1
    ax.plot([0, top_xy], [0, top_xy], linestyle="--", color="0.5", linewidth=1.0,
            label=text("cal_ideal", style.lang))
    top = max(ns) or 1
    ax.plot(xs, ys, color="#3F0F4F", linewidth=1.2)
    ax.scatter(xs, ys, s=[20 + 80 * n / top for n in ns], color="#3F0F4F", label=text("cal_points", style.lang),
               zorder=3)
    ax.set_xlim(0, top_xy)
    ax.set_ylim(0, top_xy)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel(text("cal_x", style.lang), fontsize=style.font_size)
    ax.set_ylabel(text("cal_y", style.lang), fontsize=style.font_size)
    ax.set_title(title or text("cal_title", style.lang), fontsize=style.font_size + 2, fontweight="bold")
    m = metrics or {}
    if all(isinstance(m.get(k), float) and math.isfinite(m[k])
           for k in ("poisson_deviance", "observed_expected", "calibration_slope")):
        ax.text(0.02, 0.96, text("cal_metrics", style.lang).format(dev=m["poisson_deviance"],
                                                                     oe=m["observed_expected"],
                                                                     b=m["calibration_slope"]),
                transform=ax.transAxes, ha="left", va="top", fontsize=style.font_size)
    ax.grid(alpha=0.3)
    ax.tick_params(labelsize=style.font_size - 1)
    ax.legend(fontsize=style.font_size - 1, loc="lower right")
    footer(fig, text("cal_source", style.lang), style)
    return fig
