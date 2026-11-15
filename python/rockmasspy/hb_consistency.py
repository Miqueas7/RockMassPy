"""Coherencia de los parámetros de Hoek-Brown declarados en un estudio contra los que salen de GSI, mi y D."""

from dataclasses import dataclass

from . import _rockmasspy_core as _rm


@dataclass(frozen=True)
class HbConsistency:
    expected: dict
    declared: dict
    mismatches: tuple[str, ...]
    implied_d: float | None
    notes: tuple[str, ...]


def _implied_d(gsi, mi, mb, edition):
    """D en [0, 1] cuyo mb coincide con el declarado (mb baja con D, por eso sirve la bisección); None si ninguno."""
    f = lambda d: _rm.hb_params(gsi, mi, d, edition).mb - mb  # noqa: E731
    lo, hi = 0.0, 1.0
    if f(lo) * f(hi) > 0:
        return None
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(lo) * f(mid) > 0 else (lo, mid)
    return (lo + hi) / 2


def check_hoek_brown(*, gsi, mi, d, mb=None, s=None, a=None, erm_mpa=None, ei_mpa=None, sigma_ci_mpa=None,
                     edition=_rm.HbEdition.HB2002, rel_tol=0.01) -> HbConsistency:
    p = _rm.hb_params(gsi, mi, d, edition)
    erm = (_rm.erm_hoek_diederichs_generalized(gsi, d, ei_mpa) if ei_mpa is not None
           else _rm.erm_hoek_diederichs_simplified(gsi, d)).value
    expected = {"mb": p.mb, "s": p.s, "a": p.a, "erm_mpa": erm}
    declared = {k: v for k, v in (("mb", mb), ("s", s), ("a", a), ("erm_mpa", erm_mpa), ("ei_mpa", ei_mpa),
                                  ("sigma_ci_mpa", sigma_ci_mpa)) if v is not None}
    bad = tuple(k for k in expected if k in declared and abs(declared[k] - expected[k]) > rel_tol * abs(expected[k]))
    notes = []
    implied = None
    if mb is not None:
        implied = _implied_d(gsi, mi, mb, edition)
        if "mb" in bad:
            notes.append("declared mb does not match GSI, mi and D")
        if implied is not None and abs(implied - d) > 0.02:  # 0.02 absorbe el redondeo de mb en las tesis
            notes.append("declared D differs from the D implied by mb and s")
    return HbConsistency(expected, declared, bad, implied, tuple(notes))


def check_k_ratio(k_model, k_study, rel_tol=0.1) -> tuple[str, ...]:
    """Avisa si el K del modelo no es el del estudio."""
    if abs(k_model - k_study) > rel_tol * abs(k_study):
        return ("model K differs from the study K",)
    return ()
