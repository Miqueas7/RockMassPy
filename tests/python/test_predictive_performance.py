"""Nivel 3: modelo de desempeño y recomendación (Fase 4C, tarea 12; plan R9, R10 y R13). Solo datos sintéticos."""

import csv
import dataclasses
import json
import math
from types import SimpleNamespace

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from rockmasspy.history import audit_history  # noqa: E402
from rockmasspy.predictive import (RECOMMENDATION_COLUMNS, SyntheticTruth, fit_performance,  # noqa: E402
                                   isoprobability_grid, load_model, recommend, save_model, save_recommendations,
                                   synthetic_history)

SENT = "ZZSENT"
N_BOOT = 200
TRUE = {"ln_q": -0.5, "ln_de": 1.0, "support_rank": -0.6, "ln_exposure": 0.8}


def _sentinel(h):
    """Centinela en las columnas de identificación y en la litología (R13)."""
    ts = tuple(dataclasses.replace(t, labor_codigo=f"{SENT}-{t.labor_codigo}", zona_nivel=f"{SENT}-{t.zona_nivel}",
                                   litologia=SENT, este_m=123456.0, norte_m=654321.0) for t in h.tramos)
    return dataclasses.replace(h, tramos=ts)


@pytest.fixture(scope="module")
def big():
    # ~1400 tramos: con 700 el IC de la mejora sobre la línea base aún toca el cero en algunas semillas
    h, _ = synthetic_history(seed=0, n_zones=8, labors_per_zone=12, tramos_per_labor=15)
    h = _sentinel(h)
    return h, fit_performance(h, n_boot=N_BOOT)


@pytest.fixture(scope="module")
def small():
    h, _ = synthetic_history(seed=1, n_zones=2, labors_per_zone=3, tramos_per_labor=5)
    return h, fit_performance(h, n_boot=N_BOOT)


def _p(tramo, **kw):
    return dataclasses.replace(tramo, **kw)


def test_recupera_signos_y_orden_de_magnitud(big):
    _, m = big
    c = m.coefficients
    for name, true in TRUE.items():
        assert np.sign(c[name]) == np.sign(true), (name, c[name])
        # el logit marginal sale atenuado por los efectos de zona y labor: se pide el orden de magnitud
        assert 0.5 * abs(true) <= abs(c[name]) <= 1.5 * abs(true), (name, c[name])
    lo, hi = zip(*m.coef_ci)
    assert all(a <= b for a, b in zip(lo, hi))
    assert m.features[:4] == ("ln_q", "ln_de", "support_rank", "ln_exposure")
    assert m.signs[:5] == (-1, 1, -1, 1, 1) and m.use_depth
    assert m.labor_types == ("Galería", "Rampa", "Tajeo")  # una-caliente contra Galería


def test_con_efecto_del_sitio_y_historico_grande_es_site(big):
    h, m = big
    assert m.calibration == "site", m.calibration_reason
    assert m.validation.recommend
    assert set(m.metrics) >= {"brier", "auc", "average_precision", "calibration_intercept", "calibration_slope"}
    assert 0.5 < m.metrics["auc"] < 1 and 0 < m.metrics["brier"] < 0.25
    assert m.calibration_curve and sum(n for _, _, n in m.calibration_curve) == m.metrics["n"]
    # la preparación es la misma que cuenta audit_history
    r3 = next(r for r in audit_history(h).readiness if r.level == 3)
    assert r3.ready and m.counts["minority_class"] == r3.counts["minority_class"]
    assert m.counts["minority_class_minimum"] == r3.minimums["minority_class"]
    assert m.counts["parameters"] == r3.counts["parameters"] == len(m.features)


@pytest.mark.parametrize("seed", [1, 2])
def test_con_efecto_del_sitio_otras_semillas(seed):
    h, _ = synthetic_history(seed=seed, n_zones=8, labors_per_zone=12, tramos_per_labor=15)
    assert fit_performance(h, n_boot=N_BOOT, seed=seed).calibration == "site"


def test_sin_efecto_del_sitio_no_es_site_en_la_mayoria():
    levels = []
    for seed in range(5):
        h, _ = synthetic_history(seed=seed, n_zones=6, labors_per_zone=8, tramos_per_labor=15,
                                 truth=SyntheticTruth(site_effect=False))
        levels.append(fit_performance(h, n_boot=N_BOOT, seed=seed).calibration)
    assert sum(lv == "site" for lv in levels) <= 1, levels
    assert all(lv == "partial" or lv == "site" for lv in levels)  # cumplen el mínimo: el motivo es la línea base


def test_bajo_el_minimo_no_calibrado_y_no_elige(small):
    h, m = small
    assert m.calibration == "not_calibrated" and "below the level-3 minimum" in m.calibration_reason
    recs = recommend(m, h.tramos[:5], threshold=0.5, exposure_days=365)
    assert all(r.chosen is None and r.reason.startswith("no choice (not_calibrated)") for r in recs)
    assert all(len(r.options) == 5 and r.calibration == "not_calibrated" for r in recs)


def test_partial_muestra_probabilidades_sin_elegir(big):
    h, m = big
    pm = dataclasses.replace(m, calibration="partial", calibration_reason="test")
    r = recommend(pm, h.tramos[:1], threshold=0.9, exposure_days=100)[0]
    assert r.chosen is None and r.reason == "no choice (partial): test" and len(r.options) == 5


def test_cota_activa_en_el_sostenimiento_no_elige(big):
    h, m = big
    assert "support_rank" not in m.active_bounds
    # con la cota activa el modelo no distingue tipos: elegir el más liviano sería peligroso
    bm = dataclasses.replace(m, active_bounds=("support_rank",))
    recs = recommend(bm, h.tramos[:10], threshold=0.9, exposure_days=100)
    assert all(r.chosen is None and r.reason == "support effect not identified (bound active)" for r in recs)
    assert all(len(r.options) == 5 for r in recs)
    # una cota activa en otra variable solo avisa
    assert m.active_bounds and all(any(f"sign bound active for {a}" in w for w in m.warnings)
                                   for a in m.active_bounds)
    assert any(r.chosen for r in recommend(m, h.tramos[:40], threshold=0.35, exposure_days=365))


def test_sin_fallas_no_calibrado_sin_caerse(tmp_path):
    h, _ = synthetic_history(seed=4, n_zones=3, labors_per_zone=4, tramos_per_labor=8)
    h = dataclasses.replace(h, inspections=tuple(dataclasses.replace(i, estado="Estable", tipo_falla=None)
                                                 for i in h.inspections))
    m = fit_performance(h, n_boot=20)
    assert m.fit is None and m.calibration == "not_calibrated" and "no events / no non-events" in m.calibration_reason
    assert m.coefficients == {} and any("no events / no non-events" in w for w in m.warnings)
    r = recommend(m, h.tramos[:2], threshold=0.2, exposure_days=365)
    assert all(x.options == () and x.chosen is None and x.reason.startswith("no choice (not_calibrated)") for x in r)
    m2 = load_model(save_model(m, tmp_path / "m.json"))
    assert m2.fit is None and m2.calibration == "not_calibrated"
    with pytest.raises(ValueError, match="no fit"):
        isoprobability_grid(m, support_code="I", exposure_days=365, q_range=(0.1, 10), de_range=(1, 10))


def test_elige_el_mas_liviano_que_cumple(big):
    h, m = big
    recs = recommend(m, h.tramos[:40], threshold=0.35, exposure_days=365)
    assert any(r.chosen for r in recs) and any(r.reason == "none meets the threshold" for r in recs)
    for r in recs:
        assert [o.order for o in r.options] == [1, 2, 3, 4, 5]
        assert all(o.p_low <= o.p_failure <= o.p_high for o in r.options)
        first = next((o.code for o in r.options if o.p_high <= 0.35), None)
        assert r.chosen == first and (r.reason is None) == (first is not None)
        assert len(r.reasons) == 3 and all(x.effect in ("raises", "lowers", "neutral") for x in r.reasons)
        assert r.id_tramo is not None and r.threshold == 0.35 and r.level == 0.9


def _order(r):
    return {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}.get(r.chosen, 6)  # ninguno = más pesado que todos


def test_monotonia_umbral_y_macizo(big):
    h, m = big
    t = h.tramos[0]
    by_thr = [_order(recommend(m, [t], threshold=thr, exposure_days=365)[0]) for thr in (0.1, 0.2, 0.3, 0.5, 0.8)]
    assert by_thr == sorted(by_thr, reverse=True), by_thr  # más umbral: igual o más liviano
    by_q = [_order(recommend(m, [_p(t, q_valor=q)], threshold=0.4, exposure_days=365)[0])
            for q in (30.0, 10.0, 3.0, 1.0, 0.3, 0.1)]
    assert by_q == sorted(by_q), by_q  # peor macizo: igual o más pesado
    assert len(set(by_q)) > 1


def test_umbral_y_exposicion_obligatorios(big):
    h, m = big
    with pytest.raises(TypeError, match="threshold"):
        recommend(m, h.tramos[:1], exposure_days=365)
    with pytest.raises(TypeError, match="exposure_days"):
        recommend(m, h.tramos[:1], threshold=0.2)
    with pytest.raises(ValueError, match="threshold is required"):
        recommend(m, h.tramos[:1], threshold=None, exposure_days=365)
    with pytest.raises(ValueError, match="exposure_days is required"):
        recommend(m, h.tramos[:1], threshold=0.2, exposure_days=None)
    for bad in (0, 1, 1.5, True):
        with pytest.raises(ValueError, match="threshold must be"):
            recommend(m, h.tramos[:1], threshold=bad, exposure_days=365)
    with pytest.raises(ValueError, match="exposure_days must be"):
        recommend(m, h.tramos[:1], threshold=0.2, exposure_days=-3)


def test_alerta_de_extrapolacion(big):
    h, m = big
    t = h.tramos[0]
    normal = recommend(m, [t], threshold=0.3, exposure_days=365)[0]
    assert not any("ln_q" in n for n in normal.extrapolation_notes)
    r = recommend(m, [_p(t, q_valor=1e5)], threshold=0.3, exposure_days=365)[0]
    assert r.extrapolation and "ln_q outside the training range" in r.extrapolation_notes
    r = recommend(m, [_p(t, tipo_labor="Chimenea")], threshold=0.3, exposure_days=365)[0]
    assert "tipo_labor not seen in training: read as the reference type" in r.extrapolation_notes
    r = recommend(m, [t], threshold=0.3, exposure_days=20000)[0]
    assert "ln_exposure outside the training range" in r.extrapolation_notes


def test_tramo_minimo_dict_y_datos_faltantes(big):
    h, m = big
    t = h.tramos[0]
    d = {"id_tramo": "N1", "q_valor": t.q_valor, "luz_m": t.luz_m, "esr": t.esr, "tipo_labor": t.tipo_labor,
         "profundidad_m": t.profundidad_m}
    a, b = recommend(m, [d, SimpleNamespace(**d)], threshold=0.3, exposure_days=365)
    assert a.options == b.options == recommend(m, [t], threshold=0.3, exposure_days=365)[0].options
    r = recommend(m, [{**d, "luz_m": None, "profundidad_m": None}], threshold=0.3, exposure_days=365)[0]
    assert r.options == () and r.chosen is None and r.reason == "missing or invalid input: luz_m, profundidad_m"


def test_protocolo_de_la_practica(big):
    h, m = big

    class Practice:
        def conformal_set(self, tramo):
            return ("II", "III")
    r = recommend(m, h.tramos[:2], threshold=0.3, exposure_days=365, practice=Practice())
    assert all(x.conformal_set == ("II", "III") for x in r)
    assert recommend(m, h.tramos[:1], threshold=0.3, exposure_days=365)[0].conformal_set is None


def test_json_ida_y_vuelta_exacta_y_sin_ids(big, tmp_path):
    h, m = big
    path = save_model(m, tmp_path / "model.json")
    text = path.read_text(encoding="utf-8")
    m2 = load_model(path)
    X = np.array([[0.5, 1.0, 3.0, 5.9, 400.0, 0.0, 1.0], [-2.0, 0.3, 1.0, 4.0, 200.0, 1.0, 0.0]])
    for a, b in zip(m.fit.predict_interval(X), m2.fit.predict_interval(X)):
        assert np.array_equal(a, b)
    r1 = recommend(m, h.tramos[:30], threshold=0.3, exposure_days=365)
    assert r1 == recommend(m2, h.tramos[:30], threshold=0.3, exposure_days=365)
    assert m2.features == m.features and m2.support_types == m.support_types and m2.calibration == m.calibration
    assert m2.validation.recommend == m.validation.recommend and m2.coef_ci == m.coef_ci
    d = json.loads(text)
    assert d["schema_version"] == 1 and "version" in d
    # nunca filas ni ids: ningún id_tramo, labor, zona, coordenada ni litología del entrenamiento
    assert SENT not in text and "123456" not in text and "654321" not in text
    assert not any(t.id_tramo in text for t in h.tramos)
    d["schema_version"] = 99
    (tmp_path / "bad.json").write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(ValueError, match="schema_version"):
        load_model(tmp_path / "bad.json")


def test_privacidad_mensajes_razones_y_repr(big):
    h, m = big
    recs = recommend(m, h.tramos[:30] + (_p(h.tramos[0], q_valor=1e5),), threshold=0.3, exposure_days=365)
    msgs = [m.calibration_reason, *m.warnings, *m.validation.skipped.values()]
    for r in recs:
        msgs += [r.reason or "", *r.extrapolation_notes, *(x.variable for x in r.reasons)]
    assert r.extrapolation and not any(SENT in s for s in [repr(m), repr(recs), *msgs])
    # el id_tramo es un campo de la recomendación (sí sale en su repr), nunca parte de un texto
    ids = {t.id_tramo for t in h.tramos}
    assert not any(i in s for s in msgs for i in ids)


def test_save_recommendations_con_columnas_vacias(big, tmp_path):
    h, m = big
    recs = recommend(m, h.tramos[:4] + ({"id_tramo": "N9", "q_valor": None},), threshold=0.3, exposure_days=365)
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
    assert g.tipo_labor == "Galería" and g.depth_m == pytest.approx(m.maha_mean[4])
    with pytest.raises(ValueError, match="support_code"):
        isoprobability_grid(m, support_code="X", exposure_days=365, q_range=(0.01, 100), de_range=(1, 20))


def test_calidad_rmr_y_errores(small):
    h, _ = synthetic_history(seed=3, n_zones=4, labors_per_zone=5, tramos_per_labor=12)
    m = fit_performance(h, quality="rmr", n_boot=50)
    assert m.features[0] == "rmr" and m.coefficients["rmr"] <= 0
    with pytest.raises(ValueError, match="quality='q'"):
        isoprobability_grid(m, support_code="I", exposure_days=365, q_range=(0.1, 10), de_range=(1, 10))
    with pytest.raises(ValueError, match="quality must be"):
        fit_performance(h, quality="gsi")
    empty = dataclasses.replace(h, inspections=())
    with pytest.raises(ValueError, match="at least 2 usable tramos"):
        fit_performance(empty)
    assert math.isfinite(m.maha_p99)
