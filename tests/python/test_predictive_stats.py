"""Estadística lineal del nivel 1 (Fase 4A, tarea 3). Solo datos sintéticos."""

import ast
import importlib
import sys
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

np = pytest.importorskip("numpy")
student_t = pytest.importorskip("scipy.stats").t

from rockmasspy.predictive import bayes_linear_fit, deming_fit, group_bootstrap, ols_fit  # noqa: E402


def _data(n=40, a=2.0, b=1.0, sd=0.5, seed=1):
    rng = np.random.default_rng(seed)
    x = rng.uniform(-2, 3, n)
    return x, a * x + b + rng.normal(0, sd, n)


# ---------- paquete ----------

def test_sin_scipy_pide_el_extra_ml(monkeypatch):
    monkeypatch.setitem(sys.modules, "scipy", None)
    for mod in ("rockmasspy.predictive", "rockmasspy.predictive.stats"):
        monkeypatch.delitem(sys.modules, mod, raising=False)
    with pytest.raises(ImportError, match=r"install the ml extra: pip install rockmasspy\[ml\]"):
        importlib.import_module("rockmasspy.predictive")


def test_rockmasspy_no_importa_predictive():
    # numpy es opcional: el paquete raíz no puede importar predictive (revisión estática, no depende del entorno)
    import rockmasspy
    tree = ast.parse(Path(rockmasspy.__file__).read_text(encoding="utf-8"))
    names = [a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names]
    modules = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    assert not any("predictive" in s for s in names + modules)


# ---------- OLS ----------

@pytest.mark.parametrize("level", [0.95, 0.80])
def test_ols_contra_statsmodels(level):
    sm = pytest.importorskip("statsmodels.api")
    x, y = _data()
    fit = ols_fit(x, y)
    ref = sm.OLS(y, sm.add_constant(x)).fit()
    assert fit.a == pytest.approx(ref.params[1], rel=1e-10)
    assert fit.b == pytest.approx(ref.params[0], rel=1e-10)
    assert fit.se_a == pytest.approx(ref.bse[1], rel=1e-10)
    assert fit.se_b == pytest.approx(ref.bse[0], rel=1e-10)
    assert fit.r2 == pytest.approx(ref.rsquared, rel=1e-10)
    assert fit.sigma == pytest.approx(np.sqrt(ref.scale), rel=1e-10)
    assert (fit.n, fit.dof) == (40, 38)
    x0 = np.array([-3.0, 0.0, 0.7, 5.0])
    frame = ref.get_prediction(sm.add_constant(x0, has_constant="add")).summary_frame(alpha=1 - level)
    yhat, lo, hi = fit.predict(x0, level=level)
    np.testing.assert_allclose(yhat, frame["mean"], rtol=1e-10)
    np.testing.assert_allclose(lo, frame["obs_ci_lower"], rtol=1e-10)
    np.testing.assert_allclose(hi, frame["obs_ci_upper"], rtol=1e-10)


def test_ols_predict_escalar_devuelve_floats():
    yhat, lo, hi = ols_fit(*_data()).predict(1.0)
    assert all(isinstance(v, float) for v in (yhat, lo, hi)) and lo < yhat < hi


def test_ols_y_constante_r2_nan():
    fit = ols_fit([1, 2, 3, 4], [5, 5, 5, 5])
    assert (fit.a, fit.b, fit.sigma) == (0.0, 5.0, 0.0) and np.isnan(fit.r2)


# ---------- Deming ----------

def test_deming_ratio_1_es_ortogonal():
    x, y = _data(sd=1.0)
    fit = deming_fit(x, y, 1.0)
    a, b = fit.a, fit.b
    centered = np.column_stack([x - x.mean(), y - y.mean()])
    v = np.linalg.svd(centered, full_matrices=False)[2][0]
    assert a == pytest.approx(v[1] / v[0], rel=1e-10)
    assert b == pytest.approx(y.mean() - a * x.mean(), rel=1e-10)


def test_deming_extremos_del_cociente():
    x, y = _data(sd=1.0)
    ols_yx = ols_fit(x, y)
    assert deming_fit(x, y, 1e12).a == pytest.approx(ols_yx.a, rel=1e-8)
    assert deming_fit(x, y, 1e12).b == pytest.approx(ols_yx.b, rel=1e-8)
    ols_xy = ols_fit(y, x)
    assert deming_fit(x, y, 1e-12).a == pytest.approx(1 / ols_xy.a, rel=1e-8)


@pytest.mark.parametrize("ratio", [1e-6, 0.3, 1.0, 7.0, 1e6])
@pytest.mark.parametrize("slope", [3.0, -0.4])
def test_deming_datos_exactos(ratio, slope):
    x = np.linspace(-1, 4, 9)
    fit = deming_fit(x, slope * x - 2.0, ratio)
    assert fit.a == pytest.approx(slope, rel=1e-12) and fit.b == pytest.approx(-2.0, abs=1e-12)


def test_deming_escala_enorme_sin_desborde():
    x, y = _data(sd=1.0)
    ref = deming_fit(x, y, 1.0)
    fit = deming_fit(x * 1e100, y * 1e100, 1.0)
    assert fit.a == pytest.approx(ref.a, rel=1e-10) and fit.b == pytest.approx(ref.b * 1e100, rel=1e-10)


# ---------- bootstrap por grupos ----------

def _grupos(n_groups=30, per=6, seed=0):
    # x casi constante dentro de cada grupo (como una labor) y efecto de grupo: las filas no son independientes
    rng = np.random.default_rng(seed)
    g = np.repeat(np.arange(n_groups), per)
    x = rng.uniform(0, 10, n_groups)[g] + rng.normal(0, 0.5, g.size)
    y = 1.5 * x + 4 + rng.normal(0, 2.0, n_groups)[g] + rng.normal(0, 1.0, g.size)
    return g, x, y


def test_bootstrap_reproducible():
    g, x, y = _grupos()
    stat = lambda i: ols_fit(x[i], y[i]).a  # noqa: E731
    r1 = group_bootstrap(g, stat, n_boot=200, seed=5)
    r2 = group_bootstrap(list(g), stat, n_boot=200, seed=5)
    np.testing.assert_array_equal(r1.replicates, r2.replicates)
    assert not np.array_equal(r1.replicates, group_bootstrap(g, stat, n_boot=200, seed=6).replicates)


def test_bootstrap_solo_grupos_completos():
    sizes = {"L1": 3, "L2": 5, "L3": 7, "L4": 2}
    labels = np.array([k for k, s in sizes.items() for _ in range(s)])
    stat = lambda i: [np.sum(labels[i] == k) / s for k, s in sizes.items()]  # noqa: E731
    res = group_bootstrap(labels, stat, n_boot=300, seed=1)
    assert res.replicates.shape == (300, 4)
    np.testing.assert_array_equal(res.replicates, np.round(res.replicates))  # múltiplos del tamaño del grupo
    np.testing.assert_array_equal(res.replicates.sum(axis=1), 4)  # tantos grupos como hay
    lo, hi = res.percentile_ci()
    assert lo.shape == hi.shape == (4,)


def test_bootstrap_descarta_degeneradas():
    groups = ["A"] * 4 + ["B"] * 4
    x = np.array([1.0] * 4 + [2.0] * 4)  # x constante dentro de cada grupo
    y = np.arange(8.0)
    res = group_bootstrap(groups, lambda i: ols_fit(x[i], y[i]).a, n_boot=200, seed=0)
    assert res.n_discarded > 0 and len(res.replicates) + res.n_discarded == 200
    res_nan = group_bootstrap(groups, lambda i: np.nan, n_boot=10)
    assert res_nan.n_discarded == 10
    with pytest.raises(ValueError, match="no valid bootstrap replicates") as info:
        res_nan.percentile_ci()
    assert "last error" not in str(info.value)


def test_bootstrap_todas_fallan_muestra_el_error_de_la_estadistica():
    # error del usuario (largos distintos) no debe leerse solo como «réplicas degeneradas»
    res = group_bootstrap(["A", "A", "B", "B"], lambda i: ols_fit(np.arange(4.0)[i], [1.0, 2.0]).a, n_boot=5)
    with pytest.raises(ValueError, match="last error from statistic: ValueError: x and y must have the same") as info:
        res.percentile_ci()
    assert isinstance(info.value.__cause__, ValueError)


def test_bootstrap_cubre_la_pendiente_verdadera():
    # con estas semillas: por grupos cubre 37/40; remuestreando filas, solo 25/40 (IC demasiado angosto)
    por_grupo = por_fila = 0
    for seed in range(40):
        g, x, y = _grupos(seed=seed)
        stat = lambda i: ols_fit(x[i], y[i]).a  # noqa: E731
        lo, hi = group_bootstrap(g, stat, n_boot=300, seed=seed).percentile_ci(0.95)
        por_grupo += lo <= 1.5 <= hi
        lo, hi = group_bootstrap(np.arange(g.size), stat, n_boot=300, seed=seed).percentile_ci(0.95)
        por_fila += lo <= 1.5 <= hi
    assert por_grupo >= 36 and por_fila <= 30


# ---------- bayesiano conjugado ----------

PRIOR = dict(prior_mean=(5.0, 40.0), prior_sd=(2.5, 10.0), prior_sigma=6.0)


def test_bayes_prior_debil_tiende_a_ols():
    x, y = _data()
    fit = bayes_linear_fit(x, y, prior_mean=(5.0, 40.0), prior_sd=(1e7, 1e7), prior_sigma=0.5)
    ols = ols_fit(x, y)
    assert fit.a == pytest.approx(ols.a, rel=1e-8) and fit.b == pytest.approx(ols.b, rel=1e-8)


def test_bayes_prior_fuerte_tiende_al_prior():
    x, y = _data()
    fit = bayes_linear_fit(x, y, prior_mean=(5.0, 40.0), prior_sd=(1e-7, 1e-7), prior_sigma=0.5)
    assert fit.a == pytest.approx(5.0, abs=1e-6) and fit.b == pytest.approx(40.0, abs=1e-6)


@pytest.mark.parametrize("n", [0, 1])
def test_bayes_pocos_datos_queda_cerca_del_prior(n):
    x, y = [3.0][:n], [60.0][:n]
    fit = bayes_linear_fit(x, y, **PRIOR)
    assert abs(fit.a - 5.0) < 2.5 and abs(fit.b - 40.0) < 10.0 and fit.n == n
    yhat, lo, hi = fit.predict(2.0)
    assert np.isfinite([lo, hi]).all() and lo < yhat < hi
    if n == 0:
        assert (fit.a, fit.b) == (5.0, 40.0) and fit.alpha == 2.0 and fit.beta == pytest.approx(36.0)


@pytest.mark.parametrize("n", [2, 4])
def test_bayes_se_encoge_entre_ols_y_el_prior(n):
    # OLS lejos del prior (a = 5, b = 40): el ajuste queda estrictamente entre los dos. x centrado → X'X y Λ0
    # diagonales, así el encogimiento vale coordenada a coordenada (con x sin centrar no siempre)
    x = np.array([-1.0, 1.0]) if n == 2 else np.array([-1.5, -0.5, 0.5, 1.5])
    y = np.array([15.0, 5.0]) if n == 2 else np.array([18.0, 12.0, 8.0, 2.0])
    ols = np.polyfit(x, y, 1)
    fit = bayes_linear_fit(x, y, **PRIOR)
    for post, lsq, prior in ((fit.a, ols[0], 5.0), (fit.b, ols[1], 40.0)):
        assert min(lsq, prior) < post < max(lsq, prior)
        assert abs(post - lsq) > 0.01 * abs(prior - lsq) and abs(post - prior) > 0.01 * abs(prior - lsq)


def test_bayes_predictiva_a_priori_exacta():
    # n = 0, α0 = 3: ν = 6 y la varianza t es ν/(ν−2)·escala² = σp² + sa²·x0² + sb² (exacto)
    s, sa, sb = 6.0, 2.5, 10.0
    fit = bayes_linear_fit([], [], prior_mean=(5.0, 40.0), prior_sd=(sa, sb), prior_sigma=s, prior_strength=3.0)
    x0 = np.array([-2.0, 0.0, 1.5, 4.0])
    yhat, lo, hi = fit.predict(x0, level=0.95)
    np.testing.assert_allclose(yhat, 5.0 * x0 + 40.0, rtol=1e-14)
    var = s ** 2 + sa ** 2 * x0 ** 2 + sb ** 2
    np.testing.assert_allclose(hi - yhat, student_t.ppf(0.975, 6) * np.sqrt(var * 4 / 6), rtol=1e-12)
    np.testing.assert_allclose(yhat - lo, hi - yhat, rtol=1e-12)
    assert fit.beta == pytest.approx(2 * s ** 2) and fit.alpha == 3.0


@pytest.mark.parametrize("n", [3, 5])
def test_bayes_posterior_contra_la_forma_clasica(n):
    # oráculo: βn = β0 + ½(y'y + m0'Λ0m0 − mn'Λn·mn) y la predictiva t calculada a mano con Λn⁻¹ completa
    x = np.array([2.0, 3.5, 4.0, 5.5, 7.0][:n])
    y = np.array([20.0, 31.0, 30.0, 45.0, 52.0][:n])
    m0, s, sa, sb, a0 = np.array([5.0, 40.0]), 6.0, 2.5, 10.0, 3.0
    fit = bayes_linear_fit(x, y, prior_mean=tuple(m0), prior_sd=(sa, sb), prior_sigma=s, prior_strength=a0)
    X = np.column_stack([x, np.ones(n)])
    lam0 = np.diag([s ** 2 / sa ** 2, s ** 2 / sb ** 2])
    lam_n = X.T @ X + lam0
    mn = np.linalg.solve(lam_n, X.T @ y + lam0 @ m0)
    alpha_n = a0 + n / 2
    beta_n = s ** 2 * (a0 - 1) + 0.5 * (y @ y + m0 @ lam0 @ m0 - mn @ lam_n @ mn)
    np.testing.assert_allclose([fit.a, fit.b], mn, rtol=1e-12)
    assert fit.alpha == alpha_n and fit.beta == pytest.approx(beta_n, rel=1e-10)
    for x0 in (0.0, 3.0, 10.0):
        xt = np.array([x0, 1.0])
        scale = np.sqrt(beta_n / alpha_n * (1 + xt @ np.linalg.inv(lam_n) @ xt))
        half = student_t.ppf(0.95, 2 * alpha_n) * scale
        yhat, lo, hi = fit.predict(x0, level=0.90)
        assert (yhat, lo, hi) == pytest.approx((xt @ mn, xt @ mn - half, xt @ mn + half), rel=1e-10)


def test_bayes_intervalo_predictivo_se_acerca_al_de_ols():
    x, y = _data(n=3000, sd=6.0, seed=3)
    fit = bayes_linear_fit(x, y, prior_mean=(0.0, 0.0), prior_sd=(1e3, 1e3), prior_sigma=6.0)
    x0 = np.array([-1.0, 0.5, 2.0])
    _, lo_b, hi_b = fit.predict(x0)
    _, lo_o, hi_o = ols_fit(x, y).predict(x0)
    np.testing.assert_allclose(hi_b - lo_b, hi_o - lo_o, rtol=0.01)
    np.testing.assert_allclose(lo_b, lo_o, rtol=0.01, atol=0.05)


finitos = st.floats(-50, 50, allow_nan=False, allow_infinity=False)


@settings(max_examples=60, deadline=None)
@given(xy=st.lists(st.tuples(finitos, finitos), min_size=0, max_size=12),
       m0=st.tuples(finitos, finitos), sd=st.tuples(st.floats(0.01, 100), st.floats(0.01, 100)),
       sigma=st.floats(0.1, 20))
def test_bayes_media_posterior_resuelve_el_sistema(xy, m0, sd, sigma):
    # gradiente nulo del objetivo penalizado: X'(y − Xβ) = Λ0(β − m0)
    x = np.array([p[0] for p in xy], dtype=float)
    y = np.array([p[1] for p in xy], dtype=float)
    fit = bayes_linear_fit(x, y, prior_mean=m0, prior_sd=sd, prior_sigma=sigma)
    beta = np.array([fit.a, fit.b])
    X = np.column_stack([x, np.ones_like(x)])
    lam0 = np.diag([sigma ** 2 / sd[0] ** 2, sigma ** 2 / sd[1] ** 2])
    lhs, rhs = X.T @ (y - X @ beta), lam0 @ (beta - np.array(m0))
    # error de redondeo acotado por la magnitud de cada término del sistema
    scale = (np.abs(X.T @ X) @ np.abs(beta) + np.abs(X.T @ y)
             + np.abs(lam0) @ (np.abs(beta) + np.abs(np.array(m0))))
    np.testing.assert_allclose(lhs - rhs, 0.0, atol=1e-10 * scale.max() + 1e-12)
    assert fit.beta > 0 and fit.alpha == pytest.approx(2.0 + len(xy) / 2)


# ---------- validación de entradas ----------

@pytest.mark.parametrize("x,y,msg", [
    ([1, 2, 3], [1, 2], "same length"),
    ([1, 2, np.nan], [1, 2, 3], "x must contain only finite"),
    ([1, 2, 3], [1, np.inf, 3], "y must contain only finite"),
    ([1, 2], [1, 2], "at least 3"),
    ([2, 2, 2], [1, 2, 3], "x must not be constant"),
    (["a", "b", "c"], [1, 2, 3], "x must be a sequence of numbers"),
    ([[1, 2], [3, 4]], [1, 2], "x must be one-dimensional"),
])
def test_ols_errores(x, y, msg):
    with pytest.raises(ValueError, match=msg):
        ols_fit(x, y)


def test_predict_errores():
    fit = ols_fit(*_data())
    with pytest.raises(ValueError, match="level"):
        fit.predict(1.0, level=1.0)
    with pytest.raises(ValueError, match="x0"):
        fit.predict([1.0, np.nan])


@pytest.mark.parametrize("ratio", [0, -1, np.inf, np.nan, True, "1"])
def test_deming_ratio_invalido(ratio):
    with pytest.raises(ValueError, match="ratio must be a positive finite number"):
        deming_fit([1, 2, 3], [1, 3, 2], ratio)


@pytest.mark.parametrize("x,y", [([1, 1, 1], [1, 2, 3]), ([1, 2, 3], [4, 4, 4]), ([-1, 0, 1], [1, 0, 1])])
def test_deming_sin_pendiente(x, y):
    with pytest.raises(ValueError, match="Deming slope is undefined"):
        deming_fit(x, y, 1.0)


def test_bootstrap_errores():
    stat = lambda i: 0.0  # noqa: E731
    with pytest.raises(ValueError, match="at least 2 distinct groups"):
        group_bootstrap(["A", "A"], stat)
    with pytest.raises(ValueError, match="n_boot"):
        group_bootstrap(["A", "B"], stat, n_boot=0)
    with pytest.raises(ValueError, match="seed"):
        group_bootstrap(["A", "B"], stat, seed=1.5)
    with pytest.raises(ValueError, match="hashable"):
        group_bootstrap([["A"], ["B"]], stat)


@pytest.mark.parametrize("kwargs,msg", [
    (dict(prior_strength=1.0), "prior_strength must be greater than 1"),
    (dict(prior_strength=0.0), "prior_strength must be a positive"),
    (dict(prior_sd=(0.0, 1.0)), r"prior_sd\[0\]"),
    (dict(prior_sd=(1.0, np.inf)), r"prior_sd\[1\]"),
    (dict(prior_sigma=-1.0), "prior_sigma"),
    (dict(prior_mean=(np.nan, 1.0)), "prior_mean must be finite"),
    (dict(prior_mean=(1.0, 2.0, 3.0)), "pairs of numbers"),
    (dict(prior_mean=5.0), "pairs of numbers"),
])
def test_bayes_errores(kwargs, msg):
    with pytest.raises(ValueError, match=msg):
        bayes_linear_fit([1, 2], [3, 4], **{**PRIOR, **kwargs})
