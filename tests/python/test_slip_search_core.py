import math

import pytest

import rockmasspy as rm

P = rm.Point2
M = rm.LeMethod


def pts(xy):
    return [P(float(x), float(y)) for x, y in xy]


def mirror(xy):
    return [(-x, y) for x, y in reversed(xy)]


def mc(g, c, phi):
    m = rm.LeMaterial()
    m.unit_weight, m.cohesion, m.friction_deg = g, c, phi
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


def grid(x0, x1, y0, y1, nx=20, ny=20, nr=11):
    g = rm.CircularGrid()
    g.x_min, g.x_max, g.y_min, g.y_max, g.nx, g.ny, g.n_radii = x0, x1, y0, y1, nx, ny, nr
    return g


def opts(method, refine=True):
    o = rm.SearchOptions()
    o.method, o.refine = method, refine
    return o


# ACADS 1(a), Slide problema 1: la cara mira a la izquierda; malla de centros del manual
ACADS1A = [(20, 25), (30, 25), (50, 35), (70, 35)]
GRID1A = (22.8, 43.7, 42.3, 62.6)


def acads1a(surface=ACADS1A):
    return section(surface, [layer([], 0)], [mc(20, 3, 19.6)], base=20)


# ACADS 3(a), Slide problema 7: capa débil entre y = 26.5 y 27.0
ACADS3 = [(20, 27.75), (43, 27.75), (67.5, 40), (84, 40)]


def acads3(mirrored=False):
    f = mirror if mirrored else (lambda p: p)
    return section(f(ACADS3), [layer(f([(20, 27.0), (63.5, 27.0), (84, 27.0)]), 0), layer(f([(20, 26.5), (84, 26.5)]), 1),
                               layer([], 0)], [mc(18.84, 28.5, 20), mc(18.84, 0, 10)], base=20)


def test_acads1a_bishop_search():
    r = rm.search_circular(acads1a(), grid(*GRID1A), opts(M.Bishop))
    assert r.best.factor_of_safety == pytest.approx(0.987, rel=0.01)  # Slide
    assert r.best.factor_of_safety == pytest.approx(0.9857, abs=2e-3)  # recalculado con afinado
    assert r.best.method == M.Bishop
    assert r.surface.circle is not None and r.surface.polyline is None
    assert r.info.verification == rm.Verification.Secondary
    assert not any("edge" in w for w in r.warnings)
    assert 0 < len(r.top) <= 10
    fs = [f for _, f in r.top]
    assert fs == sorted(fs) and fs[0] == r.best.factor_of_safety
    assert isinstance(r.top[0][0], rm.SlipSurface)
    assert 0 <= r.discarded < r.evaluated


def test_ordinary_method_works():
    r = rm.search_circular(acads1a(), grid(*GRID1A, nx=8, ny=8, nr=6), opts(M.Ordinary))
    assert r.best.method == M.Ordinary
    assert r.best.factor_of_safety is not None and r.best.factor_of_safety > 0


def test_reflected_section_gives_same_fs():
    x0, x1, y0, y1 = GRID1A
    a = rm.search_circular(acads1a(), grid(x0, x1, y0, y1, 8, 8, 6), opts(M.Bishop))
    b = rm.search_circular(acads1a(mirror(ACADS1A)), grid(-x1, -x0, y0, y1, 8, 8, 6), opts(M.Bishop))
    assert a.best.factor_of_safety == pytest.approx(b.best.factor_of_safety, abs=1e-6)
    assert a.surface.circle.xc == pytest.approx(-b.surface.circle.xc, abs=1e-9)


def test_block_search_acads3a_and_mirror():
    blk = rm.BlockSearch()
    blk.weak_line = pts([(20, 26.75), (84, 26.75)])
    assert (blk.left_angle_min, blk.left_angle_max, blk.right_angle_min, blk.right_angle_max) == (135, 155, 45, 65)
    r = rm.search_block(acads3(), blk, opts(M.Spencer))
    assert 1.246 * 0.97 <= r.best.factor_of_safety <= 1.246 * 1.01  # Slide 3(a), Spencer
    assert r.surface.polyline is not None and r.info.method_id == "Block-Search"
    blk.n_points, blk.n_angles = 8, 3
    a = rm.search_block(acads3(), blk, opts(M.Spencer))
    blk.weak_line = pts(mirror([(20, 26.75), (84, 26.75)]))
    b = rm.search_block(acads3(mirrored=True), blk, opts(M.Spencer))
    assert a.best.factor_of_safety == pytest.approx(b.best.factor_of_safety, abs=1e-6)


def test_edge_warning_and_determinism():
    g = grid(50, 60, 70, 80, 4, 4, 5)
    r1 = rm.search_circular(acads1a(), g, opts(M.Bishop, refine=False))
    r2 = rm.search_circular(acads1a(), g, opts(M.Bishop, refine=False))
    assert "critical centre on the edge of the search grid" in r1.warnings
    assert r1.best.factor_of_safety == r2.best.factor_of_safety
    assert (r1.evaluated, r1.discarded) == (r2.evaluated, r2.discarded)


def test_nothing_valid_gives_empty_fs():
    o = opts(M.Bishop, refine=False)
    o.min_mass_area = 1e9
    r = rm.search_circular(acads1a(), grid(*GRID1A, nx=2, ny=2, nr=3), o)
    assert r.best.factor_of_safety is None
    assert r.evaluated == r.discarded > 0
    assert r.top == []
    assert "no valid slip surface found" in r.warnings


@pytest.mark.parametrize(
    "field, value, name",
    [("x_min", math.nan, "grid.x_min"), ("nx", 0, "grid.nx"), ("n_radii", 1, "grid.n_radii")],
)
def test_invalid_grid_names_the_field(field, value, name):
    g = grid(*GRID1A)
    setattr(g, field, value)
    with pytest.raises(ValueError, match=name):
        rm.search_circular(acads1a(), g)


def test_invalid_block_names_the_field():
    blk = rm.BlockSearch()
    blk.weak_line = pts([(20, 26.75), (84, 26.75)])
    blk.left_angle_min = 45.0
    with pytest.raises(ValueError, match="left_angle_min"):
        rm.search_block(acads3(), blk)
