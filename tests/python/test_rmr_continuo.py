import pytest
from hypothesis import example, given, strategies as st

import rockmasspy as rm


@pytest.mark.parametrize("fn,x,y", [
    (rm.rating_ucs89_continuous, 1, 0.3173), (rm.rating_ucs89_continuous, 50, 5.2398),
    (rm.rating_ucs89_continuous, 90, 7.7248), (rm.rating_ucs89_continuous, 100, 8.2796),
    (rm.rating_ucs89_continuous, 250, 15.0), (rm.rating_ucs89_continuous, 300, 15.0),
    (rm.rating_rqd89_continuous, 25, 5.7094), (rm.rating_rqd89_continuous, 65, 13.5400),
    (rm.rating_rqd89_continuous, 100, 19.9687),
    (rm.rating_spacing89_continuous, 0.2, 8.8497), (rm.rating_spacing89_continuous, 0.25, 9.6058),
    (rm.rating_spacing89_continuous, 0.6, 13.1453), (rm.rating_spacing89_continuous, 3, 20.0),
    (rm.rating_is50_89_continuous, 2, 5.3630), (rm.rating_is50_89_continuous, 10, 14.1026),
    (rm.rmr14_joints_per_m_rating, 0, 40.0), (rm.rmr14_joints_per_m_rating, 5, 27.2778),
    (rm.rmr14_joints_per_m_rating, 40, 4.5630), (rm.rmr14_strength_rating, 90, 7.7248),
])
def test_values(fn, x, y):
    assert fn(x) == pytest.approx(y, abs=1e-4)


@pytest.mark.parametrize("fn,name", [
    (rm.rating_ucs89_continuous, "ucs_mpa"), (rm.rating_rqd89_continuous, "rqd_pct"),
    (rm.rating_spacing89_continuous, "spacing_m"), (rm.rating_is50_89_continuous, "is50_mpa"),
    (rm.rmr14_strength_rating, "ucs_mpa"), (rm.rmr14_joints_per_m_rating, "n_per_m"),
])
def test_negative_names_parameter(fn, name):
    with pytest.raises(ValueError, match=name):
        fn(-1.0)


def test_is50_at_one_raises():
    with pytest.raises(ValueError, match="Is50 <= 1 MPa"):
        rm.rating_is50_89_continuous(1.0)


def _input(functions):
    i = rm.Rmr89Input()
    i.ucs_mpa, i.rqd_pct, i.spacing_m, i.joint_condition_rating = 90.0, 65.0, 0.25, 18.0
    i.water, i.orientation, i.application = rm.Water.Damp, rm.OrientationClass.Fair, rm.Application.Tunnel
    i.functions = functions
    return i


def test_rmr89_modes():
    d = rm.rmr89(_input(rm.RmrFunctions.Discrete))
    assert d.rmr == 53.0 and d.info.method_id == "RMR89" and d.r_strength == 7.0
    c = rm.rmr89(_input(rm.RmrFunctions.Continuous))
    assert c.rmr == pytest.approx(53.8707, abs=1e-4)
    assert c.info.method_id == "RMR89-continuous" and c.rmr_class.roman == "III"


@pytest.mark.parametrize("fn,hi,top,lo", [
    (rm.rating_ucs89_continuous, 400.0, 15.0, 0.0), (rm.rating_rqd89_continuous, 100.0, 20.0, 0.0),
    (rm.rating_spacing89_continuous, 10.0, 20.0, 0.0), (rm.rmr14_joints_per_m_rating, 100.0, 40.0, 0.0),
    (rm.rmr14_strength_rating, 400.0, 15.0, 0.0),
])
@example(a=0.0, b=1e-5)
@example(a=0.0, b=1e-4)
@given(a=st.floats(0, 1), b=st.floats(0, 1))
def test_monotone_and_in_range(fn, hi, top, lo, a, b):
    x, y = sorted((a * hi, b * hi))
    if fn is rm.rmr14_joints_per_m_rating:  # más juntas, menos puntaje
        assert lo <= fn(y) <= fn(x) <= top
    else:
        assert lo <= fn(x) <= fn(y) <= top


@given(a=st.floats(1.0001, 400), b=st.floats(1.0001, 400))
def test_is50_monotone(a, b):
    x, y = sorted((a, b))
    assert 0.0 <= rm.rating_is50_89_continuous(x) <= rm.rating_is50_89_continuous(y) <= 15.0


def test_bottom_of_range_is_zero():
    for x in (0.0, 0.03, 0.07):
        assert rm.rating_rqd89_continuous(x) == 0.0
    for x in (0.0, 0.005):
        assert rm.rating_ucs89_continuous(x) == 0.0 and rm.rmr14_strength_rating(x) == 0.0
    assert rm.rating_rqd89_continuous(0.0) <= rm.rating_rqd89_continuous(0.001)
