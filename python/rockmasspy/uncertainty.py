"""Incertidumbre en las clasificaciones (Fase 7, tarea 2): Monte Carlo / LHS sobre las entradas de RMR89, Q, GSI y
Hoek-Brown. Se informa, no se juzga: no cambia ninguna regla de atención. Los mensajes nunca repiten valores."""

from __future__ import annotations

import math
import statistics
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass

from . import _rockmasspy_core as rm
from .probabilistic import Distribution, sample_model

UNCERTAINTY_INFO = rm.MethodInfo(
    "Uncertainty-MC-LHS", rm.Verification.Secondary,
    "Hoek (2023) PRE ch. 9; sampling as in Probabilistic-MC-LHS")

_VARS = {"RMR89": ("ucs_mpa", "is50_mpa", "rqd_pct", "spacing_m", "joint_condition_rating"),
         "Q": ("rqd_pct", "jn", "jr", "ja", "jw", "srf"),
         "GSI": ("jcond89", "rqd_pct"),
         "HB": ("gsi", "mi", "d")}
_TABLE_METHOD = {"RMR89": "RMR", "Q": "Q", "GSI": "GSI"}


@dataclass(frozen=True)
class Summary:
    mean: float
    sd: float
    p05: float
    p50: float
    p95: float
    minimum: float
    maximum: float


@dataclass(frozen=True)
class UncertaintyResult:
    method: str
    sampling: str
    n: int
    seed: int
    n_valid: int
    variables: tuple[str, ...]
    outputs: dict[str, Summary]
    class_probabilities: dict[str, float]
    support_probabilities: dict[str, float]
    info: rm.MethodInfo
    warnings: tuple[str, ...]
    notes: tuple[str, ...]


def _summary(v) -> Summary:
    q = statistics.quantiles(v, n=20, method="inclusive") if len(v) > 1 else [v[0]] * 19
    return Summary(math.fsum(v) / len(v), statistics.stdev(v) if len(v) > 1 else 0.0, q[0],
                   statistics.median(v), q[-1], min(v), max(v))


def _missing(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


def classification_uncertainty(method: str, base, variables: Mapping[str, Distribution], *, table=None,
                               edition=None, n: int = 5000, sampling: str = "lhs",
                               seed: int = 1) -> UncertaintyResult:
    if method not in _VARS:
        raise ValueError(f"method must be one of: {', '.join(_VARS)}")
    allowed = _VARS[method]
    for name in variables:
        if name not in allowed:
            raise ValueError(f"unknown variable '{name}'; allowed: {', '.join(allowed)}")
    if not variables:
        raise ValueError("at least one variable is required")
    if table is not None:
        if method == "HB":
            raise ValueError("HB does not take a table")
        if not hasattr(table, "table") or getattr(table.table, "method", None) != _TABLE_METHOD[method]:
            raise ValueError(f"the table must be a {_TABLE_METHOD[method]} range table of a LaborTable")
    if method == "RMR89":
        if not isinstance(base, rm.Rmr89Input):
            raise ValueError("base must be an Rmr89Input for method 'RMR89'")
        get = lambda k: getattr(base, k)  # noqa: E731
    elif method == "Q":
        if not isinstance(base, rm.QInput):
            raise ValueError("base must be a QInput for method 'Q'")
        get = lambda k: getattr(base, k)  # noqa: E731
    else:
        if not isinstance(base, Mapping) or set(base) != set(allowed):
            raise ValueError(f"base must be a dict with the keys: {', '.join(allowed)}")
        get = base.get
    for name in variables:
        if _missing(get(name)):
            raise ValueError(f"variable '{name}' is sampled but the base has no value for it")
    if method == "Q" and edition is None:
        edition = rm.QEdition.NGI2025
    out_key = {"RMR89": "rmr", "Q": "q", "GSI": "gsi"}.get(method)
    labels = [c.label for c in table.table.classes] if table is not None else []
    counts, supports = Counter(), Counter()
    work = rm.Rmr89Input() if method == "RMR89" else None
    if work is not None:  # copia de trabajo: la base no se toca
        for k in ("application", "functions", "is50_mpa", "joint_condition", "joint_condition_rating",
                  "orientation", "rqd_pct", "spacing_m", "ucs_mpa", "water"):
            setattr(work, k, getattr(base, k))

    def one(draw):
        vals = {k: get(k) for k in allowed}
        vals.update(draw)
        if method == "RMR89":
            for k, v in draw.items():
                setattr(work, k, v)
            r = rm.rmr89(work)
            outs, ws = {"rmr": r.rmr}, list(r.warnings)
        elif method == "Q":
            r = rm.q_value(rm.QInput(*(vals[k] for k in allowed)), edition)
            outs, ws = {"q": r.q}, list(r.warnings)
        elif method == "GSI":
            outs, ws = {"gsi": rm.gsi_from_jcond89_rqd(vals["jcond89"], vals["rqd_pct"]).gsi}, []
        else:
            r = rm.hb_params(vals["gsi"], vals["mi"], vals["d"])
            outs, ws = {"mb": r.mb, "s": r.s, "a": r.a}, []
        if table is not None:
            v = outs[out_key]
            try:
                c = table.classify(v)
            except ValueError:
                raise ValueError("a sampled result falls outside every class of the table; "
                                 "widen the table or narrow the variables") from None
            counts[c.label] += 1
            if c.support is not None:
                supports[c.support.code] += 1
            ws += c.warnings
        return outs, ws

    ms = sample_model(one, variables, n=n, sampling=sampling, seed=seed)
    k = ms.n_valid
    notes = list(ms.notes)
    if not k:
        notes.append("no valid samples")
    return UncertaintyResult(
        method, sampling, n, seed, k, tuple(sorted(variables)), {name: _summary(v) for name, v in ms.outputs.items()},
        {lb: counts[lb] / k for lb in labels} if k else {}, {c: m / k for c, m in sorted(supports.items())} if k else {},
        UNCERTAINTY_INFO, ms.warnings, tuple(notes))
