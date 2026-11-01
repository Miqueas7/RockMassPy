"""Ida y vuelta de LaborTable a dict, JSON y YAML. Las claves son API, por eso van en inglés.

En 1B la cartilla de una tabla de celdas se serializa solo por su id (debe existir en GSI_CHARTS).
"""

import datetime
import importlib
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
        table = {"kind": "cells", "chart": t.table.base_edition, "base_edition": t.table.base_edition,
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


def _bool(v, path):
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        w = v.strip().lower()
        if w in ("true", "si", "sí", "yes"):
            return True
        if w in ("false", "no"):
            return False
    raise ValueError(f"{path}: expected true/false")


def _opt(d, key, path, kind=None, default=None):
    # si d no es un objeto, _get lanza «expected an object» con la ruta
    return default if isinstance(d, Mapping) and d.get(key) is None else _get(d, key, path, kind)


def _pair(d, key, path):
    """[lo, hi] opcional: exactamente dos números, o None."""
    v = _opt(d, key, path, "list")
    if v is not None and (len(v) != 2 or any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in v)):
        raise ValueError(f"{f'{path}.{key}' if path else key}: expected a list of 2 numbers, got {v!r}")
    return None if v is None else tuple(v)


def _at(path, build, *args, **kw):
    """Construye un objeto; cualquier error de sus datos sale como ValueError que nombra la ruta."""
    try:
        return build(*args, **kw)
    except (ValueError, TypeError, AttributeError, KeyError) as e:
        msg = e.args[0] if isinstance(e, KeyError) and e.args else e  # KeyError agrega comillas en str()
        raise ValueError(f"{path}: {msg}" if path else str(msg)) from e


def _sub(path, key):
    return f"{path}.{key}" if path else ""  # sin ruta (Excel) no se inventa una


def support_from_dict(s, path: str = "") -> SupportType:
    """Un tipo de sostenimiento; con path="" los errores no llevan ruta (Excel pone hoja y fila)."""
    b, sc = _opt(s, "bolt", path), _opt(s, "shotcrete", path)
    bp, sp = _sub(path, "bolt"), _sub(path, "shotcrete")
    bolt = None if b is None else _at(bp, Bolt, _get(b, "kind", bp, "str"), _get(b, "length_m", bp, "number"),
                                      _get(b, "spacing_m", bp, "number"))
    shot = None if sc is None else _at(sp, Shotcrete, _get(sc, "thickness_mm", sp, "number"),
                                       _bool(sc.get("fiber", False), f"{sp}.fiber" if sp else "fiber"))
    return _at(path, SupportType, _get(s, "code", path, "str"), _get(s, "order", path, "number"),
               _opt(s, "description", path, "str", ""), bolt, shot, _opt(s, "mesh", path, "str"),
               _opt(s, "arch", path, "str"), _opt(s, "relative_cost", path, "number"))


def catalog_from_dicts(items: list) -> SupportCatalog:
    """Arma el catálogo desde la lista `support_types`."""
    return _at("support_types", SupportCatalog, [support_from_dict(s, f"support_types[{i}]") for i, s in enumerate(items)])


def correlation_from_dict(c, path: str = ""):
    """Una CustomCorrelation; el constructor de C++ valida nombres, números y valid_min < valid_max."""
    form = _get(c, "form", path, "str")
    if form not in _rm.CorrelationForm.__members__:
        raise ValueError(f"{_sub(path, 'form') or 'form'}: expected one of {list(_rm.CorrelationForm.__members__)}, got {form!r}")
    return _at(path, _rm.CustomCorrelation,
               name=_get(c, "name", path, "str"), from_=_get(c, "from", path, "str"), to=_get(c, "to", path, "str"),
               form=_rm.CorrelationForm.__members__[form], a=_get(c, "a", path, "number"), b=_get(c, "b", path, "number"),
               valid_min=_get(c, "valid_min", path, "number"), valid_max=_get(c, "valid_max", path, "number"),
               source=_opt(c, "source", path, "str", ""))


def from_dict(d: Mapping) -> LaborTable:
    if _get(d, "schema", "") != SCHEMA:
        raise ValueError(f"schema: expected {SCHEMA!r}, got {d['schema']!r}")
    if _get(d, "version", "") != SCHEMA_VERSION:
        raise ValueError(f"version: expected {SCHEMA_VERSION}, got {d['version']!r}")

    catalog = catalog_from_dicts(_get(d, "support_types", "", "list"))

    td = _get(d, "table", "")
    kind = _get(td, "kind", "table", "str")
    if kind == "range":
        classes = []
        for i, c in enumerate(_get(td, "classes", "table", "list")):
            p = f"table.classes[{i}]"
            classes.append(_at(p, RangeClass, _get(c, "lo", p, "number"), _get(c, "hi", p, "number"),
                               _get(c, "label", p, "str"), c.get("support")))
        table = _at("table", RangeTable, _get(td, "method", "table", "str"), _get(td, "base_edition", "table", "str"), classes)
    elif kind == "cells":
        chart_id = _get(td, "chart", "table", "str")
        if chart_id not in GSI_CHARTS:
            raise ValueError(f"table.chart: unknown chart {chart_id!r}; known charts: {list(GSI_CHARTS)}")
        base = _opt(td, "base_edition", "table", "str")
        if base is not None and base != chart_id:  # en una tabla de celdas la edición base es la cartilla
            raise ValueError(f"table.base_edition: expected the chart id {chart_id!r}, got {base!r}")
        cells = []
        for i, c in enumerate(_get(td, "cells", "table", "list")):
            p = f"table.cells[{i}]"
            cells.append(_at(p, CellClass, _get(c, "cell", p, "str"), _opt(c, "support", p),
                             _pair(c, "gsi_range", p), _opt(c, "label", p, "str", "")))
        table = _at("table", CellTable, GSI_CHARTS[chart_id], cells)
    else:
        raise ValueError(f"table.kind: expected 'range' or 'cells', got {kind!r}")

    corrs = tuple(correlation_from_dict(c, f"correlations[{i}]")
                  for i, c in enumerate(_opt(d, "correlations", "", "list", [])))

    date = d.get("date")
    if isinstance(date, datetime.datetime):  # YAML con hora: solo la fecha
        date = date.date()
    if isinstance(date, datetime.date):  # YAML escrito a mano: `date: 2026-11-01` sin comillas
        d = {**d, "date": date.isoformat()}
    return _at("", LaborTable,
               _get(d, "labor_type", "", "str"), catalog, table, _pair(d, "span_m", ""), corrs,
               _opt(d, "author", "", "str", ""), _opt(d, "date", "", "str", ""), _opt(d, "notes", "", "str", ""))


def save_json(t: LaborTable, path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(to_dict(t), f, ensure_ascii=False, indent=2)


def load_json(path) -> LaborTable:
    with open(path, encoding="utf-8") as f:
        return from_dict(json.load(f))


def _optional(name: str):
    """Importa una dependencia opcional; si falta, el error nombra el extra [io]."""
    try:
        return importlib.import_module(name)
    except ImportError as e:
        raise ImportError("install the optional extra: pip install rockmasspy[io]") from e


def _yaml():
    return _optional("yaml")


def save_yaml(t: LaborTable, path) -> None:
    yaml = _yaml()
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(to_dict(t), f, allow_unicode=True, sort_keys=False)


def load_yaml(path) -> LaborTable:
    yaml = _yaml()
    with open(path, encoding="utf-8") as f:
        return from_dict(yaml.safe_load(f))
