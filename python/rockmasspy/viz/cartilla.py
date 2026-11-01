"""Cartilla publicable de una tabla por labor (art. 33 DS 024): celdas GSI o barra de rangos, con leyenda."""

from __future__ import annotations

import math

from ..cell_table import CellTable
from ..intact_rock import _strip
from ..labor_table import LaborTable
from ..range_table import RANGE_METHODS
from ..support import SupportType
from ..vallejo_lines import RMR_PRIME_LINES
from .style import TEXTS, Style, footer, new_figure, support_color, text

# No aplica: blanco con rayado gris claro, distinto de todo color de sostenimiento también en blanco y negro.
_NA_BG, _NA_HATCH, _UNDEFINED = "white", "0.75", "#BDBDBD"
_LINES_CHART = "GSI-Vallejo-Osinergmin2017"  # la única cartilla con líneas RMR′ digitalizadas


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
    desc = "; ".join(parts) or text("no_support", lang)
    return desc[:1].upper() + desc[1:]


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
    # el subtítulo se omite si el título ya trae el tipo de labor (sin mayúsculas ni tildes)
    if not (title and _strip(table.labor_type).lower() in _strip(title).lower()):
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


def _cells(fig, table: LaborTable, rect, colors, style, show_lines):
    from matplotlib.patches import Rectangle
    from matplotlib.patheffects import withStroke

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
                # el rayado toma el color del borde (matplotlib ≥ 3.8), así que el borde oscuro va en otro parche
                p = Rectangle((k, r), 1, 1, facecolor=_NA_BG, edgecolor=_NA_HATCH, hatch="///", linewidth=0)
                p.set_gid(f"dashed:{code}")
                ax.add_patch(p)
                ax.add_patch(_rect(k, r, 1, 1, "none"))
                continue
            known = cell is not None and cell.support in colors
            bg = colors[cell.support] if known else _UNDEFINED
            p = _rect(k, r, 1, 1, bg)
            p.set_gid(code)
            ax.add_patch(p)
            second = cell.support if known else text("undefined", style.lang)
            ink = _ink(bg)
            # contorno del color opuesto y zorder alto: las líneas RMR′ no cortan el texto
            halo = [withStroke(linewidth=3, foreground="white" if ink == "black" else "#222222")]
            ax.text(k + 0.5, r + 0.5, f"{code}\n{second}", ha="center", va="center", color=ink,
                    fontsize=style.font_size, zorder=5, path_effects=halo)
    if show_lines:
        _rmr_lines(ax, ns, nc, style)
    ax.set_xticks([k + 0.5 for k in range(nc)], [f"{c}\n{_axis_label('cond', c, lbl, style.lang)}" for c, lbl in chart.conditions],
                  fontsize=style.font_size - 1)
    ax.set_yticks([r + 0.5 for r in range(ns)], [f"{s}\n{_axis_label('struct', s, lbl, style.lang)}" for s, lbl in chart.structures],
                  fontsize=style.font_size - 1)
    ax.xaxis.tick_top()
    ax.xaxis.set_label_position("top")
    ax.set_xlabel(text("condition_axis", style.lang), fontsize=style.font_size)
    ax.set_ylabel(text("structure_axis", style.lang), fontsize=style.font_size)
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)


def _rmr_lines(ax, ns, nc, style):
    """Líneas RMR′ finas y oscuras, con su valor en el extremo superior."""
    from matplotlib.patheffects import withStroke

    halo = [withStroke(linewidth=1.8, foreground="white")]  # sin el halo, la línea se pierde en las celdas moradas
    for i, ln in enumerate(RMR_PRIME_LINES):
        x0, y0, x1, y1 = ln.x0 * nc, ln.y0 * ns, ln.x1 * nc, ln.y1 * ns
        ax.plot([x0, x1], [y0, y1], color="0.15", linewidth=0.7, gid=f"rmr_line:{ln.value:g}", path_effects=halo)
        # el rótulo va sobre la línea, un poco hacia adentro para no pisar el borde de la cuadrícula
        k = 0.12 / math.hypot(x1 - x0, y1 - y0)
        ax.text(x1 - k * (x1 - x0), y1 - k * (y1 - y0), (f"RMR′ {ln.value:g}" if i == 0 else f"{ln.value:g}"), ha="center", va="center",
                fontsize=style.font_size - 2, color="0.15",
                bbox=dict(boxstyle="round,pad=0.1", facecolor="white", edgecolor="none", alpha=0.8))


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
        second = c.support if known else text('undefined', style.lang)
        label = f"{c.label}  ({c.lo:g}–{c.hi:g})"
        if second != c.label.strip():  # etiqueta igual al código: se muestra una sola vez
            label += f"  {second}"
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
                  show_lines: bool = True):
    """Cartilla de la tabla por labor: cuadrícula de celdas o barra de rangos, más leyenda del catálogo.

    Con show_lines=True, la cartilla de Vallejo lleva las líneas RMR′ digitalizadas y su fuente en el pie.
    """
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
    lines = show_lines and is_cells and table.table.chart.chart_id == _LINES_CHART
    if is_cells:
        _cells(fig, table, body, colors, style, lines)
    else:
        _ranges(fig, table, body, colors, style)
    _legend(fig, [0.04, 0.07, 0.92, legend_h], ordered, colors, style)
    source = f"{table.table.base_edition} · {text('engineer_decides', style.lang)}"
    if not is_cells:
        source += f" · {text('boundary_rule', style.lang)}"
    if lines:
        source += "\n" + text("lines_source", style.lang)
    footer(fig, source, style)
    return fig
