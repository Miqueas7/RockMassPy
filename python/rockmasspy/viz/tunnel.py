"""Figura del túnel: GRC con la SCC y su cruce, y el LDP con la distancia de instalación. Diagrama de capacidad del
revestimiento (N, M)."""

from __future__ import annotations

import os

from .. import _rockmasspy_core as rm
from .save import save_figure
from .style import Style, footer, new_figure, text

_LDP = {"PANET1995": rm.Ldp.PANET1995, "UNLU_GERCEK2003": rm.Ldp.UNLU_GERCEK2003, "CHERN1998": rm.Ldp.CHERN1998,
        "VD2009": rm.Ldp.VD2009}


def tunnel_figure(result, *, lang: str = "es"):
    """Figura (matplotlib) de un TunnelResult; `plot_tunnel` la guarda."""
    style = Style(lang=lang)
    fig = new_figure(style)
    fs = style.font_size
    ax = fig.add_axes([0.08, 0.14, 0.52, 0.76])
    ax.plot([u * 1e3 for _, u in result.grc], [p for p, _ in result.grc], color="black", lw=1.6,
            label=text("tn_grc", lang))
    i, u_in = result.interaction, result.u_install_m
    if i is not None and u_in is not None:
        if result.scc:
            ax.plot([u * 1e3 for u, _ in result.scc], [p for _, p in result.scc], color="tab:blue", lw=1.4,
                    label=text("tn_scc", lang))
        if i.found:
            ax.scatter([i.u_eq_m * 1e3], [i.p_eq_mpa], c="tab:red", zorder=5, label=text("tn_cross", lang))
        ax.axvline(u_in * 1e3, color="0.5", ls="--", lw=1, label=text("tn_install", lang))
    ax.set_xlabel(text("tn_u_axis", lang), fontsize=fs)
    ax.set_ylabel(text("tn_p_axis", lang), fontsize=fs)
    ax.set_title(text("tn_title", lang), fontsize=fs + 2)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=fs - 1)

    bx = fig.add_axes([0.68, 0.14, 0.29, 0.76])
    if result.radius_m and result.nu is not None and result.ldp_model in _LDP:
        r, ld = result.radius_m, _LDP[result.ldp_model]
        xs = [k / 10 for k in range(0, 61)]
        bx.plot(xs, [rm.ldp_ratio(ld, x, result.rp_m / r, result.nu) for x in xs], color="black", lw=1.4,
                label=text("tn_ldp_model", lang).format(m=result.ldp_model))
        if result.install_distance_m is not None and u_in is not None and result.u_max_m > 0:
            bx.scatter([result.install_distance_m / r], [u_in / result.u_max_m], c="tab:red", zorder=5,
                       label=text("tn_install", lang))
    bx.set_xlabel(text("tn_x_axis", lang), fontsize=fs)
    bx.set_ylabel(text("tn_ur_axis", lang), fontsize=fs)
    bx.set_title(text("tn_ldp_title", lang), fontsize=fs + 2)
    bx.grid(alpha=0.3)
    bx.legend(fontsize=fs - 1)
    footer(fig, f"{result.method} | {text('engineer_decides', lang)}", style)
    return fig


def plot_tunnel(result, path: str | os.PathLike, *, lang: str = "es"):
    return save_figure(tunnel_figure(result, lang=lang), path)


def lining_capacity_figure(section, forces, *, fs_values=(1.0, 1.5, 2.0), lang: str = "es"):
    """Envolvente (N, M) del revestimiento para cada FS, con los pares de diseño encima."""
    style = Style(lang=lang)
    fig = new_figure(style)
    ax = fig.add_axes([0.1, 0.14, 0.85, 0.76])
    for k, f in enumerate(fs_values):
        v = list(rm.capacity_mn(section, f).vertices)
        xs, ms = [p[0] for p in v], [p[1] for p in v]
        ax.plot(xs + xs[:1], ms + ms[:1], lw=1.4, color=("black", "tab:blue", "tab:green", "tab:purple")[k % 4],
                label=f"FS {f:g}")
    ax.scatter([x.n_mn for x in forces], [x.m_mnm for x in forces], c="tab:red", zorder=5, label=text("tn_demand", lang))
    ax.set_xlabel(text("tn_n_axis", lang), fontsize=style.font_size)
    ax.set_ylabel(text("tn_m_axis", lang), fontsize=style.font_size)
    ax.set_title(text("tn_cap_title", lang), fontsize=style.font_size + 2)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=style.font_size - 1)
    footer(fig, text("engineer_decides", lang), style)
    return fig


def plot_lining_capacity(section, forces, path: str | os.PathLike, *, fs_values=(1.0, 1.5, 2.0), lang: str = "es"):
    return save_figure(lining_capacity_figure(section, forces, fs_values=fs_values, lang=lang), path)
