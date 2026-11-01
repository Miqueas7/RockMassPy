"""Propiedades (hypothesis) y rechazo de NaN (celdas vacías de Excel)."""
import pytest
from hypothesis import given, settings, strategies as st

import rockmasspy as rm


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
