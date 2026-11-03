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
    nb = rm.planar_back_analysis(make(60, 50, 50, 0.027, 0, 0), [30])
    assert list(nb.cohesion) == [] and nb.friction_at_zero_cohesion_deg is None and "not formed" in nb.notes[0]


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


def test_water_unit_weight_optional():
    i = make(60, 50, 35, 0.027, 0.1, 35)
    assert i.water_unit_weight is None and fs(i) is not None  # None con fill 0 se acepta
    i.water_unit_weight = NAN
    with pytest.raises(ValueError, match="water_unit_weight"):  # NaN explícito lanza aun con fill 0
        rm.planar_fs(i)
    i.water_unit_weight = None
    i.water_fill = 0.5
    with pytest.raises(ValueError, match="water_unit_weight"):
        rm.planar_fs(i)


def test_degenerate_block():
    i = make(30, 90, 60, 0.026, 0.1, 30, tension_crack_distance_m=0)
    r = rm.planar_fs(i)
    assert not r.formed and r.factor_of_safety is None and list(r.warnings) == []
    assert "no volume" in r.notes[0]
    b = rm.planar_back_analysis(i, [30])
    assert list(b.cohesion) == [] and "no volume" in b.notes[0]


def test_back_analysis_negative_normal():
    b = rm.planar_back_analysis(pl1(water_unit_weight=0.1), [20, 40])
    assert b.cohesion[0] == b.cohesion[1] and b.friction_at_zero_cohesion_deg is None
    assert list(b.notes) == ["normal force on the sliding plane is negative; c does not depend on friction"]


def test_crack_requires_daylight():
    with pytest.raises(ValueError, match="plane_dip_deg"):
        rm.critical_tension_crack(60, 35, 35)


@st.composite
def geom(draw):
    """Altura, cara y plano válidos (plano bajo la cara) y una grieta b dentro de [0, bmax]."""
    h = draw(st.floats(5, 200))
    ff = draw(st.floats(40, 90))
    pp = draw(st.floats(20, 85).filter(lambda x: x < ff - 5))
    cot = lambda d: 1 / math.tan(math.radians(d))
    bmax = h * (cot(pp) - cot(ff))
    b = draw(st.one_of(st.none(), st.floats(0.05, 0.95).map(lambda t: t * bmax)))
    return h, ff, pp, b


def _base(g, c, phi, f, kh):
    h, ff, pp, b = g
    return make(h, ff, pp, 0.026, c, phi, tension_crack_distance_m=b, water_fill=f, water_unit_weight=0.01, kh=kh)


@settings(max_examples=80, deadline=None)
@given(g=geom(), c=st.floats(0, 0.2), phi=st.floats(10, 45), f=st.floats(0, 1), kh=st.floats(0, 0.2),
       dc=st.floats(0.001, 0.1), dp=st.floats(0.5, 10), df=st.floats(0.01, 0.5), dk=st.floats(0.001, 0.1))
def test_monotonic(g, c, phi, f, kh, dc, dp, df, dk):
    base = rm.planar_fs(_base(g, c, phi, f, kh))
    assert base.formed
    v = base.factor_of_safety
    assert fs(_base(g, c + dc, phi, f, kh)) >= v - 1e-9
    if base.normal_force > 0:
        assert fs(_base(g, c, phi + dp, f, kh)) >= v - 1e-9
    assert fs(_base(g, c, phi, min(f + df, 1), kh)) <= v + 1e-9
    assert fs(_base(g, c, phi, f, kh + dk)) <= v + 1e-9


@settings(max_examples=80, deadline=None)
@given(g=geom(), k=st.floats(0.01, 100), t=st.floats(0, 0.5), e=st.floats(0, 0.5))
def test_scale_invariance(g, k, t, e):
    h, ff, pp, b = g

    def build(s):
        return make(h, ff, pp, 0.026 * s, 0.02 * s, 30, tension_crack_distance_m=b, water_fill=0.5,
                    water_unit_weight=0.01 * s, kh=0.05, bolt_force=t * s, bolt_plunge_deg=20,
                    external_force=e * s, external_angle_deg=60)
    assert fs(build(k)) == pytest.approx(fs(build(1)), rel=1e-9)


@settings(max_examples=100, deadline=None)
@given(g=geom(), t=st.floats(0.001, 0.05), plunge=st.floats(-20, 30), phi=st.floats(20, 40))
def test_active_ge_passive_iff_passive_ge_one(g, t, plunge, phi):
    h, ff, pp, b = g

    def build(mode):
        return make(h, ff, pp, 0.026, 0.01, phi, tension_crack_distance_m=b, bolt_force=t, bolt_plunge_deg=plunge,
                    bolt_mode=mode)
    act, pas = rm.planar_fs(build(rm.BoltMode.Active)), rm.planar_fs(build(rm.BoltMode.Passive))
    # la identidad vale con cos(psi_p + theta) > 0, D - Tc > 0 y la misma normal en los dos modos
    if math.cos(math.radians(pp + plunge)) <= 1e-9 or act.driving_force <= 1e-9 or act.factor_of_safety == INF:
        return
    margin = pas.factor_of_safety - 1
    if abs(margin) < 1e-9:
        return
    assert (act.factor_of_safety >= pas.factor_of_safety) == (margin >= 0)
