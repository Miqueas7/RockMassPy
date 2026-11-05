"""Nivel 2: auditoría de la práctica de sostenimiento (Fase 4B, tarea 10; plan R7, R8, R13 y R14).

Describe qué sostenimiento instala la mina en cada condición; **nunca dice qué instalar**. La práctica pasada como
etiqueta reproduce las decisiones del pasado, no las óptimas, y las fallas dependen de lo que se eligió (sesgo de
selección; `docs/investigacion/MODELOS_SOSTENIMIENTO.md` §1.2, punto 8): por eso el modelo de práctica va separado
del de desempeño (§7.2) y aquí solo se audita.

- Modelo: logit acumulado de odds proporcionales (Bürkner y Vuorre 2019, [V2]) del rango del tipo instalado sobre
  ln Q, ln De, el indicador de vida útil permanente y `tipo_labor` en una-caliente, **sin restricciones de signo**.
  Convención de `stats.ordinal_logit_fit`: P(y ≤ k) = σ(θ_k − x·β), así que β > 0 empuja a un tipo más pesado.
- Signos: peor macizo o más luz → tipo más pesado, o sea β_lnQ < 0 y β_lnDe > 0. Si el IC 95 % (de la covarianza)
  excluye 0 con el signo contrario, la práctica es incoherente; si incluye 0, «no significativo», nunca «coherente».
- Validación (`validation.validate`, R7) con kappa ponderado cuadrático (Cohen 1968, [V2]) contra el ficticio de
  clase y la línea base NGI (el mismo logit con la categoría de `read_q_chart` como única variable). Solo dice si la
  práctica es más predecible que la carta Q; no habilita ninguna recomendación.
- Conjunto conforme agrupado (Angelopoulos y Bates 2023, [V2]): probabilidades fuera de pliegue por labor, puntaje
  1 − p(clase verdadera) y cuantil con la corrección de muestra finita. La garantía de cobertura supone que las
  labores son intercambiables; con zonas muy distintas entre sí no se cumple (§4, punto 3).
- Concordancia entre `sost_recomendado` y `sost_instalado` (matriz y kappa ponderado).

Privacidad (R13): los avisos y veredictos llevan conteos, nombres de variables y códigos de tipo de sostenimiento;
nunca labor, zona, coordenadas ni litología. Los `id_tramo` van solo en campos (`outside_set`, `tramos`) y en el
archivo de resultados.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..batch import write_table
from ..history import (MIN_LABORS_PER_TYPE_LEVEL2, MIN_TRAMOS_PER_TYPE_LEVEL2, History, audit_history, labor_key,
                       level2_rows)
from ..q_support import read_q_chart
from .stats import ordinal_logit_fit, quadratic_weighted_kappa
from .validation import (ValidationReport, dummy_class_fit_predict, group_kfold, out_of_fold, tramo_groups,
                         validate)

VERDICTS = ("coherent", "not significant", "practice incoherent with rock quality", "practice incoherent with span",
            "not estimable")
STATUSES = ("ready", "insufficient data")
_EXPECTED_SIGN = {"ln_q": -1.0, "ln_de": 1.0}  # peor macizo (ln Q menor) o más luz → tipo más pesado
_INCOHERENT = {"ln_q": VERDICTS[2], "ln_de": VERDICTS[3]}
_Z95 = 1.959963984540054
PRACTICE_RESULT_COLUMNS = ("id_tramo", "sost_instalado", "sost_mas_probable", "conjunto_conforme",
                           "fuera_del_conjunto")


@dataclass(frozen=True)
class Coefficient:
    """Coeficiente del ajuste final con su IC 95 % de Wald (NaN si la covarianza no se pudo calcular)."""

    value: float
    se: float
    ci_low: float
    ci_high: float


@dataclass(frozen=True)
class PracticeTramo:
    """Resultado de un tramo, para la tabla de resultados. `conformal_set` es None si su pliegue falló."""

    id_tramo: str
    installed: str
    most_probable: str | None
    conformal_set: tuple[str, ...] | None
    outside: bool


@dataclass(frozen=True)
class Concordance:
    """Recomendado frente a instalado en la escala de todos los tipos definidos (por `orden`).

    `matrix[i, j]` = tramos con el recomendado `types[i]` y el instalado `types[j]`. `kappa` es None si no está
    definido (los dos constantes en el mismo tipo)."""

    types: tuple[str, ...]
    matrix: np.ndarray
    kappa: float | None
    n: int


@dataclass(frozen=True)
class PracticeAudit:
    """Auditoría de la práctica. `validation.recommend` aquí NO es una recomendación: solo dice si la práctica de
    la mina es más predecible que la carta Q (ver `beyond_chart`)."""

    n: int
    labors: int
    types: tuple[str, ...]  # tipos presentes, del más liviano al más pesado (clases 0..K−1)
    coefficients: dict[str, Coefficient]
    verdicts: dict[str, str]  # "ln_q" y "ln_de" → uno de VERDICTS
    converged: bool
    validation: ValidationReport = field(repr=False)
    conformal_level: float
    conformal_threshold: float  # q del puntaje 1 − p; inf si hay muy pocas filas para el nivel; NaN sin conjuntos
    coverage: float  # fracción de tramos con conjunto cuyo tipo instalado cae dentro (NaN sin conjuntos)
    outside_set: tuple[str, ...] = field(repr=False)  # id_tramo fuera de su conjunto conforme
    tramos: tuple[PracticeTramo, ...] = field(repr=False)
    concordance: Concordance | None
    status: str  # uno de STATUSES
    missing_types: tuple[str, ...]  # tipos definidos bajo el mínimo del nivel 2
    dropped_columns: tuple[str, ...]  # columnas colineales (o constantes) fuera del ajuste final
    warnings: tuple[str, ...]

    @property
    def beyond_chart(self) -> bool:
        """¿La práctica es más predecible que la carta Q en la validación por labor (IC de la mejora > 0)?"""
        r = self.validation.results.get("labor")
        return r is not None and r.beats("ngi")


def _candidates(rows) -> tuple[np.ndarray, list[str], list[str]]:
    """Columnas candidatas (sin y): no usan la respuesta, así que se arman con todas las filas; la selección por
    rango se rehace con el train de cada pliegue."""
    warns = []
    cols = {"ln_q": [math.log(t.q_valor) for t in rows], "ln_de": [math.log(t.luz_m / t.esr) for t in rows]}
    missing_vida = sum(t.vida_util is None for t in rows)
    if missing_vida:  # como la profundidad del nivel 3: la variable entra solo si todas las filas la traen
        warns.append(f"vida_util is missing in {missing_vida} of {len(rows)} rows: the permanent indicator is "
                     "left out of the model")
    else:
        cols["permanent"] = [float(t.vida_util == "Permanente") for t in rows]
    levels = sorted({t.tipo_labor or "(missing)" for t in rows})
    if len({t.tipo_labor for t in rows} - {None}) >= 2:
        for lv in levels:
            cols[f"tipo_labor={lv}"] = [float((t.tipo_labor or "(missing)") == lv) for t in rows]
    return np.column_stack(list(cols.values())), list(cols), warns


def _select(X: np.ndarray) -> np.ndarray:
    """Índices de columnas linealmente independientes junto con el intercepto, en orden (una-caliente: cae la
    categoría redundante; también las constantes y las colineales con vida útil)."""
    keep, base = [], np.ones((X.shape[0], 1))
    for j in range(X.shape[1]):
        trial = np.column_stack([base, X[:, j]])
        if np.linalg.matrix_rank(trial) > base.shape[1]:
            keep.append(j)
            base = trial
    return np.array(keep, dtype=np.intp)


def _fit_proba(Xtr, ytr, Xte, K):
    """Ajusta con las clases presentes en train y devuelve P de las K clases en test (0 para una clase ausente)."""
    cols = _select(Xtr)
    present = np.unique(ytr)
    if present.size < 2:
        raise ValueError("the training set has a single support type")
    fit = ordinal_logit_fit(Xtr[:, cols], np.searchsorted(present, ytr), n_classes=present.size)
    if not (np.all(np.isfinite(fit.coef)) and np.all(np.isfinite(fit.cuts))):
        raise ValueError("ordinal fit gave non-finite parameters")
    out = np.zeros((Xte.shape[0], K))
    out[:, present] = fit.predict_proba(Xte[:, cols])
    return out


def _model(X, y, K, kind):
    def fit_predict(train, test):
        p = _fit_proba(X[train], y[train], X[test], K)
        return p if kind == "proba" else np.argmax(p, axis=1)
    return fit_predict


def _verdict(name, c: Coefficient | None) -> str:
    if c is None or not (math.isfinite(c.ci_low) and math.isfinite(c.ci_high)):
        return VERDICTS[4]
    if c.ci_low <= 0 <= c.ci_high:
        return VERDICTS[1]
    return VERDICTS[0] if math.copysign(1.0, c.value) == _EXPECTED_SIGN[name] else _INCOHERENT[name]


def _concordance(history: History) -> Concordance | None:
    order = sorted(history.support_types, key=lambda s: s.orden)
    rank = {s.codigo_tipo: i for i, s in enumerate(order)}
    pairs = [(rank[t.sost_recomendado], rank[t.sost_instalado]) for t in history.tramos
             if t.sost_recomendado in rank and t.sost_instalado in rank]
    if not pairs or len(rank) < 2:
        return None
    rec, ins = np.array(pairs).T
    K = len(rank)
    matrix = np.bincount(rec * K + ins, minlength=K * K).reshape(K, K)
    try:
        kappa = quadratic_weighted_kappa(rec, ins, K)
    except ValueError:
        kappa = None
    return Concordance(tuple(rank), matrix, kappa, len(pairs))


def audit_practice(history: History, *, conformal_level: float = 0.9, k: int = 5, n_boot: int = 2000,
                   seed: int = 0) -> PracticeAudit:
    """Audita la práctica del nivel 2 con las filas de `history.level2_rows`. Nunca recomienda qué instalar.

    Lanza ValueError si no hay al menos 2 tipos instalados con filas usables. Por debajo del mínimo del nivel 2
    (≥ 10 tramos por tipo en ≥ 5 labores, decisión de diseño) igual ajusta y marca `status="insufficient data"`.
    """
    if not (isinstance(conformal_level, (int, float)) and 0 < conformal_level < 1):
        raise ValueError("conformal_level must be between 0 and 1")
    rows = level2_rows(history)
    by_code = {s.codigo_tipo: s.orden for s in history.support_types}
    types = tuple(sorted({t.sost_instalado for t in rows}, key=lambda c: by_code[c]))
    if len(types) < 2:
        raise ValueError(f"level 2 needs at least 2 installed support types with usable rows (Q, span and ESR > 0), "
                         f"got {len(types)}")
    K = len(types)
    y = np.array([types.index(t.sost_instalado) for t in rows], dtype=np.intp)
    X, names, warns = _candidates(rows)

    readiness = [r for r in audit_history(history).readiness if r.level == 2]
    missing = tuple(r.item for r in readiness if not r.ready)
    status = STATUSES[1] if missing else STATUSES[0]
    if missing:
        warns.append(f"insufficient data for level 2: support type(s) {', '.join(missing)} below the minimum of "
                     f"{MIN_TRAMOS_PER_TYPE_LEVEL2} tramos in {MIN_LABORS_PER_TYPE_LEVEL2} labors (design decision)")

    # ajuste final con todos los datos, sin restricciones de signo
    cols = _select(X)
    fit = ordinal_logit_fit(X[:, cols], y, n_classes=K)
    if not fit.converged:
        warns.append(f"final ordinal fit did not converge: {fit.message}")
    se = np.sqrt(np.diag(fit.cov)[:cols.size]) if cols.size else np.empty(0)
    coefficients = {names[j]: Coefficient(float(fit.coef[i]), float(se[i]), float(fit.coef[i] - _Z95 * se[i]),
                                          float(fit.coef[i] + _Z95 * se[i])) for i, j in enumerate(cols)}
    verdicts = {v: _verdict(v, coefficients.get(v)) for v in _EXPECTED_SIGN}
    dropped = tuple(n for j, n in enumerate(names) if j not in set(cols.tolist()))

    # validación: modelo de práctica contra el ficticio y la carta Q (categoría NGI como única variable)
    labors, zones, years = tramo_groups(rows)
    ngi = np.array([[float(read_q_chart(t.q_valor, t.luz_m / t.esr).category)] for t in rows])
    validation = validate(y, {"practice": _model(X, y, K, "class"), "dummy": dummy_class_fit_predict(y),
                              "ngi": _model(ngi, y, K, "class")},
                          kind="class", labors=labors, zones=zones, years=years,
                          metric=lambda a, b: quadratic_weighted_kappa(a, b, K), higher_is_better=True,
                          reference=("dummy", "ngi"), k=k, n_boot=n_boot, seed=seed)

    # conjunto conforme agrupado por labor
    sets: list[tuple[int, ...] | None] = [None] * len(rows)
    best: list[int | None] = [None] * len(rows)
    q_hat, coverage = math.nan, math.nan
    try:
        folds = group_kfold(labors, k=k, seed=seed)
    except ValueError:
        folds = None
        warns.append("conformal sets need at least 2 labors: none computed")
    if folds is not None:
        oof = out_of_fold(folds, _model(X, y, K, "proba"), len(rows), kind="proba")
        if oof.n_failed:
            warns.append(f"{oof.n_failed} of {len(folds)} conformal folds failed: their tramos have no set")
        idx = np.flatnonzero(oof.covered)
        if idx.size:
            scores = np.sort(1.0 - oof.pred[idx, y[idx]])
            rank = math.ceil((idx.size + 1) * conformal_level)  # corrección de muestra finita
            if rank > idx.size:
                q_hat = math.inf
                warns.append(f"too few covered rows ({idx.size}) for the conformal level: every set holds all types")
            else:
                q_hat = float(scores[rank - 1])
            for i in idx:
                p = oof.pred[i]
                sets[i] = tuple(int(c) for c in np.flatnonzero(1.0 - p <= q_hat))
                best[i] = int(np.argmax(p))
            coverage = float(np.mean([y[i] in sets[i] for i in idx]))

    tramos = tuple(PracticeTramo(t.id_tramo, t.sost_instalado, None if best[i] is None else types[best[i]],
                                 None if sets[i] is None else tuple(types[c] for c in sets[i]),
                                 sets[i] is not None and int(y[i]) not in sets[i]) for i, t in enumerate(rows))
    return PracticeAudit(
        n=len(rows), labors=len({labor_key(t) for t in rows} - {None}), types=types, coefficients=coefficients,
        verdicts=verdicts, converged=fit.converged, validation=validation, conformal_level=float(conformal_level),
        conformal_threshold=q_hat, coverage=coverage, outside_set=tuple(t.id_tramo for t in tramos if t.outside),
        tramos=tramos, concordance=_concordance(history), status=status, missing_types=missing,
        dropped_columns=dropped, warnings=tuple(warns))


def save_practice_results(audit: PracticeAudit, path) -> Path:
    """Escribe .xlsx (hoja `Practica`) o .csv, un tramo por fila. Es un archivo de resultados: el id_tramo sí va.
    El conjunto conforme va con los códigos separados por «|»; vacío si el pliegue del tramo falló."""
    rows = [(t.id_tramo, t.installed, t.most_probable,
                       None if t.conformal_set is None else "|".join(t.conformal_set), "sí" if t.outside else "no")
                      for t in audit.tramos]
    return write_table(path, PRACTICE_RESULT_COLUMNS, rows, sheet="Practica")
