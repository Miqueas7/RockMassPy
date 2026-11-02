import math

import pytest
from hypothesis import given, strategies as st

import rockmasspy as rm


def test_factor_a():
    assert rm.mathews_factor_a(100, 50).value == 0.1
    assert rm.mathews_factor_a(100, 25).value == pytest.approx(0.325, abs=1e-12)
    for s1 in (10, 5, 0, -5):
        assert rm.mathews_factor_a(ucs_mpa=100, induced_stress_mpa=s1).value == 1.0


def test_factor_c():
    assert rm.mathews_factor_c_gravity(0).value == 2.0
    assert rm.mathews_factor_c_gravity(90).value == pytest.approx(8.0, abs=1e-12)
    assert rm.mathews_factor_c_gravity(60).value == pytest.approx(5.0)
    assert rm.mathews_factor_c_gravity(45).value == pytest.approx(3.757359, abs=1e-6)
    assert rm.mathews_factor_c_sliding(20).value == 8.0
    assert rm.mathews_factor_c_sliding(30).value == 8.0
    assert rm.mathews_factor_c_sliding(60).value == pytest.approx(5.0)
    assert rm.mathews_factor_c_sliding(joint_dip_deg=90).value == pytest.approx(2.0)


def test_hydraulic_radius():
    assert rm.hydraulic_radius(100, 40) == 2.5
    assert rm.hydraulic_radius(area_m2=127, perimeter_m=40) > 3
    assert rm.hydraulic_radius_rect(10, 20) == pytest.approx(3.333333, abs=1e-6)
    assert rm.hydraulic_radius_rect(width_m=30, length_m=15) == 5.0
    with pytest.raises(ValueError, match="area too large"):
        rm.hydraulic_radius(130, 40)


def test_errors_and_info():
    nan, inf = float("nan"), float("inf")
    for f in (lambda: rm.mathews_factor_a(nan, 1), lambda: rm.mathews_factor_a(100, inf),
              lambda: rm.mathews_factor_a(0, 1), lambda: rm.mathews_factor_c_gravity(-1),
              lambda: rm.mathews_factor_c_gravity(91), lambda: rm.mathews_factor_c_sliding(90.5),
              lambda: rm.hydraulic_radius(100, 0), lambda: rm.hydraulic_radius_rect(-1, 5)):
        with pytest.raises(ValueError):
            f()
    for r in (rm.mathews_factor_a(100, 25), rm.mathews_factor_c_gravity(45), rm.mathews_factor_c_sliding(45)):
        assert r.info.method_id == "Mathews-Potvin1988"
        assert r.info.verification == rm.Verification.Primary


pos = st.floats(0.1, 500, allow_nan=False)


@given(pos, pos, pos)
def test_a_monotone(u1, u2, s):
    lo, hi = sorted((u1, u2))
    assert rm.mathews_factor_a(lo, s).value <= rm.mathews_factor_a(hi, s).value + 1e-12
    a = rm.mathews_factor_a(lo, s).value
    assert 0.1 - 1e-12 <= a <= 1.0 + 1e-12


@given(pos, pos, pos)
def test_a_baja_con_sigma1(u, s1, s2):
    lo, hi = sorted((s1, s2))
    assert rm.mathews_factor_a(u, hi).value <= rm.mathews_factor_a(u, lo).value + 1e-12


@given(st.floats(0, 90), st.floats(0, 90))
def test_c_monotonos(x, y):
    lo, hi = sorted((x, y))
    g1, g2 = rm.mathews_factor_c_gravity(lo).value, rm.mathews_factor_c_gravity(hi).value
    s1, s2 = rm.mathews_factor_c_sliding(lo).value, rm.mathews_factor_c_sliding(hi).value
    assert g1 <= g2 + 1e-12 and s1 >= s2 - 1e-12
    for v in (g1, g2, s1, s2):
        assert 2.0 - 1e-12 <= v <= 8.0 + 1e-12
