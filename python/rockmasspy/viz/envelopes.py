"""Envolventes de Hoek-Brown (curva) y de Mohr-Coulomb (recta) en σ1–σ3 y en τ–σn."""

from __future__ import annotations

import math
from collections.abc import Sequence

from .. import MohrCoulombFit, hb_normal_shear, hb_sigma1, hb_tensile
from .style import Style, footer, new_figure, text

_N = 200


def plot_hb_envelopes(
    sigma_ci_mpa: float,
    params,
    *,
    sigma3max_mpa: float,
    mc: MohrCoulombFit | None = None,
    tests: Sequence[tuple[float, float]] = (),
    style: Style = Style(),
):
    """Izquierda σ1–σ3 (con ensayos (σ3, σ1)), derecha τ–σn; la curva HB va de σt a sigma3max_mpa."""
    st = hb_tensile(sigma_ci_mpa, params)
    if not sigma3max_mpa > st:
        raise ValueError(f"sigma3max_mpa must be greater than the tensile strength {st:g}, got {sigma3max_mpa!r}")

    import numpy as np  # viene con matplotlib

    # Espaciado geométrico de (σ3 − σt): más puntos cerca de la tracción, donde la curva se dobla.
    t = np.concatenate(([0.0], np.geomspace(1e-4, 1.0, _N - 1)))
    s3 = st + (sigma3max_mpa - st) * t
    s3[-1] = sigma3max_mpa
    s1 = [hb_sigma1(float(x), sigma_ci_mpa, params) for x in s3]
    ns = [hb_normal_shear(float(x), sigma_ci_mpa, params) for x in s3]
    sn, tau = [r.sigma_n_mpa for r in ns], [r.tau_mpa for r in ns]

    lang = style.lang
    fig = new_figure(style)
    a1, a2 = fig.subplots(1, 2)
    a1.plot(s3, s1, color="#1F4E79", label=text("hb_curve", lang))
    a2.plot(sn, tau, color="#1F4E79", label=text("hb_curve", lang))
    if mc is not None:
        # shortcut: recta de dibujo de Mohr-Coulomb a partir de c′ y φ′, no es un resultado; pasar al núcleo si se necesita como resultado
        phi = math.radians(mc.phi_deg)
        k = (1 + math.sin(phi)) / (1 - math.sin(phi))
        scm = 2 * mc.cohesion_mpa * math.cos(phi) / (1 - math.sin(phi))
        a1.plot(s3, scm + k * s3, color="#C0392B", linestyle="--", label=text("mc_line", lang))
        sn_line = np.array([0.0, max(sn)])
        a2.plot(sn_line, mc.cohesion_mpa + sn_line * math.tan(phi), color="#C0392B", linestyle="--", label=text("mc_line", lang))
    if tests:
        a1.scatter([p[0] for p in tests], [p[1] for p in tests], color="#2E7D32", zorder=3, label=text("lab_tests", lang))

    fs = style.font_size
    a1.set_title(text("hb_envelope_title", lang), fontsize=fs + 2)
    a1.set_xlabel(text("sigma3_axis", lang), fontsize=fs)
    a1.set_ylabel(text("sigma1_axis", lang), fontsize=fs)
    a2.set_xlabel(text("sigma_n_axis", lang), fontsize=fs)
    a2.set_ylabel(text("tau_axis", lang), fontsize=fs)
    for ax in (a1, a2):
        ax.grid(alpha=0.25)
        ax.legend(fontsize=fs - 1)
    fig.subplots_adjust(bottom=0.12, wspace=0.25)

    src = f"{params.info.method_id} · σci {sigma_ci_mpa:g} MPa"
    if mc is not None:
        src += f" · c′ {mc.cohesion_mpa:.3g} MPa, φ′ {mc.phi_deg:.1f}°"
    footer(fig, src, style)
    return fig
