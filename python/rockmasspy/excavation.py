"""Análisis de túneles circulares: GRC, LDP, cruce con el sostenimiento, squeezing, avisos de alcance e incertidumbre
(Fase 8B, tarea 6). Une el núcleo (GRC de Mohr-Coulomb y de Hoek-Brown, LDP, interacción, Hoek y Marinos) con la tabla de
capacidades de la Tarea 5 y con el muestreo de la Fase 7. Los avisos y errores nunca repiten valores de entrada."""

from __future__ import annotations

import dataclasses
import math
from collections import Counter
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
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
N_ERM = "Erm from Hoek-Carranza-Corkum (2002)"
N_E_USER = "e_mpa given by the user replaces Erm from Hoek-Carranza-Corkum (2002)"
N_A_IGNORED = "parameter 'a' is ignored: it comes from 'gsi', 'mi' and 'd'"
N_MBS_IGNORED = "parameters 'mb' and 's' are ignored: they come from 'gsi', 'mi' and 'd'"
N_VALIDITY = "outside model validity (strain > 100 %)"


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
    """(entrada del núcleo, función de interacción, función de GRC, σcm para el squeezing y notas). σcm va
    diferido: se calcula después de que el núcleo valide la entrada (con φ = 90° la fórmula se divide por cero)."""
    if inp.criterion not in ("MC", "HB"):
        raise ValueError("criterion must be 'MC' or 'HB'")
    if inp.hb_edition not in _EDITION:
        raise ValueError("hb_edition must be 'HB2002' or 'HB2018'")
    if inp.criterion == "MC":
        _need(inp, "e_mpa", "c_mpa", "phi_deg")
        g = rm.GrcMcInput(radius_m=inp.radius_m, p0_mpa=inp.p0_mpa, e_mpa=inp.e_mpa, nu=inp.nu, c_mpa=inp.c_mpa,
                          phi_deg=inp.phi_deg, psi_deg=inp.psi_deg)
        phi = math.radians(inp.phi_deg)
        return g, rm.interaction_mc, rm.grc_mc, lambda: 2 * inp.c_mpa * math.cos(phi) / (1 - math.sin(phi)), []
    _need(inp, "sigma_ci_mpa")
    mb, s, a, notes = inp.mb, inp.s, inp.a, []
    if inp.gsi is not None and inp.mi is not None:
        p = rm.hb_params(inp.gsi, inp.mi, inp.d, _EDITION[inp.hb_edition])
        if inp.a is not None:
            notes.append(N_A_IGNORED)
        if inp.mb is not None or inp.s is not None:
            notes.append(N_MBS_IGNORED)
        mb, s, a = p.mb, p.s, p.a
    a = 0.5 if a is None else a
    if abs(a - 0.5) > 1e-9:  # D2: equivalente Mohr-Coulomb al estilo RocSupport
        _need(inp, "gsi", "mi")
        g = rm.grc_mc_from_hb(inp.sigma_ci_mpa, inp.gsi, inp.mi, inp.d, inp.p0_mpa, inp.radius_m, inp.nu,
                              _EDITION[inp.hb_edition])
        g.psi_deg = inp.psi_deg
        if inp.e_mpa is not None:
            g.e_mpa = inp.e_mpa
        notes.append(N_E_USER if inp.e_mpa is not None else N_ERM)
        return g, rm.interaction_mc, rm.grc_mc, lambda: g.sigma_cm_override_mpa, notes
    if mb is None or s is None:
        raise ValueError("parameter 'gsi' (with 'mi') or parameters 'mb' and 's' are required for criterion 'HB'")
    e = inp.e_mpa
    if e is None and inp.gsi is not None:  # GSI = 100 da a = 0.5: mismo Erm que el camino D2, sin salto
        e = rm.em_hoek2002(inp.gsi, inp.d, inp.sigma_ci_mpa).value * 1000
        notes.append(N_ERM)
    elif e is None:
        _need(inp, "e_mpa")
    if not 0 <= inp.nu < 0.5:  # antes de G = E/(2(1+ν)), que con ν = −1 se divide por cero
        raise ValueError("parameter 'nu' must be within [0, 0.5)")
    g = rm.GrcHbInput(radius_m=inp.radius_m, p0_mpa=inp.p0_mpa, g_mpa=e / (2 * (1 + inp.nu)), nu=inp.nu,
                      sigma_ci_mpa=inp.sigma_ci_mpa, mb=mb, s=s, psi_deg=inp.psi_deg)
    # Hoek y Marinos usan la resistencia global del macizo (la misma σcm del camino D2), no σci·√s
    return g, rm.interaction_hb, rm.grc_hb, lambda: rm.hb_global_strength(
        inp.sigma_ci_mpa, rm.hb_params_from_constants(mb, s, 0.5)), notes


@contextmanager
def _no_values():
    """Los mensajes del núcleo traen «Received: valor»; la API de túneles nunca repite valores de entrada."""
    try:
        yield
    except ValueError as e:
        raise ValueError(str(e).split("Received:")[0].strip()) from None


def _pick(table, key, name):
    if key not in table:
        raise ValueError(f"{name} must be one of: {', '.join(table)}")
    return table[key]


def analyze_tunnel(inp: TunnelInput, *, supports: Sequence[SupportCapacity | rm.SupportElement] = (),
                   install_distance_m: float | None = None, ldp: str = "VD2009", combination: str = "stiffness",
                   n_points: int = 50, support_diameter_m: float | None = None) -> TunnelResult:
    with _no_values():
        ldp_e, comb = _pick(_LDP, ldp, "ldp"), _pick(_COMB, combination, "combination")
        g, interact, grc_fn, sigma_cm, ground_notes = _ground(inp)
        grc = grc_fn(g, n_points)
        r, notes, warns = inp.radius_m, list(grc.notes) + ground_notes, []
        strain = grc.u_max_m / r * 100
        sq = rm.hoek_marinos(sigma_cm(), inp.p0_mpa, 0.0, r)  # sin sostenimiento: pi = 0
        if not sq.in_fit_range:
            notes.append(N_FIT)
        if strain > 100:
            notes.append(N_VALIDITY)
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
            els = [s.to_element(support_diameter_m or 2 * r) if isinstance(s, SupportCapacity) else s
                   for s in supports]
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
    classes, below, none = Counter(), [0], [0]

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
            # sin cruce = instalado después de la convergencia total: el sostenimiento no carga, no está fallando
            none[0] += fs is None
            below[0] += fs is not None and fs < 1
        return outs, list(r.warnings)

    ms = sample_model(one, variables, n=n, sampling=sampling, seed=seed)
    k = ms.n_valid
    return UncertaintyResult(
        "Tunnel-GRC", sampling, n, seed, k, tuple(sorted(variables)),
        {name: _summary(v) for name, v in ms.outputs.items()},
        {c: classes[c] / k for c in _CLASSES} if k else {},
        {"fs_below_1": below[0] / k, "no_crossing": none[0] / k} if k and supports else {}, UNCERTAINTY_INFO,
        ms.warnings, ms.notes)
