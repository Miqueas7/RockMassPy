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
    assert (r.from_, r.to) == ("Q", "RMR76")  # ajustada con el RMR de 1976
    assert len(r.warnings) == 1


def test_chaining_blocked_but_explicit_value_allowed():
    rmr = rm.correlate(rm.Correlation.RmrFromQ_Bieniawski1976, 4.5)
    with pytest.raises(ValueError, match="must not be chained"):
        rm.correlate(rm.Correlation.GsiFromRmr89Prime_HoekDiederichs2006, rmr)
    g = rm.correlate(rm.Correlation.GsiFromRmr89Prime_HoekDiederichs2006, rmr.value)
    assert abs(g.value - (rmr.value - 5)) < 1e-12


def test_gsi_rqd_fraction_warns():
    w = rm.gsi_from_jcond89_rqd(18, 0.7).warnings
    assert w == ["rqd_pct <= 1: RQD is a percentage (0-100); check it is not a fraction"]


def test_custom_correlation():
    c = rm.CustomCorrelation(name="mineA-RMR-Q", from_="Q", to="RMR89", form=rm.CorrelationForm.LogLinear,
                             a=7.5, b=47.0, valid_min=0.01, valid_max=100.0, source="site fit")
    r = rm.correlate_custom(c, 4.5)
    assert r.info.method_id == "site:mineA-RMR-Q" and r.info.verification == rm.Verification.UserDefined
    assert r.from_ == "Q" and r.warnings == []
    assert len(rm.correlate_custom(c, 500.0).warnings) == 1
    with pytest.raises(ValueError):
        rm.correlate_custom(c, r)
    with pytest.raises(ValueError):
        rm.correlate_custom(c, 0.0)
    assert c == rm.CustomCorrelation("mineA-RMR-Q", "Q", "RMR89", rm.CorrelationForm.LogLinear, 7.5, 47.0, 0.01, 100.0, "site fit")
