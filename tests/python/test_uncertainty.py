import pytest

import rockmasspy as rm
from rockmasspy import probabilistic as pb
from rockmasspy.uncertainty import classification_uncertainty as cu

CAT = rm.SupportCatalog([rm.SupportType("I", 1), rm.SupportType("II", 2)])


def lab(method, edition, cuts):
    cls = [rm.RangeClass(cuts[0], cuts[1], "B", "II"), rm.RangeClass(cuts[1], cuts[2], "A", "I")]
    return rm.LaborTable("galeria", CAT, rm.RangeTable(method, edition, cls))


def q_base(**kw):
    d = dict(rqd_pct=65, jn=12, jr=1.5, ja=2, jw=1, srf=1)
    d.update(kw)
    return rm.QInput(**d)


def rmr_base(**kw):
    i = rm.Rmr89Input()
    i.functions = rm.RmrFunctions.Continuous
    i.ucs_mpa, i.rqd_pct, i.spacing_m, i.joint_condition_rating = 90.0, 70.0, 0.3, 20.0
    i.water = rm.Water.Dry
    for k, v in kw.items():
        setattr(i, k, v)
    return i


def test_q_class_probability():
    var = {"jn": pb.uniform(9, 15)}
    t = lab("Q", "Q-NGI-2025", (0, 4, 1000))
    r = cu("Q", q_base(), var, table=t, n=2000)
    jn = pb.sample(var, 2000)["jn"]
    expect = sum(x <= 12.1875 for x in jn) / 2000
    assert r.class_probabilities["A"] == pytest.approx(expect)
    assert 0.4 < expect < 0.6
    assert sum(r.class_probabilities.values()) == pytest.approx(1)
    assert sum(r.support_probabilities.values()) == pytest.approx(1)
    assert r.info.method_id == "Uncertainty-MC-LHS"


def test_rmr_continuous_reproducible_and_samplings():
    var = {"ucs_mpa": pb.normal(90, 15, 30, 150)}
    a = cu("RMR89", rmr_base(), var, n=5000)
    assert a == cu("RMR89", rmr_base(), var, n=5000)
    o = a.outputs["rmr"]
    assert o.p05 < o.p50 < o.p95
    b = cu("RMR89", rmr_base(), var, n=5000, sampling="monte_carlo")
    assert abs(o.mean - b.outputs["rmr"].mean) < 0.5


def test_gsi_hb_and_near_boundary():
    r = cu("HB", {"gsi": 50, "mi": 10, "d": 0}, {"gsi": pb.uniform(40, 60)}, n=200)
    assert set(r.outputs) == {"mb", "s", "a"}
    t = lab("GSI", "GSI-2013", (0, 50, 100))
    g = cu("GSI", {"jcond89": 15, "rqd_pct": 70}, {"rqd_pct": pb.uniform(60, 80)}, table=t, n=200)
    assert g.n_valid == 200 and "gsi" in g.outputs


def test_near_boundary_warning():
    t = lab("Q", "Q-NGI-2025", (0, 4, 1000))
    r = cu("Q", q_base(), {"jn": pb.uniform(11, 13)}, table=t, n=100)
    assert any(w.startswith("near the boundary between classes B and A (") for w in r.warnings)


def test_errors():
    q = q_base()
    with pytest.raises(ValueError, match=r"'zz'.*allowed: rqd_pct, jn"):
        cu("Q", q, {"zz": pb.uniform(1, 2)})
    with pytest.raises(ValueError, match="is50_mpa"):
        cu("RMR89", rmr_base(), {"is50_mpa": pb.uniform(2, 4)})
    with pytest.raises(ValueError):
        cu("HB", {"gsi": 50, "mi": 10, "d": 0}, {"gsi": pb.uniform(40, 60)}, table=lab("GSI", "GSI-2013", (0, 50, 100)))
    with pytest.raises(ValueError):
        cu("Q", q, {"jn": pb.uniform(9, 15)}, table=lab("RMR", "RMR89", (0, 40, 100)))
    with pytest.raises(ValueError, match="rqd_pct.*narrow its minimum and maximum") as e:
        cu("RMR89", rmr_base(), {"rqd_pct": pb.uniform(80, 120)}, n=100)
    assert "120" not in str(e.value)


def test_no_input_values_in_errors():
    with pytest.raises(ValueError) as e:
        cu("RMR89", rmr_base(rqd_pct=777.7), {"rqd_pct": pb.uniform(80, 120)}, n=100)
    assert "777.7" not in str(e.value)
    with pytest.raises(ValueError) as e:
        cu("Q", q_base(rqd_pct=777.7), {"jn": pb.uniform(-1, 1)}, n=100)
    assert "777.7" not in str(e.value)
