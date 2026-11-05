"""Nivel 2, auditoría de la práctica (Fase 4B, tarea 10; plan R8): signos según la incoherencia del generador,
conjunto conforme agrupado, concordancia, preparación, centinela de privacidad (R13) y archivo de resultados.
Todo con datos sintéticos."""

import dataclasses
import math

import pytest

pytest.importorskip("scipy")

import numpy as np  # noqa: E402

from rockmasspy.history import History, level2_rows  # noqa: E402
from rockmasspy.predictive import (PRACTICE_RESULT_COLUMNS, SyntheticTruth, audit_practice,  # noqa: E402
                                   quadratic_weighted_kappa, save_practice_results, synthetic_history)
from rockmasspy.predictive.practice import VERDICTS  # noqa: E402

N_BOOT = 100  # las pruebas no miden la precisión del IC del bootstrap


def _history(incoherence=0.0, seed=0, **kw):
    return synthetic_history(truth=SyntheticTruth(practice_incoherence=incoherence), seed=seed, **kw)[0]


def _edit(h, f):
    return History(tuple(f(i, t) for i, t in enumerate(h.tramos)), h.support_types, h.inspections)


@pytest.fixture(scope="module")
def coherent():
    h = _history(0.0, seed=1)
    return h, audit_practice(h, n_boot=N_BOOT)


@pytest.fixture(scope="module")
def inverted():
    return audit_practice(_history(1.0, seed=1), n_boot=N_BOOT)


def test_practica_coherente_da_signos_esperados_y_significativos(coherent):
    _, a = coherent
    assert a.verdicts == {"ln_q": "coherent", "ln_de": "coherent"}
    assert a.coefficients["ln_q"].ci_high < 0 < a.coefficients["ln_de"].ci_low
    assert a.converged and a.status == "ready" and not a.missing_types
    assert a.types == ("I", "II", "III", "IV", "V")
    # la validación compara contra las dos referencias en las tres particiones del generador
    assert set(a.validation.results) == {"labor", "zone", "temporal"}
    assert set(a.validation.results["labor"].improvements) == {"dummy", "ngi"}
    assert a.beyond_chart  # ln Q y ln De explican la práctica mejor que la categoría NGI sola


def test_practica_invertida_es_incoherente(inverted):
    assert inverted.verdicts == {"ln_q": "practice incoherent with rock quality",
                                 "ln_de": "practice incoherent with span"}


def test_practica_que_ignora_el_macizo_no_es_significativa():
    seeds = range(5)
    verdicts = [audit_practice(_history(0.5, seed=s), n_boot=20).verdicts for s in seeds]
    for name in ("ln_q", "ln_de"):
        assert sum(v[name] == "not significant" for v in verdicts) > len(seeds) / 2, name
    assert not any(v[name] == "coherent" for v in verdicts for name in v)  # nunca «coherente» sin evidencia


def test_colinealidad_avisada(coherent):
    _, a = coherent
    # en el generador Tajeo = Temporal: con Galería de referencia, la columna de Tajeo repite la vida útil
    assert a.dropped_columns == ("tipo_labor=Tajeo",)
    assert "columns dropped for collinearity: tipo_labor=Tajeo; remaining coefficients are contrasts" in a.warnings
    assert set(a.coefficients) == {"ln_q", "ln_de", "permanent", "tipo_labor=Rampa"}


def test_sin_convergencia_no_hay_conjuntos():
    h = _history(0.0, seed=1)
    med = float(np.median([t.q_valor for t in h.tramos]))
    sep = _edit(h, lambda i, t: dataclasses.replace(t, sost_instalado="I" if t.q_valor > med else "V"))
    a = audit_practice(sep, n_boot=10)  # Q separa las clases: el MLE no existe
    assert not a.converged and math.isnan(a.conformal_threshold)
    assert not a.outside_set and all(t.conformal_set is None for t in a.tramos)
    assert "conformal sets not computed: the final ordinal fit did not converge" in a.warnings
    with pytest.raises(ValueError, match="no conformal threshold"):
        a.conformal_set(h.tramos[0])


def test_tramos_fuera_del_conjunto(coherent):
    _, a = coherent
    expected = tuple(t.id_tramo for t in a.tramos if t.installed not in t.conformal_set)
    assert expected and a.outside_set == expected
    assert all(t.outside == (t.id_tramo in a.outside_set) for t in a.tramos)
    lo = audit_practice(_history(0.0, seed=1), conformal_level=0.5, n_boot=10)
    assert len(lo.outside_set) > len(a.outside_set)  # un nivel menor deja más tramos fuera


def test_concordancia_con_el_recomendado_del_generador(coherent):
    h, a = coherent
    c = a.concordance
    rank = {s.codigo_tipo: s.orden - 1 for s in h.support_types}
    rec = np.array([rank[t.sost_recomendado] for t in h.tramos])
    ins = np.array([rank[t.sost_instalado] for t in h.tramos])
    assert c.types == ("I", "II", "III", "IV", "V") and c.n == len(h.tramos) == c.matrix.sum()
    assert c.matrix[rank["III"], rank["IV"]] == np.sum((rec == 2) & (ins == 3))
    assert c.kappa == pytest.approx(quadratic_weighted_kappa(rec, ins, 5))
    same = audit_practice(_edit(h, lambda i, t: dataclasses.replace(t, sost_recomendado=t.sost_instalado)),
                          n_boot=10).concordance
    assert same.kappa == pytest.approx(1.0) and np.count_nonzero(same.matrix - np.diag(np.diag(same.matrix))) == 0
    none = _edit(h, lambda i, t: dataclasses.replace(t, sost_recomendado=None))
    assert audit_practice(none, n_boot=10).concordance is None


def test_datos_insuficientes_quedan_marcados():
    h = _history(0.0, seed=2, n_zones=1, labors_per_zone=4, tramos_per_labor=8)
    a = audit_practice(h, n_boot=20)
    assert a.status == "insufficient data" and a.missing_types
    assert any("insufficient data" in w for w in a.warnings)
    assert set(a.coefficients) >= {"ln_q", "ln_de"}  # igual se ajusta
    assert all(v in VERDICTS for v in a.verdicts.values())
    assert "zone" in a.validation.skipped  # una sola zona: la partición se omite, no se cae
    assert not a.beyond_chart and set(a.validation.warnings) <= set(a.warnings)


def test_vida_util_faltante_y_errores():
    h = _history(0.0, seed=1)
    a = audit_practice(_edit(h, lambda i, t: dataclasses.replace(t, vida_util=None) if i == 0 else t), n_boot=10)
    assert "permanent" not in a.coefficients and any("vida_util" in w for w in a.warnings)
    one = _edit(h, lambda i, t: dataclasses.replace(t, sost_instalado="I"))
    with pytest.raises(ValueError, match="at least 2 installed support types"):
        audit_practice(one)
    with pytest.raises(ValueError, match="conformal_level"):
        audit_practice(h, conformal_level=1.0)


def test_el_centinela_no_aparece_en_textos():
    def sent(i, t):
        return dataclasses.replace(t, labor_codigo=f"ZZSENT{t.labor_codigo}", zona_nivel=f"ZZSENT{t.zona_nivel}",
                                   litologia=f"ZZSENT-{t.litologia}")

    for h in (_history(0.0, seed=1), _history(0.5, seed=3, n_zones=1, labors_per_zone=3, tramos_per_labor=6)):
        h = _edit(h, sent)
        a = audit_practice(h, n_boot=10)
        v = a.validation
        texts = [*a.warnings, *a.verdicts.values(), repr(a), repr(v), *v.skipped.values(),
                 *a.dropped_columns, *a.coefficients]
        assert not [s for s in texts if "ZZSENT" in s]


def test_save_practice_results_csv_y_xlsx(coherent, tmp_path):
    _, a = coherent
    p = save_practice_results(a, tmp_path / "practica.csv")
    lines = p.read_text(encoding="utf-8-sig").splitlines()
    assert len(lines) == a.n + 1 and all(c in lines[0] for c in PRACTICE_RESULT_COLUMNS)
    assert sum(line.endswith("sí") for line in lines) == len(a.outside_set)
    openpyxl = pytest.importorskip("openpyxl")
    px = save_practice_results(a, tmp_path / "practica.xlsx")
    ws = openpyxl.load_workbook(px)["Practica"]
    rows = list(ws.iter_rows(values_only=True))
    assert rows[0] == PRACTICE_RESULT_COLUMNS and len(rows) == a.n + 1
    outside = {r[0] for r in rows[1:] if r[4] == "sí"}
    assert outside == set(a.outside_set)
    assert all(set(r[3].split("|")) <= set(a.types) for r in rows[1:])


def test_conjunto_conforme_en_labores_nuevas(coherent):
    _, a = coherent
    new = [t for s in (7, 8) for t in level2_rows(_history(0.0, seed=s))]  # otras semillas: labores nuevas
    p = a.predict_proba(new)
    assert p.shape == (len(new), len(a.types)) and np.allclose(p.sum(axis=1), 1.0)
    sets = [a.conformal_set(t) for t in new]
    assert all(s == tuple(c for c in a.types if c in s) for s in sets)  # en orden, del más liviano al más pesado
    cov = np.mean([t.sost_instalado in s for t, s in zip(new, sets)])
    assert abs(cov - 0.9) <= 3 * math.sqrt(0.9 * 0.1 / len(new)) + 1 / a.n


def test_tramo_nuevo_incompleto_o_con_tipo_de_labor_no_visto(coherent):
    _, a = coherent
    t = dataclasses.replace(level2_rows(_history(0.0, seed=7))[0], labor_codigo="ZZSENT", zona_nivel="ZZSENT")
    for bad, match in ((dict(q_valor=None), "q_valor"), (dict(luz_m=0.0), "luz_m"), (dict(esr=None), "esr"),
                       (dict(vida_util=None), "vida_util"), (dict(tipo_labor="ZZSENT"), "tipo_labor")):
        with pytest.raises(ValueError, match=match) as e:
            a.conformal_set(dataclasses.replace(t, **bad))
        assert "ZZSENT" not in str(e.value) and "position" not in str(e.value)
    with pytest.raises(ValueError, match="tramo at position 1: esr"):
        a.predict_proba([t, dataclasses.replace(t, esr=None)])
    assert a.conformal_set(t)  # con todo, funciona
