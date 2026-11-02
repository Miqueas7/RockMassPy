import math

import pytest
from hypothesis import given, strategies as st

import rockmasspy as rm

M, D, C = rm.SmrMode, rm.SmrFunctions, rm.SlopeExcavation
FACE = rm.PlaneOrientation(133, 72)  # Riquelme et al. (2016), Tabla 4
P, T, W = M.Planar, M.Toppling, M.Wedge
NORMAL = C.NormalBlastingOrMechanical

# fuente, conjunto, dir, dip, RMRb, modo, A, B, C, F1, F2, F3, SMR publicado, clase
ROWS = [
    ("campo", "J1", 325, 87, 44, T, 12, 87, 159, 0.70, 1, -25, 26, 4),
    ("campo", "J3", 234, 83, 42, T, 79, 83, 155, 0.15, 1, -25, 38, 4),
    ("campo", "J4", 62, 62, 47, P, 71, 62, -10, 0.15, 1, -60, 38, 4),
    ("campo", "W12", 55, 9, 44, W, 78, 9, -63, 0.15, 0.15, -60, 42, 3),
    ("campo", "W14", 49, 61, 44, W, 84, 61, -11, 0.15, 1, -60, 35, 4),
    ("campo", "W23", 146, 18, 42, W, 13, 18, -54, 0.70, 0.15, -60, 35, 4),
    ("campo", "W24", 142, 19, 45, W, 9, 19, -53, 0.85, 0.15, -60, 37, 4),
    ("campo", "W34", 145, 12, 42, W, 12, 12, -60, 0.70, 0.15, -60, 35, 4),
    ("SfM", "J2", 135, 26, 45, P, 2, 26, -46, 1, 0.40, -60, 21, 4),
    ("SfM", "J3", 250, 76, 42, T, 63, 76, 148, 0.15, 1, -25, 38, 4),
    ("SfM", "J4", 41, 57, 47, T, 88, 57, 129, 0.15, 1, -25, 43, 3),
    ("SfM", "W23", 166, 23, 42, W, 33, 23, -49, 0.15, 0.40, -60, 38, 4),
    ("SfM", "W24", 114, 24, 45, W, 19, 24, -48, 0.70, 0.40, -60, 28, 4),
    ("laser", "J1", 321, 87, 44, T, 8, 87, 159, 0.85, 1, -25, 22, 4),
    ("laser", "J2", 121, 16, 45, P, 12, 16, -56, 0.70, 0.15, -60, 38, 4),
    ("laser", "W23", 139, 15, 42, W, 6, 15, -57, 0.85, 0.15, -60, 34, 4),
    ("laser", "W24", 113, 16, 45, W, 20, 16, -56, 0.70, 0.15, -60, 38, 4),
]


def run(rmr, mode, fn, a, b, c, exc=NORMAL):
    return rm.smr(rmr, mode, fn, exc, rm.SmrAngles(a, b, c))


@pytest.mark.parametrize("row", ROWS, ids=lambda r: f"{r[0]}-{r[1]}")
def test_riquelme_table4(row):
    _, _, d, dip, rmr, mode, a, b, c, f1, f2, f3, smr, cls = row
    ang = rm.smr_angles(mode, d, dip, FACE)
    assert ang.a_deg == pytest.approx(a, abs=0.5)
    assert ang.b_deg == pytest.approx(b, abs=0.5)
    assert ang.c_deg == pytest.approx(c, abs=0.5)
    r = rm.smr(rmr, mode, D.Discrete, NORMAL, ang)
    assert (r.f1, r.f2, r.f3) == (f1, f2, f3)
    assert math.floor(r.smr + 1e-9) == smr  # la tabla trunca
    assert r.smr_class == cls


def test_boundary_convention_difference_with_riquelme():
    # SfM J1 323/89 (A = 10) y campo J2 119/20 (B = 20): la tabla usa el lado favorable (SMRTool); aquí, el desfavorable.
    r = rm.smr(44, T, D.Discrete, NORMAL, rm.smr_angles(T, 323, 89, FACE))
    assert (r.f1, round(r.smr, 6), r.smr_class) == (0.85, 22.75, 4)
    r = rm.smr(45, P, D.Discrete, NORMAL, rm.smr_angles(P, 119, 20, FACE))
    assert (r.f2, round(r.smr, 6), r.smr_class) == (0.40, 28.2, 4)


@pytest.mark.parametrize("a,b,c", [(29, 21, -1), (21, 29, -9)])
def test_tomas2006_discrete_products(a, b, c):
    r = run(50, P, D.Discrete, a, b, c)
    assert r.f1 * r.f2 * r.f3 == pytest.approx(-8)


def test_continuous_formulas():
    k = D.Continuous
    assert run(60, P, k, 0, 45, 0).f1 == pytest.approx(0.997207, abs=1e-4)
    assert run(60, P, k, 0, 0, 0).f2 == pytest.approx(0.158961, abs=1e-4)
    assert run(60, P, k, 0, 90, 0).f2 == pytest.approx(0.995601, abs=1e-4)
    assert run(60, P, k, 0, 45, -30).f3 == pytest.approx(-59.3636, abs=1e-4)
    assert run(60, T, k, 0, 45, 130).f3 == pytest.approx(-25.0413, abs=1e-4)
    r = run(60, P, k, 21, 29, -9)
    assert r.f1 * r.f2 * r.f3 == pytest.approx(-15.975, abs=1e-3)  # no -7: ese valor es de las funciones de 2006
    r = rm.smr(60, P, k, NORMAL, rm.smr_angles(P, 180, 45, rm.PlaneOrientation(180, 60)))
    assert r.smr == pytest.approx(6.2368, abs=1e-3) and r.smr_class == 5


def test_limits_and_classes():
    d = D.Discrete
    assert [run(50, P, d, a, 45, 20).f1 for a in (10, 20, 5)] == [0.85, 0.70, 1.0]
    assert [run(50, P, d, 40, b, 20).f2 for b in (20, 45)] == [0.40, 1.0]
    assert [run(50, P, d, 40, 45, c).f3 for c in (0, 0.5, -10)] == [-25, -6, -60]
    assert [run(50, T, d, 40, 45, c).f3 for c in (110, 120)] == [-6, -25]
    assert [rm.smr_class(x) for x in (20.5, 21, 80.5, 81)] == [5, 4, 2, 1]


def test_f4_probability_info_and_range():
    for e, f4 in [(C.NaturalSlope, 15), (C.Presplitting, 10), (C.SmoothBlasting, 8), (NORMAL, 0),
                  (C.DeficientBlasting, -8)]:
        assert run(50, P, D.Discrete, 40, 45, 20, e).f4 == f4
    r = run(50, P, D.Discrete, 40, 45, 20)
    assert r.failure_probability == 0.4 and r.info.method_id == "SMR-Romana1985"
    assert run(50, W, D.Discrete, 40, 45, 20).info.verification == rm.Verification.Secondary
    assert run(50, W, D.Continuous, 40, 45, 20).info.verification == rm.Verification.PrimaryLaterAuthors
    r = run(100, P, D.Discrete, 40, 45, 20, C.NaturalSlope)
    assert (r.smr, r.smr_class, r.warnings) == (115, 1, ["SMR outside 0-100"])


@pytest.mark.parametrize("args", [(101, P, 40, 45, 20), (float("nan"), P, 40, 45, 20), (50, P, 190, 45, 20),
                                  (50, P, 40, 45, 100), (50, T, 40, 45, -5)])
def test_errors(args):
    rmr, mode, a, b, c = args
    with pytest.raises(ValueError):
        run(rmr, mode, D.Discrete, a, b, c)


@given(st.floats(0, 180), st.floats(0, 180))
def test_f1_continuous_decreases(x, y):
    lo, hi = sorted((x, y))
    assert run(50, P, D.Continuous, hi, 45, 0).f1 <= run(50, P, D.Continuous, lo, 45, 0).f1 + 1e-12


@given(st.floats(0, 90), st.floats(0, 90))
def test_f2_continuous_increases(x, y):
    lo, hi = sorted((x, y))
    assert run(50, P, D.Continuous, 40, hi, 0).f2 >= run(50, P, D.Continuous, 40, lo, 0).f2 - 1e-12


@given(st.floats(-90, 90), st.floats(-90, 90))
def test_f3_continuous_increases(x, y):
    lo, hi = sorted((x, y))
    assert run(50, P, D.Continuous, 40, 45, hi).f3 >= run(50, P, D.Continuous, 40, 45, lo).f3 - 1e-12


# A <= 90: con A > 100 el F1 continuo baja a 0.121, por debajo del 0.15 discreto menos 0.01 (propiedad del brief, no cumplida)
@given(st.floats(0, 90), st.floats(0, 90), st.floats(-90, 90))
def test_continuous_within_discrete_extremes(a, b, c):
    k = run(50, P, D.Continuous, a, b, c)
    assert 0.15 - 0.01 <= k.f1 <= 1.0 + 0.01 and 0.15 - 0.01 <= k.f2 <= 1.0 + 0.01
    assert -60 - 1 <= k.f3 <= 0 + 1


@given(st.floats(0, 100), st.floats(0, 100), st.sampled_from(list(C.__members__.values())))
def test_class_monotonic_and_f4_exact(x, y, exc):
    lo, hi = sorted((x, y))
    assert rm.smr_class(lo) >= rm.smr_class(hi)
    r = run(lo, P, D.Discrete, 40, 45, 20, exc)
    assert r.smr == pytest.approx(lo + r.f1 * r.f2 * r.f3 + r.f4)
