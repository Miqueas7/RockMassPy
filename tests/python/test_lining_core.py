import pytest

import rockmasspy as rm


def section(a, i, t, sc, st):
    s = rm.LiningSection()
    s.area_m2, s.inertia_m4, s.thickness_m, s.sigma_c_mpa, s.sigma_t_mpa = a, i, t, sc, st
    return s


def test_capacity_steel_and_shotcrete():
    st = section(4.75e-3, 2.23e-5, 0.162, 500, -500)
    e = rm.capacity_mn(st, 1)
    assert e.n_max == pytest.approx(2.375, abs=1e-3) and e.m_max == pytest.approx(0.1377, abs=1e-4)
    assert rm.q_crit(st, 1) == pytest.approx(1.583, abs=1e-3)
    assert rm.shear_capacity_n(st, 1.19, 1, True) == pytest.approx(1.033, abs=1e-3)
    sh = section(0.12, 0.0004, 0.2, 40, -5)  # sigma_t = -5: errata de KL08 p. 51
    e = rm.capacity_mn(sh, 2)
    assert (e.n_max, e.n_min, e.n_cr) == (pytest.approx(2.4), pytest.approx(-0.3), pytest.approx(1.05))
    assert len(e.vertices) == 4 and e.info.method_id == "Lining-capacity-Carranza-Torres-Diederichs-2009"
    assert rm.shear_capacity_n(sh, 0.85, 1, False) == pytest.approx(2.109, abs=1e-3)


def test_check_capacity_with_einstein_schwartz():
    s = section(0.5, 0.5**3 / 12, 0.5, 60, -6)
    forces = []
    for th in (0, 45, 90):
        i = rm.EinsteinSchwartzInput()
        i.sigma_v_mpa, i.k_ratio, i.e_rock_mpa, i.nu_rock = 15, 2, 6000, 0.2
        i.e_lining_mpa, i.nu_lining, i.thickness_m, i.radius_m, i.theta_deg = 20000, 0.2, 0.5, 2.5, th
        r = rm.einstein_schwartz(i)
        f = rm.LiningForce()
        f.n_mn, f.m_mnm = r.n_mn, r.m_mnm
        forces.append(f)
    assert rm.check_capacity(s, forces, 1).outside == [2]
    assert not rm.check_capacity(s, forces, 2).all_inside


def test_composite_split_and_errors():
    st, sh = rm.ElasticSection(), rm.ElasticSection()
    st.e_mpa, st.nu, st.area_m2, st.inertia_m4 = 200000, 0.3, 4.75e-3, 2.23e-5
    sh.e_mpa, sh.nu, sh.area_m2, sh.inertia_m4 = 20000, 0.2, 0.12, 0.0004
    c = rm.composite(st, sh, 1 / 0.6, 3)
    f = rm.split_forces(c, 2.0, 0.1, 0.5)
    assert f.n_steel + f.n_shotcrete == pytest.approx(2.0 * 0.6)
    assert f.m_steel + f.m_shotcrete == pytest.approx(0.1 * 0.6)
    with pytest.raises(ValueError, match="sigma_t_mpa"):
        rm.capacity_mn(section(0.12, 0.0004, 0.2, 40, 5), 1)
