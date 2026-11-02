"""Red estereográfica (hemisferio inferior, norte arriba) con polos, familias, cara y zonas críticas de Markland.

Las zonas se sombrean con los mismos criterios del núcleo (`check_plane`, `check_intersection`) sobre una grilla,
así la figura y los conteos no pueden discrepar. Solo se rotulan códigos de familia: nunca un id_talud ni un id_tramo.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from .. import _rockmasspy_core as rm
from .style import Style, footer, new_figure, support_color, text

MODES = ("planar", "wedge", "flexural_toppling", "direct_toppling")
_PROJ = {"equal_area": rm.Projection.EqualArea, "equal_angle": rm.Projection.EqualAngle}
_DENSITY_GRID = 61
_ZONE_GRID = 321
_LINE = "#08306B"  # azul oscuro: fronteras y borde de la zona, distinto de la paleta de la densidad
_FILL = "#9ECAE1"


def _line(t, p):
    return rm.LineOrientation(t % 360.0, p)


def _circle(plunge):  # pequeño círculo de inmersión constante
    return [_line(t, plunge) for t in range(361)]


def _radial(trend):  # del centro al primitivo, en la tendencia dada
    return [_line(trend, 90.0), _line(trend, 0.0)]


def _envelope(face, lim):
    """Polos de los planos con el buzamiento aparente de la cara en cada dirección dentro del límite lateral."""
    bs = math.radians(face.dip_deg)
    out = []
    for k in range(61):
        d = -lim + 2 * lim * k / 60
        app = math.degrees(math.atan2(math.sin(bs) * math.cos(math.radians(d)), math.cos(bs)))
        out.append(_line(face.dip_direction_deg + 180.0 + d, 90.0 - max(app, 0.0)))
    return out


def _great(plane, proj):
    return [(p.x, p.y) for p in rm.great_circle(plane, proj, 181)]


def _boundaries(mode, face, phi, lim):
    """[(clave de texto, estilo, líneas | plano)]: fronteras de cada modo; un plano se dibuja como círculo máximo."""
    a, bs = face.dip_direction_deg, face.dip_deg

    def lat(base):
        return [("stereo_lateral_limits", "-.", _radial(base - lim)), ("stereo_lateral_limits", "-.", _radial(base + lim))]

    if mode == "planar":
        return [("stereo_daylight", "--", _envelope(face, lim)), ("stereo_friction_cone", ":", _circle(90 - phi)),
                *lat(a + 180)]
    if mode == "wedge":
        return [("stereo_friction_cone", ":", _circle(phi)),
                ("stereo_slip_limit", "--", rm.PlaneOrientation(a, phi))]
    if mode == "flexural_toppling":
        return ([("stereo_slip_limit", "--", rm.PlaneOrientation(a, bs - phi))] if bs > phi else []) + lat(a)
    return [("stereo_slip_limit", "--", _circle(90 - bs)), ("stereo_friction_cone", ":", _circle(90 - phi)),
            *lat(a + 180)]


def _critical(mode, line, ki):
    if mode in ("planar", "flexural_toppling"):  # la grilla son polos
        c = rm.check_plane(rm.plane_of(line), ki)
        return c.planar if mode == "planar" else c.flexural_toppling
    c = rm.check_intersection(line, ki)
    if mode == "wedge":
        return c.wedge_primary or c.wedge_secondary
    return 1 if c.direct_toppling else 2 if c.direct_toppling_oblique else 0  # zonas 1-2 y zona 3 (oblicua)


def _grid(n, proj):
    """Grilla n × n del cuadrado y sus líneas; fuera del primitivo se usa el borde (se recorta al dibujar)."""
    import numpy as np

    xs = np.linspace(-1.0, 1.0, n)
    X, Y = np.meshgrid(xs, xs)
    lines = []
    for x, y in zip(X.ravel(), Y.ravel()):
        r = math.hypot(x, y)
        s = min(1.0, 0.9999 / r) if r > 0 else 1.0
        lines.append(rm.unproject(rm.Point2(float(x * s), float(y * s)), proj))
    return X, Y, lines


def _counts(mode, planes, lines, ki):
    if mode in ("planar", "flexural_toppling"):
        key = "planar" if mode == "planar" else "flexural_toppling"
        return sum(getattr(rm.check_plane(p, ki), key) for p in planes), len(planes), None
    ch = [rm.check_intersection(x, ki) for x in lines]
    if mode == "wedge":
        return sum(c.wedge_primary or c.wedge_secondary for c in ch), len(ch), None
    return sum(c.direct_toppling for c in ch), len(ch), sum(c.direct_toppling_oblique for c in ch)


def _label(ax, code, plane, proj, taken, style):
    """Código de la familia sobre el punto medio de su círculo máximo (el de mayor buzamiento); si choca, en sus extremos."""
    a = plane.dip_direction_deg
    q = rm.project(_line(a, plane.dip_deg), proj)
    cands = [(q.x, q.y)]
    for r in (1.07, 1.15, 1.23):
        for t in (a + 270.0, a + 90.0):
            e = rm.project(_line(t, 0.0), proj)
            cands.append((e.x * r, e.y * r))
    x, y = next(((x, y) for x, y in cands if all(math.hypot(x - u, y - v) > 0.11 for u, v in taken)), cands[-1])
    taken.append((x, y))  # si todo choca, se dibuja igual en el último: nunca se omite
    ax.text(x, y, code, ha="center", va="center", fontsize=style.font_size, zorder=8,
            bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="none"))


def plot_stereonet(planes: Sequence[rm.PlaneOrientation] = (), *,
                   families: Sequence[tuple[str, rm.PlaneOrientation]] = (),
                   face: rm.PlaneOrientation | None = None, friction_deg: float | None = None,
                   lateral_limit_deg: float | None = None, mode: str | None = None,
                   intersections: Sequence[rm.LineOrientation] = (), projection: str = "equal_area",
                   density: bool = True, area_fraction: float = 0.01, style: Style = Style()):
    """Red estereográfica: polos, densidad, planos medios, cara y, con `mode`, su zona crítica de Markland."""
    if projection not in _PROJ:
        raise ValueError(f"projection must be one of {', '.join(_PROJ)}, got {projection!r}")
    if mode is not None:
        if mode not in MODES:
            raise ValueError(f"mode must be one of {', '.join(MODES)}, got {mode!r}")
        if face is None or friction_deg is None:
            raise ValueError("mode needs face and friction_deg")
        if lateral_limit_deg is None and mode != "wedge":
            raise ValueError(f"mode {mode!r} needs lateral_limit_deg")
    proj, lang = _PROJ[projection], style.lang
    fig = new_figure(style)  # primero: si falta matplotlib, el error nombra rockmasspy[viz]
    from matplotlib.lines import Line2D
    from matplotlib.patches import Circle, Patch

    ax = fig.add_axes([0.04, 0.10, 0.62, 0.80])
    ax.set_aspect("equal")
    ax.set_xlim(-1.18, 1.18)
    ax.set_ylim(-1.18, 1.18)
    ax.axis("off")
    ax.set_title(text("stereo_title", lang), fontsize=style.font_size + 2)
    ax.add_patch(Circle((0, 0), 1.0, fill=False, edgecolor="black", linewidth=1.3, zorder=6))
    clip = Circle((0, 0), 1.0, transform=ax.transData)
    ax.text(0, 1.04, "N", ha="center", va="bottom", fontsize=style.font_size + 1, fontweight="bold")
    taken = [(0.0, 1.10)]  # posiciones de rótulos ya puestas

    poles = [rm.pole_of(p) for p in planes]

    def xy(lines):
        return [(q.x, q.y) for q in (rm.project(x, proj) for x in lines)]

    handles = []
    if density and len(poles) >= 3:
        import numpy as np

        X, Y, at = _grid(_DENSITY_GRID, proj)
        Z = np.array(rm.pole_density(poles, at, area_fraction)).reshape(X.shape)
        top = float(Z.max())
        if top > 0:
            levels = [top * k / 5 for k in range(6)]
            levels[0] = top / 10  # lo que queda debajo no se pinta
            cs = ax.contourf(X, Y, Z, levels=levels, colors=[support_color(k, 5, style) for k in range(1, 6)], zorder=1)
            cs.set_clip_path(clip)
            cax = fig.add_axes([0.76, 0.12, 0.02, 0.30])
            fig.colorbar(cs, cax=cax).set_label(text("stereo_density", lang), fontsize=style.font_size)
            cax.tick_params(labelsize=style.font_size - 1)

    ki = None
    if mode is not None:
        import numpy as np

        lim = lateral_limit_deg if lateral_limit_deg is not None else 30.0  # la cuña no lo usa
        ki = rm.KinematicInput(face, friction_deg, lim)
        X, Y, at = _grid(_ZONE_GRID, proj)
        V = np.array([float(_critical(mode, ln, ki)) for ln in at]).reshape(X.shape)
        Z = (V == 1).astype(float)
        if (V == 2).any():  # volteo oblicuo (zona 3): mismo tono, con trama
            for cs in (ax.contourf(X, Y, (V == 2).astype(float), levels=[0.5, 1.5], colors=[_FILL], alpha=0.15,
                                   hatches=["///"], zorder=2),
                       ax.contour(X, Y, (V == 2).astype(float), levels=[0.5], colors=[_LINE], linewidths=0.8,
                                  linestyles="dashed", zorder=2)):
                cs.set_clip_path(clip)
        if Z.max() > 0:
            for cs in (ax.contourf(X, Y, Z, levels=[0.5, 1.5], colors=[_FILL], alpha=0.35, zorder=2),
                       ax.contour(X, Y, Z, levels=[0.5], colors=[_LINE], linewidths=1.0, zorder=2)):
                cs.set_clip_path(clip)
        handles.append(Patch(facecolor=_FILL, edgecolor=_LINE, alpha=0.8, label=text("stereo_critical_zone", lang)))
        if (V == 2).any():
            handles.append(Patch(facecolor="none", edgecolor=_LINE, hatch="///", label=text("stereo_oblique_zone", lang)))
        seen = set()
        for key, ls, geo in _boundaries(mode, face, friction_deg, lim):
            pts = _great(geo, proj) if isinstance(geo, rm.PlaneOrientation) else xy(geo)
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color=_LINE, linestyle=ls, linewidth=1.1, zorder=4)
            if key not in seen:
                seen.add(key)
                handles.append(Line2D([], [], color=_LINE, linestyle=ls, label=text(key, lang)))

    if face is not None:
        pts = _great(face, proj)
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color="black", linewidth=2.6, zorder=5)
        handles.append(Line2D([], [], color="black", linewidth=2.6, label=text("stereo_face", lang)))
    for code, plane in families:
        pts = _great(plane, proj)
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color="0.25", linewidth=1.0, zorder=4)
        _label(ax, code, plane, proj, taken, style)
    for pts_, marker, size, key in ((xy(poles), "o", 22, "stereo_poles"), (xy(intersections), "^", 26, "stereo_intersections")):
        if pts_:  # blanco con borde negro, legible sobre cualquier relleno
            ax.scatter([p[0] for p in pts_], [p[1] for p in pts_], marker=marker, c="white", edgecolors="black",
                       linewidths=0.6, s=size, zorder=7)
            handles.append(Line2D([], [], ls="", marker=marker, markerfacecolor="white", markeredgecolor="black",
                                  label=text(key, lang)))
    if handles:
        ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.02, 1.0), fontsize=style.font_size - 1)

    lines = [" | ".join(filter(None, (
        text("stereo_equal_area" if projection == "equal_area" else "stereo_equal_angle", lang),
        text(f"stereo_mode_{mode}", lang) if mode else "",
        rm.kinematic_analysis([], [], ki).methods[MODES.index(mode)].method_id if mode else "",
        text("engineer_decides", lang))))]
    if mode:
        k, n, k2 = _counts(mode, list(planes), list(intersections), ki)
        if n:
            pct = f"{100 * k / n:.0f}"
            head = (text("stereo_count", lang).format(k=k, n=n, pct=pct) if k2 is None else
                    text("stereo_count_oblique", lang).format(k=k, n=n, pct=pct, k2=k2, pct2=f"{100 * k2 / n:.0f}"))
            lines.insert(0, head + " | " + text("stereo_feasibility", lang))
    footer(fig, "\n".join(lines), style)
    return fig
