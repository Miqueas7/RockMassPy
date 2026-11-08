"""Escribe las entradas sintéticas del ejemplo 14: la hoja Tramos y la hoja Distribuciones (todo inventado)."""
from pathlib import Path

import openpyxl

import rockmasspy as rm

# id_tramo, tipo_labor, luz_m, rmr_valor, jn, jr, ja, jw, srf
TRAMOS = [
    ("ZZSENT-1", "galeria", 4.0, 41.0) + (None,) * 5,
    ("ZZSENT-2", "galeria", 4.0, 58.0) + (None,) * 5,
    ("ZZSENT-3", "galeria", 4.0, 75.0) + (None,) * 5,
    ("ZZSENT-4", "crucero", 4.0, None, 9, 1.5, 2, 1, 2.5),
    ("ZZSENT-5", "crucero", 4.0, None, 9, 3, 1, 1, 2.5),
    ("ZZSENT-6", "crucero", 4.0, None, 4, 3, 1, 1, 1),
]
# id_tramo, variable, distribucion, media, desviacion, minimo, maximo
DISTRIBUCIONES = [
    ("ZZSENT-1", "rmr_valor", "normal", 41.0, 4.0, 30.0, 55.0),
    ("ZZSENT-2", "rmr_valor", "normal", 58.0, 5.0, 45.0, 72.0),
    ("ZZSENT-3", "rmr_valor", "normal", 75.0, 4.0, 62.0, 88.0),
    ("ZZSENT-4", "ja", "uniforme", None, None, 1.0, 4.0),
    ("ZZSENT-5", "jn", "normal", 9.0, 1.5, 6.0, 12.0),
    ("ZZSENT-6", "srf", "uniforme", None, None, 1.0, 2.5),
]


def escribir(ruta: Path) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Tramos"
    ws.append(list(rm.TRAMO_COLUMNS))
    for i, (idt, labor, luz, rmr, jn, jr, ja, jw, srf) in enumerate(TRAMOS):
        fila = dict.fromkeys(rm.TRAMO_COLUMNS)
        fila.update(id_tramo=idt, tipo_labor=labor, luz_m=luz, rmr_valor=rmr, rmr_edicion="RMR89" if rmr else None,
                    rqd_pct=90.0 if jn else None, jn=jn, jr=jr, ja=ja, jw=jw, srf=srf)
        ws.append([fila[c] for c in rm.TRAMO_COLUMNS])
    wd = wb.create_sheet("Distribuciones")
    wd.append(["id_tramo", "variable", "distribucion", "media", "desviacion", "minimo", "maximo"])
    for r in DISTRIBUCIONES:
        wd.append(list(r))
    wb.save(ruta)
    return ruta
