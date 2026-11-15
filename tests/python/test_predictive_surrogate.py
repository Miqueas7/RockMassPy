"""Sustituto (Fase 8D, tarea 1): datos, poly2, RBF y dominio. Solo datos sintéticos."""

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from scipy.stats import qmc  # noqa: E402

from rockmasspy.predictive import SurrogateData, fit_surrogate, load_runs  # noqa: E402


def _f(X):
    a, b = X[:, 0], X[:, 1]
    return 1 + 2 * a - b + 0.5 * a ** 2 + 0.3 * a * b


def _lhs(n, seed=0, p=3):
    return qmc.scale(qmc.LatinHypercube(d=p, seed=seed).random(n), [0, 0, 0], [10, 5, 2])


@pytest.fixture
def data():
    X = _lhs(40)
    return SurrogateData(X, _f(X), ("a", "b", "c"))


def test_poly2_reproduces_quadratic(data):
    s = fit_surrogate(data, kind="poly2")
    Xt = _lhs(200, seed=1)
    pr = s.predict(Xt)
    assert pr.in_domain.sum() > 100
    assert np.allclose(pr.y[pr.in_domain], _f(Xt)[pr.in_domain], atol=1e-9)
    assert s.kind == "poly2" and s.names == ("a", "b", "c") and s.info.method_id == "Surrogate-poly2"


def test_rbf_interpolates_and_is_accurate(data):
    s = fit_surrogate(data, kind="rbf")
    assert np.allclose(s.predict(data.X).y, data.y, atol=1e-8)
    Xt = _lhs(100, seed=2)
    Xt = Xt[np.all((Xt > [2, 1, 0.4]) & (Xt < [8, 4, 1.6]), axis=1)]
    y = s.predict(Xt).y
    assert np.abs(y - _f(Xt)).max() <= 0.02 * np.ptp(data.y)  # 2 % del rango de la salida


def test_extrapolation_refused(data):
    s = fit_surrogate(data)
    pr = s.predict([[5.0, 2.5, 1.0], [5.0, 2.5, 2.3], [11.0, 2.5, 1.0]])
    assert list(pr.in_domain) == [True, False, False]
    assert np.isfinite(pr.y[0]) and np.isnan(pr.y[1:]).all()


def test_correlated_corner_out_of_domain():
    rng = np.random.default_rng(0)
    a = rng.uniform(0, 10, 60)
    X = np.column_stack([a, a + rng.normal(0, 0.2, 60)])
    s = fit_surrogate(SurrogateData(X, X.sum(axis=1), ("a", "b")))
    pr = s.predict([[a.max(), a.min()], [5, 5]])
    assert list(pr.in_domain) == [False, True] and np.isnan(pr.y[0])


def test_errors_without_values(data):
    with pytest.raises(ValueError, match="runs"):
        fit_surrogate(SurrogateData(data.X[:7], data.y[:7], data.names))
    X = data.X.copy()
    X[:, 1] = 3.0
    with pytest.raises(ValueError, match="column 'b'"):
        fit_surrogate(SurrogateData(X, data.y, data.names))
    with pytest.raises(ValueError, match="names"):
        SurrogateData(data.X, data.y, ("a", "a", "c"))
    with pytest.raises(ValueError, match="kind"):
        fit_surrogate(data, kind="x")


def test_load_runs_csv_comma_decimal(tmp_path):
    f = tmp_path / "corridas.csv"
    rows = ["escenario;c;phi;fs"] + [f"{'E1' if i < 8 else 'E2'};1,{i};{20 + i};{'' if i == 3 else f'1,{i + 10}'}"
                                     for i in range(14)]
    f.write_text("\n".join(rows), encoding="utf-8")
    d = load_runs(f, sheet="corridas", output="fs", group="escenario")
    assert d.names == ("c", "phi") and d.X.shape == (13, 2) and len(d.groups) == 13
    assert set(d.groups) == {"E1", "E2"} and d.X[0, 0] == pytest.approx(1.0)
    assert d.notes == ("runs without a finite output ignored",)
    assert load_runs(f, sheet="corridas", output="fs", inputs=["phi"]).names == ("phi",)


def test_poly2_needs_more_runs_than_terms(data):
    with pytest.raises(ValueError, match="runs.*quadratic"):
        fit_surrogate(SurrogateData(data.X[:8], data.y[:8], data.names))
    assert fit_surrogate(SurrogateData(data.X[:11], data.y[:11], data.names)).kind == "poly2"
    fit_surrogate(SurrogateData(data.X[:8], data.y[:8], data.names), kind="rbf")


def test_rbf_duplicate_rows(data):
    X = data.X[:12].copy()
    X[1] = X[0]
    d = SurrogateData(X, data.y[:12], data.names)
    with pytest.raises(ValueError, match="runs.*smoothing"):
        fit_surrogate(d, kind="rbf")
    assert fit_surrogate(d, kind="rbf", smoothing=1e-3).kind == "rbf"


# ---------- tarea 2: validación agrupada y banco ----------

from rockmasspy.predictive.surrogate import USEFUL_RMSE_RATIO, validate_surrogate  # noqa: E402
from rockmasspy.predictive.surrogate_bench import grc_runs, planar_runs  # noqa: E402


def test_planar_bench_grouped_validation():
    d = planar_runs(300, seed=1)
    assert d.groups is not None and len(set(d.groups)) == 6
    v2, vr = validate_surrogate(d, kind="poly2"), validate_surrogate(d, kind="rbf")
    assert v2.folds_kind == vr.folds_kind == "group_kfold" and v2.n_folds == 5
    assert v2.useful and vr.useful and vr.rmse <= v2.rmse
    assert vr.rmse < 0.2 * vr.rmse_mean_model and USEFUL_RMSE_RATIO == 0.5


def test_no_groups_note_and_leave_one_group_out():
    d = planar_runs(120, seed=3)
    assert validate_surrogate(SurrogateData(d.X, d.y, d.names)).notes == \
        ("no groups given: random folds overestimate accuracy",)
    g3 = SurrogateData(d.X, d.y, d.names, tuple("ABC"[i % 3] for i in range(len(d.y))))
    v = validate_surrogate(g3, k=5)
    assert v.folds_kind == "leave_one_group_out" and v.n_folds == 3


def test_unbalanced_groups():
    d = planar_runs(150, seed=4)
    g = tuple("big" if i < 0.8 * len(d.y) else f"s{i % 4}" for i in range(len(d.y)))
    v = validate_surrogate(SurrogateData(d.X, d.y, d.names, g), kind="rbf")
    assert all(np.isfinite(x) for x in (v.rmse, v.mae, v.max_abs_error, v.r2, v.rmse_mean_model))


def test_grc_bench_rbf_useful():
    v = validate_surrogate(grc_runs(200, seed=2), kind="rbf")
    assert v.useful and 0 <= v.ood_fraction < 0.05


def test_validation_deterministic_and_small_fold_error():
    d = planar_runs(100, seed=5)
    assert validate_surrogate(d, seed=7) == validate_surrogate(d, seed=7)
    with pytest.raises(ValueError, match="runs"):
        validate_surrogate(SurrogateData(d.X[:14], d.y[:14], d.names), kind="poly2")
