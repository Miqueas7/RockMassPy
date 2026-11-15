import math

import pytest

import rockmasspy as rm


def test_kirsch():
    b = rm.kirsch_boundary(30, 1)
    assert b.crown_mpa == pytest.approx(60) and b.sidewall_mpa == pytest.approx(60)
    s = rm.kirsch_stress(30, 1, 1, 1, 0)
    assert s.sigma_r == pytest.approx(0, abs=1e-9) and s.sigma_theta == pytest.approx(60)
    b = rm.kirsch_boundary(10, 0.5)
    assert (b.crown_mpa, b.sidewall_mpa) == (pytest.approx(5), pytest.approx(25))
    assert rm.kirsch_stress(10, 0.5, 2, 3, 90).tau_r_theta == pytest.approx(0, abs=1e-9)
    assert s.info.method_id == "Kirsch-1898"
    with pytest.raises(ValueError, match="r_m"):
        rm.kirsch_stress(10, 1, 2, 1.5, 0)


def test_ellipse():
    assert rm.ellipse_boundary_stress(20, 10, 1, 1, 0) == pytest.approx(50)
    assert rm.ellipse_boundary_stress(20, 10, 1, 1, 90) == pytest.approx(10)
    for th in (0.0, math.degrees(0.3), math.degrees(0.9), 90.0):
        assert rm.ellipse_boundary_stress(20, 10, 1, 2, th) == pytest.approx(30)
    e = rm.ellipse_ends(20, 0.5, 4, 2)
    assert e.sidewall_mpa == pytest.approx(90) and e.crown_mpa == pytest.approx(0, abs=1e-9)
    with pytest.raises(ValueError, match="b_m"):
        rm.ellipse_boundary_stress(20, 10, 1, 0, 0)


def test_einstein_schwartz():
    def run(theta):
        i = rm.EinsteinSchwartzInput()
        i.sigma_v_mpa, i.k_ratio, i.e_rock_mpa, i.nu_rock = 15, 2, 6000, 0.2
        i.e_lining_mpa, i.nu_lining, i.thickness_m, i.radius_m, i.theta_deg = 20000, 0.2, 0.5, 2.5, theta
        return rm.einstein_schwartz(i)

    r = run(0)
    assert r.c_star == pytest.approx(1.5) and r.f_star == pytest.approx(450)
    for th, n, m in ((0, 14.61, -0.703), (45, 25.61, 0.0), (90, 36.62, 0.703)):
        r = run(th)
        assert r.n_mn == pytest.approx(n, abs=0.01) and r.m_mnm == pytest.approx(m, abs=0.001)
    assert r.info.method_id == "Lining-Einstein-Schwartz-1979"
    with pytest.raises(ValueError, match="sigma_v_mpa"):
        rm.einstein_schwartz(rm.EinsteinSchwartzInput())


def test_hoek_marinos():
    s = rm.hoek_marinos(0.6, 4, 0, 2)
    assert s.plastic_radius_m == pytest.approx(7.37, abs=0.01)
    assert s.strain_pct == pytest.approx(8.89, abs=0.01)
    assert s.wall_displacement_m == pytest.approx(0.178, abs=0.001)
    assert s.squeezing_class == "D" and s.in_fit_range
    s = rm.hoek_marinos(0.6, 4, 1, 2)
    assert s.strain_pct == pytest.approx(1.96, abs=0.01) and s.squeezing_class == "B"
    assert not rm.hoek_marinos(2.4, 4, 0, 2).in_fit_range
    assert s.info.method_id == "Squeezing-Hoek-Marinos-2000"
    with pytest.raises(ValueError, match="p0_mpa"):
        rm.hoek_marinos(1, 0, 0, 2)
    with pytest.raises(ValueError, match="pi_mpa"):
        rm.hoek_marinos(1, 4, -1, 2)
