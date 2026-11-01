import pytest

import rockmasspy as rm


def test_priest_hudson():
    r = rm.rqd_priest_hudson(10.0)
    assert r.rqd_pct == pytest.approx(73.5759, abs=1e-4)
    assert r.info.method_id == "RQD-PH1976"
    assert r.info.verification == rm.Verification.Primary


def test_jv_default_and_1982():
    assert rm.rqd_from_jv(10.0).rqd_pct == 85.0
    assert rm.rqd_from_jv(10.0, rm.JvMethod.Palmstrom1982).rqd_pct == 82.0


def test_core_and_errors():
    assert rm.rqd_from_core([0.25, 0.05, 0.30, 0.08, 0.10], 1.0).rqd_pct == pytest.approx(65.0)
    with pytest.raises(ValueError):
        rm.rqd_from_core([0.8, 0.5], 1.0)
    assert rm.rqd_from_jv(0.0).warnings != []
