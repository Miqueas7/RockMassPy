"""Exporta de FLAC3D, en formato largo, lo que RockMassPy lee con `load_external` (corre DENTRO de FLAC3D).

Uso: en FLAC3D, abre el modelo en la etapa que quieres exportar, ajusta las variables de abajo y ejecuta este
archivo con el Python integrado. Escribe desplazamientos por nodo y sigma1/sigma3 por zona (compresión positiva,
MPa); FLAC3D usa tracción positiva, por eso se invierte el signo. Solo se usan los arreglos documentados
(`gridpointarray.pos/disp`, `zonearray.pos/stress`); no se importa nada de RockMassPy.
"""
import csv

import itasca  # solo existe dentro de FLAC3D
import numpy as np

MODELO = "M1"            # nombre del modelo
ETAPA = "E1"             # etapa o paso que estás exportando
VERSION = ""             # versión de FLAC3D, opcional
SALIDA = "flac3d_resultados.csv"
UNIDAD_LONGITUD = "m"    # unidad de longitud del modelo: m, cm o mm
UNIDAD_ESFUERZO = "Pa"   # unidad de esfuerzo del modelo: Pa, kPa o MPa
# Función de itasca.zonearray con el estado plástico, si tu versión la trae (revisa el manual); None la omite.
# Se espera 1 en zonas en fluencia y 0 en las demás.
FUNCION_FLUENCIA = None

COLUMNAS = ["programa", "version", "modelo", "etapa", "tipo_objeto", "id", "x", "y", "z", "magnitud", "metodo",
            "valor", "unidad"]


def _tensores(s):
    s = np.asarray(s, dtype=float)
    if s.ndim != 3 or s.shape[1:] != (3, 3):  # solo zonearray.stress() (n, 3, 3); stress_flat() usa otro orden
        raise ValueError("zonearray.stress() must return an (n, 3, 3) array")
    return s


def exportar():
    filas = []
    base = ["FLAC3D", VERSION, MODELO, ETAPA]

    pos, disp = np.asarray(itasca.gridpointarray.pos(), float), np.asarray(itasca.gridpointarray.disp(), float)
    for i, (p, d) in enumerate(zip(pos, disp)):
        oid = f"N{i + 1}"
        vals = [("u_total_m", float(np.linalg.norm(d))), ("ux_m", d[0]), ("uy_m", d[1]), ("uz_m", d[2])]
        for q, v in vals:
            filas.append(base + ["node", oid, *p, q, "", float(v), UNIDAD_LONGITUD])

    zpos = np.asarray(itasca.zonearray.pos(), float)
    # tracción positiva es la convención general de FLAC para stress() (supuesto: confírmalo en tu versión)
    eig = np.linalg.eigvalsh(-_tensores(itasca.zonearray.stress()))  # compresión positiva; orden ascendente
    fluencia = None
    if FUNCION_FLUENCIA and hasattr(itasca.zonearray, FUNCION_FLUENCIA):
        fluencia = np.asarray(getattr(itasca.zonearray, FUNCION_FLUENCIA)())
    for i, p in enumerate(zpos):
        oid = f"Z{i + 1}"
        filas.append(base + ["zone", oid, *p, "sigma1_mpa", "", float(eig[i, 2]), UNIDAD_ESFUERZO])
        filas.append(base + ["zone", oid, *p, "sigma3_mpa", "", float(eig[i, 0]), UNIDAD_ESFUERZO])
        if fluencia is not None:
            filas.append(base + ["zone", oid, *p, "yielded", "", int(fluencia[i] > 0), "-"])

    with open(SALIDA, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNAS)
        w.writerows(filas)
    return len(filas)


print(f"FLAC3D: {exportar()} filas escritas")
