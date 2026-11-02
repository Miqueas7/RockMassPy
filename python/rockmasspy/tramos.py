"""Lectura de la hoja Tramos (Excel o CSV) con un mapeo de columnas del usuario a las de la plantilla.

Reutiliza las fuentes de hojas de la 1C (_ExcelSource/_CsvSource) y el número con ubicación de la 1B (_num):
aquí no hay un segundo parser. Las columnas de identificación nunca aparecen en un mensaje de error.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .csv_io import _CsvSource
from .excel_io import _num, _open, _text, _where
from .gsi_charts import normalize_cell


@dataclass(frozen=True)
class Tramo:
    id_tramo: str
    tipo_labor: str
    labor_codigo: str | None
    zona_nivel: str | None
    fecha_evaluacion: str | None
    progresiva_inicio_m: float | None
    progresiva_fin_m: float | None
    este_m: float | None
    norte_m: float | None
    cota_m: float | None
    datum: str | None
    luz_m: float | None
    ucs_mpa: float | None
    rqd_pct: float | None
    jn: float | None
    jr: float | None
    ja: float | None
    jw: float | None
    srf: float | None
    rmr_valor: float | None
    rmr_edicion: str | None
    q_valor: float | None
    q_edicion: str | None
    gsi_valor: float | None
    gsi_celda: str | None
    sost_recomendado: str | None
    sost_instalado: str | None
    fila: int  # fila de origen (la cabecera es la 1), para ubicar errores


TRAMO_COLUMNS = tuple(n for n in Tramo.__dataclass_fields__ if n != "fila")
_TEXTO = {"id_tramo", "tipo_labor", "labor_codigo", "zona_nivel", "fecha_evaluacion", "datum", "rmr_edicion",
          "q_edicion", "gsi_celda", "sost_recomendado", "sost_instalado"}
_OBLIGATORIAS = ("id_tramo", "tipo_labor")
# nunca se muestran en un error; codigo_mina, evaluador_codigo y observaciones no se leen
_IDENT = {"labor_codigo", "zona_nivel", "este_m", "norte_m"}


def _norm(h):
    return "" if h is None else _text(h).casefold()


def _columnas(header, sheet, column_map):
    """{columna nuestra: posición en el archivo}; el mapeo va de la columna del usuario a la nuestra."""
    cmap = {}
    for k, v in (column_map or {}).items():
        if v not in TRAMO_COLUMNS:
            raise ValueError(f"column_map maps '{k}' to unknown name '{v}'; valid names: {', '.join(TRAMO_COLUMNS)}")
        cmap[_norm(k)] = v
    heads = [_norm(h) for h in header]
    for k in cmap:
        if k not in heads:
            raise ValueError(f"column '{k}' in column_map not found in sheet '{sheet}'")
    pos = {}
    for i, h in enumerate(heads):
        c = cmap.get(h, h if h in TRAMO_COLUMNS else None)
        if c is None:
            continue
        if c in pos:
            raise ValueError(f"sheet '{sheet}': two columns map to '{c}'")
        pos[c] = i
    for c in _OBLIGATORIAS:
        if c not in pos:
            extra = f" (column_map maps: {dict(column_map)})" if column_map else ""
            raise ValueError(f"sheet '{sheet}': required column '{c}' not found{extra}")
    return pos


def _leer(src, sheet, column_map):
    if sheet not in src.sheetnames:
        raise ValueError(src.missing(sheet))
    rows = iter(src.rows(sheet))
    pos = _columnas(next(rows, ()), sheet, column_map)
    dec = src.decimal_comma(sheet)
    out, vistos = [], {}
    for n, raw in enumerate(rows, start=2):
        vals = {}
        for c in TRAMO_COLUMNS:
            v = raw[pos[c]] if c in pos and pos[c] < len(raw) else None
            vals[c] = None if v is None or (isinstance(v, str) and not v.strip()) else v
        if all(v is None for v in vals.values()):
            continue
        for c, v in vals.items():
            if v is None:
                if c in _OBLIGATORIAS:
                    raise ValueError(f"{_where(sheet, n, c)}: required value is empty")
            elif c == "fecha_evaluacion":
                vals[c] = _text(src.date(v))
            elif c in _TEXTO:
                vals[c] = _text(v)
            else:
                try:
                    vals[c] = _num(v, sheet, n, c, dec)
                except ValueError:
                    if c in _IDENT:
                        raise ValueError(f"{_where(sheet, n, c)}: invalid value") from None
                    raise
        if vals["gsi_celda"] is not None:
            try:
                vals["gsi_celda"] = normalize_cell(vals["gsi_celda"])
            except ValueError as e:
                raise ValueError(f"{_where(sheet, n, 'gsi_celda')}: {e}") from None
        if vals["id_tramo"] in vistos:
            raise ValueError(f"sheet '{sheet}': duplicate id_tramo in rows {vistos[vals['id_tramo']]} and {n}")
        vistos[vals["id_tramo"]] = n
        out.append(Tramo(**vals, fila=n))
    return out


def load_tramos(path, *, sheet: str = "Tramos", column_map: Mapping[str, str] | None = None) -> list[Tramo]:
    """Lee los tramos de un .xlsx (hoja `sheet`) o de un .csv (la hoja es el archivo; su nombre sin .csv da la hoja)."""
    p = Path(path)
    if p.suffix.lower() == ".csv":
        return _leer(_CsvSource({p.stem: p}), p.stem, column_map)
    wb = _open(p)
    try:
        return _leer(wb, sheet, column_map)
    finally:
        wb.wb.close()
