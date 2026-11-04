"""Sección de equilibrio límite con la superficie crítica, y el desplazamiento de Newmark (3C, tarea 7).

Los FS, la superficie y las 10 mejores salen de `LeAnalysisResult`; la figura no recalcula nada. Los estratos se rotulan
por su orden (Estrato 1 arriba), nunca por el material, y ningún id llega a la figura (Foco 5).
"""

from __future__ import annotations

import math

from .style import Style, footer, new_figure, text

# Paleta neutra por estrato (arena, ocre, grises) con un rayado distinto para que se lea en blanco y negro
_LAYER_COLORS = ("#EFE8D8", "#D9CCAF", "#BFB195", "#E2E2E2", "#C6C6C6", "#A9A9A9")
_LAYER_HATCH = ("", "..", "//", "xx", "\\\\", "++")
_CRITICAL = "#B03A2E"


def _interp(xs, pts):
    import numpy as np

    return np.interp(xs, [p.x for p in pts], [p.y for p in pts])


def _method_name(m, lang) -> str:
    return text(f"le_method_{m.name}", lang)


def _slip_trace(f, xs, ground):
    """Traza de una superficie bajo el terreno: el arco del círculo bajo la superficie o la polilínea tal cual."""
    import numpy as np

    if f.circle is not None:
        c = f.circle
        x = np.linspace(c.xc - c.radius, c.xc + c.radius, 400)
        x = x[(x >= xs[0]) & (x <= xs[-1])]
        y = c.yc - np.sqrt(np.maximum(c.radius ** 2 - (x - c.xc) ** 2, 0.0))
        g = np.interp(x, xs, ground)
        return x, np.where(y <= g + 1e-9, y, np.nan)  # NaN corta la línea donde el arco sale al aire
    return [p.x for p in f.polyline], [p.y for p in f.polyline]


def _critical_trace(result):
    """La superficie crítica por las bases de las tajadas: es la masa que de verdad se evaluó."""
    sl = next((r.slices for r in result.results if getattr(r, "slices", None)), None)
    if not sl:
        return None
    return ([s.x_left for s in sl] + [sl[-1].x_right], [s.base_y_left for s in sl] + [sl[-1].base_y_right])


def plot_le_section(result, *, title: str = "", style: Style = Style()):
    """Sección con estratos, línea piezométrica, superficie crítica, las 10 mejores en gris, centro y FS por método."""
    import numpy as np
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    lang, sec = style.lang, result.section
    if sec is None:
        raise ValueError("result has no section: use a result from assess_le")
    fig = new_figure(style)
    footer(fig, " | ".join(m.method_id for m in result.methods), style)
    ax = fig.add_axes([0.08, 0.12, 0.66, 0.8])
    ax.set_title(title or text("le_section_title", lang), fontsize=style.font_size + 2)
    ax.set_xlabel(text("le_x_axis", lang), fontsize=style.font_size)
    ax.set_ylabel(text("le_y_axis", lang), fontsize=style.font_size)

    surf, layers = list(sec.surface), list(sec.layers)
    x0, x1 = surf[0].x, surf[-1].x
    lines = [surf, *(lay.bottom for lay in layers if lay.bottom)]
    if sec.piezometric is not None:
        lines.append(sec.piezometric)
    xs = np.unique(np.concatenate([np.linspace(x0, x1, 600)] + [[p.x for p in ln if x0 <= p.x <= x1] for ln in lines]))
    ground = _interp(xs, surf)
    crit = _critical_trace(result)
    lows = [ground.min(), *(_interp(xs, lay.bottom).min() for lay in layers if lay.bottom)]
    if crit:
        lows.append(min(crit[1]))
    height = max(ground.max() - min(lows), 1e-9)
    base = sec.model_base_y if sec.model_base_y is not None else min(lows) - 0.1 * height

    handles = []
    prev = ground
    for k, lay in enumerate(layers):
        bot = np.minimum(prev, _interp(xs, lay.bottom)) if lay.bottom else np.full_like(xs, base)
        col, hatch = _LAYER_COLORS[k % len(_LAYER_COLORS)], _LAYER_HATCH[k % len(_LAYER_HATCH)]
        ax.fill_between(xs, bot, prev, where=prev > bot, facecolor=col, edgecolor="#6E6E6E", hatch=hatch,
                        linewidth=0.0, interpolate=True, zorder=1)
        if lay.bottom:
            ax.plot(xs, bot, color="#6E6E6E", lw=0.8, zorder=2)
        handles.append(Patch(facecolor=col, edgecolor="#6E6E6E", hatch=hatch,
                             label=text("le_layer", lang).format(n=k + 1)))
        prev = bot
    ax.plot(xs, ground, color="black", lw=1.6, zorder=5)
    handles.append(Line2D([], [], color="black", lw=1.6, label=text("le_ground", lang)))
    if sec.piezometric is not None:
        ax.plot(xs, np.minimum(_interp(xs, sec.piezometric), ground), color="#2F6DB5", lw=1.3, ls="--", zorder=5)
        handles.append(Line2D([], [], color="#2F6DB5", lw=1.3, ls="--", label=text("le_piezometric", lang)))

    top = list(result.search.top) if result.search is not None else []
    for f, _ in top:
        ax.plot(*_slip_trace(f, xs, ground), color="#8C8C8C", lw=0.7, zorder=3)
    if top:
        handles.append(Line2D([], [], color="#8C8C8C", lw=0.7, label=text("le_top", lang).format(n=len(top))))
    if result.surface is not None:
        x, y = crit or _slip_trace(result.surface, xs, ground)
        ax.plot(x, y, color=_CRITICAL, lw=2.4, zorder=6)
        key = "le_given" if result.surface_type == "given" else "le_critical"
        handles.append(Line2D([], [], color=_CRITICAL, lw=2.4, label=text(key, lang)))
        c = result.surface.circle
        if c is not None:
            ax.scatter([c.xc], [c.yc], marker="o", c="white", edgecolors="black", linewidths=1.2, s=60, zorder=7)
            handles.append(Line2D([], [], ls="", marker="o", markersize=7, markerfacecolor="white",
                                  markeredgecolor="black", label=text("le_centre", lang)))
    else:
        ax.text(0.5, 0.5, text("le_no_surface", lang), ha="center", va="center", transform=ax.transAxes,
                fontsize=style.font_size + 2)

    fs_lines = [f"{_method_name(r.method, lang)}: " + (text("le_no_fs", lang) if r.factor_of_safety is None
                                                       else f"FS = {r.factor_of_safety:.3f}") for r in result.results]
    if sec.kh > 0:
        fs_lines.append(f"kh = {sec.kh:g}")
    if result.yield_ is not None and result.yield_.ky is not None:
        fs_lines.append(f"ky = {result.yield_.ky:.3f}")
    fig.text(0.765, 0.70, "\n".join(fs_lines), ha="left", va="top",  # fuera de los ejes: no tapa el centro
             fontsize=style.font_size + 1, fontweight="bold",
             bbox=dict(facecolor="white", edgecolor="black", linewidth=0.6))
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(x0, x1)
    c = result.surface.circle if result.surface is not None else None
    ymax = max(ground.max(), c.yc if c is not None else -math.inf)  # el centro del círculo tiene que verse
    ax.set_ylim(base, ymax + 0.15 * (ymax - base))
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.76, 0.92), fontsize=style.font_size - 1,
               frameon=True)
    return fig


def plot_newmark(result, accelerogram, ky: float, *, title: str = "", style: Style = Style()):
    """Registro (en g) con la línea de ky y el desplazamiento acumulado del bloque rígido.

    `accelerogram` es el registro ya escalado que usó Newmark (`LeAnalysisResult.record`); con los dos sentidos
    (nota «both directions» del resultado) se dibuja también −ky.
    """
    if not (isinstance(ky, (int, float)) and math.isfinite(ky) and ky > 0):
        raise ValueError("ky must be a finite number > 0")
    lang = style.lang
    acc = list(accelerogram.acceleration_g)
    t = [i * accelerogram.dt_s for i in range(len(acc))]
    hist = list(result.displacement_history_m)
    if len(hist) != len(acc):
        raise ValueError("accelerogram and Newmark result have different lengths: pass the record Newmark used")
    fig = new_figure(style)
    footer(fig, result.info.method_id, style)
    a1 = fig.add_axes([0.09, 0.56, 0.86, 0.36])
    a2 = fig.add_axes([0.09, 0.12, 0.86, 0.36], sharex=a1)
    a1.set_title(title or text("newmark_title", lang), fontsize=style.font_size + 2)
    a1.plot(t, acc, color="#555555", lw=0.8, label=text("newmark_record", lang))
    a1.axhline(ky, color=_CRITICAL, lw=1.4, ls="--", label=f"ky = {ky:.3f} g")
    if any(n.startswith("both directions") for n in result.notes):
        a1.axhline(-ky, color=_CRITICAL, lw=1.4, ls="--")
    a1.axhline(0, color="black", lw=0.5)
    a1.set_ylabel(text("newmark_acc", lang), fontsize=style.font_size)
    a1.legend(loc="upper right", fontsize=style.font_size - 1)
    a2.plot(t, hist, color="black", lw=1.4)
    a2.set_xlabel(text("newmark_time", lang), fontsize=style.font_size)
    a2.set_ylabel(text("newmark_disp", lang), fontsize=style.font_size)
    a2.text(0.02, 0.92, text("newmark_total", lang).format(d=result.displacement_m), transform=a2.transAxes,
            ha="left", va="top", fontsize=style.font_size + 2, fontweight="bold")
    return fig
