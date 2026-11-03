import math

import pytest
from hypothesis import given, settings, strategies as st

import rockmasspy as rm

NAN, INF = float("nan"), float("inf")


def make(h, ff, pp, g, c, phi, **kw):
    i = rm.PlanarInput()
    i.height_m, i.face_dip_deg, i.plane_dip_deg = h, ff, pp
    i.unit_weight, i.cohesion, i.friction_deg = g, c, phi
    for k, v in kw.items():
        setattr(i, k, v)
    return i


def pl1(**kw):
    # RocPlane, problema 1 (Sau Mau Ping), sin grieta y saturado
    return make(60, 50, 35, 0.027, 0.1, 35, **{"water_fill": 1, "water_unit_weight": 0.01, "kh": 0.08, **kw})


def fs(i):
    return rm.planar_fs(i).factor_of_safety


def test_pl1():
    r = rm.planar_fs(pl1())
    assert r.factor_of_safety == pytest.approx(0.818425, abs=1e-6)
    assert r.weight == pytest.approx(28.6278, abs=1e-4)
    assert r.base_area == pytest.approx(104.6068, abs=1e-4)
    assert r.uplift_force == pytest.approx(15.6910, abs=1e-4)
    assert r.formed
    assert r.info.verification == rm.Verification.PrimaryLaterAuthors
    assert "Hoek" in r.info.source


def test_pl2_crack():
    # errata del manual (p. 9): imprime zw 16.6082, U 4.4932, V 0.6280 y c 0.01; no se usan
    k = rm.critical_tension_crack(60, 50, 35)
    assert k.depth_m == pytest.approx(14.00915, abs=1e-5)
    assert k.distance_m == pytest.approx(15.33576, abs=1e-5)
    r = rm.planar_fs(pl1(tension_crack_distance_m=k.distance_m, water_fill=0.9))
    assert r.factor_of_safety == pytest.approx(1.065474, abs=1e-6)
    assert r.uplift_force == pytest.approx(5.0548, abs=1e-4)
    assert r.crack_water_force == pytest.approx(0.7948, abs=1e-4)


def test_pl3_bolt_external():
    i = make(30, 50, 35, 2.79, 7, 30, tension_crack_distance_m=9, water_fill=0.51, water_unit_weight=0.981,
             kh=0.10, external_force=37, external_angle_deg=90)
    assert fs(i) == pytest.approx(1.22233, abs=1e-5)
    i.bolt_force, i.bolt_plunge_deg, i.bolt_mode = 111, 30, rm.BoltMode.Active
    assert fs(i) == pytest.approx(1.50059, abs=1e-5)


def test_pl4_priest():
    r = rm.planar_fs(make(30, 60, 30, 2.5, 2, 30, tension_crack_distance_m=8.660, water_fill=0.25,
                          water_unit_weight=0.981))
    assert r.factor_of_safety == pytest.approx(1.04898, abs=1e-5)
    assert r.tension_crack_depth_m == pytest.approx(15.000, abs=1e-3)


@pytest.mark.parametrize("c,phi,want", [(0, 20, 0.36397), (1.1025, 20, 0.64361), (2.2051, 35, 1.25951)])
def test_watts_west(c, phi, want):
    assert fs(make(95, 85, 45, 0.18192, c, phi)) == pytest.approx(want, abs=1e-5)


def test_rocplane_bolts():
    i = make(33, 65, 55, 0.026, 0, 35)
    assert fs(i) == pytest.approx(0.4903, abs=5e-5)
    i.bolt_force, i.bolt_plunge_deg = 0.1, 25
    assert fs(i) == pytest.approx(0.5190, abs=5e-5)
    i.bolt_mode = rm.BoltMode.Passive
    assert fs(i) == pytest.approx(0.5221, abs=5e-5)


def test_back_analysis():
    b = rm.planar_back_analysis(pl1(), [30, 35, 40])
    assert b.cohesion == pytest.approx([0.139329, 0.131758, 0.123200], abs=1e-6)
    assert b.friction_at_zero_cohesion_deg == pytest.approx(70.5924, abs=1e-4)
    i = pl1()
    i.cohesion = b.cohesion[1]
    assert fs(i) == pytest.approx(1.0, abs=1e-9)
    none = rm.planar_back_analysis(pl1(), [75, 80])
    assert list(none.cohesion) == [] and none.notes
    with pytest.raises(ValueError, match="friction_deg"):
        rm.planar_back_analysis(pl1(), [])
    with pytest.raises(ValueError):
        rm.planar_back_analysis(make(60, 50, 50, 0.027, 0, 0), [30])


@pytest.mark.parametrize("pp", [50.0, 50.0 - 1e-12])
def test_not_formed(pp):
    i = pl1()
    i.plane_dip_deg = pp
    r = rm.planar_fs(i)
    assert not r.formed and r.factor_of_safety is None and list(r.warnings) == []
    assert list(r.notes) == ["planar block not formed: the plane does not daylight in the face"]


def test_crack_at_limit():
    i = make(60, 50, 35, 0.027, 0.1, 35)
    bmax = 60 * (1 / math.tan(math.radians(35)) - 1 / math.tan(math.radians(50)))
    i.tension_crack_distance_m = bmax
    assert rm.planar_fs(i).tension_crack_depth_m == pytest.approx(0.0, abs=1e-9)
    i.tension_crack_distance_m = bmax + 1e-6
    with pytest.raises(ValueError, match="tension_crack_distance_m") as e:
        rm.planar_fs(i)
    assert "Received" not in str(e.value)
    i.tension_crack_distance_m = None
    assert i.tension_crack_distance_m is None and fs(i) is not None


def test_negative_normal_and_no_driving():
    i = pl1()
    i.water_unit_weight = 0.1
    r = rm.planar_fs(i)
    assert list(r.warnings) == ["effective normal force on the plane is negative: friction taken as zero"]
    assert r.factor_of_safety == pytest.approx(0.1 * r.base_area / r.driving_force, abs=1e-12)
    j = make(60, 50, 35, 0.027, 0.1, 35, bolt_force=1000)
    s = rm.planar_fs(j)
    assert s.factor_of_safety == INF and list(s.notes) == ["no driving force on the block"]


BAD = [
    ("height_m", 0), ("face_dip_deg", 0), ("face_dip_deg", 95), ("plane_dip_deg", 0), ("plane_dip_deg", 90),
    ("friction_deg", 90), ("water_fill", 1.5), ("kh", -0.1), ("bolt_plunge_deg", 95), ("external_angle_deg", 200),
    ("bolt_force", -1), ("external_force", -1), ("cohesion", -1), ("unit_weight", 0),
] + [(n, v) for n in ("height_m", "face_dip_deg", "plane_dip_deg", "unit_weight", "cohesion", "friction_deg",
                      "tension_crack_distance_m", "water_fill", "water_unit_weight", "kh", "bolt_force",
                      "bolt_plunge_deg", "external_force", "external_angle_deg") for v in (NAN, INF)]


@pytest.mark.parametrize("name,value", BAD)
def test_rejects(name, value):
    i = pl1()
    setattr(i, name, value)
    with pytest.raises(ValueError, match=name):
        rm.planar_fs(i)


def test_water_requires_unit_weight():
    i = make(60, 50, 35, 0.027, 0.1, 35, water_fill=0.5)
    with pytest.raises(ValueError, match="water_unit_weight"):
        rm.planar_fs(i)


def test_crack_requires_daylight():
    with pytest.raises(ValueError, match="plane_dip_deg"):
        rm.critical_tension_crack(60, 35, 35)


def _base(c, phi, f, kh):
    return make(40, 60, 30, 0.026, c, phi, tension_crack_distance_m=5, water_fill=f, water_unit_weight=0.01, kh=kh)


@settings(max_examples=60, deadline=None)
@given(c=st.floats(0, 0.2), phi=st.floats(10, 45), f=st.floats(0, 1), kh=st.floats(0, 0.2),
       dc=st.floats(0.001, 0.1), dp=st.floats(0.5, 10), df=st.floats(0.01, 0.5), dk=st.floats(0.001, 0.1))
def test_monotonic(c, phi, f, kh, dc, dp, df, dk):
    base = rm.planar_fs(_base(c, phi, f, kh))
    assume_ok = base.normal_force > 0
    assert fs(_base(c + dc, phi, f, kh)) >= fs(_base(c, phi, f, kh)) - 1e-12
    if assume_ok:
        assert fs(_base(c, phi + dp, f, kh)) >= fs(_base(c, phi, f, kh)) - 1e-12
    assert fs(_base(c, phi, min(f + df, 1), kh)) <= fs(_base(c, phi, f, kh)) + 1e-12
    assert fs(_base(c, phi, f, kh + dk)) <= fs(_base(c, phi, f, kh)) + 1e-12


@settings(max_examples=60, deadline=None)
@given(k=st.floats(0.01, 100), t=st.floats(0, 0.5), e=st.floats(0, 0.5))
def test_scale_invariance(k, t, e):
    def build(s):
        return make(40, 60, 30, 0.026 * s, 0.02 * s, 30, tension_crack_distance_m=5, water_fill=0.5,
                    water_unit_weight=0.01 * s, kh=0.05, bolt_force=t * s, bolt_plunge_deg=20,
                    external_force=e * s, external_angle_deg=60)
    assert fs(build(k)) == pytest.approx(fs(build(1)), rel=1e-9)


@settings(max_examples=80, deadline=None)
@given(t=st.floats(0.001, 0.05), plunge=st.floats(-20, 30), phi=st.floats(20, 40))
def test_active_ge_passive_iff_passive_ge_one(t, plunge, phi):
    def build(mode):
        return make(40, 60, 35, 0.026, 0.01, phi, bolt_force=t, bolt_plunge_deg=plunge, bolt_mode=mode)
    act, pas = rm.planar_fs(build(rm.BoltMode.Active)), rm.planar_fs(build(rm.BoltMode.Passive))
    if act.factor_of_safety == INF or act.factor_of_safety is None:
        return
    # solo con la componente del perno a lo largo del plano a favor (cos(psi_p + theta) > 0) y D - Tc > 0
    if math.cos(math.radians(35 + plunge)) <= 0 or act.driving_force <= 1e-9:
        return
    margin = pas.factor_of_safety - 1
    if abs(margin) < 1e-9:
        return
    assert (act.factor_of_safety >= pas.factor_of_safety) == (margin >= 0)
