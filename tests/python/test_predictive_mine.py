"""Mina sintética realista (Fase 5, tareas 2 a 4). Solo datos sintéticos; los rangos salen de
docs/investigacion/CALIBRACION_MINA_SINTETICA.md."""

import dataclasses
import datetime
import math
import re
from collections import Counter, defaultdict

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from rockmasspy.history import audit_history, labor_key, load_history, save_history_xlsx, tramo_outcomes  # noqa: E402
from rockmasspy.predictive import SCENARIOS, MineScenario, MineTruth, synthetic_mine  # noqa: E402
from rockmasspy.predictive.mine import _DEFECT_KINDS, _chart_rank, _table_rank  # noqa: E402
from rockmasspy.predictive.synthetic import LITHOLOGIES  # noqa: E402

_ORDER = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}


@pytest.fixture(scope="module")
def bases():
    """La mina base con las semillas 0 a 5, generada una vez (History y MineTruth son inmutables)."""
    return {seed: synthetic_mine(seed=seed) for seed in range(6)}


@pytest.fixture(scope="module")
def grandes():
    return [synthetic_mine("large_mine", seed=seed) for seed in range(3)]


def test_misma_semilla_misma_mina_y_otra_semilla_otra():
    a, ta = synthetic_mine(seed=3)
    b, tb = synthetic_mine(seed=3)
    c, _ = synthetic_mine(seed=4)
    assert a == b and ta == tb and isinstance(ta, MineTruth)
    assert ta.scenario == SCENARIOS["base"] and ta.defects == ()
    assert a != c
    assert synthetic_mine("small_mine", seed=1)[0] == synthetic_mine(SCENARIOS["small_mine"], seed=1)[0]


def test_escenarios_y_validacion():
    assert all(name == s.name for name, s in SCENARIOS.items())
    assert {"base", "ngi_site", "worse_site", "better_site", "shifted_correlation", "conservative_practice",
            "incoherent_practice", "mine_practice", "noisy_mapping", "small_mine", "large_mine"} == set(SCENARIOS)
    assert MineScenario(practice_gsi_cuts=[20, 30, 40, 50]).practice_gsi_cuts == (20, 30, 40, 50)
    with pytest.raises(ValueError, match="unknown scenario"):
        synthetic_mine("no_existe")
    with pytest.raises(ValueError, match="practice_gsi_cuts"):
        MineScenario(practice_gsi_cuts=(10, 5, 20, 30))
    with pytest.raises(ValueError, match="standard deviations"):
        MineScenario(sd_mapping_rqd=-1)
    with pytest.raises(ValueError, match="probabilities"):
        MineScenario(p_lighter=0.7, p_heavier=0.5)
    with pytest.raises(ValueError, match="practice_mode"):
        MineScenario(practice_mode="otra")
    with pytest.raises(ValueError, match="n_zones"):
        MineScenario(n_zones=0)
    with pytest.raises(ValueError):
        MineScenario(table_change_date="3-ene-2022")


def test_ida_y_vuelta_por_xlsx(tmp_path):
    pytest.importorskip("openpyxl")
    h, _ = synthetic_mine("small_mine", seed=2, defects=True)
    p = tmp_path / "mina.xlsx"
    save_history_xlsx(h, p)
    assert load_history(p) == h


def test_base_rmr_y_clases_como_la_calibracion(bases):
    # A1.6: RMR89 ~ N(45, 11) → III ≈ 55 %, IV ≈ 30 %, II ≈ 12 %, V ≈ 3 %
    rmr = np.concatenate([[t.rmr for t in tr.tramos] for _, tr in bases.values()])
    assert 42 < rmr.mean() < 52 and 10 < rmr.std() < 14
    cls = np.digitize(rmr, [21, 41, 61, 81])  # 0 = V … 4 = I
    share = {k: np.mean(cls == k) for k in range(5)}
    assert share[0] < 0.07 and 0.2 < share[1] < 0.4 and 0.45 < share[2] < 0.65 and 0.05 < share[3] < 0.2
    # A1.7: DE de log10 Q dentro de una mina 0.5–0.8 (un poco de holgura por las zonas)
    for _, tr in bases.values():
        assert 0.5 < np.std(np.log10([t.q for t in tr.tramos])) < 0.9


def test_base_recta_rmr_lnq_emerge_en_el_rango_de_b5(bases):
    # B5.4: pendiente por estudio p5–p95 = 2.8–8.9; residuo dentro del estudio ≈ 7
    for h, tr in bases.values():
        lnq = np.log([t.q_valor for t in h.tramos])
        rmr = np.array([t.rmr_valor for t in h.tramos])
        a, b = np.polyfit(lnq, rmr, 1)
        res = np.std(rmr - (a * lnq + b), ddof=2)
        assert 2.8 < a < 8.9 and 5 < res < 9
        assert 2.8 < tr.rmr_lnq_slope < 8.9 and 5 < tr.rmr_lnq_residual_sd < 9
        assert abs(a - tr.rmr_lnq_slope) < 1.0  # lo registrado sigue a la verdad con el ruido del geólogo
        lnq_t = np.log([t.q for t in tr.tramos])
        assert tr.rmr_lnq_slope == pytest.approx(np.polyfit(lnq_t, [t.rmr for t in tr.tramos], 1)[0])


def test_correlacion_del_sitio_corrida_mueve_la_recta(bases):
    _, tr = synthetic_mine("shifted_correlation", seed=0)
    base = bases[0][1]
    assert tr.rmr_lnq_intercept - base.rmr_lnq_intercept > 4  # B5.4: una DE del sesgo por estudio es 8


def test_autocorrelacion_a_lo_largo_de_la_labor_cae_con_la_distancia(bases):
    by = defaultdict(list)
    for h, tr in bases.values():
        for t, v in zip(h.tramos, tr.tramos):
            by[(id(h), labor_key(t))].append(v.rmr)

    def ac(lag):
        p = np.array([(s[i], s[i + lag]) for s in by.values() for i in range(len(s) - lag)])
        return np.corrcoef(p[:, 0], p[:, 1])[0, 1]

    r1, r4, r12 = ac(1), ac(4), ac(12)
    assert r1 > r4 > r12 > 0  # AR(1) + pepita y efecto de labor: cae pero no llega a 0
    assert r1 < 0.85  # la pepita no deja que tramos vecinos sean casi iguales


def test_sin_defectos_la_auditoria_no_levanta_hallazgos():
    for name in SCENARIOS:
        if name == "large_mine":
            continue
        h, _ = synthetic_mine(name, seed=0)
        assert audit_history(h).findings == (), name
    h, _ = synthetic_mine(seed=0)
    assert all(r.ready for r in audit_history(h).readiness)


def test_registro_completo_y_recalculable(bases):
    h, tr = bases[0]
    for t in h.tramos:
        assert None not in (t.ucs_mpa, t.rqd_pct, t.espaciamiento_m, t.puntaje_condicion_juntas, t.agua, t.jn,
                            t.jr, t.ja, t.jw, t.srf, t.q_valor, t.rmr_valor, t.gsi_valor)
        assert t.q_valor == float(f"{t.q_valor:.4g}")
        assert t.agua in ("Seco", "Húmedo", "Mojado", "Goteo")
    assert {v.geologist for v in tr.tramos} <= {f"G{i:02d}" for i in range(1, 5)}
    # el geólogo es uno por labor
    geo = defaultdict(set)
    for t, v in zip(h.tramos, tr.tramos):
        geo[labor_key(t)].add(v.geologist)
    assert all(len(g) == 1 for g in geo.values())
    # el registro difiere de la verdad (B4) pero poco: DE del RMR entre 3 y 7 puntos
    err = np.array([t.rmr_valor - v.rmr for t, v in zip(h.tramos, tr.tramos)])
    assert 3 < err.std() < 7


def test_practica_tabla_desvios_y_horas(bases):
    h, tr = bases[0]
    sc = tr.scenario
    for t, v in zip(h.tramos, tr.tramos):
        temporary = t.vida_util == "Temporal"
        date = datetime.date.fromisoformat(t.fecha_evaluacion)
        assert _ORDER[t.sost_recomendado] == _table_rank(sc, t.gsi_valor, temporary, date) == _ORDER[v.table_type]
        assert _ORDER[t.sost_instalado] - _ORDER[t.sost_recomendado] == v.practice_deviation
        assert t.tiempo_sin_sostener_h == v.unsupported_hours
        inst = datetime.date.fromisoformat(t.fecha_instalacion)
        assert (inst - date).days == int(v.unsupported_hours // 24)
    devs = Counter(v.practice_deviation for _, trr in bases.values() for v in trr.tramos)
    n = sum(devs.values())
    assert devs[-1] / n < sc.p_lighter + 0.02 and devs[1] / n < sc.p_heavier + 0.02  # el recorte a I–V resta
    assert devs[-1] / n > sc.p_lighter / 2 and devs[1] / n > sc.p_heavier / 2
    # más GSI → tipo más liviano; la tabla nueva es más liviana; el piso y la pendiente de la práctica tipo mina
    d0, d1 = datetime.date(2020, 1, 1), datetime.date(2023, 1, 1)
    ranks = [_table_rank(sc, g, False, d0) for g in range(10, 80, 5)]
    assert ranks == sorted(ranks, reverse=True) and ranks[0] == 5 and ranks[-1] == 1
    changed = dataclasses.replace(sc, table_change_date="2022-01-01")
    assert all(_table_rank(changed, g, False, d1) <= _table_rank(changed, g, False, d0) for g in range(10, 80))
    assert any(_table_rank(changed, g, False, d1) < _table_rank(changed, g, False, d0) for g in range(10, 80))
    mp = SCENARIOS["mine_practice"]
    assert min(_table_rank(mp, g, False, d0) for g in range(0, 101)) == 2
    flat = [_table_rank(mp, g, False, d0) for g in range(0, 101)]
    full = [_table_rank(sc, g, False, d0) for g in range(0, 101)]
    assert flat.count(5) < full.count(5) and flat.count(2) > full.count(2)  # pendiente al 60 %: más plana


def test_practica_carta_q_instala_lo_que_pide_la_carta():
    h, tr = synthetic_mine("ngi_site", seed=0)
    assert all(_ORDER[t.sost_instalado] == _chart_rank(t.q_valor, t.luz_m / t.esr) for t in h.tramos)
    assert all(v.practice_deviation == 0 for v in tr.tramos)


def test_prevalencia_base_entre_5_y_15_por_ciento(bases):
    # D7.5: modo realista, 5–15 % de los tramos fallados en la vida del histórico
    rates = [np.mean([o.failed for o in tramo_outcomes(h)]) for h, _ in bases.values()]
    assert 0.05 < np.mean(rates) < 0.15
    assert all(0.03 < r < 0.2 for r in rates)


def test_inspecciones_falla_al_final_y_exposicion_exacta(bases):
    h, tr = bases[0]
    by = defaultdict(list)
    for i in h.inspections:
        by[i.id_tramo].append(i)
    out = {o.id_tramo: o for o in tramo_outcomes(h)}
    for v in tr.tramos:
        ins = by[v.id_tramo]
        assert ins[0].sobreexcavacion_pct is not None and all(i.sobreexcavacion_pct is None for i in ins[1:])
        assert [i.fecha_inspeccion for i in ins] == sorted(i.fecha_inspeccion for i in ins)
        assert all(i.estado == "Estable" for i in ins[:-1])
        o = out[v.id_tramo]
        if o.failed:
            assert ins[-1].estado == "Falla" and ins[-1].tipo_falla and ins[-1].volumen_m3 >= 0.01
            assert o.exposure_days <= v.censor_days
        else:
            assert ins[-1].estado in ("Estable", "Abandonado") and o.exposure_days == v.censor_days
    # mensual mientras la labor está activa (D9.5)
    first = [(datetime.date.fromisoformat(by[t.id_tramo][0].fecha_inspeccion)
              - datetime.date.fromisoformat(t.fecha_instalacion)).days for t in h.tramos]
    assert Counter(first).most_common(1)[0][0] == 30


def test_p_verdadera_coincide_con_la_frecuencia_simulada(grandes):
    # P(falla en H | labor) = 1 − exp(−λwH) contra lo simulado, en los tramos cuya censura planeada pasa H
    for horizon in (180, 730):
        obs = exp = var = 0.0
        for h, tr in grandes:
            out = {o.id_tramo: o for o in tramo_outcomes(h)}
            for v in tr.tramos:
                if v.censor_days >= horizon:
                    p = tr.p_fail(v.id_tramo, v.installed_type, horizon, conditional=True)
                    o = out[v.id_tramo]
                    obs += o.failed and o.exposure_days <= horizon
                    exp, var = exp + p, var + p * (1 - p)
        assert abs(obs - exp) < 4 * math.sqrt(var), (horizon, obs, exp)


def test_p_marginal_es_la_de_la_fragilidad_gamma(grandes):
    _, tr = grandes[0]
    theta = tr.scenario.frailty_variance
    w = np.random.default_rng(0).gamma(1 / theta, theta, 400_000)
    for v in tr.tramos[:5]:
        for code in ("I", "III", "V"):
            lam = tr.rate(v.id_tramo, code)
            mc = np.mean(-np.expm1(-lam * w * 730))
            assert tr.p_fail(v.id_tramo, code, 730) == pytest.approx(mc, abs=3e-3)
            assert tr.rate(v.id_tramo, code, conditional=True) == pytest.approx(lam * v.frailty)
    # más sostenimiento, menos P (hasta el tipo que pide la carta del sitio y más allá)
    for v in tr.tramos[:50]:
        ps = [tr.p_fail(v.id_tramo, c, 365) for c in _ORDER]
        assert ps == sorted(ps, reverse=True)


def test_sitio_ngi_sin_efectos_la_tasa_depende_solo_del_deficit():
    h, tr = synthetic_mine("ngi_site", seed=0)
    sc = tr.scenario
    assert sc.site_shift_delta == 0 and len(set(sc.log_lambda0)) == 1
    lam0 = math.exp(sc.log_lambda0[0])
    by_deficit = defaultdict(set)
    for t, v in zip(h.tramos, tr.tramos):
        assert v.frailty == 1.0
        assert _ORDER[v.required_type] == _chart_rank(v.q, t.luz_m / t.esr)  # δ = 0: la carta NGI tal cual
        d = _ORDER[v.required_type] - _ORDER[v.installed_type]
        expected = lam0 * math.exp(sc.kappa_deficit * max(0, d) - sc.kappa_surplus * max(0, -d))
        assert tr.rate(v.id_tramo, v.installed_type) == pytest.approx(expected)
        assert tr.rate(v.id_tramo, v.required_type) == pytest.approx(lam0)  # lo que pide la carta: la tasa base
        by_deficit[d].add(round(tr.rate(v.id_tramo, v.installed_type), 15))
    assert all(len(s) == 1 for s in by_deficit.values())


def test_delta_positivo_pide_mas_sostenimiento():
    h, tr = synthetic_mine(seed=0)
    assert tr.scenario.site_shift_delta > 0
    for t, v in zip(h.tramos, tr.tramos):
        assert _ORDER[v.required_type] >= _chart_rank(v.q, t.luz_m / t.esr)


def test_defectos_en_la_tasa_pedida_y_la_auditoria_los_ve():
    sc = SCENARIOS["base"]
    want = {"empty_cell": sc.defect_empty_rate, "q_mismatch": sc.defect_q_mismatch_rate,
            "overlapping_chainage": sc.defect_overlap_rate,
            "inspection_before_installation": sc.defect_inspection_before_rate,
            "unknown_support": sc.defect_unknown_support_rate}
    assert set(want) == set(_DEFECT_KINDS)
    got, n_tramos, n_not_first = Counter(), 0, 0
    for seed in range(6):
        h, tr = synthetic_mine(seed=seed, defects=True)
        clean, _ = synthetic_mine(seed=seed)
        n_tramos += len(h.tramos)
        n_not_first += len(h.tramos) - len({labor_key(t) for t in h.tramos})
        got += Counter(k for k, _, _ in tr.defects)
        hit = {d[1] for d in tr.defects}
        # lo que no tiene defecto queda igual que sin defectos
        assert [t for t in h.tramos if t.id_tramo not in hit] == [t for t in clean.tramos if t.id_tramo not in hit]
        # la auditoría ve exactamente los defectos detectables y nada más
        found = {(f.kind, f.id_tramo) for f in audit_history(h).findings}
        detectable = {(k, tid) for k, tid, _ in tr.defects if k != "empty_cell"}
        assert found == detectable
        for k, tid, col in tr.defects:
            if k == "empty_cell":
                assert getattr(next(t for t in h.tramos if t.id_tramo == tid), col) is None
    for kind, rate in want.items():
        n = n_not_first if kind == "overlapping_chainage" else n_tramos
        assert abs(got[kind] - n * rate) < 4 * math.sqrt(n * rate * (1 - rate)) + 1, (kind, got[kind], n * rate)


def test_ningun_texto_trae_nombres_reales(bases):
    h, tr = bases[0]
    allowed = re.compile(r"(T\d{4}|L\d{3}|Z\d+|\d{4}-\d{2}-\d{2}|I|II|III|IV|V|RMR89|Q-NGI-2025)")
    vocab = {"Galería", "Rampa", "Tajeo", "Temporal", "Permanente", "Perforación y voladura", "Estable", "Falla",
             "Abandonado", "Desprendimiento", "Caída de bloque", "Deformación", "Seco", "Húmedo", "Mojado", "Goteo",
             "GSI cuantificado", "GSI clásico", *LITHOLOGIES}
    texts = [v for rec in (*h.tramos, *h.inspections) for v in dataclasses.asdict(rec).values() if isinstance(v, str)]
    assert all(allowed.fullmatch(v) or v in vocab for v in texts)
    assert all(re.fullmatch(r"G\d{2}", v.geologist) for v in tr.tramos)
    assert {name for s in SCENARIOS.values() for name, _, _ in s.lithologies} <= set(LITHOLOGIES)
