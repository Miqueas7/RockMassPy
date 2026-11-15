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
