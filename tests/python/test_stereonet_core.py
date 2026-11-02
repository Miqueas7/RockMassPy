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
    assert math.hypot(pt.x, pt.y) <= 1 + 1e-12  # inmersión >= 0: dentro del disco en ambas proyecciones
    back = rm.unproject(pt, proj)
    assert back.plunge_deg == pytest.approx(pl, abs=1e-6)
    if pl < 89:
        assert adiff(back.trend_deg, t) < 1e-6


@given(t=st.floats(0, 360), proj=st.sampled_from([EA, EQ]))
def test_proyeccion_inmersion_90(t, proj):  # la tendencia es indiferente en el centro
    pt = rm.project(rm.LineOrientation(t, 90), proj)
    assert (pt.x, pt.y) == pytest.approx((0, 0), abs=1e-12)
    assert rm.unproject(pt, proj).plunge_deg == pytest.approx(90, abs=1e-9)


def test_cerca_de_vertical_ida_y_vuelta():
    q = rm.plane_of(rm.pole_of(rm.PlaneOrientation(123, 89.999999)))
    assert abs(q.dip_deg - 89.999999) < 1e-9


def test_unproject_fuera_nombra_point():
    with pytest.raises(ValueError, match="'point'") as e:
        rm.unproject(rm.Point2(1.0, 0.1), EQ)
    assert "1.00498" in str(e.value)


def test_interseccion_horizontal_canonica():
    P = rm.PlaneOrientation
    for a, b in [(P(90, 45), P(270, 45)), (P(10, 90), P(100, 90)), (P(280, 90), P(10, 90))]:
        ab, ba = rm.plane_intersection(a, b), rm.plane_intersection(b, a)
        assert (ab.trend_deg, ab.plunge_deg) == pytest.approx((ba.trend_deg, ba.plunge_deg), abs=1e-9)
        if ab.plunge_deg == 0:
            assert 0 <= ab.trend_deg < 180


def test_gran_circulo_oblicuo():
    pl = rm.PlaneOrientation(130, 55)
    pole = rm.pole_of(pl)
    for proj in (EA, EQ):
        g = rm.great_circle(pl, proj)
        assert all(rm.angle_between(rm.unproject(p, proj), pole) == pytest.approx(90, abs=1e-6) for p in g)
        mid = rm.project(rm.LineOrientation(130, 55), proj)
        assert (g[90].x, g[90].y) == pytest.approx((mid.x, mid.y), abs=1e-9)


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
        assert adiff(ab.trend_deg, ba.trend_deg) < 1e-6 or ab.plunge_deg > 89.999
        assert ab.plunge_deg == pytest.approx(ba.plunge_deg, abs=1e-6)


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


def test_fisher_cuatro_polos():
    s = rm.fisher_stats([rm.LineOrientation(t, 80) for t in (0, 90, 180, 270)])
    assert s.mean.plunge_deg == pytest.approx(90, abs=1e-9)
    assert s.resultant_length == pytest.approx(4 * math.sin(math.radians(80)), abs=1e-9)
    assert s.kappa == pytest.approx(49.3673, abs=1e-4)
    assert s.alpha95_deg == pytest.approx(13.2067, abs=1e-4)
    assert s.info.verification == rm.Verification.Secondary and "Tauxe" in s.info.source


def test_fisher_uno_e_identicos():
    s = rm.fisher_stats([rm.LineOrientation(120, 40)])
    assert s.kappa is None and s.alpha95_deg is None
    s = rm.fisher_stats([rm.LineOrientation(120, 40)] * 3)
    assert math.isinf(s.kappa) and s.alpha95_deg == 0


def test_fisher_axial_casi_vertical():
    s = rm.fisher_stats([rm.LineOrientation(t, p) for t, p in ((90, 2), (270, 2), (88, 1), (272, 3))])
    assert s.mean.plunge_deg < 3


def test_fisher_dispersos_no_lanza():
    s = rm.fisher_stats([rm.LineOrientation(t, p) for t, p in ((0, 0), (90, 0), (180, 45), (270, 30), (0, 89))])
    assert s.n == 5
    s = rm.fisher_stats([rm.LineOrientation(0, 0), rm.LineOrientation(90, 0)])  # R = sqrt(2)
    assert s.alpha95_deg is None
    assert s.warnings == ["alpha95 undefined: poles too dispersed for their number"]


def test_fisher_errores():
    with pytest.raises(ValueError):
        rm.fisher_stats([])
    with pytest.raises(ValueError):
        rm.fisher_stats([rm.LineOrientation(float("nan"), 10)])


_line = st.builds(rm.LineOrientation, st.floats(0, 359.9), st.floats(0, 90))


@given(st.lists(_line, min_size=2, max_size=8), st.lists(st.floats(0, 359.9), min_size=1, max_size=4))
def test_fisher_invertir_polo_horizontal_no_cambia(poles, trends):
    # un polo horizontal en t y en t + 180 es el mismo eje: media y kappa no cambian
    flat = [rm.LineOrientation(t, 0) for t in trends]
    flipped = [rm.LineOrientation((t + 180) % 360, 0) for t in trends]
    a, b = rm.fisher_stats(poles + flat), rm.fisher_stats(poles + flipped)
    assert a.resultant_length == pytest.approx(b.resultant_length, abs=1e-9)
    assert rm.angle_between(a.mean, b.mean) < 1e-4
    if a.kappa is not None and math.isfinite(a.kappa):
        assert a.kappa == pytest.approx(b.kappa, rel=1e-6)


def test_fisher_invertir_eje_horizontal():
    base = [rm.LineOrientation(t, p) for t, p in ((10, 0), (20, 5), (355, 3), (15, 0))]
    flip = [rm.LineOrientation(190, 0)] + base[1:]  # 10/0 y 190/0 son el mismo eje
    a, b = rm.fisher_stats(base), rm.fisher_stats(flip)
    assert rm.angle_between(a.mean, b.mean) < 1e-6
    assert a.kappa == pytest.approx(b.kappa, rel=1e-9)
    assert a.resultant_length == pytest.approx(b.resultant_length, abs=1e-9)


def test_densidad_circulo_de_conteo():
    poles = [rm.LineOrientation(120, 40)] * 50
    d = rm.pole_density(poles, [rm.LineOrientation(120, 40), rm.LineOrientation(150, 40)])
    assert d[0] == pytest.approx(100) and d[1] == 0
    assert rm.pole_density([rm.LineOrientation(90, 0)], [rm.LineOrientation(270, 0)])[0] == pytest.approx(100)
    for bad in (0.0, 0.6):
        with pytest.raises(ValueError):
            rm.pole_density(poles, [rm.LineOrientation(0, 0)], bad)
    with pytest.raises(ValueError):
        rm.pole_density([], [rm.LineOrientation(0, 0)])


@given(st.lists(_line, min_size=1, max_size=6), _line, st.floats(0.005, 0.5))
def test_densidad_acotada(poles, at, frac):
    d = rm.pole_density(poles, [at], frac)[0]
    assert 0 <= d <= 100 * 0.01 / frac + 1e-9


def test_densidad_media_uniforme():
    import random

    rng = random.Random(7)

    def uniform():  # uniforme en el hemisferio inferior
        return rm.LineOrientation(rng.uniform(0, 360), math.degrees(math.asin(rng.random())))

    poles = [uniform() for _ in range(300)]
    d = rm.pole_density(poles, [uniform() for _ in range(2000)])
    assert sum(d) / len(d) == pytest.approx(1.0, abs=0.15)


def test_densidad_factor_area_fraction():
    poles = [rm.LineOrientation(120, 40)] * 50
    assert rm.pole_density(poles, [rm.LineOrientation(120, 40)], 0.05)[0] == pytest.approx(20)


def test_fisher_media_horizontal_no_depende_del_orden():
    a = rm.fisher_stats([rm.LineOrientation(t, 0) for t in (10, 190, 20)])
    b = rm.fisher_stats([rm.LineOrientation(t, 0) for t in (190, 10, 20)])
    assert a.mean.trend_deg == pytest.approx(b.mean.trend_deg, abs=1e-9) and a.mean.trend_deg < 180
