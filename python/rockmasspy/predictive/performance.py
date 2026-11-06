"""Nivel 3: modelo de desempeño y recomendación de sostenimiento (Fase 4C, tarea 12; plan R9, R10, R13 y R14).

Modelo de tasa de falla constante con fragilidad gamma compartida por labor: evento_i ~ Poisson(λ_i·Z_g·t_i),
log λ = intercepto + X·β, Z_g ~ Gamma(media 1, varianza θ), con t_i = días de exposición hasta la primera falla o
hasta la última inspección (censurada). La exposición entra como offset y no como variable: con una logística, los
tramos fallados (exposición cortada por la falla) empujarían su coeficiente a 0 o al signo contrario. La fragilidad
recoge la heterogeneidad entre labores (las labores de una mina no son copias), que sin ella deja los intervalos
demasiado angostos. MAP de β y log θ sobre la verosimilitud marginal cerrada (`stats.frailty_hazard_map_fit`): prior
Cauchy en β (Gelman et al. 2008 [V2]), normal(0, 2) en log θ y restricciones de signo (`MODELOS_SOSTENIMIENTO.md`
§3.3, decisión de diseño): peor macizo, más luz y más profundidad no bajan la tasa; más sostenimiento no la sube. La
covarianza es la sándwich agrupada por zona (los tramos de una zona comparten efecto), con t de Student; con menos de
5 zonas, la de Laplace con aviso. Las filas salen de `history.level3_rows`.

Validación (R7) con `validate`. Métrica de decisión: la devianza de Poisson por tramo, media de μ − d·log μ con
μ_i = λ_i·t_i, la media marginal de eventos (menor es mejor), que es la regla de puntaje propia de una tasa con
exposición. Decisión de diseño: NO se usa el Brier de P(falla dentro de la exposición propia), porque en un tramo
fallado la exposición termina en la falla (ventana informativa): con ese Brier el ficticio de prevalencia le gana al
modelo verdadero. Por lo mismo, las métricas fuera de pliegue son las de una tasa: devianza, eventos
observados/esperados, pendiente de calibración y C de Harrell. Referencias: el ficticio de tasa constante (la de
train) y la línea base de nivel 0, el modelo exponencial con una sola variable, la categoría de la carta Q NGI
(`ngi_category`), sin cota de signo; la exposición entra como offset en las tres. Se reajusta en cada pliegue.

La recomendación (R10, §4 punto 7) es para una labor NUEVA: muestra P(falla en H días) para CADA tipo de la mina
(central = la media marginal 1 − (1 + θλH)^(−1/θ)); elige el más liviano elegible cuyo límite superior
1 − exp(−λ_sup·H·Z_q) queda bajo el umbral del ingeniero (umbral y H obligatorios), con λ_sup la cota de η al nivel y
Z_q el cuantil `level` de la fragilidad evaluado con la cota superior de θ, exp(log θ̂ + z·sd(log θ)): conservador
por diseño (con pocas labores θ̂ puede salir bajo). Solo elige si el modelo está calibrado al sitio,
el efecto del sostenimiento está identificado y el tramo no extrapola. La decisión final queda en las columnas
`decision_ingeniero` y `motivo`.

Fase 5B (banco de la mina sintética, `docs/investigacion/BANCO_MINA_SINTETICA.md`):
- Forma del modelo: además de la aditiva, la interacción calidad × rango, con la columna
  (calidad − calidad_máx)·(rango − rango_máx) y cota de signo ≥ 0: el sostenimiento ayuda más en peor roca y, con
  β_q ≤ 0 y β_rank ≤ 0, la tasa sigue siendo monótona en la calidad y en el rango dentro del dominio. Entra solo si
  la clase menor alcanza 10 eventos por parámetro CONTANDO el de la interacción y si baja la devianza de Poisson
  fuera de pliegue (partición por labor, los mismos pliegues) frente a la aditiva; si no, queda la aditiva. El
  déficit frente a la carta NGI se probó en el banco y no ayudó; además la librería no tiene la equivalencia entre
  los tipos de la mina y las categorías de la carta.
- Zona nueva: el modelo no tiene efecto de zona en la media, así que la cota superior suma en cuadratura la
  varianza entre zonas, σ_z² = C·Var(η en la media) con la covarianza agrupada por zona (C zonas). Es una cota por
  exceso (incluye el ruido propio de cada zona), decisión de diseño: en el banco recupera σ_z con 8 zonas.
- Compuertas de `recommend`: (a) observados/esperados fuera de pliegue en el tercio peor de la calidad; si pasa de
  `POOR_ROCK_MAX_OE` o hay menos de `POOR_ROCK_MIN_EVENTS` fallas para verlo, no elige en ese estrato; (b) soporte:
  un tipo no es elegible en una clase de Q (Barton et al. 1974; RMR de Bieniawski 1989 con quality="rmr") donde el
  entrenamiento tiene menos de `MIN_TRAMOS_PER_CLASS` tramos de ese tipo; (c) «ningún tipo cumple» explícito.

Privacidad (R13): el modelo y su JSON nunca llevan filas ni ids; los mensajes y las razones solo llevan nombres de
variables, códigos de tipo de sostenimiento y conteos. El `id_tramo` va como campo de `Recommendation` y en la
tabla de resultados, nunca dentro de un texto. Los rangos se guardan redondeados hacia afuera a 3 cifras y un modelo
de menos de 100 tramos no se guarda (sus resúmenes casi reconstruyen las filas).
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
from scipy.stats import t as student_t

from .. import __version__
from ..batch import write_table
from ..history import (MIN_EVENTS_PER_PARAMETER_LEVEL3, MIN_TRAMOS_PER_TYPE_LEVEL2, MIN_ZONES_LEVEL3, History,
                       LevelReadiness, labor_key, level3_parameters, level3_rows)
from .stats import FrailtyHazardFit, _eta_interval, exponential_hazard_map_fit, frailty_hazard_map_fit
from .validation import (Comparison, Improvement, ValidationReport, _tramo_number, group_kfold, ngi_category,
                         out_of_fold, tramo_groups, validate)

SCHEMA_VERSION = 4
CALIBRATION_LEVELS = ("site", "partial", "not_calibrated")
QUALITIES = ("q", "rmr")
MAIN, BASELINE, DUMMY = "site", "baseline_ngi", "dummy"
COEF_LEVEL = 0.95  # IC de los coeficientes (covarianza agrupada por zona)
MAHALANOBIS_PERCENTILE = 99.0
FEW_ROWS = 100  # con menos tramos, los resúmenes guardados casi reconstruyen las filas: no se guarda el modelo
MIN_CLUSTERS = 5  # zonas mínimas para la covarianza agrupada; con menos, Laplace con aviso
MISSING_LABOR_TYPE = "(missing)"  # tipo_labor vacío en el entrenamiento: un nivel propio, como en el nivel 2
NO_LABOR, NO_ZONE = "(no labor)", "(no zone)"
_ONEHOT = "tipo_labor="
_RANK = 2  # columna del rango del sostenimiento (posición 0..K−1 en el orden de `orden`)
_INT = 3  # columna de la interacción calidad × rango, si el modelo la tiene
FORMS = ("additive", "interaction")
CANDIDATE_FORMS = FORMS  # las que se prueban; el banco puede restringirlo dentro de su proceso
# compuerta (a): calibración en el tercio peor de la calidad (decisión de diseño, valores por confirmar)
POOR_ROCK_FRACTION = 1 / 3
POOR_ROCK_MAX_OE = 1.2
POOR_ROCK_MIN_EVENTS = 10
# compuerta (b): soporte por clase de calidad. Clases de Q de Barton et al. 1974 (NGI) y de RMR de Bieniawski 1989.
# «Casi no» = menos de 10 tramos de ese tipo en esa clase (decisión de diseño, valor por confirmar)
Q_CLASS_EDGES = (0.01, 0.1, 1.0, 4.0, 10.0, 40.0, 100.0, 400.0)
RMR_CLASS_EDGES = (21.0, 41.0, 61.0, 81.0)
MIN_TRAMOS_PER_CLASS = 10


# ---------- datos del nivel 3 ----------

def _get(t, name):
    """Un campo de un `HistoryTramo`, de cualquier objeto con esos atributos o de un dict."""
    return t.get(name) if isinstance(t, Mapping) else getattr(t, name, None)


def _labor_types(tipos) -> tuple[str, ...]:
    """Niveles de tipo_labor para la una-caliente (alfabéticos, «(missing)» al final); el primero es la referencia.
    Vacío con menos de 2 niveles."""
    lv = sorted({MISSING_LABOR_TYPE if x is None else x for x in tipos}, key=lambda x: (x == MISSING_LABOR_TYPE, x))
    return tuple(lv) if len(lv) >= 2 else ()


def _feature_names(quality: str, use_depth: bool, labor_types, form: str = "additive") -> tuple[str, ...]:
    q = "ln_q" if quality == "q" else "rmr"
    return ((q, "ln_de", "support_rank") + ((f"{q}:support_rank",) if form == "interaction" else ())
            + (("depth_m",) if use_depth else ()) + tuple(_ONEHOT + x for x in labor_types[1:]))


def _signs(use_depth: bool, labor_types, form: str = "additive") -> tuple[int, ...]:
    # peor macizo (Q o RMR más bajos), más luz y más profundidad no bajan la tasa; más sostenimiento no la sube;
    # la interacción (calidad − máx)·(rango − máx) ≥ 0: el sostenimiento ayuda más en peor roca; el tipo de labor
    # queda libre
    return ((-1, 1, -1) + ((1,) if form == "interaction" else ()) + ((1,) if use_depth else ())
            + (0,) * max(0, len(labor_types) - 1))


def _row(quality_value: float, lnde: float, rank: float, depth, tipo, use_depth, labor_types, ref=None):
    """Fila del diseño. `ref` = (calidad máx, rango máx) del entrenamiento si el modelo lleva la interacción: su
    columna (calidad − máx)·(rango − máx) es ≥ 0 dentro del dominio."""
    tipo = MISSING_LABOR_TYPE if tipo is None else tipo
    inter = [] if ref is None else [(quality_value - ref[0]) * (rank - ref[1])]
    return ([quality_value, lnde, rank] + inter + ([depth] if use_depth else [])
            + [float(tipo == x) for x in labor_types[1:]])


def _quality_class(quality: str, value: float) -> int:
    """Clase de calidad del tramo (0 = la peor): Q de Barton et al. 1974 o RMR de Bieniawski 1989."""
    if quality == "q":
        return int(np.searchsorted(Q_CLASS_EDGES, math.exp(value), side="right"))
    return int(np.searchsorted(RMR_CLASS_EDGES, value, side="right"))


def _n_classes(quality: str) -> int:
    return len(Q_CLASS_EDGES if quality == "q" else RMR_CLASS_EDGES) + 1


def _round_out(x: float, up: bool) -> float:
    """Redondea hacia afuera a 3 cifras significativas (nunca hacia adentro del rango)."""
    if x == 0 or not math.isfinite(x):
        return float(x)
    q = 10.0 ** (math.floor(math.log10(abs(x))) - 2)
    r = float(f"{(math.ceil if up else math.floor)(x / q) * q:.3g}")
    return max(r, x) if up else min(r, x)


def _calibration(fit: FrailtyHazardFit | None, ready: bool, validation_recommend: bool) -> str:
    """El estado de calibración: una sola regla para el ajuste y para la carga del JSON (I3)."""
    if fit is None or not ready:
        return "not_calibrated"
    return "site" if fit.converged and validation_recommend else "partial"


# ---------- el modelo ----------

@dataclass(frozen=True)
class PerformanceModel:
    """Modelo de desempeño del nivel 3. No lleva filas ni ids: solo coeficientes, rangos, métricas y conteos.

    `fit` es la tasa de falla con fragilidad gamma por labor, en la escala ORIGINAL de `features` (ln Q o RMR,
    ln De, rango del tipo = su posición 0..K−1 en el orden de `orden`, profundidad si está en todas las filas y
    `tipo_labor=<nivel>` una-caliente contra `labor_types[0]`), con λ por día y `fit.theta` la varianza de la
    fragilidad. `coef_ci` = IC 95 % de cada coeficiente con la covarianza agrupada por zona (t con C − 1 grados de
    libertad) o la de Laplace con menos de 5 zonas. `support_counts` = tramos usables de cada tipo en el
    entrenamiento (solo el conteo). `train_min`/`train_max`, `exposure_min`/`exposure_max` (redondeados hacia
    afuera a 3 cifras), `maha_mean`, `maha_inv` (pseudoinversa de la covarianza) y `maha_p99` son el dominio de
    aplicabilidad.

    Fase 5B: `zone_sd` = DE entre zonas que suma la cota superior de una zona nueva; `poor_rock` = (corte de la
    calidad del tercio peor, fallas observadas, esperadas) fuera de pliegue, o None si no hubo predicciones fuera
    de pliegue; `class_counts[c][k]` = tramos del tipo k en la clase de calidad c (`_quality_class`).
    """

    quality: str
    features: tuple[str, ...]
    labor_types: tuple[str, ...]  # () si hay menos de 2 niveles con datos
    use_depth: bool
    fit: FrailtyHazardFit | None = field(repr=False)  # None: todos los tramos con el mismo resultado
    signs: tuple[int, ...]
    coef_ci: tuple[tuple[float, float], ...]
    active_bounds: tuple[str, ...]  # variables con la cota de signo activa (coeficiente 0)
    support_types: tuple[tuple[str, int], ...]  # (código, orden), del más liviano al más pesado
    support_counts: tuple[int, ...]  # tramos usables por tipo, en el orden de support_types
    calibration: str  # uno de CALIBRATION_LEVELS
    calibration_reason: str
    metrics: dict  # fuera de pliegue (partición por labor): devianza, observados/esperados, pendiente, C
    calibration_curve: tuple[tuple[float, float, int], ...]  # (μ medio, falla observada, n) por decil de λ
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
    zone_sd: float
    poor_rock: tuple[float, int, float] | None
    class_counts: tuple[tuple[int, ...], ...]
    version: str = __version__
    schema_version: int = SCHEMA_VERSION

    @property
    def coefficients(self) -> dict[str, float]:
        return {} if self.fit is None else dict(zip(self.features, map(float, self.fit.coef)))

    @property
    def form(self) -> str:
        return "interaction" if len(self.features) > _INT and self.features[_INT].endswith(":support_rank")             else "additive"

    @property
    def interaction_ref(self) -> tuple[float, float] | None:
        """(calidad máx, rango máx) de la columna de interacción, o None en la forma aditiva."""
        return (self.train_max[0], len(self.support_types) - 1.0) if self.form == "interaction" else None

    def _support_effect_upper(self) -> float:
        """Límite superior del IC 95 % del efecto de un tipo más en log λ: β_rank en la forma aditiva; con la
        interacción, β_rank + β_int·(calidad media − máx), con su covarianza."""
        if self.form == "additive":
            return self.coef_ci[_RANK][1]
        d = self.maha_mean[0] - self.train_max[0]
        c = np.zeros(self.fit.cov.shape[0])
        c[_RANK], c[_INT] = 1.0, d
        z = norm.ppf(0.5 + COEF_LEVEL / 2) if self.fit.df is None else float(
            student_t.ppf(0.5 + COEF_LEVEL / 2, self.fit.df))
        return float(c[:-1] @ self.fit.coef + z * math.sqrt(max(c @ self.fit.cov @ c, 0.0)))

    @property
    def poor_rock_cut(self) -> float:
        """Corte de la calidad del tercio peor (∞ sin predicciones fuera de pliegue: la compuerta cubre todo)."""
        return math.inf if self.poor_rock is None else self.poor_rock[0]

    @property
    def poor_rock_problem(self) -> str | None:
        """Compuerta (a): por qué no se elige en el tercio peor de la calidad (None: la calibración pasa)."""
        if self.poor_rock is None:
            return "calibration in the worst third of rock quality not checked (no out-of-fold predictions)"
        _, obs, exp = self.poor_rock
        if obs < POOR_ROCK_MIN_EVENTS:
            return f"too few failures ({obs}) in the worst third of rock quality to check its calibration"
        if obs > POOR_ROCK_MAX_OE * exp:
            return (f"out-of-fold observed/expected failures above {POOR_ROCK_MAX_OE:g} in the worst third of rock "
                    "quality")
        return None

    @property
    def recommendation_blockers(self) -> tuple[str, ...]:
        """Motivos globales por los que `recommend` nunca elige un tipo con este modelo (vacío: puede elegir).
        Se derivan de los campos guardados, así que no pueden quedar desfasados del modelo."""
        out = []
        if self.calibration != "site":
            out.append(f"no choice ({self.calibration}): {self.calibration_reason}")
        if self.fit is not None:
            if "support_rank" in self.active_bounds and (self.form == "additive"
                                                           or self.features[_INT] in self.active_bounds):
                out.append("support effect not identified (bound active)")
            elif not self._support_effect_upper() < 0:  # el IC 95 % del efecto del sostenimiento toca el cero
                out.append("support effect not identified")
            quality_off = self.features[0] in self.active_bounds and (self.form == "additive"
                                                                       or self.features[_INT] in self.active_bounds)
            if quality_off or "ln_de" in self.active_bounds:
                out.append("model ignores rock quality/span (bound active)")
        return tuple(out)


def _expected_events(p) -> np.ndarray:
    """μ_i = λ_i·t_i desde P_i = 1 − exp(−μ_i) (lo que devuelven los `fit_predict`)."""
    return np.maximum(-np.log1p(-np.minimum(np.asarray(p, dtype=float), 1.0 - 1e-15)), 1e-300)


def poisson_deviance(y, p) -> float:
    """Media de μ − d·log μ (−log verosimilitud de Poisson por tramo, sin constantes): la métrica de decisión del
    nivel 3, con μ = −log(1 − p). Es una regla de puntaje propia para la tasa con exposición; el Brier de P(falla
    dentro de la exposición propia) no lo es, porque en un tramo fallado la exposición termina en la falla."""
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
    calibración (Poisson de d sobre log λ con offset log t, ideal 1) y C de Harrell con λ = μ/t. La curva va por
    deciles de λ (no de μ: μ depende de t, que en un fallado termina en la falla): (esperados medios, observados
    medios, n)."""
    mu = _expected_events(p)
    lam = mu / t
    out = {"n": int(y.size), "poisson_deviance": poisson_deviance(y, p),
           "observed_expected": float(y.sum() / mu.sum()), "c_index": _c_index(y, t, lam)}
    try:
        f = exponential_hazard_map_fit(np.log(lam)[:, None], y, t, prior_scale=1e6, intercept_scale=1e6)
        out["calibration_slope"] = float(f.coef[0])
    except ValueError:  # una sola clase o λ constante
        out["calibration_slope"] = math.nan
    order = np.argsort(lam, kind="stable")
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
    if temporal is not None and not temporal.noninferior:  # no inferioridad (ValidationReport.recommend)
        parts += [f"temporal: {temporal.main} worse than {r} in the last year"
                  for r, i in temporal.improvements.items() if i.value < 0]
    return "; ".join(parts)


def _readiness(rows, extra_parameters: int = 0) -> LevelReadiness:
    """Preparación del nivel 3 sobre las filas que de verdad usa el ajuste (I2), con los mínimos de history; la
    interacción suma un parámetro (`extra_parameters`) al mínimo de eventos."""
    failures = sum(o.failed for o, _ in rows)
    return LevelReadiness(3, "performance", {"minority_class": min(failures, len(rows) - failures),
                                             "zones": len({t.zona_nivel for _, t in rows} - {None})},
                          {"minority_class": MIN_EVENTS_PER_PARAMETER_LEVEL3 * (level3_parameters(rows)
                                                                                 + extra_parameters),
                           "zones": MIN_ZONES_LEVEL3})


def _coef_ci(fit: FrailtyHazardFit) -> tuple[tuple[float, float], ...]:
    z = norm.ppf(0.5 + COEF_LEVEL / 2) if fit.df is None else float(student_t.ppf(0.5 + COEF_LEVEL / 2, fit.df))
    sd = np.sqrt(np.diag(fit.cov)[:-1])
    return tuple((float(c - z * s), float(c + z * s)) for c, s in zip(fit.coef, sd))


def fit_performance(history: History, *, quality: str = "q", k: int = 5, n_boot: int = 2000,
                    seed: int = 0) -> PerformanceModel:
    """Ajusta el modelo de desempeño del nivel 3 (R9, R10) y lo valida contra el ficticio y la línea base NGI (R7).

    - `quality`: "q" (ln Q, por defecto) o "rmr" (RMR tal como viene; las filas sin RMR quedan fuera, con aviso).
    - Estado: "site" (cumple la preparación del nivel 3 sobre las filas del ajuste, `ValidationReport.recommend`
      es verdadero y el ajuste convergió), "partial" (cumple el mínimo pero no lo demás: muestra P(falla), no
      elige) y "not_calibrated" (bajo el mínimo: el ajuste igual se hace, es la curva del prior actualizada con
      pocos datos; sin fallas o sin tramos estables no hay ajuste).
    """
    if quality not in QUALITIES:
        raise ValueError(f"quality must be one of {', '.join(QUALITIES)}")
    rows = level3_rows(history)
    warns = []
    if quality == "rmr":
        kept = tuple(r for r in rows if _tramo_number(r[1], "rmr_valor", allow_zero=True) is not None)
        if len(kept) < len(rows):
            warns.append(f"{len(rows) - len(kept)} tramo(s) without rmr_valor left out")
        rows = kept
    if len(rows) < 2:
        raise ValueError(f"level 3 needs at least 2 usable tramos (inspected, with Q, span, ESR, installed support "
                         f"and exposure), got {len(rows)}")
    support = tuple((s.codigo_tipo, s.orden) for s in sorted(history.support_types, key=lambda s: s.orden))
    position = {c: i for i, (c, _) in enumerate(support)}  # I1: la posición, no el valor de `orden`
    ts = [t for _, t in rows]
    y = np.array([o.failed for o, _ in rows], dtype=float)
    days = np.array([o.exposure_days for o, _ in rows], dtype=float)
    qual = np.array([math.log(t.q_valor) if quality == "q" else t.rmr_valor for t in ts], dtype=float)
    lnde = np.array([math.log(t.luz_m / t.esr) for t in ts])
    rank = np.array([position[t.sost_instalado] for t in ts], dtype=float)
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
    labors, zones, years = tramo_groups(ts)
    frail = [NO_LABOR if g is None else g for g in labors]  # sin labor: un solo grupo, como en el nivel 2
    clusters = [NO_ZONE if z is None else z for z in zones]
    labors = [g if g is not None else (None, i) for i, g in enumerate(labors)]  # validación: su propio grupo

    k_max = len(support) - 1.0

    def ref_of(idx, form):  # la referencia de la interacción sale de train (R7), redondeada hacia afuera
        return (_round_out(float(qual[list(idx)].max()), True), k_max) if form == "interaction" else None

    def design(idx, lt, ref=None):
        return np.array([_row(qual[i], lnde[i], rank[i], None if depth is None else depth[i], tipos[i], use_depth,
                              lt, ref) for i in idx], dtype=float)

    def site_fp_of(form):
        def site_fp(train, test):  # la codificación de tipo_labor y la referencia se arman con train (R7)
            lt, ref = _labor_types([tipos[i] for i in train]), ref_of(train, form)
            f = frailty_hazard_map_fit(design(train, lt, ref), y[train], days[train], [frail[i] for i in train],
                                       clusters=[clusters[i] for i in train], signs=_signs(use_depth, lt, form))
            return f.prob_within(design(test, lt, ref), days[test])  # μ = λ·t, la media marginal de eventos
        return site_fp

    # la forma: la interacción entra solo con eventos para su parámetro y si baja la devianza fuera de pliegue
    try:
        folds = group_kfold(labors, k=k, seed=seed)
    except ValueError:  # una sola labor: no hay partición agrupada
        folds = None
    minority = min(int(y.sum()), int(y.size - y.sum()))
    oofs = {}
    for f_name in CANDIDATE_FORMS:
        if f_name == "interaction" and minority < MIN_EVENTS_PER_PARAMETER_LEVEL3 * (level3_parameters(rows) + 1):
            continue
        oofs[f_name] = None if folds is None else out_of_fold(folds, site_fp_of(f_name), y.size, kind="proba")
    form, form_metrics = CANDIDATE_FORMS[0], {}
    if len(oofs) > 1 and all(o is not None for o in oofs.values()):
        common = np.logical_and.reduce([o.covered for o in oofs.values()])
        if common.any():
            dev = {f_name: poisson_deviance(y[common], o.pred[common]) for f_name, o in oofs.items()}
            form_metrics = {f"oof_deviance_{f_name}": v for f_name, v in dev.items()}
            form = min(dev, key=lambda f_name: (dev[f_name], CANDIDATE_FORMS.index(f_name)))  # empate: la primera
    site_fp = site_fp_of(form)

    X0 = np.array([[ngi_category(t)] for t in ts], dtype=float)

    def baseline_fp(train, test):
        return exponential_hazard_map_fit(X0[train], y[train], days[train]).prob_within(X0[test], days[test])

    def dummy_fp(train, test):  # tasa constante de train
        if y[train].sum() == 0:
            raise ValueError("no events in train")
        return -np.expm1(-y[train].sum() / days[train].sum() * days[test])

    report = validate(y, {MAIN: site_fp, BASELINE: baseline_fp, DUMMY: dummy_fp}, kind="proba",
                      labors=labors, zones=zones, years=years, metric=poisson_deviance, higher_is_better=False,
                      reference=(DUMMY, BASELINE), k=k, n_boot=n_boot, seed=seed)
    warns += report.warnings
    oof = oofs.get(form)
    poor = None
    if oof is not None and oof.covered.any():
        metrics, curve = _oof_metrics(y[oof.covered], oof.pred[oof.covered], days[oof.covered])
        # compuerta (a): observados/esperados fuera de pliegue en el tercio peor de la calidad
        cut = _round_out(float(np.quantile(qual, POOR_ROCK_FRACTION)), True)
        sel = oof.covered & (qual <= cut)
        poor = (cut, int(y[sel].sum()), float(_expected_events(oof.pred[sel]).sum()) if sel.any() else 0.0)
    else:
        metrics, curve = {"n": 0}, ()
    metrics |= form_metrics

    ref_full = ref_of(range(y.size), form)
    X = design(range(y.size), labor_types, ref_full)
    signs = _signs(use_depth, labor_types, form)
    names = _feature_names(quality, use_depth, labor_types, form)
    # sin fallas o sin tramos estables no hay tasa que ajustar (la guarda de stats): sin modelo
    fit = (frailty_hazard_map_fit(X, y, days, frail, clusters=clusters, signs=signs, min_clusters=MIN_CLUSTERS)
           if 0 < y.sum() < y.size else None)
    coef_ci, active = (), ()
    if fit is None:
        warns.append("no events / no non-events: every usable tramo has the same outcome; no model is fitted")
    else:
        coef_ci = _coef_ci(fit)
        active = tuple(names[j] for j in fit.active_bounds)
        if not fit.converged:
            warns.append(f"the final fit did not converge: {fit.message}")
        if fit.cov_kind != "cluster":
            warns.append(f"fewer than {MIN_CLUSTERS} zones: Laplace covariance (it ignores the correlation within "
                         "a zone, so the intervals may be too narrow)")
    warns += [f"sign bound active for {a}: its coefficient is 0 (the data push it the other way)" for a in active]
    n_missing = sum(x is None for x in tipos)
    if labor_types and n_missing:
        warns.append(f"{n_missing} tramo(s) without tipo_labor: own level {MISSING_LABOR_TYPE}")
    n_eval = sum(o.start_from_evaluation for o, _ in rows)
    if n_eval:
        warns.append(f"{n_eval} tramo(s) without fecha_instalacion: exposure counted from fecha_evaluacion")
    if y.size < FEW_ROWS:
        warns.append(f"fewer than {FEW_ROWS} usable tramos: the stored ranges, mean and covariance are close to the "
                     "training rows, so the model cannot be saved")

    if poor is not None and (poor[1] < POOR_ROCK_MIN_EVENTS or poor[1] > POOR_ROCK_MAX_OE * poor[2]):
        warns.append("the calibration gate fails in the worst third of rock quality: no choice there")
    zone_sd = 0.0
    if fit is not None and fit.n_clusters >= 2:
        # σ_z² = C·Var(η en la media del diseño): cota por exceso de la varianza entre zonas (decisión de diseño)
        c = np.append(fit.x_mean, 1.0)
        v = float(c @ fit.cov @ c)
        zone_sd = math.sqrt(fit.n_clusters * v) if math.isfinite(v) and v > 0 else 0.0
    n_cls = _n_classes(quality)
    cls = Counter((_quality_class(quality, qual[i]), int(rank[i])) for i in range(y.size))
    class_counts = tuple(tuple(cls.get((c, j), 0) for j in range(len(support))) for c in range(n_cls))

    ready = _readiness(rows, extra_parameters=int(form == "interaction"))
    level = _calibration(fit, ready.ready, report.recommend)
    if fit is None:
        reason = "not calibrated to the site: no events / no non-events, no model is fitted"
    elif not ready.ready:
        miss = ", ".join(f"{k} short by {v}" for k, v in ready.missing.items() if v)
        reason = f"not calibrated to the site: below the level-3 minimum ({miss}); the fit is the prior updated " \
                 "with few data"
    elif not fit.converged:
        reason = "the final fit did not converge"
    elif level == "partial":
        reason = _validation_reason(report)
    else:
        reason = "calibrated to the site: the labor and zone validations recommend"

    cov = np.cov(X, rowvar=False).reshape(X.shape[1], X.shape[1])
    inv = np.linalg.pinv(cov)
    mean = X.mean(axis=0)
    dist = np.sqrt(np.einsum("ij,jk,ik->i", X - mean, inv, X - mean).clip(min=0))
    installed = Counter(t.sost_instalado for t in ts)
    counts = {"tramos": int(y.size), "failures": int(y.sum()), "non_failures": int(y.size - y.sum()),
              "labors": len(set(labors)), "zones": ready.counts["zones"],
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
        maha_p99=float(np.percentile(dist, MAHALANOBIS_PERCENTILE)), counts=counts, warnings=tuple(warns),
        zone_sd=zone_sd, poor_rock=poor, class_counts=class_counts)


# ---------- recomendación ----------

@dataclass(frozen=True)
class SupportOption:
    code: str
    order: int
    p_failure: float  # P(falla dentro del horizonte) para una labor nueva (media marginal)
    p_low: float
    p_high: float  # cota conservadora: 1 − exp(−λ_sup·H·Z_q)
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
    vals = {c: _tramo_number(t, c, allow_zero=c in ("rmr_valor", "profundidad_m"))
            for c in (qcol, "luz_m", "esr", "profundidad_m")}
    missing = [c for c in (qcol, "luz_m", "esr") if vals[c] is None]
    if model.use_depth and vals["profundidad_m"] is None:
        missing.append("profundidad_m")
    if missing:
        return None, None, None, None, missing
    qual = math.log(vals[qcol]) if model.quality == "q" else vals[qcol]
    return qual, math.log(vals["luz_m"] / vals["esr"]), vals["profundidad_m"], _get(t, "tipo_labor"), []


def _model_row(model, qual, lnde, rank, depth, tipo):
    return _row(qual, lnde, rank, depth, tipo, model.use_depth, model.labor_types, model.interaction_ref)


def _p_high(model: PerformanceModel, X, exposure: float, level: float) -> np.ndarray:
    """Cota superior de P(falla en H) para una labor nueva en una zona nueva: 1 − exp(−e^η_sup·H·Z_q), con
    η_sup = η + q·sqrt(se² + σ_z²) (se = el error de η de `prob_interval`, q su cuantil) y Z_q el cuantil de la
    fragilidad. Con σ_z = 0 es exactamente el límite superior de `FrailtyHazardFit.prob_interval`."""
    f = model.fit
    eta, _, hi = _eta_interval(f, X, level)
    u = 0.5 + level / 2
    q = norm.ppf(u) if f.df is None else float(student_t.ppf(u, f.df))
    eta_up = eta + np.sqrt((hi - eta) ** 2 + (q * model.zone_sd) ** 2)
    return -np.expm1(-np.exp(eta_up) * exposure * f.frailty_quantile(level))


def recommend(model: PerformanceModel, tramos, *, threshold, exposure_days, practice=None,
              level: float = 0.9) -> tuple[Recommendation, ...]:
    """P(falla dentro de `exposure_days`) para una labor nueva, con su intervalo (`level` en [0.5, 1), 90 % por
    defecto), de cada tipo de la mina para cada tramo (R10). Nunca hace caer el lote: un tramo con datos
    inválidos sale sin opciones.

    - `threshold` (P(falla) aceptable) y `exposure_days` (horizonte H en días) son OBLIGATORIOS: los fija el
      ingeniero.
    - Se elige el tipo más liviano ELEGIBLE cuyo límite SUPERIOR, 1 − exp(−λ_sup·H·Z_q), queda ≤ el umbral;
      λ_sup suma la varianza entre zonas (`_p_high`). Elegible: con al menos `MIN_TRAMOS_PER_TYPE_LEVEL2` tramos
      en el entrenamiento, con al menos `MIN_TRAMOS_PER_CLASS` de ese tipo en la clase de calidad del tramo y sin
      extrapolar ese tipo (rango del tipo fuera del entrenamiento o Mahalanobis sobre el p99). No se elige en
      ningún tipo si `model.recommendation_blockers` no está vacío, si el tramo extrapola (Q, De, profundidad o H
      fuera del rango de entrenamiento, o tipo de labor no visto o vacío) o si está en el tercio peor de la
      calidad y su calibración fuera de pliegue no pasa (`model.poor_rock_problem`). Si ningún tipo queda bajo el
      umbral, lo dice («no support type meets the threshold»). Las opciones se muestran igual.
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
    n_cont = 3 + (model.form == "interaction") + model.use_depth  # columnas no una-caliente
    ranged = [j for j in range(n_cont) if j != _RANK and not (model.form == "interaction" and j == _INT)]
    poor_problem = model.poor_rock_problem
    blockers = model.recommendation_blockers
    block = blockers[0] if blockers else None
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
            out.append(empty(block))
            continue
        qual, lnde, depth, tipo, missing = _tramo_inputs(model, t)
        if missing:
            out.append(empty(f"missing or invalid input: {', '.join(missing)}"))
            continue
        X = np.array([_model_row(model, qual, lnde, i, depth, tipo) for i in range(len(model.support_types))])
        p, p_lo, _ = model.fit.prob_interval(X, exp, lv)
        p_hi = _p_high(model, X, exp, lv)
        q_class = min(_quality_class(model.quality, qual), len(model.class_counts) - 1)
        d = np.sqrt(np.einsum("ij,jk,ik->i", X - mean, inv, X - mean).clip(min=0))
        outside = (X[:, :n_cont] < lo_tr[:n_cont]) | (X[:, :n_cont] > hi_tr[:n_cont])
        rank_out, far = outside[:, _RANK], d > model.maha_p99
        ext_notes = [f"{model.features[j]} outside the training range" for j in ranged if outside[0, j]]
        if not model.exposure_min <= exp <= model.exposure_max:
            ext_notes.append("exposure_days outside the training range of exposures")
        if model.labor_types and (tipo is None or tipo not in model.labor_types):
            ext_notes.append("tipo_labor missing or not seen in training")
        tramo_ext = bool(ext_notes)
        options = []
        for i, ((c, o), n_hist) in enumerate(zip(model.support_types, model.support_counts)):
            note = ("not enough history" if n_hist < MIN_TRAMOS_PER_TYPE_LEVEL2
                    else "extrapolation" if rank_out[i] or far[i]
                    else "not enough history in this rock class"
                    if model.class_counts[q_class][i] < MIN_TRAMOS_PER_CLASS else None)
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
        if reason is None and poor_problem is not None and qual <= model.poor_rock_cut:
            reason = poor_problem
        if reason is None:
            chosen = next((o.code for o in options if o.eligible and o.meets_threshold), None)
            if chosen is None:  # compuerta (c): «ningún tipo cumple», o los que cumplen no son elegibles
                reason = ("no support type meets the threshold" if not any(o.meets_threshold for o in options)
                          else "the types that meet the threshold are not eligible")
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
    """Mallas n×n en el plano (log10 Q, log10 De) y P(falla en `exposure_days`) de una labor nueva (media
    marginal) para un tipo de sostenimiento (al estilo de Mawdesley et al. 2001)."""

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
    ranks = {c: i for i, (c, _) in enumerate(model.support_types)}
    if support_code not in ranks:
        raise ValueError(f"support_code must be one of {', '.join(ranks)}")
    exp = _exposure(exposure_days)
    if isinstance(n, bool) or not isinstance(n, (int, np.integer)) or n < 2:
        raise ValueError("n must be an integer >= 2")
    for name, rg in (("q_range", q_range), ("de_range", de_range)):
        if len(rg) != 2 or not 0 < rg[0] < rg[1]:
            raise ValueError(f"{name} must be (low, high) with 0 < low < high")
    if model.use_depth and depth_m is None:
        depth_m = model.maha_mean[model.features.index("depth_m")]
    tipo = tipo_labor if tipo_labor is not None else (model.labor_types[0] if model.labor_types else None)
    lq = np.linspace(math.log10(q_range[0]), math.log10(q_range[1]), n)
    ld = np.linspace(math.log10(de_range[0]), math.log10(de_range[1]), n)
    LQ, LD = np.meshgrid(lq, ld)
    X = np.array([_model_row(model, a * math.log(10), b * math.log(10), ranks[support_code], depth_m, tipo)
                  for a, b in zip(LQ.ravel(), LD.ravel())])
    return IsoprobabilityGrid(LQ, LD, model.fit.prob_marginal(X, exp).reshape(LQ.shape), support_code, exp, tipo,
                              None if not model.use_depth else float(depth_m))


# ---------- JSON ----------

_FIT_KEYS = ("coef", "intercept", "cov", "active_bounds", "converged", "n", "loglik", "x_mean", "x_scale", "message",
             "signs", "n_events", "theta", "log_theta_sd", "cov_kind", "n_clusters", "df", "n_groups")


class _ModelFileError(ValueError):
    """Un archivo de modelo inválido; el mensaje nombra la clave, nunca su valor."""


def save_model(model: PerformanceModel, path) -> Path:
    """Guarda el modelo en JSON (con `schema_version`). Nunca lleva filas ni ids (R10, R13). Un modelo de menos de
    100 tramos no se guarda: su media, su covarianza y sus rangos casi reconstruyen las filas."""
    if model.counts.get("tramos", 0) < FEW_ROWS:
        raise ValueError(f"the model was fitted with fewer than {FEW_ROWS} usable tramos: its stored summaries "
                         "would nearly rebuild the training rows, so it is not saved")
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


_KNOWN_KEYS = set(_FIT_KEYS)  # se completa con los campos del modelo abajo


def _check_keys(what: str, got, expected) -> None:
    extra, missing = set(got) - set(expected), sorted(set(expected) - set(got))
    if extra or missing:
        named = sorted(k for k in extra if k in _KNOWN_KEYS)
        unknown = len(extra) - len(named)
        parts = ([f"unexpected keys {named}"] if named else []) + ([f"{unknown} unknown key(s)"] if unknown else []) \
            + ([f"missing keys {missing}"] if missing else [])
        raise _ModelFileError(f"{what}: {', '.join(parts)}")


def _is_num(x, *, finite=True) -> bool:
    return (isinstance(x, (int, float)) and not isinstance(x, bool)
            and (math.isfinite(x) or (not finite and math.isnan(x))))


def _is_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _nums(x, n=None, *, finite=True) -> bool:
    return isinstance(x, list) and (n is None or len(x) == n) and all(_is_num(v, finite=finite) for v in x)


def _strs(x) -> bool:
    return isinstance(x, list) and all(isinstance(v, str) for v in x)


_TOP_CHECKS = {
    "quality": lambda v: v in QUALITIES,
    "features": lambda v: _strs(v) and len(v) >= 3,
    "labor_types": _strs,
    "use_depth": lambda v: isinstance(v, bool),
    "signs": lambda v: isinstance(v, list) and all(_is_int(s) and s in (-1, 0, 1) for s in v),
    "coef_ci": lambda v: isinstance(v, list) and all(_nums(c, 2, finite=False) for c in v),
    "active_bounds": _strs,
    "support_types": lambda v: isinstance(v, list) and len(v) >= 1 and all(
        isinstance(s, list) and len(s) == 2 and isinstance(s[0], str) and _is_int(s[1]) for s in v),
    "support_counts": lambda v: isinstance(v, list) and all(_is_int(c) and c >= 0 for c in v),
    "calibration": lambda v: v in CALIBRATION_LEVELS,
    "calibration_reason": lambda v: isinstance(v, str),
    "metrics": lambda v: isinstance(v, dict) and all(_is_num(x, finite=False) for x in v.values()),
    "calibration_curve": lambda v: isinstance(v, list) and all(_nums(c, 3) for c in v),
    "train_min": _nums, "train_max": _nums,
    "exposure_min": lambda v: _is_num(v) and v > 0, "exposure_max": lambda v: _is_num(v) and v > 0,
    "maha_mean": _nums,
    "maha_inv": lambda v: isinstance(v, list) and all(_nums(r) for r in v),
    "maha_p99": lambda v: _is_num(v) and v >= 0,
    "counts": lambda v: isinstance(v, dict) and all(_is_int(x) for x in v.values())
    and {"tramos", "zones", "minority_class", "minority_class_minimum"} <= set(v),
    "warnings": _strs, "version": lambda v: isinstance(v, str), "schema_version": _is_int,
    "zone_sd": lambda v: _is_num(v) and v >= 0,
    "poor_rock": lambda v: v is None or (isinstance(v, list) and len(v) == 3 and _is_num(v[0]) and _is_int(v[1])
                                         and v[1] >= 0 and _is_num(v[2]) and v[2] >= 0),
    "class_counts": lambda v: isinstance(v, list) and all(
        isinstance(r, list) and all(_is_int(c) and c >= 0 for c in r) for r in v),
    "fit": lambda v: v is None or isinstance(v, dict), "validation": lambda v: v is None or isinstance(v, dict),
}
_FIT_CHECKS = {
    "coef": _nums, "intercept": _is_num, "cov": lambda v: isinstance(v, list) and all(
        _nums(r, finite=False) for r in v), "active_bounds": lambda v: isinstance(v, list) and all(map(_is_int, v)),
    "converged": lambda v: isinstance(v, bool), "n": _is_int, "loglik": lambda v: _is_num(v, finite=False),
    "x_mean": _nums, "x_scale": lambda v: _nums(v) and all(x > 0 for x in v), "message": lambda v: isinstance(v, str),
    "signs": lambda v: isinstance(v, list) and all(_is_int(s) and s in (-1, 0, 1) for s in v), "n_events": _is_int,
    "theta": lambda v: _is_num(v) and v >= 0, "log_theta_sd": lambda v: _is_num(v, finite=False),
    "cov_kind": lambda v: v in ("cluster", "laplace"), "n_clusters": _is_int, "df": lambda v: v is None or (
        _is_int(v) and v >= 1), "n_groups": _is_int,
}


def _check_model(m: PerformanceModel) -> None:
    """Coherencia de un modelo leído (C, I3): orden de los tipos, largos, signos y la calibración recalculada."""
    orders = [o for _, o in m.support_types]
    if any(b <= a for a, b in zip(orders, orders[1:])):
        raise _ModelFileError("performance model: support_types must be in strictly increasing order")
    if len(m.support_counts) != len(m.support_types):
        raise _ModelFileError("performance model: support_counts must have one count per support type")
    if len(m.class_counts) != _n_classes(m.quality) or any(len(r) != len(m.support_types) for r in m.class_counts):
        raise _ModelFileError("performance model: class_counts must have one row per quality class and one count per "
                              "support type")
    p = len(m.features)
    lengths = {"signs": len(m.signs), "train_min": len(m.train_min), "train_max": len(m.train_max),
               "maha_mean": len(m.maha_mean), "maha_inv": len(m.maha_inv)}
    if m.fit is not None:
        lengths.update({"coef_ci": len(m.coef_ci), "fit.coef": m.fit.coef.size, "fit.signs": len(m.fit.signs),
                        "fit.x_mean": m.fit.x_mean.size, "fit.x_scale": m.fit.x_scale.size})
    bad = {k for k, n in lengths.items() if n != p} | ({"maha_inv"} if any(len(r) != p for r in m.maha_inv) else set())
    if m.fit is not None and m.fit.cov.shape != (p + 1, p + 1):
        bad.add("fit.cov")
    if bad:
        raise _ModelFileError(f"performance model: lengths do not match the features: {', '.join(sorted(bad))}")
    if not set(m.active_bounds) <= set(m.features):
        raise _ModelFileError("performance model: active_bounds must name features")
    if m.fit is not None:
        if tuple(m.fit.signs) != tuple(m.signs):
            raise _ModelFileError("performance model: fit.signs differ from signs")
        if any(s * c < 0 for s, c in zip(m.signs, m.fit.coef)):
            raise _ModelFileError("performance model: a coefficient breaks its sign constraint")
        if m.fit.converged and not np.all(np.isfinite(m.fit.cov)):
            raise _ModelFileError("performance model: fit.cov must be finite in a converged fit")
    ready = (m.counts["minority_class"] >= m.counts["minority_class_minimum"]
             and m.counts["zones"] >= MIN_ZONES_LEVEL3)
    if m.calibration != _calibration(m.fit, ready, m.validation is not None and m.validation.recommend):
        raise _ModelFileError("performance model: calibration does not match the stored validation, readiness and "
                              "convergence")


def load_model(path) -> PerformanceModel:
    """Lee un modelo guardado con `save_model`; la predicción es exactamente la misma. Valida el esquema: claves
    exactas, tipos y números finitos, orden de los tipos, largos, signos y la calibración recalculada con lo
    guardado (ValueError si algo no cuadra; el mensaje nombra la clave, nunca su valor)."""
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("the performance model file is not valid JSON") from None
    if not isinstance(d, dict):
        raise ValueError("the performance model file must hold a JSON object")
    if d.get("schema_version") != SCHEMA_VERSION or isinstance(d.get("schema_version"), bool):
        raise ValueError(f"unsupported performance model schema_version (this version reads {SCHEMA_VERSION})")
    _check_keys("performance model", d, PerformanceModel.__dataclass_fields__)
    for k, chk in _TOP_CHECKS.items():
        if not chk(d[k]):
            raise ValueError(f"performance model: {k} is not valid")
    f = d.pop("fit")
    if f is not None:
        _check_keys("fit", f, _FIT_KEYS)
        for k, chk in _FIT_CHECKS.items():
            if not chk(f[k]):
                raise ValueError(f"performance model: fit.{k} is not valid")
    try:
        fit = None if f is None else FrailtyHazardFit(
            coef=np.array(f["coef"], dtype=float), intercept=float(f["intercept"]),
            cov=np.array(f["cov"], dtype=float), active_bounds=tuple(f["active_bounds"]), converged=f["converged"],
            n=f["n"], loglik=f["loglik"], x_mean=np.array(f["x_mean"], dtype=float),
            x_scale=np.array(f["x_scale"], dtype=float), message=f["message"], signs=tuple(f["signs"]),
            n_events=f["n_events"], theta=float(f["theta"]), log_theta_sd=f["log_theta_sd"], cov_kind=f["cov_kind"],
            n_clusters=f["n_clusters"], df=f["df"], n_groups=f["n_groups"])
        v = d.pop("validation")
        report = None if v is None else ValidationReport(
            results={k: Comparison(**{**c, "improvements": {r: Improvement(**i) for r, i in c["improvements"].items()}})
                     for k, c in v["results"].items()}, skipped=dict(v["skipped"]))
    except (TypeError, KeyError, AttributeError, ValueError):
        raise ValueError("performance model: fit or validation is not valid") from None
    keep = ("metrics", "counts")  # dicts: se quedan como dicts
    m = PerformanceModel(fit=fit, validation=report,
                         **{k: (val if k in keep else _tuples(val)) for k, val in d.items()})
    _check_model(m)
    return m


_KNOWN_KEYS |= set(PerformanceModel.__dataclass_fields__)
