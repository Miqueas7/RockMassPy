import math

import pytest
from hypothesis import given, settings, strategies as st

import rockmasspy as rm

NAN, INF = float("nan"), float("inf")


def ex1(phi=38.15, support=0.5):
    # Goodman y Bray (1976), ejemplo 1
    i = rm.TopplingInput()
    i.heights_m = rm.goodman_bray_heights(16, 10, 5, 5, 1)
    i.block_width_m, i.base_dip_deg, i.a1_m, i.a2_m, i.crest_block = 10, 30, 5, 5, 10
    i.unit_weight, i.friction_deg, i.support_force = 25, phi, support
    return i


def test_heights():
    assert rm.goodman_bray_heights(16, 10, 5, 5, 1) == [4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 34, 28, 22, 16, 10, 4]
    with pytest.raises(ValueError):
        rm.goodman_bray_heights(16, 10, 5, 5, 5)


def test_table1():
    f = rm.toppling_forces(ex1(), 0.7855)
    p = lambda n: f.blocks[n].p_lower  # P_n lo produce el bloque n + 1
    assert [p(n) for n in (15, 14, 13)] == [0, 0, 0]
    assert all(f.blocks[n].state == rm.TopplingState.Stable for n in (15, 14, 13))
    for n, v in {12: 292.5, 11: 825.7, 10: 1556.0, 9: 2826.7, 8: 3922.2, 7: 4594.8, 6: 4837.0, 5: 4637.5, 4: 3978.1,
                 3: 2825.6, 2: 1413.5, 1: 472.2}.items():
        assert p(n) == pytest.approx(v, abs=0.2)
    assert f.blocks[2].state == rm.TopplingState.Sliding and f.blocks[1].state == rm.TopplingState.Sliding
    assert f.blocks[12].normal == pytest.approx(4533.4, abs=0.2)
    assert f.blocks[12].shear == pytest.approx(2457.5, abs=0.2)
    assert f.support_toppling == pytest.approx(-1486.8, abs=0.2)
    assert f.support_sliding == pytest.approx(0.47, abs=0.01)


def test_table2():
    f = rm.toppling_forces(ex1(support=2013), 0.650)
    assert f.blocks[1].p_lower == pytest.approx(4260.3, abs=0.2)
    assert f.support_sliding == pytest.approx(2012.9, abs=0.2)
    assert f.blocks[0].normal == pytest.approx(4641.7, abs=0.3)
    assert f.blocks[0].shear == pytest.approx(3017.1, abs=0.3)


@pytest.mark.parametrize("phi,t,expected", [(38.15, 0.5, 1.000), (33.02, 2013, 1.000), (38.66, 0.5, 1.018),
                                            (38.66, 2013, 1.231)])
def test_vo1(phi, t, expected):
    r = rm.toppling_fs(ex1(phi, t))
    assert r.factor_of_safety == pytest.approx(expected, abs=1e-3)
    assert r.info.verification == rm.Verification.Primary
    assert not r.fs_bounded


def test_zero_force_top_block_is_toppling():
    i = rm.TopplingInput()
    i.heights_m = [20.0, 10.0 / math.tan(math.radians(30))]
    i.block_width_m, i.base_dip_deg, i.a1_m, i.a2_m, i.crest_block = 10, 30, 0, 0, 1
    i.unit_weight, i.friction_deg = 25, 40
    f = rm.toppling_forces(i, 0.7)
    assert f.blocks[1].state == rm.TopplingState.Toppling
    assert abs(f.blocks[1].p_lower) < 1e-9


def test_bounds():
    r = rm.toppling_fs(ex1(60, 1e9))
    assert r.factor_of_safety == 100 and not r.fs_bounded and "toppling FS above 100" in r.notes
    i = ex1(20, 0.0)
    i.base_dip_deg = 60
    r = rm.toppling_fs(i)
    assert r.fs_bounded and r.factor_of_safety < math.tan(math.radians(20)) + 1e-6
    assert any("support is insufficient" in w for w in r.warnings)


@settings(max_examples=40, deadline=None)
@given(st.floats(0.3, 0.98), st.floats(0.3, 0.98), st.floats(0, 5000), st.floats(0, 5000))
def test_monotone(m1, m2, t1, t2):
    lo, hi = sorted((m1, m2))
    assert rm.toppling_forces(ex1(), hi).support_required <= rm.toppling_forces(ex1(), lo).support_required + 1e-9
    lo, hi = sorted((t1, t2))
    assert rm.toppling_fs(ex1(38.66, hi)).factor_of_safety >= rm.toppling_fs(ex1(38.66, lo)).factor_of_safety - 1e-9


def _set(**kw):
    i = ex1()
    for k, v in kw.items():
        setattr(i, k, v)
    return i


@pytest.mark.parametrize("kw", [dict(heights_m=[]), dict(crest_block=0), dict(crest_block=17), dict(base_dip_deg=0),
                                dict(base_dip_deg=90), dict(friction_deg=0), dict(support_height_m=5.0),
                                dict(a1_m=8.0)])
def test_rejects(kw):
    with pytest.raises(ValueError):
        rm.toppling_fs(_set(**kw))


def test_zero_height_rejected():
    i = ex1()
    i.heights_m = [4, 0, 12]
    i.crest_block = 3
    with pytest.raises(ValueError):
        rm.toppling_fs(i)


@pytest.mark.parametrize("field", ["block_width_m", "base_dip_deg", "a1_m", "a2_m", "unit_weight", "friction_deg",
                                   "support_force", "support_angle_deg", "support_height_m"])
@pytest.mark.parametrize("bad", [NAN, INF])
def test_non_finite_names_field(field, bad):
    with pytest.raises(ValueError, match=field):
        rm.toppling_fs(_set(**{field: bad}))


def test_unset_field_names_it():
    i = rm.TopplingInput()
    i.heights_m, i.crest_block = [4.0, 8.0], 1
    with pytest.raises(ValueError, match="block_width_m"):
        rm.toppling_fs(i)
