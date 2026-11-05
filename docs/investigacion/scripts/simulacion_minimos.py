"""Simulación de los mínimos de datos de cada nivel del módulo predictivo (Fase 4C, tarea 13; plan R6 y R11).

Todo es sintético: los históricos salen de `synthetic_history`, con mecanismo conocido. No lee ningún dato de mina.
Escribe un CSV en formato largo (una métrica por fila de resultados) e imprime solo avances y agregados por celda.

Uso (con el paquete importable):
    python simulacion_minimos.py --seed 20261105 --reps 50 --reps-l1 200 --n-boot 500 --out resultados.csv
    python simulacion_minimos.py --quick   # corrida corta de prueba

Para medir cada celda, el script baja los mínimos de la librería a 1 SOLO dentro de este proceso
(`correlations.MIN_*` y `performance.MIN_EVENTS_PER_PARAMETER_LEVEL3`): así se ve qué hace la regla de validación
con 5, 10 o 20 eventos por parámetro aunque el mínimo vigente sea 10. La librería no se modifica.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
import time
from collections import Counter, defaultdict

import numpy as np
from scipy.special import expit

from rockmasspy.history import History, level3_parameters, level3_rows
from rockmasspy.predictive import (SyntheticTruth, audit_practice, brier, dummy_proba_fit_predict, fit_performance,
                                   fit_site_correlation, logistic_map_fit, recommend, synthetic_history, tramo_groups,
                                   validate)
from rockmasspy.predictive import correlations as _corr
from rockmasspy.predictive import performance as _perf
from rockmasspy.predictive.performance import _labor_types, _row, _signs
from rockmasspy.q_support import read_q_chart

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

THRESHOLD = 0.10  # P(falla) aceptable fija para la métrica de recomendación demasiado liviana
EXPOSURE = 365.0  # días, fija
N_TEST = 100  # tramos nuevos (labores y zonas nuevas) por réplica
PREVALENCES = (0.10, 0.25)
EVENTS = (5, 10, 20)
L1_PAIRS, L1_LABORS = (15, 30, 60), (3, 5, 8)
L2_PER_TYPE = (5, 10, 20)
COLUMNS = ("nivel", "escenario", "celda", "metrica", "valor", "exitos", "n", "ic95_inf", "ic95_sup")


# ---------- intervalos ----------

def wilson(k: int, n: int, z: float = 1.959963984540054):
    """IC 95 % de Wilson de una proporción k/n."""
    if n == 0:
        return math.nan, math.nan, math.nan
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def ratio_ci(nums, dens, seed=0, n_boot=2000):
    """Razón de sumas con IC 95 % por bootstrap de réplicas (los eventos de una réplica no son independientes)."""
    nums, dens = np.asarray(nums, float), np.asarray(dens, float)
    if dens.sum() == 0:
        return math.nan, math.nan, math.nan
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, nums.size, size=(n_boot, nums.size))
    d = dens[idx].sum(axis=1)
    r = nums[idx].sum(axis=1)[d > 0] / d[d > 0]
    return float(nums.sum() / dens.sum()), float(np.quantile(r, 0.025)), float(np.quantile(r, 0.975))


def mean_ci(x):
    x = np.asarray([v for v in x if math.isfinite(v)], float)
    if x.size == 0:
        return math.nan, math.nan, math.nan
    h = 1.96 * x.std(ddof=1) / math.sqrt(x.size) if x.size > 1 else math.nan
    return float(x.mean()), float(x.mean() - h), float(x.mean() + h)


class Out:
    def __init__(self):
        self.rows = []

    def prop(self, nivel, esc, celda, metrica, k, n):
        p, lo, hi = wilson(k, n)
        self.rows.append((nivel, esc, celda, metrica, p, k, n, lo, hi))

    def ratio(self, nivel, esc, celda, metrica, nums, dens):
        v, lo, hi = ratio_ci(nums, dens)
        self.rows.append((nivel, esc, celda, metrica, v, int(sum(nums)), int(sum(dens)), lo, hi))

    def mean(self, nivel, esc, celda, metrica, xs):
        v, lo, hi = mean_ci(xs)
        self.rows.append((nivel, esc, celda, metrica, v, "", len(xs), lo, hi))


def _seed(*parts) -> int:
    return int(np.random.SeedSequence(list(parts)).generate_state(1)[0])


def _fmt(x):
    return f"{x:.6g}" if isinstance(x, float) else x


# ---------- armado de históricos ----------

def _by_labor(h: History):
    tram, insp = defaultdict(list), defaultdict(list)
    for t in h.tramos:
        tram[t.labor_codigo].append(t)
    for i in h.inspections:
        insp[i.id_tramo].append(i)
    return tram, insp


def grow(h: History, rng, ready):
    """Agrega labores enteras (en orden aleatorio) hasta que `ready(tramos)` se cumple: la mina que recién alcanza
    la celda. None si el pozo se agota."""
    tram, insp = _by_labor(h)
    sel = []
    for lab in rng.permutation(sorted(tram)):
        sel += tram[lab]
        if ready(sel):
            return History(tuple(sel), h.support_types, tuple(i for t in sel for i in insp[t.id_tramo]))
    return None


def _failed_ids(h: History):
    return {i.id_tramo for i in h.inspections if i.estado in ("Falla", "Reparado")}


def calibrate(target: float, site_effect: bool, seed: int) -> float:
    """β0 (con efecto) o β0 de la categoría (nulo) que da la prevalencia `target` en un pozo grande. Con semilla fija
    solo cambia el sorteo de la falla, así que la prevalencia es monótona en β0 (bisección)."""
    name = "fail_beta0" if site_effect else "fail_category_beta0"
    lo, hi = -12.0, 2.0
    for _ in range(25):
        mid = (lo + hi) / 2
        rates = []
        for s in range(3):
            h, _ = synthetic_history(n_zones=4, labors_per_zone=60, tramos_per_labor=12, seed=_seed(seed, s),
                                     truth=SyntheticTruth(site_effect=site_effect, **{name: mid}))
            rates.append(len(_failed_ids(h)) / len(h.tramos))
        lo, hi = (mid, hi) if np.mean(rates) < target else (lo, mid)
    return (lo + hi) / 2


# ---------- nivel 1 ----------

def level1(out: Out, reps: int, n_boot: int, seed: int):
    tr = SyntheticTruth()
    for ci, (n_pairs, n_labors) in enumerate((p, l) for p in L1_PAIRS for l in L1_LABORS):
        cell = f"pares={n_pairs};labores={n_labors}"
        cov = site = 0
        e_ols, e_bay, width = [], [], []
        for r in range(reps):
            h, _ = synthetic_history(n_zones=1, labors_per_zone=n_labors, seed=_seed(seed, 1, ci, r),
                                     tramos_per_labor=math.ceil(1.5 * n_pairs / n_labors) + 4)
            tram, _ = _by_labor(h)
            lists = [tram[k] for k in sorted(tram)]
            order = [t for i in range(max(map(len, lists))) for lst in lists if i < len(lst) for t in [lst[i]]]
            sub = History(tuple(order[:n_pairs]), h.support_types, ())
            m = fit_site_correlation(sub, "rmr_from_q", group_by=None, n_boot=n_boot, seed=r).mine
            assert m.n == n_pairs and m.n_labors == n_labors, (m.n, m.n_labors)
            site += m.status == "site"
            if m.a_ci is not None:
                cov += m.a_ci[0] <= tr.rmr_a <= m.a_ci[1]
                width.append((m.a_ci[1] - m.a_ci[0]) / abs(m.ols.a))
            e_ols.append(abs(m.ols.a - tr.rmr_a))
            e_bay.append(abs(m.bayes_a - tr.rmr_a))
        out.prop(1, "rmr_from_q", cell, "cobertura_ic95_pendiente", cov, reps)
        out.prop(1, "rmr_from_q", cell, "tasa_site", site, reps)
        out.mean(1, "rmr_from_q", cell, "eam_pendiente_ols", e_ols)
        out.mean(1, "rmr_from_q", cell, "eam_pendiente_bayes", e_bay)
        out.mean(1, "rmr_from_q", cell, "ancho_rel_ic95_pendiente", width)
        print(f"[nivel 1] {cell}: cobertura {cov}/{reps}, site {site}/{reps}, EAM OLS {np.mean(e_ols):.2f}, "
              f"EAM bayes {np.mean(e_bay):.2f}", flush=True)


# ---------- nivel 3 ----------

_GH_X, _GH_W = np.polynomial.hermite_e.hermegauss(40)
_GH_W = _GH_W / _GH_W.sum()


def p_marginal(eta, sd):
    """P(falla) verdadera de un tramo de una labor y zona NUEVAS: E[σ(η + b)], b ~ N(0, sd²) (Gauss-Hermite)."""
    eta = np.asarray(eta, float)
    return expit(eta[..., None] + sd * _GH_X) @ _GH_W


assert abs(p_marginal(0.3, 0.0) - expit(0.3)) < 1e-12 and abs(p_marginal(0.0, 2.0) - 0.5) < 1e-12


def _level3_ready(events):
    def ready(sel):
        fails = sum(t.id_tramo in ready.failed for t in sel)
        n_types = len({t.tipo_labor for t in sel})
        params = 5 + (n_types - 1 if n_types >= 2 else 0)  # = level3_parameters: base 4 + profundidad + tipos − 1
        zones = len({t.zona_nivel for t in sel})
        return min(fails, len(sel) - fails) >= events * params and zones >= 3
    return ready


def _cell_history(truth, events, seed):
    pool, _ = synthetic_history(n_zones=4, labors_per_zone=60, tramos_per_labor=12, truth=truth, seed=seed)
    ready = _level3_ready(events)
    ready.failed = _failed_ids(pool)
    h = grow(pool, np.random.default_rng(seed), ready)
    if h is not None:  # la cuenta propia coincide con la de la librería
        rows = level3_rows(h)
        f = sum(o.failed for o, _ in rows)
        assert len(rows) == len(h.tramos) and min(f, len(rows) - f) >= events * level3_parameters(rows)
    return h


def _describe(out, esc, cell, hs):
    out.mean(3, esc, cell, "tramos_medios", [len(h.tramos) for h in hs])
    out.mean(3, esc, cell, "labores_medias", [len({t.labor_codigo for t in h.tramos}) for h in hs])
    out.mean(3, esc, cell, "prevalencia_observada", [len(_failed_ids(h)) / len(h.tramos) for h in hs])


def level3_effect(out: Out, reps: int, n_boot: int, seed: int, beta0: dict):
    for pi in PREVALENCES:
        tr = SyntheticTruth(fail_beta0=beta0[(pi, True)])
        sd_b = math.hypot(tr.sd_zone_failure, tr.sd_labor_failure)
        att = 1 / math.sqrt(1 + (16 * math.sqrt(3) / (15 * math.pi)) ** 2 * sd_b ** 2)  # Zeger et al. (1988)
        true_coef = {"ln_q": tr.fail_beta_lnq * att, "ln_de": tr.fail_beta_lnde * att,
                     "support_rank": tr.fail_beta_rank * att, "ln_exposure": tr.fail_beta_lnexp * att}
        for ev in EVENTS:
            cell = f"prevalencia={pi:.2f};eventos_por_parametro={ev}"
            hs, site, conv = [], 0, 0
            cov_coef = Counter()
            pc_num, pc_den, light_num, light_den, free_num, free_den, choice = [], [], [], [], [], [], []
            for r in range(reps):
                s = _seed(seed, 3, int(pi * 100), ev, r)
                h = _cell_history(tr, ev, s)
                if h is None:
                    continue
                hs.append(h)
                m = fit_performance(h, n_boot=n_boot, seed=r)
                site += m.calibration == "site"
                for name, (lo, hi) in zip(m.features, m.coef_ci):
                    tc = true_coef.get(name, 0.0)
                    cov_coef[name if name in true_coef else "nulos"] += lo <= tc <= hi
                    cov_coef["n_nulos"] += name not in true_coef
                test_h, _ = synthetic_history(n_zones=2, labors_per_zone=10, truth=tr, seed=_seed(s, 99))
                test = [test_h.tramos[i] for i in np.random.default_rng(s).choice(len(test_h.tramos), N_TEST,
                                                                                  replace=False)]
                recs = recommend(m, test, threshold=THRESHOLD, exposure_days=EXPOSURE)
                pcov = pden = ln = ld = fn = fd = 0
                for t, rec in zip(test, recs):
                    base = (tr.fail_beta0 + tr.fail_beta_lnq * math.log(t.q_valor)
                            + tr.fail_beta_lnde * math.log(t.luz_m / t.esr) + tr.fail_beta_lnexp * math.log(EXPOSURE))
                    p_true = {o.code: float(p_marginal(base + tr.fail_beta_rank * o.order, sd_b)) for o in rec.options}
                    for o in rec.options:
                        pcov += o.p_low <= p_true[o.code] <= o.p_high
                        pden += 1
                    if rec.chosen is not None:
                        ld += 1
                        ln += p_true[rec.chosen] > THRESHOLD
                    # sin la compuerta de calibración: lo que pasaría si se eligiera igual
                    if rec.options and "support_rank" not in m.active_bounds:
                        free = next((o.code for o in rec.options if o.meets_threshold), None)
                        if free is not None:
                            fd += 1
                            fn += p_true[free] > THRESHOLD
                pc_num.append(pcov), pc_den.append(pden), light_num.append(ln), light_den.append(ld)
                free_num.append(fn), free_den.append(fd), choice.append(ld)
            n = len(hs)
            _describe(out, "efecto", cell, hs)
            out.prop(3, "efecto", cell, "tasa_site", site, n)
            for name in true_coef:
                out.prop(3, "efecto", cell, f"cobertura_ic95_coef_{name}", cov_coef[name], n)
            out.prop(3, "efecto", cell, "cobertura_ic95_coef_nulos", cov_coef["nulos"], cov_coef["n_nulos"])
            out.ratio(3, "efecto", cell, "cobertura_ic90_p_falla", pc_num, pc_den)
            out.ratio(3, "efecto", cell, "tasa_eleccion", choice, [N_TEST] * n)
            out.ratio(3, "efecto", cell, "tasa_demasiado_liviana", light_num, light_den)
            out.ratio(3, "efecto", cell, "tasa_demasiado_liviana_sin_compuerta", free_num, free_den)
            print(f"[nivel 3 efecto] {cell}: n={n}, site {site}/{n}, cob P {sum(pc_num) / max(1, sum(pc_den)):.3f}, "
                  f"liviana {sum(light_num)}/{sum(light_den)}, sin compuerta {sum(free_num)}/{sum(free_den)}",
                  flush=True)


def boundary_recommends(h: History, n_boot: int, seed: int) -> bool:
    """Regla de `fit_performance` con un modelo del sitio que TAMBIÉN tiene la categoría NGI: anida a la línea base
    (categoría + ln exposición), así que en el nulo de frontera la regla se mide en su tamaño real."""
    rows = level3_rows(h)
    order = {s.codigo_tipo: s.orden for s in h.support_types}
    ts = [t for _, t in rows]
    y = np.array([o.failed for o, _ in rows], dtype=float)
    lnq = np.array([math.log(t.q_valor) for t in ts])
    lnde = np.array([math.log(t.luz_m / t.esr) for t in ts])
    rank = np.array([order[t.sost_instalado] for t in ts], dtype=float)
    lnexp = np.array([math.log(o.exposure_days) for o, _ in rows])
    depth = np.array([t.profundidad_m for t in ts], dtype=float)
    use_depth = bool(np.ptp(depth) > 0)
    tipos = [t.tipo_labor for t in ts]
    cat = np.array([read_q_chart(t.q_valor, t.luz_m / t.esr).category for t in ts], dtype=float)

    def design(idx, lt):
        return np.array([_row(lnq[i], lnde[i], rank[i], lnexp[i], depth[i], tipos[i], use_depth, lt) + [cat[i]]
                         for i in idx], dtype=float)

    def site_fp(train, test):
        lt = _labor_types([tipos[i] for i in train])
        f = logistic_map_fit(design(train, lt), y[train], signs=_signs(use_depth, lt) + (0,))  # categoría libre
        return f.predict_proba(design(test, lt))

    X0 = np.column_stack([cat, lnexp])

    def baseline_fp(train, test):
        return logistic_map_fit(X0[train], y[train]).predict_proba(X0[test])

    labors, zones, years = tramo_groups(ts)
    report = validate(y, {"site": site_fp, "baseline_ngi": baseline_fp, "dummy": dummy_proba_fit_predict(y)},
                      kind="proba", labors=labors, zones=zones, years=years, metric=brier, higher_is_better=False,
                      reference=("dummy", "baseline_ngi"), k=5, n_boot=n_boot, seed=seed)
    lt = _labor_types(tipos)
    final = logistic_map_fit(design(range(y.size), lt), y, signs=_signs(use_depth, lt) + (0,))
    return bool(report.recommend and final.converged)


def level3_null(out: Out, reps: int, n_boot: int, seed: int, beta0: dict):
    for pi in PREVALENCES:
        tr = SyntheticTruth(site_effect=False, fail_category_beta0=beta0[(pi, False)])
        for ev in EVENTS:
            cell = f"prevalencia={pi:.2f};eventos_por_parametro={ev}"
            hs, false_rec, misspec = [], 0, 0
            for r in range(reps):
                h = _cell_history(tr, ev, _seed(seed, 4, int(pi * 100), ev, r))
                if h is None:
                    continue
                hs.append(h)
                false_rec += boundary_recommends(h, n_boot, r)
                misspec += fit_performance(h, n_boot=n_boot, seed=r).calibration == "site"
            n = len(hs)
            _describe(out, "nulo_frontera", cell, hs)
            out.prop(3, "nulo_frontera", cell, "tasa_recomendacion_falsa", false_rec, n)
            out.prop(3, "nulo_mal_especificado", cell, "tasa_site", misspec, n)
            print(f"[nivel 3 nulo] {cell}: n={n}, frontera {false_rec}/{n}, mal especificado {misspec}/{n}",
                  flush=True)


# ---------- nivel 2 ----------

def level2(out: Out, reps: int, n_boot: int, seed: int):
    for inc in (0.0, 0.5):
        tr = SyntheticTruth(practice_incoherence=inc)
        esc = "coherente" if inc == 0 else "incoherencia_0.5"
        for n_type in L2_PER_TYPE:
            cell = f"tramos_por_tipo={n_type}"
            n = coh_q = coh_de = coh = false_inc = 0
            cnum, cden, size, n_tramos, min_labors = [], [], [], [], []
            for r in range(reps):
                s = _seed(seed, 2, int(inc * 10), n_type, r)
                pool, _ = synthetic_history(n_zones=4, labors_per_zone=40, tramos_per_labor=12, truth=tr, seed=s)

                def ready(sel):
                    c = Counter(t.sost_instalado for t in sel)
                    return len(c) == 5 and min(c.values()) >= n_type
                h = grow(pool, np.random.default_rng(s), ready)
                if h is None:
                    continue
                n += 1
                n_tramos.append(len(h.tramos))
                labs = defaultdict(set)
                for t in h.tramos:
                    labs[t.sost_instalado].add(t.labor_codigo)
                min_labors.append(min(map(len, labs.values())))
                a = audit_practice(h, n_boot=n_boot, seed=r)
                v = a.verdicts
                coh_q += v["ln_q"] == "coherent"
                coh_de += v["ln_de"] == "coherent"
                coh += v["ln_q"] == v["ln_de"] == "coherent"
                false_inc += any(x.startswith("practice incoherent") for x in v.values())
                test_h, _ = synthetic_history(n_zones=2, labors_per_zone=10, truth=tr, seed=_seed(s, 99))
                levels = a.design.labor_levels
                test = [t for t in test_h.tramos if not levels or t.tipo_labor in levels]
                if math.isnan(a.conformal_threshold) or not test:
                    cnum.append(0), cden.append(0)
                    continue
                p = a.predict_proba(test)
                sets = (1.0 - p) <= a.conformal_threshold
                y = np.array([a.types.index(t.sost_instalado) for t in test])
                cnum.append(int(sets[np.arange(len(test)), y].sum())), cden.append(len(test))
                size.append(float(sets.sum(axis=1).mean()))
            out.mean(2, esc, cell, "tramos_medios", n_tramos)
            out.mean(2, esc, cell, "labores_min_por_tipo", min_labors)
            if inc == 0:
                out.prop(2, esc, cell, "tasa_coherent_ln_q", coh_q, n)
                out.prop(2, esc, cell, "tasa_coherent_ln_de", coh_de, n)
                out.prop(2, esc, cell, "tasa_coherent_ambos", coh, n)
            out.prop(2, esc, cell, "tasa_falso_incoherent", false_inc, n)  # en los dos escenarios es un error
            out.ratio(2, esc, cell, "cobertura_conforme_90_labores_nuevas", cnum, cden)
            out.mean(2, esc, cell, "tamano_medio_conjunto", size)
            print(f"[nivel 2 {esc}] {cell}: n={n}, coherent ambos {coh}/{n}, falso incoherent {false_inc}/{n}, "
                  f"cobertura conforme {sum(cnum) / max(1, sum(cden)):.3f}", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=20261105)
    ap.add_argument("--reps", type=int, default=50, help="réplicas por celda de los niveles 2 y 3")
    ap.add_argument("--reps-l1", type=int, default=200, help="réplicas por celda del nivel 1 (es barato)")
    ap.add_argument("--n-boot", type=int, default=500)
    ap.add_argument("--out", default="simulacion_minimos.csv")
    ap.add_argument("--quick", action="store_true", help="prueba corta: 3 réplicas, n_boot 100")
    ap.add_argument("--levels", default="1,2,3", help="niveles a correr, p. ej. 3")
    a = ap.parse_args(argv)
    if a.quick:
        a.reps, a.reps_l1, a.n_boot = 3, 5, 100
    # solo dentro de este proceso: cada celda se mide con la regla de validación, sin el corte del mínimo vigente
    _corr.MIN_PAIRS_LEVEL1 = _corr.MIN_LABORS_LEVEL1 = 1
    _perf.MIN_EVENTS_PER_PARAMETER_LEVEL3 = 1
    levels = {int(x) for x in a.levels.split(",")}
    out, t0 = Out(), time.time()
    if 1 in levels:
        level1(out, a.reps_l1, a.n_boot, a.seed)
    if 3 in levels:
        beta0 = {(pi, eff): calibrate(pi, eff, _seed(a.seed, 0, int(pi * 100), eff))
                 for pi in PREVALENCES for eff in (True, False)}
        for (pi, eff), b in beta0.items():
            out.rows.append((3, "efecto" if eff else "nulo_frontera", f"prevalencia={pi:.2f}",
                             "beta0_calibrado", b, "", "", "", ""))
            print(f"[calibración] prevalencia {pi:.2f}, {'efecto' if eff else 'nulo'}: beta0 = {b:.3f}", flush=True)
        level3_effect(out, a.reps, a.n_boot, a.seed, beta0)
        level3_null(out, a.reps, a.n_boot, a.seed, beta0)
    if 2 in levels:
        level2(out, a.reps, a.n_boot, a.seed)
    meta = (0, "meta", f"seed={a.seed};reps={a.reps};reps_l1={a.reps_l1};n_boot={a.n_boot};umbral={THRESHOLD};"
            f"exposicion_dias={EXPOSURE:g};n_test={N_TEST}", "segundos", round(time.time() - t0, 1), "", "", "", "")
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for row in [meta, *out.rows]:
            w.writerow([_fmt(x) for x in row])
    print(f"listo en {time.time() - t0:.0f} s: {len(out.rows)} métricas en {a.out}")


if __name__ == "__main__":
    main()
