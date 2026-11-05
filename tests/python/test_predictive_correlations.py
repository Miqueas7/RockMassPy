"""Nivel 1, correlaciones propias del sitio (Fase 4A, tarea 6): estados, recuperación, prior, Deming, ediciones,
CustomCorrelation, centinela de privacidad (R13) y banda de predicción en el gráfico. Todo con datos sintéticos."""

import dataclasses
import math

import pytest

pytest.importorskip("scipy")

import numpy as np  # noqa: E402

import rockmasspy as rm  # noqa: E402
from rockmasspy.history import History, audit_history  # noqa: E402
from rockmasspy.predictive import (KINDS, NO_DOMAIN, SyntheticTruth, deming_fit, fit_site_correlation,  # noqa: E402
                                   ols_fit, synthetic_history)
from rockmasspy.predictive.correlations import SLOPE_CI_REL_TOL  # noqa: E402

N_BOOT = 400  # menos réplicas que el valor por defecto: las pruebas no miden la precisión del IC


def _big(seed=1):
    return synthetic_history(n_zones=4, labors_per_zone=6, seed=seed)


def _small(seed=1):
    return synthetic_history(n_zones=1, labors_per_zone=2, tramos_per_labor=5, seed=seed)


def _edit(h, f):
    return History(tuple(f(i, t) for i, t in enumerate(h.tramos)), h.support_types, h.inspections)


def _pairs_q(h):
    return [(t.q_valor, t.rmr_valor) for t in h.tramos]


def test_estados_segun_el_tamano():
    hb = _big()[0]
    big = fit_site_correlation(hb, "rmr_from_q", n_boot=N_BOOT)
    assert big.mine.status == "site" and big.mine.n == len(hb.tramos) and big.mine.n_labors == 24
    small = fit_site_correlation(_small()[0], "rmr_from_q", n_boot=N_BOOT)
    m = small.mine
    assert m.status == "not_calibrated" and m.method == "Bayesian"
    assert m.ols is None and m.bootstrap is None and m.deming is None
    assert any("not calibrated to the site" in w for w in m.warnings)
    assert any("few labors" in w for w in m.warnings)


def test_ic_ancho_da_inestable():
    noisy = SyntheticTruth(sd_rmr=40.0, sd_labor_rmr=15.0)
    h, _ = synthetic_history(n_zones=1, labors_per_zone=5, tramos_per_labor=8, truth=noisy, seed=3)
    m = fit_site_correlation(h, "rmr_from_q", group_by=None, n_boot=N_BOOT).mine
    assert m.n >= 30 and m.n_labors == 5  # justo sobre el mínimo
    assert m.status == "unstable" and m.method == "OLS"
    lo, hi = m.a_ci
    tol = SLOPE_CI_REL_TOL * abs(m.ols.a)
    assert lo < m.ols.a - tol or hi > m.ols.a + tol
    assert any(w.startswith("unstable") for w in m.warnings)


def test_recupera_a_y_b_del_mecanismo():
    h, tr = synthetic_history(n_zones=6, labors_per_zone=8, seed=2)
    rmr = fit_site_correlation(h, "rmr_from_q", n_boot=N_BOOT).mine
    assert rmr.a_ci[0] <= tr.rmr_a <= rmr.a_ci[1]
    assert rmr.ols.a == pytest.approx(tr.rmr_a, abs=0.6) and rmr.ols.b == pytest.approx(tr.rmr_b, abs=1.5)
    gsi = fit_site_correlation(h, "gsi_from_rmr", n_boot=N_BOOT).mine
    assert gsi.ols.a == pytest.approx(tr.gsi_c, abs=0.05) and gsi.ols.b == pytest.approx(tr.gsi_d, abs=2.5)


def test_con_pocos_datos_el_bayesiano_queda_cerca_de_la_global():
    h, _ = _small()
    r = fit_site_correlation(h, "rmr_from_q", group_by=None)
    a_g, b_g = r.prior_mean
    q = np.array([t.q_valor for t in h.tramos])
    y = np.array([t.rmr_valor for t in h.tramos])
    ols = ols_fit(np.log(q), y)
    assert abs(r.mine.bayes_a - a_g) < abs(ols.a - a_g)
    # la global se lee del núcleo (Huang 2026 para RMR89), no se copia a mano
    assert r.prior_correlation == "RmrFromQ_Huang2026" and r.prior_verification == "Secondary"
    assert a_g * math.log(5.0) + b_g == pytest.approx(rm.correlate(rm.Correlation.RmrFromQ_Huang2026, 5.0).value)
    assert r.prior_sd == pytest.approx((0.5 * abs(a_g), 10.0)) and r.prior_sigma == 8.0


def test_prior_por_edicion_y_tipo():
    h, _ = _small()
    r76 = fit_site_correlation(_edit(h, lambda i, t: dataclasses.replace(t, rmr_edicion="RMR-76")), "rmr_from_q",
                               group_by=None)
    assert r76.prior_correlation == "RmrFromQ_Bieniawski1976" and r76.mine.y_to == "RMR76"
    g = fit_site_correlation(h, "gsi_from_rmr", group_by=None)
    assert g.prior_correlation == "GsiFromRmr89Prime_HoekDiederichs2006"
    assert g.prior_mean == pytest.approx((1.0, -5.0))
    assert any("RMR89'" in w and "orientation" in w for w in g.warnings)
    qp = fit_site_correlation(h, "gsi_from_q_prime", group_by=None)
    assert qp.prior_correlation == "GsiFromQPrime_Hoek1995" and qp.mine.x_from == "Q'"


def test_pares_iguales_a_la_preparacion_del_nivel_1():
    h, _ = _big()
    # un hueco por tipo: los conteos tienen que seguir coincidiendo
    # casos del revisor: componentes de Q′ inválidos, edición vacía y una fila RMR76 entre RMR89
    bad = {3: dict(jn=0.0), 5: dict(ja=0.0), 8: dict(rqd_pct=150.0), 13: dict(rmr_edicion=None),
           17: dict(rmr_edicion=""), 19: dict(rmr_edicion="RMR76")}
    h = _edit(h, lambda i, t: dataclasses.replace(t, gsi_valor=None) if i % 7 == 0 else
              dataclasses.replace(t, q_valor=None) if i % 11 == 0 else dataclasses.replace(t, **bad.get(i, {})))
    ready = {r.item: r.counts for r in audit_history(h).readiness if r.level == 1}
    for kind in KINDS:
        r = fit_site_correlation(h, kind, group_by=None, n_boot=50)
        m = r.mine
        assert (m.n, m.n_labors) == (ready[kind]["pairs"], ready[kind]["labors"]), kind
        if kind != "gsi_from_q_prime":
            assert m.y_to == "RMR89" or m.x_from == "RMR89"
            assert any(w.startswith("3 pair(s) excluded: rmr_edicion") for w in r.warnings), kind
    qp = fit_site_correlation(h, "gsi_from_q_prime", group_by=None, n_boot=50)
    assert any(w.startswith("3 pair(s) excluded: Q'") for w in qp.warnings)
    # con la edición pedida entra solo esa
    r76 = fit_site_correlation(h, "rmr_from_q", group_by=None, rmr_edition="RMR76", n_boot=50)
    assert r76.mine.n == 1 and r76.prior_correlation == "RmrFromQ_Bieniawski1976"


def test_dominios_y_sin_dominio():
    h, _ = _big()
    h = _edit(h, lambda i, t: dataclasses.replace(t, litologia=None if i < 40 else "  " if i < 50 else t.litologia))
    r = fit_site_correlation(h, "rmr_from_q", n_boot=50)
    assert r.domains[NO_DOMAIN].n == 50
    assert sum(f.n for f in r.domains.values()) == r.mine.n
    assert [f.label for f in r.domains.values()] == [f"D{j + 1}" for j in range(len(r.domains))]
    assert list(r.domains)[-1] == NO_DOMAIN
    assert fit_site_correlation(h, "rmr_from_q", group_by=None, n_boot=50).domains == {}
    with pytest.raises(ValueError, match="group_by"):
        fit_site_correlation(h, "rmr_from_q", group_by="no_such_column")


def test_to_custom_correlation_con_correlate_custom():
    h, _ = _big()
    m = fit_site_correlation(h, "rmr_from_q", group_by=None, n_boot=N_BOOT).mine
    c = m.to_custom_correlation()
    qs = [t.q_valor for t in h.tramos]
    assert (c.valid_min, c.valid_max) == (min(qs), max(qs))
    assert c.form == rm.CorrelationForm.LogLinear and (c.from_, c.to) == ("Q", "RMR89")
    r = rm.correlate_custom(c, 2.0)
    assert r.value == pytest.approx(m.ols.a * math.log(2.0) + m.ols.b) and not r.warnings
    assert any("outside the calibration range" in w for w in rm.correlate_custom(c, c.valid_max * 10).warnings)
    assert c.source == f"RockMassPy site fit rmr_from_q: n={len(h.tramos)}, labors=24, method=OLS, status=site"
    # bajo el mínimo predice el bayesiano
    s = fit_site_correlation(_small()[0], "gsi_from_rmr", group_by=None).mine
    cs = s.to_custom_correlation()
    assert cs.form == rm.CorrelationForm.Linear and (cs.a, cs.b) == (s.bayes_a, s.bayes_b)
    assert "method=Bayesian" in cs.source and "status=not_calibrated" in cs.source
    assert "GsiFromRmr89Prime_HoekDiederichs2006 (Primary)" in cs.source and s.prior_verification == "Primary"
    y, lo, hi = s.predict(50.0)
    assert lo < y < hi and y == pytest.approx(s.bayes_a * 50 + s.bayes_b)


def test_to_custom_correlation_none_con_un_solo_tramo():
    h, _ = _big()
    h = _edit(h, lambda i, t: dataclasses.replace(t, litologia="unica") if i == 0 else t)
    r = fit_site_correlation(h, "rmr_from_q", n_boot=50)
    one = r.domains["unica"]
    assert one.n == 1 and one.status == "not_calibrated"
    assert one.to_custom_correlation() is None


def test_pendiente_con_signo_opuesto_es_inestable():
    h, _ = synthetic_history(n_zones=4, labors_per_zone=6, truth=SyntheticTruth(rmr_a=-9.0, rmr_b=60.0), seed=1)
    m = fit_site_correlation(h, "rmr_from_q", group_by=None, n_boot=N_BOOT).mine
    assert m.ols.a < 0 and m.status == "unstable"
    assert "unstable: slope sign opposite to the global correlation; check the data" in m.warnings


def test_deming_solo_con_razon():
    h, _ = _big()
    m = fit_site_correlation(h, "rmr_from_q", group_by=None, n_boot=50).mine
    assert m.deming is None and "deming_ratio" in m.deming_reason
    d = fit_site_correlation(h, "rmr_from_q", group_by=None, deming_ratio=2.0, n_boot=50).mine
    x = np.log([t.q_valor for t in h.tramos])
    assert d.deming == deming_fit(x, [t.rmr_valor for t in h.tramos], 2.0) and d.deming_reason is None
    with pytest.raises(ValueError, match="deming_ratio"):
        fit_site_correlation(h, "rmr_from_q", deming_ratio=0.0)
    s = fit_site_correlation(_small()[0], "rmr_from_q", group_by=None, deming_ratio=2.0).mine
    assert s.deming is None and s.deming_reason == "below the level-1 minimum"


def test_ediciones_mezcladas_usan_la_mayoritaria():
    h, _ = _small()
    mixed = _edit(h, lambda i, t: dataclasses.replace(t, rmr_edicion="RMR76") if i % 3 == 0 else t)
    n76 = sum(t.rmr_edicion == "RMR76" for t in mixed.tramos)
    for kind in ("rmr_from_q", "gsi_from_rmr"):
        r = fit_site_correlation(mixed, kind)
        assert r.mine.n == len(mixed.tramos) - n76 and "RMR89" in (r.mine.x_from, r.mine.y_to)
        assert f"{n76} pair(s) excluded: rmr_edicion missing or other than RMR89; RMR editions are not mixed " \
               "in one fit" in r.warnings
        assert fit_site_correlation(mixed, kind, rmr_edition="RMR76").mine.n == n76
    assert fit_site_correlation(mixed, "gsi_from_q_prime").mine.n == len(mixed.tramos)  # la edición no importa
    with pytest.raises(ValueError, match="no usable pairs with rmr_edicion"):
        fit_site_correlation(_edit(h, lambda i, t: dataclasses.replace(t, rmr_edicion="RMR14")), "rmr_from_q")
    with pytest.raises(ValueError, match="rmr_edition"):
        fit_site_correlation(h, "rmr_from_q", rmr_edition="RMR14")


def test_centinela_no_aparece_en_mensajes():
    def sent(i, t):
        return dataclasses.replace(t, labor_codigo=f"ZZSENT{t.labor_codigo}", zona_nivel=f"ZZSENT{t.zona_nivel}",
                                   litologia=f"ZZSENT-{t.litologia}")

    for h in (_big()[0], _small()[0]):
        h = _edit(h, sent)
        for kind in KINDS:
            r = fit_site_correlation(h, kind, n_boot=50)
            assert all(k.startswith("ZZSENT") for k in r.domains)  # el dominio sí va como clave de resultados
            texts = [*r.warnings, repr(r)]
            for f in (r.mine, *r.domains.values()):
                c = f.to_custom_correlation()
                texts += [*f.warnings, f.deming_reason or "", f.label, repr(f)] + ([c.name, c.source] if c else [])
            assert not [s for s in texts if "ZZSENT" in s], kind
        mixed = _edit(h, lambda i, t: dataclasses.replace(t, rmr_edicion="RMR76") if i % 3 == 0 else t)
        assert not [w for w in fit_site_correlation(mixed, "rmr_from_q").warnings if "ZZSENT" in w]
        with pytest.raises(ValueError) as e:
            fit_site_correlation(_edit(h, lambda i, t: dataclasses.replace(t, rmr_edicion="ZZSENT")), "rmr_from_q")
        assert "ZZSENT" not in str(e.value)


def test_errores_de_entrada():
    h, _ = _small()
    with pytest.raises(ValueError, match="kind"):
        fit_site_correlation(h, "rmr_from_gsi")
    with pytest.raises(ValueError, match="no usable pairs"):
        fit_site_correlation(_edit(h, lambda i, t: dataclasses.replace(t, gsi_valor=None)), "gsi_from_rmr")


def test_plot_correlation_con_banda():
    pytest.importorskip("matplotlib")
    from matplotlib.collections import PolyCollection

    from rockmasspy.viz import Style, plot_correlation

    h, _ = _big()
    m = fit_site_correlation(h, "rmr_from_q", group_by=None, n_boot=50).mine
    fig = plot_correlation(_pairs_q(h), x="Q", y="RMR89", global_correlations=[rm.Correlation.RmrFromQ_Huang2026],
                           site=[m.to_custom_correlation()], bands=[m], style=Style(lang="en"))
    ax = fig.axes[0]
    polys = [c for c in ax.collections if isinstance(c, PolyCollection)]
    assert len(polys) == 1 and len(ax.lines) == 2
    assert "95 % prediction interval" in [t.get_text() for t in ax.get_legend().get_texts()]
    # eje lineal y banda del bayesiano (bajo el mínimo)
    hs, _ = _small()
    s = fit_site_correlation(hs, "gsi_from_rmr", group_by=None).mine
    fig = plot_correlation([(t.rmr_valor, t.gsi_valor) for t in hs.tramos], x="RMR89", y="GSI", bands=[s])
    band = [c for c in fig.axes[0].collections if isinstance(c, PolyCollection)]
    assert len(band) == 1
    ys = np.concatenate([p.vertices[:, 1] for p in band[0].get_paths()])
    assert ys.min() >= 0 and ys.max() <= 100  # recortada como los valores del núcleo
    with pytest.raises(ValueError, match="band:mine"):
        plot_correlation(_pairs_q(h), x="Q", y="GSI", bands=[m])
