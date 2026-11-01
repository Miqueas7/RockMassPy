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


def test_rmr_class_rejects_nan():
    with pytest.raises(ValueError):
        rm.rmr_class(float("nan"))


def test_condition_rating_accepts_excel_float_and_rejects_nan():
    inp = rm.Rmr89Input()
    inp.ucs_mpa, inp.rqd_pct, inp.spacing_m, inp.water = 120.0, 80.0, 0.5, rm.Water.Dry
    inp.joint_condition_rating = 18.0
    assert rm.rmr89(inp).r_condition == 18.0
    inp.joint_condition_rating = float("nan")
    with pytest.raises(ValueError, match="joint_condition_rating"):
        rm.rmr89(inp)


def test_ucs_over_400_warns_about_units_in_rmr89_and_rmr76():
    msg = "ucs_mpa > 400: check the unit is MPa (not kg/cm2)"
    i = rm.Rmr89Input()
    i.ucs_mpa, i.rqd_pct, i.spacing_m, i.joint_condition_rating, i.water = 401, 80, 0.5, 20, rm.Water.Dry
    i.orientation = rm.OrientationClass.Fair
    assert rm.rmr89(i).warnings == [msg]
    j = rm.Rmr76Input()
    j.ucs_mpa, j.rqd_pct, j.spacing_m = 401, 80, 0.5
    j.condition, j.water, j.orientation = rm.JointCondition76.VeryRoughTight, rm.Water76.CompletelyDry, rm.OrientationClass.Fair
    assert rm.rmr76(j).warnings == [msg]
