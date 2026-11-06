"""Nivel 1: correlaciones propias del sitio (Fase 4A, tarea 6; plan R5, R6, R13 y R14).

Ajusta RMR = a·ln Q + b, GSI = a·RMR + b o GSI = a·ln Q′ + b por dominio (`group_by`, por defecto la litología;
Somodi et al. 2021) y para toda la mina, con los métodos de `stats.py`: OLS con intervalo de predicción (la que
predice), Deming solo con la razón de varianzas de error, bootstrap por labor y bayesiano con la correlación global
del núcleo como *prior* (`docs/investigacion/MODELOS_SOSTENIMIENTO.md` §2.2). Los pares salen de
`history.level1_rows`, la misma selección que cuenta la preparación del nivel 1.

Privacidad (R13): el valor del dominio (la litología) solo va como clave de `SiteCorrelationResult.domains`, para la
tabla de resultados. Los avisos, el `name` y el `source` de la `CustomCorrelation` llevan códigos genéricos («D1»),
conteos y métodos, nunca un valor de una columna de identificación ni la litología.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .. import _rockmasspy_core as rm
from ..batch import write_table
from ..history import (LEVEL1_KINDS, LEVEL1_RMR_EDITIONS, MIN_LABORS_LEVEL1, MIN_PAIRS_LEVEL1, History,
                       check_group_by, labor_key, level1_rows)
from ..table_io import correlation_to_dict
from .stats import (BayesLinearFit, BootstrapResult, DemingFit, OlsFit, _positive, bayes_linear_fit, deming_fit,
                    group_bootstrap, ols_fit)

KINDS = LEVEL1_KINDS
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
    prior_verification: str  # su marca en el núcleo (Primary, Secondary…), R14
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

    def to_custom_correlation(self) -> rm.CustomCorrelation | None:
        """CustomCorrelation para las tablas por labor (1B) y `plot_correlation` (1C), o None si no se puede armar:
        con un solo valor de x observado no hay rango de validez (valid_min < valid_max).

        El nombre y el `source` solo llevan el código genérico, conteos, método y estado (R13); con el bayesiano,
        también el prior y su marca de verificación (R14).
        """
        if not self.x_min < self.x_max:
            return None
        form = rm.CorrelationForm.LogLinear if self.log_x else rm.CorrelationForm.Linear
        prior = f", prior {self.prior_correlation} ({self.prior_verification})" if self.method == "Bayesian" else ""
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
    below = n < MIN_PAIRS_LEVEL1 or n_labors < MIN_LABORS_LEVEL1
    if n_labors < MIN_LABORS_LEVEL1:
        warns.append(f"few excavations: {n_labors} (needs {MIN_LABORS_LEVEL1})")
    if below:
        warns.append(f"not calibrated to the site: {n} pairs from {n_labors} excavations (needs {MIN_PAIRS_LEVEL1} "
                     f"from {MIN_LABORS_LEVEL1}); Bayesian fit only, close to the global correlation")
    else:
        try:
            ols = ols_fit(t, y)
        except ValueError:
            warns.append("not calibrated to the site: x has no spread; Bayesian fit only")
    if ols is not None:
        def slope_intercept(idx):
            f = ols_fit(t[idx], y[idx])
            return f.a, f.b

        boot = group_bootstrap(groups, slope_intercept, n_boot=n_boot, seed=seed)
        frac = boot.n_discarded / boot.n_boot
        if len(boot.replicates):
            (a_lo, b_lo), (a_hi, b_hi) = boot.percentile_ci(0.95)
            a_ci, b_ci = (float(a_lo), float(a_hi)), (float(b_lo), float(b_hi))
        tol = SLOPE_CI_REL_TOL * abs(ols.a)
        narrow = a_ci is not None and ols.a - tol <= a_ci[0] and a_ci[1] <= ols.a + tol
        same_sign = np.sign(ols.a) == np.sign(a_g)
        status = "site" if narrow and same_sign and frac <= MAX_DISCARDED_FRACTION else "unstable"
        if not narrow:
            warns.append(f"unstable: bootstrap 95 % CI of the slope wider than ±{SLOPE_CI_REL_TOL:.0%} "
                         "of the OLS slope")
        if frac > MAX_DISCARDED_FRACTION:
            warns.append(f"unstable: {boot.n_discarded} of {boot.n_boot} bootstrap replicates discarded "
                         f"(over {MAX_DISCARDED_FRACTION:.0%})")
        if not same_sign:
            warns.append("unstable: slope sign opposite to the global correlation; check the data")
    if deming_ratio is None:
        deming_reason = ("deming_ratio not given: without the error-variance ratio the Deming line is "
                         "arbitrary (Carroll et al. 2006)")
    elif below:
        deming_reason = "below the level-1 minimum"
    elif ols is None:
        deming_reason = "x has no spread: no regression is possible"
    else:
        deming_reason = None
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
                              prior_verification=info.verification.name, warnings=tuple(warns))


def fit_site_correlation(history: History, kind: str, *, group_by: str | None = "litologia",
                         rmr_edition: str | None = None, deming_ratio: float | None = None,
                         prior_sd: tuple[float, float] | None = None, prior_sigma: float | None = None,
                         n_boot: int = 2000, seed: int = 0) -> SiteCorrelationResult:
    """Correlación propia del sitio por dominio y para toda la mina (nivel 1, R5).

    - `kind`: "rmr_from_q" (RMR = a·ln Q + b), "gsi_from_rmr" (GSI = a·RMR + b) o "gsi_from_q_prime"
      (GSI = a·ln Q′ + b, Q′ = RQD/Jn·Jr/Ja de los componentes, con el RQD < 10 tomado como 10).
    - `group_by`: atributo de `HistoryTramo` que define el dominio; None = solo la mina. Sin valor → "(no domain)".
    - `rmr_edition`: edición de RMR que entra al ajuste (RMR76 o RMR89); None = la mayoritaria. Las ediciones no
      se mezclan: las filas de otra edición o sin edición quedan fuera, con aviso.
    - `deming_ratio`: var(error de y)/var(error de x) en las unidades del ajuste (x = ln Q para Q y Q′).
    - `prior_sd` = (desviación de a, desviación del nivel de la curva en el centro de los datos); por defecto
      (50 % de |a global|, 10 puntos). `prior_sigma` = desviación residual a priori, por defecto 8.
    - Estados: "site" (≥ 30 pares de ≥ 5 labores, IC bootstrap de la pendiente dentro de ±25 % de la OLS, a lo
      más 10 % de réplicas descartadas y pendiente con el signo de la global), "unstable" (cumple el mínimo pero
      no lo demás) y "not_calibrated" (bajo el mínimo: solo el bayesiano).
    """
    check_group_by(group_by)
    if deming_ratio is not None:
        _positive("deming_ratio", deming_ratio)
    sel = level1_rows(history, kind, rmr_edition=rmr_edition)  # valida kind y rmr_edition
    rows, x, y = sel.tramos, np.array(sel.x), np.array(sel.y)
    if not rows:
        need = f" with rmr_edicion {' or '.join(LEVEL1_RMR_EDITIONS)}" if kind != "gsi_from_q_prime" else ""
        raise ValueError(f"{kind}: no usable pairs{need} in the history")
    a_g, b_g, info = _global_line(_GLOBAL[(kind, sel.edition)], _LOG_X[kind])
    sd = prior_sd if prior_sd is not None else (PRIOR_SD_A_FRACTION * abs(a_g), PRIOR_SD_B_POINTS)
    sigma = PRIOR_SIGMA if prior_sigma is None else prior_sigma
    prior = ((a_g, b_g), sd, sigma, info)

    warns = []
    if sel.excluded_edition:
        warns.append(f"{sel.excluded_edition} pair(s) excluded: rmr_edicion missing or other than {sel.edition}; "
                     "RMR editions are not mixed in one fit")
    if sel.excluded_x:  # gsi_from_rmr no excluye por x
        what = "Q <= 0" if kind == "rmr_from_q" else "Q' components out of range"
        warns.append(f"{sel.excluded_x} pair(s) excluded: {what}")
    if kind == "gsi_from_rmr":
        warns.append(f"the global prior uses {sel.edition}' (dry, no orientation adjustment); rmr_valor may include "
                     "the water and orientation ratings (not recorded), which shifts the site line")
        # Fase 5B: el error de mapeo de la condición de juntas y el RQD entra en x y en y a la vez
        quantified = sum((t.gsi_tabla or "").strip().casefold().startswith("gsi cuantificado") for t in rows)
        warns.append("GSI and RMR share components (joint condition and RQD): their mapping errors are correlated, "
                     "so the CI of the slope is optimistic when the mapping is noisy"
                     + (f"; {quantified} pair(s) use the quantified GSI (Hoek et al. 2013), computed from those "
                        "same ratings" if quantified else ""))
    else:
        q_eds = {t.q_edicion.strip().casefold() for t in rows if t.q_edicion}
        if len(q_eds) > 1:
            warns.append(f"q_edicion mixes {len(q_eds)} editions; pairs from different Q table editions are pooled")
    unlabeled = sum(labor_key(t) is None for t in rows)
    if unlabeled:
        warns.append(f"{unlabeled} pair(s) without labor_codigo: each one is its own bootstrap group")
    # sin labor, cada fila es su propio grupo: no se puede saber con quién comparte dependencia
    groups = [labor_key(t) or (None, i) for i, t in enumerate(rows)]

    def fit(label, domain, idx):
        return _fit(kind, label, domain, [rows[i] for i in idx], x[idx], y[idx], [groups[i] for i in idx],
                    sel.edition, prior, deming_ratio, n_boot, seed)

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


CORRELATION_RESULT_COLUMNS = ("par", "etiqueta", "dominio", "n", "labores", "estado", "metodo", "a", "b",
                              "a_ic95_inf", "a_ic95_sup", "b_ic95_inf", "b_ic95_sup", "x_min", "x_max", "desde",
                              "hacia", "prior", "avisos")


def save_site_correlations(results, folder) -> tuple[Path, Path]:
    """Escribe `site_correlations.csv` y `site_correlations.json` en `folder` (la crea si falta).

    `results`: un `SiteCorrelationResult` o una secuencia de ellos; un par que no se pudo ajustar va como la tupla
    (tipo, razón) y queda en el CSV con estado `not_fitted`. El CSV lleva todos los ajustes con su estado (y el
    dominio: es un archivo de resultados). El JSON, en el formato `correlations` de las tablas por labor, lleva solo
    los ajustes con estado `site`: los `unstable` y `not_calibrated` no se pegan en una tabla.
    """
    if isinstance(results, SiteCorrelationResult):
        results = (results,)
    out = Path(folder)
    out.mkdir(parents=True, exist_ok=True)
    rows, corrs = [], []
    for r in results:
        if isinstance(r, tuple):
            rows.append((r[0], *[None] * 4, "not_fitted", *[None] * 12, r[1]))
            continue
        for f in (r.mine, *r.domains.values()):
            a_ci, b_ci = (f.a_ci, f.b_ci) if f.method == "OLS" else (None, None)
            rows.append((r.kind, f.label, f.domain, f.n, f.n_labors, f.status, f.method, f.a, f.b,
                         *(a_ci or (None, None)), *(b_ci or (None, None)), f.x_min, f.x_max, f.x_from, f.y_to,
                         r.prior_correlation, "; ".join((*r.warnings, *f.warnings))))
            c = f.to_custom_correlation() if f.status == "site" else None
            if c is not None:
                corrs.append(correlation_to_dict(c))
    csv_path = write_table(out / "site_correlations.csv", CORRELATION_RESULT_COLUMNS, rows)
    js = out / "site_correlations.json"
    js.write_text(json.dumps({"correlations": corrs}, indent=2, ensure_ascii=False), encoding="utf-8")
    return csv_path, js
