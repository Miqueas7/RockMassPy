import math

import pytest

import rockmasspy as rm
from rockmasspy import bem


def test_shapes_basic():
    c = bem.circle(0, 0, 2, n=64)
    assert len(c) == 64 and all(abs(math.hypot(x, y) - 2) < 1e-12 for x, y in c)
    e = bem.ellipse(1, 2, 3, 1, n=64)
    assert all(abs(((x - 1) / 3) ** 2 + (y - 2) ** 2 - 1) < 1e-12 for x, y in e)
    r = bem.rectangle(0, 0, 4, 2, n_per_side=4)
    assert len(r) == 16 and max(x for x, _ in r) == 2 and min(y for _, y in r) == -1
    h = bem.horseshoe(0, 0, 4, 3, n=64)
    assert min(y for _, y in h) == 0 and max(y for _, y in h) == pytest.approx(5)


def test_kirsch_circle_min_sf_matches_strength_factor():
    mat = bem.BemMaterial("MC", c_mpa=5, phi_deg=30)
    res = bem.analyze_bem([bem.circle(0, 0, 3)], sigma1_mpa=30, sigma3_mpa=30, e_mpa=10000, nu=0.2, material=mat,
                          points=[(3.0003 * math.cos(t), 3.0003 * math.sin(t)) for t in (0.3, 1.0, 2.0)])
    ref = rm.strength_factor(rm.SfMaterial(criterion=rm.SfCriterion.MohrCoulomb, c_mpa=5, phi_deg=30,
                                           tensile_mpa=0.0), 60.0, 0.0, 12.0).sf
    assert res.min_sf == pytest.approx(ref, rel=0.02)


def test_horseshoe_vertical_sigma1_runs():
    mat = bem.BemMaterial("MC", c_mpa=3, phi_deg=35)
    res = bem.analyze_bem([bem.horseshoe(0, 0, 5, 3)], sigma1_mpa=20, sigma3_mpa=0, alpha_deg=90, e_mpa=20000,
                          nu=0.25, material=mat)
    assert res.min_sf is not None and res.min_sf_location is not None
    assert res.tension_count > 0 and "tension zone present" in res.warnings
    assert res.needs_attention
    assert "elastic analysis: strength factor below 1 marks overstress, not failure extent" in res.notes


def test_two_stopes_pillar_has_highest_sigma1():
    a = bem.rectangle(-8, 0, 6, 10, n_per_side=4)
    b = bem.rectangle(8, 0, 6, 10, n_per_side=4)
    res = bem.analyze_bem([a, b], sigma1_mpa=30, sigma3_mpa=15, alpha_deg=90, e_mpa=30000, nu=0.2,
                          points=[(0.0, 0.0), (0.0, 20.0), (-30.0, 0.0), (30.0, 30.0)])
    s1 = res.field.sigma1
    assert s1[0] == max(s1)


def test_default_grid_masks_interior():
    res = bem.analyze_bem([bem.circle(0, 0, 3)], sigma1_mpa=30, sigma3_mpa=15, e_mpa=10000, nu=0.2)
    f = res.field
    assert len(f.x) == 3600 and 0 < sum(f.inside) < 3600
    assert all(math.isnan(s) for s, i in zip(f.sigma1, f.inside) if i)
    assert all(not math.isnan(s) for s, i in zip(f.sigma1, f.inside) if not i)
    assert res.min_sf is None and len(res.boundary.sigma_tt) > 0


def test_gsi_mi_d_equals_mb_s_a():
    p = rm.hb_params(50, 10, 0.0, rm.HbEdition.HB2002)
    kw = dict(sigma1_mpa=25, sigma3_mpa=10, e_mpa=10000, nu=0.2, grid=(-8, 8, -8, 8, 9, 9))
    r1 = bem.analyze_bem([bem.circle(0, 0, 2)], material=bem.BemMaterial("HB", sigma_ci_mpa=60, gsi=50, mi=10, d=0.0),
                         **kw)
    r2 = bem.analyze_bem([bem.circle(0, 0, 2)], material=bem.BemMaterial("HB", sigma_ci_mpa=60, mb=p.mb, s=p.s,
                                                                         a=p.a), **kw)
    assert r1.field.sf == r2.field.sf and r1.min_sf == r2.min_sf


def test_overlapping_excavations_rejected():
    with pytest.raises(ValueError, match="excavations") as e:
        bem.analyze_bem([bem.rectangle(0, 0, 4, 4), bem.rectangle(1, 1, 4, 4)], sigma1_mpa=30, sigma3_mpa=15,
                        e_mpa=10000, nu=0.2)
    assert "1.0" not in str(e.value)


def test_zero_area_and_too_many_elements():
    with pytest.raises(ValueError, match="excavations"):
        bem.analyze_bem([[(0, 0), (1, 1), (2, 2)]], sigma1_mpa=30, sigma3_mpa=15, e_mpa=10000, nu=0.2)
    with pytest.raises(ValueError, match="max_element_m"):
        bem.analyze_bem([bem.circle(0, 0, 3)], sigma1_mpa=30, sigma3_mpa=15, e_mpa=10000, nu=0.2,
                        max_element_m=0.001)


def test_coarse_pillar_warning_and_min_sf_split():
    mat = bem.BemMaterial("MC", c_mpa=3, phi_deg=30)
    a = bem.rectangle(-4.05, 0, 8, 8, n_per_side=1)
    b = bem.rectangle(4.05, 0, 8, 8, n_per_side=1)
    res = bem.analyze_bem([a, b], sigma1_mpa=30, sigma3_mpa=15, e_mpa=10000, nu=0.2, material=mat, max_element_m=4,
                          points=[(0.0, 0.0), (0.0, 3.9), (0.0, 30.0)])
    w = bem.WARN_COARSE
    assert any(res.field.coarse)
    assert w in res.warnings and res.needs_attention
    assert res.min_sf_coarse is not None


def test_ubc_lab_geometry_runs():
    ex = [[(570, 1050), (571, 1055), (567, 1072), (556, 1085), (545, 1085), (544, 1081), (563, 1055), (565, 1050)],
          [(600, 1015), (600, 1025), (595, 1036), (583, 1036), (582, 1032), (595, 1015)],
          [(531, 1048), (538, 1048), (538, 1052), (531, 1052)],
          [(531, 1012), (538, 1012), (538, 1016), (531, 1016)]]
    mat = bem.BemMaterial("HB", sigma_ci_mpa=40, mb=5, s=0.02, a=0.503)
    res = bem.analyze_bem(ex, sigma1_mpa=40, sigma3_mpa=20, alpha_deg=0, sigma_z_mpa=30, e_mpa=30000, nu=0.2,
                          material=mat)
    assert res.min_sf is not None and math.isfinite(res.min_sf)


def test_default_element_size_small_circle_next_to_large_rectangle():
    res = bem.analyze_bem([bem.circle(0, 0, 1), bem.rectangle(30, 0, 40, 20)], sigma1_mpa=30, sigma3_mpa=15,
                          e_mpa=10000, nu=0.2, points=[(10.0, 10.0)])
    assert res.field.x == [10.0]


def test_grid_non_integer_is_value_error_naming_grid():
    with pytest.raises(ValueError, match="'grid'"):
        bem.analyze_bem([bem.circle(0, 0, 1)], sigma1_mpa=30, sigma3_mpa=15, e_mpa=10000, nu=0.2,
                        grid=(-3, 3, -3, 3, 10.5, 10))
