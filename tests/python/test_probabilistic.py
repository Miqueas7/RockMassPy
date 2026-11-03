import math
import random

import pytest
from hypothesis import given, settings, strategies as st

import rockmasspy as rm
from rockmasspy import probabilistic as pb
from rockmasspy.probabilistic import (exponential, is_failure, normal, run_probabilistic, sample, summarize_fs,
                                      uniform)

from test_wedge_core import cu2


def smp_base():
    i = rm.PlanarInput()
    i.height_m, i.face_dip_deg, i.plane_dip_deg, i.unit_weight, i.water_unit_weight = 60, 50, 35, 2.6, 1.0
    i.cohesion, i.friction_deg, i.tension_crack_distance_m = 10, 35, 15.3
    return i


SMP_VARS = {"friction_deg": normal(35, 5, 15, 70), "cohesion": normal(10, 2, 0, 25),
            "tension_crack_distance_m": normal(15.3, 4, 0, 35.3429), "water_fill": exponential(0.5, 0, 1),
            "kh": exponential(0.08, 0, 0.16)}


# Tolerancias de VALIDACION §0: con p = 0.064 y n = 5 000 la desviación binomial de la PoF es 0.35 puntos; 1.5 puntos
# son unas 4 desviaciones y cubren además lo que el texto no fija (forma exacta del truncamiento de RocPlane). La
# media tiene error estándar 0.0033 y su ±0.02 cubre el redondeo publicado.
@pytest.mark.parametrize("sampling,seed", [("lhs", s) for s in range(1, 6)] + [("monte_carlo", 1), ("monte_carlo", 2)])
def test_sau_mau_ping(sampling, seed):
    r = run_probabilistic("planar", smp_base(), SMP_VARS, n=5000, sampling=sampling, seed=seed)
    assert r.fs_mean == pytest.approx(1.34, abs=0.02)
    assert r.fs_sd == pytest.approx(0.23, abs=0.02)
    assert r.pof * 100 == pytest.approx(6.4, abs=1.5)
    assert r.fs_min < 0.8 and r.fs_max > 2.0
    assert r.info.verification == rm.Verification.Secondary and r.n_valid == 5000
    assert r.variables == tuple(sorted(SMP_VARS))


def test_reproducible_and_base_untouched():
    base = smp_base()
    before = repr(base)
    a = run_probabilistic("planar", base, SMP_VARS, n=300, seed=7)
    b = run_probabilistic("planar", base, SMP_VARS, n=300, seed=7)
    c = run_probabilistic("planar", base, SMP_VARS, n=300, seed=8)
    assert a.fs == b.fs and a.fs != c.fs and repr(base) == before


def test_lhs_stratification():
    s = sample({"b": uniform(0, 1), "a": uniform(0, 1)}, 50, sampling="lhs", seed=3)
    assert list(s) == ["a", "b"]
    for v in s.values():
        assert sorted(math.floor(u * 50) for u in v) == list(range(50))
    ranks = [[math.floor(u * 50) for u in v] for v in s.values()]
    assert ranks[0] != ranks[1]  # permutaciones independientes por variable


def test_sample_errors():
    for kw in ({"n": 0}, {"n": 5, "seed": -1}, {"n": 5, "sampling": "sobol"}, {"n": 2.5}):
        with pytest.raises(ValueError):
            sample({"a": uniform(0, 1)}, **kw)


@given(st.floats(0, 1), st.floats(0, 1))
@settings(max_examples=100)
def test_ppf_bounded_monotone(u, v):
    for d in (normal(5, 2, 1, 9), exponential(0.5, 0, 1), uniform(-2, 3)):
        lo, hi = sorted((u, v))
        assert d.minimum <= d.ppf(lo) <= d.ppf(hi) <= d.maximum


def test_ppf_values():
    assert normal(0, 1, -1, 1).ppf(0.5) == pytest.approx(0, abs=1e-12)
    assert exponential(0.5, 0, 1).ppf(1 - 1e-12) <= 1
    d = exponential(0.5, 0, 1)
    rng = random.Random(4)
    assert sum(d.ppf(rng.random()) for _ in range(20000)) / 20000 == pytest.approx(0.3435, abs=0.01)


def test_indices():
    r = summarize_fs([0.9, 1.1, 1.3], model="planar", sampling="lhs", n=3, seed=1, variables=())
    assert (r.fs_mean, r.fs_sd, r.reliability_index) == pytest.approx((1.1, 0.2, 0.5))
    assert r.pof == pytest.approx(1 / 3) and r.reliability_index_lognormal > 0
    assert is_failure(1.0) and is_failure(1 + 1e-12) and not is_failure(1 + 1e-6)
    r = summarize_fs([1.0000000000000002] * 4, model="planar", sampling="lhs", n=4, seed=1, variables=())
    assert r.pof == 1 and r.n_failed == 4 and r.reliability_index is None


@pytest.mark.parametrize("make", [lambda: normal(35, 0, 15, 70), lambda: uniform(2, 2),
                                  lambda: normal(80, 5, 15, 70), lambda: normal(0, 1, 50, 60),
                                  lambda: exponential(0, 0, 1), lambda: exponential(2, 0, 1),
                                  lambda: normal(float("nan"), 1, 0, 2), lambda: exponential(0.5, -1, 1)])
def test_bad_distributions(make):
    with pytest.raises(ValueError) as e:
        make()
    assert "Received" not in str(e.value)


def test_sampled_value_out_of_domain():
    with pytest.raises(ValueError) as e:
        run_probabilistic("planar", smp_base(), {"friction_deg": uniform(80, 95)}, n=50)
    m = str(e.value)
    assert "variable 'friction_deg'" in m and "Received" not in m
    assert not any(ch.isdigit() for ch in m.split("variable 'friction_deg'")[1])


def test_wedge_detach_counts_as_failure():
    base = cu2()
    r = run_probabilistic("wedge", base, {"joint1.water_pressure": uniform(0, 0.1)}, n=200)
    assert r.n_valid == 200 and 0 in r.fs and r.n_failed > 0 and r.pof > 0
    assert repr(base) == repr(cu2())
    assert run_probabilistic("wedge", base, {"joint2.friction_deg": uniform(30, 40)}, n=20).n_valid == 20


def test_unformed_planar_samples():
    i = smp_base()
    i.tension_crack_distance_m = 0.0
    r = run_probabilistic("planar", i, {"plane_dip_deg": uniform(45, 55)}, n=400)
    assert 0 < r.fs.count(None) < 400 and r.n_valid == 400 - r.fs.count(None)
    k = r.fs.count(None)
    assert any(n.startswith(f"{k} of 400 samples do not form a block (planar block not formed") for n in r.notes)
    assert r.n == 400 and r.n_valid < r.n and r.pof == r.n_failed / r.n_valid


def test_infinite_fs_and_n1():
    i = smp_base()
    i.bolt_force, i.bolt_plunge_deg = 1e12, 30
    r = run_probabilistic("planar", i, {"cohesion": uniform(5, 15)}, n=10)
    assert r.fs_mean is None and r.n_failed == 0 and r.pof == 0
    assert any("counted as stable and left out of the FS statistics" in n for n in r.notes)
    r = run_probabilistic("planar", smp_base(), {"cohesion": uniform(5, 15)}, n=1)
    assert r.fs_sd is None and r.reliability_index is None and r.n_valid == 1
    r = summarize_fs([None, None], model="planar", sampling="lhs", n=2, seed=1, variables=())
    assert r.pof is None and "no valid samples" in r.warnings


def test_toppling_runs():
    from test_toppling_core import ex1
    r = run_probabilistic("toppling", ex1(), {"friction_deg": normal(38, 3, 25, 50)}, n=100)
    assert r.n_valid == 100 and r.fs_mean > 0


def test_unknown_names_and_model():
    with pytest.raises(ValueError) as e:
        run_probabilistic("planar", smp_base(), {"friccion": uniform(0, 1)}, n=5)
    assert "friction_deg" in str(e.value) and "friccion" not in str(e.value)
    with pytest.raises(ValueError):
        run_probabilistic("wedge", cu2(), {"joint3.cohesion": uniform(0, 1)}, n=5)
    with pytest.raises(ValueError):
        run_probabilistic("nope", smp_base(), {}, n=5)
    with pytest.raises(ValueError):
        run_probabilistic("planar", smp_base(), SMP_VARS, n=5, sampling="sobol")


def test_wedge_joint_variable_named_without_value():
    with pytest.raises(ValueError) as e:
        run_probabilistic("wedge", cu2(), {"joint1.friction_deg": uniform(95, 99)}, n=5)
    m = str(e.value)
    assert m.startswith("variable 'joint1.friction_deg':") and "Received" not in m
    assert not any(ch.isdigit() for ch in m.replace("joint1", ""))


def test_error_not_blamed_on_unsampled_field():
    i = smp_base()
    i.friction_deg = 95.0  # campo fijo malo; la variable muestreada es otra
    with pytest.raises(ValueError) as e:
        run_probabilistic("planar", i, {"cohesion": uniform(5, 15)}, n=5)
    assert "variable" not in str(e.value) and "Received" not in str(e.value)


def test_core_warnings_aggregated():
    r = run_probabilistic("wedge", cu2(), {"joint1.water_pressure": uniform(0, 0.1)}, n=500)
    k = sum(1 for f in r.fs if f == 0)
    assert 0 < k < 500 and f"wedge lifts off both joints ({k} of 500 samples)" in r.warnings
    i = smp_base()
    i.water_fill = 1.0
    r = run_probabilistic("planar", i, {"water_unit_weight": uniform(1, 10)}, n=200)
    w = [x for x in r.warnings if x.startswith("effective normal force on the plane is negative")]
    assert len(w) == 1 and w[0].endswith(" of 200 samples)") and "Received" not in w[0]


def test_toppling_notes_and_grouped_counts():
    from test_toppling_core import ex1
    r = run_probabilistic("toppling", ex1(60, 0.0), {"support_force": uniform(0, 1e9)}, n=100)
    assert any(n.startswith("toppling FS above N (") and n.endswith(" of 100 samples)") for n in r.notes)
    i = ex1(20, 0.0)
    i.base_dip_deg = 60
    r = run_probabilistic("toppling", i, {"friction_deg": uniform(15, 25)}, n=60)
    assert r.warnings and all(w.endswith(" of 60 samples)") for w in r.warnings)
    assert len(set(r.warnings)) == len(r.warnings)
    from rockmasspy.probabilistic import _norm
    assert _norm("fail in 12 blocks") == _norm("fail in 5 blocks") == "fail in N blocks"


def test_sampling_an_unset_optional_field():
    i = smp_base()
    i.tension_crack_distance_m = None
    r = run_probabilistic("planar", i, {"tension_crack_distance_m": uniform(5, 20)}, n=30)
    assert r.n_valid == 30 and i.tension_crack_distance_m is None


def test_distribution_rejects_foreign_params():
    with pytest.raises(ValueError):
        pb.Distribution("uniform", 0, 1, mean=5)
    with pytest.raises(ValueError):
        pb.Distribution("exponential", 0, 1, mean=0.5, sd=1)


def test_clone_keeps_orientations():
    w = pb._clone(cu2())
    assert repr(w) == repr(cu2()) and w.face.dip_direction_deg == 230 and w.external_direction.plunge_deg == 70
