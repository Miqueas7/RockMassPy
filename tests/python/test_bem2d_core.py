import math

import pytest

import rockmasspy as rm


def ellipse_pts(n, a, b, cx=0.0, cy=0.0):
    """Nodos en ángulo paramétrico uniforme; el punto medio del elemento 0 queda en t = 0."""
    ts = [2 * math.pi * (k - 0.5) / n for k in range(n)]
    return [(cx + a * math.cos(t), cy + b * math.sin(t)) for t in ts]


def solve(polys, s1, s3, alpha=90.0, **kw):
    return rm.bem_solve(rm.BemInput(contours=[rm.BemContour(vertices=p) for p in polys], sigma1_mpa=s1,
                                    sigma3_mpa=s3, alpha_deg=alpha, e_mpa=10000, nu=0.2, max_element_m=10, **kw))


def test_kirsch_boundary():
    b = rm.bem_boundary(solve([ellipse_pts(128, 1, 1)], 30, 30))
    assert all(abs(s - 60) <= 0.6 for s in b.sigma_tt_mpa)
    b = rm.bem_boundary(solve([ellipse_pts(128, 1, 1)], 30, 15))
    k = rm.kirsch_boundary(30, 0.5)
    assert b.sigma_tt_mpa[0] == pytest.approx(k.sidewall_mpa, abs=0.75)  # 3σv − σh
    assert b.sigma_tt_mpa[32] == pytest.approx(k.crown_mpa, abs=0.75)  # 3σh − σv


@pytest.mark.parametrize("k", [1.0, 0.5])
def test_kirsch_field(k):
    sol = solve([ellipse_pts(64, 1, 1)], 30, 30 * k)
    for r in (1.5, 2.0):
        ths = [2 * math.pi * i / 72 for i in range(72)]
        f = rm.bem_field(sol, [(r * math.cos(t), r * math.sin(t)) for t in ths])
        err = smax = 0.0
        for p, t in zip(f, ths):
            ex = rm.kirsch_stress(30, k, 1, r, math.degrees(t))
            c, s = math.cos(t), math.sin(t)
            sr = p.sxx * c * c + p.syy * s * s + 2 * p.sxy * s * c
            st = p.sxx * s * s + p.syy * c * c - 2 * p.sxy * s * c
            err = max(err, abs(sr - ex.sigma_r), abs(st - ex.sigma_theta))
            smax = max(smax, abs(ex.sigma_theta))
        assert err / smax < 0.006


def test_ellipse():
    sol = solve([ellipse_pts(256, 2, 1)], 20, 10)
    b = rm.bem_boundary(sol)
    assert b.sigma_tt_mpa[0] == pytest.approx(90.98, abs=0.1)
    assert b.sigma_tt_mpa[64] == pytest.approx(0.05, abs=0.05)
    for k in range(16, 256, 32):  # 8 puntos intermedios; la función de Inglis recibe el ángulo polar
        th = math.degrees(math.atan2(b.y[k], b.x[k]))
        assert b.sigma_tt_mpa[k] == pytest.approx(rm.ellipse_boundary_stress(20, 10, 2, 1, th), abs=0.015 * 90)
    assert sol.info.method_id == "BEM-DDM-Crouch-Starfield-1983"
    assert sol.info.verification == rm.Verification.Secondary


def test_orientation_and_closing_point():
    ccw = ellipse_pts(128, 1, 1)
    cw = ccw[::-1] + [ccw[-1]]
    a, b = rm.bem_boundary(solve([ccw], 30, 15, 70)), rm.bem_boundary(solve([cw], 30, 15, 70))
    assert len(a.x) == len(b.x) == 128
    for u, v in zip(a.sigma_tt_mpa + a.ux_m + a.x, b.sigma_tt_mpa + b.ux_m + b.x):
        assert u == pytest.approx(v, abs=1e-12)


def test_point_on_boundary():
    poly = ellipse_pts(128, 1, 1)
    sol = solve([poly], 30, 15)
    e = sol.elements[5]
    f = rm.bem_field(sol, [poly[7], (e.xm, e.ym), (0.0, 0.0)])
    for p in f[:2]:
        assert not p.inside and p.corrected
        assert all(math.isfinite(v) for v in (p.sxx, p.syy, p.sxy, p.szz, p.sigma1, p.sigma3, p.angle1_deg))
    assert f[2].inside and math.isnan(f[2].sigma1)


def test_single_contour_not_singular():
    b = rm.bem_boundary(solve([ellipse_pts(256, 1, 1)], 30, 30))
    assert b.sigma_tt_mpa[0] == pytest.approx(60.25, abs=0.05)


def test_errors():
    sq = [(0, 0), (2, 0), (2, 2), (0, 2)]
    for polys, name in [([[(0, 0), (1, 0)]], "vertices"), ([[(0, 0), (2, 2), (2, 0), (0, 2)]], "contours"),
                        ([sq, [(1, 1), (3, 1), (3, 3), (1, 3)]], "contours")]:
        with pytest.raises(ValueError, match=f"'{name}'") as e:
            solve(polys, 30, 15)
        assert "Received" not in str(e.value)
    for kw, name in [({"e_mpa": 0}, "e_mpa"), ({"nu": 0.5}, "nu"), ({"nu": -0.1}, "nu")]:
        args = dict(contours=[rm.BemContour(vertices=sq)], sigma1_mpa=30, sigma3_mpa=15, alpha_deg=90, e_mpa=1e4,
                    nu=0.2, max_element_m=1)
        args.update(kw)
        with pytest.raises(ValueError, match=f"'{name}'") as e:
            rm.bem_solve(rm.BemInput(**args))
        assert "Received" not in str(e.value)
    with pytest.raises(ValueError, match="'alpha_deg'"):
        rm.bem_solve(rm.BemInput(contours=[rm.BemContour(vertices=sq)], sigma1_mpa=30, sigma3_mpa=15, e_mpa=1e4,
                                 nu=0.2, max_element_m=1))


def _pillar(w, el, bw, h):
    rect = lambda x0, x1: [(x0, -h / 2), (x1, -h / 2), (x1, h / 2), (x0, h / 2)]
    sol = rm.bem_solve(rm.BemInput(contours=[rm.BemContour(vertices=rect(-w / 2 - bw, -w / 2)),
                                             rm.BemContour(vertices=rect(w / 2, w / 2 + bw))],
                                   sigma1_mpa=30, sigma3_mpa=15, alpha_deg=90, e_mpa=10000, nu=0.2, max_element_m=el))
    pts = [(-w / 2 - bw - 3 + (w + 2 * bw + 6) * i / 60, 0.0) for i in range(61)]
    pts += [(0.0, -h / 2 + h * i / 20) for i in range(21)]
    return rm.bem_field(sol, pts)


@pytest.mark.parametrize("w,el,bw,h", [(1.0, 1.0, 4.0, 4.0), (0.5, 1.0, 4.0, 4.0), (3.0, 3.0, 5.0, 6.0)])
def test_narrow_pillar_no_nan(w, el, bw, h):
    f = _pillar(w, el, bw, h)
    out = [p for p in f if not p.inside]
    assert all(math.isfinite(v) for p in out for v in (p.sxx, p.syy, p.sxy, p.szz, p.sigma1, p.sigma3))
    assert f[61 + 10].coarse and not f[61 + 10].corrected
    assert not any(p.coarse and p.corrected for p in out)


def test_fine_pillar_unchanged():
    f = _pillar(1.0, 0.25, 4.0, 4.0)
    assert not any(p.coarse for p in f)
    assert f[61 + 10].syy == pytest.approx(81.683, abs=1e-3)


def test_messages_without_values():
    sq = [(0, 0), (2, 0), (2, 2), (0, 2)]
    with pytest.raises(ValueError, match="'e_mpa'") as e:
        rm.bem_solve(rm.BemInput(contours=[rm.BemContour(vertices=sq)], sigma1_mpa=30, sigma3_mpa=15, alpha_deg=90,
                                 e_mpa=float("nan"), nu=0.2, max_element_m=1))
    assert "Received" not in str(e.value)
    with pytest.raises(ValueError, match="'elements_per_side_hint'"):
        rm.bem_discretize([rm.BemContour(vertices=sq, elements_per_side_hint=2000)], 1.0)
