import pytest

import rockmasspy as rm
from rockmasspy.excavation import TunnelInput, analyze_tunnel
from rockmasspy.external import ExternalRecord, ExternalSet, compare_monitoring, lining_forces
from rockmasspy.support_capacity import SupportCapacity, hoek_psm


def _conv(oid, v, stage=None):
    return ExternalRecord(oid, "convergence_pct", v, "%", stage=stage)


def test_ratio_without_warning():
    c, = compare_monitoring(ExternalSet((_conv("C1", 1.2),)), ExternalSet((_conv("C1", 1.0),)))
    assert c.measured == 1.2 and c.modeled == 1.0 and c.ratio == pytest.approx(1.2) and c.warning is None


def test_ratio_warning_without_values():
    c, = compare_monitoring(ExternalSet((_conv("C1", 1.6),)), ExternalSet((_conv("C1", 1.0),)))
    assert c.warning == "measured exceeds model by more than 50 %"


def test_against_tunnel_result():
    inp = TunnelInput(radius_m=6, p0_mpa=1.62, nu=0.3, criterion="HB", sigma_ci_mpa=7, gsi=15, mi=10, d=0.0)
    bolt = SupportCapacity("B34", "bolt", psm_mpa=hoek_psm("34 mm rockbolt", spacing_m=1.0), eps_sm=0.002)
    r = analyze_tunnel(inp, supports=[bolt], install_distance_m=3, ldp="CHERN1998", combination="rocsupport3")
    c, = compare_monitoring(ExternalSet((_conv("T1", 1.0),)), {"T1": r})
    assert c.modeled == pytest.approx(0.989, abs=0.001) and c.ratio == pytest.approx(1.0 / c.modeled)
    free = analyze_tunnel(inp)  # sin cruce: strain_pct
    c, = compare_monitoring(ExternalSet((_conv("T1", 1.0),)), {"T1": free})
    assert c.modeled == pytest.approx(free.strain_pct)


def test_no_model_for_some():
    out = compare_monitoring(ExternalSet((_conv("C1", 1.0), _conv("SENT", 1.0))), ExternalSet((_conv("C1", 1.0),)))
    miss = [c for c in out if c.modeled is None]
    assert len(out) == 2 and len(miss) == 1 and miss[0].ratio is None
    assert miss[0].note == "no model for some measurements" and "SENT" not in miss[0].note


def _f(oid, stage, q, v):
    return ExternalRecord(oid, q, v, stage=stage)


def test_lining_forces_and_capacity():
    recs = []
    for st, n, m in (("1", 0.5, 0.01), ("2", 1.0, 0.05), ("3", 40.0, 0.5)):
        recs += [_f("L1", st, "axial_force_mn", n), _f("L1", st, "moment_mnm", m)]
    recs += [_f("L2", "1", "axial_force_mn", 9.0), _f("L2", "1", "moment_mnm", 0.1)]
    fs = lining_forces(ExternalSet(tuple(recs)), object_id="L1")
    assert len(fs) == 3 and fs[1].n_mn == 1.0 and fs[1].m_mnm == 0.05
    s = rm.LiningSection()
    s.area_m2, s.inertia_m4, s.thickness_m, s.sigma_c_mpa, s.sigma_t_mpa = 0.12, 0.0004, 0.2, 40, -5
    assert rm.check_capacity(s, fs, 1).outside == [2]
    assert len(lining_forces(ExternalSet(tuple(recs)))) == 4


def test_moment_without_axial():
    with pytest.raises(ValueError, match="axial_force_mn") as e:
        lining_forces(ExternalSet((_f("SENT", "1", "moment_mnm", 0.1),)))
    assert "SENT" not in str(e.value)


def test_axial_without_moment_and_missing_shear_note():
    with pytest.raises(ValueError, match="moment_mnm") as e:
        lining_forces(ExternalSet((_f("SENT", "1", "axial_force_mn", 1.0),)))
    assert "SENT" not in str(e.value)
    recs = ExternalSet((_f("L", "1", "axial_force_mn", 1.0), _f("L", "1", "moment_mnm", 0.1),
                        _f("L", "2", "axial_force_mn", 1.0), _f("L", "2", "moment_mnm", 0.1)))
    notes = []
    assert len(lining_forces(recs, notes=notes)) == 2 and notes == ["shear force absent; assumed 0"]
