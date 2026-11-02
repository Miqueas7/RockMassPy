"""Declaraciones de diseño que las reglas de `verify` inspeccionan: los tipos y el lector de archivos (`load_design_inputs`).

Cada tipo valida en `__post_init__` con ValueError que nombra el campo y nunca el valor. Los identificadores
de fila (`id_refugio`, `id_via`, `id_analisis`) no salen en ningún mensaje de la verificación.
"""
from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .excel_io import _where
from .intact_rock import _strip

REFUGE_TYPES = ("roca", "movil")
VIAS = ("galeria", "rampa", "otra")
GEOMETRIES = ("tangente_larga", "tangente_corta", "curva")
TERMS = ("corto", "mediano", "largo")


def _num(obj, name, *, lo=None, hi=None, positive=False):
    v = getattr(obj, name)
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ValueError(f"{name}: must be a finite number")
    if positive and v <= 0:
        raise ValueError(f"{name}: must be > 0")
    if lo is not None and v < lo or hi is not None and v > hi:
        raise ValueError(f"{name}: out of range")


def _int(obj, name, minimum):
    v = getattr(obj, name)
    if isinstance(v, bool) or not isinstance(v, int) or v < minimum:
        raise ValueError(f"{name}: must be an integer >= {minimum}")


def _text(obj, name, allowed=None):
    v = getattr(obj, name)
    if not isinstance(v, str) or not v.strip() or (allowed is not None and v not in allowed):
        raise ValueError(f"{name}: " + (f"must be one of {allowed}" if allowed else "required text"))


@dataclass(frozen=True)
class RefugeStation:
    id_refugio: str
    tipo: str
    rmr: float
    distancia_frente_m: float
    area_m2: float
    aforo: int
    sostenido: bool = False
    fila: int = 0

    def __post_init__(self):
        _text(self, "id_refugio")
        _text(self, "tipo", REFUGE_TYPES)
        _num(self, "rmr", lo=0, hi=100)
        _num(self, "distancia_frente_m", lo=0)
        _num(self, "area_m2", positive=True)
        _int(self, "aforo", 1)
        if not isinstance(self.sostenido, bool):
            raise ValueError("sostenido: must be true or false")


@dataclass(frozen=True)
class PedestrianRefugeSpacing:
    id_via: str
    via: str
    espaciado_max_m: float
    geometria: str | None = None
    fila: int = 0

    def __post_init__(self):
        _text(self, "id_via")
        _text(self, "via", VIAS)
        _num(self, "espaciado_max_m", positive=True)
        if (self.via == "rampa") != (self.geometria is not None):
            raise ValueError("geometria: required if and only if via is rampa")
        if self.geometria is not None:
            _text(self, "geometria", GEOMETRIES)


@dataclass(frozen=True)
class QcMonth:
    periodo: str
    sostenimiento: str
    instalados: int
    ensayados: int
    fila: int = 0

    def __post_init__(self):
        if not isinstance(self.periodo, str) or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", self.periodo):
            raise ValueError("periodo: expected yyyy-mm with month 01 to 12")
        _text(self, "sostenimiento")
        _int(self, "instalados", 0)
        _int(self, "ensayados", 0)


@dataclass(frozen=True)
class SafetyFactor:
    id_analisis: str
    plazo: str
    fs: float
    fila: int = 0

    def __post_init__(self):
        _text(self, "id_analisis")
        _text(self, "plazo", TERMS)
        _num(self, "fs", positive=True)


@dataclass(frozen=True)
class StandupTime:
    tipo_labor: str
    autosoporte_h: float
    fila: int = 0

    def __post_init__(self):
        _text(self, "tipo_labor")
        _num(self, "autosoporte_h", positive=True)


@dataclass(frozen=True)
class DesignInputs:
    refuge_stations: tuple = ()
    pedestrian_refuges: tuple = ()
    qc: tuple = ()
    safety_factors: tuple = ()
    standup: tuple = ()


# hoja -> (campo de DesignInputs, tipo, columnas, obligatorias, numéricas, id_column)
DESIGN_SHEETS = {
    "Estaciones_refugio": ("refuge_stations", RefugeStation,
                           ("id_refugio", "tipo", "rmr", "distancia_frente_m", "area_m2", "aforo", "sostenido"),
                           ("id_refugio", "tipo", "rmr", "distancia_frente_m", "area_m2", "aforo"),
                           ("rmr", "distancia_frente_m", "area_m2", "aforo"), "id_refugio"),
    "Refugios_peatonales": ("pedestrian_refuges", PedestrianRefugeSpacing,
                            ("id_via", "via", "geometria", "espaciado_max_m"),
                            ("id_via", "via", "espaciado_max_m"), ("espaciado_max_m",), "id_via"),
    "Resumen_QC": ("qc", QcMonth, ("periodo", "sostenimiento", "instalados", "ensayados"),
                   ("periodo", "sostenimiento", "instalados", "ensayados"), ("instalados", "ensayados"), None),
    "Factores_seguridad": ("safety_factors", SafetyFactor, ("id_analisis", "plazo", "fs"),
                           ("id_analisis", "plazo", "fs"), ("fs",), "id_analisis"),
    "Autosoporte": ("standup", StandupTime, ("tipo_labor", "autosoporte_h"), ("tipo_labor", "autosoporte_h"),
                    ("autosoporte_h",), None),
}
_SI_NO = {"si": True, "no": False}


def _norm_text(s):
    return _strip(s).casefold()


def _read_sheet(src, sheet):
    from .tramos import read_records  # import perezoso: tramos no depende de este módulo
    campo, tipo, columns, required, numeric, id_column = DESIGN_SHEETS[sheet]
    text = tuple(c for c in columns if c not in numeric)
    # los números también van como `ident`: un valor inválido nunca se repite en el mensaje
    recs = read_records(src, sheet, None, columns=columns, text=text, required=required, ident=numeric,
                        id_column=id_column, dates=("periodo",) if sheet == "Resumen_QC" else ())
    out, vistos = [], {}
    for n, vals in recs:
        for c, v in vals.items():
            if v is None or c == id_column or c.startswith("id_") or c in numeric:
                continue
            vals[c] = _norm_text(v)
        if "sostenido" in vals:
            s = vals["sostenido"]
            if s not in (None, "si", "no"):
                raise ValueError(f"{_where(sheet, n, 'sostenido')}: expected si or no")
            vals["sostenido"] = _SI_NO.get(s, False)
        if sheet == "Resumen_QC":
            vals["periodo"] = re.sub(r"^(\d{4}-\d{2})-\d{2}$", r"\1", vals["periodo"])
        for c in ("aforo", "instalados", "ensayados"):
            if vals.get(c) is not None and float(vals[c]).is_integer():
                vals[c] = int(vals[c])  # 2.5 queda decimal y lo rechaza el tipo
        try:
            obj = tipo(**vals, fila=n)
        except ValueError as e:
            col, _, motivo = str(e).partition(": ")
            raise ValueError(f"{_where(sheet, n, col)}: {motivo}") from None
        if sheet == "Resumen_QC":
            clave = (obj.periodo, obj.sostenimiento)
            if clave in vistos:
                raise ValueError(f"{_where(sheet, n, 'sostenimiento')}: (periodo, sostenimiento) repeated from row "
                                 f"{vistos[clave]}")
            vistos[clave] = n
        out.append(obj)
    return campo, tuple(out)


def load_design_inputs(paths: Sequence[str | Path]) -> DesignInputs:
    """Lee las declaraciones de diseño: un .xlsx con hojas de DESIGN_SHEETS o un .csv por hoja (el nombre es la hoja)."""
    from .csv_io import _CsvSource
    from .excel_io import _open
    nombres = ", ".join(DESIGN_SHEETS)
    canon = {k.casefold(): k for k in DESIGN_SHEETS}
    campos = {}
    for path in paths:
        p = Path(path)
        ext = p.suffix.lower()
        if ext == ".csv":
            hoja = canon.get(p.stem.casefold())
            if hoja is None:
                raise ValueError(f"{p.name}: the file name must be one of the design sheets: {nombres}")
            fuentes = [(_CsvSource({hoja: p}), [hoja], None)]
        elif ext == ".xlsx":
            wb = _open(p)
            hojas = [h for h in DESIGN_SHEETS if h in wb.sheetnames]
            if not hojas:
                wb.wb.close()
                raise ValueError(f"{p.name}: no design sheet found; expected at least one of: {nombres}")
            fuentes = [(wb, hojas, wb.wb)]
        else:
            raise ValueError(f"{p.name}: unsupported file type '{p.suffix}'; save it as .xlsx or .csv")
        for src, hojas, cierre in fuentes:
            try:
                for h in hojas:
                    campo, filas = _read_sheet(src, h)
                    if campo in campos:
                        raise ValueError(f"{p.name}: sheet '{h}' given more than once")
                    campos[campo] = filas
            finally:
                if cierre is not None:
                    cierre.close()
    return DesignInputs(**campos)
