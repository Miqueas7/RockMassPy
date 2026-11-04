import pytest

import rockmasspy as rm

from test_limit_equilibrium_core import FK_CIRCLE, circle, fk, mirror, FK_SURFACE, run
from test_slip_search_core import GRID1A, grid, layer, mc, opts, section

M = rm.LeMethod


def test_fredlund_krahn_bishop_ky_gives_fs_one():
    r = rm.le_yield_coefficient(fk(), circle(*FK_CIRCLE), M.Bishop)
    assert 0 < r.ky < 1 and r.fs_static == pytest.approx(2.0756, abs=2e-3)
    s = fk()
    s.kh = r.ky
    assert run(s, circle(*FK_CIRCLE), M.Bishop).factor_of_safety == pytest.approx(1.0, abs=1e-6)
    assert r.info.verification == rm.Verification.Secondary and r.warnings == []


def test_reflected_section_gives_same_ky():
    a = rm.le_yield_coefficient(fk(), circle(*FK_CIRCLE), M.Bishop)
    b = rm.le_yield_coefficient(fk(surface=mirror(FK_SURFACE)), circle(-FK_CIRCLE[0], *FK_CIRCLE[1:]), M.Bishop)
    assert a.ky == pytest.approx(b.ky, abs=1e-6)


def acads1d():
    s = section([(20, 25), (30, 25), (50, 35), (70, 35)],
                [layer([(20, 25), (30, 25), (40, 27), (50, 29), (54, 31), (70, 31)], 0),
                 layer([(20, 25), (30, 25), (40, 27), (52, 24), (70, 24)], 1), layer([], 2)],
                [mc(19.5, 0, 38), mc(19.5, 5.3, 23), mc(19.5, 7.2, 20)], base=20)
    s.kh = 0.15
    return s


def test_acads_1d_bishop_ky_near_015():
    # Slide 1(d): Bishop 1.016 con kh 0.15, así que el ky de Bishop en ese círculo queda cerca de 0.15
    sr = rm.search_circular(acads1d(), grid(*GRID1A), opts(M.Bishop))
    r = rm.le_yield_coefficient(acads1d(), sr.surface, M.Bishop)
    assert r.ky == pytest.approx(0.15, abs=0.02)


def test_static_failure_strong_slope_and_no_convergence():
    weak = fk()
    weak.materials = [mc(120, 0, 5)]
    r = rm.le_yield_coefficient(weak, circle(*FK_CIRCLE), M.Bishop)
    assert r.ky == 0 and any("at or below 1" in w for w in r.warnings)
    strong = fk()
    strong.materials = [mc(120, 1e6, 20)]
    r = rm.le_yield_coefficient(strong, circle(*FK_CIRCLE), M.Bishop)
    assert r.ky is None and any("kh = 1" in n for n in r.notes)
    o = rm.LeOptions()
    o.max_iterations = 1
    r = rm.le_yield_coefficient(fk(), circle(*FK_CIRCLE), M.Spencer, o)
    assert r.ky is None and any("ky not found" in w for w in r.warnings)
