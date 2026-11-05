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
            "incoherent_practice", "mine_practice", "noisy_mapping", "small_mine", "large_mine", "saturating_large",
            "saturating_worse"} == set(SCENARIOS)
    with pytest.raises(ValueError, match="failure_mechanism"):
        MineScenario(failure_mechanism="otro")
    with pytest.raises(ValueError, match="saturating"):
        MineScenario(saturating_support_scale=0)
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
    with pytest.raises(ValueError, match="does not fit"):
        MineScenario(years=1, tramos_per_labor=100)
    with pytest.raises(ValueError, match="practice_type_shift"):
        MineScenario(practice_type_shift=0.5)
    with pytest.raises(ValueError, match="triples of numbers"):
        MineScenario(lithologies=(("andesita", 80.0, "buena"),))
    with pytest.raises(ValueError, match="generic rock names"):
        MineScenario(lithologies=(("veta norte", 80.0, 0.0),))
    assert MineScenario(lithologies=(("granito", 150, 1),)).lithologies == (("granito", 150, 1),)
    # lo que sí cabe no deja tramos ni inspecciones fuera del histórico
    h, _ = synthetic_mine(MineScenario(years=2, tramos_per_labor=60, n_zones=1, labors_per_zone=3), seed=0)
    end = datetime.date(2019, 1, 1) + datetime.timedelta(days=round(365.25 * 2))
    assert max(t.fecha_evaluacion for t in h.tramos) < end.isoformat()
    assert max(i.fecha_inspeccion for i in h.inspections) <= end.isoformat()


def test_ida_y_vuelta_por_xlsx(tmp_path):
    pytest.importorskip("openpyxl")
    h, _ = synthetic_mine("small_mine", seed=2, defects=True)
    p = tmp_path / "mina.xlsx"
    save_history_xlsx(h, p)
    assert load_history(p) == h


def test_base_de_unos_800_tramos_y_los_derivados_de_unos_600(bases):
    # Fase 5B: la base llega al mínimo del nivel 3; los derivados conservan el tamaño del banco c575d12
    assert 700 < np.mean([len(h.tramos) for h, _ in bases.values()]) < 900
    assert SCENARIOS["base"].labors_per_zone == 8 and MineScenario() == SCENARIOS["base"]
    assert all(s.labors_per_zone == 6 for n, s in SCENARIOS.items()
               if n not in ("base", "small_mine", "large_mine", "saturating_large"))


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


def _z_failures(mines, horizon, p_of, keep=lambda v: True):
    """(observadas − esperadas)/DE de las fallas dentro de H, en los tramos cuya censura planeada pasa H."""
    obs = exp = var = 0.0
    for h, tr in mines:
        out = {o.id_tramo: o for o in tramo_outcomes(h)}
        for v in tr.tramos:
            if v.censor_days >= horizon and keep(v):
                p = p_of(tr, v)
                o = out[v.id_tramo]
                obs += o.failed and o.exposure_days <= horizon
                exp, var = exp + p, var + p * (1 - p)
    return (obs - exp) / math.sqrt(var)


def test_p_verdadera_coincide_con_la_frecuencia_simulada(grandes):
    # P(falla en H | labor) = 1 − exp(−λwH) contra lo simulado
    for horizon in (180, 730):
        z = _z_failures(grandes, horizon, lambda tr, v: tr.p_fail(v.id_tramo, v.installed_type, horizon,
                                                                   conditional=True))
        assert abs(z) < 4, (horizon, z)
    # por estratos de fragilidad: sin la fragilidad (o con la marginal) se pasa de largo en los dos extremos
    for lo, hi, sign in ((0.0, 0.6, -1), (1.5, math.inf, 1)):
        keep = lambda v: lo <= v.frailty < hi  # noqa: E731
        z = _z_failures(grandes, 730, lambda tr, v: tr.p_fail(v.id_tramo, v.installed_type, 730,
                                                               conditional=True), keep)
        assert abs(z) < 4, (lo, z)
        z_w1 = _z_failures(grandes, 730, lambda tr, v: -math.expm1(-tr.rate(v.id_tramo, v.installed_type) * 730),
                           keep)
        z_marg = _z_failures(grandes, 730, lambda tr, v: tr.p_fail(v.id_tramo, v.installed_type, 730), keep)
        assert sign * z_w1 > 4 and sign * z_marg > 4, (lo, z_w1, z_marg)


@pytest.fixture(scope="module")
def saturadas():
    return [synthetic_mine("saturating_large", seed=seed) for seed in range(3)]


def test_mecanismo_saturado_p_verdadera_exacta(saturadas):
    # mismo contraste que con el mecanismo M5: la P verdadera condicional coincide con lo simulado
    for horizon in (180, 730):
        z = _z_failures(saturadas, horizon, lambda tr, v: tr.p_fail(v.id_tramo, v.installed_type, horizon,
                                                                     conditional=True))
        assert abs(z) < 4, (horizon, z)
    z = _z_failures(saturadas, 730, lambda tr, v: tr.p_fail(v.id_tramo, v.installed_type, 730, conditional=True),
                    lambda v: v.frailty > 1.5)
    assert abs(z) < 4, z
    rates = [np.mean([o.failed for o in tramo_outcomes(h)]) for h, _ in saturadas]
    assert 0.05 < np.mean(rates) < 0.2  # D7.5, como large_mine


def test_mecanismo_saturado_sin_carta_ni_deficit(saturadas):
    from rockmasspy.predictive.mine import _LABOR_TYPE_NAMES
    h, tr = saturadas[0]
    sc = tr.scenario
    assert sc.failure_mechanism == "saturating" and SCENARIOS["base"].failure_mechanism == "chart_deficit"
    steps = []
    for t, v in list(zip(h.tramos, tr.tramos))[:300]:
        for rk, hours in enumerate(v.unsupported_hours_by_type, start=1):
            log_rate = (sc.log_lambda0[_LABOR_TYPE_NAMES.index(t.tipo_labor)] + v.zone_failure_effect
                        + (math.log(sc.unsupported_multiplier) if hours > v.standup_hours else 0.0)
                        - sc.saturating_beta_lnq * math.log(v.q) + sc.saturating_beta_lnde * math.log(t.luz_m / t.esr)
                        - sc.saturating_support_max * (1 - math.exp(-(rk - 1) / sc.saturating_support_scale)))
            assert v.rates[rk - 1] == pytest.approx(math.exp(log_rate))
        hb = v.unsupported_hours_by_type
        if all((x > v.standup_hours) == (hb[0] > v.standup_hours) for x in hb):  # mismo término de horas
            steps.append(np.diff(np.log(v.rates)))
    # el efecto del sostenimiento se satura (cada paso ayuda menos) y es el mismo en cualquier macizo
    steps = np.array(steps)
    assert steps.size and np.all(steps < 0) and np.all(np.diff(steps, axis=1) > 0)
    assert np.allclose(steps, steps[0])


def test_p_contrafactual_con_los_desvios_como_experimento_natural():
    # El desvío a un tipo más liviano se sortea sin mirar el tramo: entre los tramos donde la tabla pide k, la
    # fracción f que se desvió a k − 1 es una muestra al azar, así que sus fallas ≈ f·Σ P(k − 1) de TODOS ellos.
    # Se miran los tramos donde las horas sin sostener del tipo más liviano pasan el autosoporte y las del de la
    # tabla no (se sabe antes del desvío): ahí usar las horas del tipo instalado subestima la P ≈ 4 veces.
    sc = dataclasses.replace(SCENARIOS["large_mine"], name="experimento", p_lighter=0.5, p_heavier=0.0)
    mines = [synthetic_mine(sc, seed=seed) for seed in range(3)]
    codes = list(_ORDER)
    for horizon in (365, 730):
        obs, ps, n_dev = 0, [], 0
        for h, tr in mines:
            out = {o.id_tramo: o for o in tramo_outcomes(h)}
            for v in tr.tramos:
                k = _ORDER[v.table_type] - 1  # rango del tipo más liviano
                hb = v.unsupported_hours_by_type
                if k < 1 or v.censor_days < horizon or not hb[k - 1] > v.standup_hours >= hb[k]:
                    continue
                ps.append(tr.p_fail(v.id_tramo, codes[k - 1], horizon, conditional=True))
                if v.practice_deviation == -1:
                    o = out[v.id_tramo]
                    n_dev += 1
                    obs += o.failed and o.exposure_days <= horizon
        ps = np.array(ps)
        f = n_dev / len(ps)
        assert 0.4 < f < 0.6 and len(ps) > 500
        z = (obs - f * ps.sum()) / math.sqrt(f * (ps * (1 - f * ps)).sum())
        assert abs(z) < 4, (horizon, obs, f * ps.sum())


def test_tasas_por_tipo_desde_sus_horas_sin_sostener(bases):
    from rockmasspy.predictive.mine import _LABOR_TYPE_NAMES
    h, tr = bases[0]
    sc = tr.scenario
    for t, v in zip(h.tramos, tr.tramos):
        assert v.unsupported_hours_by_type[_ORDER[v.installed_type] - 1] == v.unsupported_hours
        assert v.unsupported_hours_by_type[3] <= v.unsupported_hours_by_type[2]  # IV y V: 1 turno; I–III: días
        req = _ORDER[v.required_type]
        for rk, hours in enumerate(v.unsupported_hours_by_type, start=1):
            log_rate = (sc.log_lambda0[_LABOR_TYPE_NAMES.index(t.tipo_labor)] + v.zone_failure_effect
                        + (math.log(sc.unsupported_multiplier) if hours > v.standup_hours else 0.0)
                        + sc.kappa_deficit * max(0, req - rk) - sc.kappa_surplus * max(0, rk - req))
            assert v.rates[rk - 1] == pytest.approx(math.exp(log_rate))
        assert v.failed == (v.failure_day <= v.censor_days)
    out = {o.id_tramo: o for o in tramo_outcomes(h)}
    assert all(out[v.id_tramo].failed == v.failed for v in tr.tramos)
    assert all(out[v.id_tramo].exposure_days == v.failure_day for v in tr.tramos if v.failed)


def test_sitio_peor_el_sostenimiento_ayuda_poco_solo_en_roca_v():
    h, tr = synthetic_mine("worse_site", seed=0)
    sc = tr.scenario
    assert sc.kappa_deficit == SCENARIOS["base"].kappa_deficit and sc.kappa_deficit_rock_v < sc.kappa_deficit
    rock_v = [v for v in tr.tramos if v.rmr < 21]
    assert rock_v and len(rock_v) < len(tr.tramos)
    for v in tr.tramos:
        if _ORDER[v.required_type] >= 2:
            kd = sc.kappa_deficit_rock_v if v.rmr < 21 else sc.kappa_deficit
            h1, h0 = v.unsupported_hours_by_type[_ORDER[v.required_type] - 2:_ORDER[v.required_type]]
            if (h1 > v.standup_hours) == (h0 > v.standup_hours):  # mismo término de horas
                ratio = v.rates[_ORDER[v.required_type] - 2] / v.rates[_ORDER[v.required_type] - 1]
                assert ratio == pytest.approx(math.exp(kd))


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
    more = 0
    for t, v in zip(h.tramos, tr.tramos):
        ngi = _chart_rank(v.q, t.luz_m / t.esr)
        assert _ORDER[v.required_type] >= ngi
        more += _ORDER[v.required_type] > ngi
    assert more > 0


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
        # las inspecciones defectuosas van al final: las demás conservan su fila
        assert h.inspections[:len(clean.inspections)] == clean.inspections
        assert len(h.inspections) - len(clean.inspections) == sum(k == "inspection_before_installation"
                                                                  for k, _, _ in tr.defects)
        # la auditoría ve exactamente los defectos detectables y nada más
        found = {(f.kind, f.id_tramo) for f in audit_history(h).findings}
        detectable = {(k, tid) for k, tid, _ in tr.defects if k != "empty_cell"}
        # las celdas vacías salen contadas por columna, sin id (tarea 8)
        detectable |= {("missing_values", None)} if any(k == "empty_cell" for k, _, _ in tr.defects) else set()
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
