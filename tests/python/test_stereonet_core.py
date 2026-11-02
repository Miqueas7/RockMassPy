import math

import pytest
from hypothesis import given, strategies as st

import rockmasspy as rm

EA, EQ = rm.Projection.EqualAngle, rm.Projection.EqualArea


def adiff(a, b):
    d = abs((a - b) % 360.0)
    return 360.0 - d if d > 180 else d


def near_line(line, trend, plunge, tol=1.0):
    assert line is not None
    assert adiff(line.trend_deg, trend) <= tol
    assert line.plunge_deg == pytest.approx(plunge, abs=tol)


def test_polo_y_plano():
    p = rm.pole_of(rm.PlaneOrientation(180, 60))
    assert (p.trend_deg, p.plunge_deg) == pytest.approx((0, 30))
    p = rm.pole_of(rm.PlaneOrientation(350, 20))
    assert (p.trend_deg, p.plunge_deg) == pytest.approx((170, 70))
    q = rm.plane_of(rm.pole_of(rm.PlaneOrientation(360, 30)))  # 360 se guarda como 0
    assert (q.dip_direction_deg, q.dip_deg) == pytest.approx((0, 30))


@given(dd=st.floats(0, 360), dip=st.floats(0, 90))
def test_ida_y_vuelta(dd, dip):
    q = rm.plane_of(rm.pole_of(rm.PlaneOrientation(dd, dip)))
    assert adiff(q.dip_direction_deg, dd) < 1e-9
    assert q.dip_deg == pytest.approx(dip, abs=1e-9)


def test_proyecciones():
    assert rm.project(rm.LineOrientation(0, 45), EA).y == pytest.approx(0.41421356, abs=1e-8)
    assert rm.project(rm.LineOrientation(0, 45), EQ).y == pytest.approx(0.54119610, abs=1e-8)
    for p in (EA, EQ):
        c = rm.project(rm.LineOrientation(70, 90), p)
        assert (c.x, c.y) == pytest.approx((0, 0), abs=1e-12)
        e = rm.project(rm.LineOrientation(90, 0), p)
        assert (e.x, e.y) == pytest.approx((1, 0), abs=1e-12)
    with pytest.raises(ValueError):
        rm.unproject(rm.Point2(1.0, 0.1), EQ)


@given(t=st.floats(0, 360), pl=st.floats(0, 89.9), proj=st.sampled_from([EA, EQ]))
def test_proyeccion_ida_y_vuelta(t, pl, proj):
    pt = rm.project(rm.LineOrientation(t, pl), proj)
    if proj == EQ:
        assert math.hypot(pt.x, pt.y) <= 1 + 1e-12
    if proj == EA:  # equiangular: r puede pasar de 1 solo con inmersión negativa; aquí r <= 1
        assert math.hypot(pt.x, pt.y) <= 1 + 1e-12
    back = rm.unproject(pt, proj)
    assert back.plunge_deg == pytest.approx(pl, abs=1e-6)
    if pl < 89:
        assert adiff(back.trend_deg, t) < 1e-6


def test_caso_publicado_riquelme_tabla4():
    P = rm.PlaneOrientation
    f1, f2, f3, f4 = P(325, 87), P(119, 20), P(234, 83), P(62, 62)
    near_line(rm.plane_intersection(f1, f2), 55, 9)
    near_line(rm.plane_intersection(f1, f4), 49, 61)
    near_line(rm.plane_intersection(f2, f3), 146, 18)
    near_line(rm.plane_intersection(f2, f4), 142, 19)
    near_line(rm.plane_intersection(f3, f4), 145, 12)
    s1, s2, s3, s4 = P(323, 89), P(135, 26), P(250, 76), P(41, 57)
    near_line(rm.plane_intersection(s1, s2), 53, 4)
    near_line(rm.plane_intersection(s1, s4), 51, 57)
    near_line(rm.plane_intersection(s2, s3), 166, 23)
    near_line(rm.plane_intersection(s2, s4), 114, 24)


@given(d1=st.floats(0, 360), p1=st.floats(1, 89), d2=st.floats(0, 360), p2=st.floats(1, 89))
def test_interseccion_propiedades(d1, p1, d2, p2):
    a, b = rm.PlaneOrientation(d1, p1), rm.PlaneOrientation(d2, p2)
    ab, ba = rm.plane_intersection(a, b), rm.plane_intersection(b, a)
    assert (ab is None) == (ba is None)
    if ab is not None:
        assert rm.angle_between(rm.pole_of(a), ab) == pytest.approx(90, abs=1e-6)
        assert rm.angle_between(rm.pole_of(b), ab) == pytest.approx(90, abs=1e-6)
        assert rm.angle_between(ab, ba) < 1e-6


def test_paralelos():
    a = rm.PlaneOrientation(10, 90)
    assert rm.plane_intersection(a, a) is None
    assert rm.plane_intersection(a, rm.PlaneOrientation(190, 90)) is None


def test_bordes():
    assert rm.angle_between(rm.pole_of(rm.PlaneOrientation(90, 90)), rm.pole_of(rm.PlaneOrientation(270, 90))) \
        == pytest.approx(0, abs=1e-9)
    g = rm.great_circle(rm.PlaneOrientation(40, 0), EA, 11)
    assert all(math.hypot(p.x, p.y) == pytest.approx(1, abs=1e-9) for p in g)
    g = rm.great_circle(rm.PlaneOrientation(90, 90), EQ)
    assert len(g) == 181
    assert all(abs(p.x) < 1e-9 for p in g) and abs(g[90].y) < 1e-9 and abs(g[0].y) == pytest.approx(1)
    with pytest.raises(ValueError):
        rm.great_circle(rm.PlaneOrientation(0, 30), EQ, 2)


@pytest.mark.parametrize("make,field", [
    (lambda: rm.pole_of(rm.PlaneOrientation(0, 95)), "dip_deg"),
    (lambda: rm.pole_of(rm.PlaneOrientation(-5, 30)), "dip_direction_deg"),
    (lambda: rm.pole_of(rm.PlaneOrientation(float("nan"), 30)), "dip_direction_deg"),
    (lambda: rm.pole_of(rm.PlaneOrientation(10, float("inf"))), "dip_deg"),
    (lambda: rm.plane_of(rm.LineOrientation(float("nan"), 30)), "trend_deg"),
    (lambda: rm.project(rm.LineOrientation(10, 91), EQ), "plunge_deg"),
])
def test_validacion(make, field):
    with pytest.raises(ValueError, match=field):
        make()
