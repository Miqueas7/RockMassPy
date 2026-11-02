"""Tablas 5 a 9 del Q-slope de Bar y Barton: factor O, Jwice y SRF (datos puros, sin E/S).

Los números son los de la fuente; los rótulos de las claves son propios.
"""

SOURCE = (
    "Bar & Barton (2018) Periodica Polytechnica Civ. Eng. 62(4) 893-900: eq. 1 (p. 894), eq. 3 (p. 896), "
    "Tables 1-9 (pp. 894-896); SRFslope = max(SRFa, SRFb, SRFc) (p. 895)"
)

# Tabla 5 (p. 895): (set A, set B)
O_FACTOR = {
    "very_favorable": (2.0, 1.5),
    "quite_favorable": (1.0, 1.0),
    "unfavorable": (0.75, 0.9),
    "very_unfavorable": (0.50, 0.8),
    "causing_failure": (0.25, 0.5),
}

# Tabla 6 (p. 895): condición x ambiente
JWICE = {
    ("stable_competent", "desert"): 1.0, ("stable_competent", "wet"): 0.7,
    ("stable_competent", "tropical_storms"): 0.5, ("stable_competent", "ice_wedging"): 0.9,
    ("stable_incompetent", "desert"): 0.7, ("stable_incompetent", "wet"): 0.6,
    ("stable_incompetent", "tropical_storms"): 0.3, ("stable_incompetent", "ice_wedging"): 0.5,
    ("unstable_competent", "desert"): 0.8, ("unstable_competent", "wet"): 0.5,
    ("unstable_competent", "tropical_storms"): 0.1, ("unstable_competent", "ice_wedging"): 0.3,
    ("unstable_incompetent", "desert"): 0.5, ("unstable_incompetent", "wet"): 0.3,
    ("unstable_incompetent", "tropical_storms"): 0.05, ("unstable_incompetent", "ice_wedging"): 0.2,
}
JWICE_DRAINAGE = 1.5
JWICE_REINFORCEMENT = 1.3

# Tabla 7 (p. 896)
SRF_A = {"A": 2.5, "B": 5.0, "C": 10.0, "D": 15.0, "E": 20.0}

# Tabla 8 (p. 896): (σc/σ1, SRFb) en los extremos de cada fila F a K; entre extremos, interpolación lineal (R16)
_SRF_B_POINTS = ((200.0, 1.0), (50.0, 2.5), (10.0, 5.0), (5.0, 10.0), (2.5, 15.0), (1.0, 20.0))

# Tabla 9 (p. 896): favorable, desfavorable, muy desfavorable, causa falla
_SRF_C_ORIENTATIONS = ("favorable", "unfavorable", "very_unfavorable", "causing_failure")
SRF_C = {"L": (1.0, 2.0, 4.0, 8.0), "M": (2.0, 4.0, 8.0, 16.0), "N": (4.0, 8.0, 12.0, 24.0)}


def _pick(table, key, what):
    try:
        return table[key]
    except KeyError:
        raise ValueError(f"unknown {what} {key!r}; valid: {sorted(table, key=str)}") from None


def o_factor(rating: str, joint_set: str = "A") -> float:
    pair = _pick(O_FACTOR, rating, "O-factor rating")
    return pair[_pick({"A": 0, "B": 1}, joint_set, "joint set")]


def jwice(condition: str, environment: str, *, drainage: bool = False, reinforcement: bool = False) -> float:
    if (condition, environment) not in JWICE:
        conditions = sorted({c for c, _ in JWICE})
        environments = sorted({e for _, e in JWICE})
        raise ValueError(f"unknown Jwice entry ({condition!r}, {environment!r}); valid conditions: {conditions}; "
                         f"valid environments: {environments}")
    value = JWICE[(condition, environment)]
    return value * (JWICE_DRAINAGE if drainage else 1.0) * (JWICE_REINFORCEMENT if reinforcement else 1.0)


def srf_a(category: str) -> float:
    return _pick(SRF_A, category, "SRFa category")


def srf_b(ucs_over_sigma1: float) -> float:
    x = float(ucs_over_sigma1)
    if not x > 0:  # también atrapa NaN
        raise ValueError(f"ucs_over_sigma1 must be a positive number, got {ucs_over_sigma1!r}")
    pts = _SRF_B_POINTS
    if x >= pts[0][0]:
        return pts[0][1]
    if x <= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x1 <= x <= x0:
            return y0 + (y1 - y0) * (x0 - x) / (x0 - x1)
    raise AssertionError("unreachable: x is inside the table range")


def srf_c(category: str, orientation: str) -> float:
    row = _pick(SRF_C, category, "SRFc category")
    return row[_c_index(orientation)]


def _c_index(orientation):
    if orientation not in _SRF_C_ORIENTATIONS:
        raise ValueError(f"unknown orientation {orientation!r}; valid: {list(_SRF_C_ORIENTATIONS)}")
    return _SRF_C_ORIENTATIONS.index(orientation)
