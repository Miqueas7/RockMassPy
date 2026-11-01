import pytest

import rockmasspy as rm


def test_gsi_quantified():
    r = rm.gsi_from_jcond89_rqd(22, 70)
    assert r.gsi == 68.0 and r.info.method_id == "GSI-2013"
    assert rm.jcond89_from_jr_ja(3, 1) == 26.25
    with pytest.raises(ValueError):
        rm.gsi_from_jcond89_rqd(31, 70)


def test_correlation_value_and_labels():
    r = rm.correlate(rm.Correlation.RmrFromQ_Bieniawski1976, 4.5)
    assert abs(r.value - 57.536) < 1e-3
    assert (r.from_, r.to) == ("Q", "RMR89")
    assert len(r.warnings) == 1


def test_chaining_blocked_but_explicit_value_allowed():
    rmr = rm.correlate(rm.Correlation.RmrFromQ_Bieniawski1976, 4.5)
    with pytest.raises(ValueError, match="must not be chained"):
        rm.correlate(rm.Correlation.GsiFromRmr89Prime_HoekDiederichs2006, rmr)
    g = rm.correlate(rm.Correlation.GsiFromRmr89Prime_HoekDiederichs2006, rmr.value)
    assert abs(g.value - (rmr.value - 5)) < 1e-12
