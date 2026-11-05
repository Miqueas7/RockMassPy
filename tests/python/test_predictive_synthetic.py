"""Generador de históricos sintéticos (Fase 4A, tarea 4). Solo datos sintéticos."""

import dataclasses
import math
import re
from collections import Counter

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from rockmasspy.history import audit_history, labor_key, load_history, save_history_xlsx, tramo_outcomes  # noqa: E402
from rockmasspy.predictive import SyntheticTruth, group_bootstrap, ols_fit, synthetic_history  # noqa: E402
from rockmasspy.predictive.synthetic import LITHOLOGIES  # noqa: E402


@pytest.fixture(scope="module")
def historicos():
    """Los históricos por defecto de las semillas 0 a 39, generados una vez: los comparten la cobertura del nivel 1
    y las pruebas con la semilla 0 (History es inmutable)."""
    return {seed: synthetic_history(seed=seed) for seed in range(40)}


def _lnq_rmr(h):
    return (np.array([math.log(t.q_valor) for t in h.tramos]), np.array([t.rmr_valor for t in h.tramos]))


def test_misma_semilla_mismo_historico_y_otra_semilla_otro():
    a, ta = synthetic_history(seed=3)
    b, tb = synthetic_history(seed=3)
    c, _ = synthetic_history(seed=4)
    assert a == b and ta == tb == SyntheticTruth()
    assert a != c


def test_tamano_y_codigos():
    h, _ = synthetic_history(n_zones=3, labors_per_zone=2, tramos_per_labor=4, seed=1)
    assert {t.zona_nivel for t in h.tramos} == {"Z1", "Z2", "Z3"}
    assert {t.labor_codigo for t in h.tramos} == {f"L{i:03d}" for i in range(1, 7)}
    assert [t.id_tramo for t in h.tramos] == [f"T{i:04d}" for i in range(1, len(h.tramos) + 1)]
    assert [s.codigo_tipo for s in h.support_types] == ["I", "II", "III", "IV", "V"]


def test_labores_desbalanceadas_con_la_media_pedida():
    h, _ = synthetic_history(n_zones=4, labors_per_zone=10, tramos_per_labor=12, seed=1)
    sizes = Counter(labor_key(t) for t in h.tramos).values()
    assert min(sizes) >= 4 and max(sizes) - min(sizes) >= 6
    assert abs(sum(sizes) / len(sizes) - 12) < 1.5


def test_verdad_hasheable_con_listas():
    tr = SyntheticTruth(practice_cuts=[-2.0, -1.0, 0.0, 1.0], exposure_days=[10, 100])
    assert tr.practice_cuts == (-2.0, -1.0, 0.0, 1.0) and tr.exposure_days == (10, 100)
    hash(tr)


def test_ida_y_vuelta_por_xlsx(tmp_path):
    pytest.importorskip("openpyxl")
    h, _ = synthetic_history(n_zones=2, labors_per_zone=3, tramos_per_labor=5, seed=2)
    p = tmp_path / "historico.xlsx"
    save_history_xlsx(h, p)
    assert load_history(p) == h


def test_auditoria_limpia_y_niveles_listos(historicos):
    h, _ = historicos[0]
    audit = audit_history(h)
    assert audit.findings == ()  # ni Q, ni coherencia, ni solapes, ni componentes repetidos
    assert all(r.ready for r in audit.readiness)
    assert len({t.zona_nivel for t in h.tramos}) >= 3
    assert len({t.fecha_evaluacion[:4] for t in h.tramos}) >= 4
    lnde = [math.log(t.luz_m / t.esr) for t in h.tramos]
    assert max(lnde) - min(lnde) >= 1.5


def test_auditoria_lista_tambien_sin_efecto_del_sitio():
    h, _ = synthetic_history(seed=0, truth=SyntheticTruth(site_effect=False))
    audit = audit_history(h)
    assert audit.findings == ()
    assert all(r.ready for r in audit.readiness)


def test_resultados_por_tramo(historicos):
    h, _ = historicos[0]
    out = tramo_outcomes(h)
    assert len(out) == len(h.tramos)  # todos tienen inspecciones
    rate = sum(o.failed for o in out) / len(out)
    assert 0.30 < rate < 0.65
    assert all(o.exposure_days is not None and o.exposure_days > 0 for o in out)
    # la falla, si hay, es la última inspección
    last = {}
    for i in h.inspections:
        last[i.id_tramo] = i
    assert all(o.failed == (last[o.id_tramo].estado == "Falla") for o in out)
    # más intercepto → más fallas
    hi, _ = synthetic_history(seed=0, truth=SyntheticTruth(fail_beta0=-2.0))
    assert sum(o.failed for o in tramo_outcomes(hi)) > sum(o.failed for o in out)


def test_sin_efecto_del_sitio_depende_solo_de_la_categoria():
    # condicionado a la categoría NGI, ln Q, ln De, rango y exposición no aportan nada (oráculo: statsmodels Logit)
    sm = pytest.importorskip("statsmodels.api")
    from rockmasspy.q_support import read_q_chart
    h, _ = synthetic_history(n_zones=8, labors_per_zone=10, tramos_per_labor=25, seed=0,
                             truth=SyntheticTruth(site_effect=False))
    out = {o.id_tramo: o for o in tramo_outcomes(h)}
    rank = {s.codigo_tipo: s.orden for s in h.support_types}
    rows = [(read_q_chart(t.q_valor, t.luz_m / t.esr).category, math.log(t.q_valor), math.log(t.luz_m / t.esr),
             rank[t.sost_instalado], math.log(out[t.id_tramo].exposure_days)) for t in h.tramos]
    y = np.array([out[t.id_tramo].failed for t in h.tramos], dtype=float)
    fit = sm.Logit(y, sm.add_constant(np.array(rows))).fit(disp=0)
    assert fit.params[1] > 0 and fit.pvalues[1] < 1e-6  # la categoría sí cuenta
    assert all(p > 0.01 for p in fit.pvalues[2:])  # semilla fija; con otras, ~1 de 40 cae bajo 0.01 por azar


def test_nivel1_ic_bootstrap_cubre_la_pendiente_verdadera(historicos):
    cover = 0
    for seed in range(40):  # cobertura real ~92 %: con 40 semillas, >= 33 casi nunca falla por azar
        h, tr = historicos[seed]
        x, y = _lnq_rmr(h)
        bs = group_bootstrap([labor_key(t) for t in h.tramos], lambda i: ols_fit(x[i], y[i]).a,
                             n_boot=200, seed=seed)
        lo, hi = bs.percentile_ci()
        cover += lo <= tr.rmr_a <= hi
    assert cover >= 33


def test_nivel1_gsi_sigue_al_rmr_y_a_q_prima(historicos):
    h, tr = historicos[0]
    rmr = np.array([t.rmr_valor for t in h.tramos])
    gsi = np.array([t.gsi_valor for t in h.tramos])
    qp = np.array([math.log(t.rqd_pct / t.jn * t.jr / t.ja) for t in h.tramos])
    fit = ols_fit(rmr, gsi)
    assert abs(fit.a - tr.gsi_c) < 0.1 and abs(fit.b - tr.gsi_d) < 5
    assert np.corrcoef(qp, gsi)[0, 1] > 0.7


def _heavy_share(h):
    lnq = np.array([math.log(t.q_valor) for t in h.tramos])
    rank = np.array([int({"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}[t.sost_instalado]) for t in h.tramos])
    lo, hi = np.quantile(lnq, [1 / 3, 2 / 3])
    return (rank[lnq <= lo] >= 4).mean(), (rank[lnq >= hi] >= 4).mean()


def test_nivel2_signos_peor_macizo_tipo_mas_pesado(historicos):
    bad, good = _heavy_share(historicos[0][0])
    assert bad > good + 0.3
    # con la práctica invertida el signo se da vuelta
    bad, good = _heavy_share(synthetic_history(seed=0, truth=SyntheticTruth(practice_incoherence=1.0))[0])
    assert bad < good


def test_verdad_valida_sus_parametros():
    with pytest.raises(ValueError, match="practice_cuts"):
        SyntheticTruth(practice_cuts=(0.0, 1.0))
    with pytest.raises(ValueError, match="practice_incoherence"):
        SyntheticTruth(practice_incoherence=1.5)
    with pytest.raises(ValueError, match="standard deviations"):
        SyntheticTruth(sd_rmr=-1.0)
    with pytest.raises(ValueError, match="n_zones"):
        synthetic_history(n_zones=0)


def test_ningun_texto_trae_nombres_reales(historicos):
    h, _ = historicos[0]
    allowed = re.compile(r"(T\d{4}|L\d{3}|Z\d+|\d{4}-\d{2}-\d{2}|I|II|III|IV|V|RMR89|Q-NGI-2025|GSI clásico)")
    vocab = {"Galería", "Rampa", "Tajeo", "Temporal", "Permanente", "Perforación y voladura",
             "Estable", "Falla", "Desprendimiento", *LITHOLOGIES}
    texts = [v for rec in (*h.tramos, *h.inspections) for v in dataclasses.asdict(rec).values() if isinstance(v, str)]
    assert all(allowed.fullmatch(v) or v in vocab for v in texts)
    # los tipos de sostenimiento: elementos genéricos, sin marcas
    support_text = " ".join(str(dataclasses.asdict(s)) for s in h.support_types)
    assert not re.search(r"split|swellex|hilti|atlas|sandvik|epiroc", support_text, re.IGNORECASE)
