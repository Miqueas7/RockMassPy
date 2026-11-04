"""Criterios de aceptación de taludes: compara bloques (3B) y análisis LE (3C) con un perfil de criterios (3D).

Cada objeto lleva una escala y una consecuencia (`assignments`). Por cada regla del perfil que aplica al tipo de
objeto sale un chequeo: `meets`, `fails` o `not_verifiable`, con el criterio, su fuente, su fuerza y su marca.
Nunca dice «aprobado». Una sola regla de atención: un `fails` (R10); `not_verifiable` es nota.
El estado sigue el comparador (R2): un FS igual al mínimo cumple con «>=» y una PoF igual al máximo con «<=»;
la comparación es exacta en decimales, así que 1.2 - 1e-12 no cumple «>= 1.2».
Los ids van solo al archivo de resultados; las razones van en inglés y sin valores ni ids.
"""
from __future__ import annotations

import datetime
import math
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

from .batch import write_table
from .blocks import BlockResult
from .excel_io import _where
from .limit_equilibrium import LeAnalysisResult, le_fs, le_static_fs
from .normative import (CONSEQUENCES, RANGE_POLICIES, SCALES, NormativeProfile, NormItem, _check_date)
from .slopes import _cargar, _rango
from .verify import _OPS

CRITERIA_STATUSES = ("meets", "fails", "not_verifiable")
CRITERIA_SHEET = "Criterios"
CRITERIA_COLUMNS = ("escala", "consecuencia", "fs_estatico_min", "fs_seudoestatico_min", "pof_max_pct",
                    "confiabilidad_berma_min_pct", "fuente")
# reglas que se miran en cada tipo de objeto
_KIND_RULES = {"block": ("slope_fs_static", "slope_pof", "slope_fs_pseudostatic"), "berm": ("berm_reliability",),
               "le": ("slope_fs_static", "slope_fs_pseudostatic", "deformation_required")}
NOT_IN_FORCE = "profile not in force on the evaluation date"
NOT_APPLICABLE = "the guideline sets no minimum for this consequence (not applicable)"


@dataclass(frozen=True)
class CriterionCheck:
    object_kind: str  # block, berm, le o le_set (el conjunto de análisis, para pseudostatic_analysis_present)
    object_id: str = field(repr=False)
    order: int
    item_id: str
    rule: str
    required: float | None
    comparison: str | None
    obtained: float | None
    status: str
    reason: str
    source: str = field(repr=False)
    force: str
    verification: str
    range_used: str | None

    @property
    def needs_attention(self) -> bool:
        return self.status == "fails"


def _ok(x, comparison, value) -> bool:
    """Exacta en decimales (como la 2C, R8); ±inf se compara como float."""
    if isinstance(x, float) and math.isinf(x):
        return _OPS[comparison](x, value)
    return _OPS[comparison](Fraction(str(x)), Fraction(str(value)))


def _threshold(item: NormItem, policy: str):
    """(valor usado, texto del rango o None) según la política (R1)."""
    if item.value_range is None:
        return item.value, None
    a, b = item.value_range
    if policy == "conservative":
        policy = "upper" if item.comparison in (">", ">=") else "lower"
    return (b if policy == "upper" else a), f"{policy} of {a:g}-{b:g}"


def _matches(item: NormItem, scale, cons) -> bool:
    for key in item.applies_to:
        s, _, c = key.partition(":")
        if (s == "*" or s == scale) and (c == "*" or c == cons):
            return True
    return False


def _no_match_reason(items, scale, cons) -> str:
    keys = [k.partition(":") for i in items for k in i.applies_to]
    if scale is None and not any(s == "*" for s, _, _ in keys):
        return "no scale assigned"
    if not any(s in ("*", scale) for s, _, _ in keys):
        return "the profile has no criterion for this scale"
    if cons is None:
        return "no consequence assigned"
    return "the profile has no criterion for this consequence"


def _word(v, what):
    if v is None:
        return None
    if not isinstance(v, str):
        raise ValueError(f"assignments: {what} must be text")
    return v.strip().casefold() or None  # una palabra fuera de la lista se juzga en assess_criteria


def _unknown(scale, cons) -> str:
    """Razón «no verificable» si la escala o la consecuencia no es de la lista (sin repetir el texto del usuario)."""
    if scale is not None and scale not in SCALES:
        return "unknown scale"
    if cons is not None and cons not in CONSEQUENCES:
        return "unknown consequence"
    return ""


def _finite(x) -> bool:
    return x is not None and not (isinstance(x, float) and math.isnan(x))


def _pct(fraction) -> Fraction:
    return Fraction(str(fraction)) * 100  # 0.1 da 10 exacto, no 10.000000000000002


# --- qué se compara: (obtenido o None, razón si falta, nota si hay) ---

def _block_value(rule, r: BlockResult):
    if rule in ("slope_fs_static", "slope_pof") and r.kh > 0:  # el FS y la PoF de la fila son seudoestáticos
        return None, "block analysed with kh: no static FS or PoF", ""
    if rule in ("slope_fs_static", "slope_fs_pseudostatic"):
        return (r.fs, "", "") if _finite(r.fs) else (None, "no deterministic FS", "")
    if rule == "slope_pof":
        p = r.probabilistic
        if p is None:
            return None, "no probabilistic analysis", ""
        if not _finite(p.pof):
            return None, "no valid probabilistic samples", ""
        return _pct(p.pof), "", ""
    b = r.berm  # berm_reliability
    if b is None or b.reliability is None:
        return None, "berm reliability not evaluated", ""
    return _pct(b.reliability.reliability), "", ""


def _lowest(values, what):
    fs = [x for x in values if _finite(x)]
    if not fs:
        return None, f"no {what}", ""
    return min(fs), "", (f"lowest of {len(fs)} methods" if len(fs) > 1 else "")


def _pseudo(r: LeAnalysisResult) -> bool:
    return r.kh is not None and r.kh > 0


def _le_value(rule, r: LeAnalysisResult):
    if rule == "slope_fs_static":
        return _lowest(le_static_fs(r), "static FS")
    if not _pseudo(r):
        return None, "no pseudo-static analysis", ""
    return _lowest(le_fs(r), "pseudo-static FS")


def _check(kind, oid, order, item, policy, obtained, reason, note, newmark=None):
    required, rng = _threshold(item, policy)
    if obtained is None:
        status = "not_verifiable"
    elif item.check == "deformation_required":
        if _ok(obtained, item.comparison, required):  # FS seudoestático bajo el valor: se exige deformación
            status, note = ("meets", "deformation analysis required and given") if newmark else \
                           ("fails", "deformation analysis required and missing")
        else:
            status, note = "meets", "deformation analysis not required"
    else:
        status = "meets" if _ok(obtained, item.comparison, required) else "fails"
    return CriterionCheck(kind, oid, order, item.item_id, item.check, required, item.comparison,
                          None if obtained is None else float(obtained), status, reason or note,
                          _source(item), item.force, item.verification, rng)


def _source(item: NormItem) -> str:
    return ", ".join(x for x in (item.instrument, item.article, f"p. {item.page}" if item.page else "") if x)


def _empty(kind, oid, order, rule, items, reason):
    """«no verificable» sin ítem: la fuente es la de los ítems de la regla, sin repetir."""
    first = items[0]
    return CriterionCheck(kind, oid, order, "", rule, None, None, None, "not_verifiable", reason,
                          "; ".join(dict.fromkeys(map(_source, items))), first.force, first.verification, None)


def _assigner(assignments: Mapping):
    """(tipo, id) -> (escala, consecuencia) normalizadas; vacía o ausente = None."""
    def assign(key):
        v = assignments.get(key)
        if v is None:
            return None, None
        if isinstance(v, str) or len(v) != 2:
            raise ValueError("assignments: each value must be a pair (scale, consequence)")
        return _word(v[0], "scale"), _word(v[1], "consequence")
    return assign


def criteria_assignments(blocks: Iterable[BlockResult] = (),
                         le: Iterable[LeAnalysisResult] = ()) -> dict:
    """El `assignments` de `assess_criteria`, de las columnas `escala` y `consecuencia` de `Bloques` y `Analisis_LE`."""
    out = {("berm" if r.model == "berm" else "block", r.id_bloque): (r.escala, r.consecuencia) for r in blocks}
    out.update({("le", r.id_analisis): (r.escala, r.consecuencia) for r in le})
    return out


def return_periods(le: Iterable[LeAnalysisResult]) -> dict:
    """El `return_periods` de `assess_criteria`: {id_analisis: periodo_retorno_anios} de los análisis que lo dan."""
    return {r.id_analisis: r.periodo_retorno_anios for r in le if r.periodo_retorno_anios is not None}


def _pseudostatic_present(item, le, assign, return_periods):
    """art. 264 (también la usa `verify` con PE-264): algún análisis global con kh > 0 y Tr >= valor."""
    if not le:
        return "not_verifiable", "no limit equilibrium analyses given"
    scales = [assign(("le", r.id_analisis))[0] for r in le]
    glob = [r for r, s in zip(le, scales) if s == "global" and _pseudo(r)]
    tr = [return_periods.get(r.id_analisis) for r in glob]
    if any(t is not None and _ok(t, item.comparison, item.value) for t in tr):
        return "meets", ""
    if any(t is None for t in tr):
        return "not_verifiable", "return period not given for a pseudo-static overall analysis"
    if not glob and any(s is None for s in scales):
        return "not_verifiable", "no scale assigned"
    if not glob and any(s not in SCALES for s in scales):
        return "not_verifiable", "unknown scale"
    return "fails", "no pseudo-static analysis of the overall slope with the required return period"


def assess_criteria(profile: NormativeProfile, *, blocks: Iterable[BlockResult] = (),
                    le: Iterable[LeAnalysisResult] = (), assignments: Mapping, range_policy: str | None = None,
                    return_periods: Mapping | None = None, as_of: str | None = None) -> list[CriterionCheck]:
    """Un chequeo por objeto y regla del perfil que aplica a su tipo (y por ítem si varios calzan).

    `assignments`: {(tipo, id): (escala, consecuencia)} con tipo `block`, `berm` (bloque modelo berma) o `le`;
    una escala o consecuencia vacía, ausente o fuera de la lista deja el chequeo «not_verifiable» (con la razón
    «unknown scale» o «unknown consequence»). `range_policy` sobrescribe la del
    perfil. `return_periods`: {id_analisis: Tr en años}, solo para `pseudostatic_analysis_present`.
    """
    policy = profile.range_policy if range_policy is None else range_policy
    if policy not in RANGE_POLICIES:
        raise ValueError(f"range_policy: must be one of {RANGE_POLICIES}")
    as_of = datetime.date.today().isoformat() if as_of is None else _check_date(as_of, "as_of")
    items = [i for i in (profile.version(iid, as_of) for iid in profile.item_ids()) if i is not None]
    by_rule: dict[str, list[NormItem]] = {}
    for i in items:
        by_rule.setdefault(i.check, []).append(i)
    all_by_rule: dict[str, list[NormItem]] = {}  # todas las versiones, para avisar si ninguna está vigente (I2)
    for i in profile.items:
        all_by_rule.setdefault(i.check, []).append(i)

    assign = _assigner(assignments)
    out: list[CriterionCheck] = []
    objects = [("berm" if r.model == "berm" else "block", r.id_bloque, r) for r in blocks]
    le = list(le)
    objects += [("le", r.id_analisis, r) for r in le]
    for kind, oid, r in objects:
        scale, cons = assign((kind, oid))
        unknown = _unknown(scale, cons)
        for rule in _KIND_RULES[kind]:
            if kind == "block" and rule == "slope_fs_pseudostatic" and not r.kh > 0:
                continue  # un bloque sin kh se juzga solo con las reglas estáticas
            if rule not in by_rule:
                old = [i for i in all_by_rule.get(rule, ()) if not unknown and _matches(i, scale, cons)]
                if old:
                    out.append(_empty(kind, oid, r.order, rule, old, NOT_IN_FORCE))
                continue
            if unknown:
                out.append(_empty(kind, oid, r.order, rule, by_rule[rule], unknown))
                continue
            hits = [i for i in by_rule[rule] if _matches(i, scale, cons)]
            if not hits:
                old = [i for i in all_by_rule[rule] if _matches(i, scale, cons)]
                reason = NOT_IN_FORCE if old else _no_match_reason(by_rule[rule], scale, cons)
                if reason == "the profile has no criterion for this consequence" and cons in profile.not_applicable:
                    reason = NOT_APPLICABLE
                out.append(_empty(kind, oid, r.order, rule, old or by_rule[rule], reason))
                continue
            rule_value = "slope_fs_pseudostatic" if rule == "deformation_required" else rule
            obtained, reason, note = (_le_value(rule_value, r) if kind == "le" else _block_value(rule, r))
            for item in hits:
                out.append(_check(kind, oid, r.order, item, policy, obtained, reason, note,
                                  newmark=kind == "le" and r.newmark is not None))
    for item in by_rule.get("pseudostatic_analysis_present", ()):
        status, reason = _pseudostatic_present(item, le, assign, return_periods or {})
        out.append(CriterionCheck("le_set", "", 0, item.item_id, item.check, item.value, item.comparison, None,
                                  status, reason, _source(item), item.force, item.verification, None))
    if "pseudostatic_analysis_present" not in by_rule and "pseudostatic_analysis_present" in all_by_rule:
        out.append(_empty("le_set", "", 0, "pseudostatic_analysis_present",
                          all_by_rule["pseudostatic_analysis_present"], NOT_IN_FORCE))
    return out


def criteria_counts(checks: Iterable[CriterionCheck]) -> dict[str, int]:
    """Conteos de una sola fuente para la CLI, el informe y las pruebas de paridad."""
    c = Counter(x.status for x in checks)
    return {"checks": sum(c.values()), **{s: c.get(s, 0) for s in CRITERIA_STATUSES}}


def criteria_attention(checks: Iterable[CriterionCheck]) -> Counter:
    """Única regla de atención (R10): los «fails», agrupados por regla y sin ids. Vacío = nada pide atención."""
    return Counter(x.rule for x in checks if x.needs_attention)


CRITERIA_RESULT_COLUMNS = ("tipo_objeto", "id_objeto", "orden", "criterio", "regla", "requerido", "comparacion",
                           "obtenido", "estado", "razon", "fuente", "fuerza", "marca", "rango_usado")
_KIND_WORD = {"block": "bloque", "berm": "berma", "le": "le", "le_set": "conjunto_le"}
_STATUS_WORD = {"meets": "cumple", "fails": "no_cumple", "not_verifiable": "no_verificable"}
_FORCE_WORD = {"law": "ley", "guide": "guia"}


def save_criteria_results(checks: Iterable[CriterionCheck], path) -> Path:
    """Escribe .xlsx (hoja `Criterios_resultados`) o .csv. Lleva el id del objeto; un FS infinito va como «inf»."""
    rows = [[_KIND_WORD[c.object_kind], c.object_id, c.order, c.item_id, c.rule, c.required, c.comparison,
             ("inf" if c.obtained > 0 else "-inf") if c.obtained is not None and math.isinf(c.obtained)
             else c.obtained, _STATUS_WORD[c.status], c.reason, c.source, _FORCE_WORD.get(c.force, c.force),
             c.verification, c.range_used] for c in checks]
    return write_table(path, CRITERIA_RESULT_COLUMNS, rows, sheet="Criterios_resultados")


# --- tabla propia del usuario (R7) ---

_TABLE_RULES = (("fs_estatico_min", "slope_fs_static", ">=", "FS"),
                ("fs_seudoestatico_min", "slope_fs_pseudostatic", ">=", "FS"),
                ("pof_max_pct", "slope_pof", "<=", "%"),
                ("confiabilidad_berma_min_pct", "berm_reliability", ">=", "%"))
_SUMMARY = {"es": "Criterio de la tabla propia del usuario.", "en": "Criterion from the user's own table."}


def _table_row(vals, n, sheet):
    def bad(c, why):
        raise ValueError(f"{_where(sheet, n, c)}: {why}")

    for c, allowed in (("escala", SCALES), ("consecuencia", CONSEQUENCES)):
        v = vals[c].strip().casefold()
        if v not in (*allowed, "*"):
            bad(c, f"must be one of {', '.join(allowed)} or *")
        vals[c] = v
    for c in ("fs_estatico_min", "fs_seudoestatico_min"):
        _rango(vals, sheet, n, c, 0, math.inf, lo_open=True)
    for c in ("pof_max_pct", "confiabilidad_berma_min_pct"):
        _rango(vals, sheet, n, c, 0, 100)
    if all(vals[c] is None for c, *_ in _TABLE_RULES):
        bad("fs_estatico_min", "give at least one criterion in the row")
    return n, vals


def load_criteria_table(path, *, sheet: str = CRITERIA_SHEET,
                        column_map: Mapping[str, str] | None = None) -> NormativeProfile:
    """Lee la hoja `Criterios` (o un .csv) y la vuelve un perfil en memoria: fuerza `guide`, marca `user` (R7)."""
    rows = _cargar(path, sheet, column_map, CRITERIA_COLUMNS, {"escala", "consecuencia", "fuente"},
                   ("escala", "consecuencia", "fuente"), None, _table_row)
    sheet_name = Path(path).stem if Path(path).suffix.lower() == ".csv" else sheet
    seen: dict = {}
    items, sources = [], {}
    for n, v in rows:
        key = (v["escala"], v["consecuencia"])
        if key in seen:
            raise ValueError(f"{_where(sheet_name, n, 'consecuencia')}: duplicate escala and consecuencia "
                             f"(first in row {seen[key]})")
        seen[key] = n
        src = f"row{n}"
        sources[src] = (v["fuente"], "")
        for col, rule, comp, unit in _TABLE_RULES:
            if v[col] is None:
                continue
            items.append(NormItem(
                item_id=f"{src}-{col}", jurisdiction="user", instrument=v["fuente"],
                article=f"sheet '{sheet_name}', row {n}", page="", source=src, url="", force="guide",
                verification="user", effective_from="0001-01-01", effective_to=None, check=rule,
                summary=_SUMMARY, value=v[col], unit=unit, comparison=comp,
                applies_to=(f"{v['escala']}:{v['consecuencia']}",)))
    if not items:
        raise ValueError(f"sheet '{sheet_name}': no criteria rows")
    return NormativeProfile(profile_id="USER-TABLE", jurisdiction="user",
                            name={"es": "Tabla propia de criterios", "en": "User criteria table"},
                            instruments=("user table",), sources=sources, items=tuple(items))


def profile_marks(profile: NormativeProfile) -> tuple[str, str]:
    """(marcas, fuerzas) de los ítems del perfil, sin repetir y en su orden; varias se unen con «/» (V2, guide)."""
    return ("/".join(dict.fromkeys(i.verification for i in profile.items)),
            "/".join(dict.fromkeys(i.force for i in profile.items)))
