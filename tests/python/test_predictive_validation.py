"""Motor de validación del módulo predictivo (Fase 4B, tarea 9; plan R7). Solo datos sintéticos."""

import math

import pytest

np = pytest.importorskip("numpy")
optimize = pytest.importorskip("scipy.optimize")

from rockmasspy.history import tramo_outcomes  # noqa: E402
from rockmasspy.predictive import (Comparison, Fold, Improvement, SyntheticTruth, ValidationReport,  # noqa: E402
                                   compare_models,
                                   dummy_class_fit_predict, dummy_proba_fit_predict, group_bootstrap, group_kfold,
                                   leave_one_group_out, out_of_fold, random_kfold, synthetic_history, temporal_split,
                                   tramo_groups, validate)
from rockmasspy.predictive.validation import MAX_DISCARDED_FRACTION_DECISION  # noqa: E402
from rockmasspy.q_support import read_q_chart  # noqa: E402


def _accuracy(y, pred):
    return float(np.mean(y == pred))


def _brier(y, p):
    return float(np.mean((p - y) ** 2))


def _cubre_una_vez(folds, n):
    tests = np.concatenate([f.test for f in folds])
    assert np.array_equal(np.sort(tests), np.arange(n))
    for f in folds:
        assert np.intersect1d(f.train, f.test).size == 0
        assert np.array_equal(np.sort(np.concatenate([f.train, f.test, f.excluded])), np.arange(n))


# ---------- particiones ----------

def test_group_kfold_no_comparte_grupos_cubre_todo_y_es_reproducible():
    rng = np.random.default_rng(0)
    groups = [("Z1", f"L{g:03d}") for g in rng.integers(0, 17, 300)]  # etiquetas tupla, como labor_key
    folds = group_kfold(groups, k=5, seed=3)
    assert len(folds) == 5
    _cubre_una_vez(folds, 300)
    for f in folds:
        assert not {groups[i] for i in f.train} & {groups[i] for i in f.test}
        assert not f.optimistic
    sizes = [f.test.size for f in folds]
    assert max(sizes) - min(sizes) <= max(np.unique(groups, axis=0, return_counts=True)[1])  # equilibrio greedy
    again = group_kfold(groups, k=5, seed=3)
    assert all(np.array_equal(a.test, b.test) for a, b in zip(folds, again))
    other = group_kfold(groups, k=5, seed=4)
    assert any(not np.array_equal(a.test, b.test) for a, b in zip(folds, other))


def test_group_kfold_casos_borde():
    folds = group_kfold(["a", "a", "b", "c", "c"], k=10)
    assert len(folds) == 3  # k = número de grupos
    _cubre_una_vez(folds, 5)
    with pytest.raises(ValueError, match="at least 2 distinct groups"):
        group_kfold(["a"] * 4)
    with pytest.raises(ValueError, match="k must be"):
        group_kfold(["a", "b"], k=1)
    with pytest.raises(ValueError, match="hashable"):
        group_kfold([["a"], ["b"]])


def test_leave_one_group_out_un_pliegue_por_grupo_sin_etiquetas_en_el_nombre():
    zones = ["ZZSENT", "Z2", "ZZSENT", "Z3", "Z2"]
    folds = leave_one_group_out(zones)
    assert [f.name for f in folds] == ["group-1", "group-2", "group-3"]
    assert [f.test.tolist() for f in folds] == [[0, 2], [1, 4], [3]]
    _cubre_una_vez(folds, 5)
    with pytest.raises(ValueError, match="at least 2 distinct groups"):
        leave_one_group_out(["Z1", "Z1"])


def test_temporal_split_entrena_con_lo_anterior_y_excluye_sin_ano():
    years = [2020, None, 2022, 2021, float("nan"), 2022, 2019]
    (fold,) = temporal_split(years)
    assert fold.train.tolist() == [0, 3, 6]
    assert fold.test.tolist() == [2, 5]
    assert fold.excluded.tolist() == [1, 4]
    with pytest.raises(ValueError, match="at least 2 distinct years"):
        temporal_split([2020, 2020, None])
    with pytest.raises(ValueError, match="at least 2 distinct years"):
        temporal_split([None, None])
    with pytest.raises(ValueError, match="integers or None"):
        temporal_split([2020, 2021.5])
    with pytest.raises(ValueError, match="integers or None"):
        temporal_split([2020, float("inf")])


def test_random_kfold_marca_optimista():
    folds = random_kfold(23, k=5, seed=1)
    assert len(folds) == 5 and all(f.optimistic for f in folds)
    _cubre_una_vez(folds, 23)
    assert len(random_kfold(3, k=5)) == 3


def test_tramo_groups_saca_labor_zona_y_ano():
    h, _ = synthetic_history(n_zones=2, labors_per_zone=2, tramos_per_labor=4, seed=0)
    labors, zones, years = tramo_groups(h.tramos)
    assert labors[0] == (h.tramos[0].zona_nivel, h.tramos[0].labor_codigo)
    assert zones[0] == h.tramos[0].zona_nivel
    assert years[0] == int(h.tramos[0].fecha_evaluacion[:4])


# ---------- fuera de pliegue ----------

def test_un_pliegue_fallido_se_registra_y_la_validacion_sigue():
    y = np.array([0, 1] * 10)
    groups = np.repeat(np.arange(5), 4)
    folds = group_kfold(groups, k=5)
    bad = folds[2].name

    def fit_predict(train, test):  # perfecto salvo en un pliegue, que falla
        if np.array_equal(test, folds[2].test):
            raise ValueError("class 1 missing from train in labor ZZSENT")
        return y[test].astype(float)

    oof = out_of_fold(folds, fit_predict, 20, kind="proba")
    assert oof.n_failed == 1 and oof.failures[0].fold == bad
    assert oof.failures[0].reason == "ValueError"  # sin el texto: podría traer etiquetas (R13)
    assert not oof.covered[folds[2].test].any() and oof.covered.sum() == 16
    assert (oof.fold_of[folds[2].test] == -1).all()
    dummy = out_of_fold(folds, dummy_proba_fit_predict(y), 20, kind="proba")
    cmp = compare_models(y, {"site": oof, "dummy": dummy}, metric=_brier, higher_is_better=False, groups=groups,
                         reference="dummy", n_boot=50)
    assert cmp.n_rows == 16 and cmp.failed_folds == {"site": 1, "dummy": 0}
    # gana con holgura en los pliegues que quedaron, pero un pliegue fallido bloquea la recomendación
    assert cmp.beats("dummy") and not cmp.recommend
    assert cmp.blockers == ("site failed 1 fold(s)",)
    # lo mismo si el que falla es la referencia
    def coin(train, test):
        if np.array_equal(test, folds[0].test):
            raise ZeroDivisionError
        return np.full(len(test), 0.5)
    ok = out_of_fold(folds, lambda tr, te: y[te].astype(float), 20, kind="proba")
    bad_ref = out_of_fold(folds, coin, 20, kind="proba")
    cmp = compare_models(y, {"site": ok, "dummy": bad_ref}, metric=_brier, higher_is_better=False, groups=groups,
                         reference="dummy", n_boot=50)
    assert cmp.beats("dummy") and not cmp.recommend and cmp.blockers == ("dummy failed 1 fold(s)",)


def test_validate_no_recomienda_si_el_principal_falla_pliegues():
    rng = np.random.default_rng(2)
    labors = np.repeat(np.arange(10), 6)
    zones = labors // 5
    years = np.where(np.arange(60) % 2, 2021, 2020)
    y = rng.integers(0, 2, 60).astype(float)

    def site(train, test):
        if 0 in test:
            raise ValueError("boom")
        return y[test]
    models = {"site": site, "dummy": dummy_proba_fit_predict(y)}
    rep = validate(y, models, kind="proba", labors=labors, zones=zones, years=years, metric=_brier,
                   higher_is_better=False, reference="dummy", n_boot=50)
    assert not rep.recommend
    assert rep.results["labor"].beats("dummy") and rep.results["labor"].failed_folds["site"] == 1
    models["site"] = lambda tr, te: y[te]
    assert validate(y, models, kind="proba", labors=labors, zones=zones, years=years, metric=_brier,
                    higher_is_better=False, reference="dummy", n_boot=50).recommend


def test_probabilidades_invalidas_fallan_el_pliegue_y_formas_malas_son_error():
    folds = group_kfold(np.repeat(np.arange(4), 3), k=4)
    oof = out_of_fold(folds, lambda tr, te: np.full(len(te), np.nan), 12, kind="proba")
    assert oof.n_failed == 4 and not oof.covered.any()
    with pytest.raises(ValueError, match="shape"):
        out_of_fold(folds, lambda tr, te: np.zeros(len(te) + 1), 12, kind="proba")
    with pytest.raises(ValueError, match="more than one test"):
        out_of_fold(folds + folds[:1], lambda tr, te: np.zeros(len(te)), 12, kind="class")
    with pytest.raises(ValueError, match="train indices out of range"):
        out_of_fold([Fold("f", np.array([-1, 1]), np.array([2]))], lambda tr, te: np.zeros(len(te)), 12, kind="class")
    with pytest.raises(ValueError, match="test indices out of range"):
        out_of_fold([Fold("f", np.array([1]), np.array([12]))], lambda tr, te: np.zeros(len(te)), 12, kind="class")
    with pytest.raises(ValueError, match="train and test share rows"):
        out_of_fold([Fold("f", np.array([1, 2]), np.array([2]))], lambda tr, te: np.zeros(len(te)), 12, kind="class")
    with pytest.raises(TypeError):  # un error de código no se esconde como pliegue fallido
        out_of_fold(folds, lambda tr, te: None + 1, 12, kind="class")


def test_referencias_ficticias():
    y = np.array([0, 0, 1, 2, 2, 2])
    tr, te = np.array([0, 1, 2, 3, 4]), np.array([5])
    assert dummy_class_fit_predict(y)(tr, te).tolist() == [0]  # empate 0/2: la etiqueta menor
    assert dummy_proba_fit_predict(y, n_classes=3)(tr, te).tolist() == [[0.4, 0.2, 0.4]]
    assert dummy_proba_fit_predict(np.array([0, 1, 1, 1]))(np.arange(4), np.arange(2)).tolist() == [0.75, 0.75]
    with pytest.raises(ValueError, match="0/1"):
        dummy_proba_fit_predict(y)


# ---------- bootstrap ----------

def test_bootstrap_pareado_y_por_grupos():
    G = 12
    y = np.repeat(np.arange(G), 30)  # la etiqueta es el grupo: la métrica ve qué grupos entraron
    groups = [f"L{g:03d}" for g in y]
    folds = group_kfold(groups, k=4)
    ones = out_of_fold(folds, lambda tr, te: np.ones(len(te)), y.size, kind="proba")
    zeros = out_of_fold(folds, lambda tr, te: np.zeros(len(te)), y.size, kind="proba")

    # pareado: los dos modelos ven las mismas filas en cada réplica, así que la mejora es exactamente 1 siempre
    paired = compare_models(y, {"a": ones, "b": zeros}, metric=lambda yy, p: np.unique(yy).size + p.mean(),
                            higher_is_better=True, groups=groups, reference="b", n_boot=200)
    imp = paired.improvements["b"]
    assert imp.value == imp.ci_low == imp.ci_high == pytest.approx(1.0)
    assert paired.beats("b") and paired.recommend and paired.n_groups == G

    # por grupos: la mejora = grupos distintos en la réplica; remuestrear filas daría casi siempre los 12
    by_group = compare_models(y, {"a": ones, "b": zeros}, metric=lambda yy, p: np.unique(yy).size * p.mean(),
                              higher_is_better=True, groups=groups, reference="b", n_boot=400)
    imp = by_group.improvements["b"]
    assert imp.value == G and imp.ci_high < G and imp.ci_low < 0.75 * G

    lower = compare_models(y, {"a": ones, "b": zeros}, metric=lambda yy, p: p.mean(), higher_is_better=False,
                           groups=groups, reference="b", n_boot=20)
    assert lower.improvements["b"].value == -1 and not lower.recommend


def test_compare_models_valida_la_llamada_y_marca_optimista():
    y = np.array([0, 1] * 6)
    groups = np.repeat(np.arange(6), 2)
    fp = dummy_proba_fit_predict(y)
    rnd = {m: out_of_fold(random_kfold(12, k=3), fp, 12, kind="proba") for m in ("site", "dummy")}
    assert compare_models(y, rnd, metric=_brier, higher_is_better=False, groups=groups, reference="dummy",
                          n_boot=20).optimistic
    with pytest.raises(ValueError, match="not in preds"):
        compare_models(y, rnd, metric=_brier, higher_is_better=False, groups=groups, reference="ngi")
    with pytest.raises(ValueError, match="at least one model"):
        compare_models(y, rnd, metric=_brier, higher_is_better=False, groups=groups, reference=())
    with pytest.raises(ValueError, match="exactly one model"):
        compare_models(y, {**rnd, "otro": rnd["site"]}, metric=_brier, higher_is_better=False, groups=groups,
                       reference="dummy")


# ---------- fuga espacial (MODELOS_SOSTENIMIENTO §1.2, trampa 1) ----------

def _nn_fit_predict(x, y):
    def fit_predict(train, test):
        d = np.abs(x[test][:, None] - x[train][None, :])
        return y[train][np.argmin(d, axis=1)]
    return fit_predict


def test_vecino_mas_cercano_gana_con_particion_aleatoria_y_no_con_agrupada():
    rng = np.random.default_rng(7)
    G, m = 40, 8
    groups = np.repeat(np.arange(G), m)
    center, label = rng.uniform(0, 100, G), rng.integers(0, 2, G)  # la etiqueta es solo un efecto del grupo
    x, y = center[groups] + rng.normal(0, 0.05, G * m), label[groups]
    models = {"knn": _nn_fit_predict(x, y), "dummy": dummy_class_fit_predict(y)}

    def run(folds):
        preds = {k: out_of_fold(folds, fp, y.size, kind="class") for k, fp in models.items()}
        return compare_models(y, preds, metric=_accuracy, higher_is_better=True, groups=groups,
                              reference="dummy", n_boot=300)

    leaky, honest = run(random_kfold(y.size, k=5)), run(group_kfold(groups, k=5))
    assert leaky.metrics["knn"] > 0.95 and leaky.recommend and leaky.optimistic
    assert honest.metrics["knn"] < 0.7 and not honest.recommend and not honest.optimistic


# ---------- con el generador sintético ----------

def _logit_fit_predict(X, y, ridge=1e-3):
    """Logística MAP simple; estandariza con la media y la desviación de train (preprocesamiento por pliegue)."""
    def fit_predict(train, test):
        if np.unique(y[train]).size < 2:
            raise ValueError("one class missing from train")
        mu, sd = X[train].mean(0), X[train].std(0)
        sd[sd == 0] = 1.0
        A = np.column_stack([np.ones(train.size), (X[train] - mu) / sd])
        yt = y[train]

        def nll(b):
            eta = A @ b
            return np.sum(np.logaddexp(0, eta) - yt * eta) + ridge * b[1:] @ b[1:], \
                A.T @ (1 / (1 + np.exp(-eta)) - yt) + 2 * ridge * np.r_[0, b[1:]]
        b = optimize.minimize(nll, np.zeros(A.shape[1]), jac=True, method="L-BFGS-B").x
        B = np.column_stack([np.ones(test.size), (X[test] - mu) / sd])
        return 1 / (1 + np.exp(-(B @ b)))
    return fit_predict


def _level3(seed, site_effect, **size):
    h, _ = synthetic_history(seed=seed, truth=SyntheticTruth(site_effect=site_effect), **size)
    out = {o.id_tramo: o for o in tramo_outcomes(h)}
    order = {s.codigo_tipo: s.orden for s in h.support_types}
    ts = [t for t in h.tramos if t.id_tramo in out]
    lnq = np.array([math.log(t.q_valor) for t in ts])
    lnde = np.array([math.log(t.luz_m / t.esr) for t in ts])
    rank = np.array([order[t.sost_instalado] for t in ts], dtype=float)
    lnexp = np.array([math.log(out[t.id_tramo].exposure_days) for t in ts])
    cat = np.array([read_q_chart(t.q_valor, t.luz_m / t.esr).category for t in ts], dtype=float)
    y = np.array([out[t.id_tramo].failed for t in ts], dtype=float)
    labors, zones, years = tramo_groups(ts)
    return np.column_stack([lnq, lnde, rank, lnexp]), cat[:, None], y, labors, zones, years


def _decision(seed, site_effect, n_boot, **size):
    X_site, X_ngi, y, labors, zones, years = _level3(seed, site_effect, **size)
    models = {"site": _logit_fit_predict(X_site, y), "baseline_ngi": _logit_fit_predict(X_ngi, y),
              "dummy": dummy_proba_fit_predict(y)}
    return validate(y, models, kind="proba", labors=labors, zones=zones, years=years, metric=_brier,
                    higher_is_better=False, reference=("dummy", "baseline_ngi"), n_boot=n_boot, seed=seed)


def test_sin_efecto_del_sitio_no_recomienda_en_al_menos_90_por_ciento_de_semillas():
    reports = [_decision(seed, False, n_boot=150) for seed in range(10)]
    assert sum(r.recommend for r in reports) <= 1
    assert all(set(r.results) | set(r.skipped) == {"labor", "zone", "temporal"} for r in reports)
    assert all(not r.results["labor"].optimistic for r in reports)


def test_con_efecto_del_sitio_el_modelo_correcto_gana_al_ficticio():
    recommended = 0
    for seed in range(5):
        # el efecto de labor y zona pesa: con 240 tramos el IC de la mejora aún toca el cero
        rep = _decision(seed, True, n_boot=150, n_zones=6, labors_per_zone=8, tramos_per_labor=15)
        for part in ("labor", "zone"):
            cmp = rep.results[part]
            assert cmp.beats("dummy") and cmp.recommend, (part, cmp.improvements)
        recommended += rep.recommend  # la temporal, como no inferioridad, a veces sale peor por azar
    assert recommended >= 3


def test_validate_omite_particiones_imposibles_y_decide_por_labor():
    y = np.array([0, 1] * 8, dtype=float)
    labors = np.repeat(np.arange(8), 2)
    models = {"site": dummy_proba_fit_predict(y), "dummy": dummy_proba_fit_predict(y)}
    rep = validate(y, models, kind="proba", labors=labors, zones=["Z1"] * 16, years=[2020] * 16, metric=_brier,
                   higher_is_better=False, reference="dummy", n_boot=20, random_split=True)
    assert set(rep.skipped) == {"zone", "temporal"} and set(rep.results) == {"labor", "random"}
    assert rep.results["random"].optimistic and not rep.recommend
    assert len(rep.warnings) == 2 and "temporal validation not run" in rep.warnings[0]
    with pytest.raises(ValueError, match="not in preds"):
        validate(y, models, kind="proba", labors=labors, zones=labors, years=[2020] * 16, metric=_brier,
                 higher_is_better=False, reference="ngi")
    with pytest.raises(ValueError, match="k must be"):
        validate(y, models, kind="proba", labors=labors, zones=labors, years=[2020] * 16, metric=_brier,
                 higher_is_better=False, reference="dummy", k=1)


def test_temporal_exige_dos_grupos_en_el_ultimo_ano():
    years, labors = [2020, 2020, 2021, 2021], ["a", "b", "c", "c"]
    with pytest.raises(ValueError, match="at least 2 groups in the last year, got 1"):
        temporal_split(years, groups=labors)
    assert temporal_split(years, groups=["a", "b", "c", "d"])[0].test.tolist() == [2, 3]
    y = np.array([0, 1, 0, 1] * 3, dtype=float)
    labors = np.repeat(np.arange(6), 2)
    years = [2020] * 10 + [2021] * 2  # el último año tiene una sola labor
    models = {"site": lambda tr, te: y[te], "dummy": dummy_proba_fit_predict(y)}
    rep = validate(y, models, kind="proba", labors=labors, zones=labors // 3, years=years, metric=_brier,
                   higher_is_better=False, reference="dummy", n_boot=50)
    assert "got 1" in rep.skipped["temporal"] and rep.warnings
    assert rep.recommend  # la temporal omitida no bloquea; labor y zona deciden


def test_temporal_peor_que_la_referencia_bloquea():
    rng = np.random.default_rng(5)
    labors = np.repeat(np.arange(20), 10)
    zones, years = labors // 5, np.where(np.arange(200) % 10 >= 8, 2021, 2020)
    y = rng.integers(0, 2, 200).astype(float)
    models = {"dummy": dummy_proba_fit_predict(y)}

    def run(site):
        models["site"] = site
        return validate(y, models, kind="proba", labors=labors, zones=zones, years=years, metric=_brier,
                        higher_is_better=False, reference="dummy", n_boot=200)
    # perfecto salvo en el último año, donde se equivoca con 0.7: gana en labor y zona, pierde en la temporal
    worse = run(lambda tr, te: np.where(years[te] == 2021, 0.7 - 0.4 * y[te], y[te]))
    assert worse.results["labor"].recommend and worse.results["zone"].recommend
    assert worse.results["temporal"].improvements["dummy"].value < 0 and not worse.recommend
    assert run(lambda tr, te: y[te]).recommend


def _cmp(**over):
    base = dict(main="site", metrics={}, improvements={}, higher_is_better=False, n_rows=10, n_groups=5, n_boot=100,
                n_discarded=0, failed_folds={"site": 0}, optimistic=False)
    base["improvements"] = {"dummy": Improvement(over.pop("value", 0.1), over.pop("lo", 0.05), 0.2)}
    return Comparison(**{**base, **over})


def test_replicas_degeneradas_bloquean_sobre_el_1_por_ciento():
    assert MAX_DISCARDED_FRACTION_DECISION == 0.01
    assert _cmp(n_discarded=1).recommend  # 1 de 100: en el límite
    c = _cmp(n_discarded=2)
    assert c.beats("dummy") and not c.recommend and "2 of 100 bootstrap replicates" in c.blockers[0]
    assert _cmp(lo=0.0).blockers == ("site does not beat dummy (95% CI of the improvement reaches 0)",)


def test_reporte_exige_labor_y_zona_y_la_temporal_si_existe():
    yes, no = _cmp(), _cmp(lo=-0.1)
    R = ValidationReport
    assert R({"labor": yes, "zone": yes, "temporal": yes}, {}).recommend
    assert not R({"labor": yes, "zone": no, "temporal": yes}, {}).recommend
    assert not R({"labor": no, "zone": yes, "temporal": yes}, {}).recommend
    # temporal como no inferioridad: un IC que toca el cero no bloquea; una mejora puntual negativa sí
    assert R({"labor": yes, "zone": yes, "temporal": no}, {}).recommend
    assert not R({"labor": yes, "zone": yes, "temporal": _cmp(value=-0.01, lo=-0.1)}, {}).recommend
    assert not R({"labor": yes, "temporal": yes}, {"zone": "x"}).recommend  # sin zona fuera no se recomienda
    skipped_t = R({"labor": yes, "zone": yes, "random": no}, {"temporal": "x"})
    assert skipped_t.recommend and len(skipped_t.warnings) == 2
    assert R({"labor": yes, "zone": yes}, {}).warnings == ()


def test_group_bootstrap_descarta_division_por_cero():
    calls = iter(range(10))

    def stat(idx):
        if next(calls) % 2:
            raise ZeroDivisionError
        return float(len(idx))
    res = group_bootstrap(["a", "b", "c"], stat, n_boot=10)
    assert res.n_discarded == 5 and len(res.replicates) == 5
