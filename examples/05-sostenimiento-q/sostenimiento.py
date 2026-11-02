"""Sostenimiento con la carta Q (referencia) con datos sintéticos y el caso público de Hoek.

Necesita los extras: pip install "rockmasspy[io,viz,report]". La librería recomienda, el ingeniero decide.
Imprime solo el resumen (categorías, valores de fórmulas y nombres de archivo), nunca filas de tramos.
"""
import csv
import importlib.util
import sys
from pathlib import Path

import rockmasspy as rm
import rockmasspy.report as rp
from rockmasspy.cli import main as cli
from rockmasspy.q_support import recommend_q_support
from rockmasspy.viz import Style, plot_q_chart, save_figure

# Reutiliza el catálogo y las tablas del ejemplo 02 (la carpeta tiene guion: no se puede importar como paquete).
_spec = importlib.util.spec_from_file_location(
    "_ejemplo02_tabla", Path(__file__).resolve().parents[1] / "02-tabla-por-labor" / "tabla.py")
tabla = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tabla)

DATUM = "WGS84 UTM 18S"
# (rmr, q) de 6 galerías (luz 3.5 m) y (celda GSI, q) de 2 tajeos (luz 6 m); todo inventado.
_GALERIA = [(72, 12.0), (65, 6.0), (55, 2.5), (41, 0.9), (33, 0.3), (18, 0.04)]
_TAJEO = [("LF/B", 8.0), ("IF/P", 0.6)]


def filas_sinteticas() -> list[list]:
    filas = [list(rm.TRAMO_COLUMNS)]
    base = dict.fromkeys(rm.TRAMO_COLUMNS)

    def fila(**kw):
        d = {**base, "datum": DATUM, "cota_m": 3500.0, "fecha_evaluacion": "2026-11-01",
             "q_edicion": "Q-NGI-2025", **kw}
        filas.append([d[c] for c in rm.TRAMO_COLUMNS])

    for i, (rmr, q) in enumerate(_GALERIA):
        fila(id_tramo=f"G{i + 1:02d}", tipo_labor="galería", labor_codigo="LAB-A", luz_m=3.5, rmr_valor=rmr,
             rmr_edicion="RMR89", q_valor=q, progresiva_inicio_m=20 * i, progresiva_fin_m=20 * i + 20,
             este_m=500000.0 + 20 * i, norte_m=8600000.0)
    for i, (celda, q) in enumerate(_TAJEO):
        fila(id_tramo=f"T{i + 1:02d}", tipo_labor="tajeo", labor_codigo="LAB-B", luz_m=6.0, gsi_celda=celda,
             q_valor=q, progresiva_inicio_m=10 * i, progresiva_fin_m=10 * i + 10, este_m=500200.0,
             norte_m=8600100.0 + 10 * i)
    return filas


def escribir_tramos(filas, out_dir: Path) -> None:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Tramos"
    for f in filas:
        ws.append(f)
    wb.save(out_dir / "tramos.xlsx")
    with open(out_dir / "tramos.csv", "w", newline="", encoding="utf-8-sig") as fh:
        csv.writer(fh).writerows(["" if v is None else v for v in f] for f in filas)


def main(out_dir: Path) -> dict:
    out_dir = Path(out_dir)
    # 1. Cámara de Hoek (Q 4.5, luz 15 m, categoría ESR C). La carta fiel de NGI da la categoría 3; el 4 que
    #    publica Hoek sale de una carta anterior (1993).
    hoek = recommend_q_support(4.5, 15.0, esr_category="C")
    # 2. Mismas paredes en las dos ediciones: Q 0.4, luz 4.5 m, altura 4.5 m.
    w15 = recommend_q_support(0.4, 4.5, esr_category="C", edition="Q-NGI-2015", wall_height_m=4.5)
    w25 = recommend_q_support(0.4, 4.5, esr_category="C", wall_height_m=4.5)

    # 3. Lote: tramos sintéticos con Q, clasificados con tablas propias y con la referencia de la carta.
    escribir_tramos(filas_sinteticas(), out_dir)
    tablas = [tabla.tabla_galeria(tabla.catalogo()), tabla.tabla_tajeo(tabla.catalogo())]
    for nombre, t in (("galeria", tablas[0]), ("tajeo", tablas[1])):
        rm.save_json(t, out_dir / f"{nombre}.json")
    tramos = rm.load_tramos(out_dir / "tramos.xlsx")
    resultados = rm.add_q_chart_reference(rm.classify_tramos(tramos, tablas), {"*": "C"})
    rm.save_results(resultados, out_dir / "resultados.csv")
    rm.save_results(resultados, out_dir / "resultados.xlsx")

    # 4. Carta con los tramos (sin rótulos) y memoria con la sección 5.1.
    save_figure(plot_q_chart("Q-NGI-2025", results=resultados, style=Style(lang="es")), out_dir / "carta.png")
    memoria = rp.build_memoria(resultados, tablas, title="Informe sintético", author="", date="2026-11-01")
    rp.write_html(memoria, out_dir / "memoria.html")

    # 5. La misma tubería por la CLI.
    codigos = {
        "qsupport": cli(["qsupport", "--q", "4.5", "--span", "15", "--esr-category", "C",
                         "--chart", str(out_dir / "punto.png")]),
        "classify": cli(["classify", str(out_dir / "tramos.xlsx"), "--tables", str(out_dir / "galeria.json"),
                         str(out_dir / "tajeo.json"), "--esr", "*=C", "-o", str(out_dir / "resultados_cli.csv")]),
    }
    archivos = ["tramos.xlsx", "tramos.csv", "resultados.csv", "resultados.xlsx", "carta.png", "memoria.html",
                "punto.png", "resultados_cli.csv"]
    return {
        "hoek_category": hoek.roof.category, "max_span_m": hoek.max_unsupported_span.value,
        "bolt_length_m": hoek.bolt_length_formula.value,
        "walls_q_2015": w15.wall_q, "walls_q_2025": w25.wall_q,
        "tramos": len(resultados), "con_referencia": sum(r.q_chart is not None for r in resultados),
        "files": archivos, "exit_codes": codigos,
    }


if __name__ == "__main__":
    import tempfile
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp())
    destino.mkdir(parents=True, exist_ok=True)
    r = main(destino)
    print(f"Hoek: categoría {r['hoek_category']}, luz máxima {r['max_span_m']:.3g} m, perno {r['bolt_length_m']:.3g} m")
    print(f"paredes Q 0.4: 2015 -> {r['walls_q_2015']:g}, 2025 -> {r['walls_q_2025']:g}")
    print(f"tramos: {r['tramos']} (con referencia {r['con_referencia']})")
    print("archivos:", ", ".join(r["files"]), "->", destino)
