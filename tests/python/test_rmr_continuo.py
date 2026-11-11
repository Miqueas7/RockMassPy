import pytest
from hypothesis import example, given, strategies as st

import rockmasspy as rm


@pytest.mark.parametrize("fn,x,y", [
    (rm.rating_ucs89_continuous, 1, 0.4073), (rm.rating_ucs89_continuous, 50, 5.3298),
    (rm.rating_ucs89_continuous, 90, 7.8148), (rm.rating_ucs89_continuous, 100, 8.3696),
    (rm.rating_ucs89_continuous, 250, 15.0), (rm.rating_ucs89_continuous, 300, 15.0),
    (rm.rating_rqd89_continuous, 25, 5.7094), (rm.rating_rqd89_continuous, 65, 13.5400),
    (rm.rating_rqd89_continuous, 100, 19.9687),
    (rm.rating_spacing89_continuous, 0.2, 8.8497), (rm.rating_spacing89_continuous, 0.25, 9.6058),
    (rm.rating_spacing89_continuous, 0.6, 13.1453), (rm.rating_spacing89_continuous, 3, 20.0),
    (rm.rating_is50_89_continuous, 2, 5.3630), (rm.rating_is50_89_continuous, 10, 14.1026),
    (rm.rmr14_joints_per_m_rating, 0, 40.0), (rm.rmr14_joints_per_m_rating, 5, 27.2535),
    (rm.rmr14_joints_per_m_rating, 40, 4.4234), (rm.rmr14_strength_rating, 90, 7.8148),
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
    assert c.rmr == pytest.approx(53.9607, abs=1e-4)
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
        assert lo <= fn(y) <= fn(x) + 1e-12 and fn(x) <= top
    else:
        assert lo <= fn(x) <= fn(y) + 1e-12 and fn(y) <= top


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


# Condición de juntas, agua y alterabilidad (Tabla 3 de Kundu et al. 2020); valores calculados con las ecuaciones.
_soft89 = lambda x: rm.rating_infilling89_continuous(x, soft=True)  # noqa: E731
_soft14 = lambda x: rm.rmr14_infilling_rating(x, soft=True)  # noqa: E731


@pytest.mark.parametrize("fn,x,y", [
    (rm.rating_persistence89_continuous, 0, 6.0), (rm.rating_persistence89_continuous, 2, 3.7594),
    (rm.rating_persistence89_continuous, 10, 1.5015),
    (rm.rating_aperture89_continuous, 0, 6.0), (rm.rating_aperture89_continuous, 0.5, 3.4364),
    (rm.rating_aperture89_continuous, 5, 0.7062),
    (rm.rating_roughness89_continuous, 0, 0.0), (rm.rating_roughness89_continuous, 20, 6.0),
    (rm.rating_infilling89_continuous, 0, 6.0), (rm.rating_infilling89_continuous, 5, 3.1623),
    (rm.rating_infilling89_continuous, 20, 2.0064),
    (_soft89, 0, 6.0), (_soft89, 2, 4.6286), (_soft89, 10, 0.1577),
    (rm.rating_weathering89_continuous, 0, 5.9993), (rm.rating_weathering89_continuous, 30, 4.3237),
    (rm.rating_weathering89_continuous, 100, 0.0783),
    (rm.rating_inflow89_continuous, 0, 15.0), (rm.rating_inflow89_continuous, 25, 4.5833),
    (rm.rating_inflow89_continuous, 200, 0.7820),
    (rm.rating_water_pressure89_continuous, 0, 15.0), (rm.rating_water_pressure89_continuous, 0.15, 7.0),
    (rm.rating_water_pressure89_continuous, 2.5, 0.0),
    (rm.rmr14_continuity_rating, 0, 5.0), (rm.rmr14_continuity_rating, 4, 3.0), (rm.rmr14_continuity_rating, 12, 0.0),
    (rm.rmr14_roughness_rating, 20, 5.0),
    (rm.rmr14_infilling_rating, 0, 5.0), (rm.rmr14_infilling_rating, 5, 2.8571), (_soft14, 0, 5.0), (_soft14, 3, 1.25),
    (rm.rmr14_weathering_rating, 0, 4.9988), (rm.rmr14_weathering_rating, 40, 2.7110),
    (rm.rmr14_weathering_rating, 100, 0.0865),
    (rm.rmr14_alterability_rating, 0, 0.0354), (rm.rmr14_alterability_rating, 50, 4.9031),
    (rm.rmr14_alterability_rating, 100, 10.0),
])
def test_condition_values(fn, x, y):
    assert fn(x) == pytest.approx(y, abs=1e-4)


@pytest.mark.parametrize("fn,hi,top,rising", [
    (rm.rating_persistence89_continuous, 100.0, 6.0, False), (rm.rating_aperture89_continuous, 20.0, 6.0, False),
    (rm.rating_roughness89_continuous, 20.0, 6.0, True), (rm.rating_infilling89_continuous, 50.0, 6.0, False),
    (_soft89, 50.0, 6.0, False), (rm.rating_weathering89_continuous, 100.0, 6.0, False),
    (rm.rating_inflow89_continuous, 500.0, 15.0, False), (rm.rating_water_pressure89_continuous, 5.0, 15.0, False),
    (rm.rmr14_continuity_rating, 20.0, 5.0, False), (rm.rmr14_roughness_rating, 20.0, 5.0, True),
    (rm.rmr14_infilling_rating, 50.0, 5.0, False), (_soft14, 50.0, 5.0, False),
    (rm.rmr14_weathering_rating, 100.0, 5.0, False), (rm.rmr14_alterability_rating, 100.0, 10.0, True),
])
@given(a=st.floats(0, 1), b=st.floats(0, 1))
def test_condition_monotone_and_in_range(fn, hi, top, rising, a, b):
    x, y = sorted((a * hi, b * hi))
    lo_x, lo_y = fn(x), fn(y)
    assert 0.0 <= min(lo_x, lo_y) and max(lo_x, lo_y) <= top
    assert (lo_x <= lo_y + 1e-12) if rising else (lo_y <= lo_x + 1e-12)


@pytest.mark.parametrize("fn,x,name", [
    (rm.rating_persistence89_continuous, -1, "persistence_m"), (rm.rating_aperture89_continuous, -1, "aperture_mm"),
    (rm.rating_roughness89_continuous, 21, "jrc"), (rm.rating_infilling89_continuous, -1, "infilling_mm"),
    (rm.rating_weathering89_continuous, 101, "i5_pct"), (rm.rating_inflow89_continuous, -1, "inflow_l_min"),
    (rm.rating_water_pressure89_continuous, -1, "pressure_ratio"), (rm.rmr14_continuity_rating, -1, "continuity_m"),
    (rm.rmr14_roughness_rating, -1, "jrc"), (rm.rmr14_infilling_rating, -1, "infilling_mm"),
    (rm.rmr14_weathering_rating, -1, "i5_pct"), (rm.rmr14_alterability_rating, 101, "id2_pct"),
])
def test_condition_errors_name_parameter(fn, x, name):
    with pytest.raises(ValueError, match=name):
        fn(x)


def test_jcond_sums_and_feed_the_ratings():
    j = rm.JointCondition89Continuous(persistence_m=2, aperture_mm=0.5, jrc=10, infilling_mm=2, i5_pct=30)
    assert rm.jcond89_continuous(j) == pytest.approx(20.2842, abs=1e-4)
    with pytest.raises(ValueError, match="persistence_m"):
        rm.jcond89_continuous(rm.JointCondition89Continuous())
    j14 = rm.JointCondition14Continuous(continuity_m=2, jrc=10, infilling_mm=1, i5_pct=20, soft_infilling=True)
    assert rm.jcond14_continuous(j14) == pytest.approx(13.2746, abs=1e-4)

    i = _input(rm.RmrFunctions.Continuous)
    i.joint_condition_rating, i.water, i.water_rating = rm.jcond89_continuous(j), None, rm.rating_inflow89_continuous(25)
    r = rm.rmr89(i)
    assert r.r_condition == pytest.approx(20.2842, abs=1e-4) and r.r_water == pytest.approx(4.5833, abs=1e-4)


def test_water_or_water_rating_rmr89():
    i = _input(rm.RmrFunctions.Discrete)
    i.water_rating = 7.0
    with pytest.raises(ValueError, match="exactly one of 'water' or 'water_rating'"):
        rm.rmr89(i)
    i.water = None
    assert rm.rmr89(i).rmr == 50.0  # Damp puntúa 10: con 7 baja tres puntos
    i.water_rating = 16.0
    with pytest.raises(ValueError, match="water_rating"):
        rm.rmr89(i)


def _rmr14():
    i = rm.Rmr14Input()
    i.strength_rating, i.joints_per_m_rating, i.continuity_m = 10, 30, 2.0
    i.roughness, i.infilling, i.alteration = rm.Roughness14.Rough, rm.Infilling14.HardUnder5mm, rm.Alteration14.Unaltered
    i.water, i.id2_pct = rm.Water.Dry, 90
    return i


def test_rmr14_ratings_replace_their_data():
    base = rm.rmr14(_rmr14()).basic  # 10 + 30 + 4 + 3 + 5 + 5 + 15 + 10
    assert base == 82.0
    i = _rmr14()
    i.continuity_m, i.roughness, i.infilling, i.alteration = float("nan"), None, None, None
    i.joint_condition_rating = 12.5
    i.water, i.water_rating = None, 11.0
    i.id2_pct, i.alterability_rating = float("nan"), rm.rmr14_alterability_rating(90)
    assert rm.rmr14(i).basic == pytest.approx(10 + 30 + 12.5 + 11 + rm.rmr14_alterability_rating(90))


@pytest.mark.parametrize("field,value,msg", [
    ("joint_condition_rating", 12.0, "joint_condition_rating"), ("water_rating", 10.0, "water_rating"),
    ("alterability_rating", 8.0, "alterability_rating"),
])
def test_rmr14_data_and_rating_not_both(field, value, msg):
    i = _rmr14()
    setattr(i, field, value)
    with pytest.raises(ValueError, match=f"'{msg}', not both"):
        rm.rmr14(i)
