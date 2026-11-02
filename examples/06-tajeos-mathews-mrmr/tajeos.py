"""Tajeos con Mathews (Potvin) y MRMR de Laubscher con datos sintéticos.

Necesita los extras: pip install "rockmasspy[io,viz,report]". La librería recomienda, el ingeniero decide.
Imprime solo el resumen (zonas, N′, MRMR y nombres de archivo), nunca el contenido del archivo de caras.
"""
import csv
import sys
from pathlib import Path

import rockmasspy as rm
import rockmasspy.report as rp
from rockmasspy.cli import main as cli
from rockmasspy.viz import Style, plot_stability_graph, save_figure

# Seis caras de un tajeo inventado: q_prima, ucs, sigma1, dif. buzamiento, modo, inclinación, buz. junta, geometría.
_CARAS = [
    dict(id_superficie="Techo", q_prima=12.0, ucs_mpa=120, sigma1_mpa=30, dif_buz_junta_deg=60,
         modo_falla="gravedad", inclinacion_cara_deg=0, ancho_m=6, largo_m=20),
    dict(id_superficie="Pared-1", q_prima=8.0, ucs_mpa=120, sigma1_mpa=25, dif_buz_junta_deg=45,
         modo_falla="gravedad", inclinacion_cara_deg=90, ancho_m=15, largo_m=20),
    dict(id_superficie="Pared-2", q_prima=3.0, ucs_mpa=100, sigma1_mpa=30, dif_buz_junta_deg=30,
         modo_falla="gravedad", inclinacion_cara_deg=90, ancho_m=25, largo_m=40),
    dict(id_superficie="Pared-3", q_prima=6.0, ucs_mpa=110, sigma1_mpa=20, dif_buz_junta_deg=50,
         modo_falla="deslizamiento", buz_junta_deg=60, ancho_m=15, largo_m=30),
    dict(id_superficie="Cierre", q_prima=15.0, ucs_mpa=130, sigma1_mpa=20, dif_buz_junta_deg=80,
         modo_falla="gravedad", inclinacion_cara_deg=90, area_m2=120, perimetro_m=46),
    dict(id_superficie="Inclinada", q_prima=6.0, ucs_mpa=90, sigma1_mpa=35, dif_buz_junta_deg=20,
         modo_falla="gravedad", inclinacion_cara_deg=60, area_m2=300, perimetro_m=70),
]


def escribir_caras(out_dir: Path) -> Path:
    ruta = out_dir / "Superficies.csv"
    with open(ruta, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow([*rm.SURFACE_COLUMNS, "observaciones"])  # una columna ajena: la librería no la lee
        for c in _CARAS:
            w.writerow([*("" if c.get(k) is None else c[k] for k in rm.SURFACE_COLUMNS), "SECRETO-123"])
    return ruta


def main(out_dir: Path) -> dict:
    out_dir = Path(out_dir)
    # 1-2. Caras sintéticas: se leen, se evalúan y se guardan en CSV y Excel.
    caras = escribir_caras(out_dir)
    resultados = rm.assess_stope_surfaces(rm.load_stope_surfaces(caras))
    rm.save_stope_results(resultados, out_dir / "resultados.csv")
    rm.save_stope_results(resultados, out_dir / "resultados.xlsx")
    # 3. Gráfico de Mathews con las caras e informe HTML.
    casos = [(r.mathews.reading.x, r.mathews.reading.y) for r in resultados]
    graph = resultados[0].mathews.graph
    save_figure(plot_stability_graph(graph, cases=casos, style=Style(lang="es")), out_dir / "mathews.png")
    informe = rp.build_stope_report(resultados, title="Informe sintético de tajeos", date="2026-11-01")
    rp.write_html(informe, out_dir / "informe.html")
    # 4. MRMR del caso de la tarea 2 (IRS 100, RQD 75, espaciamientos 0.5/1/3 m) ubicado en el diagrama con HR = 30.
    i = rm.Mrmr90Input()
    i.irs_mpa, i.rqd_pct, i.spacings_m, i.joint_condition = 100, 75, [0.5, 1.0, 3.0], 10.8
    i.weathering_pct, i.orientation_pct, i.stress_pct, i.blasting_pct = 85, 75, 100, 90
    m = rm.mrmr90(i)
    lectura = rm.read_stability_graph("Laubscher1994-stability", 30.0, m.mrmr)
    save_figure(plot_stability_graph("Laubscher1994-stability", points=[(lectura.x, lectura.y)],
                                     style=Style(lang="es")), out_dir / "laubscher.png")
    # 5. Lo mismo por la CLI.
    codigos = {
        "mathews": cli(["mathews", str(caras), "--chart", str(out_dir / "mathews_cli.png")]),
        "mrmr": cli(["mrmr", "--irs", "100", "--rqd", "75", "--spacing", "0.5", "1.0", "3.0", "--jc", "10.8",
                     "--weathering", "85", "--orientation", "75", "--stress", "100", "--blasting", "90",
                     "--hr", "30", "--chart", str(out_dir / "laubscher_cli.png")]),
    }
    archivos = ["Superficies.csv", "resultados.csv", "resultados.xlsx", "mathews.png", "informe.html",
                "laubscher.png", "mathews_cli.png", "laubscher_cli.png"]
    return {
        "zones": rm.stope_zone_counts(resultados), "n_prime": [r.mathews.n_prime for r in resultados],
        "mrmr": m.mrmr, "mrmr_class": m.mrmr_class, "laubscher_zone": lectura.zone,
        "files": archivos, "exit_codes": codigos,
    }


if __name__ == "__main__":
    import tempfile
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp())
    destino.mkdir(parents=True, exist_ok=True)
    r = main(destino)
    print(f"zonas (estable, transición, hundimiento): {tuple(r['zones'].values())}")
    print("N′:", ", ".join(f"{n:.3g}" for n in r["n_prime"]))
    print(f"MRMR {r['mrmr']:.1f} (clase {r['mrmr_class']}), zona {r['laubscher_zone']} con HR 30 m")
    print("archivos:", ", ".join(r["files"]), "->", destino)
