"""Banco de pruebas del módulo predictivo con la mina sintética (Fase 5, tarea 5; plan M8).

Todo es sintético: las minas salen de `synthetic_mine` (`predictive/mine.py`), con mecanismo y verdad conocidos. No
lee ningún dato de mina. Corre cada escenario de `SCENARIOS` × N semillas (y una corrida con `defects=True` por
escenario, con la semilla de la réplica 0) por la auditoría y los niveles 1, 2 y 3, y mide contra la verdad.
Escribe un CSV ancho (una fila por escenario × semilla × defectos × umbral × horizonte) e imprime solo agregados.

Uso (con el paquete importable, desde la raíz del repo):
    .venv/Scripts/python.exe -I docs/investigacion/scripts/banco_mina_sintetica.py --reps 20 --reps-large 10
    ... --quick   # corrida corta de prueba

Los mínimos de la librería NO se tocan: se mide lo que hace el módulo tal como se entrega.
La recomendación se aplica a una SEGUNDA mina del mismo escenario (otra semilla): labores y zonas que el ajuste no vio.
"""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):  # un hilo por proceso: los procesos van en paralelo
    os.environ.setdefault(_v, "1")

import argparse  # noqa: E402
import csv  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from collections import Counter, defaultdict  # noqa: E402
from concurrent.futures import ProcessPoolExecutor, as_completed  # noqa: E402

import numpy as np  # noqa: E402

from rockmasspy import history as _hist  # noqa: E402
from rockmasspy.history import audit_history, level1_rows, level3_rows  # noqa: E402
from rockmasspy.predictive import (SCENARIOS, audit_practice, fit_performance, fit_site_correlation,  # noqa: E402
                                   recommend, synthetic_mine)
from rockmasspy.predictive.mine import _chart_rank  # noqa: E402  la carta Q como la lee el generador
from rockmasspy.predictive import performance as _perf  # noqa: E402
from rockmasspy.predictive.synthetic import SUPPORT_TYPES  # noqa: E402

THRESHOLDS = (0.05, 0.10)  # P(falla) aceptable
HORIZONS = (365.0, 1095.0)  # días; 3 años cabe en la exposición de las minas de 4 a 10 años
CODES = tuple(s.codigo_tipo for s in SUPPORT_TYPES)  # I…V
COST = {s.codigo_tipo: s.elementos.relative_cost for s in SUPPORT_TYPES}
DEFECT_KINDS = ("empty_cell", "q_mismatch", "overlapping_chainage", "inspection_before_installation",
                "unknown_support")
# hallazgo de la auditoría que corresponde a cada defecto; la celda vacía no tiene hallazgo propio: se cuenta
# cualquier hallazgo en su tramo
FINDING_FOR = {"q_mismatch": "q_mismatch", "overlapping_chainage": "overlapping_chainage",
               "inspection_before_installation": "inspection_before_installation",
               "unknown_support": "unknown_support", "empty_cell": None}
L1_KINDS = (("rq", "rmr_from_q"), ("gr", "gsi_from_rmr"))
WHY = ("elige", "no_calibrado", "parcial", "beta_rank", "cota_calidad_o_luz", "extrapola", "ninguno_cumple", "otro")
TEST_OFFSET = 99  # la mina de prueba: misma receta, otra semilla

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _seed(*parts) -> int:
    return int(np.random.SeedSequence(list(parts)).generate_state(1)[0])


def _why(reason):
    """Motivo de no elegir, en categorías cortas (los textos de `recommend` no llevan valores)."""
    if reason is None:
        return "elige"
    for key, tag in (("not_calibrated", "no_calibrado"), ("(partial)", "parcial"), ("support effect", "beta_rank"),
                     ("ignores rock", "cota_calidad_o_luz"), ("extrapolation", "extrapola"),
                     ("threshold", "ninguno_cumple")):
        if key in reason:
            return tag
    return "otro"


assert _why("no choice (not_calibrated): x") == "no_calibrado" and _why("no choice (partial): x") == "parcial"
assert _why(None) == "elige" and _why("no eligible type meets the threshold") == "ninguno_cumple"


def _line(x, y):
    a, b = np.polyfit(np.asarray(x, float), np.asarray(y, float), 1)
    return float(a), float(b)


# ---------- auditoría ----------

def run_audit(h, truth):
    a = audit_history(h)
    found = {(f.kind, f.id_tramo) for f in a.findings}
    ids_with_finding = {f.id_tramo for f in a.findings}
    out = {"aud_hallazgos": len(a.findings)}
    explained = set()
    for kind in DEFECT_KINDS:
        inj = [tid for k, tid, _ in truth.defects if k == kind]
        fk = FINDING_FOR[kind]
        det = [tid for tid in inj if ((fk, tid) in found if fk else tid in ids_with_finding)]
        if fk:
            explained |= {(fk, tid) for tid in inj}
        out[f"aud_iny_{kind}"], out[f"aud_det_{kind}"] = len(inj), len(det)
    out["aud_falsos"] = sum((f.kind, f.id_tramo) not in explained for f in a.findings)
    return out


# ---------- nivel 1 ----------

def _l1_fit_metrics(fit, ids, x_rec, truth_by_id, kind):
    """Cobertura de la pendiente verdadera (OLS sobre los valores verdaderos del mismo grupo de tramos), sesgo de la
    pendiente y cobertura del intervalo de predicción al 95 % del valor verdadero, dado el x registrado."""
    tt = [truth_by_id[i] for i in ids]
    xt = [math.log(t.q) for t in tt] if kind == "rmr_from_q" else [t.rmr for t in tt]
    yt = np.array([t.rmr if kind == "rmr_from_q" else t.gsi for t in tt])
    a_true, _ = _line(xt, yt)
    cover = math.nan if fit.a_ci is None else float(fit.a_ci[0] <= a_true <= fit.a_ci[1])
    _, lo, hi = fit.predict(np.asarray(x_rec, float))
    return dict(estado=fit.status, n=fit.n, pend=fit.a, pend_verdad=a_true, sesgo=fit.a - a_true, cubre_ic=cover,
                cob_pi=float(np.mean((yt >= lo) & (yt <= hi))))


def run_level1(h, truth, n_boot, seed, defects):
    out = {}
    by_id = {t.id_tramo: t for t in truth.tramos}
    for tag, kind in L1_KINDS:
        p = f"l1_{tag}_"
        try:
            res = fit_site_correlation(h, kind, group_by="litologia", n_boot=n_boot, seed=seed)
        except Exception as e:  # el banco no se cae; el tipo de error queda en el CSV
            out[p + "error"] = type(e).__name__
            continue
        sel = level1_rows(h, kind)
        ids = [t.id_tramo for t in sel.tramos]
        m = _l1_fit_metrics(res.mine, ids, sel.x, by_id, kind)
        if kind == "rmr_from_q" and not defects:  # la recta verdadera coincide con la que guarda la verdad
            assert abs(m["pend_verdad"] - truth.rmr_lnq_slope) < 1e-9 or len(ids) < len(truth.tramos)
        out |= {p + k: v for k, v in m.items()}
        dom = defaultdict(list)
        for i, t in enumerate(sel.tramos):
            dom[(t.litologia or "").strip()].append(i)
        ms = [_l1_fit_metrics(res.domains[k if k else "(no domain)"], [ids[i] for i in idx],
                              [sel.x[i] for i in idx], by_id, kind)
              for k, idx in dom.items() if len(idx) >= 3 and (k if k else "(no domain)") in res.domains]
        out[p + "dom_n"] = len(ms)
        out[p + "dom_site"] = sum(x["estado"] == "site" for x in ms)
        out[p + "dom_unstable"] = sum(x["estado"] == "unstable" for x in ms)
        cov = [x["cubre_ic"] for x in ms if not math.isnan(x["cubre_ic"])]
        out[p + "dom_con_ic"], out[p + "dom_cubre_ic"] = len(cov), int(sum(cov))
        out[p + "dom_sesgo_medio"] = float(np.mean([x["sesgo"] for x in ms])) if ms else math.nan
        out[p + "dom_cob_pi"] = float(np.average([x["cob_pi"] for x in ms], weights=[x["n"] for x in ms])) \
            if ms else math.nan
    return out


# ---------- nivel 2 ----------

def run_level2(h, truth, n_boot, seed):
    try:
        a = audit_practice(h, n_boot=n_boot, seed=seed)
    except Exception as e:
        return {"l2_error": type(e).__name__}
    by_id = {t.id_tramo: t for t in truth.tramos}
    with_set = [t for t in a.tramos if t.conformal_set is not None]
    dev = {t.id_tramo for t in with_set if by_id[t.id_tramo].practice_deviation != 0}
    flagged = {t.id_tramo for t in with_set if t.outside}
    hit = len(dev & flagged)
    v = a.verdicts
    return dict(l2_estado=a.status, l2_converge=int(a.converged), l2_ver_lnq=v["ln_q"], l2_ver_lnde=v["ln_de"],
                l2_incoherente=int(any(x.startswith("practice incoherent") for x in v.values())),
                l2_supera_carta=int(a.beyond_chart),
                l2_kappa_conc=math.nan if a.concordance is None or a.concordance.kappa is None
                else a.concordance.kappa,
                l2_con_conjunto=len(with_set),
                l2_tam_conjunto=float(np.mean([len(t.conformal_set) for t in with_set])) if with_set else math.nan,
                l2_desvios=len(dev), l2_fuera=len(flagged), l2_aciertos=hit,
                l2_precision=hit / len(flagged) if flagged else math.nan,
                l2_sensibilidad=hit / len(dev) if dev else math.nan)


# ---------- nivel 3 y recomendación ----------

def _blocker(m):
    b = m.recommendation_blockers
    return "ninguno" if not b else _why(b[0])


def _cost_metrics(prefix, picks, p_true, opt, thr):
    """Para pares (tramo, tipo elegido): demasiado liviano (P verdadera > umbral), más pesado que el óptimo y
    sobrecosto neto relativo frente al óptimo (solo tramos que tienen óptimo)."""
    n = len(picks)
    light = sum(p_true[i][c] > thr for i, c in picks)
    with_opt = [(i, c) for i, c in picks if opt[i] is not None]
    heavy = sum(CODES.index(c) > CODES.index(opt[i]) for i, c in with_opt)
    c_pick, c_opt = sum(COST[c] for _, c in with_opt), sum(COST[opt[i]] for i, _ in with_opt)
    return {prefix + "n": n, prefix + "liviana": light, prefix + "pesada": heavy, prefix + "con_optimo": len(with_opt),
            prefix + "sobrecosto_rel": c_pick / c_opt - 1 if c_opt else math.nan}


def run_level3(h, sc_name, test_seed, n_boot, seed):
    base = {}
    rows = level3_rows(h)
    base["l3_filas"] = len(rows)
    base["l3_fallas"] = sum(o.failed for o, _ in rows)
    try:
        m = fit_performance(h, n_boot=n_boot, seed=seed)
    except Exception as e:
        return [base | {"l3_error": type(e).__name__}]
    base |= dict(l3_estado=m.calibration, l3_bloqueo=_blocker(m), l3_theta=m.fit.theta if m.fit else math.nan,
                 l3_beta_rank=m.coefficients.get("support_rank", math.nan),
                 l3_beta_rank_inf=m.coef_ci[2][0] if m.fit else math.nan,
                 l3_beta_rank_sup=m.coef_ci[2][1] if m.fit else math.nan,
                 l3_exp_max=m.exposure_max)
    h2, tr2 = synthetic_mine(sc_name, seed=test_seed)
    test = list(h2.tramos)
    by2 = {t.id_tramo: t for t in tr2.tramos}
    chart = [CODES[_chart_rank(t.q_valor, t.luz_m / t.esr) - 1] for t in test]
    inst = [by2[t.id_tramo].installed_type for t in test]
    out = []
    for H in HORIZONS:
        p_true = [{c: tr2.p_fail(t.id_tramo, c, H) for c in CODES} for t in test]
        for thr in THRESHOLDS:
            r = dict(base, umbral=thr, horizonte_dias=H, rec_tramos=len(test))
            opt = [next((c for c in CODES if p[c] <= thr), None) for p in p_true]
            r["opt_sin"] = sum(o is None for o in opt)
            recs = recommend(m, test, threshold=thr, exposure_days=H)
            why = Counter(_why(x.reason) for x in recs)
            r |= {f"rec_why_{w}": why[w] for w in WHY}
            picks = [(i, x.chosen) for i, x in enumerate(recs) if x.chosen is not None]
            r |= _cost_metrics("rec_", picks, p_true, opt, thr)
            r["rec_igual_carta"] = sum(c == chart[i] for i, c in picks)
            c_rec, c_chart = sum(COST[c] for _, c in picks), sum(COST[chart[i]] for i, _ in picks)
            r["rec_costo_vs_carta"] = c_rec / c_chart - 1 if picks else math.nan  # en los mismos tramos
            r |= _cost_metrics("carta_", list(enumerate(chart)), p_true, opt, thr)
            r |= _cost_metrics("inst_", list(enumerate(inst)), p_true, opt, thr)
            r["carta_liviana_en_elegidos"] = sum(p_true[i][chart[i]] > thr for i, _ in picks)
            r["inst_liviana_en_elegidos"] = sum(p_true[i][inst[i]] > thr for i, _ in picks)
            out.append(r)
    return out


def _set_min_events(n):
    """Solo en este proceso (sensibilidad): el mínimo de eventos por parámetro del nivel 3. La librería no cambia."""
    if n is not None:
        _hist.MIN_EVENTS_PER_PARAMETER_LEVEL3 = _perf.MIN_EVENTS_PER_PARAMETER_LEVEL3 = n


# ---------- un trabajo: escenario × semilla × defectos ----------

def job(sc_name, rep, seed, defects, n_boot):
    t0 = time.time()
    h, truth = synthetic_mine(sc_name, seed=seed, defects=defects)
    common = dict(escenario=sc_name, replica=rep, semilla=seed, defectos=int(defects), tramos=len(h.tramos))
    common |= run_audit(h, truth)
    common |= run_level1(h, truth, n_boot, seed, defects)
    common |= run_level2(h, truth, n_boot, seed)
    rows = run_level3(h, sc_name, _seed(seed, TEST_OFFSET), n_boot, seed)
    secs = round(time.time() - t0, 1)
    return [common | r | {"segundos": secs} for r in rows]


# ---------- resumen (solo agregados) ----------

def _med(xs):
    xs = [x for x in xs if isinstance(x, (int, float)) and math.isfinite(x)]
    if not xs:
        return "—"
    return f"{np.median(xs):.3g} [{min(xs):.3g}, {max(xs):.3g}]"


def _ratio(rows, num, den):
    n, d = sum(r.get(num, 0) or 0 for r in rows), sum(r.get(den, 0) or 0 for r in rows)
    return f"{n / d:.3f} ({n}/{d})" if d else "sin casos"


def summary(rows):
    clean = [r for r in rows if r["defectos"] == 0]
    scen = list(dict.fromkeys(r["escenario"] for r in rows))
    print("\n## Auditoría (corrida con defectos, una por escenario): detectados/inyectados")
    tot = Counter()
    for r in rows:
        if r["defectos"] == 1 and r["umbral"] == THRESHOLDS[0] and r["horizonte_dias"] == HORIZONS[0]:
            for k in DEFECT_KINDS:
                tot["iny_" + k] += r[f"aud_iny_{k}"]
                tot["det_" + k] += r[f"aud_det_{k}"]
            tot["falsos"] += r["aud_falsos"]
    print(" | ".join(f"{k}: {tot['det_' + k]}/{tot['iny_' + k]}" for k in DEFECT_KINDS), "| falsos:", tot["falsos"])
    first = [r for r in clean if r["umbral"] == THRESHOLDS[0] and r["horizonte_dias"] == HORIZONS[0]]
    print("hallazgos en corridas limpias:", sum(r["aud_hallazgos"] for r in first))
    print("\n## Niveles 1 y 2 por escenario (corridas limpias; mediana [mín, máx] y conteos)")
    for s in scen:
        rs = [r for r in first if r["escenario"] == s]
        st = Counter(r.get("l1_rq_estado") for r in rs)
        stg = Counter(r.get("l1_gr_estado") for r in rs)
        print(f"{s}: n={len(rs)} tramos {_med([r['tramos'] for r in rs])} | L1 RMR–lnQ {dict(st)} "
              f"pend {_med([r.get('l1_rq_pend') for r in rs])} verdad {_med([r.get('l1_rq_pend_verdad') for r in rs])}"
              f" cubre {sum(r.get('l1_rq_cubre_ic', 0) == 1 for r in rs)}/{len(rs)} cobPI "
              f"{_med([r.get('l1_rq_cob_pi') for r in rs])} dom site {_ratio(rs, 'l1_rq_dom_site', 'l1_rq_dom_n')} "
              f"dom cubre {_ratio(rs, 'l1_rq_dom_cubre_ic', 'l1_rq_dom_con_ic')} | L1 GSI–RMR {dict(stg)} "
              f"sesgo {_med([r.get('l1_gr_sesgo') for r in rs])} cubre "
              f"{sum(r.get('l1_gr_cubre_ic', 0) == 1 for r in rs)}/{len(rs)} cobPI {_med([r.get('l1_gr_cob_pi') for r in rs])}")
        print(f"    L2 converge {sum(r.get('l2_converge', 0) for r in rs)}/{len(rs)} lnQ "
              f"{dict(Counter(r.get('l2_ver_lnq') for r in rs))} lnDe {dict(Counter(r.get('l2_ver_lnde') for r in rs))}"
              f" incoherente {sum(r.get('l2_incoherente', 0) for r in rs)} supera carta "
              f"{sum(r.get('l2_supera_carta', 0) for r in rs)} kappa {_med([r.get('l2_kappa_conc') for r in rs])} "
              f"conjunto {_med([r.get('l2_tam_conjunto') for r in rs])} precisión {_ratio(rs, 'l2_aciertos', 'l2_fuera')}"
              f" sensibilidad {_ratio(rs, 'l2_aciertos', 'l2_desvios')} errores "
              f"{dict(Counter(r.get('l2_error') for r in rs if r.get('l2_error')))}")
    print("\n## Nivel 3 y recomendación (corridas limpias)")
    for s in scen:
        rs0 = [r for r in first if r["escenario"] == s]
        print(f"{s}: estado {dict(Counter(r.get('l3_estado') for r in rs0))} bloqueo "
              f"{dict(Counter(r.get('l3_bloqueo') for r in rs0))} fallas {_med([r['l3_fallas'] for r in rs0])} "
              f"filas {_med([r['l3_filas'] for r in rs0])}")
        for H in HORIZONS:
            for thr in THRESHOLDS:
                rs = [r for r in clean if r["escenario"] == s and r["umbral"] == thr and r["horizonte_dias"] == H]
                print(f"    H={H:g} umbral={thr}: elige {_ratio(rs, 'rec_n', 'rec_tramos')} liviana "
                      f"{_ratio(rs, 'rec_liviana', 'rec_n')} sobrecosto {_med([r.get('rec_sobrecosto_rel') for r in rs])}"
                      f" vs carta {_med([r.get('rec_costo_vs_carta') for r in rs])} igual carta {_ratio(rs, 'rec_igual_carta', 'rec_n')}"
                      f" carta liviana en elegidos {_ratio(rs, 'carta_liviana_en_elegidos', 'rec_n')} | carta liviana "
                      f"{_ratio(rs, 'carta_liviana', 'carta_n')} sobrecosto "
                      f"{_med([r.get('carta_sobrecosto_rel') for r in rs])} | instalado liviana "
                      f"{_ratio(rs, 'inst_liviana', 'inst_n')} sobrecosto {_med([r.get('inst_sobrecosto_rel') for r in rs])}"
                      f" | sin óptimo {_ratio(rs, 'opt_sin', 'rec_tramos')}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=20261105)
    ap.add_argument("--reps", type=int, default=20, help="semillas por escenario")
    ap.add_argument("--reps-large", type=int, default=10, help="semillas de large_mine")
    ap.add_argument("--n-boot", type=int, default=500)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 4))
    ap.add_argument("--scenarios", default=",".join(SCENARIOS))
    ap.add_argument("--out", default="docs/investigacion/banco_mina_sintetica.csv")
    ap.add_argument("--quick", action="store_true", help="prueba corta: 2 semillas, n_boot 100")
    ap.add_argument("--min-events-l3", type=int, default=None,
                    help="sensibilidad: baja el mínimo de eventos por parámetro del nivel 3 dentro del proceso")
    ap.add_argument("--no-defects", action="store_true", help="sin la gemela con defectos")
    a = ap.parse_args(argv)
    if a.quick:
        a.reps, a.reps_large, a.n_boot = 2, 1, 100
    names = a.scenarios.split(",")
    jobs = []
    for si, name in enumerate(names):
        reps = a.reps_large if name == "large_mine" else a.reps
        seeds = [_seed(a.seed, list(SCENARIOS).index(name), r) for r in range(reps)]
        jobs += [(name, r, s, False, a.n_boot) for r, s in enumerate(seeds)]
        if not a.no_defects:
            jobs.append((name, 0, seeds[0], True, a.n_boot))  # la gemela con defectos de la réplica 0
    t0, rows, secs = time.time(), [], defaultdict(float)
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_set_min_events, initargs=(a.min_events_l3,)) as ex:
        futs = {ex.submit(job, *j): j for j in jobs}
        for k, f in enumerate(as_completed(futs), 1):
            res = f.result()
            rows += res
            secs[res[0]["escenario"]] += res[0]["segundos"]
            if k % 20 == 0 or k == len(jobs):
                print(f"[{k}/{len(jobs)}] {time.time() - t0:.0f} s", flush=True)
    order = {n: i for i, n in enumerate(names)}
    rows.sort(key=lambda r: (order[r["escenario"]], r["defectos"], r["replica"], r["horizonte_dias"], r["umbral"]))
    cols = list(dict.fromkeys(k for r in rows for k in r))
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.6g}" if isinstance(v, float) else v) for k, v in r.items()})
    summary(rows)
    print("\nsegundos de CPU por escenario (suma de trabajos):", {k: round(v) for k, v in secs.items()})
    print(f"listo en {time.time() - t0:.0f} s de reloj con {a.workers} procesos: {len(rows)} filas en {a.out}; "
          f"seed={a.seed} reps={a.reps} reps_large={a.reps_large} n_boot={a.n_boot} min_events_l3={a.min_events_l3}")


if __name__ == "__main__":
    main()
