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
  labores son intercambiables; con zonas muy distintas entre sí no se cumple (§4, punto 3). **«Fuera del conjunto»
  marca ≈ 1 − nivel de los tramos por construcción** (≈ 10 % al 90 %), con cualquier práctica: no equivale a un
  desvío ni a un error de la mina, solo dice cuáles tramos son los menos típicos de su propia práctica.
- Consistencia (Fase 5B, revisada): los signos no ven una práctica ruidosa (tipos más livianos o más pesados al
  azar, GSI leído a ojo, cambio de tabla), porque el ruido no invierte la tendencia. El indicador sale del ajuste
  final: w = ancho medio de las bandas internas del logit (distancia media entre cortes consecutivos, en la escala
  logística). En el centro de la banda de un tipo el modelo da P(ese tipo) = tanh(w/4); el indicador es
  1 − tanh(w/4), la parte de los tramos que en ese centro reciben otro tipo: 0 = siempre el mismo tipo en la misma
  condición, 1 = sin relación con la condición. Sobre `MAX_PRACTICE_INCONSISTENCY` el veredicto es «practice poorly
  consistent», además de los de signo; sin ajuste final convergido o con menos de 3 tipos (no hay banda interna),
  «not estimable». La entropía media fuera de pliegue / ln K de antes medía la mezcla de tipos de la mina y no el
  ruido; normalizarla con la entropía de la marginal (coeficiente de incertidumbre) tampoco separa (ver la
  constante). Mide la práctica vista desde Q y De: una tabla por GSI con una correlación GSI–Q floja también sale
  poco consistente (`shifted_correlation`: 11 de 20).
- Concordancia entre `sost_recomendado` y `sost_instalado` (matriz y kappa ponderado).
- Tramos nuevos: `PracticeAudit.predict_proba` y `conformal_set` usan el ajuste final y la misma codificación; es
  el protocolo `practice` que recibe `recommend` del nivel 3. Un `tipo_labor` no visto lanza ValueError.

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
from .stats import OrdinalLogitFit, ordinal_logit_fit, quadratic_weighted_kappa
from .validation import _tramo_number  # validación común de las entradas (niveles 2 y 3)
from .validation import (ValidationReport, dummy_class_fit_predict, group_kfold, ngi_category, out_of_fold,
                         tramo_groups, validate)

VERDICTS = ("coherent", "not significant", "practice incoherent with rock quality", "practice incoherent with span",
            "not estimable")
STATUSES = ("ready", "insufficient data")
CONSISTENCY_VERDICTS = ("consistent", "practice poorly consistent", "not estimable")
# Decisión de diseño, valor por confirmar (revisión de la Fase 5B). Banco de la mina sintética con 5 tipos, 20 semillas
# (3000–3019) por celda, prácticas × geologías con dataclasses.replace sobre SCENARIOS: consistente (la de cada
# escenario), ruidosa de mapeo (campos de mapeo de noisy_mapping) e incoherente (GSI a ojo con DE 10, desvíos de 0.2
# a cada lado y cambio de tabla, de incoherent_practice) sobre base, worse_site, better_site, large_mine y
# small_mine. Media [mín; máx] y marcadas con 0.66:
#   base      cons. 0.593 [0.572; 0.609] 0/20 · mapeo 0.636 [0.606; 0.654] 0/20 · incoh. 0.699 [0.679; 0.732] 20/20
#   worse     cons. 0.605 [0.582; 0.641] 0/20 · mapeo 0.627 [0.576; 0.664] 1/20 · incoh. 0.687 [0.634; 0.719] 19/20
#   better    cons. 0.609 [0.532; 0.655] 0/20 · mapeo 0.629 [0.562; 0.666] 3/20 · incoh. 0.693 [0.650; 0.733] 18/20
#   large     cons. 0.593 [0.584; 0.602] 0/20 · mapeo 0.637 [0.624; 0.649] 0/20 · incoh. 0.705 [0.696; 0.715] 20/20
#   small     cons. 0.574 [0.488; 0.649] 0/19 · mapeo 0.620 [0.525; 0.699] 6/20 · incoh. 0.699 [0.622; 0.759] 16/20
# (cons. = consistente, incoh. = incoherente; small: 1 semilla sin convergencia, «not estimable»). Sin small: 4
# falsos positivos de 160 y 3 falsos negativos de 80; small: 6 de 39 y 4 de 20. Con base: mine_practice 0.346, conservative_practice 0.474 y ngi_site 0.009 (0/20); shifted_correlation 0.659
# [0.626; 0.694], 11/20 (ver el docstring). La entropía / ln K con 0.76 marcaba 0/20 incoherentes en worse y better;
# dividida entre la entropía de la marginal, better consistente daba 0.72–0.84 y base incoherente 0.80–0.84
MAX_PRACTICE_INCONSISTENCY = 0.66
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
    la mina es más predecible que la carta Q y el ficticio (ver `beyond_chart`)."""

    n: int
    labors: int
    types: tuple[str, ...]  # tipos presentes, del más liviano al más pesado (clases 0..K−1)
    coefficients: dict[str, Coefficient]
    verdicts: dict[str, str]  # "ln_q" y "ln_de" → uno de VERDICTS
    # 1 − tanh(w/4), w = ancho medio de las bandas internas del ajuste final (NaN si no convergió o con < 3 tipos),
    # y su veredicto, uno de CONSISTENCY_VERDICTS: describe qué tan ruidosa es la práctica, aparte de los signos
    consistency: float
    consistency_verdict: str
    converged: bool
    validation: ValidationReport = field(repr=False)
    conformal_level: float
    # q del puntaje 1 − p; inf si hay muy pocas filas para el nivel; NaN sin conjuntos (p. ej. el ajuste final
    # no convergió)
    conformal_threshold: float
    outside_set: tuple[str, ...] = field(repr=False)  # id_tramo fuera de su conjunto conforme
    tramos: tuple[PracticeTramo, ...] = field(repr=False)
    concordance: Concordance | None
    status: str  # uno de STATUSES
    missing_types: tuple[str, ...]  # tipos definidos bajo el mínimo del nivel 2
    dropped_columns: tuple[str, ...]  # columnas colineales (o constantes) fuera del ajuste final, con aviso
    warnings: tuple[str, ...]
    # lo mínimo del ajuste final para predecir tramos nuevos (coeficientes, cortes y codificación; nunca filas)
    fit: OrdinalLogitFit = field(repr=False)
    design: PracticeDesign = field(repr=False)
    columns: tuple[int, ...] = field(repr=False)  # columnas de `design.names` que entraron al ajuste final

    @property
    def beyond_chart(self) -> bool:
        """¿La práctica es más predecible que la carta Q y el ficticio? Es la regla de `ValidationReport.recommend`
        (labor y zona fuera con IC > 0, sin pliegues fallidos, ≤ 1 % de réplicas descartadas; temporal como no
        inferioridad). Describe la práctica; no habilita ninguna recomendación."""
        return self.validation.recommend

    def predict_proba(self, tramos) -> np.ndarray:
        """P de cada tipo de `types` (n, K) para tramos nuevos, con el ajuste final (todos los datos) y sus mismas
        columnas. ValueError si a un tramo le falta una variable que el modelo usa o trae un tipo_labor no visto."""
        X = self.design.matrix(list(tramos))[:, list(self.columns)]
        if not (np.all(np.isfinite(self.fit.coef)) and np.all(np.isfinite(self.fit.cuts))):
            raise ValueError("the final practice fit has non-finite parameters: it cannot predict")
        return self.fit.predict_proba(X)

    def conformal_set(self, tramo) -> tuple[str, ...]:
        """Tipos (en orden, del más liviano al más pesado) con 1 − p_k ≤ `conformal_threshold` para un tramo nuevo.

        El umbral sale de las predicciones fuera de pliegue por labor y se aplica a las probabilidades del ajuste con
        todos los datos (estilo cross-conformal): la garantía de cobertura es aproximada y supone que las labores
        nuevas son intercambiables con las del histórico. En la revisión, con labores nuevas, la cobertura al 90 %
        dio 0.902 de media y 0.776 de mínimo en 20 semillas. ValueError si no hay umbral (ver `warnings`)."""
        if math.isnan(self.conformal_threshold):
            raise ValueError("no conformal threshold was computed for this audit (see its warnings)")
        p = self.predict_proba([tramo])[0]
        return tuple(c for c, pk in zip(self.types, p) if 1.0 - pk <= self.conformal_threshold)


_MISSING_LEVEL = "(missing)"


@dataclass(frozen=True)
class PracticeDesign:
    """Codificación de las variables (sin y, sin filas ni ids): se fija con el histórico y se aplica igual a
    tramos nuevos. `labor_levels` vacío = tipo_labor no entra; si entra, la categoría de referencia es la primera
    (alfabética, «(missing)» al final) y cada una de las demás tiene su columna."""

    permanent: bool
    labor_levels: tuple[str, ...]

    @property
    def names(self) -> list[str]:
        return ["ln_q", "ln_de", *(["permanent"] if self.permanent else []),
                *[f"tipo_labor={lv}" for lv in self.labor_levels[1:]]]

    def matrix(self, tramos) -> np.ndarray:
        """Columnas candidatas de cada tramo. Los mensajes dicen la posición en la lista (si hay más de un tramo),
        nunca un identificador.
        Un tipo_labor no visto lanza ValueError: el histórico no dice nada de esa práctica (decisión de diseño;
        tratarlo como la categoría de referencia inventaría un dato)."""
        out = []
        for i, t in enumerate(tramos):
            who = "tramo" if len(tramos) == 1 else f"tramo at position {i}"
            for name in ("q_valor", "luz_m", "esr"):
                if _tramo_number(t, name) is None:
                    raise ValueError(f"{who}: {name} must be a number > 0 for the practice model")
            row = [math.log(t.q_valor), math.log(t.luz_m / t.esr)]
            if self.permanent:
                if t.vida_util is None:
                    raise ValueError(f"{who}: vida_util is required by the practice model")
                row.append(float(t.vida_util == "Permanente"))
            if self.labor_levels:
                lv = t.tipo_labor or _MISSING_LEVEL
                if lv not in self.labor_levels:
                    raise ValueError(f"{who}: tipo_labor was not seen in the history, so the "
                                     "practice model has no information about it")
                row += [float(lv == x) for x in self.labor_levels[1:]]
            out.append(row)
        return np.array(out, dtype=float).reshape(len(out), len(self.names))


def _design(rows) -> tuple[PracticeDesign, list[str]]:
    """Codificación con todas las filas: no usa la respuesta; la selección por rango se rehace en cada pliegue."""
    warns = []
    missing_vida = sum(t.vida_util is None for t in rows)
    if missing_vida:  # como la profundidad del nivel 3: la variable entra solo si todas las filas la traen
        warns.append(f"vida_util is missing in {missing_vida} of {len(rows)} rows: the permanent indicator is "
                     "left out of the model")
    levels = ()
    if len({t.tipo_labor for t in rows} - {None}) >= 2:
        levels = tuple(sorted({t.tipo_labor or _MISSING_LEVEL for t in rows},
                              key=lambda lv: (lv == _MISSING_LEVEL, lv)))
    return PracticeDesign(not missing_vida, levels), warns


def _select(X: np.ndarray) -> np.ndarray:
    """Índices de columnas linealmente independientes junto con el intercepto, en orden: caen las constantes y las
    colineales (p. ej. un tipo de labor que coincide con la vida útil)."""
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
    design, warns = _design(rows)
    X, names = design.matrix(rows), design.names

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
    if dropped:  # los nombres de tipo de labor vienen de la lista de la plantilla: pueden ir en el aviso
        warns.append(f"columns dropped for collinearity: {', '.join(dropped)}; remaining coefficients are contrasts")

    # validación: modelo de práctica contra el ficticio y la carta Q (categoría NGI como única variable)
    labors, zones, years = tramo_groups(rows)
    ngi = np.array([[float(ngi_category(t))] for t in rows])
    validation = validate(y, {"practice": _model(X, y, K, "class"), "dummy": dummy_class_fit_predict(y),
                              "ngi": _model(ngi, y, K, "class")},
                          kind="class", labors=labors, zones=zones, years=years,
                          metric=lambda a, b: quadratic_weighted_kappa(a, b, K), higher_is_better=True,
                          reference=("dummy", "ngi"), k=k, n_boot=n_boot, seed=seed)
    warns += validation.warnings

    # conjunto conforme agrupado por labor
    sets: list[tuple[int, ...] | None] = [None] * len(rows)
    best: list[int | None] = [None] * len(rows)
    q_hat, folds, consistency = math.nan, None, math.nan
    if not fit.converged:  # conformal_set usa el ajuste final: sin él no hay conjuntos
        warns.append("conformal sets not computed: the final ordinal fit did not converge")
    else:
        try:
            folds = group_kfold(labors, k=k, seed=seed)
        except ValueError:
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
    # consistencia con el ajuste final: ancho medio w de las bandas internas en la escala logística; en el centro de
    # una banda P(tipo de la banda) = σ(w/2) − σ(−w/2) = tanh(w/4), y el indicador es lo que falta para 1
    if fit.converged and K >= 3 and np.all(np.isfinite(fit.cuts)):
        consistency = 1.0 - math.tanh(float(np.mean(np.diff(fit.cuts))) / 4.0)
    if math.isnan(consistency):
        consistency_verdict = CONSISTENCY_VERDICTS[2]
    elif consistency > MAX_PRACTICE_INCONSISTENCY:
        consistency_verdict = CONSISTENCY_VERDICTS[1]
        warns.append(f"practice poorly consistent: at the centre of a support type's range, {consistency:.0%} of the "
                     f"tramos get another type (threshold {MAX_PRACTICE_INCONSISTENCY:g}, design decision): the same "
                     "condition gets different support types")
    else:
        consistency_verdict = CONSISTENCY_VERDICTS[0]

    tramos = tuple(PracticeTramo(t.id_tramo, t.sost_instalado, None if best[i] is None else types[best[i]],
                                 None if sets[i] is None else tuple(types[c] for c in sets[i]),
                                 sets[i] is not None and int(y[i]) not in sets[i]) for i, t in enumerate(rows))
    return PracticeAudit(
        n=len(rows), labors=len({labor_key(t) for t in rows} - {None}), types=types, coefficients=coefficients,
        verdicts=verdicts, consistency=consistency, consistency_verdict=consistency_verdict, converged=fit.converged,
        validation=validation, conformal_level=float(conformal_level),
        conformal_threshold=q_hat, outside_set=tuple(t.id_tramo for t in tramos if t.outside),
        tramos=tramos, concordance=_concordance(history), status=status, missing_types=missing,
        dropped_columns=dropped, warnings=tuple(warns), fit=fit, design=design, columns=tuple(cols.tolist()))


def save_practice_results(audit: PracticeAudit, path) -> Path:
    """Escribe .xlsx (hoja `Practica`) o .csv, un tramo por fila. Es un archivo de resultados: el id_tramo sí va.
    El conjunto conforme va con los códigos separados por «|»; vacío si el pliegue del tramo falló."""
    rows = [(t.id_tramo, t.installed, t.most_probable,
                       None if t.conformal_set is None else "|".join(t.conformal_set), "sí" if t.outside else "no")
                      for t in audit.tramos]
    return write_table(path, PRACTICE_RESULT_COLUMNS, rows, sheet="Practica")
