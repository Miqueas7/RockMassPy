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
    assert r.pof is None and "no valid samples" in r.notes and "no valid samples" not in r.warnings


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
    k = sum(1 for f in r.fs if f == 100.0)
    assert r.notes == (f"{k} of 100 samples have FS above the cap; excluded from the statistics",)  # una sola nota
    i = ex1(20, 0.0)
    i.base_dip_deg = 60
    r = run_probabilistic("toppling", i, {"friction_deg": uniform(15, 25)}, n=60)
    assert r.warnings and all(w.endswith(" of 60 samples)") for w in r.warnings)
    assert len(set(r.warnings)) == len(r.warnings)
    from rockmasspy.probabilistic import _norm
    assert _norm("fail in 12 blocks") == _norm("fail in 5 blocks") == "fail in N blocks"
    assert _norm("Goodman-Bray conditions (8)-(9) fail in 3 blocks") == "Goodman-Bray conditions (8)-(9) fail in N blocks"
    assert _norm("toppling FS above 100") == "toppling FS above 100"
    t = "toppling: support is insufficient for any friction coefficient below 1; FS is an upper bound"
    assert _norm(t) == t
    assert all("(N)" not in w for w in r.warnings)


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


# --- ola final de la 3B ------------------------------------------------------------------------------------------

def test_constant_fs_has_no_reliability_index():
    # c = 0 y seco: FS = tan(phi)/tan(psi) no depende de gamma, la desviación es puro ruido (I1)
    i = smp_base()
    i.cohesion, i.friction_deg, i.tension_crack_distance_m = 0.0, 40.0, None
    r = run_probabilistic("planar", i, {"unit_weight": normal(2.6, 0.1, 2.2, 3.0)}, n=500)
    assert r.reliability_index is None and r.reliability_index_lognormal is None
    assert "FS does not vary with the sampled variables; reliability index undefined" in r.notes
    assert r.pof == 0 and r.n_valid == 500
    assert r.fs_mean == pytest.approx(math.tan(math.radians(40)) / math.tan(math.radians(35)), rel=1e-12)
    r = summarize_fs([1.2] * 3, model="planar", sampling="lhs", n=3, seed=1, variables=())
    assert r.reliability_index is None and r.notes == ("FS does not vary with the sampled variables; reliability "
                                                       "index undefined",)


def test_lognormal_index_uses_log1p():
    # con v = 1e-9, log(1 + v²) da 0 y el índice lognormal dividiría por cero; log1p lo resuelve
    r = summarize_fs([2 - 1e-9, 2, 2 + 1e-9], model="planar", sampling="lhs", n=3, seed=1, variables=())
    assert r.reliability_index_lognormal == pytest.approx(math.log(2) / (r.fs_sd / 2), rel=1e-6)


def test_toppling_cap_is_left_out_of_the_statistics():
    from test_toppling_core import ex1
    # el tope (FS 100) llega con soporte de unos 4.24e5: la mitad de las muestras queda en el tope
    r = run_probabilistic("toppling", ex1(60, 0.0), {"support_force": uniform(0, 8.5e5)}, n=200)
    capped = [f for f in r.fs if f >= 100]
    rest = [f for f in r.fs if f < 100]
    assert capped and rest
    assert r.fs_max < 100 and r.fs_mean == pytest.approx(math.fsum(rest) / len(rest))
    assert r.n_failed == sum(is_failure(f) for f in rest) and r.n_valid == 200  # el tope cuenta como estable
    assert r.excluded == tuple(i for i, f in enumerate(r.fs) if f >= 100)
    assert f"{len(capped)} of 200 samples have FS above the cap; excluded from the statistics" in r.notes
    assert r.reliability_index == pytest.approx((r.fs_mean - 1) / r.fs_sd)


def _bounded(phi):
    # sin soporte, el soporte requerido no se anula con ningún mu < 1: el FS es una cota superior
    i = rm.TopplingInput()
    i.heights_m = rm.goodman_bray_heights(16, 10, 5, 5, 0.5)
    i.block_width_m, i.base_dip_deg, i.a1_m, i.a2_m, i.crest_block = 10, 45, 5, 5, 10
    i.unit_weight, i.friction_deg = 25, phi
    return i


def test_toppling_upper_bound_counts_as_failure():
    d = rm.toppling_fs(_bounded(55))
    assert d.fs_bounded and d.factor_of_safety > 1  # la cota no prueba FS > 1
    r = run_probabilistic("toppling", _bounded(55), {"friction_deg": uniform(40, 60)}, n=400)
    assert r.pof == 1 and r.n_failed == 400
    # la cota no es un FS: fuera de la estadística, como el tope (R1)
    assert r.excluded == tuple(range(400)) and r.fs_mean is None and r.fs_min is None and r.reliability_index is None
    assert ("400 of 400 samples have FS only as an upper bound; counted as failures and excluded from the statistics"
            in r.notes)
    assert any(w.startswith("toppling: support is insufficient") and w.endswith("(400 of 400 samples)")
               for w in r.warnings)


@pytest.mark.parametrize("bad", [float("nan"), float("-inf")])
def test_summarize_fs_rejects_nan_and_minus_inf(bad):
    with pytest.raises(ValueError, match=r"^fs: "):
        summarize_fs([1.2, bad], model="planar", sampling="lhs", n=2, seed=1, variables=())
