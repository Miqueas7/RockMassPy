import pytest

import rockmasspy as rm


def test_hoek_granite():
    in_ = rm.Rmr89Input()
    in_.is50_mpa = 8.0
    in_.rqd_pct = 70
    in_.spacing_m = 0.30
    in_.joint_condition = rm.JointCondition89(
        2.0, 0.5, rm.Roughness.SlightlyRough, rm.Infilling.None_, rm.Weathering.Slightly
    )
    in_.water = rm.Water.Wet
    in_.orientation = rm.OrientationClass.Fair
    r = rm.rmr89(in_)
    assert r.rmr == 59
    assert r.rmr_class.roman == "III"
    assert r.info.method_id == "RMR89"


def test_ambiguous_raises():
    in_ = rm.Rmr89Input()
    in_.rqd_pct = 80
    with pytest.raises(ValueError):
        rm.rmr89(in_)
