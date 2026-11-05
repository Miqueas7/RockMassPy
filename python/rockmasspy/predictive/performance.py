"""Nivel 3: modelo de desempeño y recomendación de sostenimiento (Fase 4C, tarea 12; plan R9, R10, R13 y R14).

Modelo de tasa de falla constante (exponencial; MLE de Poisson con offset log t): evento_i ~ Poisson(λ_i·t_i),
log λ = intercepto + X·β, con t_i = días de exposición hasta la primera falla o hasta la última inspección
(censurada). P(falla dentro de H días) = 1 − exp(−λ·H). La exposición entra como offset y no como variable: con una
logística, los tramos fallados (exposición cortada por la falla) empujarían su coeficiente a 0 o al signo contrario.
MAP con prior Cauchy y Laplace (Gelman et al. 2008 [V2], `stats.exponential_hazard_map_fit`) y restricciones de
signo (`MODELOS_SOSTENIMIENTO.md` §3.3, decisión de diseño): peor macizo, más luz y más profundidad no bajan la tasa;
más sostenimiento no la sube. Las filas salen de `history.level3_rows`, la misma selección que cuenta la preparación
del nivel 3.

Validación (R7) con `validate`. Métrica de decisión: la devianza de Poisson por tramo, media de μ − d·log μ con
μ_i = λ_i·t_i (menor es mejor), que es la regla de puntaje propia de este modelo. Decisión de diseño: NO se usa el
Brier de P(falla dentro de la exposición propia), 1 − exp(−λ_i·t_i), porque en un tramo fallado la exposición
termina en la falla (ventana informativa): con ese Brier el ficticio de prevalencia le gana al modelo verdadero.
Por lo mismo, las métricas fuera de pliegue son las de una tasa: devianza, eventos observados/esperados, pendiente
de calibración y C de Harrell. Referencias: el ficticio de tasa constante (la de train) y la línea base de nivel 0,
que es el mismo modelo exponencial con una sola variable, la categoría de la carta Q NGI (`ngi_category`), sin cota
de signo (la referencia más fuerte con esa variable); la exposición entra como offset en las tres. Se reajusta en
cada pliegue.

La recomendación (R10, §4 punto 7) muestra P(falla en H días) con su intervalo para CADA tipo de la mina; elige el
más liviano elegible cuyo límite superior queda bajo el umbral del ingeniero (umbral y H obligatorios), solo si el
modelo está calibrado al sitio, el efecto del sostenimiento está identificado y el tramo no extrapola. La decisión
final queda en las columnas `decision_ingeniero` y `motivo`.

Privacidad (R13): el modelo y su JSON nunca llevan filas ni ids; los mensajes y las razones solo llevan nombres de
variables, códigos de tipo de sostenimiento y conteos. El `id_tramo` va como campo de `Recommendation` y en la
tabla de resultados, nunca dentro de un texto. Los rangos se guardan redondeados hacia afuera a 3 cifras.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from scipy.stats import norm

from .. import __version__
from ..batch import write_table
from ..history import MIN_TRAMOS_PER_TYPE_LEVEL2, History, _readiness, level3_rows
from .stats import ExponentialHazardFit, exponential_hazard_map_fit
from .validation import (Comparison, Improvement, ValidationReport, group_kfold, ngi_category, out_of_fold,
                         tramo_groups, validate)

SCHEMA_VERSION = 2
CALIBRATION_LEVELS = ("site", "partial", "not_calibrated")
QUALITIES = ("q", "rmr")
MAIN, BASELINE, DUMMY = "site", "baseline_ngi", "dummy"
COEF_LEVEL = 0.95  # IC de Laplace de los coeficientes
MAHALANOBIS_PERCENTILE = 99.0
FEW_ROWS_WARNING = 100  # con menos tramos, los resúmenes guardados se acercan a las filas
_ONEHOT = "tipo_labor="
_RANK = 2  # columna del rango del sostenimiento


# ---------- datos del nivel 3 ----------

def _get(t, name):
    """Un campo de un `HistoryTramo`, de cualquier objeto con esos atributos o de un dict."""
    return t.get(name) if isinstance(t, Mapping) else getattr(t, name, None)


def _labor_types(tipos) -> tuple[str, ...]:
    """Tipos de labor para la codificación una-caliente: el primero (orden alfabético) es la referencia."""
    lt = sorted({x for x in tipos if x is not None})
    return tuple(lt) if len(lt) >= 2 else ()


def _feature_names(quality: str, use_depth: bool, labor_types) -> tuple[str, ...]:
    return (("ln_q" if quality == "q" else "rmr", "ln_de", "support_rank") + (("depth_m",) if use_depth else ())
            + tuple(_ONEHOT + x for x in labor_types[1:]))


def _signs(use_depth: bool, labor_types) -> tuple[int, ...]:
    # peor macizo (Q o RMR más bajos), más luz y más profundidad no bajan la tasa; más sostenimiento no la sube;
    # el tipo de labor queda libre
    return (-1, 1, -1) + ((1,) if use_depth else ()) + (0,) * max(0, len(labor_types) - 1)


def _row(quality_value: float, lnde: float, rank: float, depth, tipo, use_depth, labor_types):
    return [quality_value, lnde, rank] + ([depth] if use_depth else []) + [float(tipo == x) for x in labor_types[1:]]


def _round_out(x: float, up: bool) -> float:
    """Redondea hacia afuera a 3 cifras significativas (nunca hacia adentro del rango)."""
    if x == 0 or not math.isfinite(x):
        return float(x)
    q = 10.0 ** (math.floor(math.log10(abs(x))) - 2)
    r = float(f"{(math.ceil if up else math.floor)(x / q) * q:.3g}")
    return max(r, x) if up else min(r, x)


# ---------- el modelo ----------

@dataclass(frozen=True)
class PerformanceModel:
    """Modelo de desempeño del nivel 3. No lleva filas ni ids: solo coeficientes, rangos, métricas y conteos.

    `fit` es la tasa de falla exponencial MAP en la escala ORIGINAL de `features` (ln Q o RMR, ln De, rango del
    tipo, profundidad si está en todas las filas y `tipo_labor=<tipo>` una-caliente contra `labor_types[0]`), con
    λ por día. `coef_ci` = IC 95 % de Laplace de cada coeficiente. `support_counts` = tramos usables de cada tipo
    en el entrenamiento (solo el conteo). `train_min`/`train_max`, `exposure_min`/`exposure_max` (redondeados hacia
    afuera a 3 cifras), `maha_mean`, `maha_inv` (pseudoinversa de la covarianza) y `maha_p99` son el dominio de
    aplicabilidad.
    """

    quality: str
    features: tuple[str, ...]
    labor_types: tuple[str, ...]  # () si hay menos de 2 tipos con datos
    use_depth: bool
    fit: ExponentialHazardFit | None = field(repr=False)  # None: todos los tramos con el mismo resultado
    signs: tuple[int, ...]
    coef_ci: tuple[tuple[float, float], ...]
    active_bounds: tuple[str, ...]  # variables con la cota de signo activa (coeficiente 0)
    support_types: tuple[tuple[str, int], ...]  # (código, orden), del más liviano al más pesado
    support_counts: tuple[int, ...]  # tramos usables por tipo, en el orden de support_types
    calibration: str  # uno de CALIBRATION_LEVELS
    calibration_reason: str
    metrics: dict  # fuera de pliegue (partición por labor): devianza, observados/esperados, pendiente, C
    calibration_curve: tuple[tuple[float, float, int], ...]  # (μ medio, falla observada, n) por decil de μ
    validation: ValidationReport | None = field(repr=False)
    train_min: tuple[float, ...]
    train_max: tuple[float, ...]
    exposure_min: float
    exposure_max: float
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


def _expected_events(p) -> np.ndarray:
    """μ_i = λ_i·t_i desde P_i = 1 − exp(−μ_i) (lo que devuelven los `fit_predict`)."""
    return np.maximum(-np.log1p(-np.minimum(np.asarray(p, dtype=float), 1.0 - 1e-15)), 1e-300)


def poisson_deviance(y, p) -> float:
    """Media de μ − d·log μ (−log verosimilitud de Poisson por tramo, sin constantes): la métrica de decisión del
    nivel 3. Es una regla de puntaje propia para la tasa con exposición; el Brier de P(falla dentro de la exposición
    propia) no lo es, porque en un tramo fallado la exposición termina en la falla (ventana informativa)."""
    mu = _expected_events(p)
    return float(np.mean(mu - np.asarray(y, dtype=float) * np.log(mu)))


def _c_index(d, t, risk) -> float:
    """C de Harrell: pares (i, j) con t_i < t_j y falla en i; concordante si el riesgo de i es mayor (empates 1/2)."""
    i = np.flatnonzero(d == 1)
    if i.size == 0:
        return math.nan
    comparable = t[i, None] < t[None, :]
    diff = risk[i, None] - risk[None, :]
    n = comparable.sum()
    return math.nan if n == 0 else float(((diff > 0) + 0.5 * (diff == 0))[comparable].sum() / n)


def _oof_metrics(y, p, t) -> tuple[dict, tuple]:
    """Métricas fuera de pliegue de la tasa: devianza de Poisson, eventos observados/esperados, pendiente de
    calibración (Poisson de d sobre log μ, ideal 1) y C de Harrell con λ = μ/t. La curva va por deciles de μ:
    (esperados medios, observados medios, n)."""
    mu = _expected_events(p)
    out = {"n": int(y.size), "poisson_deviance": poisson_deviance(y, p),
           "observed_expected": float(y.sum() / mu.sum()), "c_index": _c_index(y, t, mu / t)}
    try:
        f = exponential_hazard_map_fit(np.log(mu)[:, None], y, np.ones_like(mu), prior_scale=1e6,
                                       intercept_scale=1e6)
        out["calibration_slope"] = float(f.coef[0])
    except ValueError:  # una sola clase o μ constante
        out["calibration_slope"] = math.nan
    order = np.argsort(mu, kind="stable")
    curve = tuple((float(mu[g].mean()), float(y[g].mean()), int(g.size)) for g in np.array_split(order, 10)
                  if g.size)
    return out, curve


def _validation_reason(report: ValidationReport) -> str:
    """Los bloqueos de cada partición tal como los da `Comparison.blockers` (o el motivo de `skipped`)."""
    parts = []
    for name in ("labor", "zone"):
        if name in report.results:
            parts += [f"{name}: {b}" for b in report.results[name].blockers]
        else:
            parts.append(f"{name}: {report.skipped.get(name, 'not run')}")
    temporal = report.results.get("temporal")
    if temporal is not None:  # no inferioridad (ValidationReport.recommend)
        parts += [f"temporal: {temporal.main} worse than {r} in the last year"
                  for r, i in temporal.improvements.items() if i.value < 0]
    return "; ".join(parts)


def fit_performance(history: History, *, quality: str = "q", k: int = 5, n_boot: int = 2000,
                    seed: int = 0) -> PerformanceModel:
    """Ajusta el modelo de desempeño del nivel 3 (R9, R10) y lo valida contra el ficticio y la línea base NGI (R7).

    - `quality`: "q" (ln Q, por defecto) o "rmr" (RMR tal como viene; las filas sin RMR quedan fuera, con aviso).
    - Estado: "site" (cumple la preparación del nivel 3 de `audit_history`, `ValidationReport.recommend` es
      verdadero y el ajuste convergió), "partial" (cumple el mínimo pero no lo demás: muestra P(falla), no elige)
      y "not_calibrated" (bajo el mínimo: el ajuste igual se hace, es la curva del prior actualizada con pocos
      datos; sin fallas o sin tramos estables no hay ajuste).
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
    days = np.array([o.exposure_days for o, _ in rows], dtype=float)
    qual = np.array([math.log(t.q_valor) if quality == "q" else t.rmr_valor for t in ts], dtype=float)
    lnde = np.array([math.log(t.luz_m / t.esr) for t in ts])
    rank = np.array([order[t.sost_instalado] for t in ts], dtype=float)
    tipos = [t.tipo_labor for t in ts]
    use_depth = all(t.profundidad_m is not None for t in ts)
    depth = np.array([t.profundidad_m for t in ts], dtype=float) if use_depth else None
    if use_depth and np.ptp(depth) == 0:
        use_depth, depth = False, None
        warns.append("depth_m is the same in every tramo: left out of the model")
    labor_types = _labor_types(tipos)
    for name, col in zip(("quality", "ln_de", "support_rank"), (qual, lnde, rank)):
        if np.ptp(col) == 0:
            raise ValueError(f"level 3: {name} is the same in every usable tramo; its effect cannot be estimated")

    def design(idx, lt):
        return np.array([_row(qual[i], lnde[i], rank[i], None if depth is None else depth[i], tipos[i], use_depth,
                              lt) for i in idx], dtype=float)

    def site_fp(train, test):  # la codificación de tipo_labor se arma con train (R7)
        lt = _labor_types([tipos[i] for i in train])
        f = exponential_hazard_map_fit(design(train, lt), y[train], days[train], signs=_signs(use_depth, lt))
        return f.prob_within(design(test, lt), days[test])

    X0 = np.array([[ngi_category(t)] for t in ts], dtype=float)

    def baseline_fp(train, test):
        return exponential_hazard_map_fit(X0[train], y[train], days[train]).prob_within(X0[test], days[test])

    def dummy_fp(train, test):  # tasa constante de train
        if y[train].sum() == 0:
            raise ValueError("no events in train")
        return -np.expm1(-y[train].sum() / days[train].sum() * days[test])

    labors, zones, years = tramo_groups(ts)
    labors = [g if g is not None else (None, i) for i, g in enumerate(labors)]  # sin labor: su propio grupo
    report = validate(y, {MAIN: site_fp, BASELINE: baseline_fp, DUMMY: dummy_fp}, kind="proba",
                      labors=labors, zones=zones, years=years, metric=poisson_deviance, higher_is_better=False,
                      reference=(DUMMY, BASELINE), k=k, n_boot=n_boot, seed=seed)
    warns += report.warnings
    try:
        oof = out_of_fold(group_kfold(labors, k=k, seed=seed), site_fp, y.size, kind="proba")
    except ValueError:  # una sola labor: no hay partición agrupada
        oof = None
    if oof is not None and oof.covered.any():
        metrics, curve = _oof_metrics(y[oof.covered], oof.pred[oof.covered], days[oof.covered])
    else:
        metrics, curve = {"n": 0}, ()

    X = design(range(y.size), labor_types)
    signs = _signs(use_depth, labor_types)
    names = _feature_names(quality, use_depth, labor_types)
    # sin fallas o sin tramos estables no hay tasa que ajustar (la guarda de stats): sin modelo
    fit = exponential_hazard_map_fit(X, y, days, signs=signs) if 0 < y.sum() < y.size else None
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
    warns += [f"sign bound active for {a}: its coefficient is 0 (the data push it the other way)" for a in active]
    if labor_types and any(x is None for x in tipos):
        warns.append(f"{sum(x is None for x in tipos)} tramo(s) without tipo_labor read as the reference type")
    n_eval = sum(o.start_from_evaluation for o, _ in rows)
    if n_eval:
        warns.append(f"{n_eval} tramo(s) without fecha_instalacion: exposure counted from fecha_evaluacion")
    if y.size < FEW_ROWS_WARNING:
        warns.append(f"fewer than {FEW_ROWS_WARNING} usable tramos: the stored ranges, mean and covariance are "
                     "close to the training rows; share the model file with care")

    ready = next(r for r in _readiness(history) if r.level == 3)
    if fit is None:
        level, reason = "not_calibrated", "not calibrated to the site: no events / no non-events, no model is fitted"
    elif not ready.ready:
        miss = ", ".join(f"{k} short by {v}" for k, v in ready.missing.items() if v)
        level, reason = "not_calibrated", (f"not calibrated to the site: below the level-3 minimum ({miss}); the "
                                           "fit is the prior updated with few data")
    elif not fit.converged:
        level, reason = "partial", "the final fit did not converge"
    elif not report.recommend:
        level, reason = "partial", _validation_reason(report)
    else:
        level, reason = "site", "calibrated to the site: the labor and zone validations recommend"

    cov = np.cov(X, rowvar=False).reshape(X.shape[1], X.shape[1])
    inv = np.linalg.pinv(cov)
    mean = X.mean(axis=0)
    dist = np.sqrt(np.einsum("ij,jk,ik->i", X - mean, inv, X - mean).clip(min=0))
    support = tuple((s.codigo_tipo, s.orden) for s in sorted(history.support_types, key=lambda s: s.orden))
    installed = Counter(t.sost_instalado for t in ts)
    counts = {"tramos": int(y.size), "failures": int(y.sum()), "non_failures": int(y.size - y.sum()),
              "labors": len(set(labors)), "zones": len({x for x in zones if x is not None}),
              "parameters": len(names), "start_from_evaluation": n_eval,
              "minority_class": ready.counts["minority_class"],
              "minority_class_minimum": ready.minimums["minority_class"]}
    return PerformanceModel(
        quality=quality, features=names, labor_types=labor_types, use_depth=use_depth, fit=fit, signs=signs,
        coef_ci=coef_ci, active_bounds=active, support_types=support,
        support_counts=tuple(installed.get(c, 0) for c, _ in support),
        calibration=level, calibration_reason=reason, metrics=metrics, calibration_curve=curve, validation=report,
        train_min=tuple(_round_out(float(v), False) for v in X.min(axis=0)),
        train_max=tuple(_round_out(float(v), True) for v in X.max(axis=0)),
        exposure_min=_round_out(float(days.min()), False), exposure_max=_round_out(float(days.max()), True),
        maha_mean=tuple(map(float, mean)), maha_inv=tuple(tuple(map(float, r)) for r in inv),
        maha_p99=float(np.percentile(dist, MAHALANOBIS_PERCENTILE)), counts=counts, warnings=tuple(warns))


# ---------- recomendación ----------

@dataclass(frozen=True)
class SupportOption:
    code: str
    order: int
    p_failure: float  # P(falla dentro del horizonte)
    p_low: float
    p_high: float
    meets_threshold: bool  # límite superior ≤ umbral
    mahalanobis: float
    extrapolated: bool  # el tramo extrapola, o este tipo (rango fuera del entrenamiento o Mahalanobis > p99)
    history: int  # tramos usables de este tipo en el entrenamiento
    eligible: bool  # con historia suficiente y sin extrapolar este tipo
    note: str | None  # por qué no es elegible: "not enough history" o "extrapolation"


@dataclass(frozen=True)
class Reason:
    variable: str
    contribution: float  # β·(x − media) en la escala log λ
    effect: str  # "raises", "lowers" o "neutral" (sobre P(falla))


@dataclass(frozen=True)
class Recommendation:
    """Recomendación para un tramo. `chosen` es None con `reason` (el motivo, sin valores); las razones son del
    tipo elegido o, si no hay elegido, del más liviano. `notes` = cotas activas del modelo y fallas del nivel 2.
    `conformal_set` sale del nivel 2 si se pasó `practice`."""

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
    notes: tuple[str, ...] = ()


def _number(v) -> bool:
    return (not isinstance(v, bool) and isinstance(v, (int, float, np.integer, np.floating))
            and math.isfinite(v))


def _probability_threshold(threshold) -> float:
    if threshold is None:
        raise ValueError("threshold is required: the engineer sets the acceptable P(failure); there is no default")
    if not _number(threshold) or not 0 < threshold < 1:
        raise ValueError("threshold must be a probability strictly between 0 and 1")
    return float(threshold)


def _exposure(exposure_days) -> float:
    if exposure_days is None:
        raise ValueError("exposure_days is required: the engineer sets the horizon (days); there is no default")
    if not _number(exposure_days) or exposure_days <= 0:
        raise ValueError("exposure_days must be a positive number of days")
    return float(exposure_days)


def _rec_level(level) -> float:
    if not _number(level) or not 0.5 <= level < 1:
        raise ValueError("level must be in [0.5, 1)")
    return float(level)


def _tramo_inputs(model: PerformanceModel, t):
    """(calidad, ln De, profundidad, tipo, faltantes) de un tramo; faltantes = nombres de columnas, sin valores."""
    qcol = "q_valor" if model.quality == "q" else "rmr_valor"
    vals = {c: _get(t, c) for c in (qcol, "luz_m", "esr", "profundidad_m")}
    missing = [c for c in (qcol, "luz_m", "esr")
               if not _number(vals[c]) or (c != "rmr_valor" and vals[c] <= 0)]
    if model.use_depth and (not _number(vals["profundidad_m"]) or vals["profundidad_m"] < 0):
        missing.append("profundidad_m")
    if missing:
        return None, None, None, None, missing
    qual = math.log(vals[qcol]) if model.quality == "q" else float(vals[qcol])
    return qual, math.log(vals["luz_m"] / vals["esr"]), vals["profundidad_m"], _get(t, "tipo_labor"), []


def _model_row(model, qual, lnde, rank, depth, tipo):
    return _row(qual, lnde, rank, depth, tipo, model.use_depth, model.labor_types)


def _block_reason(model: PerformanceModel) -> str | None:
    """Motivo del modelo para no elegir en ningún tramo, o None (R10 y la revisión del nivel 3)."""
    if model.calibration != "site":
        return f"no choice ({model.calibration}): {model.calibration_reason}"
    if "support_rank" in model.active_bounds:
        return "support effect not identified (bound active)"
    if not model.coef_ci[_RANK][1] < 0:  # el IC 95 % de β_rank toca el cero
        return "support effect not identified"
    if model.features[0] in model.active_bounds or "ln_de" in model.active_bounds:
        return "model ignores rock quality/span (bound active)"
    return None


def recommend(model: PerformanceModel, tramos, *, threshold, exposure_days, practice=None,
              level: float = 0.9) -> tuple[Recommendation, ...]:
    """P(falla dentro de `exposure_days`) con su intervalo (`level` en [0.5, 1), 90 % por defecto) de cada tipo de
    la mina para cada tramo (R10). Nunca hace caer el lote: un tramo con datos inválidos sale sin opciones.

    - `threshold` (P(falla) aceptable) y `exposure_days` (horizonte H en días) son OBLIGATORIOS: los fija el
      ingeniero.
    - Se elige el tipo más liviano ELEGIBLE cuyo límite SUPERIOR queda ≤ el umbral. Elegible: con al menos
      `MIN_TRAMOS_PER_TYPE_LEVEL2` tramos en el entrenamiento y sin extrapolar ese tipo (rango del tipo fuera del
      entrenamiento o Mahalanobis sobre el p99). No se elige en ningún tipo si: la calibración no es "site"; el
      efecto del sostenimiento no está identificado (cota activa, o el IC 95 % de β_rank no queda bajo 0); la cota
      está activa en la calidad o en ln De; o el tramo extrapola (Q, De, profundidad o H fuera del rango de
      entrenamiento, o tipo de labor no visto o vacío). Las opciones se muestran igual.
    - `tramos`: `HistoryTramo`, o cualquier objeto (o dict) con `id_tramo`, `q_valor` (o `rmr_valor`), `luz_m`,
      `esr`, `tipo_labor` y `profundidad_m` (si el modelo la usa).
    - `practice`: el nivel 2, opcional. Protocolo: cualquier objeto con `conformal_set(tramo) -> tuple[str, ...]`
      (los códigos del conjunto conforme); recibe el tramo con atributos (un dict se convierte). Si falla, el
      conjunto queda None con una nota.
    """
    thr, exp = _probability_threshold(threshold), _exposure(exposure_days)
    lv = _rec_level(level)
    lo_tr, hi_tr = np.array(model.train_min), np.array(model.train_max)
    mean, inv = np.array(model.maha_mean), np.array(model.maha_inv)
    n_cont = 3 + model.use_depth  # columnas no una-caliente
    block = _block_reason(model) if model.fit is not None else None
    bound_notes = tuple(f"sign bound active for {a}" for a in model.active_bounds)
    out = []
    for t in tramos:
        tid = _get(t, "id_tramo")
        obj = SimpleNamespace(**t) if isinstance(t, Mapping) else t
        notes, cset = list(bound_notes), None
        if practice is not None:
            try:
                cset = tuple(practice.conformal_set(obj))
            except Exception as e:  # el nivel 2 no hace caer el lote; su texto no se copia (R13)
                notes.append(f"practice conformal set failed ({type(e).__name__})")

        def empty(reason):
            return Recommendation(tid, (), None, reason, (), False, (), model.calibration, thr, exp, lv, cset,
                                  tuple(notes))
        if model.fit is None:
            out.append(empty(f"no choice ({model.calibration}): {model.calibration_reason}"))
            continue
        qual, lnde, depth, tipo, missing = _tramo_inputs(model, t)
        if missing:
            out.append(empty(f"missing or invalid input: {', '.join(missing)}"))
            continue
        X = np.array([_model_row(model, qual, lnde, r, depth, tipo) for _, r in model.support_types])
        p, p_lo, p_hi = model.fit.prob_interval(X, exp, lv)
        d = np.sqrt(np.einsum("ij,jk,ik->i", X - mean, inv, X - mean).clip(min=0))
        outside = (X[:, :n_cont] < lo_tr[:n_cont]) | (X[:, :n_cont] > hi_tr[:n_cont])
        rank_out, far = outside[:, _RANK], d > model.maha_p99
        ext_notes = [f"{model.features[j]} outside the training range" for j in range(n_cont)
                     if j != _RANK and outside[0, j]]
        if not model.exposure_min <= exp <= model.exposure_max:
            ext_notes.append("exposure_days outside the training range of exposures")
        if model.labor_types and tipo not in model.labor_types:
            ext_notes.append("tipo_labor missing or not seen in training")
        tramo_ext = bool(ext_notes)
        options = []
        for i, ((c, o), n_hist) in enumerate(zip(model.support_types, model.support_counts)):
            note = ("not enough history" if n_hist < MIN_TRAMOS_PER_TYPE_LEVEL2
                    else "extrapolation" if rank_out[i] or far[i] else None)
            options.append(SupportOption(c, o, float(p[i]), float(p_lo[i]), float(p_hi[i]), bool(p_hi[i] <= thr),
                                         float(d[i]), bool(tramo_ext or rank_out[i] or far[i]), int(n_hist),
                                         note is None, note))
        if rank_out.any():
            ext_notes.append("support_rank outside the training range for types: "
                             + ", ".join(o.code for o, r in zip(options, rank_out) if r))
        if far.any():
            ext_notes.append("Mahalanobis distance above the training 99th percentile for types: "
                             + ", ".join(o.code for o, f in zip(options, far) if f))
        chosen, reason = None, block
        if reason is None and tramo_ext:
            reason = "input outside the training domain (extrapolation)"
        if reason is None:
            chosen = next((o.code for o in options if o.eligible and o.meets_threshold), None)
            reason = None if chosen else "no eligible type meets the threshold"
        i_ref = next((i for i, o in enumerate(options) if o.code == chosen), 0)
        contrib = model.fit.coef * (X[i_ref] - model.fit.x_mean)
        top = np.argsort(-np.abs(contrib), kind="stable")[:3]
        reasons = tuple(Reason(model.features[j], float(contrib[j]),
                               "raises" if contrib[j] > 0 else "lowers" if contrib[j] < 0 else "neutral")
                        for j in top)
        out.append(Recommendation(tid, tuple(options), chosen, reason, reasons, bool(ext_notes), tuple(ext_notes),
                                  model.calibration, thr, exp, lv, cset, tuple(notes)))
    return tuple(out)


RECOMMENDATION_COLUMNS = ("id_tramo", "tipo", "orden", "p_falla", "p_falla_inf", "p_falla_sup", "cumple_umbral",
                          "tramos_historia", "elegible", "nota_tipo", "extrapolado", "elegido",
                          "motivo_sin_eleccion", "razones", "alerta_extrapolacion", "notas", "conjunto_conforme",
                          "calibracion", "umbral", "exposicion_dias", "nivel", "decision_ingeniero", "motivo")


def save_recommendations(recs, path) -> Path:
    """Escribe .xlsx (hoja `Recomendaciones`) o .csv: un tramo × tipo por fila (un tramo sin opciones, una fila).

    `decision_ingeniero` y `motivo` van vacías: ahí el ingeniero registra lo que decidió y por qué (R10); con el
    desempeño posterior, alimentan el siguiente ajuste.
    """
    rows = []
    for r in recs:
        why = "; ".join(f"{x.variable} {x.effect} ({x.contribution:+.2f})" for x in r.reasons)
        tail = (r.chosen, r.reason, why, "; ".join(r.extrapolation_notes), "; ".join(r.notes),
                None if r.conformal_set is None else ", ".join(r.conformal_set), r.calibration, r.threshold,
                r.exposure_days, r.level, None, None)
        if not r.options:
            rows.append((r.id_tramo, *[None] * 10, *tail))
        for o in r.options:
            rows.append((r.id_tramo, o.code, o.order, o.p_failure, o.p_low, o.p_high, o.meets_threshold, o.history,
                         o.eligible, o.note, o.extrapolated, *tail))
    return write_table(path, RECOMMENDATION_COLUMNS, rows, sheet="Recomendaciones")


# ---------- isoprobabilidades ----------

@dataclass(frozen=True)
class IsoprobabilityGrid:
    """Mallas n×n en el plano (log10 Q, log10 De) y P(falla en `exposure_days`) para un tipo de sostenimiento
    (al estilo de Mawdesley et al. 2001)."""

    log10_q: np.ndarray
    log10_de: np.ndarray
    p_failure: np.ndarray
    support_code: str
    exposure_days: float
    tipo_labor: str | None
    depth_m: float | None


def isoprobability_grid(model: PerformanceModel, *, support_code: str, exposure_days, q_range, de_range,
                        n: int = 60, tipo_labor: str | None = None, depth_m: float | None = None) -> IsoprobabilityGrid:
    """P(falla en `exposure_days`) en una malla log-espaciada de Q × De para `support_code`. Las demás variables
    quedan fijas: `tipo_labor` (por defecto el de referencia, `model.labor_types[0]`) y `depth_m` (por defecto la
    media del entrenamiento). Solo para modelos con `quality="q"`."""
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
        depth_m = model.maha_mean[3]
    tipo = tipo_labor if tipo_labor is not None else (model.labor_types[0] if model.labor_types else None)
    lq = np.linspace(math.log10(q_range[0]), math.log10(q_range[1]), n)
    ld = np.linspace(math.log10(de_range[0]), math.log10(de_range[1]), n)
    LQ, LD = np.meshgrid(lq, ld)
    X = np.array([_model_row(model, a * math.log(10), b * math.log(10), ranks[support_code], depth_m, tipo)
                  for a, b in zip(LQ.ravel(), LD.ravel())])
    return IsoprobabilityGrid(LQ, LD, model.fit.prob_within(X, exp).reshape(LQ.shape), support_code, exp, tipo,
                              None if not model.use_depth else float(depth_m))


# ---------- JSON ----------

_FIT_KEYS = ("coef", "intercept", "cov", "active_bounds", "converged", "n", "loglik", "x_mean", "x_scale", "message",
             "signs", "n_events")


def save_model(model: PerformanceModel, path) -> Path:
    """Guarda el modelo en JSON (con `schema_version`). Nunca lleva filas ni ids (R10, R13)."""
    f = model.fit
    d = {k: getattr(model, k) for k in model.__dataclass_fields__ if k not in ("fit", "validation")}
    d["fit"] = None if f is None else {
        k: (v.tolist() if isinstance(v, np.ndarray) else list(v) if isinstance(v, tuple) else v)
        for k, v in ((k, getattr(f, k)) for k in _FIT_KEYS)}
    v = model.validation
    d["validation"] = None if v is None else {"results": {k: asdict(c) for k, c in v.results.items()},
                                              "skipped": v.skipped}
    p = Path(path)
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def _tuples(x):
    return tuple(_tuples(i) for i in x) if isinstance(x, list) else x


def _check_keys(what: str, got, expected) -> None:
    extra, missing = sorted(set(got) - set(expected)), sorted(set(expected) - set(got))
    if extra or missing:
        raise ValueError(f"{what}: unexpected keys {extra}, missing keys {missing}")


def _check_model(m: PerformanceModel) -> None:
    """Coherencia de un modelo leído (C): estado válido, tipos en orden y largos iguales."""
    if m.calibration not in CALIBRATION_LEVELS:
        raise ValueError(f"calibration must be one of {', '.join(CALIBRATION_LEVELS)}")
    orders = [o for _, o in m.support_types]
    if not orders or any(b <= a for a, b in zip(orders, orders[1:])):
        raise ValueError("support_types must be in strictly increasing order")
    if len(m.support_counts) != len(m.support_types):
        raise ValueError("support_counts must have one count per support type")
    p = len(m.features)
    lengths = {"signs": len(m.signs), "train_min": len(m.train_min), "train_max": len(m.train_max),
               "maha_mean": len(m.maha_mean), "maha_inv": len(m.maha_inv)}
    if m.fit is not None:
        lengths.update({"coef_ci": len(m.coef_ci), "fit.coef": m.fit.coef.size, "fit.signs": len(m.fit.signs),
                        "fit.x_mean": m.fit.x_mean.size, "fit.x_scale": m.fit.x_scale.size})
        if m.fit.cov.shape != (p + 1, p + 1):
            raise ValueError(f"fit.cov must be {p + 1}x{p + 1}")
    bad = sorted(k for k, n in lengths.items() if n != p) + (["maha_inv"] if any(len(r) != p for r in m.maha_inv)
                                                              else [])
    if bad:
        raise ValueError(f"lengths do not match the {p} features: {', '.join(sorted(set(bad)))}")


def load_model(path) -> PerformanceModel:
    """Lee un modelo guardado con `save_model`; la predicción es exactamente la misma. Valida el esquema: claves
    exactas, estado, orden de los tipos y largos coherentes (ValueError si algo no cuadra)."""
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(d, dict) or d.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported performance model schema_version {d.get('schema_version')!r} "
                         f"(this version reads {SCHEMA_VERSION})" if isinstance(d, dict)
                         else "the performance model file must hold a JSON object")
    _check_keys("performance model", d, PerformanceModel.__dataclass_fields__)
    f = d.pop("fit")
    if f is not None:
        _check_keys("fit", f, _FIT_KEYS)
    fit = None if f is None else ExponentialHazardFit(
        coef=np.array(f["coef"], dtype=float), intercept=f["intercept"], cov=np.array(f["cov"], dtype=float),
        active_bounds=tuple(f["active_bounds"]), converged=f["converged"], n=f["n"], loglik=f["loglik"],
        x_mean=np.array(f["x_mean"], dtype=float), x_scale=np.array(f["x_scale"], dtype=float), message=f["message"],
        signs=tuple(f["signs"]), n_events=f["n_events"])
    v = d.pop("validation")
    report = None if v is None else ValidationReport(
        results={k: Comparison(**{**c, "improvements": {r: Improvement(**i) for r, i in c["improvements"].items()}})
                 for k, c in v["results"].items()}, skipped=v["skipped"])
    keep = ("metrics", "counts")  # dicts: se quedan como dicts
    m = PerformanceModel(fit=fit, validation=report, **{k: (val if k in keep else _tuples(val)) for k, val in d.items()})
    _check_model(m)
    return m
