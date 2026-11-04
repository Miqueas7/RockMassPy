import math

import pytest

import rockmasspy as rm

NAN = float("nan")
P = rm.Point2
M = rm.LeMethod
METHODS = (M.Ordinary, M.Bishop, M.JanbuSimplified, M.Spencer, M.MorgensternPrice)


def pts(xy):
    return [P(float(x), float(y)) for x, y in xy]


def mirror(xy):
    return [(-x, y) for x, y in reversed(xy)]


def mc(g, c, phi, ru=0.0):
    m = rm.LeMaterial()
    m.unit_weight, m.cohesion, m.friction_deg, m.ru = g, c, phi, ru
    return m


def layer(bottom, material):
    lay = rm.LeLayer()
    lay.bottom, lay.material = pts(bottom), material
    return lay


def section(surface, layers, materials, base=None):
    s = rm.LeSection()
    s.surface, s.layers, s.materials = pts(surface), layers, materials
    s.model_base_y = base
    return s


def circle(xc, yc, r):
    f = rm.SlipSurface()
    f.circle = rm.Circle(xc, yc, r)
    return f


def polyline(xy):
    f = rm.SlipSurface()
    f.polyline = pts(xy)
    return f


def run(s, f, method, n=50, **kw):
    o = rm.LeOptions()
    o.n_slices = n
    for k, v in kw.items():
        setattr(o, k, v)
    return rm.le_factor_of_safety(s, f, method, o)


def fs(s, f, method, n=50):
    r = run(s, f, method, n)
    assert r.factor_of_safety is not None, method
    return r.factor_of_safety


# Slide2 Verification Manual (2022), problema 21: Fredlund y Krahn (1977), psf, pcf y ft
FK_SURFACE = [(0, 60), (60, 60), (140, 20), (180, 20)]


def fk(ru=0.0, surface=FK_SURFACE):
    return section(surface, [layer([], 0)], [mc(120, 600, 20, ru)])


FK_CIRCLE = (120, 90, 80)

# ACADS 1(a): la cara mira a la izquierda
ACADS1A = [(20, 25), (30, 25), (50, 35), (70, 35)]

# ACADS 3(b): capa débil entre 26.5 y 27.0, superficie dada de la Tabla 8.2
ACADS3B = [(20, 27.75), (43, 27.75), (67.5, 40), (84, 40)]
ACADS3B_SLIP = [(41.85, 27.75), (44.0, 26.5), (63.5, 27.0), (73.31, 40.0)]


def acads3b(flip=False):
    t = mirror if flip else (lambda p: p)
    return section(t(ACADS3B), [layer(t([(20, 27.0), (63.5, 27.0), (84, 27.0)]), 0),
                                layer(t([(20, 26.5), (84, 26.5)]), 1), layer([], 0)],
                   [mc(18.84, 28.5, 20), mc(18.84, 0, 10)], base=20.0)


@pytest.mark.parametrize("n", [50, 400])
@pytest.mark.parametrize("method,pub_dry,re_dry,pub_ru,re_ru", [
    (M.Ordinary, 1.928, 1.9277, 1.607, None),  # el recalculado con ru va aparte, con 400 tajadas
    (M.Bishop, 2.080, 2.0756, 1.766, 1.7592),
    (M.Spencer, 2.073, 2.0718, 1.761, 1.7574),
    (M.MorgensternPrice, 2.076, 2.0714, 1.764, 1.7567),
])
def test_fredlund_krahn(n, method, pub_dry, re_dry, pub_ru, re_ru):
    # el Ordinario de Slide con ru (1.687) resta u de otra forma; manda F&K (N' = W cos a - u l), 1.607
    dry, wet = fs(fk(), circle(*FK_CIRCLE), method, n), fs(fk(0.25), circle(*FK_CIRCLE), method, n)
    assert dry == pytest.approx(pub_dry, rel=0.005)
    assert dry == pytest.approx(re_dry, abs=1e-3)
    assert wet == pytest.approx(pub_ru, rel=0.005)
    if re_ru is not None:
        assert wet == pytest.approx(re_ru, abs=1e-3)


def test_fredlund_krahn_ordinary_ru_recalculated():
    # N' recortado a >= 0 con nota; recalculado con el recorte y 400 tajadas (sin recorte saldría 1.6062)
    assert fs(fk(0.25), circle(*FK_CIRCLE), M.Ordinary, 400) == pytest.approx(1.6073, abs=1e-3)


def test_fredlund_krahn_lambda_and_notes():
    assert run(fk(), circle(*FK_CIRCLE), M.Spencer, 400).lambda_ == pytest.approx(0.258, abs=2e-3)
    r = run(fk(), circle(*FK_CIRCLE), M.MorgensternPrice, 400)
    assert r.lambda_ == pytest.approx(0.323, abs=2e-3)
    assert r.converged and not r.warnings
    assert run(fk(), circle(*FK_CIRCLE), M.Bishop).lambda_ is None
    notes = run(fk(0.25), circle(*FK_CIRCLE), M.Ordinary).notes
    assert len(notes) == 1 and "friction taken as zero" in notes[0]


def test_acads_1a_fixed_circle():
    s = section(ACADS1A, [layer([], 0)], [mc(20, 3, 19.6)], base=20.0)
    f = circle(30.16, 51.9, 26.9)
    for method, re, slide in ((M.Bishop, 0.9857, 0.987), (M.Spencer, 0.9846, 0.986),
                              (M.MorgensternPrice, 0.9846, 0.986)):
        v = fs(s, f, method)
        assert v == pytest.approx(re, abs=2e-3)
        assert v == pytest.approx(slide, rel=0.01)


def test_acads_3b_given_surface():
    # la base entre x 43.14 y 44 cae en la capa débil; oráculo: recalculado y Slide (1.277, 1.262).
    # La referencia ACADS 1.34 solo se anota: con los estratos no se reproduce (-4.8 %).
    f = polyline(ACADS3B_SLIP)
    s, m = fs(acads3b(), f, M.Spencer), fs(acads3b(), f, M.MorgensternPrice)
    assert s == pytest.approx(1.2758, abs=3e-3)
    assert m == pytest.approx(1.2601, abs=3e-3)
    assert s == pytest.approx(1.277, rel=0.005)
    assert m == pytest.approx(1.262, rel=0.005)


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("case", ["fk", "fk_ru", "acads3b"])
def test_reflected_section(case, method):
    if case == "acads3b":
        a, b = acads3b(), acads3b(flip=True)
        fa, fb = polyline(ACADS3B_SLIP), polyline(mirror(ACADS3B_SLIP))
    else:
        ru = 0.25 if case == "fk_ru" else 0.0
        a, b = fk(ru), fk(ru, mirror(FK_SURFACE))
        fa, fb = circle(*FK_CIRCLE), circle(-120, 90, 80)
    ra, rb = run(a, fa, method), run(b, fb, method)
    assert rb.factor_of_safety == pytest.approx(ra.factor_of_safety, rel=1e-9)
    if ra.lambda_ is not None:
        assert rb.lambda_ == pytest.approx(ra.lambda_, rel=1e-9)
    assert rb.slices[0].x_left == pytest.approx(-ra.slices[-1].x_right, abs=1e-9)
    assert all(t.x_left < t.x_right for t in rb.slices)


def test_weights_and_slices():
    a = run(fk(), circle(*FK_CIRCLE), M.Bishop, 50)
    b = run(fk(), circle(*FK_CIRCLE), M.Bishop, 400)
    assert a.sliding_mass_area == pytest.approx(b.sliding_mass_area, rel=1e-3)
    assert sum(t.weight for t in a.slices) == pytest.approx(120 * a.sliding_mass_area, rel=1e-9)
    sl = rm.make_slices(fk(), circle(*FK_CIRCLE), 50)
    assert all(x.x_right == y.x_left for x, y in zip(sl, sl[1:]))
    assert {60.0, 140.0} <= {t.x_left for t in sl}
    s = fk()
    s.materials = [mc(0.0, 600, 20)]
    with pytest.raises(ValueError, match=r"materials\[0\]\.unit_weight"):
        run(s, circle(*FK_CIRCLE), M.Bishop)


def test_odd_surfaces():
    with pytest.raises(ValueError, match="slip surface does not cut the ground surface twice"):
        run(fk(), circle(120, 200, 50), M.Bishop)
    with pytest.raises(ValueError, match="polyline"):
        run(fk(), polyline([(40, 60), (100, 30), (90, 25), (150, 20)]), M.Spencer)
    with pytest.raises(ValueError, match="polyline"):
        run(fk(), polyline([(50, 50), (100, 25), (150, 20)]), M.Spencer)
    with pytest.raises(ValueError, match="model_base_y"):
        run(section(ACADS1A, [layer([], 0)], [mc(20, 3, 19.6)], base=30.0), circle(30.16, 51.9, 26.9), M.Bishop)
    moved = [list(p) for p in ACADS3B_SLIP]
    moved[2][0] += 1e-12
    for method in METHODS:
        a = fs(acads3b(), polyline(ACADS3B_SLIP), method)
        assert fs(acads3b(), polyline(moved), method) == pytest.approx(a, abs=1e-9)
    notch = fk(surface=[(0, 60), (60, 60), (90, 45), (95, 10), (100, 40), (140, 20), (180, 20)])
    r = run(notch, circle(*FK_CIRCLE), M.Bishop)
    assert r.factor_of_safety is not None
    assert len(r.warnings) == 1 and "more than twice" in r.warnings[0]


def test_backward_mass_and_convergence():
    s = section([(-20, 50), (12, 50), (13, 70), (22, 70), (22.5, 45), (60, 45)], [layer([], 0)], [mc(20, 10, 30)])
    for method in METHODS:
        r = run(s, circle(12, 65, 20), method)
        assert r.factor_of_safety is None and not r.converged
        assert r.notes == ["the sliding mass does not move towards the face"]
    r = run(fk(), circle(*FK_CIRCLE), M.Spencer, max_iterations=1)
    assert r.factor_of_safety is None and r.lambda_ is None and not r.converged
    assert r.warnings == ["Spencer did not converge"]


@pytest.mark.parametrize("method", METHODS)
def test_seismic_coefficient(method):
    s = fk()
    s.kh = 0.1
    assert fs(s, circle(*FK_CIRCLE), method) < fs(fk(), circle(*FK_CIRCLE), method)
    s.kh = 0.0
    assert fs(s, circle(*FK_CIRCLE), method) == fs(fk(), circle(*FK_CIRCLE), method)


def _edit(fn):
    s, f, o = fk(), circle(*FK_CIRCLE), rm.LeOptions()
    fn(s, f, o)
    return lambda: rm.le_factor_of_safety(s, f, M.Bishop, o)


def _set(obj, **kw):
    for k, v in kw.items():
        setattr(obj, k, v)


def _material(**kw):
    def edit(s, f, o):
        m = s.materials[0]
        _set(m, **kw)
        s.materials = [m]
    return edit


def _crack(depth, fill):
    def edit(s, f, o):
        c = rm.LeTensionCrack()
        c.depth_m, c.water_fill = depth, fill
        s.crack = c
    return edit


def _hb(**kw):
    return _material(model=rm.StrengthModel.HoekBrown, **kw)


@pytest.mark.parametrize("edit,field", [
    (lambda s, f, o: _set(s, surface=pts([(0, 60), (60, NAN), (140, 20)])), r"surface\[1\]\.y"),
    (_material(cohesion=NAN), r"materials\[0\]\.cohesion"),
    (_material(friction_deg=NAN), r"materials\[0\]\.friction_deg"),
    (_material(unit_weight=NAN), r"materials\[0\]\.unit_weight"),
    (_material(ru=1.0), r"materials\[0\]\.ru"),
    (_material(ru=NAN), r"materials\[0\]\.ru"),
    (lambda s, f, o: _set(s, kh=NAN), "kh"),
    (lambda s, f, o: _set(s, kh=-0.1), "kh"),
    (lambda s, f, o: _set(s, water_unit_weight=NAN), "water_unit_weight"),
    (lambda s, f, o: _set(s, model_base_y=NAN), "model_base_y"),
    (_crack(2.0, 1.5), r"crack\.water_fill"),
    (_crack(NAN, 0.0), r"crack\.depth_m"),
    (lambda s, f, o: _set(f, circle=rm.Circle(120, 90, NAN)), r"circle\.radius"),
    (lambda s, f, o: _set(f, polyline=pts([(0, 1), (2, 3)])), "exactly one"),
    (lambda s, f, o: _set(o, n_slices=4), "n_slices"),
    (lambda s, f, o: _set(o, tolerance=NAN), "tolerance"),
    (lambda s, f, o: _set(o, function=rm.InterSliceFunction.Points), "function_points"),
    (lambda s, f, o: _set(o, function=rm.InterSliceFunction.Points, function_points=pts([(0, 1), (1, -0.5)])),
     r"function_points\[1\]\.y"),
    (_hb(), r"materials\[0\]\.hb"),
    (_hb(hb=rm.hb_params(50, 10, 0)), r"materials\[0\]\.sigma_ci"),
    (_crack(2.0, 0.5), r"not implemented yet \(task 2\)"),
    (lambda s, f, o: _set(s, piezometric=pts([(0, 50), (180, 10)])), r"not implemented yet \(task 2\)"),
    (_hb(hb=rm.hb_params(50, 10, 0), sigma_ci=50.0), r"not implemented yet \(task 3\)"),
])
def test_invalid_inputs_name_the_field(edit, field):
    with pytest.raises(ValueError, match=field):
        _edit(edit)()


def test_janbu_corrected_not_implemented_yet():
    with pytest.raises(ValueError, match=r"not implemented yet \(task 2\)"):
        run(fk(), circle(*FK_CIRCLE), M.JanbuCorrected)


def test_interslice_functions():
    sp = fs(fk(), circle(*FK_CIRCLE), M.Spencer)
    flat = run(fk(), circle(*FK_CIRCLE), M.MorgensternPrice, function=rm.InterSliceFunction.Points,
               function_points=pts([(0, 1), (1, 1)]))
    assert flat.factor_of_safety == pytest.approx(sp, abs=1e-9)
    sine = pts([(i / 100, math.sin(math.pi * i / 100)) for i in range(101)])
    r = run(fk(), circle(*FK_CIRCLE), M.MorgensternPrice, function=rm.InterSliceFunction.Points, function_points=sine)
    assert r.factor_of_safety == pytest.approx(fs(fk(), circle(*FK_CIRCLE), M.MorgensternPrice), abs=1e-4)


@pytest.mark.parametrize("method", METHODS)
def test_method_info_is_secondary(method):
    r = run(fk(), circle(*FK_CIRCLE), method)
    assert r.info.verification == rm.Verification.Secondary
    assert r.method == method
    assert "Fredlund" in r.info.source


# --- Correcciones de la revisión de la tarea 1 ---


def reviewer_slope(kh):
    s = section([(0, 30), (40, 30), (80, 0), (120, 0)], [layer([], 0)], [mc(20, 20, 35)])
    s.kh = kh
    return s


@pytest.mark.parametrize("method", METHODS)
def test_zero_strength_gives_zero(method):
    r = run(section(FK_SURFACE, [layer([], 0)], [mc(120, 0, 0)]), circle(*FK_CIRCLE), method)
    assert r.factor_of_safety == 0.0
    assert r.converged and not r.warnings


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("material", [mc(120, 0, 20, 0.99), mc(120, 600, 89.9)])
def test_bad_iterates_warn_instead_of_note(method, material):
    r = run(section(FK_SURFACE, [layer([], 0)], [material]), circle(*FK_CIRCLE), method)
    assert r.factor_of_safety is not None or r.warnings
    assert not any("does not move towards the face" in n for n in r.notes)
    if r.factor_of_safety is None:
        assert "did not converge" in r.warnings[0]


def test_lambda_root_with_strong_kh():
    # valores del revisor con su propio solver; la sustitución directa de λ divergía aquí
    f = circle(70, 45, 50)
    sp = run(reviewer_slope(0.2), f, M.Spencer)
    assert sp.factor_of_safety == pytest.approx(1.4389, abs=2e-3)
    assert sp.lambda_ == pytest.approx(0.5748, abs=2e-3)
    assert fs(reviewer_slope(0.2), f, M.Bishop) == pytest.approx(1.4118, abs=2e-3)
    assert fs(reviewer_slope(0.2), f, M.MorgensternPrice) == pytest.approx(1.4346, abs=2e-3)
    sp = run(reviewer_slope(0.25), f, M.Spencer)
    assert sp.factor_of_safety == pytest.approx(1.346, abs=2e-3)
    assert sp.lambda_ == pytest.approx(0.597, abs=2e-3)


def test_polyline_bishop_warns_when_not_converged():
    r = run(fk(), polyline([(30, 60), (70, 35), (110, 25), (150, 20)]), M.Bishop, max_iterations=1)
    assert r.factor_of_safety is None
    assert len(r.warnings) == 1 and r.warnings[0].startswith("Bishop did not converge")


def test_negligible_mass_note():
    r = run(fk(), polyline([(80, 50), (90, 45 - 1e-7), (100, 40)]), M.Ordinary)
    assert r.factor_of_safety is not None
    assert "negligible sliding mass" in r.notes


@pytest.mark.parametrize("method", METHODS)
def test_translated_coordinates(method):
    dx, dy = 5e5, 8.5e6
    moved = fk(surface=[(x + dx, y + dy) for x, y in FK_SURFACE])
    assert fs(moved, circle(120 + dx, 90 + dy, 80), method) == pytest.approx(
        fs(fk(), circle(*FK_CIRCLE), method), rel=1e-9)


@pytest.mark.parametrize("ox", [0.0, 8.5e6])
def test_false_cut_is_rejected(ox):
    g = [(x + ox, y) for x, y in [(0, 24.386), (40, 24.386), (59.550, 0), (99.550, 0)]]
    with pytest.raises(ValueError, match="does not cut"):
        run(section(g, [layer([], 0)], [mc(20, 10, 30)]), circle(58.480 + ox, 23.905, 24.011), M.Bishop)


def test_review_option_checks():
    with pytest.raises(ValueError, match="tolerance"):
        run(fk(), circle(*FK_CIRCLE), M.Bishop, tolerance=1e-2)
    assert "effective normal force below zero in 3 slices" in run(fk(0.25), circle(*FK_CIRCLE), M.Bishop).notes
    r = run(fk(), circle(*FK_CIRCLE), M.Spencer, max_iterations=1)
    assert all(t.normal_force == t.shear_strength == t.interslice_normal_right == t.interslice_shear_right == 0.0
               for t in r.slices)
    for p in ([(0, 1)], [(0.1, 1), (1, 1)], [(0, 1), (0.9, 1)], [(0, 0), (1, 0)]):
        with pytest.raises(ValueError, match="function_points"):
            run(fk(), circle(*FK_CIRCLE), M.MorgensternPrice, function=rm.InterSliceFunction.Points,
                function_points=pts(p))
