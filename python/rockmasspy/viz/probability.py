"""Histograma del FS y curva de PoF de un resultado probabilístico.

Los conteos y la PoF salen de `ProbabilisticResult`; la figura no los recalcula. Sin ids (Foco 5).
"""

from __future__ import annotations

import math

from ..probabilistic import ProbabilisticResult, is_failure
from .style import Style, footer, new_figure, support_color, text


def _pie(res, lang):
    m = text("prob_lhs" if res.sampling == "lhs" else "prob_monte_carlo", lang)
    return " | ".join((res.info.method_id, m, text("prob_samples", lang).format(valid=res.n_valid, n=res.n),
                       f"{text('prob_seed', lang)} {res.seed}"))


def _drawn(res) -> list[float]:
    """Muestras con posición en el eje: FS finito y no acotado (el tope y la cota superior no son un FS)."""
    ex = set(res.excluded)
    return [f for i, f in enumerate(res.fs) if f is not None and math.isfinite(f) and i not in ex]


def _excluded_failures(res) -> int:
    """Fallas que no se dibujan (cotas superiores): con las barras de falla suman n_failed."""
    return res.n_failed - sum(1 for f in _drawn(res) if is_failure(f))


def _base(res, title, style, key):
    """Figura con ejes, título y pie; None en `ax` si no hay muestras válidas."""
    lang = style.lang
    fig = new_figure(style)
    footer(fig, _pie(res, lang), style)
    ax = fig.add_axes([0.09, 0.14, 0.86, 0.76])
    ax.set_title(title or text(key, lang), fontsize=style.font_size + 2)
    ax.set_xlabel(text("prob_fs", lang), fontsize=style.font_size)
    if not res.n_valid:
        ax.set_axis_off()
        ax.text(0.5, 0.5, text("prob_no_valid", lang), ha="center", va="center", transform=ax.transAxes,
                fontsize=style.font_size + 2)
        return fig, None
    ax.text(0.02, 0.96, f"{text('prob_pof', lang)} = {res.pof * 100:.1f} %", transform=ax.transAxes,
            ha="left", va="top", fontsize=style.font_size + 2, fontweight="bold")
    k = sum(1 for f in res.fs if f is not None and math.isinf(f))
    if k:  # válidas y estables, pero sin posición en el eje
        ax.text(0.02, 0.89, text("prob_infinite", lang).format(k=k), transform=ax.transAxes, ha="left",
                va="top", fontsize=style.font_size - 1)
    if res.excluded:  # cotas del volteo: válidas, contadas en la PoF, sin posición en el eje
        ax.text(0.02, 0.84 if k else 0.89, text("prob_excluded", lang).format(k=len(res.excluded),
                f=_excluded_failures(res)), transform=ax.transAxes, ha="left", va="top", fontsize=style.font_size - 1)
    return fig, ax


def plot_fs_histogram(result: ProbabilisticResult, *, title: str = "", bins: int = 40, style: Style = Style()):
    """Histograma de las muestras con FS finito; las de falla (FS ≤ 1) en otro color y con rayado."""
    if isinstance(bins, bool) or not isinstance(bins, int) or bins < 1:
        raise ValueError("bins must be an integer >= 1")
    lang = style.lang
    fig, ax = _base(result, title, style, "prob_hist_title")
    if ax is None:
        return fig
    from matplotlib.patches import Patch

    vals = _drawn(result)
    lo, hi = min(vals + [1.0]), max(vals + [1.0])
    if hi == lo:
        lo, hi = lo - 0.5, hi + 0.5
    w = (hi - lo) / bins
    nl, nr = max(1, math.ceil((1 - lo) / w - 1e-9)), max(1, math.ceil((hi - 1) / w - 1e-9))
    fail, ok = [0] * nl, [0] * nr  # FS = 1 es borde: a su izquierda solo hay fallas, a su derecha solo estables
    for f in vals:
        if is_failure(f):
            fail[min(max(math.floor((f - (1 - nl * w)) / w), 0), nl - 1)] += 1
        else:
            ok[min(max(math.floor((f - 1) / w), 0), nr - 1)] += 1
    xf, xo = [1 - (nl - i) * w for i in range(nl)], [1 + i * w for i in range(nr)]
    c_ok, c_fail = support_color(1, 2, style), support_color(2, 2, style)
    ax.bar(xf, fail, width=w, align="edge", color=c_fail, edgecolor="black", linewidth=0.4, hatch="//")
    ax.bar(xo, ok, width=w, align="edge", color=c_ok, edgecolor="black", linewidth=0.4)
    ax.axvline(1.0, color="black", lw=1.5, ls="--")
    ax.set_ylabel(text("prob_frequency", lang), fontsize=style.font_size)
    ax.legend(handles=[Patch(facecolor=c_fail, edgecolor="black", hatch="//", label=text("prob_failure", lang)),
                       Patch(facecolor=c_ok, edgecolor="black", label=text("prob_stable", lang))],
              loc="upper right", fontsize=style.font_size - 1)
    return fig


def plot_fs_cdf(result: ProbabilisticResult, *, title: str = "", style: Style = Style()):
    """Curva acumulada empírica del FS, con la PoF marcada en FS = 1."""
    lang = style.lang
    fig, ax = _base(result, title, style, "prob_cdf_title")
    if ax is None:
        return fig
    from matplotlib.lines import Line2D

    n = result.n_valid
    vals = sorted(_drawn(result))
    # FS infinito y tope cuentan como válidos y estables: la curva acumula sobre n_valid. Las cotas superiores son
    # fallas sin FS conocido: la curva arranca en su fracción, así corta FS = 1 en la PoF
    f0 = _excluded_failures(result)
    ax.step([min(vals + [1.0])] + vals, [f0 / n] + [(f0 + i + 1) / n for i in range(len(vals))], where="post",
            color="black", lw=1.4)
    ax.axvline(1.0, color="black", lw=1.2, ls="--")
    ax.scatter([1.0], [result.pof], marker="o", c="white", edgecolors="black", linewidths=1.2, s=70, zorder=4)
    ax.set_ylim(0, 1.02)
    ax.set_ylabel(text("prob_cumulative", lang), fontsize=style.font_size)
    ax.legend(handles=[Line2D([], [], ls="", marker="o", markersize=8, markerfacecolor="white",
                              markeredgecolor="black", label=text("prob_pof_at_one", lang))],
              loc="lower right", fontsize=style.font_size - 1)
    return fig
