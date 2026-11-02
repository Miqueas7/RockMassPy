import math

import pytest
from hypothesis import given, strategies as st

import rockmasspy as rm
from rockmasspy import q_slope_tables as t

NAN = float("nan")


def base(**kw):
    i = rm.QSlopeInput()
    for k, v in {**dict(rqd_pct=80, jn=9, jr_a=1.5, ja_a=1, o_factor_a=0.75, jwice=0.7, srf_a=2.5), **kw}.items():
        setattr(i, k, v)
    return i


def test_beta_formula_and_table12():
    for q, b in [(10, 85), (1, 65), (0.1, 45), (0.01, 25)]:
        assert rm.q_slope_beta(q) == pytest.approx(b, abs=1e-12)
    for q, b, r in [(0.60, 60.563, 61), (1.50, 68.522, 69), (4.22 * 0.75, 75.007, 75)]:
        assert rm.q_slope_beta(q) == pytest.approx(b, abs=1e-3)
        assert round(rm.q_slope_beta(q)) == r


def test_components_and_set_b():
    r = rm.q_slope(base())
    assert r.q_slope == pytest.approx(2.8, abs=1e-9)
    assert r.beta_deg == pytest.approx(73.943, abs=1e-3)
    assert r.info.method_id == "Q-slope-BarBarton2017"
    assert r.info.verification == rm.Verification.PrimaryLaterAuthors
    b = base(jr_b=2, ja_b=1, o_factor_b=0.9)
    assert rm.q_slope(b).jr_ja_0 == pytest.approx(2.025)


def test_srf_max_rqd_floor_and_cap():
    i = base(srf_b=5, srf_c=2)
    assert rm.q_slope(i).srf_slope == 5
    i = base()
    i.rqd_pct = 0
    r = rm.q_slope(i)
    assert r.rqd_used == 10 and r.notes and not r.warnings
    i = base()
    i.rqd_pct, i.jn, i.jr_a, i.ja_a, i.o_factor_a, i.jwice = 100, 2, 1, 1, 1, 1
    r = rm.q_slope(i)
    assert r.beta_deg == 90 and r.beta_capped and r.notes and not r.warnings


@pytest.mark.parametrize("field,value", [("rqd_pct", 120), ("jn", 0), ("jwice", NAN), ("rqd_pct", NAN),
                                         ("jr_a", NAN), ("srf_a", NAN), ("jr_b", 2.0)])
def test_throws(field, value):
    i = base()
    setattr(i, field, value)
    with pytest.raises(ValueError):
        rm.q_slope(i)


def test_warns_without_throwing():
    assert any("jwice" in w for w in rm.q_slope(base(jwice=2.5)).warnings)
    assert any("srf_a" in w for w in rm.q_slope(base(srf_a=1.5)).warnings)


def test_o_factor_jwice_srf_tables():
    assert t.o_factor("unfavorable", "B") == 0.9
    assert t.o_factor("very_favorable") == 2.0
    assert t.jwice("unstable_competent", "tropical_storms") == 0.1
    assert t.jwice("stable_competent", "desert", drainage=True, reinforcement=True) == pytest.approx(1.95)
    assert t.jwice("stable_competent", "wet", drainage=True) == pytest.approx(1.05)
    assert t.srf_a("C") == 10
    assert t.srf_c("N", "causing_failure") == 24
    assert t.srf_c("L", "favorable") == 1
    assert t.SOURCE.startswith("Bar & Barton (2018)")


def test_srf_b():
    assert (t.srf_b(200), t.srf_b(50), t.srf_b(0.5), t.srf_b(500)) == (1, 2.5, 20, 1)
    assert t.srf_b(30) == pytest.approx(3.75)


@given(st.floats(0.1, 300), st.floats(0.1, 300))
def test_srf_b_monotone(a, b):
    lo, hi = sorted((a, b))
    assert t.srf_b(lo) >= t.srf_b(hi)


@pytest.mark.parametrize("call", [lambda: t.o_factor("muy_bueno"), lambda: t.o_factor("unfavorable", "C"),
                                  lambda: t.jwice("x", "desert"), lambda: t.jwice("stable_competent", "mars"),
                                  lambda: t.srf_a("Z"), lambda: t.srf_c("N", "bad"), lambda: t.srf_c("Q", "favorable"),
                                  lambda: t.srf_b(float("nan")), lambda: t.srf_b(0)])
def test_unknown_key_raises(call):
    with pytest.raises(ValueError):
        call()


def test_unknown_key_lists_valid():
    with pytest.raises(ValueError, match="very_favorable"):
        t.o_factor("muy_bueno")


@pytest.mark.parametrize("field", ["jr_b", "ja_b", "o_factor_b", "srf_b", "srf_c", "srf_a"])
def test_nan_in_optional_field_raises_naming_it(field):
    i = base(jr_b=2, ja_b=1, o_factor_b=0.9, srf_b=5, srf_c=2)
    setattr(i, field, NAN)
    with pytest.raises(ValueError, match=field):
        rm.q_slope(i)


def test_none_and_omission_mean_unset():
    i = base()
    assert i.srf_b is None and i.jr_b is None
    i.srf_b = 5
    i.srf_b = None
    assert rm.q_slope(i).srf_slope == 2.5
    assert any("product of sets A and B" in n for n in rm.q_slope(base(jr_b=2, ja_b=1, o_factor_b=0.9)).notes)
