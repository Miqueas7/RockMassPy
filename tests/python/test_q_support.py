import math

import pytest
from hypothesis import given, settings, strategies as st

import rockmasspy as rm
from rockmasspy import Q_CHARTS, QChartReading, QSupportResult, read_q_chart, recommend_q_support

EDITIONS = ["Q-NGI-2025", "Q-NGI-2015"]
_ENUM = {"Q-NGI-2025": rm.QEdition.NGI2025, "Q-NGI-2015": rm.QEdition.NGI2015}

# La carta de Hoek (1993, p. 18) da categoría 4; la carta digitalizada de 2015/2025 da 3 (discrepancia anotada
# en el CHANGELOG para Miqueas). Los datos no se ajustan.
_HOEK_XFAIL = pytest.mark.xfail(
    strict=True, reason="Hoek read category 4 on the older 1993 chart; the 2015/2025 plates give 3 at (Q 4.5, De 9.4)")


@pytest.mark.parametrize("edition", [pytest.param(e, marks=_HOEK_XFAIL) for e in EDITIONS])
def test_hoek_category_published_reading(edition):
    r = recommend_q_support(4.5, 15, esr_category="C", edition=edition)
    assert r.roof.category == 4


@pytest.mark.parametrize("edition", EDITIONS)
def test_hoek_chamber_formulas_and_methods(edition):
    r = recommend_q_support(4.5, 15, esr_category="C", edition=edition, jn=4, jr=3)
    assert r.roof.de_m == pytest.approx(9.375)
    assert r.esr_used == 1.6
    assert r.max_unsupported_span.value == rm.max_unsupported_span(4.5, 1.6).value
    assert r.bolt_length_formula.value == rm.bolt_length_barton1980(15, 1.6).value
    assert r.roof_pressure.value == rm.roof_pressure_grimstad_barton(4.5, 4, 3).value
    ids = {m.method_id for m in r.methods}
    assert {"Q-NGI-2025-chart" if edition == "Q-NGI-2025" else "Q-NGI-2015-chart", "Q-Barton1980"} <= ids
    keys = [(m.method_id, m.source) for m in r.methods]
    assert len(keys) == len(set(keys))


def test_2025_chart_method_is_primary():
    r = recommend_q_support(4.5, 15, esr_category="C")
    chart = next(m for m in r.methods if m.method_id == "Q-NGI-2025-chart")
    assert chart.verification == rm.Verification.Primary


def test_osinergmin_ramp_2015():
    # Osinergmin (2017, p. 92): Q 0.4, luz 4.5, altura 4.5. Imprime Q de pared 1.25, errata: 0.4 x 2.5 = 1.0.
    r = recommend_q_support(0.4, 4.5, esr_category="C", wall_height_m=4.5, edition="Q-NGI-2015")
    assert r.roof.de_m == pytest.approx(2.8125)
    assert r.roof.category == 4 and r.roof.shotcrete_mm == (60, 90)
    assert r.wall_q == pytest.approx(1.0)
    assert r.walls.category == 3
    assert r.roof.no_empirical_data


def test_osinergmin_ramp_2025_wall_q():
    r = recommend_q_support(0.4, 4.5, esr_category="C", wall_height_m=4.5, edition="Q-NGI-2025")
    assert r.wall_q == pytest.approx(0.4)


def test_out_of_frame():
    r = read_q_chart(2, 0.75)
    assert r.de_m == 1.0 and "De below the chart (1 m); read at De = 1" in r.warnings
    r = read_q_chart(2000, 5)
    assert r.q == 1000.0 and any("1000" in w for w in r.warnings)
    assert read_q_chart(0.0005, 5).category == 9
    assert read_q_chart(1, 150).category == 9
    assert "special evaluation" in read_q_chart(1, 150).warnings


def test_bottom_left_corner_is_category_6():
    # En la lámina la línea 6|7 toca el borde izquierdo en De = 1.03: fiel a la carta, no es un error.
    assert read_q_chart(0.001, 1.0).category == 6


def test_no_data_is_a_flag_not_a_category():
    r = read_q_chart(0.4, 2.8, edition="Q-NGI-2015")
    assert r.category == 4 and r.no_empirical_data
    assert "point in a dashed area of the chart (no empirical data)" in r.warnings
    assert not read_q_chart(4.5, 50).no_empirical_data


def test_esr_rules():
    with pytest.raises(ValueError, match="3-5"):
        recommend_q_support(1, 5, esr_category="A")
    r = recommend_q_support(1, 5, esr_category="A", esr=6)
    assert any("ESR 6 outside category A range 3-5 (NGI Table 4-1)" in w for w in r.warnings)
    assert recommend_q_support(1, 5, esr_category="c").esr_used == 1.6
    with pytest.raises(ValueError):
        recommend_q_support(1, 5, esr_category="H")


@pytest.mark.parametrize("kw", [dict(esr=float("nan"), esr_category="A"), dict(q=float("inf")),
                                dict(edition="Q-1974"), dict(span_m=0.0), dict(q=-1.0)])
def test_invalid_inputs(kw):
    args = dict(q=1.0, span_m=5.0, esr_category="C")
    args.update(kw)
    with pytest.raises(ValueError):
        recommend_q_support(**args)


def test_read_q_chart_validation():
    for bad in (dict(q=float("nan"), de_m=1), dict(q=1, de_m=0), dict(q=1, de_m=1, span_m=float("inf")),
                dict(q=1, de_m=1, edition="x")):
        with pytest.raises(ValueError):
            read_q_chart(**bad)


def test_low_q_forces_esr_1():
    r = recommend_q_support(0.05, 5, esr_category="C")
    assert r.esr_used == 1.0
    assert any("ESR set to 1.0" in w for w in r.warnings)
    assert not any("chart bolt length" in w for w in r.warnings)
    assert not any("chart bolt length" in w for w in recommend_q_support(5, 5, esr_category="C").warnings)
    assert "chart bolt length is given for ESR = 1" in recommend_q_support(5, 5, esr_category="C").notes
    assert recommend_q_support(5, 5, esr_category="E").notes == ()


def test_wall_height_rule_by_edition():
    r25 = recommend_q_support(5, 5, esr_category="C", wall_height_m=8, edition="Q-NGI-2025")
    r15 = recommend_q_support(5, 5, esr_category="C", wall_height_m=8, edition="Q-NGI-2015")
    assert r25.roof.de_m == pytest.approx(8 / 1.6) and r15.roof.de_m == pytest.approx(5 / 1.6)
    assert any("wall height exceeds span: roof read with wall height (NGI 2025, 4.1)" in w for w in r25.warnings)


def test_walls_use_real_q_for_esr_rule():
    r = recommend_q_support(0.05, 5, esr_category="C", wall_height_m=5)
    assert r.walls is not None and r.walls.de_m == pytest.approx(5.0)  # ESR = 1 por el Q real, no el de pared


def test_spacing_bracket():
    ch = Q_CHARTS["Q-NGI-2025"]
    q, s = ch.spacing_with_sfr[3]
    assert read_q_chart(q, 20).bolt_spacing_with_sfr_m == (s, s)
    lo, hi = read_q_chart(0.2, 20).bolt_spacing_with_sfr_m
    assert lo < hi
    assert read_q_chart(1000, 20).bolt_spacing_with_sfr_m[0] == ch.spacing_with_sfr[-1][1]
    assert read_q_chart(0.003, 5).bolt_spacing_with_sfr_m == (ch.spacing_with_sfr[0][1],) * 2


def test_rrs():
    r = read_q_chart(0.01, 5, span_m=10)
    assert r.category == 7 and r.rrs == "RRS-B" and r.rrs_spec == "D45/6+4 Ø16-20"
    assert r.rrs_spacing_m is not None
    r = read_q_chart(0.01, 5, span_m=25)
    assert r.rrs_spec is None and any("RRS" in w for w in r.warnings)
    r = read_q_chart(0.01, 2, span_m=4)  # categoría 6: RRS-A no tiene dato en 5 m
    assert r.category == 6 and r.rrs == "RRS-A" and r.rrs_spec is None and any("RRS" in w for w in r.warnings)
    r = read_q_chart(0.01, 5)
    assert r.rrs_spec is None and not any("RRS" in w for w in r.warnings)
    assert read_q_chart(5, 10, span_m=10).rrs is None


def test_category_warnings():
    assert any("categories 7-9 are indicative" in w for w in read_q_chart(0.01, 5).warnings)
    assert not any("categories 7-9" in w for w in read_q_chart(0.01, 5, edition="Q-NGI-2015").warnings)


@settings(max_examples=60, deadline=None)
@given(st.floats(1e-4, 5e3), st.floats(0.1, 200), st.sampled_from(EDITIONS))
def test_edition_travels(q, de, edition):
    r = read_q_chart(q, de, edition=edition)
    assert r.edition == edition and r.info.method_id == Q_CHARTS[edition].info.method_id
    assert 1 <= r.category <= 9
