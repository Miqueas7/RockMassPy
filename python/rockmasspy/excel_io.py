"""Excel (importar y exportar) de LaborTable. Hojas y columnas en español, como la plantilla del histórico.

Todo pasa por el diccionario de table_io (to_dict/from_dict): aquí solo se lee y se escribe la hoja;
las reglas de validación viven allá. Un número escrito a mano con coma ("3,5") no se convierte:
lanza ValueError con la hoja, la fila (de Excel, la cabecera es la 1) y la columna.
"""

import datetime
import math

from .cell_table import CellClass
from .labor_table import LaborTable
from .range_table import RangeClass
from .rating_table import RatingBin
from .support import SupportCatalog
from .table_io import _at, _bool, _optional, correlation_from_dict, from_dict, support_from_dict, to_dict

TIPOS = ("codigo_tipo", "orden", "descripcion", "perno_tipo", "perno_longitud_m", "perno_espaciamiento_m",
         "shotcrete_espesor_mm", "shotcrete_fibra", "malla", "cimbra", "costo_relativo")
CLASES = ("desde", "hasta", "clase", "tipo")
CELDAS = ("celda", "tipo", "gsi_min", "gsi_max", "rotulo")
CORRELACIONES = ("nombre", "desde", "hacia", "forma", "a", "b", "valido_min", "valido_max", "fuente")
PUNTAJES = ("parametro", "tipo", "unidad", "mejor", "desde", "hasta", "categoria", "puntos")
MEJOR = {"mayor": "higher", "menor": "lower"}
PERNO = ("perno_tipo", "perno_longitud_m", "perno_espaciamiento_m")
# campo de la hoja Tabla para cada ruta de from_dict (los errores se ubican con el nombre en español)
CAMPOS = {"schema": "schema", "version": "version", "labor_type": "labor_type", "span_m": "luz_min_m/luz_max_m",
          "author": "autor", "date": "fecha", "notes": "notas", "table.kind": "tipo_tabla", "table.method": "metodo",
          "table.base_edition": "edicion_base", "table.chart": "cartilla",
          "rating.base_edition": "edicion_puntajes"}


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
    return _at(f"sheet '{sheet}', row {n}", build, *args)


def _support_dicts(wb, sheet):
    rows = _sheet_rows(wb, sheet, TIPOS, {"codigo_tipo", "orden"},
                       {"orden", "perno_longitud_m", "perno_espaciamiento_m", "shotcrete_espesor_mm", "costo_relativo"},
                       {"shotcrete_fibra"})
    out = []
    for n, r in rows:
        # un elemento a medio llenar nunca se descarta en silencio
        vacias = [c for c in PERNO if r[c] is None]
        if 0 < len(vacias) < len(PERNO):
            raise ValueError(f"{_where(sheet, n, vacias[0])}: required when the bolt is given")
        sin_shot = not r["shotcrete_espesor_mm"]  # espesor vacío o 0 = sin shotcrete, salvo que pidan fibra
        if sin_shot and r["shotcrete_fibra"]:
            raise ValueError(f"{_where(sheet, n, 'shotcrete_espesor_mm')}: required when the shotcrete is given")
        out.append((n, {
            "code": r["codigo_tipo"], "order": r["orden"], "description": r["descripcion"] or "",
            "bolt": None if vacias else
            {"kind": r["perno_tipo"], "length_m": r["perno_longitud_m"], "spacing_m": r["perno_espaciamiento_m"]},
            "shotcrete": None if sin_shot else
            {"thickness_mm": r["shotcrete_espesor_mm"], "fiber": bool(r["shotcrete_fibra"])},
            "mesh": r["malla"], "arch": r["cimbra"], "relative_cost": r["costo_relativo"],
        }))
    return out


def _open(path):
    return _optional("openpyxl").load_workbook(path, read_only=True, data_only=True)


def _catalog(wb, sheet):
    """(dicts para from_dict, catálogo): valida fila por fila para ubicar la celda."""
    pairs = _support_dicts(wb, sheet)
    types = [_row(sheet, n, support_from_dict, d) for n, d in pairs]
    return [d for _, d in pairs], _at(f"sheet '{sheet}'", SupportCatalog, types)  # duplicados entre filas


def load_support_catalog_excel(path, sheet: str = "Tipos_sostenimiento") -> SupportCatalog:
    """Lee solo esa hoja; sirve también para la plantilla del histórico ya llena."""
    wb = _open(path)
    try:
        return _catalog(wb, sheet)[1]
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
    tipos = _catalog(wb, "Tipos_sostenimiento")[0]  # ubica errores de validación por fila
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
        d["table"] = {"kind": "cells", "chart": campos.get("cartilla"), "base_edition": campos.get("edicion_base"),
                      "cells": cells}
    else:
        raise ValueError(f"sheet 'Tabla': tipo_tabla must be 'range' or 'cells', got '{kind}'")
    d["correlations"] = [] if "Correlaciones" not in wb.sheetnames else [
        _corr(n, r) for n, r in _sheet_rows(wb, "Correlaciones", CORRELACIONES, {"nombre", "desde", "hacia", "forma"},
                                            {"a", "b", "valido_min", "valido_max"})]
    ed = campos.get("edicion_puntajes")
    if ed is None and "Puntajes" in wb.sheetnames and _sheet_rows(wb, "Puntajes", PUNTAJES, set(), set()):
        raise ValueError("sheet 'Tabla', campo 'edicion_puntajes': required when sheet 'Puntajes' exists")
    d["rating"] = None if ed is None else _puntajes(wb, ed)
    try:
        return from_dict(d)
    except ValueError as e:  # lo que queda por validar es de la hoja Tabla (o de la tabla de celdas entera)
        ruta, _, resto = str(e).partition(": ")
        if ruta.startswith("rating") and ruta not in CAMPOS:
            raise ValueError(f"sheet 'Puntajes': {str(e)}") from e
        if ruta in CAMPOS:
            raise ValueError(f"sheet 'Tabla', campo '{CAMPOS[ruta]}': {resto}") from e
        if ruta == "table":
            hoja = "sheet 'Tabla', campo 'metodo/edicion_base'" if kind == "range" else "sheet 'Celdas'"
            raise ValueError(f"{hoja}: {resto}") from e
        raise


def _clases(wb):
    pairs = _sheet_rows(wb, "Clases", CLASES, {"desde", "hasta", "clase"}, {"desde", "hasta"})
    for n, r in pairs:
        _row("Clases", n, RangeClass, r["desde"], r["hasta"], r["clase"], r["tipo"])
    return pairs


def _puntajes(wb, edicion):
    """Hoja Puntajes -> dict de rating; cada fila se valida con su constructor para ubicar hoja, fila y columna."""
    hoja = "Puntajes"
    filas = _sheet_rows(wb, hoja, PUNTAJES, {"tipo", "puntos"}, {"desde", "puntos"})
    params, ajustes = {}, {}
    for n, r in filas:
        tipo = r["tipo"]
        if tipo not in ("numerico", "categoria", "ajuste"):
            raise ValueError(f"{_where(hoja, n, 'tipo')}: expected 'numerico', 'categoria' or 'ajuste', got '{tipo}'")
        if tipo == "ajuste":
            if r["categoria"] is None:
                raise ValueError(f"{_where(hoja, n, 'categoria')}: required value is empty")
            if r["categoria"] in ajustes:
                raise ValueError(f"{_where(hoja, n, 'categoria')}: duplicate adjustment '{r['categoria']}'")
            ajustes[r["categoria"]] = r["puntos"]
            continue
        nombre = r["parametro"]
        if nombre is None:
            raise ValueError(f"{_where(hoja, n, 'parametro')}: required value is empty")
        if nombre in params and params[nombre]["kind"] != ("numeric" if tipo == "numerico" else "categorical"):
            raise ValueError(f"{_where(hoja, n, 'tipo')}: parameter '{nombre}' mixes numeric and category rows")
        if tipo == "categoria":
            if r["categoria"] is None:
                raise ValueError(f"{_where(hoja, n, 'categoria')}: required value is empty")
            p = params.setdefault(nombre, {"name": nombre, "kind": "categorical", "points": {}})
            if r["categoria"] in p["points"]:
                raise ValueError(f"{_where(hoja, n, 'categoria')}: duplicate category '{r['categoria']}' in '{nombre}'")
            p["points"][r["categoria"]] = r["puntos"]
            continue
        if r["desde"] is None:
            raise ValueError(f"{_where(hoja, n, 'desde')}: required value is empty")
        if r["mejor"] not in MEJOR:
            raise ValueError(f"{_where(hoja, n, 'mejor')}: expected 'mayor' or 'menor', got '{r['mejor']}'")
        p = params.setdefault(nombre, {"name": nombre, "kind": "numeric", "unit": r["unidad"] or "",
                                       "better": MEJOR[r["mejor"]], "bins": []})
        hi = r["hasta"]  # vacío = infinito, pero solo en el último intervalo (se revisa abajo)
        hi = None if hi is None else math.inf if hi.lower() == "inf" else _num(hi, hoja, n, "hasta")
        p["bins"].append({"lo": r["desde"], "hi": hi, "points": r["puntos"]})
        _row(hoja, n, RatingBin, r["desde"], math.inf if hi is None else hi, r["puntos"])
    for nombre, p in params.items():
        if p["kind"] != "numeric":
            continue
        for b in p["bins"][:-1]:
            if b["hi"] is None:
                raise ValueError(f"sheet '{hoja}', parameter '{nombre}': empty 'hasta' is only allowed in the last interval")
        if p["bins"][-1]["hi"] is None:
            p["bins"][-1]["hi"] = math.inf
        for b in p["bins"]:
            b["hi"] = "inf" if b["hi"] == math.inf else b["hi"]
    return {"base_edition": edicion, "params": list(params.values()), "adjustments": ajustes}


def _corr(n, r):
    d = {"name": r["nombre"], "from": r["desde"], "to": r["hacia"], "form": r["forma"], "a": r["a"], "b": r["b"],
         "valid_min": r["valido_min"], "valid_max": r["valido_max"], "source": r["fuente"] or ""}
    _row("Correlaciones", n, correlation_from_dict, d)  # mismo constructor que from_dict, solo para ubicar la fila
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
    rt = d["rating"]
    campos.append(("edicion_puntajes", rt and rt["base_edition"] or None))
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
    if rt:
        filas = []
        for p in rt["params"]:
            if p["kind"] == "numeric":
                filas += [(p["name"], "numerico", p["unit"] or None, "mayor" if p["better"] == "higher" else "menor",
                           b["lo"], b["hi"], None, b["points"]) for b in p["bins"]]
            else:
                filas += [(p["name"], "categoria", None, None, None, None, k, v) for k, v in p["points"].items()]
        filas += [(None, "ajuste", None, None, None, None, k, v) for k, v in rt["adjustments"].items()]
        sheet("Puntajes", PUNTAJES, filas)
    wb.save(path)
