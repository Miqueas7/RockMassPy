"""Ida y vuelta de LaborTable a dict, JSON y YAML. Las claves son API, por eso van en inglés.

En 1B la cartilla de una tabla de celdas se serializa solo por su id (debe existir en GSI_CHARTS).
"""

import json
from collections.abc import Mapping

from . import _rockmasspy_core as _rm
from .cell_table import CellClass, CellTable
from .gsi_charts import GSI_CHARTS
from .labor_table import LaborTable
from .range_table import RangeClass, RangeTable
from .support import Bolt, Shotcrete, SupportCatalog, SupportType

SCHEMA = "rockmasspy.labor_table"
SCHEMA_VERSION = 1


def to_dict(t: LaborTable) -> dict:
    def sup(s: SupportType) -> dict:
        return {
            "code": s.code, "order": s.order, "description": s.description,
            "bolt": None if s.bolt is None else {"kind": s.bolt.kind, "length_m": s.bolt.length_m, "spacing_m": s.bolt.spacing_m},
            "shotcrete": None if s.shotcrete is None else {"thickness_mm": s.shotcrete.thickness_mm, "fiber": s.shotcrete.fiber},
            "mesh": s.mesh, "arch": s.arch, "relative_cost": s.relative_cost,
        }

    if isinstance(t.table, RangeTable):
        table = {"kind": "range", "method": t.table.method, "base_edition": t.table.base_edition,
                 "classes": [{"lo": c.lo, "hi": c.hi, "label": c.label, "support": c.support} for c in t.table.classes]}
    else:
        table = {"kind": "cells", "chart": t.table.base_edition,
                 "cells": [{"cell": c.cell, "support": c.support,
                            "gsi_range": None if c.gsi_range is None else list(c.gsi_range), "label": c.label}
                           for c in t.table.cells]}
    return {
        "schema": SCHEMA, "version": SCHEMA_VERSION, "labor_type": t.labor_type,
        "span_m": None if t.span_m is None else list(t.span_m),
        "author": t.author, "date": t.date, "notes": t.notes,
        "support_types": [sup(s) for s in t.catalog],
        "table": table,
        "correlations": [{"name": c.name, "from": c.from_, "to": c.to, "form": c.form.name, "a": c.a, "b": c.b,
                          "valid_min": c.valid_min, "valid_max": c.valid_max, "source": c.source}
                         for c in t.correlations],
    }


def _get(d, key, path, kind=None):
    """Lee una clave obligatoria; el error nombra la ruta completa."""
    if not isinstance(d, Mapping):
        raise ValueError(f"{path}: expected an object")
    here = f"{path}.{key}" if path else key
    if key not in d:
        raise ValueError(f"{here}: missing")
    v = d[key]
    if kind == "number" and (isinstance(v, bool) or not isinstance(v, (int, float))):
        raise ValueError(f"{here}: expected a number")
    if kind == "str" and not isinstance(v, str):
        raise ValueError(f"{here}: expected a string")
    if kind == "list" and not isinstance(v, list):
        raise ValueError(f"{here}: expected a list")
    return v


def _opt(d, key, path, kind=None, default=None):
    return default if d.get(key) is None else _get(d, key, path, kind)


def from_dict(d: Mapping) -> LaborTable:
    if _get(d, "schema", "") != SCHEMA:
        raise ValueError(f"schema: expected {SCHEMA!r}, got {d['schema']!r}")
    if _get(d, "version", "") != SCHEMA_VERSION:
        raise ValueError(f"version: expected {SCHEMA_VERSION}, got {d['version']!r}")

    types = []
    for i, s in enumerate(_get(d, "support_types", "", "list")):
        p = f"support_types[{i}]"
        bolt = shot = None
        if s.get("bolt") is not None:
            b = s["bolt"]
            bolt = Bolt(_get(b, "kind", p + ".bolt", "str"), _get(b, "length_m", p + ".bolt", "number"),
                        _get(b, "spacing_m", p + ".bolt", "number"))
        if s.get("shotcrete") is not None:
            sc = s["shotcrete"]
            shot = Shotcrete(_get(sc, "thickness_mm", p + ".shotcrete", "number"), bool(sc.get("fiber", False)))
        types.append(SupportType(
            _get(s, "code", p, "str"), _get(s, "order", p, "number"), _opt(s, "description", p, "str", ""),
            bolt, shot, s.get("mesh"), s.get("arch"), _opt(s, "relative_cost", p, "number")))
    catalog = SupportCatalog(types)

    td = _get(d, "table", "")
    kind = _get(td, "kind", "table", "str")
    if kind == "range":
        classes = [RangeClass(_get(c, "lo", f"table.classes[{i}]", "number"), _get(c, "hi", f"table.classes[{i}]", "number"),
                              _get(c, "label", f"table.classes[{i}]", "str"), c.get("support"))
                   for i, c in enumerate(_get(td, "classes", "table", "list"))]
        table = RangeTable(_get(td, "method", "table", "str"), _get(td, "base_edition", "table", "str"), classes)
    elif kind == "cells":
        chart_id = _get(td, "chart", "table", "str")
        if chart_id not in GSI_CHARTS:
            raise ValueError(f"table.chart: unknown chart {chart_id!r}; known charts: {list(GSI_CHARTS)}")
        cells = []
        for i, c in enumerate(_get(td, "cells", "table", "list")):
            p = f"table.cells[{i}]"
            rng = c.get("gsi_range")
            cells.append(CellClass(_get(c, "cell", p, "str"), c.get("support"),
                                   None if rng is None else tuple(rng), _opt(c, "label", p, "str", "")))
        table = CellTable(GSI_CHARTS[chart_id], cells)
    else:
        raise ValueError(f"table.kind: expected 'range' or 'cells', got {kind!r}")

    corrs = []
    for i, c in enumerate(d.get("correlations") or []):
        p = f"correlations[{i}]"
        form = _get(c, "form", p, "str")
        if form not in _rm.CorrelationForm.__members__:
            raise ValueError(f"{p}.form: expected one of {list(_rm.CorrelationForm.__members__)}, got {form!r}")
        corrs.append(_rm.CustomCorrelation(
            name=_get(c, "name", p, "str"), from_=_get(c, "from", p, "str"), to=_get(c, "to", p, "str"),
            form=_rm.CorrelationForm.__members__[form], a=_get(c, "a", p, "number"), b=_get(c, "b", p, "number"),
            valid_min=_get(c, "valid_min", p, "number"), valid_max=_get(c, "valid_max", p, "number"),
            source=_opt(c, "source", p, "str", "")))

    span = d.get("span_m")
    return LaborTable(
        _get(d, "labor_type", "", "str"), catalog, table,
        None if span is None else tuple(span), tuple(corrs),
        _opt(d, "author", "", "str", ""), _opt(d, "date", "", "str", ""), _opt(d, "notes", "", "str", ""))


def save_json(t: LaborTable, path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(to_dict(t), f, ensure_ascii=False, indent=2)


def load_json(path) -> LaborTable:
    with open(path, encoding="utf-8") as f:
        return from_dict(json.load(f))


def _yaml():
    try:
        import yaml
    except ImportError as e:
        raise ImportError("install the optional extra: pip install rockmasspy[io]") from e
    return yaml


def save_yaml(t: LaborTable, path) -> None:
    yaml = _yaml()
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(to_dict(t), f, allow_unicode=True, sort_keys=False)


def load_yaml(path) -> LaborTable:
    yaml = _yaml()
    with open(path, encoding="utf-8") as f:
        return from_dict(yaml.safe_load(f))
