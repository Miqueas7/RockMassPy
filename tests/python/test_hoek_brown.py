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


def test_moduli_with_damage():
    # d = 0.5: valores calculados por nosotros con la fórmula publicada (no publicados).
    assert rm.erm_hoek_diederichs_generalized(45, 0.5, 20000).value == pytest.approx(2117.687, abs=0.001)
    assert rm.em_hoek2002(45, 0.5, 50).value == pytest.approx(3.976915, abs=1e-5)


def test_unit_warning_sigma_ci():
    mc = rm.hb_mohr_coulomb(401, rm.hb_params(45, 10, 0), 1.0)
    assert mc.warnings == ["sigma_ci_mpa > 400: check the unit is MPa (not kg/cm2)"]


def test_normal_shear_python():
    p = rm.hb_params(45, 10, 0, rm.HbEdition.HB2002)
    r = rm.hb_normal_shear(1.0, 50, p)
    s1 = rm.hb_sigma1(1.0, 50, p)
    assert (r.sigma_n_mpa - (s1 + 1) / 2) ** 2 + r.tau_mpa**2 == pytest.approx(((s1 - 1) / 2) ** 2, abs=1e-9)
    st = rm.hb_tensile(50, p)
    e = rm.hb_normal_shear(st, 50, p)
    assert (e.sigma_n_mpa, e.tau_mpa) == (st, 0.0)
    assert "tau_mpa" in repr(r)
    with pytest.raises(ValueError):
        rm.hb_normal_shear(st - 0.01, 50, p)


def test_normal_shear_hand_value():
    # Calculado a mano con Balmer (Hoek et al. 2002 ec. 8-10), no es un ejemplo publicado; dσ1/dσ3 = 4.981761.
    r = rm.hb_normal_shear(1.0, 50, rm.hb_params(45, 10, 0, rm.HbEdition.HB2002))
    assert r.sigma_n_mpa == pytest.approx(2.413708, abs=1e-5)
    assert r.tau_mpa == pytest.approx(3.155377, abs=1e-5)


def test_normal_shear_just_above_tensile_is_finite():
    import math
    p = rm.hb_params(45, 10, 0, rm.HbEdition.HB2002)
    st = rm.hb_tensile(50, p)
    r = rm.hb_normal_shear(st + 1e-9 * max(1.0, abs(st)), 50, p)
    assert math.isfinite(r.sigma_n_mpa) and math.isfinite(r.tau_mpa) and r.tau_mpa > 0
