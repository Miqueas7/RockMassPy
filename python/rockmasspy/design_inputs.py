"""Declaraciones de diseño que las reglas de `verify` inspeccionan (solo los tipos; el lector va en la tarea 4).

Cada tipo valida en `__post_init__` con ValueError que nombra el campo y nunca el valor. Los identificadores
de fila (`id_refugio`, `id_via`, `id_analisis`) no salen en ningún mensaje de la verificación.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

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
