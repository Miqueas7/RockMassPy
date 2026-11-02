import pytest
from hypothesis import given, strategies as st

import rockmasspy as rm


def _synthetic():
    i = rm.Mrmr90Input()
    i.irs_mpa = 100
    i.rqd_pct = 75
    i.spacings_m = [0.5, 1.0, 3.0]
    i.joint_condition = 10.8
    i.weathering_pct, i.orientation_pct, i.stress_pct, i.blasting_pct = 85, 75, 100, 90
    return i


def test_caso_sintetico():  # ejemplo de la p. 266
    r = rm.mrmr90(_synthetic())
    assert r.rmr == pytest.approx(46.351970, abs=1e-6)
    assert (r.rmr_class, r.mrmr_class) == ("3B", "4B")
    assert r.adjustment == pytest.approx(0.57375)
    assert r.mrmr == pytest.approx(26.594443, abs=1e-6)
    assert r.warnings == [] and r.info.method_id == "MRMR-Laubscher1990"


def test_junta_y_vias():
    j = rm.JointCondition90()
    j.large, j.small = rm.JointExpressionLarge.Straight, rm.JointExpressionSmall.SmoothPlanar
    j.filling, j.water = rm.JointFilling90.SoftMedium, rm.JointWater90.Dry
    assert rm.joint_condition90(j) == pytest.approx(10.8, abs=1e-9)
    i = _synthetic()
    i.ff_per_m, i.joint_sets = 5, 2
    with pytest.raises(ValueError, match="pass rqd_pct and spacings_m, or ff_per_m and joint_sets"):
        rm.mrmr90(i)
    assert rm.laubscher_class(80.5) == "2A"
    assert rm.weathering_adjustment90(rm.Weathering90.Slight, 2.5) == 92
    assert rm.blasting_adjustment90(rm.Blasting90.Poor) == 80


@given(a=st.floats(0, 300), b=st.floats(0, 300))
def test_irs_monotono(a, b):
    lo, hi = sorted((a, b))
    assert rm.rating_irs90(lo) <= rm.rating_irs90(hi)


@given(a=st.floats(0, 100), b=st.floats(0, 100))
def test_rqd_monotono(a, b):
    lo, hi = sorted((a, b))
    assert rm.rating_rqd90(lo) <= rm.rating_rqd90(hi)


@given(s=st.lists(st.floats(0.01, 20), min_size=1, max_size=3), k=st.integers(0, 2), d=st.floats(0, 5))
def test_espaciamiento_monotono(s, k, d):
    s2 = list(s)
    s2[k % len(s)] += d
    assert 0 <= rm.rating_joint_spacing90(s) <= rm.rating_joint_spacing90(s2) + 1e-9
    assert rm.rating_joint_spacing90(s2) <= 25 + 1e-9


@given(w=st.floats(30, 100), d=st.floats(0, 20),
       field=st.sampled_from(["weathering_pct", "orientation_pct", "stress_pct", "blasting_pct"]))
def test_mrmr_crece_con_ajuste(w, d, field):
    i = _synthetic()
    setattr(i, field, w)
    base = rm.mrmr90(i).mrmr
    setattr(i, field, w + d)
    assert rm.mrmr90(i).mrmr >= base
