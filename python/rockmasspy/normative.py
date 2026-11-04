"""Perfiles normativos: requisitos de una jurisdicción como datos, con vigencia por fecha.

Un perfil es un JSON (`schema` 1) en `rockmasspy/profiles/`, leído solo con la biblioteca estándar (R1).
Cada ítem nombra una regla de un conjunto cerrado (`RULES`, R3); el umbral, la comparación y `applies_to`
son datos, así que un país nuevo que reutiliza reglas es un archivo nuevo. Un requisito sin regla entra con
`check: "none"` y sale «no verificable»; nunca se omite.

Marcas de verificación (spec §13): [V1] entra normal, [V2] entra con su marca a la vista y [NV] no entra.
Las fechas de vigencia son ISO y ambos extremos son inclusive.

Criterios de aceptación (3D): las reglas `slope_*`, `berm_reliability` y `deformation_required` llevan
`applies_to` con claves `escala:consecuencia` («*» vale cualquiera). Un umbral puede ser un rango
(`value_range: [a, b]`, a < b); el perfil declara `range_policy` (por defecto `conservative`: el extremo alto
para un mínimo y el bajo para un máximo, R1). Una sola cifra es `value`, no un rango.
"""
from __future__ import annotations

import datetime
import json
import math
import re
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from .batch import EsrSpec, parse_esr_spec

FORCES = ("law", "guide")
VERIFICATIONS = ("V1", "V2", "PrimaryLaterAuthors")
RANGE_POLICIES = ("conservative", "upper", "lower")
SCALES = ("banco", "interrampa", "global", "pad", "botadero")
CONSEQUENCES = ("baja", "media", "alta", "no_seria", "moderada", "seria", "extrema")
COMPARISONS = (">", ">=", "<", "<=")

# regla -> si es de umbral (exige value numérico, unit y comparison)
RULES: dict[str, bool] = {
    "none": False, "esr": False, "table_content": False, "span_within_table": False,
    "empirical_calculation": False, "anexo39b_structure": False,
    "refuge_rock_quality": True, "refuge_distance": True, "refuge_area_per_person": True,
    "walkway_spacing": True, "qc_ratio": True, "fs_minimum": True, "standup_time": True,
    # criterios de aceptación de taludes (3D)
    "slope_fs_static": True, "slope_fs_pseudostatic": True, "slope_pof": True, "berm_reliability": True,
    "deformation_required": True, "pseudostatic_analysis_present": True,
}
# reglas cuyo applies_to son claves escala:consecuencia
CRITERIA_RULES = ("slope_fs_static", "slope_fs_pseudostatic", "slope_pof", "berm_reliability", "deformation_required")


def _check_date(text, label: str) -> str:
    """Devuelve la fecha ISO (AAAA-MM-DD) o lanza ValueError sin el prefijo del archivo."""
    if not isinstance(text, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text):
        raise ValueError(f"{label}: not an ISO date (YYYY-MM-DD)")
    try:
        datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError(f"{label}: not a real calendar date") from None
    return text


@dataclass(frozen=True)
class NormItem:
    item_id: str
    jurisdiction: str
    instrument: str
    article: str
    page: str
    source: str
    url: str
    force: str
    verification: str
    effective_from: str
    effective_to: str | None
    check: str
    summary: dict
    amended_by: tuple = ()
    value: float | str | None = None
    unit: str = ""
    comparison: str | None = None
    applies_to: tuple = ()
    cited_standard: str = ""  # edición que cita la norma, tal cual, aunque exista una más nueva (spec §2.3)
    value_range: tuple | None = None  # (a, b) con a < b; entonces value es None

    def in_force(self, as_of: str) -> bool:
        _check_date(as_of, "as_of")
        return self.effective_from <= as_of and (self.effective_to is None or as_of <= self.effective_to)


@dataclass(frozen=True)
class NormativeProfile:
    profile_id: str
    jurisdiction: str
    name: dict
    instruments: tuple
    sources: dict  # clave -> (título, URL)
    items: tuple
    range_policy: str = "conservative"

    def item_ids(self) -> tuple:
        return tuple(dict.fromkeys(i.item_id for i in self.items))

    def versions(self, item_id: str) -> tuple:
        return tuple(i for i in self.items if i.item_id == item_id)

    def version(self, item_id: str, as_of: str):
        for i in self.versions(item_id):
            if i.in_force(as_of):
                return i
        return None


def _bad_constant(name):
    raise ValueError(f"{name} is not allowed in a profile")


def _text(d: dict, key: str, where: str) -> str:
    v = d.get(key)
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"{where}{key}: required, non-empty text")
    return v


def _parse_item(raw, sources: dict, jurisdiction: str, fname: str) -> NormItem:
    if not isinstance(raw, dict):
        raise ValueError(f"profile {fname}: items: each item must be an object")
    iid = raw.get("id") if isinstance(raw.get("id"), str) and raw.get("id").strip() else "?"
    where = f"profile {fname}: item {iid}: "

    def fail(field, why):
        raise ValueError(f"{where}{field}: {why}")

    def text(key):
        try:
            return _text(raw, key, "")
        except ValueError as e:
            raise ValueError(where + str(e)) from None

    for key in ("id", "instrument", "article", "page", "source", "force", "verification", "check"):
        text(key)
    force, ver, check = raw["force"], raw["verification"], raw["check"]
    if force not in FORCES:
        fail("force", f"must be one of {FORCES}")
    if ver == "NV":
        fail("verification", "[NV] items do not enter (spec 13)")
    if ver not in VERIFICATIONS:
        fail("verification", f"must be one of {VERIFICATIONS}")
    try:
        start = _check_date(raw.get("effective_from"), "effective_from")
        end = raw.get("effective_to")
        if end is not None:
            end = _check_date(end, "effective_to")
    except ValueError as e:
        raise ValueError(where + str(e)) from None
    if end is not None and end < start:
        fail("effective_to", "is before effective_from")
    if check not in RULES:
        fail("check", f"unknown rule (known: {', '.join(RULES)})")
    value, unit, comp = raw.get("value"), raw.get("unit", ""), raw.get("comparison")
    rng = raw.get("value_range")
    if rng is not None:
        if not RULES[check]:
            fail("value_range", "only threshold rules take a range")
        if value is not None:
            fail("value_range", "give value or value_range, not both")
        if (not isinstance(rng, list) or len(rng) != 2
                or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in rng)):
            fail("value_range", "must be two finite numbers [a, b]")
        if not rng[0] < rng[1]:
            fail("value_range", "needs a < b (a single figure is a value)")
        rng = (rng[0], rng[1])
    if RULES[check]:
        if rng is None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
            fail("value", "threshold rules need a finite number")
        if not isinstance(unit, str) or not unit.strip():
            fail("unit", "threshold rules need a unit")
        if comp not in COMPARISONS:
            fail("comparison", f"threshold rules need one of {COMPARISONS}")
    elif comp is not None and comp not in COMPARISONS:
        fail("comparison", f"must be one of {COMPARISONS}")
    applies = raw.get("applies_to", [])
    if not isinstance(applies, list) or not all(isinstance(a, str) and a for a in applies):
        fail("applies_to", "must be a list of text")
    if check in CRITERIA_RULES:
        for a in applies:
            sc, _, co = a.partition(":")
            if sc not in (*SCALES, "*") or co not in (*CONSEQUENCES, "*"):
                fail("applies_to", f"criteria keys are scale:consequence with scales {SCALES} and "
                                   f"consequences {CONSEQUENCES} (or *)")
    if check == "esr":
        if len(applies) != 1:
            fail("applies_to", "an esr item needs exactly one labor")
        try:
            parse_esr_spec(value)
        except ValueError:
            fail("value", "an esr item needs an ESR spec such as C or A:3")
    src = raw["source"]
    if src not in sources:
        fail("source", "not defined in sources")
    if not sources[src][1].startswith("https://"):
        fail("url", "source URL must start with https://")
    summary = raw.get("summary")
    if not isinstance(summary, dict) or not all(
            isinstance(summary.get(k), str) and summary[k].strip() for k in ("es", "en")):
        fail("summary", "needs non-empty es and en")
    amended = raw.get("amended_by", [])
    if not isinstance(amended, list) or not all(isinstance(a, str) for a in amended):
        fail("amended_by", "must be a list of text")
    cited = raw.get("cited_standard", "")
    if not isinstance(cited, str):
        fail("cited_standard", "must be text")
    return NormItem(
        item_id=raw["id"], jurisdiction=jurisdiction, instrument=raw["instrument"], article=raw["article"],
        page=raw["page"], source=src, url=sources[src][1], force=force, verification=ver,
        effective_from=start, effective_to=end, check=check, summary={"es": summary["es"], "en": summary["en"]},
        amended_by=tuple(amended), value=value, unit=unit, comparison=comp, applies_to=tuple(applies),
        cited_standard=cited, value_range=rng)


def load_profile(path) -> NormativeProfile:
    """Carga y valida un perfil JSON. Lanza ValueError (archivo, ítem, campo) y no devuelve nada a medias."""
    path = Path(path)
    fname = path.name
    try:
        data = json.loads(path.read_text(encoding="utf-8"), parse_constant=_bad_constant)
    except (OSError, ValueError) as e:
        raise ValueError(f"profile {fname}: file: {e}") from None
    where = f"profile {fname}: "
    if not isinstance(data, dict):
        raise ValueError(where + "file: top level must be an object")
    if data.get("schema") != 1 or isinstance(data.get("schema"), bool):
        raise ValueError(where + "schema: must be 1")
    for key in ("profile_id", "jurisdiction"):
        try:
            _text(data, key, "")
        except ValueError as e:
            raise ValueError(where + str(e)) from None
    name = data.get("name")
    if not isinstance(name, dict) or not all(isinstance(name.get(k), str) and name[k].strip() for k in ("es", "en")):
        raise ValueError(where + "name: needs non-empty es and en")
    instruments = data.get("instruments")
    if not isinstance(instruments, list) or not instruments or not all(isinstance(i, str) for i in instruments):
        raise ValueError(where + "instruments: must be a non-empty list of text")
    raw_sources = data.get("sources")
    if not isinstance(raw_sources, dict) or not raw_sources:
        raise ValueError(where + "sources: must be a non-empty object")
    sources = {}
    for key, s in raw_sources.items():
        if not isinstance(s, dict) or not isinstance(s.get("title"), str) or not isinstance(s.get("url"), str):
            raise ValueError(f"{where}sources: {key}: needs title and url")
        sources[key] = (s["title"], s["url"])
    policy = data.get("range_policy", "conservative")
    if policy not in RANGE_POLICIES:
        raise ValueError(f"{where}range_policy: must be one of {RANGE_POLICIES}")
    raw_items = data.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError(where + "items: must be a non-empty list")
    items = tuple(_parse_item(r, sources, data["jurisdiction"], fname) for r in raw_items)
    for iid in dict.fromkeys(i.item_id for i in items):
        vs = sorted((i for i in items if i.item_id == iid), key=lambda i: i.effective_from)
        for a, b in zip(vs, vs[1:]):
            if a.effective_to is None or a.effective_to >= b.effective_from:
                raise ValueError(f"{where}item {iid}: effective_from: versions overlap")
    return NormativeProfile(profile_id=data["profile_id"], jurisdiction=data["jurisdiction"],
                            name={"es": name["es"], "en": name["en"]}, instruments=tuple(instruments),
                            sources=sources, items=items, range_policy=policy)


def _profiles_dir():
    return resources.files("rockmasspy") / "profiles"


def available_profiles() -> dict:
    """profile_id -> archivo JSON de la carpeta `profiles/` del paquete."""
    found: dict = {}
    for entry in sorted(_profiles_dir().iterdir(), key=lambda e: e.name):
        if not entry.name.endswith(".json"):
            continue
        pid = load_profile(entry).profile_id
        if pid in found:
            raise ValueError(f"profile_id {pid} appears in two files: {found[pid].name}, {entry.name}")
        found[pid] = entry
    return found


def get_profile(profile_id: str) -> NormativeProfile:
    avail = available_profiles()
    if profile_id not in avail:
        raise ValueError(f"unknown profile {profile_id!r}; available: {', '.join(sorted(avail)) or '(none)'}")
    return load_profile(avail[profile_id])


def profile_esr_specs(profile: NormativeProfile, as_of: str) -> dict[str, EsrSpec]:
    """labor -> ESR de los ítems `esr` vigentes en `as_of`; sin clave "*" (una labor sin entrada queda sin referencia)."""
    _check_date(as_of, "as_of")
    return {i.applies_to[0]: parse_esr_spec(i.value) for i in profile.items if i.check == "esr" and i.in_force(as_of)}
