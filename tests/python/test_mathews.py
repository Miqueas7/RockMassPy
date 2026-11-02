import math

import pytest
from hypothesis import given, settings, strategies as st

import rockmasspy as rm
from rockmasspy.mathews import JOINT_ORIENTATION_CURVES, MathewsResult, factor_b, mathews_stability
from rockmasspy.stability_graphs import read_stability_graph


def _curve(key, d):
    pts = JOINT_ORIENTATION_CURVES[key]
    if d <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if d <= x1:
            return y0 + (y1 - y0) * (d - x0) / (x1 - x0)
    return pts[-1][1]


def test_factor_b_continuous_curve():
    assert factor_b(0) == 0.3
    assert factor_b(5) == pytest.approx(0.25)
    assert factor_b(20) == 0.2
    assert factor_b(45) == pytest.approx(0.5)
    assert factor_b(60) == pytest.approx(0.8)
    assert factor_b(90) == 1.0


def test_factor_b_ninety_dip_and_ninety_strike():
    for s in (0, 30, 45, 60, 90):
        assert factor_b(90, s) == pytest.approx(1.0, abs=1e-9)
    for d in (10, 25, 60, 90):
        assert factor_b(d, 90) == 1.0


@settings(max_examples=200)
@given(st.floats(0, 90), st.floats(0, 90), st.floats(0, 90))
def test_factor_b_monotone_in_strike_and_bounded(d, s1, s2):
    lo, hi = sorted((s1, s2))
    assert factor_b(d, lo) <= factor_b(d, hi) + 1e-12
    assert 0.2 - 1e-12 <= factor_b(d, hi) <= 1.0 + 1e-12


@pytest.mark.parametrize("args", [(91,), (-1,), (20, 95), (20, -1), (float("nan"),), (20, float("inf"))])
def test_factor_b_rejects_bad_angles(args):
    with pytest.raises(ValueError, match=r"\[0, 90\]"):
        factor_b(*args)


def test_digitized_curves():
    assert set(JOINT_ORIENTATION_CURVES) == {0, 30, 45, 60, 90}
    assert JOINT_ORIENTATION_CURVES[0] == ((0, 0.3), (10, 0.2), (30, 0.2), (60, 0.8), (90, 1.0))
    assert JOINT_ORIENTATION_CURVES[90] == ((10, 1.0), (90, 1.0))
    for k in (30, 45, 60):
        pts = JOINT_ORIENTATION_CURVES[k]
        assert pts[0][0] == 10 and pts[-1][0] == 90
        assert abs(pts[-1][1] - 1.0) <= 0.02
        assert [p[0] for p in pts] == sorted(p[0] for p in pts)
    for d in range(10, 91):
        vals = [_curve(k, d) for k in (0, 30, 45, 60, 90)]
        assert all(a <= b + 1e-12 for a, b in zip(vals, vals[1:])), d
        for k in (30, 45, 60, 90):
            assert _curve(k, d) >= _curve(0, d) - 1e-12


def test_synthetic_case():
    q = (80 / 9) * (1.5 / 1)
    hr = rm.hydraulic_radius_rect(10, 20)
    r = mathews_stability(q, hr, ucs_mpa=120, sigma1_mpa=30, dip_difference_deg=20, surface_inclination_deg=0)
    assert isinstance(r, MathewsResult)
    assert (r.factor_a, r.factor_b, r.factor_c) == (0.325, 0.2, 2.0)
    assert r.n_prime == pytest.approx(1.733333, abs=1e-6)
    assert r.hr_m == pytest.approx(3.333333, abs=1e-6)
    assert r.reading.zone == read_stability_graph("Mathews-Potvin1988", r.hr_m, r.n_prime).zone
    assert r.warnings == r.reading.warnings
    assert r.failure_mode == "gravity" and r.graph == "Mathews-Potvin1988"


def test_failure_modes_and_inputs():
    kw = dict(ucs_mpa=120, sigma1_mpa=30, dip_difference_deg=20)
    with pytest.raises(ValueError, match="surface_inclination_deg is required"):
        mathews_stability(5, 5, **kw)
    with pytest.raises(ValueError, match="joint_dip_deg is required"):
        mathews_stability(5, 5, failure_mode="sliding", **kw)
    with pytest.raises(ValueError, match="failure_mode"):
        mathews_stability(5, 5, failure_mode="toppling", surface_inclination_deg=0, **kw)
    for q, hr in ((0, 5), (5, 0), (float("nan"), 5), (5, float("inf"))):
        with pytest.raises(ValueError):
            mathews_stability(q, hr, surface_inclination_deg=0, **kw)
    s = mathews_stability(5, 5, failure_mode="sliding", joint_dip_deg=60, **kw)
    assert s.factor_c == pytest.approx(rm.mathews_factor_c_sliding(60).value)
    r = mathews_stability(5, 5, ucs_mpa=120, sigma1_mpa=-2, dip_difference_deg=20, surface_inclination_deg=0)
    assert r.factor_a == 1.0


def test_above_graph_top_warns():
    r = mathews_stability(500, 5, ucs_mpa=120, sigma1_mpa=1, dip_difference_deg=90, surface_inclination_deg=90)
    assert (r.factor_a, r.factor_b, r.factor_c) == (1.0, 1.0, 8.0)
    assert r.n_prime == pytest.approx(4000)
    assert r.reading.y == 1000 and r.warnings


def test_methods_dedup_and_q_info():
    kw = dict(ucs_mpa=120, sigma1_mpa=30, dip_difference_deg=20, surface_inclination_deg=0)
    r = mathews_stability(5, 5, **kw)
    assert [m.method_id for m in r.methods] == ["Mathews-Potvin1988"] * 4
    assert len({m.source for m in r.methods}) == 4
    q = rm.q_value(rm.QInput(80, 9, 1.5, 1, 1, 1), rm.QEdition.NGI2015)
    r2 = mathews_stability(5, 5, q_info=q.info, **kw)
    assert len(r2.methods) == 5 and r2.methods[-1].method_id == "Q-NGI-2015"
