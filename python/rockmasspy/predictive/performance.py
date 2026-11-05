"""Nivel 3: modelo de desempeño y recomendación de sostenimiento (Fase 4C, tarea 12; plan R9, R10, R13 y R14).

P(falla | calidad, De, sostenimiento, exposición…) con la logística MAP de `stats.py` (prior Cauchy y Laplace;
Gelman et al. 2008 [V2]) y restricciones de signo (`MODELOS_SOSTENIMIENTO.md` §3.3, decisión de diseño): peor
macizo, más luz, más exposición y más profundidad no bajan P(falla); más sostenimiento no la sube. Las filas salen
de `history.level3_rows`, la misma selección que cuenta la preparación del nivel 3.

Validación (R7) con `validate`: Brier (menor es mejor) contra el ficticio de prevalencia y contra la línea base de
nivel 0. Decisión de diseño de la línea base: la logística MAP con la categoría de la carta Q NGI
(`read_q_chart(Q, luz/ESR)`) MÁS ln exposición, sin cotas de signo. La exposición entra porque el modelo del sitio
la tiene y la carta no: sin ella, el sitio «ganaría» solo por saber cuánto tiempo estuvo abierta la labor, que no es
conocimiento propio del sitio sobre el macizo. Sin cotas, la línea base es la más fuerte posible con esas dos
variables (comparación conservadora). Se reajusta en cada pliegue.

La recomendación (R10, §4 punto 7) muestra P(falla) con su intervalo para CADA tipo de la mina; elige el más
liviano cuyo límite superior queda bajo el umbral del ingeniero (obligatorio, sin valor por defecto) solo si el
modelo está calibrado al sitio. La decisión final queda en las columnas `decision_ingeniero` y `motivo`.

Privacidad (R13): el modelo y su JSON nunca llevan filas ni ids; los mensajes y las razones solo llevan nombres de
variables, códigos de tipo de sostenimiento y conteos. El `id_tramo` va como campo de `Recommendation` y en la
tabla de resultados, nunca dentro de un texto.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
from scipy.stats import norm

from .. import __version__
from ..batch import write_table
from ..history import (MIN_EVENTS_PER_PARAMETER_LEVEL3, MIN_ZONES_LEVEL3, History, LevelReadiness, level3_parameters,
                       level3_rows)
from ..q_support import read_q_chart
from .stats import (LogisticMapFit, _level, average_precision, brier, calibration_curve, calibration_intercept_slope,
                    logistic_map_fit, roc_auc)
from .validation import (Comparison, Improvement, ValidationReport, dummy_proba_fit_predict, group_kfold, out_of_fold,
                         tramo_groups, validate)

SCHEMA_VERSION = 1
CALIBRATION_LEVELS = ("site", "partial", "not_calibrated")
QUALITIES = ("q", "rmr")
MAIN, BASELINE, DUMMY = "site", "baseline_ngi", "dummy"
COEF_LEVEL = 0.95  # IC de Laplace de los coeficientes
MAHALANOBIS_PERCENTILE = 99.0
_ONEHOT = "tipo_labor="


# ---------- datos del nivel 3 ----------

def _get(t, name):
    """Un campo de un `HistoryTramo`, de cualquier objeto con esos atributos o de un dict."""
    return t.get(name) if isinstance(t, Mapping) else getattr(t, name, None)


def _labor_types(tipos) -> tuple[str, ...]:
    """Tipos de labor para la codificación una-caliente: el primero (orden alfabético) es la referencia."""
    lt = sorted({x for x in tipos if x is not None})
    return tuple(lt) if len(lt) >= 2 else ()


def _feature_names(quality: str, use_depth: bool, labor_types) -> tuple[str, ...]:
    return (("ln_q" if quality == "q" else "rmr", "ln_de", "support_rank", "ln_exposure")
            + (("depth_m",) if use_depth else ()) + tuple(_ONEHOT + x for x in labor_types[1:]))


def _signs(use_depth: bool, labor_types) -> tuple[int, ...]:
    # peor macizo (Q o RMR más bajos) y más luz, exposición y profundidad no bajan P(falla); más sostenimiento no la
    # sube; el tipo de labor queda libre
    return (-1, 1, -1, 1) + ((1,) if use_depth else ()) + (0,) * max(0, len(labor_types) - 1)


def _row(quality_value: float, lnde: float, rank: float, lnexp: float, depth, tipo, use_depth, labor_types):
    return ([quality_value, lnde, rank, lnexp] + ([depth] if use_depth else [])
            + [float(tipo == x) for x in labor_types[1:]])


# ---------- el modelo ----------

@dataclass(frozen=True)
class PerformanceModel:
    """Modelo de desempeño del nivel 3. No lleva filas ni ids: solo coeficientes, rangos, métricas y conteos.

    `fit` es la logística MAP en la escala ORIGINAL de las variables `features` (ln Q o RMR, ln De, rango del tipo,
    ln exposición en días, profundidad si está en todas las filas y `tipo_labor=<tipo>` una-caliente contra
    `labor_types[0]`). `coef_ci` = IC 95 % de Laplace de cada coeficiente. `train_min`/`train_max`, `maha_mean`,
    `maha_inv` (pseudoinversa de la covarianza) y `maha_p99` son el dominio de aplicabilidad.
    """

    quality: str
    features: tuple[str, ...]
    labor_types: tuple[str, ...]  # () si hay menos de 2 tipos con datos
    use_depth: bool
    fit: LogisticMapFit | None = field(repr=False)  # None: todos los tramos con el mismo resultado
    signs: tuple[int, ...]
    coef_ci: tuple[tuple[float, float], ...]
    active_bounds: tuple[str, ...]  # variables con la cota de signo activa (coeficiente 0)
    support_types: tuple[tuple[str, int], ...]  # (código, orden), del más liviano al más pesado
    calibration: str  # uno de CALIBRATION_LEVELS
    calibration_reason: str
    metrics: dict  # fuera de pliegue (partición por labor): brier, calibración, AUC, PR
    calibration_curve: tuple[tuple[float, float, int], ...]  # (p media, falla observada, n) por decil
    validation: ValidationReport | None = field(repr=False)
    train_min: tuple[float, ...]
    train_max: tuple[float, ...]
    maha_mean: tuple[float, ...] = field(repr=False)
    maha_inv: tuple[tuple[float, ...], ...] = field(repr=False)
    maha_p99: float
    counts: dict
    warnings: tuple[str, ...]
    version: str = __version__
    schema_version: int = SCHEMA_VERSION

    @property
    def coefficients(self) -> dict[str, float]:
        return {} if self.fit is None else dict(zip(self.features, map(float, self.fit.coef)))


def _readiness(rows) -> LevelReadiness:
    """La preparación del nivel 3, con las mismas cuentas y mínimos que `audit_history` (R6)."""
    failures = sum(o.failed for o, _ in rows)
    params = level3_parameters(rows)
    return LevelReadiness(3, "performance", {"minority_class": min(failures, len(rows) - failures),
                                             "zones": len({t.zona_nivel for _, t in rows} - {None})},
                          {"minority_class": MIN_EVENTS_PER_PARAMETER_LEVEL3 * params, "zones": MIN_ZONES_LEVEL3})


def _oof_metrics(y, p) -> tuple[dict, tuple]:
    out = {"n": int(y.size), "brier": brier(y, p)}
    for name, f in (("auc", roc_auc), ("average_precision", average_precision)):
        try:
            out[name] = f(y, p)
        except ValueError:  # una sola clase en las filas cubiertas
            out[name] = math.nan
    try:
        out["calibration_intercept"], out["calibration_slope"] = calibration_intercept_slope(y, p)
    except ValueError:
        out["calibration_intercept"] = out["calibration_slope"] = math.nan
    curve = tuple((float(a), float(b), int(c)) for a, b, c in zip(*calibration_curve(y, p)))
    return out, curve


def fit_performance(history: History, *, quality: str = "q", k: int = 5, n_boot: int = 2000,
                    seed: int = 0) -> PerformanceModel:
    """Ajusta el modelo de desempeño del nivel 3 (R9, R10) y lo valida contra el ficticio y la línea base NGI (R7).

    - `quality`: "q" (ln Q, por defecto) o "rmr" (RMR tal como viene; las filas sin RMR quedan fuera, con aviso).
    - Estado: "site" (cumple el mínimo del nivel 3 de `audit_history`, la partición por labor supera a las dos
      referencias con el IC 95 % de la mejora del Brier sobre cero, ningún pliegue del modelo principal falló y el
      ajuste convergió), "partial" (cumple el mínimo pero no lo demás: muestra P(falla), no elige) y
      "not_calibrated" (bajo el mínimo: el ajuste igual se hace, es la curva del prior actualizada con pocos datos).
    """
    if quality not in QUALITIES:
        raise ValueError(f"quality must be one of {', '.join(QUALITIES)}")
    rows = level3_rows(history)
    warns = []
    if quality == "rmr":
        kept = tuple(r for r in rows if r[1].rmr_valor is not None)
        if len(kept) < len(rows):
            warns.append(f"{len(rows) - len(kept)} tramo(s) without rmr_valor left out")
        rows = kept
    if len(rows) < 2:
        raise ValueError(f"level 3 needs at least 2 usable tramos (inspected, with Q, span, ESR, installed support "
                         f"and exposure), got {len(rows)}")
    order = {s.codigo_tipo: s.orden for s in history.support_types}
    ts = [t for _, t in rows]
    y = np.array([o.failed for o, _ in rows], dtype=float)
    qual = np.array([math.log(t.q_valor) if quality == "q" else t.rmr_valor for t in ts], dtype=float)
    lnde = np.array([math.log(t.luz_m / t.esr) for t in ts])
    rank = np.array([order[t.sost_instalado] for t in ts], dtype=float)
    lnexp = np.array([math.log(o.exposure_days) for o, _ in rows])
    tipos = [t.tipo_labor for t in ts]
    use_depth = all(t.profundidad_m is not None for t in ts)
    depth = np.array([t.profundidad_m for t in ts], dtype=float) if use_depth else None
    if use_depth and np.ptp(depth) == 0:
        use_depth, depth = False, None
        warns.append("depth_m is the same in every tramo: left out of the model")
    labor_types = _labor_types(tipos)
    for name, col in zip(("quality", "ln_de", "support_rank", "ln_exposure"), (qual, lnde, rank, lnexp)):
        if np.ptp(col) == 0:
            raise ValueError(f"level 3: {name} is the same in every usable tramo; its effect cannot be estimated")

    def design(idx, lt):
        return np.array([_row(qual[i], lnde[i], rank[i], lnexp[i], None if depth is None else depth[i], tipos[i],
                              use_depth, lt) for i in idx], dtype=float)

    def site_fp(train, test):  # la codificación de tipo_labor se arma con train (R7)
        lt = _labor_types([tipos[i] for i in train])
        f = logistic_map_fit(design(train, lt), y[train], signs=_signs(use_depth, lt))
        return f.predict_proba(design(test, lt))

    cat = np.array([read_q_chart(t.q_valor, t.luz_m / t.esr).category for t in ts], dtype=float)
    X0 = np.column_stack([cat, lnexp])

    def baseline_fp(train, test):
        return logistic_map_fit(X0[train], y[train]).predict_proba(X0[test])

    labors, zones, years = tramo_groups(ts)
    labors = [g if g is not None else (None, i) for i, g in enumerate(labors)]  # sin labor: su propio grupo
    report = validate(y, {MAIN: site_fp, BASELINE: baseline_fp, DUMMY: dummy_proba_fit_predict(y)}, kind="proba",
                      labors=labors, zones=zones, years=years, metric=brier, higher_is_better=False,
                      reference=(DUMMY, BASELINE), k=k, n_boot=n_boot, seed=seed)
    try:
        oof = out_of_fold(group_kfold(labors, k=k, seed=seed), site_fp, y.size, kind="proba")
    except ValueError:  # una sola labor: no hay partición agrupada
        oof = None
    if oof is not None and oof.covered.any():
        metrics, curve = _oof_metrics(y[oof.covered], oof.pred[oof.covered])
    else:
        metrics, curve = {"n": 0}, ()

    X = design(range(y.size), labor_types)
    signs = _signs(use_depth, labor_types)
    names = _feature_names(quality, use_depth, labor_types)
    # sin fallas o sin tramos estables no hay curva que ajustar (la logística exige las dos clases): sin modelo
    fit = logistic_map_fit(X, y, signs=signs) if 0 < y.sum() < y.size else None
    coef_ci, active = (), ()
    if fit is None:
        warns.append("no events / no non-events: every usable tramo has the same outcome; no model is fitted")
    else:
        z = norm.ppf(0.5 + COEF_LEVEL / 2)
        sd = np.sqrt(np.diag(fit.cov)[:-1])
        coef_ci = tuple((float(c - z * s), float(c + z * s)) for c, s in zip(fit.coef, sd))
        active = tuple(names[j] for j in fit.active_bounds)
        if not fit.converged:
            warns.append(f"the final fit did not converge: {fit.message}")
    for a in active:
        warns.append(f"sign bound active for {a}: its coefficient is 0 (the data push it the other way)"
                     + ("; the model does not separate the support types, so no type is chosen"
                        if a == "support_rank" else ""))
    if labor_types and any(x is None for x in tipos):
        warns.append(f"{sum(x is None for x in tipos)} tramo(s) without tipo_labor read as the reference type")
    n_eval = sum(o.start_from_evaluation for o, _ in rows)
    if n_eval:
        warns.append(f"{n_eval} tramo(s) without fecha_instalacion: exposure counted from fecha_evaluacion")

    ready = _readiness(rows)
    if not ready.ready or fit is None:
        miss = ", ".join(f"{k} short by {v}" for k, v in ready.missing.items() if v)
        level, reason = "not_calibrated", (f"not calibrated to the site: below the level-3 minimum ({miss}); the "
                                           "fit is the prior updated with few data")
        if fit is None:
            reason = "not calibrated to the site: no events / no non-events, no model is fitted"
    elif not fit.converged:
        level, reason = "partial", "the final fit did not converge: no recommendation"
    elif not report.recommend:  # la regla de pliegues fallidos y réplicas descartadas vive en validation.py
        level, reason = "partial", ("the site model does not beat the NGI baseline and the dummy in the grouped "
                                    "validation (95 % CI of the Brier gain includes 0, or a fold failed)")
    else:
        level, reason = "site", "calibrated to the site: beats the NGI baseline and the dummy"

    cov = np.cov(X, rowvar=False).reshape(X.shape[1], X.shape[1])
    inv = np.linalg.pinv(cov)
    mean = X.mean(axis=0)
    dist = np.sqrt(np.einsum("ij,jk,ik->i", X - mean, inv, X - mean).clip(min=0))
    counts = {"tramos": int(y.size), "failures": int(y.sum()), "non_failures": int(y.size - y.sum()),
              "labors": len(set(labors)), "zones": len({x for x in zones if x is not None}),
              "parameters": len(names), "start_from_evaluation": n_eval,
              "minority_class": ready.counts["minority_class"],
              "minority_class_minimum": ready.minimums["minority_class"]}
    return PerformanceModel(
        quality=quality, features=names, labor_types=labor_types, use_depth=use_depth, fit=fit, signs=signs,
        coef_ci=coef_ci, active_bounds=active,
        support_types=tuple((s.codigo_tipo, s.orden) for s in sorted(history.support_types, key=lambda s: s.orden)),
        calibration=level, calibration_reason=reason, metrics=metrics, calibration_curve=curve, validation=report,
        train_min=tuple(map(float, X.min(axis=0))), train_max=tuple(map(float, X.max(axis=0))),
        maha_mean=tuple(map(float, mean)), maha_inv=tuple(tuple(map(float, r)) for r in inv),
        maha_p99=float(np.percentile(dist, MAHALANOBIS_PERCENTILE)), counts=counts, warnings=tuple(warns))


# ---------- recomendación ----------

@dataclass(frozen=True)
class SupportOption:
    code: str
    order: int
    p_failure: float
    p_low: float
    p_high: float
    meets_threshold: bool  # límite superior ≤ umbral
    mahalanobis: float
    extrapolated: bool  # rango del tipo fuera del entrenamiento o Mahalanobis sobre el percentil 99


@dataclass(frozen=True)
class Reason:
    variable: str
    contribution: float  # β·(x − media) en la escala logit
    effect: str  # "raises", "lowers" o "neutral" (sobre P(falla))


@dataclass(frozen=True)
class Recommendation:
    """Recomendación para un tramo. `chosen` es None con `reason` (el motivo); las razones son del tipo elegido o,
    si no hay elegido, del más liviano. `conformal_set` sale del nivel 2 si se pasó `practice`."""

    id_tramo: str | None
    options: tuple[SupportOption, ...]
    chosen: str | None
    reason: str | None
    reasons: tuple[Reason, ...]
    extrapolation: bool
    extrapolation_notes: tuple[str, ...]
    calibration: str
    threshold: float
    exposure_days: float
    level: float
    conformal_set: tuple[str, ...] | None = None


def _probability_threshold(threshold) -> float:
    if threshold is None:
        raise ValueError("threshold is required: the engineer sets the acceptable P(failure); there is no default")
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float, np.integer, np.floating)) \
            or not 0 < threshold < 1:
        raise ValueError("threshold must be a probability strictly between 0 and 1")
    return float(threshold)


def _exposure(exposure_days) -> float:
    if exposure_days is None:
        raise ValueError("exposure_days is required: the engineer sets the horizon (days); there is no default")
    if isinstance(exposure_days, bool) or not isinstance(exposure_days, (int, float, np.integer, np.floating)) \
            or not math.isfinite(exposure_days) or exposure_days <= 0:
        raise ValueError("exposure_days must be a positive number of days")
    return float(exposure_days)


def _tramo_inputs(model: PerformanceModel, t):
    """(calidad, ln De, profundidad, tipo, faltantes) de un tramo; faltantes = nombres de columnas, sin valores."""
    qv = _get(t, "q_valor" if model.quality == "q" else "rmr_valor")
    luz, esr, depth = _get(t, "luz_m"), _get(t, "esr"), _get(t, "profundidad_m")
    missing = [c for c, v in (("q_valor" if model.quality == "q" else "rmr_valor", qv), ("luz_m", luz), ("esr", esr))
               if v is None or (c != "rmr_valor" and v <= 0)]
    if model.use_depth and depth is None:
        missing.append("profundidad_m")
    if missing:
        return None, None, None, None, missing
    qual = math.log(qv) if model.quality == "q" else float(qv)
    return qual, math.log(luz / esr), depth, _get(t, "tipo_labor"), []


def _model_row(model, qual, lnde, rank, lnexp, depth, tipo):
    return _row(qual, lnde, rank, lnexp, depth, tipo, model.use_depth, model.labor_types)


def recommend(model: PerformanceModel, tramos, *, threshold, exposure_days, practice=None,
              level: float = 0.9) -> tuple[Recommendation, ...]:
    """P(falla) con su intervalo (`level`, 90 % por defecto) de cada tipo de la mina para cada tramo (R10).

    - `threshold` (P(falla) aceptable) y `exposure_days` (horizonte en días) son OBLIGATORIOS: los fija el
      ingeniero. Se elige el tipo más liviano cuyo límite SUPERIOR queda ≤ el umbral, solo con calibración "site"
      y si la cota de signo del rango del sostenimiento no quedó activa (con β = 0 el modelo no distingue tipos y
      el más liviano «cumpliría» sin serlo).
    - `tramos`: `HistoryTramo`, o cualquier objeto (o dict) con `id_tramo`, `q_valor` (o `rmr_valor`), `luz_m`,
      `esr`, `tipo_labor` y `profundidad_m` (si el modelo la usa). Un tramo con datos faltantes sale sin opciones.
    - `practice`: el nivel 2, opcional. Protocolo: cualquier objeto con `conformal_set(tramo) -> tuple[str, ...]`
      (los códigos del conjunto conforme de lo que la mina instalaría); su salida va a `conformal_set`.
    """
    thr, exp = _probability_threshold(threshold), _exposure(exposure_days)
    lv = _level(level)
    lnexp = math.log(exp)
    lo_tr, hi_tr = np.array(model.train_min), np.array(model.train_max)
    mean, inv = np.array(model.maha_mean), np.array(model.maha_inv)
    n_cont = 4 + model.use_depth  # columnas no una-caliente
    out = []
    for t in tramos:
        tid = _get(t, "id_tramo")
        cset = None if practice is None else tuple(practice.conformal_set(t))
        qual, lnde, depth, tipo, missing = _tramo_inputs(model, t)
        if model.fit is None:
            out.append(Recommendation(tid, (), None, f"no choice ({model.calibration}): {model.calibration_reason}",
                                      (), False, (), model.calibration, thr, exp, lv, cset))
            continue
        if missing:
            out.append(Recommendation(tid, (), None, f"missing or invalid input: {', '.join(missing)}", (), False, (),
                                      model.calibration, thr, exp, lv, cset))
            continue
        X = np.array([_model_row(model, qual, lnde, r, lnexp, depth, tipo) for _, r in model.support_types])
        p, p_lo, p_hi = model.fit.predict_interval(X, lv)
        d = np.sqrt(np.einsum("ij,jk,ik->i", X - mean, inv, X - mean).clip(min=0))
        outside = (X[:, :n_cont] < lo_tr[:n_cont]) | (X[:, :n_cont] > hi_tr[:n_cont])
        rank_out = outside[:, 2]
        far = d > model.maha_p99
        options = tuple(SupportOption(c, o, float(p[i]), float(p_lo[i]), float(p_hi[i]), bool(p_hi[i] <= thr),
                                      float(d[i]), bool(rank_out[i] or far[i]))
                        for i, (c, o) in enumerate(model.support_types))
        notes = [f"{model.features[j]} outside the training range" for j in range(n_cont)
                 if j != 2 and outside[0, j]]
        if model.labor_types and tipo not in model.labor_types:
            notes.append("tipo_labor not seen in training: read as the reference type")
        if rank_out.any():
            notes.append("support_rank outside the training range for types: "
                         + ", ".join(o.code for o, r in zip(options, rank_out) if r))
        if far.any():
            notes.append("Mahalanobis distance above the training 99th percentile for types: "
                         + ", ".join(o.code for o, f in zip(options, far) if f))
        chosen = reason = None
        if model.calibration != "site":
            reason = f"no choice ({model.calibration}): {model.calibration_reason}"
        elif "support_rank" in model.active_bounds:  # el modelo no distingue tipos: el más liviano sería peligroso
            reason = "support effect not identified (bound active)"
        else:
            chosen = next((o.code for o in options if o.meets_threshold), None)
            reason = None if chosen else "none meets the threshold"
        i_ref = next((i for i, o in enumerate(options) if o.code == chosen), 0)
        contrib = model.fit.coef * (X[i_ref] - model.fit.x_mean)
        top = np.argsort(-np.abs(contrib), kind="stable")[:3]
        reasons = tuple(Reason(model.features[j], float(contrib[j]),
                               "raises" if contrib[j] > 0 else "lowers" if contrib[j] < 0 else "neutral")
                        for j in top)
        out.append(Recommendation(tid, options, chosen, reason, reasons, bool(notes), tuple(notes),
                                  model.calibration, thr, exp, lv, cset))
    return tuple(out)


RECOMMENDATION_COLUMNS = ("id_tramo", "tipo", "orden", "p_falla", "p_falla_inf", "p_falla_sup", "cumple_umbral",
                          "extrapolado", "elegido", "motivo_sin_eleccion", "razones", "alerta_extrapolacion",
                          "conjunto_conforme", "calibracion", "umbral", "exposicion_dias", "nivel",
                          "decision_ingeniero", "motivo")


def save_recommendations(recs, path) -> Path:
    """Escribe .xlsx (hoja `Recomendaciones`) o .csv: un tramo × tipo por fila (un tramo sin opciones, una fila).

    `decision_ingeniero` y `motivo` van vacías: ahí el ingeniero registra lo que decidió y por qué (R10); con el
    desempeño posterior, alimentan el siguiente ajuste.
    """
    rows = []
    for r in recs:
        why = "; ".join(f"{x.variable} {x.effect} ({x.contribution:+.2f})" for x in r.reasons)
        tail = (r.chosen, r.reason, why, "; ".join(r.extrapolation_notes),
                None if r.conformal_set is None else ", ".join(r.conformal_set), r.calibration, r.threshold,
                r.exposure_days, r.level, None, None)
        if not r.options:
            rows.append((r.id_tramo, *[None] * 7, *tail))
        for o in r.options:
            rows.append((r.id_tramo, o.code, o.order, o.p_failure, o.p_low, o.p_high, o.meets_threshold,
                         o.extrapolated, *tail))
    return write_table(path, RECOMMENDATION_COLUMNS, rows, sheet="Recomendaciones")


# ---------- isoprobabilidades ----------

@dataclass(frozen=True)
class IsoprobabilityGrid:
    """Mallas n×n en el plano (log10 Q, log10 De) y P(falla) para un tipo de sostenimiento (Mawdesley et al. 2001)."""

    log10_q: np.ndarray
    log10_de: np.ndarray
    p_failure: np.ndarray
    support_code: str
    exposure_days: float
    tipo_labor: str | None
    depth_m: float | None


def isoprobability_grid(model: PerformanceModel, *, support_code: str, exposure_days, q_range, de_range,
                        n: int = 60, tipo_labor: str | None = None, depth_m: float | None = None) -> IsoprobabilityGrid:
    """P(falla) en una malla log-espaciada de Q × De para `support_code`. Las demás variables quedan fijas:
    `tipo_labor` (por defecto el de referencia, `model.labor_types[0]`) y `depth_m` (por defecto la media del
    entrenamiento). Solo para modelos con `quality="q"`."""
    if model.quality != "q":
        raise ValueError("the isoprobability grid in (Q, De) needs a model fitted with quality='q'")
    if model.fit is None:
        raise ValueError("the model has no fit (no events / no non-events): there is no isoprobability grid")
    ranks = dict(model.support_types)
    if support_code not in ranks:
        raise ValueError(f"support_code must be one of {', '.join(ranks)}")
    exp = _exposure(exposure_days)
    if isinstance(n, bool) or not isinstance(n, (int, np.integer)) or n < 2:
        raise ValueError("n must be an integer >= 2")
    for name, rg in (("q_range", q_range), ("de_range", de_range)):
        if len(rg) != 2 or not 0 < rg[0] < rg[1]:
            raise ValueError(f"{name} must be (low, high) with 0 < low < high")
    if model.use_depth and depth_m is None:
        depth_m = model.maha_mean[4]
    tipo = tipo_labor if tipo_labor is not None else (model.labor_types[0] if model.labor_types else None)
    lq = np.linspace(math.log10(q_range[0]), math.log10(q_range[1]), n)
    ld = np.linspace(math.log10(de_range[0]), math.log10(de_range[1]), n)
    LQ, LD = np.meshgrid(lq, ld)
    X = np.array([_model_row(model, a * math.log(10), b * math.log(10), ranks[support_code], math.log(exp), depth_m,
                             tipo) for a, b in zip(LQ.ravel(), LD.ravel())])
    return IsoprobabilityGrid(LQ, LD, model.fit.predict_proba(X).reshape(LQ.shape), support_code, exp, tipo,
                              None if not model.use_depth else float(depth_m))


# ---------- JSON ----------

def save_model(model: PerformanceModel, path) -> Path:
    """Guarda el modelo en JSON (con `schema_version`). Nunca lleva filas ni ids (R10, R13)."""
    f = model.fit
    d = {k: getattr(model, k) for k in model.__dataclass_fields__ if k not in ("fit", "validation")}
    d["fit"] = None if f is None else {"coef": f.coef.tolist(), "intercept": f.intercept, "cov": f.cov.tolist(),
                "active_bounds": list(f.active_bounds), "converged": f.converged, "n": f.n, "loglik": f.loglik,
                "x_mean": f.x_mean.tolist(), "x_scale": f.x_scale.tolist(), "message": f.message}
    v = model.validation
    d["validation"] = None if v is None else {"results": {k: asdict(c) for k, c in v.results.items()},
                                              "skipped": v.skipped}
    p = Path(path)
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def _tuples(x):
    return tuple(_tuples(i) for i in x) if isinstance(x, list) else x


def load_model(path) -> PerformanceModel:
    """Lee un modelo guardado con `save_model`; la predicción es exactamente la misma."""
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    if d.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported performance model schema_version {d.get('schema_version')!r} "
                         f"(this version reads {SCHEMA_VERSION})")
    f = d.pop("fit")
    fit = None if f is None else LogisticMapFit(
        coef=np.array(f["coef"], dtype=float), intercept=f["intercept"], cov=np.array(f["cov"], dtype=float),
        active_bounds=tuple(f["active_bounds"]), converged=f["converged"], n=f["n"], loglik=f["loglik"],
        x_mean=np.array(f["x_mean"], dtype=float), x_scale=np.array(f["x_scale"], dtype=float), message=f["message"])
    v = d.pop("validation")
    report = None if v is None else ValidationReport(
        results={k: Comparison(**{**c, "improvements": {r: Improvement(**i) for r, i in c["improvements"].items()}})
                 for k, c in v["results"].items()}, skipped=v["skipped"])
    keep = ("metrics", "counts")  # dicts: se quedan como dicts
    return PerformanceModel(fit=fit, validation=report, **{k: (val if k in keep else _tuples(val))
                                                           for k, val in d.items()})
