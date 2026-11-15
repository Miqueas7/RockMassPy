"""Análisis de túneles circulares: GRC, LDP, cruce con el sostenimiento, squeezing, avisos de alcance e incertidumbre
(Fase 8B, tarea 6). Une el núcleo (GRC de Mohr-Coulomb y de Hoek-Brown, LDP, interacción, Hoek y Marinos) con la tabla de
capacidades de la Tarea 5 y con el muestreo de la Fase 7. Los avisos y errores nunca repiten valores de entrada."""

from __future__ import annotations

import dataclasses
import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from . import _rockmasspy_core as rm
from .probabilistic import Distribution, sample_model
from .support_capacity import SupportCapacity
from .uncertainty import UNCERTAINTY_INFO, Summary, UncertaintyResult, _summary

_LDP = {"PANET1995": rm.Ldp.PANET1995, "UNLU_GERCEK2003": rm.Ldp.UNLU_GERCEK2003, "CHERN1998": rm.Ldp.CHERN1998,
        "VD2009": rm.Ldp.VD2009}
_COMB = {"stiffness": rm.Combination.STIFFNESS, "rocsupport3": rm.Combination.ROCSUPPORT3,
         "rocsupport": rm.Combination.ROCSUPPORT}
_EDITION = {"HB2002": rm.HbEdition.HB2002, "HB2018": rm.HbEdition.HB2018}
_CLASSES = ("A", "B", "C", "D", "E")

W_K = "analytical GRC assumes a hydrostatic field (K = 1)"
W_SHAPE = "analytical GRC assumes a circular opening; use an equivalent radius with care"
W_LARGE = "large strain: small-strain solution may underestimate convergence"
N_FIT = "squeezing correlation used outside its fitted range (sigma_cm/p0 or pi/p0 above 0.5)"


@dataclass(frozen=True)
class TunnelInput:
    radius_m: float
    p0_mpa: float
    nu: float
    criterion: str  # "MC" | "HB"
    e_mpa: float | None = None
    c_mpa: float | None = None
    phi_deg: float | None = None
    sigma_ci_mpa: float | None = None
    gsi: float | None = None
    mi: float | None = None
    d: float = 0.0
    mb: float | None = None
    s: float | None = None
    a: float | None = None
    psi_deg: float = 0.0
    k_ratio: float = 1.0
    shape: str = "circular"
    hb_edition: str = "HB2002"


@dataclass(frozen=True)
class TunnelResult:
    method: str
    info: rm.MethodInfo
    p_crit_mpa: float
    rp_m: float
    u_max_m: float
    strain_pct: float
    squeezing: rm.Squeezing
    grc: tuple[tuple[float, float], ...]
    ldp_model: str
    u_install_m: float | None
    interaction: rm.Interaction | None
    warnings: tuple[str, ...]
    notes: tuple[str, ...]
    radius_m: float | None = None  # para dibujar el LDP; los llena analyze_tunnel
    nu: float | None = None
    install_distance_m: float | None = None

    @property
    def needs_attention(self) -> bool:
        i = self.interaction
        bad_fs = i is not None and (not i.found or i.fs is None or i.fs < 1)
        return bool(bad_fs or self.squeezing.squeezing_class in ("C", "D", "E") or self.warnings)


def _need(inp: TunnelInput, *names: str) -> None:
    for n in names:
        if getattr(inp, n) is None:
            raise ValueError(f"parameter '{n}' is required for criterion '{inp.criterion}'")


def _ground(inp: TunnelInput):
    """(entrada del núcleo, función de interacción, función de GRC, σcm para el squeezing)."""
    if inp.criterion not in ("MC", "HB"):
        raise ValueError("criterion must be 'MC' or 'HB'")
    if inp.hb_edition not in _EDITION:
        raise ValueError("hb_edition must be 'HB2002' or 'HB2018'")
    if inp.criterion == "MC":
        _need(inp, "e_mpa", "c_mpa", "phi_deg")
        g = rm.GrcMcInput(radius_m=inp.radius_m, p0_mpa=inp.p0_mpa, e_mpa=inp.e_mpa, nu=inp.nu, c_mpa=inp.c_mpa,
                          phi_deg=inp.phi_deg, psi_deg=inp.psi_deg)
        phi = math.radians(inp.phi_deg)
        return g, rm.interaction_mc, rm.grc_mc, 2 * inp.c_mpa * math.cos(phi) / (1 - math.sin(phi))
    _need(inp, "sigma_ci_mpa")
    mb, s, a = inp.mb, inp.s, inp.a
    if inp.gsi is not None and inp.mi is not None:
        p = rm.hb_params(inp.gsi, inp.mi, inp.d, _EDITION[inp.hb_edition])
        mb, s, a = p.mb, p.s, p.a
    a = 0.5 if a is None else a
    if abs(a - 0.5) > 1e-9:  # D2: equivalente Mohr-Coulomb al estilo RocSupport
        _need(inp, "gsi", "mi")
        g = rm.grc_mc_from_hb(inp.sigma_ci_mpa, inp.gsi, inp.mi, inp.d, inp.p0_mpa, inp.radius_m, inp.nu,
                              _EDITION[inp.hb_edition])
        g.psi_deg = inp.psi_deg
        return g, rm.interaction_mc, rm.grc_mc, g.sigma_cm_override_mpa
    _need(inp, "e_mpa")
    if mb is None or s is None:
        raise ValueError("parameter 'gsi' (with 'mi') or parameters 'mb' and 's' are required for criterion 'HB'")
    g = rm.GrcHbInput(radius_m=inp.radius_m, p0_mpa=inp.p0_mpa, g_mpa=inp.e_mpa / (2 * (1 + inp.nu)), nu=inp.nu,
                      sigma_ci_mpa=inp.sigma_ci_mpa, mb=mb, s=s, psi_deg=inp.psi_deg)
    return g, rm.interaction_hb, rm.grc_hb, inp.sigma_ci_mpa * math.sqrt(s)


def _pick(table, key, name):
    if key not in table:
        raise ValueError(f"{name} must be one of: {', '.join(table)}")
    return table[key]


def analyze_tunnel(inp: TunnelInput, *, supports: Sequence[SupportCapacity | rm.SupportElement] = (),
                   install_distance_m: float | None = None, ldp: str = "VD2009", combination: str = "stiffness",
                   n_points: int = 50, support_diameter_m: float | None = None) -> TunnelResult:
    ldp_e, comb = _pick(_LDP, ldp, "ldp"), _pick(_COMB, combination, "combination")
    g, interact, grc_fn, sigma_cm = _ground(inp)
    grc = grc_fn(g, n_points)
    r, notes, warns = inp.radius_m, list(grc.notes), []
    strain = grc.u_max_m / r * 100
    sq = rm.hoek_marinos(sigma_cm, inp.p0_mpa, 0.0, r)  # sin sostenimiento: pi = 0
    if not sq.in_fit_range:
        notes.append(N_FIT)
    if inp.k_ratio != 1:
        warns.append(W_K)
    if inp.shape != "circular":
        warns.append(W_SHAPE)
    if strain > 10:
        warns.append(W_LARGE)
    u_in, inter = None, None
    if install_distance_m is not None:
        u_in = rm.ldp_ratio(ldp_e, install_distance_m / r, grc.rp_unsupported_m / r, inp.nu) * grc.u_max_m
    if supports:
        if u_in is None:
            raise ValueError("install_distance_m is required when supports are given")
        els = [s.to_element(support_diameter_m or 2 * r) if isinstance(s, SupportCapacity) else s for s in supports]
        inter = interact(g, els, u_in, comb, ldp_e)
        warns += inter.warnings
    return TunnelResult(
        grc.info.method_id, grc.info, grc.p_crit_mpa, grc.rp_unsupported_m, grc.u_max_m, strain, sq,
        tuple((p.pi_mpa, p.u_m) for p in grc.curve), ldp, u_in, inter, tuple(dict.fromkeys(warns)),
        tuple(dict.fromkeys(notes)), r, inp.nu, install_distance_m)


def tunnel_uncertainty(inp: TunnelInput, variables: Mapping[str, Distribution], *,
                       supports: Sequence[SupportCapacity | rm.SupportElement] = (),
                       install_distance_m: float | None = None, ldp: str = "VD2009",
                       combination: str = "stiffness", n: int = 2000, sampling: str = "lhs",
                       seed: int = 1, support_diameter_m: float | None = None) -> UncertaintyResult:
    numeric = [f.name for f in dataclasses.fields(TunnelInput)
               if f.name not in ("criterion", "shape", "hb_edition")]
    for name in variables:
        if name not in numeric:
            raise ValueError(f"unknown variable '{name}'; allowed: {', '.join(numeric)}")
    if not variables:
        raise ValueError("at least one variable is required")
    classes, below = Counter(), [0]

    def one(draw):
        r = analyze_tunnel(dataclasses.replace(inp, **draw), supports=supports,
                           install_distance_m=install_distance_m, ldp=ldp, combination=combination, n_points=2,
                           support_diameter_m=support_diameter_m)
        outs = {"rp_m": r.rp_m, "strain_pct": r.strain_pct}
        classes[r.squeezing.squeezing_class] += 1
        if r.interaction is not None:
            fs = r.interaction.fs
            if fs is not None:
                outs["fs"] = fs
            below[0] += fs is None or fs < 1  # sin cruce cuenta como falla, el lado menos favorable
        return outs, list(r.warnings)

    ms = sample_model(one, variables, n=n, sampling=sampling, seed=seed)
    k = ms.n_valid
    return UncertaintyResult(
        "Tunnel-GRC", sampling, n, seed, k, tuple(sorted(variables)),
        {name: _summary(v) for name, v in ms.outputs.items()},
        {c: classes[c] / k for c in _CLASSES} if k else {},
        {"fs_below_1": below[0] / k} if k and supports else {}, UNCERTAINTY_INFO, ms.warnings, ms.notes)
