"""Nivel 3: tasa de falla con fragilidad gamma por labor y recomendación (Fase 4C, tarea 12; plan R9, R10 y R13). Solo datos sintéticos."""

import csv
import dataclasses
import json
import math
from types import SimpleNamespace

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from rockmasspy.history import History, audit_history  # noqa: E402
from rockmasspy.predictive import (RECOMMENDATION_COLUMNS, SyntheticTruth, fit_performance,  # noqa: E402
                                   isoprobability_grid, load_model, poisson_deviance, recommend, save_model,
                                   save_recommendations, synthetic_history)

SENT = "ZZSENT"
N_BOOT = 200
TRUE = {"ln_q": -0.5, "ln_de": 1.0, "support_rank": -0.6}  # log λ por día (SyntheticTruth)
REC = {"threshold": 0.35, "exposure_days": 365}


def _sentinel(h):
    """Centinela en las columnas de identificación y en la litología (R13)."""
    ts = tuple(dataclasses.replace(t, labor_codigo=f"{SENT}-{t.labor_codigo}", zona_nivel=f"{SENT}-{t.zona_nivel}",
                                   litologia=SENT, este_m=123456.0, norte_m=654321.0) for t in h.tramos)
    return dataclasses.replace(h, tramos=ts)


@pytest.fixture(scope="module")
def big():
    # ~1400 tramos: con ~700, «site» sale en 7 de 10 semillas
    h, _ = synthetic_history(seed=0, n_zones=8, labors_per_zone=12, tramos_per_labor=15)
    h = _sentinel(h)
    return h, fit_performance(h, n_boot=N_BOOT)


@pytest.fixture(scope="module")
def small():
    h, _ = synthetic_history(seed=1, n_zones=2, labors_per_zone=3, tramos_per_labor=5)
    return h, fit_performance(h, n_boot=N_BOOT)


@pytest.fixture(scope="module")
def null():
    h, _ = synthetic_history(seed=0, n_zones=6, labors_per_zone=8, tramos_per_labor=15,
                             truth=SyntheticTruth(site_effect=False))
    return h, fit_performance(h, n_boot=N_BOOT)


def _p(tramo, **kw):
    return dataclasses.replace(tramo, **kw)


def _ok(big):
    """Un tramo del centro del dominio: con el modelo grande, elige."""
    h, m = big
    return next(t for t in h.tramos if recommend(m, [t], **REC)[0].chosen)


# ---------- ajuste y estado ----------

def test_recupera_signos_y_orden_de_magnitud(big):
    _, m = big
    c = m.coefficients
    for name, true in TRUE.items():
        assert np.sign(c[name]) == np.sign(true), (name, c[name])
        # la tasa marginal sale atenuada por los efectos de zona y labor: se pide el orden de magnitud
        assert 0.5 * abs(true) <= abs(c[name]) <= 1.5 * abs(true), (name, c[name])
    assert all(a <= b for a, b in m.coef_ci)
    assert m.features[:3] == ("ln_q", "ln_de", "support_rank") and "ln_exposure" not in m.features
    assert m.signs[:4] == (-1, 1, -1, 1) and m.use_depth
    assert m.labor_types == ("Galería", "Rampa", "Tajeo")  # una-caliente contra Galería
    assert m.fit.n_events == m.counts["failures"]
    # fragilidad por labor y covarianza agrupada por zona (8 zonas: t con 7 grados de libertad)
    assert 0.1 < m.fit.theta < 1.5 and m.fit.cov_kind == "cluster" and m.fit.df == 7
    assert m.fit.n_groups == m.counts["labors"]


def test_con_efecto_del_sitio_y_historico_grande_es_site(big):
    h, m = big
    assert m.calibration == "site", m.calibration_reason
    assert m.validation.recommend
    assert set(m.metrics) == {"n", "poisson_deviance", "observed_expected", "calibration_slope", "c_index"}
    assert 0.6 < m.metrics["c_index"] < 1 and 0.8 < m.metrics["observed_expected"] < 1.25
    assert 0.6 < m.metrics["calibration_slope"] < 1.4
    assert m.calibration_curve and sum(n for _, _, n in m.calibration_curve) == m.metrics["n"]
    # la preparación es la de audit_history (E)
    r3 = next(r for r in audit_history(h).readiness if r.level == 3)
    assert r3.ready and m.counts["minority_class"] == r3.counts["minority_class"]
    assert m.counts["minority_class_minimum"] == r3.minimums["minority_class"]


@pytest.mark.parametrize("seed", [1, 2])
def test_con_efecto_del_sitio_otras_semillas(seed):
    h, _ = synthetic_history(seed=seed, n_zones=8, labors_per_zone=12, tramos_per_labor=15)
    assert fit_performance(h, n_boot=N_BOOT, seed=seed).calibration == "site"


def test_sin_efecto_del_sitio_no_es_site_en_la_mayoria(null):
    levels = [null[1].calibration]
    for seed in range(1, 5):
        h, _ = synthetic_history(seed=seed, n_zones=6, labors_per_zone=8, tramos_per_labor=15,
                                 truth=SyntheticTruth(site_effect=False))
        levels.append(fit_performance(h, n_boot=N_BOOT, seed=seed).calibration)
    assert sum(lv == "site" for lv in levels) <= 1, levels


def test_bajo_el_minimo_no_calibrado_y_no_elige(small):
    h, m = small
    assert m.calibration == "not_calibrated" and "below the level-3 minimum" in m.calibration_reason
    recs = recommend(m, h.tramos[:5], threshold=0.5, exposure_days=365)
    assert all(r.chosen is None and r.reason.startswith("no choice (not_calibrated)") for r in recs)
    assert all(len(r.options) == 5 and r.calibration == "not_calibrated" for r in recs)


def test_sin_fallas_no_calibrado_sin_caerse(tmp_path):
    h, _ = synthetic_history(seed=4, n_zones=3, labors_per_zone=4, tramos_per_labor=8)
    h = dataclasses.replace(h, inspections=tuple(dataclasses.replace(i, estado="Estable", tipo_falla=None)
                                                 for i in h.inspections))
    m = fit_performance(h, n_boot=20)
    assert m.fit is None and m.calibration == "not_calibrated" and "no events / no non-events" in m.calibration_reason
    assert m.coefficients == {} and any("no events / no non-events" in w for w in m.warnings)
    r = recommend(m, h.tramos[:2], threshold=0.2, exposure_days=365)
    assert all(x.options == () and x.chosen is None and x.reason.startswith("no choice (not_calibrated)") for x in r)
    assert m.counts["tramos"] < 100
    with pytest.raises(ValueError, match="fewer than 100 usable tramos"):  # casi reconstruiría las filas
        save_model(m, tmp_path / "m.json")
    assert not (tmp_path / "m.json").exists()
    with pytest.raises(ValueError, match="no fit"):
        isoprobability_grid(m, support_code="I", exposure_days=365, q_range=(0.1, 10), de_range=(1, 10))


# ---------- D: validación ----------

def test_motivo_de_calibracion_sale_de_los_bloqueos(null):
    _, m = null
    assert m.calibration == "partial"
    for name in ("labor", "zone"):
        for b in m.validation.results[name].blockers:
            assert f"{name}: {b}" in m.calibration_reason
    assert m.calibration_reason.startswith(("labor: ", "zone: "))


def test_avisos_de_la_validacion_pasan_al_modelo():
    h, _ = synthetic_history(seed=2, n_zones=4, labors_per_zone=5, tramos_per_labor=12)
    h = dataclasses.replace(h, tramos=tuple(_p(t, fecha_evaluacion="2021-06-01") for t in h.tramos))  # un solo año
    m = fit_performance(h, n_boot=50)
    assert "temporal" in m.validation.skipped and m.validation.warnings
    assert all(w in m.warnings for w in m.validation.warnings)


# ---------- recomendación ----------

def test_partial_muestra_probabilidades_sin_elegir(big):
    h, m = big
    pm = dataclasses.replace(m, calibration="partial", calibration_reason="test")
    r = recommend(pm, h.tramos[:1], threshold=0.9, exposure_days=100)[0]
    assert r.chosen is None and r.reason == "no choice (partial): test" and len(r.options) == 5


def test_elige_el_mas_liviano_elegible_que_cumple(big):
    h, m = big
    recs = recommend(m, h.tramos[:60], **REC)
    assert any(r.chosen for r in recs) and any(r.reason == "no eligible type meets the threshold" for r in recs)
    for r in recs:
        assert [o.order for o in r.options] == [1, 2, 3, 4, 5]
        assert all(o.p_low <= o.p_failure <= o.p_high for o in r.options)
        if r.reason in (None, "no eligible type meets the threshold"):
            first = next((o.code for o in r.options if o.eligible and o.p_high <= 0.35), None)
            assert r.chosen == first and (r.reason is None) == (first is not None)
        assert len(r.reasons) == 3 and all(x.effect in ("raises", "lowers", "neutral") for x in r.reasons)
        assert r.id_tramo is not None and r.threshold == 0.35 and r.level == 0.9


def _order(r):
    return {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}.get(r.chosen, 6)  # ninguno = más pesado que todos


def test_monotonia_umbral_y_macizo(big):
    h, m = big
    t = _ok(big)
    by_thr = [_order(recommend(m, [t], threshold=thr, exposure_days=365)[0]) for thr in (0.1, 0.2, 0.3, 0.5, 0.8)]
    assert by_thr == sorted(by_thr, reverse=True), by_thr  # más umbral: igual o más liviano
    by_q = [_order(recommend(m, [_p(t, q_valor=q)], threshold=0.4, exposure_days=365)[0])
            for q in (30.0, 10.0, 3.0, 1.0, 0.3, 0.1)]
    assert by_q == sorted(by_q), by_q  # peor macizo: igual o más pesado
    assert len(set(by_q)) > 1


def test_umbral_horizonte_y_nivel(big):
    h, m = big
    with pytest.raises(TypeError, match="threshold"):
        recommend(m, h.tramos[:1], exposure_days=365)
    with pytest.raises(TypeError, match="exposure_days"):
        recommend(m, h.tramos[:1], threshold=0.2)
    with pytest.raises(ValueError, match="threshold is required"):
        recommend(m, h.tramos[:1], threshold=None, exposure_days=365)
    with pytest.raises(ValueError, match="exposure_days is required"):
        recommend(m, h.tramos[:1], threshold=0.2, exposure_days=None)
    for bad in (0, 1, 1.5, True, math.nan):
        with pytest.raises(ValueError, match="threshold must be"):
            recommend(m, h.tramos[:1], threshold=bad, exposure_days=365)
    with pytest.raises(ValueError, match="exposure_days must be"):
        recommend(m, h.tramos[:1], threshold=0.2, exposure_days=-3)
    # B5: level en [0.5, 1)
    for bad in (0.4, 1.0, 0.0, True):
        with pytest.raises(ValueError, match=r"level must be in \[0.5, 1\)"):
            recommend(m, h.tramos[:1], **REC, level=bad)
    assert recommend(m, h.tramos[:1], **REC, level=0.5)[0].level == 0.5


def test_mas_horizonte_mas_probabilidad(big):
    _, m = big
    t = _ok(big)
    a, b = recommend(m, [t], threshold=0.35, exposure_days=200)[0], recommend(m, [t], threshold=0.35,
                                                                               exposure_days=600)[0]
    assert all(x.p_failure < y.p_failure for x, y in zip(a.options, b.options))


# ---------- B: seguridad de la recomendación ----------

def test_b1_extrapolacion_del_tramo_bloquea(big):
    h, m = big
    t = _ok(big)
    for tramo, note, kw in ((_p(t, q_valor=1e5), "ln_q outside the training range", {}),
                            (_p(t, luz_m=200.0), "ln_de outside the training range", {}),
                            (_p(t, profundidad_m=5000.0), "depth_m outside the training range", {}),
                            (_p(t, tipo_labor="Chimenea"), "tipo_labor missing or not seen in training", {}),
                            (_p(t, tipo_labor=None), "tipo_labor missing or not seen in training", {}),
                            (t, "exposure_days outside the training range of exposures", {"exposure_days": 20000})):
        r = recommend(m, [tramo], **{**REC, **kw})[0]
        assert r.chosen is None and r.reason == "input outside the training domain (extrapolation)", note
        assert r.extrapolation and note in r.extrapolation_notes
        assert len(r.options) == 5 and all(o.extrapolated for o in r.options)  # el tramo extrapola: todas


def test_b1_mahalanobis_sobre_p99_no_elige(big):
    h, m = big
    t = _ok(big)
    r = recommend(dataclasses.replace(m, maha_p99=0.0), [t], **REC)[0]
    assert r.chosen is None and all(o.extrapolated and not o.eligible and o.note == "extrapolation"
                                    for o in r.options)
    assert any(n.startswith("Mahalanobis distance above") for n in r.extrapolation_notes)


def test_b2_solo_tipos_con_historia(big):
    h, m = big
    assert all(n >= 10 for n in m.support_counts) and len(m.support_counts) == 5
    t = _ok(big)
    chosen = recommend(m, [t], **REC)[0].chosen
    counts = tuple(5 if c == chosen else n for (c, _), n in zip(m.support_types, m.support_counts))
    r = recommend(dataclasses.replace(m, support_counts=counts), [t], **REC)[0]
    opt = next(o for o in r.options if o.code == chosen)
    assert not opt.eligible and opt.note == "not enough history" and opt.history == 5
    assert r.chosen != chosen and (r.chosen is None or _order(r) > {"I": 1, "II": 2, "III": 3, "IV": 4}[chosen])


def test_b3_efecto_del_sostenimiento_identificado(big):
    h, m = big
    assert m.coef_ci[2][1] < 0
    ci = list(m.coef_ci)
    ci[2] = (ci[2][0], 0.01)
    r = recommend(dataclasses.replace(m, coef_ci=tuple(ci)), h.tramos[:5], **REC)
    assert all(x.chosen is None and x.reason == "support effect not identified" and len(x.options) == 5 for x in r)
    r = recommend(dataclasses.replace(m, active_bounds=("support_rank",)), h.tramos[:5], **REC)
    assert all(x.chosen is None and x.reason == "support effect not identified (bound active)" for x in r)


def test_b4_cotas_activas(big):
    h, m = big
    for var in ("ln_q", "ln_de"):
        r = recommend(dataclasses.replace(m, active_bounds=(var,)), h.tramos[:3], **REC)
        assert all(x.chosen is None and x.reason == "model ignores rock quality/span (bound active)" for x in r)
        assert all(f"sign bound active for {var}" in x.notes for x in r)
    # la cota de profundidad solo agrega la nota: sigue eligiendo
    dm = dataclasses.replace(m, active_bounds=("depth_m",))
    r = recommend(dm, [_ok(big)], **REC)[0]
    assert r.chosen and r.notes == ("sign bound active for depth_m",)


def test_b6_entradas_invalidas_no_tumban_el_lote(big):
    h, m = big
    t = _ok(big)
    d = {"id_tramo": "N1", "q_valor": t.q_valor, "luz_m": t.luz_m, "esr": t.esr, "tipo_labor": t.tipo_labor,
         "profundidad_m": t.profundidad_m}
    a, b = recommend(m, [d, SimpleNamespace(**d)], **REC)
    assert a.options == b.options == recommend(m, [t], **REC)[0].options
    bad = [{**d, "luz_m": None}, {**d, "q_valor": math.nan}, {**d, "esr": math.inf}, {**d, "q_valor": "x"},
           {**d, "q_valor": -1.0}, {**d, "profundidad_m": -5.0}, {**d, "luz_m": True}]
    cols = ["luz_m", "q_valor", "esr", "q_valor", "q_valor", "profundidad_m", "luz_m"]
    recs = recommend(m, bad + [{**d, "profundidad_m": 0.0}], **REC)
    for r, c in zip(recs, cols):
        assert r.options == () and r.chosen is None and r.reason == f"missing or invalid input: {c}"
    assert recs[-1].options  # profundidad 0 es válida (≥ 0)


def test_b6_practica_protocolo_y_errores(big):
    h, m = big
    seen = []

    class Practice:
        def conformal_set(self, tramo):
            seen.append(tramo.q_valor)  # recibe atributos aunque entre un dict
            return ("II", "III")

    class Broken:
        def conformal_set(self, tramo):
            raise RuntimeError(f"boom {SENT}")

    d = {"id_tramo": "N1", "q_valor": 2.0, "luz_m": 4.0, "esr": 1.6, "tipo_labor": "Galería", "profundidad_m": 300.0}
    r = recommend(m, [h.tramos[0], d], **REC, practice=Practice())
    assert all(x.conformal_set == ("II", "III") for x in r) and seen[-1] == 2.0
    r = recommend(m, [h.tramos[0], d], **REC, practice=Broken())
    assert all(x.conformal_set is None and "practice conformal set failed (RuntimeError)" in x.notes for x in r)
    assert not any(SENT in n for x in r for n in x.notes)
    assert recommend(m, h.tramos[:1], **REC)[0].conformal_set is None


# ---------- C: JSON ----------

def test_json_ida_y_vuelta_exacta_y_sin_ids(big, tmp_path):
    h, m = big
    path = save_model(m, tmp_path / "model.json")
    text = path.read_text(encoding="utf-8")
    m2 = load_model(path)
    X = np.array([[0.5, 1.0, 3.0, 400.0, 0.0, 1.0], [-2.0, 0.3, 1.0, 200.0, 1.0, 0.0]])
    for a, b in zip(m.fit.prob_interval(X, 365.0), m2.fit.prob_interval(X, 365.0)):
        assert np.array_equal(a, b)
    r1 = recommend(m, h.tramos[:30], **REC)
    assert r1 == recommend(m2, h.tramos[:30], **REC)
    assert m2.features == m.features and m2.support_types == m.support_types and m2.calibration == m.calibration
    assert m2.validation.recommend == m.validation.recommend and m2.coef_ci == m.coef_ci
    assert m2.fit.signs == m.fit.signs and m2.support_counts == m.support_counts
    d = json.loads(text)
    assert d["schema_version"] == 3 and "version" in d
    # nunca filas ni ids: ningún id_tramo, labor, zona, coordenada ni litología del entrenamiento
    assert SENT not in text and "123456" not in text and "654321" not in text
    assert not any(t.id_tramo in text for t in h.tramos)


def _bad_json(tmp_path, d, name):
    p = tmp_path / f"{name}.json"
    p.write_text(json.dumps(d), encoding="utf-8")
    return p


def test_json_validado_al_cargar(big, tmp_path):
    _, m = big
    base = json.loads(save_model(m, tmp_path / "ok.json").read_text(encoding="utf-8"))
    fit_bad_sign = {**base["fit"], "coef": [abs(c) + 0.1 for c in base["fit"]["coef"]]}
    cases = {
        "schema": ({**base, "schema_version": 2}, "unsupported performance model schema_version"),
        "unknown": ({**base, "rows": []}, "1 unknown key"),
        "named": ({**base, "theta": 0.5}, r"unexpected keys \['theta'\]"),
        "missing": ({k: v for k, v in base.items() if k != "maha_p99"}, r"missing keys \['maha_p99'\]"),
        "fit_extra": ({**base, "fit": {**base["fit"], "ids": []}}, "fit: 1 unknown key"),
        "calibration": ({**base, "calibration": "global"}, "calibration is not valid"),
        "order": ({**base, "support_types": [["I", 1], ["II", 1], *base["support_types"][2:]]}, "strictly increasing"),
        "malformed": ({**base, "support_types": [["I"], "II"]}, "support_types is not valid"),
        "lengths": ({**base, "train_min": base["train_min"][:-1]}, "lengths do not match"),
        "coef": ({**base, "fit": {**base["fit"], "coef": base["fit"]["coef"][:-1]}}, "lengths do not match"),
        "counts": ({**base, "support_counts": base["support_counts"][:-1]}, "one count per support type"),
        "text": ({**base, "maha_p99": "3.2"}, "maha_p99 is not valid"),
        "nan": ({**base, "train_max": [*base["train_max"][:-1], float("nan")]}, "train_max is not valid"),
        "signs": ({**base, "fit": fit_bad_sign}, "breaks its sign constraint"),
        "validation": ({**base, "validation": {"results": {"labor": {"x": 1}}, "skipped": {}}},
                       "fit or validation is not valid"),
    }
    for name, (d, msg) in cases.items():
        with pytest.raises(ValueError, match=msg) as e:
            load_model(_bad_json(tmp_path, d, name))
        assert "global" not in str(e.value) and "3.2" not in str(e.value)  # nunca repite valores del archivo
    (tmp_path / "raw.json").write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        load_model(tmp_path / "raw.json")


def test_json_manipulado_no_cambia_la_decision(null, tmp_path):
    h, m = null
    assert m.calibration == "partial"
    d = json.loads(save_model(m, tmp_path / "p.json").read_text(encoding="utf-8"))
    d["calibration"] = "site"  # I3: la calibración se recalcula con lo guardado
    with pytest.raises(ValueError, match="calibration does not match"):
        load_model(_bad_json(tmp_path, d, "flip"))
    assert load_model(tmp_path / "p.json").calibration == "partial"


def test_bloqueos_de_la_recomendacion(big, null):
    _, m = big
    assert m.recommendation_blockers == ()
    assert null[1].recommendation_blockers[0].startswith("no choice (partial): ")
    ci = list(m.coef_ci)
    ci[2] = (ci[2][0], 0.01)
    assert dataclasses.replace(m, coef_ci=tuple(ci)).recommendation_blockers == ("support effect not identified",)
    both = dataclasses.replace(m, active_bounds=("support_rank", "ln_de"))
    assert both.recommendation_blockers == ("support effect not identified (bound active)",
                                            "model ignores rock quality/span (bound active)")


def test_rango_es_la_posicion_y_no_el_valor_de_orden():
    # I1: con orden 1, 2, 3, 4, 10 el modelo es el mismo que con 1..5 (la escala es la posición)
    h, _ = synthetic_history(seed=2, n_zones=4, labors_per_zone=5, tramos_per_labor=12)
    st = tuple(dataclasses.replace(s, orden=10) if s.orden == 5 else s for s in h.support_types)
    a, b = fit_performance(h, n_boot=50), fit_performance(History(h.tramos, st, h.inspections), n_boot=50)
    np.testing.assert_allclose(a.fit.coef, b.fit.coef)
    assert b.support_types[-1] == ("V", 10) and b.train_max[2] == 4.0
    t = h.tramos[0]
    assert [o.p_high for o in recommend(a, [t], **REC)[0].options] == \
        [o.p_high for o in recommend(b, [t], **REC)[0].options]


def test_preparacion_con_las_filas_del_ajuste_rmr():
    # I2: con quality="rmr" la preparación cuenta solo las filas con RMR (aquí, de 2 zonas)
    h, _ = synthetic_history(seed=1, n_zones=6, labors_per_zone=10, tramos_per_labor=15)
    ts = tuple(t if t.zona_nivel in ("Z1", "Z2") else dataclasses.replace(t, rmr_valor=None) for t in h.tramos)
    h2 = History(ts, h.support_types, h.inspections)
    assert next(r for r in audit_history(h2).readiness if r.level == 3).ready  # la del histórico entero
    m = fit_performance(h2, quality="rmr", n_boot=50)
    assert m.calibration == "not_calibrated" and m.counts["zones"] == 2 and "zones short by 1" in m.calibration_reason


def test_tipo_labor_vacio_es_un_nivel_propio():
    h, _ = synthetic_history(seed=2, n_zones=4, labors_per_zone=5, tramos_per_labor=12)
    labs = sorted({t.labor_codigo for t in h.tramos})[:4]
    h2 = dataclasses.replace(h, tramos=tuple(dataclasses.replace(t, tipo_labor=None) if t.labor_codigo in labs else t
                                             for t in h.tramos))
    m = fit_performance(h2, n_boot=50)
    assert m.labor_types[-1] == "(missing)" and "tipo_labor=(missing)" in m.features
    assert any("own level (missing)" in w for w in m.warnings)
    r = recommend(m, [dataclasses.replace(h.tramos[0], tipo_labor=None)], **REC)[0]
    assert "tipo_labor missing or not seen in training" in r.extrapolation_notes


def test_pocas_zonas_usa_laplace_con_aviso(small):
    _, m = small
    assert m.fit.cov_kind == "laplace" and any("fewer than 5 zones: Laplace covariance" in w for w in m.warnings)


def test_poisson_deviance_exportada():
    y = np.array([1.0, 0.0])
    p = np.array([0.5, 0.2])
    mu = -np.log1p(-p)
    assert poisson_deviance(y, p) == pytest.approx(np.mean(mu - y * np.log(mu)))


def test_rangos_redondeados_hacia_afuera(big, small):
    h, m = big
    X = np.array([[math.log(t.q_valor), math.log(t.luz_m / t.esr)] for t in h.tramos])
    assert m.train_min[0] <= X[:, 0].min() and m.train_max[0] >= X[:, 0].max()
    assert m.train_min[1] <= X[:, 1].min() and m.train_max[1] >= X[:, 1].max()
    for v in (*m.train_min, *m.train_max, m.exposure_min, m.exposure_max):
        assert v == 0 or float(f"{v:.3g}") == v or abs(v) < 1e-3, v
    assert not any("fewer than 100" in w for w in m.warnings)
    assert any("fewer than 100 usable tramos" in w for w in small[1].warnings)


def test_privacidad_mensajes_razones_y_repr(big):
    h, m = big
    recs = recommend(m, h.tramos[:30] + (_p(h.tramos[0], q_valor=1e5),), **REC)
    msgs = [m.calibration_reason, *m.warnings, *m.validation.skipped.values()]
    for r in recs:
        msgs += [r.reason or "", *r.extrapolation_notes, *r.notes, *(x.variable for x in r.reasons)]
    assert r.extrapolation and not any(SENT in s for s in [repr(m), repr(recs), *msgs])
    # el id_tramo es un campo de la recomendación (sí sale en su repr), nunca parte de un texto
    ids = {t.id_tramo for t in h.tramos}
    assert not any(i in s for s in msgs for i in ids)


def test_save_recommendations_con_columnas_vacias(big, tmp_path):
    h, m = big
    recs = recommend(m, h.tramos[:4] + ({"id_tramo": "N9", "q_valor": None},), **REC)
    p = save_recommendations(recs, tmp_path / "rec.csv")
    lines = p.read_text(encoding="utf-8-sig").splitlines()
    sep = ";" if ";" in lines[0] else ","
    rows = list(csv.reader(lines, delimiter=sep))
    assert tuple(rows[0]) == RECOMMENDATION_COLUMNS
    body = [dict(zip(rows[0], r)) for r in rows[1:]]
    assert len(body) == 4 * 5 + 1
    assert all(r["decision_ingeniero"] == "" and r["motivo"] == "" for r in body)
    assert body[-1]["id_tramo"] == "N9" and body[-1]["tipo"] == ""
    assert {r["tipo"] for r in body[:5]} == {"I", "II", "III", "IV", "V"}
    assert not any(SENT in line for line in lines)


def test_isoprobabilidades(big):
    _, m = big
    g = isoprobability_grid(m, support_code="II", exposure_days=365, q_range=(0.01, 100), de_range=(1, 20), n=12)
    assert g.log10_q.shape == g.log10_de.shape == g.p_failure.shape == (12, 12)
    assert np.all(np.diff(g.p_failure, axis=1) <= 1e-12)  # más Q (columnas), menos P(falla)
    assert np.all(np.diff(g.p_failure, axis=0) >= -1e-12)  # más De (filas), más P(falla)
    heavy = isoprobability_grid(m, support_code="V", exposure_days=365, q_range=(0.01, 100), de_range=(1, 20), n=12)
    assert np.all(heavy.p_failure <= g.p_failure + 1e-12)
    longer = isoprobability_grid(m, support_code="II", exposure_days=730, q_range=(0.01, 100), de_range=(1, 20), n=12)
    assert np.all(longer.p_failure >= g.p_failure)
    assert g.tipo_labor == "Galería" and g.depth_m == pytest.approx(m.maha_mean[3])
    with pytest.raises(ValueError, match="support_code"):
        isoprobability_grid(m, support_code="X", exposure_days=365, q_range=(0.01, 100), de_range=(1, 20))


def test_calidad_rmr_y_errores():
    h, _ = synthetic_history(seed=3, n_zones=4, labors_per_zone=5, tramos_per_labor=12)
    m = fit_performance(h, quality="rmr", n_boot=50)
    assert m.features[0] == "rmr" and m.coefficients["rmr"] <= 0
    with pytest.raises(ValueError, match="quality='q'"):
        isoprobability_grid(m, support_code="I", exposure_days=365, q_range=(0.1, 10), de_range=(1, 10))
    with pytest.raises(ValueError, match="quality must be"):
        fit_performance(h, quality="gsi")
    with pytest.raises(ValueError, match="at least 2 usable tramos"):
        fit_performance(dataclasses.replace(h, inspections=()))
    assert math.isfinite(m.maha_p99)
