"""Dispersión de pares del usuario con las correlaciones globales y del sitio sobre el mismo gráfico."""

from __future__ import annotations

import math
from collections.abc import Sequence

import rockmasspy as rm

from .style import Style, footer, new_figure, text

_DASHES = ("--", "-.", ":")
_POINTS = 200


def _global_ends(c) -> tuple[str, str]:
    """Del núcleo se lee el from/to de la correlación (sin duplicar su catálogo), con un valor válido de prueba."""
    r = rm.correlate(c, 1.0 if "FromQ" in c.name else 50.0)
    return r.from_, r.to


def _check_ends(label: str, got: tuple[str, str], x: str, y: str) -> None:
    if got != (x, y):
        raise ValueError(f"correlation {label} goes {got[0]} -> {got[1]}, but the chart is {x} -> {y}")


def _grid(lo: float, hi: float, log: bool) -> list[float]:
    if log:
        lo, hi = math.log10(lo), math.log10(hi)
    pts = [lo + (hi - lo) * i / (_POINTS - 1) for i in range(_POINTS)]
    return [10 ** p for p in pts] if log else pts


def plot_correlation(pairs: Sequence[tuple[float, float]], *, x: str, y: str,
                     global_correlations: Sequence[rm.Correlation] = (),
                     site: Sequence[rm.CustomCorrelation] = (), bands: Sequence = (), style: Style = Style()):
    """Puntos (x, y) del usuario más una curva por correlación, rotulada con su method_id.

    Q y Q′ van en escala logarítmica. Cada curva se dibuja solo donde el núcleo la acepta. `bands`: ajustes con
    `predict(x)` → (ŷ, inferior, superior) y rango `x_min`/`x_max` (p. ej. `predictive.SiteCorrelationFit`); se
    sombrea su intervalo de predicción al 95 % dentro del rango observado.
    """
    pairs = list(pairs)
    if not pairs:
        raise ValueError("pairs must not be empty")
    log = x in ("Q", "Q'")
    for i, (px, py) in enumerate(pairs):
        if not (math.isfinite(px) and math.isfinite(py)):
            raise ValueError(f"pairs[{i}] must be two finite numbers, got {(px, py)!r}")
        if log and px <= 0:
            raise ValueError(f"pairs[{i}]: {x} must be > 0 on a log axis, got {px!r}")
    for c in global_correlations:
        _check_ends(c.name, _global_ends(c), x, y)
    for c in site:
        _check_ends(f"site:{c.name}", (c.from_, c.to), x, y)

    xs = [p[0] for p in pairs]
    lo, hi = min(xs), max(xs)
    # margen para que las curvas se vean un poco más allá de los datos
    lo, hi = (lo / 3, hi * 3) if log else (lo - 0.1 * (hi - lo or 1), hi + 0.1 * (hi - lo or 1))

    site_tag = text("site", style.lang)  # prefijo de las correlaciones del sitio en leyenda y pie
    fig = new_figure(style)
    ax = fig.add_axes([0.1, 0.16, 0.85, 0.74])
    if log:
        ax.set_xscale("log")
    ax.scatter(xs, [p[1] for p in pairs], s=18, color="0.25", label=text("scatter_points", style.lang), zorder=3)

    def _clipped(r) -> bool:  # el núcleo recorta a [0, 100] y avisa: ese tramo plano engañaría, así que se corta
        return any("clipped" in w for w in r.warnings)

    for k, c in enumerate(global_correlations):
        cx, cy, mid = [], [], ""
        for v in _grid(lo, hi, log):
            try:
                r = rm.correlate(c, v)
            except ValueError:  # fuera de validez (Q ≤ 0, RMR′ bajo el mínimo): el punto se omite
                continue
            if _clipped(r):
                continue
            cx.append(v)
            cy.append(r.value)
            mid = r.info.method_id
        if cx:  # sin puntos no hay curva ni entrada de leyenda
            ax.plot(cx, cy, linestyle=_DASHES[k % len(_DASHES)], linewidth=1.6, label=mid or c.name)
    for k, f in enumerate(bands):
        a, b = max(lo, f.x_min), min(hi, f.x_max)
        if a < b:
            gx = _grid(a, b, log)
            _, low, high = f.predict(gx, 0.95)
            ax.fill_between(gx, low, high, alpha=0.15, linewidth=0,
                            label=text("prediction_band", style.lang) if k == 0 else None)
    for c in site:
        a, b = max(lo, c.valid_min), min(hi, c.valid_max)
        cx, cy = [], []
        for v in (_grid(a, b, log) if a < b else []):
            r = rm.correlate_custom(c, v)
            if not _clipped(r):
                cx.append(v)
                cy.append(r.value)
        if cx:
            ax.plot(cx, cy, linewidth=1.8, label=f"{site_tag}:{c.name}")

    ax.set_xlabel(x, fontsize=style.font_size)
    ax.set_ylabel(y, fontsize=style.font_size)
    ax.set_title(text("correlation_title", style.lang), fontsize=style.font_size + 3, fontweight="bold")
    ax.grid(alpha=0.3)
    ax.tick_params(labelsize=style.font_size - 1)
    ax.legend(fontsize=style.font_size - 1, loc="best")
    if global_correlations:
        fig.text(0.5, 0.06, text("global_scatter_note", style.lang), ha="center", fontsize=style.font_size - 1, style="italic")
    ids = [c.name for c in global_correlations] + [f"{site_tag}:{c.name}" for c in site]
    footer(fig, ", ".join(ids) or f"{x} -> {y}", style)
    return fig
