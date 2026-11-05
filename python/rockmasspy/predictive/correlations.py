"""Nivel 1: correlaciones propias del sitio (Fase 4A, tarea 6; plan R5, R6 y R13).

Ajusta RMR = a·ln Q + b, GSI = a·RMR + b o GSI = a·ln Q′ + b por dominio (`group_by`, por defecto la litología;
Somodi et al. 2021) y para toda la mina, con los métodos de `stats.py`: OLS con intervalo de predicción (la que
predice), Deming solo con la razón de varianzas de error, bootstrap por labor y bayesiano con la correlación global
del núcleo como *prior* (`docs/investigacion/MODELOS_SOSTENIMIENTO.md` §2.2).

Privacidad (R13): el valor del dominio (la litología) solo va como clave de `SiteCorrelationResult.domains`, para la
tabla de resultados. Los avisos, el `name` y el `source` de la `CustomCorrelation` llevan códigos genéricos («D1»),
conteos y métodos, nunca un valor de una columna de identificación ni la litología.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

import numpy as np

from .. import _rockmasspy_core as rm
from ..history import _PAIRS, MIN_LABORS_LEVEL1, MIN_PAIRS_LEVEL1, History, HistoryTramo, _pos, labor_key
from .stats import (BayesLinearFit, BootstrapResult, DemingFit, OlsFit, _positive, bayes_linear_fit, deming_fit,
                    group_bootstrap, ols_fit)

KINDS = ("rmr_from_q", "gsi_from_rmr", "gsi_from_q_prime")
STATUSES = ("site", "unstable", "not_calibrated")
NO_DOMAIN = "(no domain)"

# Activación (R5/R6). Decisiones de diseño, por confirmar con Miqueas y con la simulación de R11.
SLOPE_CI_REL_TOL = 0.25  # el IC 95 % bootstrap de la pendiente debe caer dentro de ±25 % de la pendiente OLS
MAX_DISCARDED_FRACTION = 0.10  # más réplicas degeneradas que esto: el ajuste es inestable
# Fuerza del prior por defecto (R5-valor por confirmar): desviación de a = 50 % de |a global|, de b = 10 puntos
PRIOR_SD_A_FRACTION = 0.5
PRIOR_SD_B_POINTS = 10.0
PRIOR_SIGMA = 8.0

_LOG_X = {"rmr_from_q": True, "gsi_from_rmr": False, "gsi_from_q_prime": True}
_GLOBAL = {("rmr_from_q", "RMR89"): rm.Correlation.RmrFromQ_Huang2026,
           ("rmr_from_q", "RMR76"): rm.Correlation.RmrFromQ_Bieniawski1976,
           ("gsi_from_rmr", "RMR89"): rm.Correlation.GsiFromRmr89Prime_HoekDiederichs2006,
           ("gsi_from_rmr", "RMR76"): rm.Correlation.GsiFromRmr76Prime_HoekDiederichs2006,
           ("gsi_from_q_prime", None): rm.Correlation.GsiFromQPrime_Hoek1995}
_RMR_EDITIONS = ("RMR76", "RMR89")


def _rmr_ed(t: HistoryTramo) -> str:
    return re.sub(r"[\s-]", "", t.rmr_edicion or "").upper()  # RMR-89, RMR 89 → RMR89, como la auditoría


@dataclass(frozen=True)
class SiteCorrelationFit:
    """Ajuste de un dominio (o de toda la mina) en la variable transformada t = ln x (Q, Q′) o t = x (RMR).

    `a`, `b` y `predict` usan la OLS con estado "site" o "unstable" y el bayesiano con "not_calibrated". El
    bayesiano se ajustó con t centrada en `x_center` (ver `fit_site_correlation`): `bayes.b` es el nivel en el
    centro; `bayes_a`/`bayes_b` ya están vueltos a la forma y = a·t + b.
    """

    kind: str
    label: str  # código genérico: "mine", "D1", "D2"…; nunca el valor del dominio
    domain: str | None = field(repr=False)  # valor del dominio (dato del cliente): solo para tablas de resultados
    status: str
    n: int
    n_labors: int
    x_min: float  # rango observado de la x original (Q, no ln Q)
    x_max: float
    x_from: str
    y_to: str
    log_x: bool
    ols: OlsFit | None
    deming: DemingFit | None
    deming_reason: str | None
    bootstrap: BootstrapResult | None
    a_ci: tuple[float, float] | None
    b_ci: tuple[float, float] | None
    bayes: BayesLinearFit
    x_center: float
    prior_correlation: str  # method_id de la correlación global usada como prior
    warnings: tuple[str, ...]

    @property
    def bayes_a(self) -> float:
        return self.bayes.a

    @property
    def bayes_b(self) -> float:
        return self.bayes.b - self.bayes.a * self.x_center

    @property
    def method(self) -> str:
        return "OLS" if self.status != "not_calibrated" else "Bayesian"

    @property
    def a(self) -> float:
        return self.ols.a if self.method == "OLS" else self.bayes_a

    @property
    def b(self) -> float:
        return self.ols.b if self.method == "OLS" else self.bayes_b

    def predict(self, x0, level: float = 0.95):
        """Intervalo de predicción en x0 (x original: Q, Q′ o RMR): (ŷ, inferior, superior), sin recortar."""
        t = np.asarray(x0, dtype=float)
        t = np.log(t) if self.log_x else t
        return self.ols.predict(t, level) if self.method == "OLS" else self.bayes.predict(t - self.x_center, level)

    def to_custom_correlation(self) -> rm.CustomCorrelation:
        """CustomCorrelation para las tablas por labor (1B) y `plot_correlation` (1C).

        El nombre y el `source` solo llevan el código genérico, conteos, método y estado (R13).
        """
        if not self.x_min < self.x_max:
            raise ValueError(f"site correlation {self.label}: the observed x range is a single value; "
                             "a CustomCorrelation needs valid_min < valid_max")
        form = rm.CorrelationForm.LogLinear if self.log_x else rm.CorrelationForm.Linear
        prior = f", prior {self.prior_correlation}" if self.method == "Bayesian" else ""
        source = (f"RockMassPy site fit {self.kind}: n={self.n}, labors={self.n_labors}, "
                  f"method={self.method}{prior}, status={self.status}")
        return rm.CustomCorrelation(name=f"{self.kind}_{self.label}", from_=self.x_from, to=self.y_to, form=form,
                                    a=self.a, b=self.b, valid_min=self.x_min, valid_max=self.x_max, source=source)


@dataclass(frozen=True)
class SiteCorrelationResult:
    kind: str
    group_by: str | None
    mine: SiteCorrelationFit
    domains: dict = field(repr=False)  # valor del dominio → SiteCorrelationFit; vacío con group_by=None
    prior_correlation: str
    prior_verification: str
    prior_mean: tuple[float, float]  # (a, b) global, leídos del núcleo
    prior_sd: tuple[float, float]
    prior_sigma: float
    warnings: tuple[str, ...]


def _global_line(c, log_x: bool):
    """a y b de la correlación global evaluando el núcleo en dos puntos (sin copiar sus números)."""
    p1, p2 = (1.0, math.e) if log_x else (40.0, 60.0)  # dentro de la validez de todas (RMR′ > 23)
    r1, r2 = rm.correlate(c, p1), rm.correlate(c, p2)
    t1, t2 = (math.log(p1), math.log(p2)) if log_x else (p1, p2)
    a = (r2.value - r1.value) / (t2 - t1)
    return a, r1.value - a * t1, r1.info


def _pairs(history: History, kind: str):
    """Filas del ajuste: las mismas que cuenta la preparación del nivel 1 (`history._readiness`)."""
    rows = [t for t in history.tramos if all(getattr(t, c) is not None for c in _PAIRS[kind])
            and (kind != "rmr_from_q" or _pos(t.q_valor))]  # ln Q
    xs, ys = [], []
    for t in rows:
        if kind == "rmr_from_q":
            x, y = t.q_valor, t.rmr_valor
        elif kind == "gsi_from_rmr":
            x, y = t.rmr_valor, t.gsi_valor
        else:
            try:  # Q′ del núcleo: RQD < 10 se toma como 10 (NGI); jw = srf = 1 no entran en q_base
                x = rm.q_value(rm.QInput(t.rqd_pct, t.jn, t.jr, t.ja, 1.0, 1.0), rm.QEdition.NGI2025).q_base
            except ValueError as e:
                raise ValueError(f"Tramos row {t.fila}: cannot compute Q' from rqd_pct, jn, jr, ja: {e}") from None
            y = t.gsi_valor
        xs.append(float(x))
        ys.append(float(y))
    return rows, np.array(xs), np.array(ys)


def _edition(kind: str, rows) -> str | None:
    if kind == "gsi_from_q_prime":
        return None
    eds = Counter(_rmr_ed(t) for t in rows)
    bad = sum(v for k, v in eds.items() if k not in _RMR_EDITIONS)
    if bad:  # el valor no se repite: puede ser cualquier texto
        raise ValueError(f"{kind}: {bad} pair(s) have a missing or unsupported rmr_edicion; "
                         f"supported: {', '.join(_RMR_EDITIONS)}")
    if len(eds) > 1:
        counts = ", ".join(f"{k}: {v}" for k, v in sorted(eds.items()))
        raise ValueError(f"{kind}: rmr_edicion mixes editions ({counts}); RMR editions are not mixed in one fit, "
                         "filter the history to one edition")
    return next(iter(eds), "RMR89")


def _fit(kind, label, domain, rows, x, y, groups, edition, prior, deming_ratio, n_boot, seed):
    log_x = _LOG_X[kind]
    t = np.log(x) if log_x else x
    n, n_labors = len(rows), len({labor_key(r) for r in rows} - {None})
    warns = []
    (a_g, b_g), prior_sd, prior_sigma, info = prior
    # prior de b en el centro de los datos: con x lejos de 0 (RMR 20–80), priors independientes en x = 0 dejarían
    # el nivel de la curva en los datos fuertemente atado a la pendiente
    xc = float(t.mean())
    bayes = bayes_linear_fit(t - xc, y, prior_mean=(a_g, a_g * xc + b_g), prior_sd=prior_sd, prior_sigma=prior_sigma)
    ols = deming = boot = a_ci = b_ci = None
    status = "not_calibrated"
    if n_labors < MIN_LABORS_LEVEL1:
        warns.append(f"few labors: {n_labors} (needs {MIN_LABORS_LEVEL1})")
    if n < MIN_PAIRS_LEVEL1 or n_labors < MIN_LABORS_LEVEL1:
        warns.append(f"not calibrated to the site: {n} pairs from {n_labors} labors (needs {MIN_PAIRS_LEVEL1} "
                     f"from {MIN_LABORS_LEVEL1}); Bayesian fit only, close to the global correlation")
        deming_reason = "below the level-1 minimum"
    else:
        try:
            ols = ols_fit(t, y)
        except ValueError:
            warns.append("not calibrated to the site: x has no spread; Bayesian fit only")
        if ols is not None:
            boot = group_bootstrap(groups, lambda idx: (lambda f: (f.a, f.b))(ols_fit(t[idx], y[idx])),
                                   n_boot=n_boot, seed=seed)
            frac = boot.n_discarded / boot.n_boot
            if len(boot.replicates):
                (a_lo, b_lo), (a_hi, b_hi) = boot.percentile_ci(0.95)
                a_ci, b_ci = (float(a_lo), float(a_hi)), (float(b_lo), float(b_hi))
            tol = SLOPE_CI_REL_TOL * abs(ols.a)
            narrow = a_ci is not None and ols.a - tol <= a_ci[0] and a_ci[1] <= ols.a + tol
            status = "site" if narrow and frac <= MAX_DISCARDED_FRACTION else "unstable"
            if not narrow:
                warns.append(f"unstable: bootstrap 95 % CI of the slope wider than ±{SLOPE_CI_REL_TOL:.0%} "
                             "of the OLS slope")
            if frac > MAX_DISCARDED_FRACTION:
                warns.append(f"unstable: {boot.n_discarded} of {boot.n_boot} bootstrap replicates discarded "
                             f"(over {MAX_DISCARDED_FRACTION:.0%})")
        deming_reason = None
        if ols is None:
            deming_reason = "below the level-1 minimum"
        elif deming_ratio is None:
            deming_reason = ("deming_ratio not given: without the error-variance ratio the Deming line is "
                             "arbitrary (Carroll et al. 2006)")
        else:
            try:
                deming = deming_fit(t, y, deming_ratio)
            except ValueError as e:
                deming_reason = str(e)
    x_from, y_to = {"rmr_from_q": ("Q", edition), "gsi_from_rmr": (edition, "GSI"),
                    "gsi_from_q_prime": ("Q'", "GSI")}[kind]
    return SiteCorrelationFit(kind=kind, label=label, domain=domain, status=status, n=n, n_labors=n_labors,
                              x_min=float(x.min()), x_max=float(x.max()), x_from=x_from, y_to=y_to, log_x=log_x,
                              ols=ols, deming=deming, deming_reason=deming_reason, bootstrap=boot, a_ci=a_ci,
                              b_ci=b_ci, bayes=bayes, x_center=xc, prior_correlation=info.method_id,
                              warnings=tuple(warns))


def fit_site_correlation(history: History, kind: str, *, group_by: str | None = "litologia",
                         deming_ratio: float | None = None, prior_sd: tuple[float, float] | None = None,
                         prior_sigma: float | None = None, n_boot: int = 2000, seed: int = 0) -> SiteCorrelationResult:
    """Correlación propia del sitio por dominio y para toda la mina (nivel 1, R5).

    - `kind`: "rmr_from_q" (RMR = a·ln Q + b), "gsi_from_rmr" (GSI = a·RMR + b) o "gsi_from_q_prime"
      (GSI = a·ln Q′ + b, Q′ = RQD/Jn·Jr/Ja de los componentes, con el RQD < 10 tomado como 10).
    - `group_by`: atributo de `HistoryTramo` que define el dominio; None = solo la mina. Sin valor → "(no domain)".
    - `deming_ratio`: var(error de y)/var(error de x) en las unidades del ajuste (x = ln Q para Q y Q′).
    - `prior_sd` = (desviación de a, desviación del nivel de la curva en el centro de los datos); por defecto
      (50 % de |a global|, 10 puntos). `prior_sigma` = desviación residual a priori, por defecto 8.
    - Estados: "site" (≥ 30 pares de ≥ 5 labores e IC bootstrap de la pendiente dentro de ±25 % de la OLS, con a
      lo más 10 % de réplicas descartadas), "unstable" (cumple el mínimo pero no lo demás) y "not_calibrated"
      (bajo el mínimo: solo el bayesiano).
    """
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {', '.join(KINDS)}")
    if group_by is not None and (group_by == "fila" or group_by not in HistoryTramo.__dataclass_fields__):
        raise ValueError(f"group_by must be None or a HistoryTramo attribute, got '{group_by}'")
    if deming_ratio is not None:
        _positive("deming_ratio", deming_ratio)
    rows, x, y = _pairs(history, kind)
    if not rows:
        raise ValueError(f"{kind}: no complete pairs in the history")
    edition = _edition(kind, rows)
    corr = _GLOBAL[(kind, edition)]
    a_g, b_g, info = _global_line(corr, _LOG_X[kind])
    sd = prior_sd if prior_sd is not None else (PRIOR_SD_A_FRACTION * abs(a_g), PRIOR_SD_B_POINTS)
    sigma = PRIOR_SIGMA if prior_sigma is None else prior_sigma
    prior = ((a_g, b_g), sd, sigma, info)

    warns = []
    if kind == "gsi_from_rmr":
        warns.append(f"the global prior uses {edition}' (dry, no orientation adjustment); rmr_valor may include "
                     "the water and orientation ratings (not recorded), which shifts the site line")
    if kind != "gsi_from_rmr":
        q_eds = {re.sub(r"[\s-]", "", t.q_edicion).upper() for t in rows if t.q_edicion}
        if len(q_eds) > 1:
            warns.append(f"q_edicion mixes {len(q_eds)} editions; pairs from different Q table editions are pooled")
    unlabeled = sum(labor_key(t) is None for t in rows)
    if unlabeled:
        warns.append(f"{unlabeled} pair(s) without labor_codigo: each one is its own bootstrap group")
    # sin labor, cada fila es su propio grupo: no se puede saber con quién comparte dependencia
    groups = [labor_key(t) or (None, i) for i, t in enumerate(rows)]

    def fit(label, domain, idx):
        return _fit(kind, label, domain, [rows[i] for i in idx], x[idx], y[idx], [groups[i] for i in idx],
                    edition, prior, deming_ratio, n_boot, seed)

    mine = fit("mine", None, np.arange(len(rows)))
    domains = {}
    if group_by is not None:
        by: dict = {}
        for i, t in enumerate(rows):
            v = getattr(t, group_by)
            v = v.strip() if isinstance(v, str) else v
            by.setdefault(NO_DOMAIN if v is None or v == "" else v, []).append(i)
        keys = sorted(by, key=lambda k: (k == NO_DOMAIN, str(k)))
        domains = {k: fit(f"D{j + 1}", k, np.array(by[k])) for j, k in enumerate(keys)}
    return SiteCorrelationResult(kind=kind, group_by=group_by, mine=mine, domains=domains,
                                 prior_correlation=info.method_id, prior_verification=info.verification.name,
                                 prior_mean=(a_g, b_g), prior_sd=tuple(float(s) for s in sd),
                                 prior_sigma=float(sigma), warnings=tuple(warns))
