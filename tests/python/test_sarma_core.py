import math

import pytest

import rockmasspy as rm

from test_limit_equilibrium_core import layer, mc, mirror, pts, section

NAN = float("nan")

# Slide Sarma Verification, problema 4 (Hoek 1987): la masa baja hacia -x; el último tramo de la base se prolonga
# sobre la recta (108, 6.4)-(128, 67) hasta pasar el terreno
P4_SURFACE = [(-50, -2.97), (0, 0), (111.4, 76.5), (229.545, 13.6815), (250, 14.9)]
P4_FLOOR = [(-50, -2.97), (0, 0), (250, 14.9)]
P4_BASE = [(0, 0), (108, 6.4), (130, 6.4 + 22 * 60.6 / 20)]


def problem4(surface=P4_SURFACE, floor=P4_FLOOR):
    return section(surface, [layer(floor, 1), layer([], 0)], [mc(15.7, 10, 6), mc(15.7, 100, 42)])


def sarma_in(base, angles):
    i = rm.SarmaInput()
    i.base, i.interface_angles_deg = pts(base), list(angles)
    return i


def planar_section(h, face, g, c, phi, kh, ru=0.0):
    s = section([(-400, h), (-h / math.tan(math.radians(face)), h), (0, 0), (100, 0)], [layer([], 0)],
                [mc(g, c, phi, ru)])
    s.kh = kh
    return s


def planar_base(h, plane):
    return sarma_in([(-h / math.tan(math.radians(plane)), h), (0, 0)], [])


def planar(h, face, plane, g, c, phi, kh=0.0, fill=0.0, gw=None):
    i = rm.PlanarInput()
    i.height_m, i.face_dip_deg, i.plane_dip_deg, i.unit_weight = h, face, plane, g
    i.cohesion, i.friction_deg, i.kh, i.water_fill, i.water_unit_weight = c, phi, kh, fill, gw
    return rm.planar_fs(i).factor_of_safety


def test_problem4_given_interface():
    r = rm.sarma_fs(problem4(), sarma_in(P4_BASE, [116.5]))
    assert r.factor_of_safety == pytest.approx(1.1977, abs=2e-3)
    assert r.factor_of_safety == pytest.approx(1.198, rel=0.01)
    assert [w.base_material for w in r.wedges] == [0, 1]
    assert r.info.method_id == "Sarma-NonVertical" and r.info.verification == rm.Verification.Secondary


def test_problem4_optimized_and_kc():
    o = rm.SarmaOptions()
    o.optimize_angles = True
    r = rm.sarma_fs(problem4(), sarma_in(P4_BASE, [116.5]), o)
    assert 1.18 <= r.factor_of_safety <= 1.1977 and 100 < r.interface_angles_deg[0] < 130
    g = rm.sarma_fs(problem4(), sarma_in(P4_BASE, [116.5]))
    s = problem4()
    s.kh = g.critical_acceleration
    assert rm.sarma_fs(s, sarma_in(P4_BASE, [116.5])).factor_of_safety == pytest.approx(1.0, abs=1e-6)


def test_reflection_keeps_fs_and_kc():
    a = rm.sarma_fs(problem4(), sarma_in(P4_BASE, [116.5]))
    b = rm.sarma_fs(problem4(mirror(P4_SURFACE), mirror(P4_FLOOR)), sarma_in(mirror(P4_BASE), [63.5]))
    assert b.factor_of_safety == pytest.approx(a.factor_of_safety, abs=1e-9)
    assert b.critical_acceleration == pytest.approx(a.critical_acceleration, abs=1e-9)


def test_one_wedge_is_planar():
    assert rm.sarma_fs(planar_section(60, 50, 0.027, 0.1, 35, 0.08), planar_base(60, 35)).factor_of_safety == \
        pytest.approx(planar(60, 50, 35, 0.027, 0.1, 35, 0.08), abs=1e-6)
    for c, phi, want in [(0, 20, 0.36397), (1.1025, 20, 0.64361), (2.2051, 35, 1.25951)]:
        got = rm.sarma_fs(planar_section(95, 85, 0.18192, c, phi, 0), planar_base(95, 45)).factor_of_safety
        assert got == pytest.approx(planar(95, 85, 45, 0.18192, c, phi), abs=1e-6)
        assert got == pytest.approx(want, abs=1e-5)
    # PL-1 saturado: un ru con ru W / cos ψp = γw H² / (4 sin ψp) da la U de Hoek
    pp = math.radians(35)
    w = 0.5 * 0.027 * 3600 * (1 / math.tan(pp) - 1 / math.tan(math.radians(50)))
    ru = 0.01 * 3600 / (4 * math.sin(pp)) * math.cos(pp) / w
    r = rm.sarma_fs(planar_section(60, 50, 0.027, 0.1, 35, 0.08, ru), planar_base(60, 35))
    assert r.factor_of_safety == pytest.approx(0.818425, abs=1e-6)


@pytest.mark.parametrize("angles,msg", [
    ([30, 120], "interfaces 0 and 1 cross"),
    ([80, 150], "does not cut the ground surface"),
    ([0, 90], "must be within (0, 180)"),
    ([80, 180], "must be within (0, 180)"),
    ([NAN, 90], "interface_angles_deg[0]"),
    ([80], "one angle per interior vertex"),
])
def test_invalid_interfaces(angles, msg):
    s = section([(-100, 50), (-40, 50), (0, 0), (50, 0)], [layer([], 0)], [mc(20, 10, 30)])
    with pytest.raises(ValueError, match=msg.replace("(", r"\(").replace(")", r"\)").replace("[", r"\[")):
        rm.sarma_fs(s, sarma_in([(-90, 50), (-60, 20), (-30, 5), (0, 0)], angles))


def test_inadmissible_and_not_supported():
    with pytest.raises(ValueError, match="inadmissible mechanism at interface 0"):
        rm.sarma_fs(problem4(), sarma_in(P4_BASE, [60]))
    s = problem4()
    s.crack = rm.LeTensionCrack()
    s.crack.depth_m = 5.0
    with pytest.raises(ValueError, match="not supported in Sarma"):
        rm.sarma_fs(s, sarma_in(P4_BASE, [116.5]))
    hb = problem4()
    m = hb.materials
    m[1].model, m[1].hb, m[1].sigma_ci = rm.StrengthModel.HoekBrown, rm.hb_params_from_constants(1, 0.01, 0.5), 1000.0
    hb.materials = m
    with pytest.raises(ValueError, match="not supported in Sarma"):
        rm.sarma_fs(hb, sarma_in(P4_BASE, [116.5]))
