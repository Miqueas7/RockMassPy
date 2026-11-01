import pytest

import rockmasspy as rm


def test_rmr76_basic():
    i = rm.Rmr76Input()
    i.ucs_mpa = 120
    i.rqd_pct = 80
    i.spacing_m = 0.5
    i.condition = rm.JointCondition76.SlightlyRoughSlightlyWeathered
    i.water = rm.Water76.CompletelyDry
    r = rm.rmr76(i)
    assert r.basic == 79
    assert r.info.method_id == "RMR76"


def _in14():
    i = rm.Rmr14Input()
    i.strength_rating = 10
    i.joints_per_m_rating = 30
    i.continuity_m = 2.0
    i.roughness = rm.Roughness14.Rough
    i.infilling = rm.Infilling14.HardUnder5mm
    i.alteration = rm.Alteration14.Moderately
    i.water = rm.Water.Damp
    i.id2_pct = 90
    i.orientation = rm.OrientationClass.Fair
    return i


def test_rmr14_basic_with_face_factor():
    i = _in14()
    i.ice = 50.0
    r = rm.rmr14(i)
    assert r.basic == 75 and r.f0 == -5
    assert r.fs == pytest.approx(1.15)
    assert r.rmr == pytest.approx(80.5)
    assert r.rmr_class.roman == "I"


def test_rmr14_tbm_raises():
    i = _in14()
    i.excavation = rm.Excavation.Tbm
    with pytest.raises(ValueError):
        rm.rmr14(i)
