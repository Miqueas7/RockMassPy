import dataclasses

import pytest

import rockmasspy as rm
from rockmasspy import probabilistic as pb
from rockmasspy.excavation import TunnelInput, analyze_tunnel, tunnel_uncertainty
from rockmasspy.support_capacity import SupportCapacity, hoek_psm

W_K = "analytical GRC assumes a hydrostatic field (K = 1)"
W_SHAPE = "analytical GRC assumes a circular opening; use an equivalent radius with care"
W_LARGE = "large strain: small-strain solution may underestimate convergence"


def _rst1(**kw):
    return TunnelInput(radius_m=6, p0_mpa=1.62, nu=0.3, criterion="HB", sigma_ci_mpa=7, gsi=15, mi=10, d=0.0, **kw)


def _bolt():
    return SupportCapacity("B34", "bolt", psm_mpa=hoek_psm("34 mm rockbolt", spacing_m=1.0), eps_sm=0.002)


def test_rst_example1_full_api():
    r = analyze_tunnel(_rst1(), supports=[_bolt()], install_distance_m=3, ldp="CHERN1998",
                       combination="rocsupport3")
    assert r.method == "GRC-HB-equivalent-MC"
    assert any("mixes the global rock mass strength" in n for n in r.notes)  # nota de D2: no es aviso
    assert r.interaction.fs == pytest.approx(1.838, abs=0.001)
    assert r.rp_m == pytest.approx(13.78, abs=0.01) and r.strain_pct == pytest.approx(2.030, abs=0.001)
    assert r.squeezing.squeezing_class == "B" and r.ldp_model == "CHERN1998"
    assert r.u_install_m > 0 and len(r.grc) == 50 and not r.warnings and not r.needs_attention


def test_soria_medina_api():
    inp = TunnelInput(radius_m=5, p0_mpa=4.05, nu=0.3, criterion="MC", e_mpa=446, c_mpa=1, phi_deg=37, psi_deg=6)
    r = analyze_tunnel(inp)
    assert r.rp_m == pytest.approx(5.8573, abs=0.0001) and r.u_max_m * 1000 == pytest.approx(68.049, abs=0.001)
    assert r.interaction is None and r.method == "GRC-MC-Salencon-1969"


def test_scope_warnings_once_and_without_values():
    r = analyze_tunnel(_rst1(k_ratio=0.5, shape="horseshoe"))
    assert sorted(r.warnings) == sorted([W_K, W_SHAPE]) and r.needs_attention
    assert not any("0.5" in w or "horseshoe" in w for w in r.warnings)
    weak = TunnelInput(radius_m=3, p0_mpa=5, nu=0.3, criterion="MC", e_mpa=200, c_mpa=0.3, phi_deg=22)
    big = analyze_tunnel(weak, supports=[_bolt()], install_distance_m=1)
    assert big.warnings.count(W_LARGE) == 1 and big.squeezing.squeezing_class in ("D", "E") and big.needs_attention


def test_ldp_panet_warning_reaches_result():
    inp = TunnelInput(radius_m=6, p0_mpa=1.62, nu=0.3, criterion="MC", e_mpa=352.817, c_mpa=0.05, phi_deg=25.6)
    r = analyze_tunnel(inp, supports=[_bolt()], install_distance_m=3, ldp="PANET1995")
    assert "LDP not valid for Rp > 2R; use VD2009" in r.warnings


def test_missing_parameters_named():
    with pytest.raises(ValueError, match="c_mpa") as e:
        analyze_tunnel(TunnelInput(radius_m=5, p0_mpa=4, nu=0.3, criterion="MC", e_mpa=446, phi_deg=37))
    assert "446" not in str(e.value)
    with pytest.raises(ValueError, match="gsi"):
        analyze_tunnel(TunnelInput(radius_m=5, p0_mpa=4, nu=0.3, criterion="HB", sigma_ci_mpa=7, mb=0.5, s=1e-4,
                                   a=0.56))


def test_hb_a_half_uses_carranza_torres():
    inp = TunnelInput(radius_m=3.82, p0_mpa=30, nu=0.25, criterion="HB", e_mpa=2500, sigma_ci_mpa=30, mb=1.7,
                      s=3.9e-3)
    r = analyze_tunnel(inp)
    assert r.method == "GRC-HB-Carranza-Torres-Fairhurst-2000" and r.p_crit_mpa == pytest.approx(15.78, abs=0.01)


def test_tunnel_uncertainty():
    kw = dict(supports=[_bolt()], install_distance_m=3, ldp="CHERN1998", n=60)
    var = {"gsi": pb.normal(15, 2, 10, 20)}
    a = tunnel_uncertainty(_rst1(), var, **kw)
    b = tunnel_uncertainty(_rst1(), var, **kw)
    assert a == b and a.n_valid == 60
    assert sum(a.class_probabilities.values()) == pytest.approx(1.0)
    assert 0 <= a.support_probabilities["fs_below_1"] <= 1
    assert set(a.outputs) >= {"rp_m", "strain_pct", "fs"}
    with pytest.raises(ValueError, match="unknown variable"):
        tunnel_uncertainty(_rst1(), {"zz": pb.uniform(1, 2)}, n=5)


def test_tunnel_uncertainty_bad_sample():
    with pytest.raises(ValueError, match="gsi") as e:
        tunnel_uncertainty(_rst1(), {"gsi": pb.uniform(90, 110)}, n=50)
    msg = str(e.value)
    assert "narrow" in msg and "minimum" in msg and "maximum" in msg
    assert not any(t in msg for t in ("90", "110", "Received"))


N_ERM = "Erm from Hoek-Carranza-Corkum (2002)"


def test_hb_d2_uses_user_e_mpa():
    base = analyze_tunnel(_rst1())
    assert N_ERM in base.notes
    r = analyze_tunnel(_rst1(e_mpa=5000))
    assert r.u_max_m < base.u_max_m / 5 and N_ERM not in r.notes
    assert "e_mpa given by the user replaces Erm from Hoek-Carranza-Corkum (2002)" in r.notes
    u = tunnel_uncertainty(_rst1(), {"e_mpa": pb.uniform(100, 5000)}, n=20)
    assert u.outputs["strain_pct"].sd > 0


def test_hb_ignored_inputs_get_notes():
    r = analyze_tunnel(_rst1(a=0.7, mb=9.0, s=0.5))
    assert "parameter 'a' is ignored: it comes from 'gsi', 'mi' and 'd'" in r.notes
    assert "parameters 'mb' and 's' are ignored: they come from 'gsi', 'mi' and 'd'" in r.notes
    assert r.u_max_m == pytest.approx(analyze_tunnel(_rst1()).u_max_m, rel=1e-12)


def test_hb_gsi_100_has_no_jump():
    def run(gsi):
        return analyze_tunnel(TunnelInput(radius_m=6, p0_mpa=1.62, nu=0.3, criterion="HB", sigma_ci_mpa=100, gsi=gsi,
                                          mi=10))
    a, b = run(99.99), run(100)  # a = 0.5 exacto en GSI = 100: antes pedía e_mpa
    assert b.method == "GRC-HB-Carranza-Torres-Fairhurst-2000" and N_ERM in b.notes
    assert b.u_max_m == pytest.approx(a.u_max_m, rel=0.01)


def test_hb_a_half_squeezing_uses_global_strength():
    # σcm global de Hoek (2002) con a = 0.5: 30·(1.7 + 4s − 0.5(1.7 − 8s))·(1.7/4 + s)^−0.5/7.5 = 5.382 MPa;
    # ε = 0.2·(5.382/30)^−2 = 6.214 % (clase D). Con σci·√s salía 51 % (E).
    inp = TunnelInput(radius_m=3.82, p0_mpa=30, nu=0.25, criterion="HB", e_mpa=2500, sigma_ci_mpa=30, mb=1.7,
                      s=3.9e-3)
    sq = analyze_tunnel(inp).squeezing
    assert sq.strain_pct == pytest.approx(6.2138, abs=1e-4) and sq.squeezing_class == "D"


def test_errors_do_not_repeat_values():
    for kw in ({"gsi": 777.7}, {"sigma_ci_mpa": -777.7}, {"d": 777.7}):
        with pytest.raises(ValueError) as e:
            analyze_tunnel(dataclasses.replace(_rst1(), **kw))
        assert "777.7" not in str(e.value) and "Received" not in str(e.value)
    bad = SupportCapacity("ZZSENT", "bolt", psm_mpa=-777.7, eps_sm=0.002)
    with pytest.raises(ValueError) as e:
        analyze_tunnel(_rst1(), supports=[bad], install_distance_m=3)
    assert "ZZSENT" not in str(e.value) and "777.7" not in str(e.value)


def test_phi_90_is_a_value_error():
    with pytest.raises(ValueError, match="phi_deg"):
        analyze_tunnel(TunnelInput(radius_m=3, p0_mpa=10, nu=0.3, criterion="MC", e_mpa=2000, c_mpa=0.5, phi_deg=90))


def test_u_install_exact_and_no_crossing_needs_attention():
    r = analyze_tunnel(_rst1(), supports=[_bolt()], install_distance_m=3, ldp="CHERN1998", combination="rocsupport3")
    # Chern (1998) en X/R = 0.5: (1 + e^(−0.5/1.10))^−1.7 = 0.433649 de u_max
    assert r.u_install_m == pytest.approx(0.0528311, abs=1e-7)
    late = analyze_tunnel(_rst1(), supports=[_bolt()], install_distance_m=1000)
    assert not late.interaction.found and late.interaction.fs is None and late.needs_attention
    assert "support does not intersect the ground reaction curve" in late.warnings


def test_strain_above_100_pct_note():
    r = analyze_tunnel(TunnelInput(radius_m=3, p0_mpa=10, nu=0.3, criterion="MC", e_mpa=100, c_mpa=0.05,
                                   phi_deg=20))
    assert r.strain_pct > 100 and "outside model validity (strain > 100 %)" in r.notes
    assert "outside model validity (strain > 100 %)" not in analyze_tunnel(_rst1()).notes


def test_uncertainty_counts_no_crossing_apart():
    u = tunnel_uncertainty(_rst1(), {"gsi": pb.uniform(14, 16)}, supports=[_bolt()], install_distance_m=400, n=50)
    assert u.support_probabilities == {"fs_below_1": 0.0, "no_crossing": 1.0}


def test_support_diameter_changes_hoek_lining():
    lin = SupportCapacity("L", "lining", hoek_item="Concrete or shotcrete lining 50 mm 28 days 35 MPa")
    kw = dict(supports=[lin], install_distance_m=3)
    a, b = analyze_tunnel(_rst1(), **kw), analyze_tunnel(_rst1(), support_diameter_m=10, **kw)
    assert a.interaction.fs != pytest.approx(b.interaction.fs)


def test_scc_rst1_elastic_then_plateau():
    r = analyze_tunnel(_rst1(), supports=[_bolt()], install_distance_m=3, ldp="CHERN1998", combination="rocsupport3")
    el = _bolt().to_element(12)
    (u0, p0), (u1, p1) = r.scc[0], r.scc[1]
    assert u0 == pytest.approx(r.u_install_m) and p0 == 0
    assert (p1 - p0) / (u1 - u0) == pytest.approx(el.stiffness_mpa / 6)
    assert r.scc[-1][0] == pytest.approx(r.u_max_m) and r.scc[-1][1] == pytest.approx(el.psm_mpa)


def test_scc_weak_support_ends_at_psm_and_empty_without_support():
    weak = SupportCapacity("W", "bolt", psm_mpa=0.01, eps_sm=0.002)
    r = analyze_tunnel(_rst1(), supports=[weak], install_distance_m=3)
    assert r.scc[-1][1] == pytest.approx(0.01)
    assert analyze_tunnel(_rst1()).scc == ()


def test_scc_stiffness_two_elements_kink_at_first_yield():
    weak = SupportCapacity("W", "bolt", psm_mpa=0.01, eps_sm=0.001)
    r = analyze_tunnel(_rst1(), supports=[weak, _bolt()], install_distance_m=3, combination="stiffness")
    k_w, k_b = weak.to_element(12).stiffness_mpa, _bolt().to_element(12).stiffness_mpa
    u_y = r.u_install_m + 6 * 0.01 / k_w
    pts = r.scc
    slope = lambda a, b: (b[1] - a[1]) / (b[0] - a[0])
    assert slope(pts[0], pts[1]) == pytest.approx((k_w + k_b) / 6)
    i = next(j for j, q in enumerate(pts) if q[0] == pytest.approx(u_y))
    assert slope(pts[i], pts[i + 1]) == pytest.approx(k_b / 6)
