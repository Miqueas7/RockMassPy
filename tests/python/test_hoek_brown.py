import pytest

import rockmasspy as rm


def test_hb1_tunnel():
    p = rm.hb_params(45, 10, 0, rm.HbEdition.HB2002)
    assert p.mb == pytest.approx(1.40256, abs=5e-6)
    scm = rm.hb_global_strength(50, p)
    assert scm == pytest.approx(7.8098, abs=5e-5)
    s3 = rm.hb_sigma3max(scm, 0.027, 100, rm.HbApplication.Tunnel)
    mc = rm.hb_mohr_coulomb(50, p, s3)
    assert mc.phi_deg == pytest.approx(47.16, abs=0.05)
    assert mc.cohesion_mpa == pytest.approx(0.58, abs=0.005)
    assert mc.info.method_id == "HB-2002"


def test_unit_weight_in_kn_raises():
    with pytest.raises(ValueError, match="MN/m3"):
        rm.hb_sigma3max(7.8, 27.0, 100, rm.HbApplication.Tunnel)


def test_moduli():
    assert rm.erm_hoek_diederichs_simplified(45, 0).value == pytest.approx(6138.31, abs=0.01)
    assert rm.em_hoek2002(45, 0, 50).unit == "GPa"


def test_mohr_coulomb_carries_d_warning():
    p = rm.hb_params(45, 10, 0.5, rm.HbEdition.HB2018)
    mc = rm.hb_mohr_coulomb(50, p, 1.0)
    assert len(mc.warnings) == 1 and "blast-damaged zone" in mc.warnings[0]
