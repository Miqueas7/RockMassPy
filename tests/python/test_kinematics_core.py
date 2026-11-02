import random

import pytest
from hypothesis import assume, given, strategies as st

import rockmasspy as rm

P = rm.PlaneOrientation


def kin(phi=30, lim=20, face=(180, 60)):
    return rm.KinematicInput(P(*face), phi, lim)


def test_conjunto_generado():
    rng = random.Random(20261102)
    planes = [P(rng.uniform(170, 190), rng.uniform(40, 55)) for _ in range(40)]
    planes += [P(rng.uniform(350, 370) % 360, rng.uniform(65, 80)) for _ in range(30)]
    planes += [P(rng.uniform(0, 360), 10) for _ in range(30)]
    groups = [0] * 40 + [1] * 30 + [2] * 30
    r = rm.kinematic_analysis(planes, groups, kin())
    assert (r.planar, r.flexural_toppling, r.n_planes) == (40, 30, 100)
    assert r.n_intersections + r.n_parallel_pairs == 40 * 30 + 40 * 30 + 30 * 30
    assert len(r.pair_a) == len(r.pair_b) == r.n_intersections
    assert all(m.verification == rm.Verification.Secondary for m in r.methods)


def test_largos_distintos_y_campos():
    for bad, field in [(kin(0), "friction_deg"), (kin(90), "friction_deg"), (kin(lim=0), "lateral_limit_deg"),
                       (kin(lim=90), "lateral_limit_deg"), (kin(face=(180, 0)), "dip_deg")]:
        with pytest.raises(ValueError, match=field):
            rm.check_plane(P(180, 45), bad)
    with pytest.raises(ValueError, match="groups"):
        rm.kinematic_analysis([P(0, 10)], [0, 1], kin())


planes_st = st.lists(st.tuples(st.integers(0, 360), st.integers(0, 90)), min_size=2, max_size=12)
face_st = st.tuples(st.integers(0, 360), st.integers(1, 90))


def counts(r):
    return (r.planar, r.planar_no_limits, r.flexural_toppling, r.base_zone_1, r.base_zone_2, r.base_zone_3,
            r.n_intersections, r.wedge_primary, r.wedge_secondary, r.direct_toppling, r.direct_toppling_oblique)


@given(pl=planes_st, face=face_st, phi=st.integers(1, 89), lim=st.integers(1, 89), rot=st.integers(0, 360))
def test_giro_no_cambia_conteos(pl, face, phi, lim, rot):
    assume(face not in pl)  # un plano igual a la cara cae justo en su círculo: el límite queda al ruido de coma flotante
    a = rm.kinematic_analysis([P(d, b) for d, b in pl], [-1] * len(pl), kin(phi, lim, face))
    rotated = [P((d + rot) % 360, b) for d, b in pl]
    b = rm.kinematic_analysis(rotated, [-1] * len(pl), kin(phi, lim, ((face[0] + rot) % 360, face[1])))
    assert counts(a) == counts(b)


@given(pl=planes_st, face=face_st, phi=st.integers(1, 88), lim=st.integers(1, 88))
def test_monotonia_e_exclusiones(pl, face, phi, lim):
    ps = [P(d, b) for d, b in pl]
    g = [-1] * len(ps)
    base = rm.kinematic_analysis(ps, g, kin(phi, lim, face))
    more_phi = rm.kinematic_analysis(ps, g, kin(phi + 1, lim, face))
    more_lim = rm.kinematic_analysis(ps, g, kin(phi, lim + 1, face))
    assert more_phi.planar <= base.planar and more_phi.wedge_primary <= base.wedge_primary
    assert more_lim.planar >= base.planar and more_lim.flexural_toppling >= base.flexural_toppling
    assert all(c.planar <= c.planar_no_limits for c in base.planes)
    assert all(not (c.wedge_primary and c.wedge_secondary) for c in base.intersections)
    assert all(not (c.direct_toppling and c.direct_toppling_oblique) for c in base.intersections)
