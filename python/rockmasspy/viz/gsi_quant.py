"""Carta GSI cuantificada (Hoek, Carter y Diederichs 2013): isolíneas de GSI sobre JCond89 y RQD."""

from __future__ import annotations

from collections.abc import Sequence

from .. import gsi_from_jcond89_rqd
from .style import Style, footer, new_figure, text

_JC_MAX, _RQD_MAX = 30.0, 100.0


def plot_gsi_quantified(
    points: Sequence[tuple[float, float]] = (),
    *,
    labels: Sequence[str] | None = None,
    style: Style = Style(),
    contours: Sequence[float] = (10, 20, 30, 40, 50, 60, 70, 80, 90),
):
    """Carta con isolíneas de GSI (del núcleo) y puntos (JCond89, RQD) del usuario."""
    for i, (jc, rqd) in enumerate(points):
        if not (0 <= jc <= _JC_MAX and 0 <= rqd <= _RQD_MAX):
            raise ValueError(f"points[{i}] = ({jc}, {rqd}) is outside JCond89 in [0, 30], RQD in [0, 100]")
    if labels is not None and len(labels) != len(points):
        raise ValueError("labels must have the same length as points")

    import numpy as np  # viene con matplotlib

    xs = np.linspace(0, _JC_MAX, 61)
    ys = np.linspace(0, _RQD_MAX, 101)
    # El GSI sale siempre de la ecuación del núcleo, no se redibuja la fórmula aquí.
    z = np.array([[gsi_from_jcond89_rqd(float(x), float(y)).gsi for x in xs] for y in ys])

    fig = new_figure(style)
    ax = fig.add_subplot(111)
    for level in contours:  # una llamada por nivel: una colección por isolínea
        cs = ax.contour(xs, ys, z, levels=[level], colors="0.25", linewidths=1.0)
        ax.clabel(cs, fmt=lambda v: f"{text('gsi_label', style.lang)} {v:g}", fontsize=style.font_size - 1)
    if points:
        ax.scatter([p[0] for p in points], [p[1] for p in points], color="#C0392B", zorder=3)
        for i, lab in enumerate(labels or ()):
            ax.annotate(lab, points[i], xytext=(4, 4), textcoords="offset points", fontsize=style.font_size)
    ax.set_xlim(0, _JC_MAX)
    ax.set_ylim(0, _RQD_MAX)
    ax.set_xlabel(text("jcond89_axis", style.lang), fontsize=style.font_size)
    ax.set_ylabel(text("rqd_axis", style.lang), fontsize=style.font_size)
    ax.set_title(text("gsi_quant_title", style.lang), fontsize=style.font_size + 2)
    ax.grid(alpha=0.25)
    fig.subplots_adjust(bottom=0.12)
    footer(fig, "GSI-2013 · Hoek, Carter & Diederichs (2013)", style)
    return fig
