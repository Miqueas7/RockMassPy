"""Propiedades (hypothesis) y rechazo de NaN (celdas vacías de Excel)."""
import math

import pytest
from hypothesis import given, settings, strategies as st

import rockmasspy as rm

NAN = float("nan")


@settings(deadline=None)
@given(st.floats(0, 100), st.floats(0, 100))
def test_rqd_priest_hudson_decreases(l1, l2):
    lo, hi = sorted((l1, l2))
    assert rm.rqd_priest_hudson(lo).rqd_pct >= rm.rqd_priest_hudson(hi).rqd_pct


@settings(deadline=None)
@given(st.floats(1, 100), st.floats(1, 40), st.floats(0, 1), st.floats(0, 50), st.floats(0, 50))
def test_hb_sigma1_increases_with_sigma3(gsi, mi, d, s3a, s3b):
    p = rm.hb_params(gsi, mi, d)
    lo, hi = sorted((s3a, s3b))
    assert rm.hb_sigma1(hi, 80, p) >= rm.hb_sigma1(lo, 80, p)


@settings(deadline=None)
@given(st.floats(0, 30), st.floats(0, 100))
def test_gsi2013_bounds(j, rqd):
    assert 0 <= rm.gsi_from_jcond89_rqd(j, rqd).gsi <= 95


@settings(deadline=None)
@given(st.floats(10, 100), st.floats(10, 100))
def test_q_increases_with_rqd(r1, r2):
    lo, hi = sorted((r1, r2))
    assert rm.q_value(rm.QInput(hi, 4, 1, 1, 1, 1)).q >= rm.q_value(rm.QInput(lo, 4, 1, 1, 1, 1)).q


@pytest.mark.parametrize("call", [
    lambda: rm.rqd_priest_hudson(float("nan")),
    lambda: rm.hb_params(float("nan"), 10, 0),
    lambda: rm.q_value(rm.QInput(float("nan"), 4, 1, 1, 1, 1)),
    lambda: rm.gsi_from_jcond89_rqd(20, float("nan")),
    lambda: rm.correlate(rm.Correlation.RmrFromQ_Bieniawski1976, float("nan"))])
def test_nan_from_empty_excel_cell_raises(call):  # Foco 2
    with pytest.raises(ValueError):
        call()


@settings(deadline=None)
@given(st.floats(1, 100), st.floats(1, 40), st.floats(0, 1))
def test_hb_sigma1_finite_at_tensile_strength(gsi, mi, d):  # I4
    p = rm.hb_params(gsi, mi, d)
    assert math.isfinite(rm.hb_sigma1(rm.hb_tensile(80, p), 80, p))


def _rmr89_full():
    i = rm.Rmr89Input()
    i.ucs_mpa, i.rqd_pct, i.spacing_m, i.joint_condition_rating, i.water = 120, 80, 0.5, 20, rm.Water.Dry
    return i


def _rmr76_full():
    i = rm.Rmr76Input()
    i.ucs_mpa, i.rqd_pct, i.spacing_m = 120, 80, 0.5
    i.condition, i.water = rm.JointCondition76.SlightlyRoughSlightlyWeathered, rm.Water76.CompletelyDry
    return i


def _rmr14_full():
    i = rm.Rmr14Input()
    i.strength_rating, i.joints_per_m_rating, i.continuity_m, i.id2_pct = 10, 30, 2.0, 90
    i.roughness, i.infilling, i.alteration = rm.Roughness14.Rough, rm.Infilling14.HardUnder5mm, rm.Alteration14.Moderately
    i.water = rm.Water.Damp
    return i


_REQUIRED = [  # (calcular, armar completo, campo, valor «sin dato»)
    *[(rm.rmr89, _rmr89_full, f, NAN) for f in ("rqd_pct", "spacing_m", "joint_condition_rating")],
    (rm.rmr89, _rmr89_full, "water", None),
    *[(rm.rmr76, _rmr76_full, f, NAN) for f in ("rqd_pct", "spacing_m")],
    *[(rm.rmr76, _rmr76_full, f, None) for f in ("condition", "water")],
    *[(rm.rmr14, _rmr14_full, f, NAN) for f in ("strength_rating", "joints_per_m_rating", "continuity_m", "id2_pct")],
    *[(rm.rmr14, _rmr14_full, f, None) for f in ("roughness", "infilling", "alteration", "water")],
    *[(rm.q_value, lambda: rm.QInput(90, 4, 3, 1, 1, 15), f, NAN) for f in ("rqd_pct", "jn", "jr", "ja", "jw", "srf")],
]


@pytest.mark.parametrize("calc, make", [(rm.rmr89, rm.Rmr89Input), (rm.rmr76, rm.Rmr76Input),
                                        (rm.rmr14, rm.Rmr14Input), (rm.q_value, rm.QInput)])
def test_default_constructed_input_raises(calc, make):  # I1: nada toma el valor más favorable
    with pytest.raises(ValueError):
        calc(make())


@pytest.mark.parametrize("calc, full, field, missing", _REQUIRED, ids=lambda x: x if isinstance(x, str) else None)
def test_each_missing_field_raises_naming_it(calc, full, field, missing):  # I1
    inp = full()
    calc(inp)  # completo: no lanza
    setattr(inp, field, missing)
    with pytest.raises(ValueError, match=f"'{field}'"):
        calc(inp)
