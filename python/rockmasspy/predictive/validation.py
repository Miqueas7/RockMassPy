"""Motor de validación del módulo predictivo (Fase 4B, tarea 9; plan R7).

Particiones agrupadas (labor, zona fuera, temporal), predicciones fuera de pliegue y comparación contra referencias
con bootstrap por labor de la mejora. Las trampas que evita están en `docs/investigacion/MODELOS_SOSTENIMIENTO.md`
§1.2 y §7.3: la partición aleatoria por fila filtra el vecino de la misma labor (Roberts et al. 2017), así que solo
existe para mostrar el contraste y todo lo que la usa queda marcado `optimistic`; el preprocesamiento lo hace quien
llama dentro de `fit_predict` (se ajusta con train y se aplica a test); no hay SMOTE ni rebalanceo.

Los modelos y las métricas entran como funciones: este módulo no sabe de logits ni de kappas. La línea base NGI se
arma en `practice.py` y `performance.py` con estas mismas piezas.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Hashable, Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np

from .stats import group_bootstrap

_EMPTY = np.empty(0, dtype=np.intp)
# errores que dejan un pliegue como fallido (p. ej. falta una clase en train); cualquier otro es un error de código
_FOLD_ERRORS = (ValueError, ArithmeticError, np.linalg.LinAlgError)
# decisión de diseño (por confirmar): con más del 1 % de réplicas degeneradas el IC no es confiable: no se recomienda
MAX_DISCARDED_FRACTION_DECISION = 0.01


class _DataError(ValueError):
    """Faltan datos para una partición o una comparación (una zona, un año, un grupo en test). Su mensaje lleva
    solo conteos, nunca etiquetas: `validate` lo copia en `skipped`."""


@dataclass(frozen=True)
class Fold:
    """Un pliegue: índices de train y de test. `excluded` = filas que no entran en ninguno (p. ej. sin año)."""

    name: str
    train: np.ndarray
    test: np.ndarray
    excluded: np.ndarray = field(default_factory=lambda: _EMPTY)
    optimistic: bool = False  # partición aleatoria por fila: el resultado se informa como optimista


def _int(name: str, v, minimum: int) -> int:
    if isinstance(v, bool) or not isinstance(v, (int, np.integer)) or v < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return int(v)


def _codes(groups: Sequence[Hashable]) -> tuple[np.ndarray, int]:
    """Código entero por fila en orden de primera aparición (sirve con etiquetas tupla, como `labor_key`)."""
    seen: dict = {}
    try:
        codes = np.array([seen.setdefault(g, len(seen)) for g in groups], dtype=np.intp)
    except TypeError:
        raise ValueError("groups must be a sequence of hashable labels") from None
    return codes, len(seen)


def _at_least_two(n_groups: int) -> None:
    if n_groups < 2:
        raise _DataError(f"groups needs at least 2 distinct groups, got {n_groups}")


def group_kfold(groups: Sequence[Hashable], *, k: int = 5, seed: int = 0) -> tuple[Fold, ...]:
    """k pliegues agrupados: cada grupo (labor) entero en un solo test. k = min(k, número de grupos).

    Reparto equilibrado por filas: los grupos, barajados con la semilla y ordenados de mayor a menor, van uno a uno
    al pliegue con menos filas (el barajado solo decide los empates). Misma semilla → mismos pliegues.
    """
    k = _int("k", k, 2)
    _int("seed", seed, -(2 ** 63))
    codes, n_groups = _codes(groups)
    _at_least_two(n_groups)
    k = min(k, n_groups)
    sizes = np.bincount(codes, minlength=n_groups)
    order = np.random.default_rng(seed).permutation(n_groups)
    order = order[np.argsort(-sizes[order], kind="stable")]
    fold_of_group, load = np.empty(n_groups, dtype=np.intp), np.zeros(k, dtype=np.intp)
    for g in order:
        f = int(np.argmin(load))  # empate: el pliegue de menor índice
        fold_of_group[g], load[f] = f, load[f] + sizes[g]
    fold_of_row = fold_of_group[codes]
    return tuple(Fold(f"fold-{f + 1}", np.flatnonzero(fold_of_row != f), np.flatnonzero(fold_of_row == f))
                 for f in range(k))


def leave_one_group_out(groups: Sequence[Hashable]) -> tuple[Fold, ...]:
    """Un pliegue por grupo (p. ej. dejar una zona fuera), en orden de primera aparición.

    Los nombres son `group-1`, `group-2`…, nunca la etiqueta: un código de zona no viaja en un mensaje (R13).
    """
    codes, n_groups = _codes(groups)
    _at_least_two(n_groups)
    return tuple(Fold(f"group-{g + 1}", np.flatnonzero(codes != g), np.flatnonzero(codes == g))
                 for g in range(n_groups))


def temporal_split(years: Sequence[int | None], *, groups: Sequence[Hashable] | None = None) -> tuple[Fold, ...]:
    """Entrena con los años anteriores al último y prueba con el último. Exige ≥ 2 años distintos.

    Las filas sin año (None o NaN) van a `excluded`: no entran ni en train ni en test. Ojo: una misma labor puede
    quedar en train y en test (sus tramos de años distintos), así que el efecto de labor se filtra en parte; por eso
    esta partición complementa a la agrupada y no la reemplaza. Con `groups` (labores) exige ≥ 2 grupos en el test,
    porque el bootstrap de la mejora remuestrea grupos.
    """
    vals = []
    for y in years:
        if y is None or (isinstance(y, (float, np.floating)) and math.isnan(y)):
            vals.append(None)
        elif isinstance(y, bool) or not isinstance(y, (int, np.integer, float, np.floating)) \
                or not math.isfinite(y) or y != int(y):
            raise _DataError("years must be integers or None")
        else:
            vals.append(int(y))
    known = {v for v in vals if v is not None}
    if len(known) < 2:
        raise _DataError(f"temporal split needs at least 2 distinct years, got {len(known)}")
    last = max(known)
    arr = np.array([-1 if v is None else v for v in vals])
    missing = np.array([v is None for v in vals], dtype=bool)
    test = np.flatnonzero(~missing & (arr == last))
    if groups is not None:
        codes, _ = _codes(groups)
        if codes.size != arr.size:
            raise ValueError("years and groups must have the same number of rows")
        n_test_groups = np.unique(codes[test]).size
        if n_test_groups < 2:
            raise _DataError(f"temporal split needs at least 2 groups in the last year, got {n_test_groups}")
    return (Fold("temporal", np.flatnonzero(~missing & (arr < last)), test, np.flatnonzero(missing)),)


def random_kfold(n: int, *, k: int = 5, seed: int = 0) -> tuple[Fold, ...]:
    """k pliegues aleatorios por fila. Solo para mostrar el contraste: filtra vecinos de la misma labor y todo
    resultado que la use queda marcado `optimistic=True`."""
    n, k = _int("n", n, 2), _int("k", k, 2)
    _int("seed", seed, -(2 ** 63))
    parts = np.array_split(np.random.default_rng(seed).permutation(n), min(k, n))
    return tuple(Fold(f"random-{f + 1}", np.sort(np.concatenate(parts[:f] + parts[f + 1:])), np.sort(p),
                      optimistic=True) for f, p in enumerate(parts))


def tramo_groups(tramos) -> tuple[list, list, list]:
    """(labores, zonas, años) de una lista de `HistoryTramo`: la entrada de las tres particiones.

    Labor = `labor_key`; año = el de `fecha_evaluacion` (None sin fecha, la partición temporal la excluye).
    """
    from ..history import labor_key
    return ([labor_key(t) for t in tramos], [t.zona_nivel for t in tramos],
            [None if t.fecha_evaluacion is None else int(t.fecha_evaluacion[:4]) for t in tramos])


def _tramo_number(t, col: str, *, allow_zero: bool = False) -> float | None:
    """El valor de `col` de un tramo (objeto o dict) si es un número finito > 0 (≥ 0 con `allow_zero`); si no,
    None. Validación común de las entradas de los niveles 2 y 3."""
    v = t.get(col) if isinstance(t, Mapping) else getattr(t, col, None)
    if isinstance(v, bool) or not isinstance(v, (int, float, np.integer, np.floating)) or not math.isfinite(v):
        return None
    return float(v) if v > 0 or (allow_zero and v == 0) else None


def ngi_category(tramo) -> int:
    """Categoría de la carta Q NGI de un tramo, `read_q_chart(Q, luz/ESR)`: la variable de la línea base de nivel 0
    (niveles 2 y 3). El tramo necesita Q, luz y ESR > 0."""
    from ..q_support import read_q_chart
    return read_q_chart(tramo.q_valor, tramo.luz_m / tramo.esr).category


# ---------- predicciones fuera de pliegue ----------

@dataclass(frozen=True)
class FoldFailure:
    fold: str
    reason: str  # solo el tipo de la excepción: su texto podría traer etiquetas de labor o zona (R13)


@dataclass(frozen=True)
class OofPredictions:
    """Predicciones fuera de pliegue. `pred[i]` vale solo si `covered[i]`; `fold_of[i]` = −1 si no está cubierta."""

    pred: np.ndarray
    fold_of: np.ndarray
    covered: np.ndarray
    kind: str = "proba"
    failures: tuple[FoldFailure, ...] = ()
    optimistic: bool = False

    @property
    def n_failed(self) -> int:
        return len(self.failures)


def out_of_fold(folds: Sequence[Fold], fit_predict: Callable[[np.ndarray, np.ndarray], object], n: int, *,
                kind: str) -> OofPredictions:
    """Corre `fit_predict(train_idx, test_idx)` en cada pliegue y junta las predicciones de test.

    `kind` = "proba" (vector de probabilidades o matriz n×K) o "class" (etiquetas). Todo el preprocesamiento va
    dentro de `fit_predict`. Si un pliegue lanza ValueError, ArithmeticError o LinAlgError, o devuelve
    probabilidades no finitas o fuera de [0, 1], queda en `failures` con el tipo del error y la validación sigue;
    sus filas quedan sin cubrir y no entran en las métricas (y la comparación ya no recomienda). Índices fuera de
    [0, n), train y test que se cruzan, un test repetido o una salida de forma equivocada son errores de código.
    """
    if kind not in ("proba", "class"):
        raise ValueError('kind must be "proba" or "class"')
    n = _int("n", n, 1)
    parts, failures = [], []
    fold_of = np.full(n, -1, dtype=np.intp)
    for f, fold in enumerate(folds):
        test, train = np.asarray(fold.test, dtype=np.intp), np.asarray(fold.train, dtype=np.intp)
        for part, idx in (("test", test), ("train", train)):
            if idx.size and (idx.min() < 0 or idx.max() >= n):  # un índice negativo tomaría otra fila en silencio
                raise ValueError(f"fold {fold.name}: {part} indices out of range for n={n}")
        if np.intersect1d(train, test).size:
            raise ValueError(f"fold {fold.name}: train and test share rows")
        if np.any(fold_of[test] >= 0) or np.unique(test).size != test.size:
            raise ValueError(f"fold {fold.name}: a row is in more than one test set")
        try:
            out = np.asarray(fit_predict(train, test))
        except _FOLD_ERRORS as e:
            failures.append(FoldFailure(fold.name, type(e).__name__))
            continue
        if out.ndim == 0 or out.shape[0] != test.size or out.ndim > (2 if kind == "proba" else 1):
            raise ValueError(f"fold {fold.name}: fit_predict returned shape {out.shape} for {test.size} test rows")
        if parts and out.shape[1:] != parts[0][1].shape[1:]:
            raise ValueError(f"fold {fold.name}: prediction shape {out.shape[1:]} differs from earlier folds")
        if kind == "proba":
            out = out.astype(float)
            if not np.all(np.isfinite(out)) or np.any((out < 0) | (out > 1)):
                failures.append(FoldFailure(fold.name, "fit_predict returned probabilities that are not "
                                                       "finite or not in [0, 1]"))
                continue
        fold_of[test] = f
        parts.append((test, out))
    if parts:
        tail = parts[0][1].shape[1:]
        dtype = float if kind == "proba" else np.result_type(*[o for _, o in parts])
        pred = np.full((n,) + tail, np.nan) if kind == "proba" else np.zeros((n,) + tail, dtype=dtype)
        for test, out in parts:
            pred[test] = out
    else:
        pred = np.full(n, np.nan)
    return OofPredictions(pred=pred, fold_of=fold_of, covered=fold_of >= 0, kind=kind, failures=tuple(failures),
                          optimistic=any(f.optimistic for f in folds))


# ---------- comparación contra referencias ----------

@dataclass(frozen=True)
class Improvement:
    """Mejora del modelo principal sobre una referencia, en el sentido de «mejor» (> 0 = gana)."""

    value: float
    ci_low: float
    ci_high: float


@dataclass(frozen=True)
class Comparison:
    """Métricas en las filas cubiertas por todos los modelos y la mejora con su IC 95 % por bootstrap por grupos."""

    main: str
    metrics: dict[str, float]
    improvements: dict[str, Improvement]
    higher_is_better: bool
    n_rows: int
    n_groups: int
    n_boot: int
    n_discarded: int  # réplicas degeneradas (métrica no finita o con error)
    failed_folds: dict[str, int]  # pliegues fallidos por modelo
    optimistic: bool

    def beats(self, reference: str) -> bool:
        """Verdadero solo si el límite inferior del IC de la mejora es > 0 (un IC sin calcular no gana)."""
        lo = self.improvements[reference].ci_low
        return bool(lo > 0)  # NaN > 0 es falso

    @property
    def blockers(self) -> tuple[str, ...]:
        """Motivos por los que no se recomienda; vacío si se recomienda. Solo nombres de modelo y conteos."""
        out = [f"{m} failed {k} fold(s)" for m, k in self.failed_folds.items() if k]
        if self.n_discarded > MAX_DISCARDED_FRACTION_DECISION * self.n_boot:
            out.append(f"{self.n_discarded} of {self.n_boot} bootstrap replicates were degenerate "
                       f"(more than {MAX_DISCARDED_FRACTION_DECISION:.0%})")
        out += [f"{self.main} does not beat {r} (95% CI of the improvement reaches 0)"
                for r in self.improvements if not self.beats(r)]
        return tuple(out)

    @property
    def recommend(self) -> bool:
        """Cero pliegues fallidos en todos los modelos, ≤ 1 % de réplicas degeneradas y límite inferior > 0 contra
        todas las referencias."""
        return not self.blockers

    @property
    def noninferior(self) -> bool:
        """Mejora puntual ≥ 0 contra todas las referencias (la regla de la partición temporal)."""
        return all(i.value >= 0 for i in self.improvements.values())


def _main_and_refs(models: Mapping, reference) -> tuple[str, tuple[str, ...]]:
    refs = (reference,) if isinstance(reference, str) else tuple(reference)
    if not refs:
        raise ValueError("reference must name at least one model")
    missing = [r for r in refs if r not in models]
    if missing:
        raise ValueError(f"reference models not in preds: {missing}")
    mains = [m for m in models if m not in refs]
    if len(mains) != 1:
        raise ValueError(f"preds must have exactly one model that is not a reference, got {mains}")
    return mains[0], refs


def compare_models(y, preds: Mapping[str, OofPredictions], *, metric: Callable[[np.ndarray, np.ndarray], float],
                   higher_is_better: bool, groups: Sequence[Hashable], reference: str | Sequence[str],
                   n_boot: int = 2000, seed: int = 0) -> Comparison:
    """Compara el modelo principal (el único de `preds` que no está en `reference`) contra cada referencia.

    Las métricas se calculan solo en las filas cubiertas por TODOS los modelos. El IC 95 % de la mejora sale de un
    bootstrap por grupos (`group_bootstrap`, por labor) pareado: en cada réplica se remuestrean grupos y la métrica
    de todos los modelos se recalcula sobre las mismas filas. `metric(y, pred)` recibe las filas ya recortadas.
    """
    main, refs = _main_and_refs(preds, reference)
    ya = np.asarray(y)
    g = list(groups)
    n = ya.shape[0]
    if len(g) != n or any(p.pred.shape[0] != n for p in preds.values()):
        raise ValueError("y, groups and every prediction must have the same number of rows")
    common = np.flatnonzero(np.logical_and.reduce([p.covered for p in preds.values()]))
    if common.size == 0:
        raise _DataError("no row is covered by every model (did every fold fail?)")
    names = (main,) + refs
    yc, pc = ya[common], {m: preds[m].pred[common] for m in names}
    sub_groups = [g[i] for i in common]
    _at_least_two(len(set(sub_groups)))
    sign = 1.0 if higher_is_better else -1.0

    def scores(idx):
        return np.array([float(metric(yc[idx], pc[m][idx])) for m in names])

    def gains(idx):
        s = scores(idx)
        return sign * (s[0] - s[1:])

    point = scores(np.arange(common.size))
    boot = group_bootstrap(sub_groups, gains, n_boot=n_boot, seed=seed)
    try:
        lo, hi = boot.percentile_ci(0.95)
        lo, hi = np.atleast_1d(lo), np.atleast_1d(hi)
    except ValueError:  # todas las réplicas degeneradas: sin IC, no gana
        lo = hi = np.full(len(refs), np.nan)
    gain = sign * (point[0] - point[1:])
    return Comparison(main=main, metrics=dict(zip(names, map(float, point))),
                      improvements={r: Improvement(float(gain[i]), float(lo[i]), float(hi[i]))
                                    for i, r in enumerate(refs)},
                      higher_is_better=bool(higher_is_better), n_rows=int(common.size),
                      n_groups=len(set(sub_groups)), n_boot=boot.n_boot, n_discarded=boot.n_discarded,
                      failed_folds={m: preds[m].n_failed for m in names},
                      optimistic=any(p.optimistic for p in preds.values()))


# ---------- referencias genéricas ----------

def dummy_class_fit_predict(y) -> Callable[[np.ndarray, np.ndarray], np.ndarray]:
    """Clasificador ficticio: predice la clase más frecuente de train (empate: la etiqueta menor)."""
    ya = np.asarray(y)

    def fit_predict(train, test):
        if len(train) == 0:
            raise ValueError("empty training set")
        labels, counts = np.unique(ya[train], return_counts=True)
        return np.full(len(test), labels[np.argmax(counts)])
    return fit_predict


def dummy_proba_fit_predict(y, n_classes: int | None = None) -> Callable[[np.ndarray, np.ndarray], np.ndarray]:
    """Probabilidad ficticia: la prevalencia de train (y binario 0/1); con `n_classes`, la distribución de las
    clases 0..n_classes−1 de train, como matriz n×K."""
    ya = np.asarray(y)
    if n_classes is not None:
        n_classes = _int("n_classes", n_classes, 2)
    vals = np.unique(ya)
    allowed = np.arange(2 if n_classes is None else n_classes)
    if not np.all(np.isin(vals, allowed)):
        raise ValueError("y must hold 0/1 labels" if n_classes is None
                         else f"y must hold class labels 0..{n_classes - 1}")

    def fit_predict(train, test):
        if len(train) == 0:
            raise ValueError("empty training set")
        yt = ya[train].astype(np.intp)
        if n_classes is None:
            return np.full(len(test), yt.mean())
        return np.tile(np.bincount(yt, minlength=n_classes) / yt.size, (len(test), 1))
    return fit_predict


# ---------- envoltorio: las tres particiones ----------

@dataclass(frozen=True)
class ValidationReport:
    """Un resultado por partición (`labor`, `zone`, `temporal` y, si se pidió, `random`) y la decisión.

    Una partición que no se pudo armar o comparar (p. ej. una sola zona, un solo año) va a `skipped` con el motivo.
    """

    results: dict[str, Comparison]
    skipped: dict[str, str]

    @property
    def recommend(self) -> bool:
        """Recomiendan la partición por labor Y la de zona fuera (si falta alguna, no se recomienda). La aleatoria
        no cuenta.

        Decisión de diseño: la temporal entra como NO INFERIORIDAD, no como superioridad significativa. Si se pudo
        armar, bloquea solo cuando la mejora puntual contra alguna referencia es < 0 (el sitio sale peor en el
        último año); su IC no se exige porque el test de un solo año es chico y casi siempre toca el cero. Si quedó
        en `skipped`, no bloquea y lo dice `warnings`."""
        temporal = self.results.get("temporal")
        return all(p in self.results and self.results[p].recommend for p in ("labor", "zone")) \
            and (temporal is None or temporal.noninferior)

    @property
    def warnings(self) -> tuple[str, ...]:
        out = []
        if "temporal" in self.skipped:
            out.append(f"temporal validation not run ({self.skipped['temporal']}): the decision rests on the "
                       f"labor and zone partitions only")
        if "random" in self.results:
            out.append("the random row split is optimistic and does not count in the decision")
        return tuple(out)


def validate(y, models: Mapping[str, Callable[[np.ndarray, np.ndarray], object]], *, kind: str,
             labors: Sequence[Hashable], zones: Sequence[Hashable], years: Sequence[int | None],
             metric: Callable[[np.ndarray, np.ndarray], float], higher_is_better: bool,
             reference: str | Sequence[str], k: int = 5, n_boot: int = 2000, seed: int = 0,
             random_split: bool = False) -> ValidationReport:
    """Arma las particiones por labor (k pliegues), zona fuera y temporal; corre `out_of_fold` y `compare_models`
    en cada una con bootstrap por labor. `random_split=True` agrega la partición aleatoria, marcada optimista y
    sin peso en la decisión. `models` = {nombre: fit_predict}, con las referencias incluidas.

    Decisión (`ValidationReport.recommend`, §7.3): tienen que recomendar la partición por labor y la de zona fuera;
    si alguna no se pudo armar, no se recomienda. Decisión de diseño: la temporal entra como no inferioridad, porque
    el test de un solo año es chico y su IC casi siempre toca el cero: si se pudo armar, bloquea solo si la mejora
    puntual contra alguna referencia es < 0; si no (un solo año, un solo grupo en el último año), no bloquea y el
    reporte lo avisa en `warnings`.
    """
    n = len(labors)
    if not (len(zones) == len(years) == n == np.asarray(y).shape[0]):
        raise ValueError("y, labors, zones and years must have the same number of rows")
    _main_and_refs(models, reference)  # un error de llamada no se esconde como partición omitida
    _int("k", k, 2)
    makers = {"labor": lambda: group_kfold(labors, k=k, seed=seed), "zone": lambda: leave_one_group_out(zones),
              "temporal": lambda: temporal_split(years, groups=labors)}
    if random_split:
        makers["random"] = lambda: random_kfold(n, k=k, seed=seed)
    results, skipped = {}, {}
    for name, make in makers.items():
        try:
            folds = make()
        except _DataError as e:  # una sola zona, un solo año…
            skipped[name] = str(e)
            continue
        # fuera del try: una salida de forma equivocada es un error de código, no una partición omitida
        preds = {m: out_of_fold(folds, fp, n, kind=kind) for m, fp in models.items()}
        try:
            results[name] = compare_models(y, preds, metric=metric, higher_is_better=higher_is_better,
                                           groups=labors, reference=reference, n_boot=n_boot, seed=seed)
        except _DataError as e:  # sin filas comunes, un solo grupo en las filas comunes…
            skipped[name] = str(e)
        except ValueError as e:  # p. ej. la métrica sin definir en ese test; su texto no se copia (R13)
            skipped[name] = f"comparison failed ({type(e).__name__})"
    return ValidationReport(results=results, skipped=skipped)
