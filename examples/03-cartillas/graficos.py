"""Todos los gráficos de la fase 1C con datos sintéticos (inventados, de ninguna mina).

Necesita el extra de gráficos: pip install "rockmasspy[viz]". La librería recomienda, el ingeniero decide.
"""
import dataclasses
import importlib.util
import math
import random
import sys
from pathlib import Path

import rockmasspy as rm
import rockmasspy.viz as viz

# Reutiliza el catálogo y las tablas del ejemplo 02 (la carpeta tiene guion: no se puede importar como paquete).
_spec = importlib.util.spec_from_file_location(
    "_ejemplo02_tabla", Path(__file__).resolve().parents[1] / "02-tabla-por-labor" / "tabla.py")
tabla = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tabla)


def main(out_dir: Path) -> dict:
    out_dir = Path(out_dir)
    rnd = random.Random(42)  # semilla fija: las figuras salen siempre iguales
    cat = tabla.catalogo()
    galeria = tabla.tabla_galeria(cat)
    tajeo = dataclasses.replace(tabla.tabla_tajeo(cat), rating=rm.RatingTable.rmr89_default())

    vallejo = viz.Style(lang="es", size="cartilla", brand="Ejemplo sintético")
    a4 = viz.Style(lang="es", size="A4", brand="Ejemplo sintético")
    guardar = viz.save_figure

    fig = viz.plot_cartilla(tajeo, style=vallejo, title="Tajeo (sintético)")  # una figura, dos formatos
    guardar(fig, out_dir / "cartilla_celdas.png")
    guardar(fig, out_dir / "cartilla_celdas.pdf")
    guardar(viz.plot_cartilla(galeria, style=vallejo, title="Galería (sintético)"), out_dir / "cartilla_rango.png")

    # Cinco puntos (JCond89, RQD)
    guardar(viz.plot_gsi_quantified([(8, 30), (12, 50), (18, 65), (22, 80), (26, 92)],
                                    labels=["P1", "P2", "P3", "P4", "P5"], style=a4), out_dir / "gsi_cuantificada.svg")

    # Envolventes Hoek-Brown (HB-2018) con ensayos sintéticos alrededor de la curva
    sigma_ci, gsi, mi, d = 90.0, 59.5, 25, 0
    p = rm.hb_params(gsi, mi, d)
    s3max = rm.hb_sigma3max(rm.hb_global_strength(sigma_ci, p), 0.027, 400, rm.HbApplication.Tunnel)
    mc = rm.hb_mohr_coulomb(sigma_ci, p, s3max)
    ensayos = [(s3, rm.hb_sigma1(s3, sigma_ci, p) * rnd.uniform(0.95, 1.05)) for s3 in (0.0, 1.0, 3.0, 5.0)]
    guardar(viz.plot_hb_envelopes(sigma_ci, p, sigma3max_mpa=s3max, mc=mc, tests=ensayos, style=a4,
                                  gsi=gsi, mi=mi, d=d),  # HbParams no guarda GSI, mi ni D: van al pie
            out_dir / "envolventes.png")

    # Dispersión Q–RMR89 con la correlación global que va de Q a RMR89
    pares = []
    for _ in range(40):
        q = 10 ** rnd.uniform(-1, 1.7)
        pares.append((q, min(100.0, max(0.0, 9 * math.log(q) + 44 + rnd.gauss(0, 5)))))
    guardar(viz.plot_correlation(pares, x="Q", y="RMR89", global_correlations=[rm.Correlation.RmrFromQ_Huang2026],
                                 style=a4), out_dir / "correlacion.png")

    # Histograma de RMR89 por clase de la tabla de la galería
    rmr = [min(100.0, max(0.0, rnd.gauss(52, 15))) for _ in range(150)]
    guardar(viz.plot_class_histogram(rmr, galeria.table, catalog=cat, style=a4), out_dir / "histograma.png")

    # Tabla con `rating` a CSV (carpeta con una hoja por archivo) y de vuelta
    carpeta = rm.save_csv_dir(tajeo, out_dir / "tabla_csv")
    ok = rm.load_csv_dir(carpeta) == tajeo
    print("csv_roundtrip_ok", ok)

    archivos = ["cartilla_celdas.png", "cartilla_celdas.pdf", "cartilla_rango.png", "gsi_cuantificada.svg",
                "envolventes.png", "correlacion.png", "histograma.png"]
    return {"files": archivos, "csv_roundtrip_ok": ok}


if __name__ == "__main__":
    import tempfile
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp())
    destino.mkdir(parents=True, exist_ok=True)
    print(main(destino)["files"], "->", destino)
