"""Clasificación del modelo predictivo (Fase 4B, tarea 8, y 4C, tarea 11): logit ordinal, logística MAP y métricas.

Solo datos sintéticos. statsmodels y scikit-learn entran como oráculos (R1), nunca en tiempo de ejecución.
"""

import dataclasses
import math
import warnings

import pytest
from hypothesis import assume, given, settings, strategies as st

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")
from scipy.special import expit  # noqa: E402

from rockmasspy.predictive import (average_precision, balanced_accuracy, brier, calibration_curve,  # noqa: E402
                                   calibration_intercept_slope, exponential_hazard_map_fit, f1_macro,
                                   frailty_hazard_map_fit,
                                   logistic_map_fit, ordinal_logit_fit,
                                   quadratic_weighted_kappa, recall_per_class, roc_auc)


def _ordinal_data(n=400, beta=(1.0, -0.7), cuts=(-1.0, 0.3, 1.5), seed=3):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, len(beta)))
    return X, np.digitize(X @ np.asarray(beta) + rng.logistic(size=n), cuts)  # latente logístico


def _binary_data(n=300, beta=(1.2, -0.8), b=0.5, seed=4):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, len(beta))) * [1.0, 3.0][:len(beta)] + [2.0, -1.0][:len(beta)]
    return X, (rng.random(n) < expit(b + X @ np.asarray(beta))).astype(float)


# ---------- logit ordinal ----------

def test_ordinal_contra_statsmodels():
    om = pytest.importorskip("statsmodels.miscmodels.ordinal_model")
    X, y = _ordinal_data()
    fit = ordinal_logit_fit(X, y, n_classes=4)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ref = om.OrderedModel(y, X, distr="logit").fit(method="bfgs", disp=False, maxiter=5000, gtol=1e-10)
    assert fit.converged and fit.message == ""
    assert (fit.n, fit.n_classes) == (400, 4)
    p = X.shape[1]
    # statsmodels: umbral 0 y luego log de los incrementos
    ref_cuts = ref.params[p] + np.r_[0.0, np.cumsum(np.exp(ref.params[p + 1:]))]
    np.testing.assert_allclose(fit.coef, ref.params[:p], rtol=1e-5)
    np.testing.assert_allclose(fit.cuts, ref_cuts, rtol=1e-5)
    assert fit.loglik == pytest.approx(ref.llf, rel=1e-9)
    np.testing.assert_allclose(fit.predict_proba(X), ref.predict(X), atol=1e-6)
    # error estándar: la covarianza se lleva a la escala de statsmodels con el jacobiano de (θ0, log Δθ)
    J = np.eye(p + 3)
    for k in range(1, 3):
        gap = fit.cuts[k] - fit.cuts[k - 1]
        J[p + k, p + k], J[p + k, p + k - 1] = 1.0 / gap, -1.0 / gap
    np.testing.assert_allclose(np.sqrt(np.diag(J @ fit.cov @ J.T)), ref.bse, rtol=1e-3)


def test_ordinal_n_grande_converge_contra_statsmodels():
    # Fase 5B: con la log-verosimilitud sumada y gtol absoluto, trust-exact terminaba en «bad approximation» con
    # n grande (sin separación) y el ajuste salía no convergido; con −log L / n converge y coincide con el oráculo
    om = pytest.importorskip("statsmodels.miscmodels.ordinal_model")
    n, rng = 10000, np.random.default_rng(0)
    X = np.column_stack([rng.normal(0, 2.0, n), rng.normal(1.0, 0.4, n), rng.random(n) < 0.5]).astype(float)
    y = np.digitize(X @ np.array([-1.5, 1.2, 0.8]) + rng.logistic(size=n), [-3.0, -1.0, 1.0, 3.0])
    fit = ordinal_logit_fit(X, y, n_classes=5)
    assert fit.converged and fit.message == "" and np.all(np.isfinite(fit.cov))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ref = om.OrderedModel(y, X, distr="logit").fit(method="bfgs", disp=False, maxiter=5000, gtol=1e-8)
    np.testing.assert_allclose(fit.coef, ref.params[:3], rtol=1e-4)
    assert fit.loglik == pytest.approx(ref.llf, rel=1e-9)


def test_ordinal_dos_clases_es_la_logistica():
    sm = pytest.importorskip("statsmodels.api")
    X, y = _binary_data()
    fit = ordinal_logit_fit(X, y, n_classes=2)
    ref = sm.Logit(y, sm.add_constant(X)).fit(disp=0)
    # P(y ≤ 0) = σ(θ − x·β) ⇒ logit P(y = 1) = x·β − θ
    np.testing.assert_allclose(fit.coef, ref.params[1:], rtol=1e-6)
    assert fit.cuts[0] == pytest.approx(-ref.params[0], rel=1e-6)
    order = [1, 2, 0]
    J = np.diag([1.0, 1.0, -1.0])
    np.testing.assert_allclose(fit.cov, J @ ref.cov_params()[np.ix_(order, order)] @ J, rtol=1e-5)


@pytest.mark.parametrize("seed", [11, 12, 13])
def test_ordinal_recupera_los_parametros(seed):
    beta, cuts = np.array([0.8, -1.5, 0.3]), np.array([-2.0, -0.5, 0.4, 2.2])
    X, y = _ordinal_data(n=3000, beta=beta, cuts=cuts, seed=seed)
    fit = ordinal_logit_fit(X, y, n_classes=5)
    assert fit.converged
    se = np.sqrt(np.diag(fit.cov))
    assert np.all(np.abs(np.r_[fit.coef, fit.cuts] - np.r_[beta, cuts]) < 4 * se)


def test_ordinal_probabilidades_y_prediccion():
    X, y = _ordinal_data()
    fit = ordinal_logit_fit(X, y, n_classes=4)
    Xe = np.array([[0.0, 0.0], [80.0, -80.0], [-80.0, 80.0], [1e4, 0.0]])  # extremos: sin NaN ni desborde
    P = fit.predict_proba(Xe)
    assert P.shape == (4, 4) and np.all(np.isfinite(P)) and np.all(P >= 0)
    np.testing.assert_allclose(P.sum(axis=1), 1.0, rtol=1e-12)
    np.testing.assert_array_equal(fit.predict(Xe), np.argmax(P, axis=1))
    assert fit.predict(Xe)[1] == 3 and fit.predict(Xe)[2] == 0
    assert np.all(np.diff(fit.cuts) > 0)


def test_ordinal_clase_ausente_en_prueba_se_permite():
    X, y = _ordinal_data()
    fit = ordinal_logit_fit(X, y, n_classes=4)
    Xt = X[y < 3]  # la prueba no trae la clase 3
    assert fit.predict_proba(Xt).shape == (Xt.shape[0], 4)


def test_ordinal_clase_sin_observaciones_en_entrenamiento():
    X, y = _ordinal_data()
    keep = y != 2
    with pytest.raises(ValueError, match=r"class\(es\) \[2\] have no observations"):
        ordinal_logit_fit(X[keep], y[keep], n_classes=4)


@pytest.mark.parametrize("y", [[0] * 20 + [1] * 20, [0] * 20 + [1] * 10 + [2] * 10])
def test_ordinal_separacion_no_converge(y):
    rng = np.random.default_rng(5)
    X = np.r_[rng.normal(-3, 0.3, (20, 1)), rng.normal(3, 0.3, (20, 1))]
    y = np.asarray(y)
    if y.max() == 2:  # 1 y 2 también separados entre sí
        X[30:] += 10.0
    fit = ordinal_logit_fit(X, y, n_classes=int(y.max()) + 1)
    assert not fit.converged
    assert "separated" in fit.message
    assert np.all(np.isnan(fit.cov))
    assert np.all(np.isfinite(fit.coef)) and np.all(np.isfinite(fit.cuts))


def test_ordinal_separacion_de_un_solo_corte_no_impide_el_mle():
    # 0 contra {1, 2} separados, pero 1 y 2 se mezclan: β es común a los cortes y el MLE existe
    rng = np.random.default_rng(5)
    X = np.r_[rng.normal(-3, 0.3, (20, 1)), rng.normal(3, 0.3, (20, 1))]
    y = np.r_[np.zeros(20, int), rng.permutation(np.r_[np.ones(10, int), 2 * np.ones(10, int)])]
    fit = ordinal_logit_fit(X, y, n_classes=3)
    assert fit.converged and np.all(np.isfinite(fit.cov))


def test_ordinal_columna_constante_no_converge_con_motivo():
    X, y = _ordinal_data()
    fit = ordinal_logit_fit(np.column_stack([X, np.ones(len(y))]), y, n_classes=4)
    assert not fit.converged and "singular" in fit.message


@pytest.mark.parametrize("kwargs, msg", [
    (dict(X=[1.0, 2.0], y=[0, 1], n_classes=2), "two-dimensional"),
    (dict(X=[[1.0], [np.nan]], y=[0, 1], n_classes=2), "finite"),
    (dict(X=[[1.0], [2.0]], y=[0, 2], n_classes=2), "integer classes between 0 and 1"),
    (dict(X=[[1.0], [2.0]], y=[0, 0.5], n_classes=2), "integer classes"),
    (dict(X=[[1.0], [2.0]], y=[0, 1, 1], n_classes=2), "same number of rows"),
    (dict(X=[[1.0], [2.0]], y=[0, 1], n_classes=1), "n_classes"),
    (dict(X=[[1.0], [2.0]], y=[0, 1], n_classes=True), "n_classes"),
])
def test_ordinal_errores(kwargs, msg):
    X = kwargs.pop("X")
    y = kwargs.pop("y")
    with pytest.raises(ValueError, match=msg):
        ordinal_logit_fit(X, y, **kwargs)


def test_ordinal_predict_columnas_equivocadas():
    X, y = _ordinal_data()
    fit = ordinal_logit_fit(X, y, n_classes=4)
    with pytest.raises(ValueError, match="2 columns"):
        fit.predict_proba(np.zeros((3, 3)))


# ---------- logística MAP ----------

def _neg_log_post(X, y, coef, intercept, prior_scale=2.5, intercept_scale=10.0):
    """−log posterior escrito aparte, en la escala original (oráculo independiente de la función)."""
    mean, scale = X.mean(axis=0), 2.0 * X.std(axis=0)
    gamma, alpha = coef * scale, intercept + coef @ mean
    eta = X @ coef + intercept
    return (np.sum(np.logaddexp(0.0, eta) - y * eta) + np.sum(np.log1p((gamma / prior_scale) ** 2))
            + np.log1p((alpha / intercept_scale) ** 2))


def test_map_con_prior_enorme_tiende_al_mle():
    sm = pytest.importorskip("statsmodels.api")
    X, y = _binary_data()
    fit = logistic_map_fit(X, y, prior_scale=1e6, intercept_scale=1e6)
    ref = sm.Logit(y, sm.add_constant(X)).fit(disp=0)
    assert fit.converged and fit.active_bounds == ()
    np.testing.assert_allclose(fit.coef, ref.params[1:], rtol=1e-5)
    assert fit.intercept == pytest.approx(ref.params[0], rel=1e-5)
    assert fit.loglik == pytest.approx(ref.llf, rel=1e-9)
    order = [1, 2, 0]  # (coef..., intercept)
    np.testing.assert_allclose(fit.cov, ref.cov_params()[np.ix_(order, order)], rtol=1e-4)


def test_map_gradiente_nulo_y_hessiano_por_diferencias_finitas():
    X, y = _binary_data(n=120)
    fit = logistic_map_fit(X, y)
    w0 = np.r_[fit.coef, fit.intercept]

    def f(w):
        return _neg_log_post(X, y, w[:-1], w[-1])

    h = 1e-4
    E = np.eye(w0.size) * h
    grad = np.array([(f(w0 + e) - f(w0 - e)) / (2 * h) for e in E])
    assert np.max(np.abs(grad)) < 1e-5
    H = np.array([[(f(w0 + a + b) - f(w0 + a - b) - f(w0 - a + b) + f(w0 - a - b)) / (4 * h * h) for b in E]
                  for a in E])
    np.testing.assert_allclose(np.linalg.inv(fit.cov), H, rtol=1e-4, atol=1e-4)


def test_map_separacion_completa_es_finito():
    x = np.r_[np.linspace(-3, -1, 15), np.linspace(1, 3, 15)]
    y = np.r_[np.zeros(15), np.ones(15)]
    fit = logistic_map_fit(x[:, None], y)
    assert fit.converged
    assert np.all(np.isfinite(fit.coef)) and np.isfinite(fit.intercept) and np.all(np.isfinite(fit.cov))
    assert 0 < fit.coef[0] < 20


def test_map_signo_contrario_a_los_datos_deja_la_cota_activa():
    X, y = _binary_data()  # coef verdaderos +1.2 y −0.8
    free = logistic_map_fit(X, y)
    fit = logistic_map_fit(X, y, signs=[-1, 0])
    assert fit.active_bounds == (0,)
    assert fit.coef[0] == 0.0 and fit.converged
    assert fit.coef[1] < 0
    # signos coherentes con los datos: ninguna cota activa y el mismo MAP que sin cotas
    ok = logistic_map_fit(X, y, signs=[1, -1])
    assert ok.active_bounds == ()
    np.testing.assert_allclose(ok.coef, free.coef, rtol=1e-6)


def test_map_escala_original_igual_a_estandarizar_a_mano():
    X, y = _binary_data()
    fit = logistic_map_fit(X, y)
    np.testing.assert_allclose(fit.x_mean, X.mean(axis=0))
    np.testing.assert_allclose(fit.x_scale, 2.0 * X.std(axis=0))
    Z = (X - X.mean(axis=0)) / (2.0 * X.std(axis=0))  # ya en media 0 y desviación 0.5
    fz = logistic_map_fit(Z, y)
    np.testing.assert_allclose(fit.predict_proba(X), fz.predict_proba(Z), rtol=1e-7)
    np.testing.assert_allclose(fz.coef, fit.coef * fit.x_scale, rtol=1e-6)
    for a, b in zip(fit.predict_interval(X), fz.predict_interval(Z)):
        np.testing.assert_allclose(a, b, rtol=1e-6)


def test_map_intervalo_delta_cobertura():
    rng = np.random.default_rng(21)
    beta, b, x0 = np.array([1.0, -0.5]), -0.3, np.array([[0.5, 1.0]])
    truth = expit(b + x0 @ beta)[0]
    hits = 0
    for _ in range(200):
        X = rng.normal(size=(250, 2))
        y = (rng.random(250) < expit(b + X @ beta)).astype(float)
        c, lo, hi = logistic_map_fit(X, y).predict_interval(x0, level=0.9)
        assert lo[0] <= c[0] <= hi[0]
        hits += lo[0] <= truth <= hi[0]
    assert 0.83 <= hits / 200 <= 0.97


def _metropolis_upper(X, y, fit, x0, n_iter=40000, seed=0):
    """Cuantil 0.95 de P(y = 1 | x0) bajo el posterior truncado por la cota +1 de la columna 0 (Metropolis)."""
    p = X.shape[1]
    mu, sc = fit.x_mean, fit.x_scale
    Z = np.column_stack([(X - mu) / sc, np.ones(len(y))])
    sc2 = np.r_[np.full(p, 2.5), 10.0] ** 2
    Ainv = np.eye(p + 1)
    Ainv[:p, :p], Ainv[p, :p] = np.diag(sc), mu
    L = np.linalg.cholesky(Ainv @ fit.cov @ Ainv.T)
    w = np.r_[fit.coef * sc, fit.intercept + fit.coef @ mu]

    def f(v):
        eta = Z @ v
        return np.sum(np.logaddexp(0, eta) - y * eta) + np.sum(np.log1p(v * v / sc2))

    rng = np.random.default_rng(seed)
    cur, out = f(w), np.empty((n_iter, p + 1))
    for it in range(n_iter):
        prop = w + 0.9 * L @ rng.standard_normal(p + 1)
        if prop[0] >= 0:
            new = f(prop)
            if np.log(rng.random()) < cur - new:
                w, cur = prop, new
        out[it] = w
    W = out[n_iter // 5:]
    eta = ((x0 - mu) / sc) @ W[:, :p].T + W[:, p]
    return float(np.quantile(expit(eta), 0.95))


def test_map_cota_activa_el_superior_no_subestima():
    # β verdadero = 0 con la cota β ≥ 0: la cota queda apenas activa y el posterior es una normal truncada
    rng = np.random.default_rng(11)
    for _ in range(50):
        X = rng.normal(0, 1, (80, 1))
        y = (rng.random(80) < expit(-1.0 + 0.0 * X[:, 0])).astype(float)
        fit = logistic_map_fit(X, y, signs=[1])
        if fit.active_bounds:
            break
    assert fit.active_bounds == (0,) and fit.signs == (1,)
    x0 = np.array([[2.5]])
    upper = fit.predict_interval(x0, level=0.9)[2][0]
    laplace = expit(x0[0] @ fit.coef + fit.intercept + 1.6448536 * np.sqrt(np.r_[x0[0], 1] @ fit.cov
                                                                            @ np.r_[x0[0], 1]))
    mcmc = _metropolis_upper(X, y, fit, x0[0])
    assert laplace < mcmc - 0.01  # el Laplace simétrico subestima
    assert upper >= mcmc - 0.003


def test_map_factor_de_la_seminormal_en_la_cota():
    # con la cota activa, la desviación de γ se agranda por Φ⁻¹((3 + nivel)/4) / Φ⁻¹((1 + nivel)/2)
    from scipy.stats import norm
    X, y = _binary_data()
    fit = logistic_map_fit(X, y, signs=[-1, 0])
    assert fit.active_bounds == (0,)
    x0 = np.array([[fit.x_mean[0] + 3.0, fit.x_mean[1]]])  # solo la columna con cota aporta a la varianza
    for level in (0.8, 0.9, 0.95):
        c, _, hi = fit.predict_interval(x0, level=level)
        z = norm.ppf(0.5 + level / 2)
        half = np.log(hi / (1 - hi)) - np.log(c / (1 - c))
        Ainv = np.eye(3)
        Ainv[:2, :2], Ainv[2, :2] = np.diag(fit.x_scale), fit.x_mean
        cov_w = Ainv @ fit.cov @ Ainv.T
        zt = np.r_[3.0 / fit.x_scale[0], 0.0, 1.0]
        d = np.r_[norm.ppf((3 + level) / 4) / z, 1.0, 1.0]
        assert half[0] == pytest.approx(z * np.sqrt((zt * d) @ cov_w @ (zt * d)), rel=1e-9)
    # sin cotas el intervalo es el delta simétrico de siempre
    free = logistic_map_fit(X, y)
    c, lo, hi = free.predict_interval(x0, level=0.9)
    Xt = np.r_[x0[0], 1.0]
    assert np.log(hi / (1 - hi))[0] - np.log(c / (1 - c))[0] == pytest.approx(
        norm.ppf(0.95) * np.sqrt(Xt @ free.cov @ Xt), rel=1e-9)


def test_map_columna_binaria_solo_se_centra():
    rng = np.random.default_rng(14)
    n = 400
    rare = (rng.random(n) < 0.05).astype(float) * 3.0 + 2.0  # dos valores, 2 y 5, el 5 raro
    cont = rng.normal(1.0, 2.0, n)
    X = np.column_stack([rare, cont])
    y = (rng.random(n) < expit(-1.0 + 0.4 * (rare - 2.0) + 0.3 * cont)).astype(float)
    fit = logistic_map_fit(X, y)
    np.testing.assert_allclose(fit.x_mean, X.mean(axis=0))
    np.testing.assert_allclose(fit.x_scale, [3.0, 2.0 * cont.std()])  # rango en la binaria, 2·sd en la continua
    # el prior en la binaria es Cauchy(0, 2.5) sobre el efecto de pasar de un valor al otro: reescalarla a 0/1
    # no cambia el ajuste
    f01 = logistic_map_fit(np.column_stack([(rare - 2.0) / 3.0, cont]), y)
    assert f01.x_scale[0] == 1.0
    np.testing.assert_allclose(f01.coef[0], fit.coef[0] * 3.0, rtol=1e-6)
    np.testing.assert_allclose(f01.predict_proba(np.column_stack([(rare - 2.0) / 3.0, cont])),
                               fit.predict_proba(X), rtol=1e-7)


@pytest.mark.parametrize("y", [[0, 0, 0, 0], [1, 1, 1, 1]])
def test_map_sin_fallas_o_sin_estables_es_error(y):
    with pytest.raises(ValueError, match="both classes"):
        logistic_map_fit([[1.0], [2.0], [3.0], [4.0]], y)


@pytest.mark.parametrize("kwargs, msg", [
    (dict(y=[0, 1, 2, 1]), "only 0 and 1"),
    (dict(y=[0, 1, 1]), "same number of rows"),
    (dict(X=[[1.0], [1.0], [1.0], [1.0]]), "column 0 of X is constant"),
    (dict(signs=[2]), "each \\+1, -1 or 0"),
    (dict(signs=[1, 0]), "sequence of 1 values"),
    (dict(signs="a"), "signs"),
    (dict(prior_scale=0), "prior_scale"),
    (dict(intercept_scale=-1.0), "intercept_scale"),
])
def test_map_errores(kwargs, msg):
    args = dict(X=[[1.0], [2.0], [3.0], [4.0]], y=[0, 1, 0, 1]) | kwargs
    with pytest.raises(ValueError, match=msg):
        logistic_map_fit(args.pop("X"), args.pop("y"), **args)


def test_map_predict_errores():
    X, y = _binary_data()
    fit = logistic_map_fit(X, y)
    with pytest.raises(ValueError, match="level"):
        fit.predict_interval(X, level=1.0)
    with pytest.raises(ValueError, match="2 columns"):
        fit.predict_proba(X[:, :1])


# ---------- métricas contra scikit-learn ----------

@st.composite
def _labels(draw):
    k = draw(st.integers(2, 5))
    n = draw(st.integers(1, 40))
    cls = st.integers(0, k - 1)
    return k, draw(st.lists(cls, min_size=n, max_size=n)), draw(st.lists(cls, min_size=n, max_size=n))


@settings(max_examples=150, deadline=None)
@given(_labels())
def test_metricas_ordinales_contra_sklearn(data):
    skm = pytest.importorskip("sklearn.metrics")
    k, y, yhat = data
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        assert balanced_accuracy(y, yhat, k) == pytest.approx(skm.balanced_accuracy_score(y, yhat), abs=1e-12)
        assert f1_macro(y, yhat, k) == pytest.approx(skm.f1_score(y, yhat, average="macro", zero_division=0),
                                                     abs=1e-12)
        ref_rec = skm.recall_score(y, yhat, average=None, labels=list(range(k)), zero_division=np.nan)
        ref_kappa = skm.cohen_kappa_score(y, yhat, weights="quadratic", labels=list(range(k)))
    np.testing.assert_allclose(recall_per_class(y, yhat, k), ref_rec, atol=1e-12, equal_nan=True)
    assert np.isnan(recall_per_class(y, yhat, k)[sorted(set(range(k)) - set(y))]).all()
    if np.isnan(ref_kappa):
        with pytest.raises(ValueError, match="undefined"):
            quadratic_weighted_kappa(y, yhat, k)
    else:
        assert quadratic_weighted_kappa(y, yhat, k) == pytest.approx(ref_kappa, abs=1e-12)


def test_kappa_usa_la_escala_completa():
    # la clase 1 no aparece: la distancia entre 0 y 2 vale 4, no 1
    y, yhat = [0, 0, 2, 2], [0, 2, 2, 2]
    i = np.arange(3)
    W = (i[:, None] - i[None, :]) ** 2
    C = np.array([[1, 0, 1], [0, 0, 0], [0, 0, 2]])
    E = np.outer(C.sum(1), C.sum(0)) / 4
    assert quadratic_weighted_kappa(y, yhat, 3) == pytest.approx(1 - (W * C).sum() / (W * E).sum())


_probs = st.sampled_from([0.0, 0.05, 0.1, 0.25, 0.5, 0.5, 0.75, 0.9, 1.0])  # muchos empates a propósito


@st.composite
def _scores(draw):
    n = draw(st.integers(0, 40))
    y = draw(st.lists(st.integers(0, 1), min_size=n, max_size=n)) + [0, 1]
    p = draw(st.lists(st.one_of(_probs, st.floats(0, 1)), min_size=n + 2, max_size=n + 2))
    return np.array(y, dtype=float), np.array(p)


@settings(max_examples=150, deadline=None)
@given(_scores())
def test_metricas_de_probabilidad_contra_sklearn(data):
    skm = pytest.importorskip("sklearn.metrics")
    y, p = data
    assert brier(y, p) == pytest.approx(skm.brier_score_loss(y, p), abs=1e-12)
    assert roc_auc(y, p) == pytest.approx(skm.roc_auc_score(y, p), abs=1e-12)
    assert average_precision(y, p) == pytest.approx(skm.average_precision_score(y, p), abs=1e-12)


@settings(max_examples=100, deadline=None)
@given(_scores(), st.integers(1, 12))
def test_curva_de_calibracion_contra_sklearn(data, n_bins):
    skc = pytest.importorskip("sklearn.calibration")
    y, p = data
    p_mean, y_mean, count = calibration_curve(y, p, n_bins=n_bins)
    ref_true, ref_pred = skc.calibration_curve(y, p, n_bins=n_bins, strategy="quantile")
    np.testing.assert_allclose(p_mean, ref_pred, atol=1e-12)
    np.testing.assert_allclose(y_mean, ref_true, atol=1e-12)
    assert count.sum() == y.size and np.all(count > 0)


def test_curva_de_calibracion_deciles():
    rng = np.random.default_rng(8)
    p = rng.random(1000)
    _, _, count = calibration_curve((rng.random(1000) < p).astype(float), p)
    assert count.size == 10 and np.all(count == 100)


def test_calibracion_contra_statsmodels():
    sm = pytest.importorskip("statsmodels.api")
    rng = np.random.default_rng(9)
    p = rng.uniform(0.02, 0.98, 500)
    y = (rng.random(500) < expit(0.4 + 0.6 * np.log(p / (1 - p)))).astype(float)  # mal calibrado a propósito
    lp = np.log(p / (1 - p))
    a, b = calibration_intercept_slope(y, p)
    slope = sm.Logit(y, sm.add_constant(lp)).fit(disp=0).params[1]
    citl = sm.GLM(y, np.ones((500, 1)), family=sm.families.Binomial(), offset=lp).fit().params[0]
    assert b == pytest.approx(slope, rel=1e-6)
    assert a == pytest.approx(citl, rel=1e-6)


def test_calibracion_perfecta():
    rng = np.random.default_rng(10)
    p = rng.uniform(0.05, 0.95, 20000)
    a, b = calibration_intercept_slope((rng.random(p.size) < p).astype(float), p)
    assert abs(a) < 0.05 and abs(b - 1) < 0.07


@pytest.mark.parametrize("fn, y, p, msg", [
    (calibration_intercept_slope, [0, 1, 1], [0.2, 0.0, 0.7], "strictly between 0 and 1"),
    (calibration_intercept_slope, [1, 1, 1], [0.2, 0.3, 0.7], "both classes"),
    (calibration_intercept_slope, [0, 0, 1], [0.2, 0.3, 0.3], "separates"),
    (roc_auc, [0, 0], [0.2, 0.3], "both classes"),
    (average_precision, [0, 0], [0.2, 0.3], "at least one positive"),
    (brier, [0, 1], [0.2], "same length"),
    (brier, [0, 2], [0.2, 0.3], "only 0 and 1"),
    (brier, [0, 1], [0.2, 1.3], "between 0 and 1"),
    (brier, [0, 1], [0.2, np.nan], "finite"),
    (brier, [], [], "at least 1"),
])
def test_metricas_de_probabilidad_errores(fn, y, p, msg):
    with pytest.raises(ValueError, match=msg):
        fn(y, p)


@pytest.mark.parametrize("fn", [balanced_accuracy, f1_macro, quadratic_weighted_kappa, recall_per_class])
def test_metricas_ordinales_errores(fn):
    with pytest.raises(ValueError, match="same length"):
        fn([0, 1], [0], 2)
    with pytest.raises(ValueError, match="between 0 and 2"):
        fn([0, 3], [0, 1], 3)
    with pytest.raises(ValueError, match="n_classes"):
        fn([0, 1], [0, 1], 1)


def test_calibracion_n_bins_invalido():
    with pytest.raises(ValueError, match="n_bins"):
        calibration_curve([0, 1], [0.2, 0.4], n_bins=0)


# ---------- tasa de falla constante (exponencial MAP) ----------

def _hazard_data(n=400, beta=(-0.5, 0.8), b=-6.0, seed=7, censor=(30, 900)):
    """Tiempos de falla exponenciales con log λ = b + X·β, censurados en un plazo uniforme."""
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, len(beta))) * [1.0, 0.5][:len(beta)] + [0.5, 1.0][:len(beta)]
    lam = np.exp(b + X @ np.asarray(beta))
    T, C = rng.exponential(1 / lam), rng.uniform(*censor, size=n)
    return X, (T <= C).astype(float), np.minimum(T, C)


def _hazard_neg_log_post(X, d, t, coef, intercept, prior_scale=2.5, intercept_scale=10.0):
    """−log posterior de la exponencial escrito aparte, en la escala original (oráculo independiente)."""
    mean, scale = X.mean(axis=0), 2.0 * X.std(axis=0)
    gamma, alpha = coef * scale, intercept + coef @ mean
    eta = X @ coef + intercept
    return (np.sum(np.exp(eta) * t - d * eta) + np.sum(np.log1p((gamma / prior_scale) ** 2))
            + np.log1p((alpha / intercept_scale) ** 2))


def test_hazard_con_prior_enorme_tiende_al_glm_poisson_con_offset():
    sm = pytest.importorskip("statsmodels.api")
    X, d, t = _hazard_data()
    fit = exponential_hazard_map_fit(X, d, t, prior_scale=1e6, intercept_scale=1e6)
    ref = sm.GLM(d, sm.add_constant(X), family=sm.families.Poisson(), offset=np.log(t)).fit()
    assert fit.converged and fit.active_bounds == () and fit.n_events == int(d.sum())
    np.testing.assert_allclose(fit.coef, ref.params[1:], rtol=1e-5)
    assert fit.intercept == pytest.approx(ref.params[0], rel=1e-6)
    order = [1, 2, 0]
    np.testing.assert_allclose(fit.cov, ref.cov_params()[np.ix_(order, order)], rtol=1e-4)
    lam = fit.rate(X[:3])
    np.testing.assert_allclose(lam, np.exp(ref.params[0] + X[:3] @ ref.params[1:]), rtol=1e-5)
    np.testing.assert_allclose(fit.prob_within(X[:3], 365.0), 1 - np.exp(-lam * 365.0), rtol=1e-12)


def test_hazard_gradiente_nulo_y_hessiano_por_diferencias_finitas():
    X, d, t = _hazard_data(n=150)
    fit = exponential_hazard_map_fit(X, d, t)
    w0 = np.r_[fit.coef, fit.intercept]

    def f(w):
        return _hazard_neg_log_post(X, d, t, w[:-1], w[-1])

    h = 1e-4
    E = np.eye(w0.size) * h
    grad = np.array([(f(w0 + e) - f(w0 - e)) / (2 * h) for e in E])
    assert np.max(np.abs(grad)) < 1e-4
    H = np.array([[(f(w0 + a + b) - f(w0 + a - b) - f(w0 - a + b) + f(w0 - a - b)) / (4 * h * h) for b in E]
                  for a in E])
    np.testing.assert_allclose(np.linalg.inv(fit.cov), H, rtol=1e-3, atol=1e-3)


def test_hazard_separacion_es_finita():
    x = np.r_[np.linspace(-3, -1, 15), np.linspace(1, 3, 15)]
    d = np.r_[np.zeros(15), np.ones(15)]
    fit = exponential_hazard_map_fit(x[:, None], d, np.full(30, 100.0))
    assert fit.converged and np.all(np.isfinite(fit.coef)) and np.all(np.isfinite(fit.cov))
    assert 0 < fit.coef[0] < 30


def test_hazard_cotas_de_signo_y_guardas():
    X, d, t = _hazard_data()  # β verdaderos −0.5 y +0.8
    fit = exponential_hazard_map_fit(X, d, t, signs=[1, 0])
    assert fit.active_bounds == (0,) and fit.coef[0] == 0.0 and fit.converged and fit.signs == (1, 0)
    ok = exponential_hazard_map_fit(X, d, t, signs=[-1, 1])
    assert ok.active_bounds == () and ok.coef[0] < 0 < ok.coef[1]
    # con la cota activa el intervalo se ensancha (normal truncada), nunca se angosta
    x0 = np.array([[2.0, 1.0]])
    c, lo, hi = fit.prob_interval(x0, 365.0)
    bare = dataclasses.replace(fit, signs=(0, 0)).prob_interval(x0, 365.0)
    assert lo[0] <= bare[1][0] and hi[0] >= bare[2][0] and lo[0] < c[0] < hi[0]
    with pytest.raises(ValueError, match="at least one event and one non-event"):
        exponential_hazard_map_fit(X, np.zeros(len(d)), t)
    with pytest.raises(ValueError, match="exposure must be positive"):
        exponential_hazard_map_fit(X, d, np.r_[0.0, t[1:]])
    with pytest.raises(ValueError, match="same number of rows"):
        exponential_hazard_map_fit(X, d[:-1], t)
    with pytest.raises(ValueError, match="days"):
        fit.prob_within(x0, -1.0)


def test_hazard_cobertura_del_intervalo_al_90():
    beta, b, x0, H = (-0.5, 0.8), -6.0, np.array([[1.0, 1.2]]), 365.0
    true = 1 - np.exp(-np.exp(b + x0 @ np.asarray(beta)) * H)[0]
    cover = 0
    for seed in range(100):
        X, d, t = _hazard_data(n=200, seed=100 + seed)
        _, lo, hi = exponential_hazard_map_fit(X, d, t).prob_interval(x0, H, level=0.9)
        cover += lo[0] <= true <= hi[0]
    assert 80 <= cover <= 98, cover


# ---------- tasa de falla con fragilidad gamma (nivel 3) ----------

def _frailty_data(n_groups=40, per=12, beta=(-0.5, 0.8), b=-6.0, theta=0.5, seed=11, n_clusters=8):
    """Tiempos exponenciales con λ·Z_g, Z_g ~ Gamma(media 1, varianza θ) por grupo, censurados al azar."""
    rng = np.random.default_rng(seed)
    g = np.repeat(np.arange(n_groups), per)
    X = rng.normal(size=(g.size, len(beta))) * [1.0, 0.5] + [0.5, 1.0]
    z = rng.gamma(1 / theta, theta, n_groups)[g] if theta > 0 else np.ones(g.size)
    lam = np.exp(b + X @ np.asarray(beta)) * z
    T, C = rng.exponential(1 / lam), rng.uniform(30, 900, g.size)
    return X, (T <= C).astype(float), np.minimum(T, C), g, g % n_clusters


def _frailty_marginal_numeric(X, d, t, g, coef, b, theta):
    """log L marginal por integración numérica de Z (oráculo independiente de la fórmula cerrada)."""
    from scipy import integrate, stats
    eta = X @ coef + b
    k = 1 / theta
    out = float(np.sum(d * eta))
    for grp in np.unique(g):
        m = g == grp
        dg, lam = d[m].sum(), np.sum(np.exp(eta[m]) * t[m])
        f = lambda z: z ** dg * np.exp(-z * lam) * stats.gamma.pdf(z, k, scale=theta)  # noqa: E731
        out += math.log(integrate.quad(f, 0, np.inf, limit=200)[0])
    return out


def test_fragilidad_con_theta_cero_es_la_exponencial():
    X, d, t, g, c = _frailty_data(n_groups=60, theta=0.0)
    f = frailty_hazard_map_fit(X, d, t, g, clusters=c, signs=[-1, 1])
    e = exponential_hazard_map_fit(X, d, t, signs=[-1, 1])
    assert f.converged and f.theta < 0.1
    np.testing.assert_allclose(f.coef, e.coef, atol=0.03)
    assert f.intercept == pytest.approx(e.intercept, abs=0.05)
    # con θ ≈ 0 la media marginal es la condicional
    x0 = X[:3]
    np.testing.assert_allclose(f.prob_marginal(x0, 365.0), f.prob_within(x0, 365.0), rtol=0.05)


def test_fragilidad_marginal_cerrada_contra_integracion_numerica():
    optimize = pytest.importorskip("scipy.optimize")
    X, d, t, g, _ = _frailty_data(n_groups=12, per=8, theta=0.6, seed=5)
    f = frailty_hazard_map_fit(X, d, t, g)
    assert f.converged and f.cov_kind == "laplace" and f.df is None and f.n_groups == 12
    assert f.loglik == pytest.approx(_frailty_marginal_numeric(X, d, t, g, f.coef, f.intercept, f.theta), rel=1e-7)
    mean, scale = X.mean(axis=0), 2.0 * X.std(axis=0)

    def neg_post(v):  # (γ, log θ, α) con los mismos priors, escrito aparte
        gam, phi, alpha = v[:2], v[2], v[3]
        coef = gam / scale
        b = alpha - coef @ mean
        return (-_frailty_marginal_numeric(X, d, t, g, coef, b, math.exp(phi)) + np.sum(np.log1p((gam / 2.5) ** 2))
                + math.log1p((alpha / 10.0) ** 2) + phi ** 2 / 8.0)

    # arranca lejos del óptimo de la función (γ en 0, θ = 0.3): BFGS con gradiente numérico
    res = optimize.minimize(neg_post, np.array([0.0, 0.0, math.log(0.3), math.log(d.sum() / t.sum())]),
                            method="BFGS", options={"gtol": 1e-7})
    np.testing.assert_allclose(res.x[:2] / scale, f.coef, rtol=2e-3, atol=2e-4)
    assert math.exp(res.x[2]) == pytest.approx(f.theta, rel=5e-3)


def test_fragilidad_recupera_theta_del_generador():
    from rockmasspy.history import labor_key, level3_rows
    from rockmasspy.predictive import synthetic_history
    # θ verdadero ≈ var(exp(b)) normalizada = exp(σ²) − 1, σ² = 0.4² + 0.5² (zona + labor): 0.51; el generador es
    # lognormal y la zona es compartida entre labores, así que se pide el orden de magnitud
    target = math.exp(0.4 ** 2 + 0.5 ** 2) - 1
    for seed in range(3):
        h, _ = synthetic_history(seed=seed, n_zones=8, labors_per_zone=12, tramos_per_labor=15)
        rows = level3_rows(h)
        order = {s.codigo_tipo: s.orden for s in h.support_types}
        X = np.array([[math.log(r.q_valor), math.log(r.luz_m / r.esr), order[r.sost_instalado]] for _, r in rows])
        d = np.array([o.failed for o, _ in rows], dtype=float)
        t = np.array([o.exposure_days for o, _ in rows], dtype=float)
        f = frailty_hazard_map_fit(X, d, t, [labor_key(r) for _, r in rows], clusters=[r.zona_nivel for _, r in rows],
                                   signs=[-1, 1, -1])
        assert f.converged and f.cov_kind == "cluster" and f.df == 7
        assert 0.3 * target < f.theta < 2.0 * target, f.theta


def test_fragilidad_intervalo_y_covarianza_agrupada():
    X, d, t, g, c = _frailty_data()
    f = frailty_hazard_map_fit(X, d, t, g, clusters=c, signs=[-1, 1])
    lap = frailty_hazard_map_fit(X, d, t, g, signs=[-1, 1])
    assert f.cov_kind == "cluster" and f.n_clusters == 8 and f.df == 7 and lap.cov_kind == "laplace"
    np.testing.assert_allclose(f.coef, lap.coef)  # misma estimación, otra covarianza
    few = frailty_hazard_map_fit(X, d, t, g, clusters=c % 3, signs=[-1, 1])
    assert few.cov_kind == "laplace" and few.n_clusters == 3
    x0 = X[:5]
    c0, lo, hi = f.prob_interval(x0, 365.0, level=0.9)
    assert np.all(lo <= c0) and np.all(c0 <= hi)
    # el superior lleva el cuantil de la fragilidad: supera a la condicional con la cota de η
    assert f.frailty_quantile(0.9) > 1 and np.all(hi > f.prob_within(x0, 365.0))
    # Z_q usa la cota superior de θ (conservador por diseño): mayor que con θ̂
    from scipy.stats import gamma as gamma_dist
    th = f.theta_upper(0.9)
    assert th == pytest.approx(math.exp(math.log(f.theta) + 1.2815515655446004 * f.log_theta_sd))
    assert th > f.theta and f.frailty_quantile(0.9) > gamma_dist.ppf(0.9, 1 / f.theta, scale=f.theta)
    assert f.theta > 0.2
    with pytest.raises(ValueError, match="at least one event and one non-event"):
        frailty_hazard_map_fit(X, np.zeros(len(d)), t, g)
    with pytest.raises(ValueError, match="one label per row"):
        frailty_hazard_map_fit(X, d, t, g[:-1])
