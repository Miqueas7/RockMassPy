"""Excel (importar y exportar) de LaborTable. Hojas y columnas en español, como la plantilla del histórico.

Todo pasa por el diccionario de table_io (to_dict/from_dict): aquí solo se lee y se escribe la hoja;
las reglas de validación viven allá. Un número escrito a mano con coma ("3,5") no se convierte:
lanza ValueError con la hoja, la fila (de Excel, la cabecera es la 1) y la columna.
"""

import datetime
import math

from . import _rockmasspy_core as _rm
from .cell_table import CellClass
from .labor_table import LaborTable
from .range_table import RangeClass
from .support import SupportCatalog
from .table_io import _bool, _optional, catalog_from_dicts, from_dict, to_dict

TIPOS = ("codigo_tipo", "orden", "descripcion", "perno_tipo", "perno_longitud_m", "perno_espaciamiento_m",
         "shotcrete_espesor_mm", "shotcrete_fibra", "malla", "cimbra", "costo_relativo")
CLASES = ("desde", "hasta", "clase", "tipo")
CELDAS = ("celda", "tipo", "gsi_min", "gsi_max", "rotulo")
CORRELACIONES = ("nombre", "desde", "hacia", "forma", "a", "b", "valido_min", "valido_max", "fuente")


def _where(sheet, row, col):
    return f"sheet '{sheet}', row {row}, column '{col}'"


def _num(v, sheet, row, col):
    x = None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        x = v
    elif isinstance(v, str):
        try:
            x = float(v.strip())
        except ValueError:
            pass
    if x is None or not math.isfinite(x):
        raise ValueError(f"{_where(sheet, row, col)}: expected a number, got '{v}'")
    return x


def _text(v):
    if isinstance(v, datetime.datetime):  # fecha nativa de Excel
        v = v.date()
    if isinstance(v, datetime.date):
        return v.isoformat()
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def _sheet_rows(wb, sheet, cols, required, numeric, boolean=()):
    """Una tupla (fila_excel, dict) por fila no vacía; una celda vacía opcional queda en None."""
    if sheet not in wb.sheetnames:
        raise ValueError(f"missing sheet '{sheet}'")
    rows = wb[sheet].iter_rows(values_only=True)
    header = [_text(h) if h is not None else "" for h in next(rows, ())]
    pos = {}
    for c in cols:
        if c not in header:
            raise ValueError(f"sheet '{sheet}': missing column '{c}'")
        pos[c] = header.index(c)
    out = []
    for n, raw in enumerate(rows, start=2):
        row = {}
        for c in cols:
            v = raw[pos[c]] if pos[c] < len(raw) else None
            row[c] = None if isinstance(v, str) and not v.strip() else v
        if all(v is None for v in row.values()):
            continue
        for c, v in row.items():
            if v is None:
                if c in required:
                    raise ValueError(f"{_where(sheet, n, c)}: required value is empty")
            elif c in numeric:
                row[c] = _num(v, sheet, n, c)
            elif c in boolean:
                row[c] = _bool(v, _where(sheet, n, c))
            else:
                row[c] = _text(v)
        out.append((n, row))
    return out


def _row(sheet, n, build, *args):
    """Construye el objeto de una fila; si la validación falla, el error ubica la hoja y la fila."""
    try:
        return build(*args)
    except (ValueError, KeyError) as e:
        raise ValueError(f"sheet '{sheet}', row {n}: {e}") from e


def _support_dicts(wb, sheet):
    rows = _sheet_rows(wb, sheet, TIPOS, {"codigo_tipo", "orden"},
                       {"orden", "perno_longitud_m", "perno_espaciamiento_m", "shotcrete_espesor_mm", "costo_relativo"},
                       {"shotcrete_fibra"})
    out = []
    for n, r in rows:
        out.append((n, {
            "code": r["codigo_tipo"], "order": r["orden"], "description": r["descripcion"] or "",
            "bolt": None if r["perno_tipo"] is None else
            {"kind": r["perno_tipo"], "length_m": r["perno_longitud_m"], "spacing_m": r["perno_espaciamiento_m"]},
            # espesor vacío o 0 = sin shotcrete
            "shotcrete": None if not r["shotcrete_espesor_mm"] else
            {"thickness_mm": r["shotcrete_espesor_mm"], "fiber": bool(r["shotcrete_fibra"])},
            "mesh": r["malla"], "arch": r["cimbra"], "relative_cost": r["costo_relativo"],
        }))
    return out


def _open(path):
    return _optional("openpyxl").load_workbook(path, read_only=True, data_only=True)


def _catalog(wb, sheet):
    pairs = _support_dicts(wb, sheet)
    for n, d in pairs:  # valida fila por fila para ubicar la celda
        _row(sheet, n, catalog_from_dicts, [d])
    catalog_from_dicts([d for _, d in pairs])  # duplicados entre filas
    return [d for _, d in pairs]


def load_support_catalog_excel(path, sheet: str = "Tipos_sostenimiento") -> SupportCatalog:
    """Lee solo esa hoja; sirve también para la plantilla del histórico ya llena."""
    wb = _open(path)
    try:
        return catalog_from_dicts(_catalog(wb, sheet))
    finally:
        wb.close()


def load_excel(path) -> LaborTable:
    wb = _open(path)
    try:
        return _load(wb)
    finally:
        wb.close()


def _load(wb) -> LaborTable:
    filas = {r["campo"]: (n, r["valor"]) for n, r in _sheet_rows(wb, "Tabla", ("campo", "valor"), {"campo"}, set())}
    campos = {k: v for k, (_, v) in filas.items()}
    for k in ("tipo_tabla",):
        if campos.get(k) is None:
            raise ValueError(f"sheet 'Tabla': missing value for '{k}'")

    def numero(k):
        v = campos.get(k)
        return None if v is None else _num(v, "Tabla", filas[k][0], "valor")

    lo, hi = numero("luz_min_m"), numero("luz_max_m")
    if (lo is None) != (hi is None):
        raise ValueError("sheet 'Tabla': luz_min_m and luz_max_m must come together")
    tipos = _catalog(wb, "Tipos_sostenimiento")  # ubica errores de validación por fila
    d = {"schema": campos.get("schema"), "version": numero("version"), "labor_type": campos.get("labor_type"),
         "span_m": None if lo is None else [lo, hi], "author": campos.get("autor"), "date": campos.get("fecha"),
         "notes": campos.get("notas"), "support_types": tipos}
    kind = campos["tipo_tabla"]
    if kind == "range":
        d["table"] = {"kind": "range", "method": campos.get("metodo"), "base_edition": campos.get("edicion_base"),
                      "classes": [{"lo": r["desde"], "hi": r["hasta"], "label": r["clase"], "support": r["tipo"]}
                                  for _, r in _clases(wb)]}
    elif kind == "cells":
        cells = []
        for n, r in _sheet_rows(wb, "Celdas", CELDAS, {"celda"}, {"gsi_min", "gsi_max"}):
            if (r["gsi_min"] is None) != (r["gsi_max"] is None):
                raise ValueError(f"{_where('Celdas', n, 'gsi_max')}: gsi_min and gsi_max must come together")
            _row("Celdas", n, CellClass, r["celda"], r["tipo"], None if r["gsi_min"] is None else (r["gsi_min"], r["gsi_max"]),
                 r["rotulo"] or "")
            cells.append({"cell": r["celda"], "support": r["tipo"], "label": r["rotulo"] or "",
                          "gsi_range": None if r["gsi_min"] is None else [r["gsi_min"], r["gsi_max"]]})
        d["table"] = {"kind": "cells", "chart": campos.get("cartilla"), "cells": cells}
    else:
        raise ValueError(f"sheet 'Tabla': tipo_tabla must be 'range' or 'cells', got '{kind}'")
    d["correlations"] = [] if "Correlaciones" not in wb.sheetnames else [
        _corr(n, r) for n, r in _sheet_rows(wb, "Correlaciones", CORRELACIONES, {"nombre", "desde", "hacia", "forma"},
                                            {"a", "b", "valido_min", "valido_max"})]
    return from_dict(d)


def _clases(wb):
    pairs = _sheet_rows(wb, "Clases", CLASES, {"desde", "hasta", "clase"}, {"desde", "hasta"})
    for n, r in pairs:
        _row("Clases", n, RangeClass, r["desde"], r["hasta"], r["clase"], r["tipo"])
    return pairs


def _corr(n, r):
    d = {"name": r["nombre"], "from": r["desde"], "to": r["hacia"], "form": r["forma"], "a": r["a"], "b": r["b"],
         "valid_min": r["valido_min"], "valid_max": r["valido_max"], "source": r["fuente"] or ""}

    def build():  # misma construcción que from_dict, solo para ubicar la fila
        if d["form"] not in _rm.CorrelationForm.__members__:
            raise ValueError(f"form: expected one of {list(_rm.CorrelationForm.__members__)}, got {d['form']!r}")
        _rm.CustomCorrelation(name=d["name"], from_=d["from"], to=d["to"], form=_rm.CorrelationForm.__members__[d["form"]],
                              a=d["a"], b=d["b"], valid_min=d["valid_min"], valid_max=d["valid_max"], source=d["source"])
    _row("Correlaciones", n, build)
    return d


def save_excel(t: LaborTable, path) -> None:
    openpyxl = _optional("openpyxl")
    d = to_dict(t)
    tb = d["table"]
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    def sheet(name, cols, rows):
        ws = wb.create_sheet(name)
        ws.append(list(cols))
        for c in ws[1]:
            c.font = _optional("openpyxl.styles").Font(bold=True)
        for r in rows:
            ws.append(list(r))

    span = d["span_m"] or [None, None]
    campos = [("schema", d["schema"]), ("version", d["version"]), ("labor_type", d["labor_type"]),
              ("luz_min_m", span[0]), ("luz_max_m", span[1]), ("autor", d["author"] or None),
              ("fecha", d["date"] or None), ("notas", d["notes"] or None), ("tipo_tabla", tb["kind"])]
    if tb["kind"] == "range":
        campos += [("metodo", tb["method"]), ("edicion_base", tb["base_edition"])]
    else:  # la edición base de una tabla de celdas es la cartilla
        campos += [("edicion_base", tb["chart"]), ("cartilla", tb["chart"])]
    sheet("Tabla", ("campo", "valor"), campos)
    sheet("Tipos_sostenimiento", TIPOS, [
        (s["code"], s["order"], s["description"] or None,
         s["bolt"] and s["bolt"]["kind"], s["bolt"] and s["bolt"]["length_m"], s["bolt"] and s["bolt"]["spacing_m"],
         s["shotcrete"] and s["shotcrete"]["thickness_mm"],
         ("si" if s["shotcrete"]["fiber"] else "no") if s["shotcrete"] else None,
         s["mesh"], s["arch"], s["relative_cost"]) for s in d["support_types"]])
    if tb["kind"] == "range":
        sheet("Clases", CLASES, [(c["lo"], c["hi"], c["label"], c["support"]) for c in tb["classes"]])
    else:
        sheet("Celdas", CELDAS, [(c["cell"], c["support"], *(c["gsi_range"] or (None, None)), c["label"] or None)
                                 for c in tb["cells"]])
    if d["correlations"]:
        sheet("Correlaciones", CORRELACIONES, [
            (c["name"], c["from"], c["to"], c["form"], c["a"], c["b"], c["valid_min"], c["valid_max"], c["source"] or None)
            for c in d["correlations"]])
    wb.save(path)
