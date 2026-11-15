import math

import pytest

import rockmasspy as rm


def test_kirsch():
    b = rm.kirsch_boundary(30, 1)
    assert b.crown_mpa == pytest.approx(60) and b.sidewall_mpa == pytest.approx(60)
    s = rm.kirsch_stress(30, 1, 1, 1, 0)
    assert s.sigma_r == pytest.approx(0, abs=1e-9) and s.sigma_theta == pytest.approx(60)
    b = rm.kirsch_boundary(10, 0.5)
    assert (b.crown_mpa, b.sidewall_mpa) == (pytest.approx(5), pytest.approx(25))
    assert rm.kirsch_stress(10, 0.5, 2, 3, 90).tau_r_theta == pytest.approx(0, abs=1e-9)
    assert s.info.method_id == "Kirsch-1898"
    with pytest.raises(ValueError, match="r_m"):
        rm.kirsch_stress(10, 1, 2, 1.5, 0)


def test_ellipse():
    assert rm.ellipse_boundary_stress(20, 10, 1, 1, 0) == pytest.approx(50)
    assert rm.ellipse_boundary_stress(20, 10, 1, 1, 90) == pytest.approx(10)
    for th in (0.0, math.degrees(0.3), math.degrees(0.9), 90.0):
        assert rm.ellipse_boundary_stress(20, 10, 1, 2, th) == pytest.approx(30)
    e = rm.ellipse_ends(20, 0.5, 4, 2)
    assert e.sidewall_mpa == pytest.approx(90) and e.crown_mpa == pytest.approx(0, abs=1e-9)
    with pytest.raises(ValueError, match="b_m"):
        rm.ellipse_boundary_stress(20, 10, 1, 0, 0)


def test_einstein_schwartz():
    def run(theta):
        i = rm.EinsteinSchwartzInput()
        i.sigma_v_mpa, i.k_ratio, i.e_rock_mpa, i.nu_rock = 15, 2, 6000, 0.2
        i.e_lining_mpa, i.nu_lining, i.thickness_m, i.radius_m, i.theta_deg = 20000, 0.2, 0.5, 2.5, theta
        return rm.einstein_schwartz(i)

    r = run(0)
    assert r.c_star == pytest.approx(1.5) and r.f_star == pytest.approx(450)
    for th, n, m in ((0, 14.61, -0.703), (45, 25.61, 0.0), (90, 36.62, 0.703)):
        r = run(th)
        assert r.n_mn == pytest.approx(n, abs=0.01) and r.m_mnm == pytest.approx(m, abs=0.001)
    assert r.info.method_id == "Lining-Einstein-Schwartz-1979"
    with pytest.raises(ValueError, match="sigma_v_mpa"):
        rm.einstein_schwartz(rm.EinsteinSchwartzInput())


def test_hoek_marinos():
    s = rm.hoek_marinos(0.6, 4, 0, 2)
    assert s.plastic_radius_m == pytest.approx(7.37, abs=0.01)
    assert s.strain_pct == pytest.approx(8.89, abs=0.01)
    assert s.wall_displacement_m == pytest.approx(0.178, abs=0.001)
    assert s.squeezing_class == "D" and s.in_fit_range
    s = rm.hoek_marinos(0.6, 4, 1, 2)
    assert s.strain_pct == pytest.approx(1.96, abs=0.01) and s.squeezing_class == "B"
    assert not rm.hoek_marinos(2.4, 4, 0, 2).in_fit_range
    assert s.info.method_id == "Squeezing-Hoek-Marinos-2000"
    with pytest.raises(ValueError, match="p0_mpa"):
        rm.hoek_marinos(1, 0, 0, 2)
    with pytest.raises(ValueError, match="pi_mpa"):
        rm.hoek_marinos(1, 4, -1, 2)


def _rsv5(c, p0, psi=0.0):
    return rm.GrcMcInput(radius_m=1, p0_mpa=p0, e_mpa=10000, nu=0.2, c_mpa=c, phi_deg=30, psi_deg=psi)


def test_grc_mc_rsv_and_soria():
    for c, p0, rp in ((3.45, 30, 1.735), (3.45, 20, 1.474), (5, 30, 1.494), (5, 20, 1.286)):
        assert rm.grc_mc_plastic_radius(_rsv5(c, p0), 0) == pytest.approx(rp, abs=0.0005)
    assert rm.grc_mc_displacement(_rsv5(3.45, 30, 30), 0) * 1000 == pytest.approx(19.09, abs=0.01)
    soria = rm.GrcMcInput(radius_m=5, p0_mpa=4.05, e_mpa=446, nu=0.3, c_mpa=1, phi_deg=37, psi_deg=6)
    assert rm.grc_mc_plastic_radius(soria, 0) == pytest.approx(5.8573, abs=0.0001)
    assert rm.grc_mc_displacement(soria, 0) * 1000 == pytest.approx(68.049, abs=0.001)
    r = rm.grc_mc(soria, 30)
    assert len(r.curve) == 30 and r.info.method_id == "GRC-MC-Salencon-1969"
    assert r.rp_unsupported_m == pytest.approx(5.8573, abs=0.0001)


def test_grc_mc_from_hb_rocsupport_example():
    inp = rm.grc_mc_from_hb(7, 15, 10, 0, 1.62, 6, 0.3, rm.HbEdition.HB2002)
    assert inp.e_mpa == pytest.approx(352.817, abs=0.001)
    assert inp.sigma_cm_override_mpa == pytest.approx(0.46927, abs=0.00001)
    assert inp.phi_deg == pytest.approx(25.6394, abs=0.0001)
    r = rm.grc_mc(inp)
    assert r.info.method_id == "GRC-HB-equivalent-MC" and r.notes
    assert r.rp_unsupported_m == pytest.approx(13.78, abs=0.01)
    assert r.u_max_m / 6 * 100 == pytest.approx(2.030, abs=0.001)


def test_grc_mc_all_elastic_and_degenerate():
    r = rm.grc_mc(_rsv5(3.45, 1))
    assert r.rp_unsupported_m == 1.0 and all(math.isfinite(p.u_m) for p in r.curve)
    with pytest.raises(ValueError, match="phi_deg"):
        rm.grc_mc_displacement(rm.GrcMcInput(radius_m=1, p0_mpa=30, e_mpa=1e4, nu=0.2, c_mpa=3, phi_deg=0.5), 0)
    with pytest.raises(ValueError, match="c_mpa"):
        rm.grc_mc(_rsv5(0, 30))


def test_grc_hb_carranza_torres():
    inp = rm.GrcHbInput(radius_m=3.82, p0_mpa=30, g_mpa=1000, nu=0.25, sigma_ci_mpa=30, mb=1.7, s=3.9e-3)
    assert rm.grc_hb(inp).p_crit_mpa == pytest.approx(15.78, abs=0.01)
    assert rm.grc_hb_plastic_radius(inp, 5) / 3.82 == pytest.approx(1.623, abs=0.0005)
    assert rm.grc_hb_displacement(inp, 5) == pytest.approx(0.0835, abs=0.0001)
    assert rm.grc_hb(inp).info.method_id == "GRC-HB-Carranza-Torres-Fairhurst-2000"


D4 = "LDP not valid for Rp > 2R; use VD2009"
D6 = "support does not intersect the ground reaction curve"


def _rst1(scm=0.46927):
    return rm.GrcMcInput(radius_m=6, p0_mpa=1.62, e_mpa=352.817, nu=0.3, c_mpa=0.2, phi_deg=25.6394,
                         sigma_cm_override_mpa=scm)


def _u_install(inp, ldp, x=0.5):
    rs = rm.grc_mc_plastic_radius(inp, 0) / inp.radius_m
    return rm.ldp_ratio(ldp, x, rs, inp.nu) * rm.grc_mc_displacement(inp, 0)


def test_ldp_control_values():
    for ldp, rs, vals in ((rm.Ldp.VD2009, 1, (0.1055, 0.2869, 0.8409)), (rm.Ldp.VD2009, 2.5, (0.0843, 0.2291, 0.5769)),
                          (rm.Ldp.CHERN1998, 2.5, (0.1199, 0.3078, 0.5624))):
        for x, v in zip((-1, 0, 1), vals):
            assert rm.ldp_ratio(ldp, x, rs, 0.3) == pytest.approx(v, abs=0.0001)
    for x, v in ((0, 0.25), (1, 0.8622), (2, 0.9442)):
        assert rm.ldp_ratio(rm.Ldp.PANET1995, x, 1, 0.3) == pytest.approx(v, abs=0.0001)
    assert rm.ldp_ratio(rm.Ldp.VD2009, 0, 2, 0.3) == pytest.approx(0.247, abs=0.0005)
    assert rm.ldp_ratio(rm.Ldp.UNLU_GERCEK2003, 0, 1, 0.3) == pytest.approx(0.256)
    assert rm.ldp_distance(rm.Ldp.VD2009, rm.ldp_ratio(rm.Ldp.VD2009, 0.7, 2.5, 0.3), 2.5, 0.3) == pytest.approx(0.7)
    assert rm.ldp_info(rm.Ldp.VD2009).method_id == "LDP-Vlachopoulos-Diederichs-2009"
    with pytest.raises(ValueError, match="ldp"):
        rm.ldp_distance(rm.Ldp.PANET1995, 0.5, 2, 0.3)


def test_interaction_rst_example1():
    bolt = [rm.support_from_eps("B34", 0.354, 0.002)]
    inp = _rst1()
    r = rm.interaction_mc(inp, bolt, _u_install(inp, rm.Ldp.CHERN1998), rm.Combination.ROCSUPPORT3)
    assert r.found and r.elastic
    assert r.fs == pytest.approx(1.838, abs=0.001)
    assert r.rp_eq_m == pytest.approx(10.02, abs=0.01) and r.strain_eq_pct == pytest.approx(0.989, abs=0.001)
    assert r.info.method_id == "Support-interaction" and len(r.fs_by_element) == 1
    for ldp, fs in ((rm.Ldp.VD2009, 1.92), (rm.Ldp.PANET1995, 5.24)):
        assert rm.interaction_mc(inp, bolt, _u_install(inp, ldp), rm.Combination.ROCSUPPORT3).fs == pytest.approx(
            fs, abs=0.01)


def test_interaction_combination_and_thick_ring():
    els = [rm.support_from_eps("B34", 0.354, 0.002), rm.support_from_eps("SC50", 0.325, 0.001)]
    for mode, eps in ((rm.Combination.ROCSUPPORT3, 0.0015), (rm.Combination.ROCSUPPORT, 0.002)):
        (c,) = rm.combine_supports(els, mode)
        assert c.psm_mpa == pytest.approx(0.679) and c.psm_mpa / c.stiffness_mpa == pytest.approx(eps)
    inp = _rst1()
    u_in = _u_install(inp, rm.Ldp.CHERN1998)
    r = rm.interaction_mc(inp, els, u_in, rm.Combination.STIFFNESS)
    loads = [e.stiffness_mpa * (r.u_eq_m - u_in) / 6 for e in els]
    assert r.fs_by_element == pytest.approx([e.psm_mpa / p for e, p in zip(els, loads)], rel=1e-6)
    assert r.fs == pytest.approx(min(r.fs_by_element))
    k = rm.thick_ring_stiffness(30000, 0.25, 1.85, 0.15)
    assert k == pytest.approx(2777.5, abs=0.5)
    ubc = rm.GrcMcInput(radius_m=1.85, p0_mpa=20, e_mpa=5000, nu=0.25, c_mpa=100, phi_deg=30)
    r = rm.interaction_mc(ubc, [rm.SupportElement(code="lining", psm_mpa=50, stiffness_mpa=k)], 0.001,
                          rm.Combination.STIFFNESS)
    assert r.u_eq_m * 1000 == pytest.approx(5.869, abs=0.001) and r.p_eq_mpa == pytest.approx(7.310, abs=0.001)


def test_interaction_beyond_elastic_limit():
    inp = _rst1()
    weak = [rm.SupportElement(code="weak", psm_mpa=0.1, stiffness_mpa=500)]
    r = rm.interaction_mc(inp, weak, _u_install(inp, rm.Ldp.CHERN1998), rm.Combination.STIFFNESS)
    assert r.found and not r.elastic and r.fs < 1
    assert r.p_eq_mpa == pytest.approx(0.1)


def test_interaction_installed_too_late():
    inp = _rst1()
    umax = rm.grc_mc_displacement(inp, 0)
    r = rm.interaction_mc(inp, [rm.support_from_eps("B34", 0.354, 0.002)], umax, rm.Combination.ROCSUPPORT3)
    assert not r.found and r.fs is None and list(r.fs_by_element) == [] and D6 in r.warnings
    for f in (1e-12, 1e-14):  # casi al final: cruce con presión ínfima y FS positivo y finito
        r = rm.interaction_mc(inp, [rm.support_from_eps("B34", 0.354, 0.002)], umax * (1 - f),
                              rm.Combination.ROCSUPPORT3)
        assert r.found and math.isfinite(r.fs) and r.fs > 0 and r.fs_by_element[0] > 0


def test_interaction_ldp_warning_panet():
    inp = _rst1(0.29343)  # rp/R = 3
    assert rm.grc_mc_plastic_radius(inp, 0) / 6 == pytest.approx(3.0, abs=0.01)
    bolt = [rm.support_from_eps("B34", 0.354, 0.002)]
    u_in = _u_install(inp, rm.Ldp.PANET1995)
    assert D4 in rm.interaction_mc(inp, bolt, u_in, rm.Combination.ROCSUPPORT3, rm.Ldp.PANET1995).warnings
    assert D4 not in rm.interaction_mc(inp, bolt, u_in, rm.Combination.ROCSUPPORT3, ldp=rm.Ldp.VD2009).warnings
    hb = rm.GrcHbInput(radius_m=3.82, p0_mpa=30, g_mpa=1000, nu=0.25, sigma_ci_mpa=30, mb=1.7, s=3.9e-3)
    assert rm.interaction_hb(hb, [rm.SupportElement("x", 100, 3000)], 0.01, rm.Combination.STIFFNESS).found


def test_hb1982_and_reed_stresses():
    hb = rm.Hb1982Input(p0_mpa=30, radius_m=1, sigma_c_mpa=100, m=2.515, s=0.003865, mr=0.5, sr=1e-5)
    assert rm.hb1982_plastic_radius(hb) == pytest.approx(2.168, abs=0.001)
    s = rm.hb1982_stress(hb, 5)
    assert s.sigma_r == pytest.approx(25.8, abs=0.1) and s.sigma_theta == pytest.approx(34.2, abs=0.1)
    # ro = 4 y q = 100: la Tabla 30.1 del manual trae errata (FORMULAS §14)
    rd = rm.ReedInput(q_mpa=100, radius_m=4, c_peak_mpa=30, c_res_mpa=5, phi_deg=30)
    assert rm.reed_plastic_radius(rd) == pytest.approx(7.77, abs=0.01)
    assert rm.reed_stress(rd, 4).sigma_theta == pytest.approx(17.3, abs=0.1)
    assert rm.reed_stress(rd, 4).info.method_id == "Reed-1986"
    assert rm.hb1982_stress(hb, 5).info.method_id == "HB-1982-brittle"


def test_reed_no_residual_cohesion_no_pressure():
    rd = rm.ReedInput(q_mpa=100, radius_m=4, c_peak_mpa=30, c_res_mpa=0, phi_deg=30)
    with pytest.raises(ValueError, match="c_res_mpa") as e:
        rm.reed_plastic_radius(rd)
    assert "100" not in str(e.value)
