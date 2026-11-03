import math

import pytest
from hypothesis import given, settings, strategies as st

import rockmasspy as rm

NAN, INF = float("nan"), float("inf")


def joint(dd, dip, c, phi, u=0.0):
    j = rm.WedgeJoint()
    j.plane, j.cohesion, j.friction_deg, j.water_pressure = rm.PlaneOrientation(dd, dip), c, phi, u
    return j


def make(j1, j2, face, upper, h, g, **kw):
    i = rm.WedgeInput()
    i.joint1, i.joint2 = j1, j2
    i.face, i.upper = rm.PlaneOrientation(*face), rm.PlaneOrientation(*upper)
    i.height_m, i.unit_weight = h, g
    for k, v in kw.items():
        setattr(i, k, v)
    return i


def cu2(**kw):
    # SWedge, problema 6 (Priest ej. 1), MN y m
    return make(joint(203, 47, 0.010, 40, 0.005), joint(287, 52, 0.020, 35, 0.015), (230, 60), (225, 5), 6.7978, 0.026,
                external_force=0.18, external_direction=rm.LineOrientation(168, 70), **kw)


def cu3():
    return make(joint(65, 74, 0.015, 32, 0.025), joint(186, 41, 0.005, 40, 0.015), (134, 65), (122, 11), 6.8471, 0.025)


def dry(a, b, phi1, phi2, face, upper=(180, 0), **kw):
    return make(joint(a[0], a[1], 0, phi1), joint(b[0], b[1], 0, phi2), face, upper, 10, 0.026, **kw)


def fs(i):
    return rm.wedge_fs(i).factor_of_safety


def test_cu2():
    r = rm.wedge_fs(cu2())
    assert r.factor_of_safety == pytest.approx(1.4966, abs=1e-4)
    assert r.mode == rm.WedgeMode.TwoPlanes
    for name, want in [("volume", 45.201), ("weight", 1.175), ("area1", 41.147), ("area2", 20.428),
                       ("face_area", 38.955), ("upper_area", 21.242), ("normal1", 0.407), ("normal2", 0.251),
                       ("driving_force", 0.893), ("resisting_force", 1.337)]:
        assert getattr(r, name) == pytest.approx(want, abs=1e-3), name
    assert r.intersection.trend_deg == pytest.approx(239.4, abs=0.1)
    assert r.intersection.plunge_deg == pytest.approx(40.8, abs=0.1)
    assert r.info.verification == rm.Verification.Secondary
    assert r.warnings == []


def test_cu3_one_plane_and_swapped_joints():
    r = rm.wedge_fs(cu3())
    assert r.factor_of_safety == pytest.approx(0.8493, abs=1e-4)
    assert r.mode == rm.WedgeMode.PlaneTwo
    assert r.normal2 == pytest.approx(0.793, abs=1e-3)
    assert r.driving_force == pytest.approx(1.117, abs=1e-3)
    assert r.resisting_force == pytest.approx(0.949, abs=1e-3)
    assert r.volume == pytest.approx(81.741, abs=1e-3)
    i = cu3()
    i.joint1, i.joint2 = cu3().joint2, cu3().joint1
    s = rm.wedge_fs(i)
    assert s.mode == rm.WedgeMode.PlaneOne
    assert s.factor_of_safety == pytest.approx(r.factor_of_safety, abs=1e-12)


def test_kumsar_and_swedge_problems():
    assert fs(dry((195, 45), (105, 70), 30, 30, (160, 70))) == pytest.approx(0.7123, abs=1e-4)
    c4 = dry((33.5, 75), (248, 75), 40.8, 40.8, (337.5, 75))
    assert fs(c4) == pytest.approx(2.0203, abs=1e-4)
    c4.kh = 0.3303
    assert fs(c4) == pytest.approx(0.9872, abs=1e-4)
    p2 = dry((119, 50), (241, 50), 35, 35, (180, 70))
    assert fs(p2) == pytest.approx(1.6325, abs=1e-4)
    p2.kh = 0.2365
    assert fs(p2) == pytest.approx(1.0001, abs=5e-4)


@pytest.mark.parametrize("dip,phi,plunge", [(42.7, 33, 35.645), (45, 35, 37.852), (47.5, 37, 40.301)])
def test_kovari_fritz(dip, phi, plunge):
    r = rm.wedge_fs(dry((141, dip), (219, dip), phi, phi, (180, 70)))
    assert r.intersection.plunge_deg == pytest.approx(plunge, abs=2e-3)
    assert r.factor_of_safety == pytest.approx(1.0, abs=0.01)


def _up(dd, dip):  # normal que mira hacia dentro de la cuña (hacia arriba)
    t, d = math.radians(dd + 180), math.radians(dip)
    return (math.sin(d) * math.cos(t), math.sin(d) * math.sin(t), -math.cos(d))


@settings(max_examples=60, deadline=None)
@given(st.floats(35, 70), st.floats(20, 70))
def test_symmetric_dry_cohesionless(dip, delta):
    r = rm.wedge_fs(dry((180 - delta, dip), (180 + delta, dip), 30, 30, (180, 75)))
    ua, ub = _up(180 - delta, dip), _up(180 + delta, dip)
    theta = math.degrees(math.acos(sum(x * y for x, y in zip(ua, ub))))
    xi = math.radians((180 - theta) / 2)
    tpsi = math.tan(math.radians(r.intersection.plunge_deg))
    assert r.factor_of_safety == pytest.approx(math.tan(math.radians(30)) / (tpsi * math.sin(xi)), abs=1e-9)


@pytest.mark.parametrize("face", [(185, 60), (170, 75), (185, 80)])
def test_cu1_hoek(face):
    v = fs(dry((105, 40), (235, 70), 20, 30, face, (185, 0)))
    assert v == pytest.approx(1.1935, abs=1e-4)
    assert abs(v - 1.18) / 1.18 < 0.03


def test_vertical_joint_both_senses_and_horizontal_joint():
    a = rm.wedge_fs(make(joint(110, 90, 0.01, 30), joint(230, 50, 0.01, 30), (180, 70), (180, 0), 10, 0.026))
    b = rm.wedge_fs(make(joint(290, 90, 0.01, 30), joint(230, 50, 0.01, 30), (180, 70), (180, 0), 10, 0.026))
    assert a.factor_of_safety == pytest.approx(b.factor_of_safety, abs=1e-12)
    assert a.mode == b.mode != rm.WedgeMode.NotFormed
    for dd in (0, 180):
        r = rm.wedge_fs(make(joint(dd, 0, 0, 30), joint(150, 60, 0, 30), (180, 70), (180, 0), 10, 0.026))
        assert r.mode == rm.WedgeMode.NotFormed and r.factor_of_safety is None
        assert r.notes == ["wedge not formed: the intersection does not outcrop on the upper slope"]


@settings(max_examples=40, deadline=None)
@given(st.floats(0, 360))
def test_rotation_invariance(rot):
    base = cu2()
    f0, m0 = fs(base), rm.wedge_fs(base).mode
    i = cu2()
    for p in ("joint1", "joint2"):
        pl = getattr(i, p).plane
        getattr(i, p).plane = rm.PlaneOrientation((pl.dip_direction_deg + rot) % 360, pl.dip_deg)
    i.face = rm.PlaneOrientation((i.face.dip_direction_deg + rot) % 360, i.face.dip_deg)
    i.upper = rm.PlaneOrientation((i.upper.dip_direction_deg + rot) % 360, i.upper.dip_deg)
    i.external_direction = rm.LineOrientation((i.external_direction.trend_deg + rot) % 360, i.external_direction.plunge_deg)
    r = rm.wedge_fs(i)
    assert r.mode == m0
    assert r.factor_of_safety == pytest.approx(f0, rel=1e-9)


def test_limit_normal_zero_gives_the_lower_mode():
    base = cu2()
    base.joint1.water_pressure = 0.0
    base.joint2.water_pressure = 0.0
    d0 = rm.wedge_fs(base)
    u = d0.normal1 / d0.area1
    vals = []
    for f in (1 - 1e-12, 1 + 1e-12):
        i = cu2()
        i.joint1.water_pressure, i.joint2.water_pressure = u * f, 0.0
        vals.append(fs(i))
    assert vals[0] == pytest.approx(vals[1], abs=1e-9)
    mid = []
    for f in (1 - 1e-4, 1 + 1e-4):
        i = cu2()
        i.joint1.water_pressure, i.joint2.water_pressure = u * f, 0.0
        mid.append(rm.wedge_fs(i))
    assert [m.mode for m in mid] == [rm.WedgeMode.TwoPlanes, rm.WedgeMode.PlaneTwo]
    assert vals[0] <= min(m.factor_of_safety for m in mid) + 1e-3


def test_not_formed_cases():
    i = cu2(); i.face = rm.PlaneOrientation(50, 60)
    j = cu2(); j.face = rm.PlaneOrientation(230, 30)
    k = cu2(); k.joint1.plane = rm.PlaneOrientation(230, 60)
    for w in (i, j, k):
        r = rm.wedge_fs(w)
        assert r.mode == rm.WedgeMode.NotFormed and r.factor_of_safety is None
        assert r.notes == ["wedge not formed: the intersection does not daylight in the face"]
        assert r.warnings == []
    for a, b in [((203, 47), (203, 47)), ((110, 90), (290, 90))]:
        r = rm.wedge_fs(make(joint(*a, 0, 30), joint(*b, 0, 30), (230, 60), (225, 5), 6, 0.026))
        assert r.mode == rm.WedgeMode.NotFormed and r.factor_of_safety is None
        assert r.notes == ["wedge not formed: parallel joints"] and r.warnings == []
    assert rm.wedge_fs(make(joint(141, 45, 0, 30), joint(219, 45, 0, 30), (180, 70), (180, 38), 10, 0.026)).notes == [
        "wedge not formed: the intersection does not outcrop on the upper slope"]


def test_lifting():
    i = cu2()
    i.joint1.water_pressure = 0.05
    i.joint2.water_pressure = 0.05
    r = rm.wedge_fs(i)
    assert r.mode == rm.WedgeMode.Lifting and r.factor_of_safety == 0.0
    assert r.warnings == ["wedge lifts off both joints"]


def test_infinite_fs_has_a_note():
    i = dry((141, 45), (219, 45), 35, 35, (180, 70))
    r0 = rm.wedge_fs(i)
    i.external_force = r0.weight * math.tan(math.radians(r0.intersection.plunge_deg))
    i.external_direction = rm.LineOrientation(0, 0)
    r = rm.wedge_fs(i)
    assert r.factor_of_safety == INF and r.notes and r.warnings == []


@pytest.mark.parametrize("path,value,name", [
    ("joint1.plane", rm.PlaneOrientation(NAN, 47), "joint1.plane.dip_direction_deg"),
    ("joint2.plane", rm.PlaneOrientation(287, NAN), "joint2.plane.dip_deg"),
    ("joint1.plane", rm.PlaneOrientation(203, 95), "joint1.plane.dip_deg"),
    ("face", rm.PlaneOrientation(230, NAN), "face.dip_deg"),
    ("upper", rm.PlaneOrientation(NAN, 5), "upper.dip_direction_deg"),
    ("joint1.cohesion", NAN, "joint1.cohesion"),
    ("joint2.cohesion", -1.0, "joint2.cohesion"),
    ("joint1.friction_deg", NAN, "joint1.friction_deg"),
    ("joint2.friction_deg", 90.0, "joint2.friction_deg"),
    ("joint1.water_pressure", NAN, "joint1.water_pressure"),
    ("joint2.water_pressure", -0.1, "joint2.water_pressure"),
    ("height_m", NAN, "height_m"), ("height_m", 0.0, "height_m"),
    ("unit_weight", NAN, "unit_weight"), ("unit_weight", 0.0, "unit_weight"),
    ("kh", NAN, "kh"), ("kh", -0.1, "kh"), ("kh", INF, "kh"),
    ("external_force", NAN, "external_force"), ("external_force", -1.0, "external_force"),
    ("external_direction", rm.LineOrientation(NAN, 70), "external_direction.trend_deg"),
    ("external_direction", rm.LineOrientation(168, INF), "external_direction.plunge_deg"),
])
def test_validation_names_the_field(path, value, name):
    i = cu2()
    obj = i
    parts = path.split(".")
    for p in parts[:-1]:
        obj = getattr(obj, p)
    setattr(obj, parts[-1], value)
    with pytest.raises(ValueError) as e:
        rm.wedge_fs(i)
    assert name in str(e.value)


def test_unset_fields_raise_by_name():
    with pytest.raises(ValueError, match="joint1.plane.dip_direction_deg"):
        rm.wedge_fs(rm.WedgeInput())
