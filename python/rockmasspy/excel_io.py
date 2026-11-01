"""Excel (importar y exportar) de LaborTable. Hojas y columnas en español, como la plantilla del histórico.

Todo pasa por el diccionario de table_io (to_dict/from_dict): aquí solo se lee y se escribe la hoja;
las reglas de validación viven allá. Un número escrito a mano con coma ("3,5") no se convierte:
lanza ValueError con la hoja, la fila (de Excel, la cabecera es la 1) y la columna.
"""

import math

from .labor_table import LaborTable
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


def _support_dicts(wb, sheet):
    rows = _sheet_rows(wb, sheet, TIPOS, {"codigo_tipo", "orden"},
                       {"orden", "perno_longitud_m", "perno_espaciamiento_m", "shotcrete_espesor_mm", "costo_relativo"},
                       {"shotcrete_fibra"})
    out = []
    for _, r in rows:
        out.append({
            "code": r["codigo_tipo"], "order": r["orden"], "description": r["descripcion"] or "",
            "bolt": None if r["perno_tipo"] is None else
            {"kind": r["perno_tipo"], "length_m": r["perno_longitud_m"], "spacing_m": r["perno_espaciamiento_m"]},
            # espesor vacío o 0 = sin shotcrete
            "shotcrete": None if not r["shotcrete_espesor_mm"] else
            {"thickness_mm": r["shotcrete_espesor_mm"], "fiber": bool(r["shotcrete_fibra"])},
            "mesh": r["malla"], "arch": r["cimbra"], "relative_cost": r["costo_relativo"],
        })
    return out


def _open(path):
    return _optional("openpyxl").load_workbook(path, read_only=True, data_only=True)


def load_support_catalog_excel(path, sheet: str = "Tipos_sostenimiento") -> SupportCatalog:
    """Lee solo esa hoja; sirve también para la plantilla del histórico ya llena."""
    return catalog_from_dicts(_support_dicts(_open(path), sheet))


def load_excel(path) -> LaborTable:
    wb = _open(path)
    campos = {r["campo"]: r["valor"] for _, r in _sheet_rows(wb, "Tabla", ("campo", "valor"), {"campo"}, set())}
    for k in ("tipo_tabla",):
        if campos.get(k) is None:
            raise ValueError(f"sheet 'Tabla': missing value for '{k}'")

    def numero(k):
        v = campos.get(k)
        return None if v is None else _num(v, "Tabla", k, "valor")

    lo, hi = numero("luz_min_m"), numero("luz_max_m")
    if (lo is None) != (hi is None):
        raise ValueError("sheet 'Tabla': luz_min_m and luz_max_m must come together")
    d = {"schema": campos.get("schema"), "version": numero("version"), "labor_type": campos.get("labor_type"),
         "span_m": None if lo is None else [lo, hi], "author": campos.get("autor"), "date": campos.get("fecha"),
         "notes": campos.get("notas"), "support_types": _support_dicts(wb, "Tipos_sostenimiento")}
    kind = campos["tipo_tabla"]
    if kind == "range":
        d["table"] = {"kind": "range", "method": campos.get("metodo"), "base_edition": campos.get("edicion_base"),
                      "classes": [{"lo": r["desde"], "hi": r["hasta"], "label": r["clase"], "support": r["tipo"]}
                                  for _, r in _sheet_rows(wb, "Clases", CLASES, {"desde", "hasta", "clase"},
                                                          {"desde", "hasta"})]}
    elif kind == "cells":
        cells = []
        for n, r in _sheet_rows(wb, "Celdas", CELDAS, {"celda"}, {"gsi_min", "gsi_max"}):
            if (r["gsi_min"] is None) != (r["gsi_max"] is None):
                raise ValueError(f"{_where('Celdas', n, 'gsi_max')}: gsi_min and gsi_max must come together")
            cells.append({"cell": r["celda"], "support": r["tipo"], "label": r["rotulo"] or "",
                          "gsi_range": None if r["gsi_min"] is None else [r["gsi_min"], r["gsi_max"]]})
        d["table"] = {"kind": "cells", "chart": campos.get("cartilla"), "cells": cells}
    else:
        raise ValueError(f"sheet 'Tabla': tipo_tabla must be 'range' or 'cells', got '{kind}'")
    d["correlations"] = [] if "Correlaciones" not in wb.sheetnames else [
        {"name": r["nombre"], "from": r["desde"], "to": r["hacia"], "form": r["forma"], "a": r["a"], "b": r["b"],
         "valid_min": r["valido_min"], "valid_max": r["valido_max"], "source": r["fuente"] or ""}
        for _, r in _sheet_rows(wb, "Correlaciones", CORRELACIONES, {"nombre", "desde", "hacia", "forma"},
                                {"a", "b", "valido_min", "valido_max"})]
    return from_dict(d)


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
