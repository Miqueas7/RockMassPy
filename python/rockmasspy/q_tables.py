"""Tablas de letras del sistema Q por edición (datos puros, sin E/S).

Estructura: Q_TABLES[edición][parámetro][letra] = (mínimo, máximo, rótulo corto propio).
Un valor único tiene mínimo == máximo. Cuando el manual da alternativas en vez de un rango,
se guarda el (mínimo, máximo) global y el rótulo menciona las alternativas.
Fuentes: NGI (2025) Using the Q-system, tablas 3-1 a 3-6; NGI (2015, rev. 2022), tablas 1 a 6.
Los rótulos están escritos con palabras propias (no son texto del manual).
"""

_Q2025 = {
    "RQD": {
        "A": (10.0, 25.0, "very poor (RQD below 10 is taken as 10)"),
        "B": (25.0, 50.0, "poor"),
        "C": (50.0, 75.0, "fair"),
        "D": (75.0, 90.0, "good"),
        "E": (90.0, 100.0, "excellent"),
    },
    "Jn": {
        "A": (0.5, 1.0, "massive, few or no joints"),
        "B": (2.0, 2.0, "one joint set"),
        "C": (3.0, 3.0, "one set plus random joints"),
        "D": (4.0, 4.0, "two sets"),
        "E": (6.0, 6.0, "two sets plus random joints"),
        "F": (9.0, 9.0, "three sets"),
        "G": (12.0, 12.0, "three sets plus random joints"),
        "H": (15.0, 15.0, "four or more sets, sugar-cube rock"),
        "J": (20.0, 20.0, "crushed, soil-like rock"),
    },
    "Jr": {
        "A": (4.0, 4.0, "discontinuous joints or rough stepped"),
        "B": (3.0, 3.0, "rough or irregular undulating, or smooth stepped"),
        "C": (2.0, 2.0, "smooth undulating, or slickensided stepped"),
        "D": (1.5, 1.5, "slickensided undulating"),
        "E": (1.5, 1.5, "rough irregular planar"),
        "F": (1.0, 1.0, "smooth planar"),
        "G": (0.5, 0.5, "slickensided planar"),
        "H": (1.0, 1.0, "clay-bearing zone, no wall contact when sheared"),
    },
    "Ja": {
        "A": (0.75, 0.75, "tightly healed hard filling"),
        "B": (1.0, 1.0, "fresh walls, staining only"),
        "C": (2.0, 2.0, "slightly altered walls, non-softening coating"),
        "D": (3.0, 3.0, "silty or sandy clay coating"),
        "E": (4.0, 4.0, "softening or low-friction clay coating"),
        "F": (4.0, 4.0, "thin sandy, clay-free filling"),
        "G": (6.0, 6.0, "thin strongly consolidated clay filling"),
        "H": (8.0, 8.0, "thin softening clay filling"),
        "J": (8.0, 12.0, "thin swelling clay filling"),
        "K": (6.0, 6.0, "crushed-rock bands, strongly consolidated"),
        "L": (8.0, 8.0, "clay or crushed bands, softening"),
        "M": (8.0, 12.0, "clay or crushed bands, swelling"),
        "N": (10.0, 10.0, "thick clay bands, strongly consolidated"),
        "O": (13.0, 13.0, "thick clay bands, softening"),
        "P": (13.0, 20.0, "thick clay bands, swelling"),
    },
    "Jw": {
        "A": (1.0, 1.0, "dry or minor inflow"),
        "B": (0.66, 0.66, "medium inflow, some outwash"),
        "C": (0.5, 0.5, "jet inflow in competent rock"),
        "D": (0.33, 0.33, "large inflow, considerable outwash"),
        "E": (0.1, 0.2, "exceptional inflow, decaying"),
        "F": (0.05, 0.1, "exceptional inflow, not decaying"),
    },
    "SRF": {
        "A": (10.0, 10.0, "weak zones with clay, many in a short section"),
        "B": (7.5, 7.5, "many shear zones in competent rock"),
        "C": (5.0, 5.0, "single weak zone, depth up to 50 m"),
        "D": (5.0, 5.0, "loose, open, sugar-cube jointing"),
        "E": (2.5, 2.5, "single weak zone, depth over 50 m"),
        "F": (2.5, 2.5, "competent rock, low stress, near surface"),
        "G": (1.0, 1.0, "competent rock, medium stress"),
        "H": (0.5, 2.0, "high stress, tight structure (2-5 if unfavourable)"),
        "J": (5.0, 50.0, "moderate spalling after more than 1 h"),
        "K": (50.0, 200.0, "spalling or rock burst within minutes"),
        "L": (200.0, 400.0, "heavy rock burst, dynamic deformation"),
        "M": (5.0, 10.0, "moderate squeezing"),
        "N": (10.0, 20.0, "heavy squeezing"),
        "O": (5.0, 10.0, "moderate swelling"),
        "P": (10.0, 15.0, "heavy swelling"),
    },
}

# 2015: mismos valores salvo RQD A (0-25) y SRF, que tiene 4 categorías (a-d) con cocientes de esfuerzo en b) y c).
_Q2015 = {k: dict(v) for k, v in _Q2025.items()}
_Q2015["RQD"]["A"] = (0.0, 25.0, "very poor (RQD below 10 is taken as 10)")
_Q2015["SRF"].update({
    "F": (2.5, 2.5, "b) low stress, near surface (sigma_c/sigma_1 > 200)"),
    "G": (1.0, 1.0, "b) medium stress (sigma_c/sigma_1 200-10)"),
    "H": (0.5, 2.0, "b) high stress (sigma_c/sigma_1 10-5; 2-5 if unfavourable)"),
    "J": (5.0, 50.0, "b) moderate spalling (sigma_c/sigma_1 5-3)"),
    "K": (50.0, 200.0, "b) spalling or rock burst (sigma_c/sigma_1 3-2)"),
    "L": (200.0, 400.0, "b) heavy rock burst (sigma_c/sigma_1 < 2)"),
    "M": (5.0, 10.0, "c) mild squeezing (sigma_theta/sigma_c 1-5)"),
    "N": (10.0, 20.0, "c) heavy squeezing (sigma_theta/sigma_c > 5)"),
    "O": (5.0, 10.0, "d) mild swelling"),
    "P": (10.0, 15.0, "d) heavy swelling"),
})

Q_TABLES = {"Q-NGI-2025": _Q2025, "Q-NGI-2015": _Q2015}


def q_lookup(parameter: str, letter: str, edition: str = "Q-NGI-2025") -> tuple[float, float]:
    """Return (min, max) of the table value for a parameter letter; KeyError lists the valid options."""
    if edition not in Q_TABLES:
        raise KeyError(f"unknown edition {edition!r}; valid editions: {', '.join(Q_TABLES)}")
    params = Q_TABLES[edition]
    if parameter not in params:
        raise KeyError(f"unknown parameter {parameter!r}; valid parameters: {', '.join(params)}")
    letters = params[parameter]
    if letter not in letters:
        raise KeyError(f"unknown letter {letter!r} for {parameter} ({edition}); valid letters: {', '.join(letters)}")
    lo, hi, _ = letters[letter]
    return (lo, hi)
