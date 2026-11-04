"""Motor de verificación: revisa objetos de RockMassPy contra un perfil normativo.

Lista lo que cumple, lo que no y lo que no puede revisar. Nunca dice «aprobado»: un hallazgo es una lectura de
los datos dados contra el texto del ítem. Un hallazgo por requisito, siempre (nada desaparece en silencio).
Los mensajes van en inglés (R25) y solo llevan conteos y valores del ítem; nunca identificadores de fila.
"""
from __future__ import annotations

import datetime
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from types import SimpleNamespace

from .batch import TramoResult
from .design_inputs import DesignInputs
from .labor_table import LaborTable, _key
from .normative import NormativeProfile, NormItem, _check_date
from .stope_surfaces import StopeSurfaceResult

STATUSES = ("complies", "does_not_comply", "attention", "note", "not_checked", "not_verifiable")


@dataclass(frozen=True)
class Finding:
    item: NormItem
    status: str
    message: str


@dataclass(frozen=True)
class VerificationResult:
    profile: NormativeProfile
    as_of: str
    findings: tuple[Finding, ...]

    def counts(self) -> dict[str, int]:
        c = Counter(f.status for f in self.findings)
        return {s: c.get(s, 0) for s in STATUSES}

    @property
    def exit_code(self) -> int:
        return 2 if any(f.status in ("does_not_comply", "attention") for f in self.findings) else 0


_OPS = {">": lambda a, b: a > b, ">=": lambda a, b: a >= b, "<": lambda a, b: a < b, "<=": lambda a, b: a <= b}


def _meets(measured, comparison: str, value) -> bool:
    """Compara en fracciones exactas (R8): 1.5, 1 % y 30 m no cambian de estado por redondeo binario."""
    return _OPS[comparison](Fraction(str(measured)), Fraction(str(value)))


def _fail(item: NormItem) -> str:
    return "does_not_comply" if item.force == "law" else "attention"  # R6


def _limit(item: NormItem) -> str:
    return f"{item.comparison} {item.value:g} {item.unit}"


def _missing(what: str):
    return "not_checked", f"no {what} given"


def _count_rule(item, rows, ok, thing: str, why: str):
    """`k of n <cosa> <motivo> (<límite>)` si alguna fila no cumple; si no, `complies`."""
    bad = sum(not ok(r) for r in rows)
    if bad:
        return _fail(item), f"{bad} of {len(rows)} {thing} {why} ({_limit(item)})"
    return "complies", f"all {len(rows)} {thing} meet the requirement ({_limit(item)})"


# --- reglas ---

def _none(item, ctx):
    return "not_verifiable", "procedural requirement; the library cannot check it"


_TAIL_TABLE = "posting in the labor is a separate item"


def _table_content(item, ctx):
    if not ctx.tables:
        return _missing("tables")
    reasons: Counter = Counter()
    bad = 0
    for lt in ctx.tables:
        r = set()
        if lt.span_m is None:
            r.add("without span range")
        kinds = {i.kind for i in lt.validate()}
        r.update(k.replace("_", " ") for k in ("no_support", "unknown_support", "missing_cell") if k in kinds)
        bad += bool(r)
        reasons.update(r)
    n = len(ctx.tables)
    if bad:
        why = ", ".join(f"{k}: {v}" for k, v in sorted(reasons.items()))
        return _fail(item), f"{bad} of {n} tables incomplete ({why}); {_TAIL_TABLE}"
    return "complies", f"all {n} tables have rock quality, support and span; {_TAIL_TABLE}"


def _span_within_table(item, ctx):
    if not ctx.results:
        return _missing("results")
    if not ctx.tables:
        return _missing("tables")
    inside = outside = unjudged = 0
    for r in ctx.results:
        luz = r.tramo.luz_m
        spans = [lt.span_m for lt in ctx.tables if _key(lt.labor_type) == _key(r.tramo.tipo_labor)
                 and lt.span_m is not None]
        if luz is None or not spans:
            unjudged += 1
        elif any(lo <= luz <= hi for lo, hi in spans):
            inside += 1
        else:
            outside += 1
    msg = f"span within table range: within {inside}, outside {outside}, not judged {unjudged}; height is not checked"
    if outside:
        return _fail(item), msg
    return ("attention" if unjudged else "complies"), msg


def _empirical(item, ctx):
    if not ctx.results and not ctx.stopes:
        return _missing("results or stope faces")
    n = len(ctx.results)
    done = sum(r.label is not None for r in ctx.results)
    ref = sum(r.q_chart is not None for r in ctx.results)
    zones = sum(s.mathews.reading.zone in (2, 3) for s in ctx.stopes)
    msg = (f"classified {done} of {n} tramos, {ref} with a Q chart reference; "
           f"{len(ctx.stopes)} faces evaluated with Mathews, {zones} faces in zone 2 or 3")
    return ("attention" if done < n else "complies"), msg


def _numbers(report):
    out = {}

    def walk(sections):
        for s in sections:
            out[s.number] = s
            walk(b for b in s.blocks if hasattr(b, "number") and hasattr(b, "blocks"))
    walk(report.sections)
    return out


_REQUIRED = ("1", "2", "3", "4", "5", "6", "4.1", "4.2", "4.3")
_TAIL_REPORT = "the summary memoria covers only the RockMassPy parameters and the file copy is not reviewed"


def _anexo39b(item, ctx):
    if ctx.report is None:
        return _missing("report")
    secs = _numbers(ctx.report)
    missing = [n for n in _REQUIRED if n not in secs]
    if missing:
        return _fail(item), f"sections missing: {', '.join(missing)}; {_TAIL_REPORT}"
    todo = [n for n in _REQUIRED if secs[n].to_complete]
    if todo:
        return "attention", f"sections to complete: {', '.join(todo)}; {_TAIL_REPORT}"
    return "complies", f"all required sections are present and filled; {_TAIL_REPORT}"


def _refuge(check):
    def rule(item, ctx):
        rows = ctx.design.refuge_stations if ctx.design else ()
        if not rows:
            return _missing("refuge stations")
        return check(item, rows)
    return rule


def _rock_quality(item, rows):
    return _count_rule(item, rows, lambda s: s.sostenido or _meets(s.rmr, item.comparison, item.value),
                       "stations", "lack the rock quality or declared support")


def _distance(item, rows):
    return _count_rule(item, rows, lambda s: _meets(s.distancia_frente_m, item.comparison, item.value),
                       "stations", "are too far from the face")


def _area(item, rows):
    return _count_rule(item, rows, lambda s: _meets(Fraction(str(s.area_m2)) / s.aforo, item.comparison, item.value),
                       "stations", "have too little area per person")


def _walkway(item, ctx):
    rows = [r for r in (ctx.design.pedestrian_refuges if ctx.design else ())
            if (r.via if r.via != "rampa" else f"rampa:{r.geometria}") in item.applies_to]
    if not rows:
        return _missing("pedestrian refuge spacing for this item")
    return _count_rule(item, rows, lambda r: _meets(r.espaciado_max_m, item.comparison, item.value),
                       "roads", "have refuges too far apart")


def _qc(item, ctx):
    rows = ctx.design.qc if ctx.design else ()
    if not rows:
        return _missing("quality control summary")
    rows = [q for q in rows if q.instalados > 0]
    if not rows:
        return "note", "no month and support type has installed units; nothing to compare"
    bad = sum(not _meets(Fraction(q.ensayados * 100, q.instalados), item.comparison, item.value) for q in rows)
    if bad:
        return _fail(item), f"{bad} of {len(rows)} month and support pairs are below the tested share ({_limit(item)})"
    return "complies", f"all {len(rows)} month and support pairs meet the tested share ({_limit(item)})"


def _fs(item, ctx):
    rows = [f for f in (ctx.design.safety_factors if ctx.design else ()) if f.plazo in item.applies_to]
    if not rows:
        return _missing("safety factors for this item")
    return _count_rule(item, rows, lambda f: _meets(f.fs, item.comparison, item.value),
                       "safety factors", "are below the guide value")


def _standup(item, ctx):
    rows = ctx.design.standup if ctx.design else ()
    if not rows:
        return _missing("stand-up times")
    low = sum(_meets(s.autosoporte_h, item.comparison, item.value) for s in rows)
    if low:
        return "attention", (f"{low} of {len(rows)} stand-up times are at or below {item.value:g} {item.unit}; "
                             "apply art. 213 (labor avanzada, labor sostenida)")
    return "note", f"none of {len(rows)} stand-up times is at or below {item.value:g} {item.unit}"


_RULES = {
    "none": _none, "table_content": _table_content, "span_within_table": _span_within_table,
    "empirical_calculation": _empirical, "anexo39b_structure": _anexo39b,
    "refuge_rock_quality": _refuge(_rock_quality), "refuge_distance": _refuge(_distance),
    "refuge_area_per_person": _refuge(_area), "walkway_spacing": _walkway, "qc_ratio": _qc, "fs_minimum": _fs,
    "standup_time": _standup,
}


def _pseudostatic(item, ctx):
    """art. 264 (PE-264) con la misma regla de `criteria`: un análisis global con kh > 0 y Tr >= valor."""
    from .criteria import _assigner, _pseudostatic_present, criteria_assignments, return_periods

    status, reason = _pseudostatic_present(item, ctx.le, _assigner(criteria_assignments(le=ctx.le)),
                                           return_periods(ctx.le))
    if status == "meets":
        return "complies", (f"a pseudo-static analysis of the overall slope is given with a return period "
                            f"{_limit(item)}; the library does not derive kh from the seismic hazard")
    return (_fail(item) if status == "fails" else "not_verifiable"), reason


_RULES["pseudostatic_analysis_present"] = _pseudostatic
# los demás criterios de aceptación de taludes se evalúan con rockmasspy.criteria.assess_criteria, no aquí
_RULES.update(dict.fromkeys(
    ("slope_fs_static", "slope_fs_pseudostatic", "slope_pof", "berm_reliability", "deformation_required"),
    lambda item, ctx: ("not_verifiable", "slope acceptance criterion; evaluate it with assess_criteria")))


def verify(profile: NormativeProfile, *, as_of: str | None = None, tables: Sequence[LaborTable] = (),
           results: Sequence[TramoResult] = (), stopes: Sequence[StopeSurfaceResult] = (),
           design: DesignInputs | None = None, report=None, le: Sequence = ()) -> VerificationResult:
    """Un hallazgo por requisito, en el orden del perfil. Un incumplimiento nunca lanza; solo los datos imposibles.

    `le`: resultados de `assess_le` (3C/3D), para el art. 264 (`pseudostatic_analysis_present`), con la escala y el
    período de retorno de cada análisis."""
    as_of = datetime.date.today().isoformat() if as_of is None else _check_date(as_of, "as_of")
    ctx = SimpleNamespace(tables=tuple(tables), results=tuple(results), stopes=tuple(stopes), design=design,
                          report=report, le=tuple(le))
    findings = []
    for iid in profile.item_ids():
        if profile.versions(iid)[0].check == "esr":  # parámetro, no requisito
            continue
        item = profile.version(iid, as_of)
        if item is None:
            vs = profile.versions(iid)
            last = max(vs, key=lambda i: i.effective_from)
            nxt = min((i for i in vs if i.effective_from > as_of), key=lambda i: i.effective_from, default=None)
            if nxt is None:
                tail = f"the loaded text ended on {last.effective_to}"
                nxt = last
            else:
                tail = f"the loaded text applies from {nxt.effective_from}"
            findings.append(Finding(nxt, "not_verifiable",
                                    f"no text of this item in force on {as_of} is loaded; {tail}"))
            continue
        status, msg = _RULES[item.check](item, ctx)
        findings.append(Finding(item, status, msg))
    return VerificationResult(profile, as_of, tuple(findings))
