"""Cartilla publicable de una tabla por labor (art. 33 DS 024): celdas GSI o barra de rangos, con leyenda."""

from __future__ import annotations

import math

from ..cell_table import CellTable
from ..labor_table import LaborTable
from ..range_table import RANGE_METHODS
from ..support import SupportType
from .style import TEXTS, Style, footer, new_figure, support_color, text

_DASHED, _UNDEFINED = "#E6E6E6", "#BDBDBD"


def _ink(color: str) -> str:
    """Negro o blanco según la luminosidad del fondo, para que el texto se lea sobre los morados."""
    from matplotlib.colors import to_rgb

    r, g, b = (c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in to_rgb(color))
    return "black" if 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.18 else "white"


def _axis_label(kind: str, code: str, label: str, lang: str) -> str:
    """Rótulo de estructura o condición en el idioma pedido; si el código no está en TEXTS, el de la cartilla."""
    key = f"gsi_{kind}_{code}"
    return TEXTS[key][lang] if key in TEXTS else label


def _rect(x, y, w, h, color):
    from matplotlib.patches import Rectangle

    return Rectangle((x, y), w, h, facecolor=color, edgecolor="0.3", linewidth=0.6)


def _describe(t: SupportType, lang: str) -> str:
    parts = []
    if t.bolt:
        parts.append(f"{text('bolt', lang)} {t.bolt.kind} {t.bolt.length_m:g} m @ {t.bolt.spacing_m:g} m")
    if t.shotcrete:
        fiber = text("with_fiber" if t.shotcrete.fiber else "without_fiber", lang)
        parts.append(f"{text('shotcrete', lang)} {t.shotcrete.thickness_mm:g} mm {fiber}")
    if t.mesh:
        parts.append(text("mesh", lang))
    if t.arch:
        parts.append(text("arch", lang))
    return (lambda d: d[:1].upper() + d[1:])("; ".join(parts) or text("no_support", lang))


def _legend(fig, rect, ordered, colors, style):
    ax = fig.add_axes(rect)
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(len(ordered), -0.9)  # la franja de -0.9 a 0 es el título
    ax.text(0, -0.45, text("support_legend", style.lang), fontweight="bold", va="center", fontsize=style.font_size)
    for i, t in enumerate(ordered):
        c = colors[t.code]
        ax.add_patch(_rect(0, i + 0.1, 0.05, 0.8, c))
        ax.text(0.025, i + 0.5, t.code, ha="center", va="center", color=_ink(c),
                fontsize=style.font_size - 1, fontweight="bold")
        ax.text(0.07, i + 0.5, _describe(t, style.lang), va="center", fontsize=style.font_size)


def _header(fig, table: LaborTable, title, style):
    lang = style.lang
    y = 0.975
    if title:
        fig.text(0.5, y, title, ha="center", va="top", fontsize=style.font_size + 5, fontweight="bold")
        y -= 0.03
    fig.text(0.5, y, table.labor_type, ha="center", va="top", fontsize=style.font_size + 3, fontweight="bold")
    bits = []
    if table.span_m:
        bits.append(f"{text('span', lang)} {table.span_m[0]:.1f}–{table.span_m[1]:.1f} m")
    if table.author:
        bits.append(f"{text('author', lang)}: {table.author}")
    if table.date:
        bits.append(f"{text('date', lang)}: {table.date}")
    if bits:
        fig.text(0.5, y - 0.027, "   ·   ".join(bits), ha="center", va="top", fontsize=style.font_size)


def _cells(fig, table: LaborTable, rect, colors, style):
    chart, ct = table.table.chart, table.table
    by_cell = {c.cell: c for c in ct.cells}
    ax = fig.add_axes(rect)
    ns, nc = len(chart.structures), len(chart.conditions)
    ax.set_xlim(0, nc)
    ax.set_ylim(ns, 0)
    for r, (s, _) in enumerate(chart.structures):
        for k, (c, _) in enumerate(chart.conditions):
            code = f"{s}/{c}"
            cell = by_cell.get(code)
            if code not in chart.valid_cells:
                p = _rect(k, r, 1, 1, _DASHED)
                p.set_gid(f"dashed:{code}")
                ax.add_patch(p)
                ax.plot([k, k + 1], [r + 1, r], color="0.45", linewidth=0.8)
                continue
            known = cell is not None and cell.support in colors
            bg = colors[cell.support] if known else _UNDEFINED
            p = _rect(k, r, 1, 1, bg)
            p.set_gid(code)
            ax.add_patch(p)
            second = cell.support if known else text("undefined", style.lang)
            ax.text(k + 0.5, r + 0.5, f"{code}\n{second}", ha="center", va="center", color=_ink(bg),
                    fontsize=style.font_size)
    ax.set_xticks([k + 0.5 for k in range(nc)], [f"{c}\n{_axis_label("cond", c, lbl, style.lang)}" for c, lbl in chart.conditions],
                  fontsize=style.font_size - 1)
    ax.set_yticks([r + 0.5 for r in range(ns)], [f"{s}\n{_axis_label("struct", s, lbl, style.lang)}" for s, lbl in chart.structures],
                  fontsize=style.font_size - 1)
    ax.xaxis.tick_top()
    ax.xaxis.set_label_position("top")
    ax.set_xlabel(text("condition_axis", style.lang), fontsize=style.font_size)
    ax.set_ylabel(text("structure_axis", style.lang), fontsize=style.font_size)
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)


def _ranges(fig, table: LaborTable, rect, colors, style):
    rtab = table.table
    lo_d, hi_d = RANGE_METHODS[rtab.method][1]
    log = rtab.method == "Q"
    frac = (lambda v: math.log10(v / lo_d) / math.log10(hi_d / lo_d)) if log else (lambda v: (v - lo_d) / (hi_d - lo_d))
    ax = fig.add_axes(rect)
    ax.set_xscale("log" if log else "linear")
    ax.set_xlim(lo_d, hi_d)
    classes = sorted(rtab.classes, key=lambda c: c.lo)
    ax.set_ylim(len(classes), 0)
    for i, c in enumerate(classes):
        lo, hi = max(c.lo, lo_d), min(c.hi, hi_d)
        known = c.support in colors
        bg = colors[c.support] if known else _UNDEFINED
        ax.add_patch(_rect(lo, i + 0.1, hi - lo, 0.8, bg))
        label = f"{c.label}  ({c.lo:g}–{c.hi:g})  {c.support if known else text('undefined', style.lang)}"
        kw = dict(va="center", fontsize=style.font_size)
        mid = (lo * hi) ** 0.5 if log else (lo + hi) / 2
        pad = (lambda v, f: v * f) if log else (lambda v, f: v + (f - 1) * 20)
        if frac(hi) - frac(lo) > 0.4:  # barra ancha: el texto va dentro
            ax.text(mid, i + 0.5, label, ha="center", color=_ink(bg), **kw)
        elif frac(lo) < 0.5:  # barra angosta a la izquierda: el texto a su derecha
            ax.text(pad(hi, 1.05), i + 0.5, label, ha="left", **kw)
        else:
            ax.text(pad(lo, 1 / 1.05), i + 0.5, label, ha="right", **kw)
    ax.set_yticks([])
    ax.set_xlabel(f"{rtab.method} ({rtab.base_edition}) - {text('range_axis', style.lang)}", fontsize=style.font_size)
    ax.tick_params(labelsize=style.font_size - 1)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)


def plot_cartilla(table: LaborTable, *, style: Style = Style(size="cartilla"), title: str | None = None,
                  show_lines: bool = True):  # show_lines: lo usa la tarea 6 al dibujar las líneas RMR′
    """Cartilla de la tabla por labor: cuadrícula de celdas o barra de rangos, más leyenda del catálogo."""
    ordered = table.catalog.ordered()
    n = len(ordered)
    # el color sale de la posición en el catálogo ordenado: el `order` puede tener huecos
    colors = {t.code: support_color(i + 1, n, style) for i, t in enumerate(ordered)}
    fig = new_figure(style)
    _header(fig, table, title, style)
    is_cells = isinstance(table.table, CellTable)
    legend_h = min(0.42, 0.035 * (n + 1.5))
    bottom = 0.07 + legend_h + 0.05
    top = 0.87 if title else 0.90
    body = [0.26, bottom, 0.70, top - bottom - (0.05 if is_cells else 0.02)]
    (_cells if is_cells else _ranges)(fig, table, body, colors, style)
    _legend(fig, [0.04, 0.07, 0.92, legend_h], ordered, colors, style)
    source = f"{table.table.base_edition} · {text('engineer_decides', style.lang)}"
    footer(fig, source, style)
    return fig
