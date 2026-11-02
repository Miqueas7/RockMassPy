"""Tramos, clasificación por lote e informe Word/HTML con datos sintéticos (inventados, de ninguna mina).

Necesita los extras: pip install "rockmasspy[io,viz,report]". La librería recomienda, el ingeniero decide.
Imprime solo el resumen (conteos y nombres de archivo), nunca filas de tramos.
"""
import csv
import importlib.util
import sys
from pathlib import Path

import rockmasspy as rm
import rockmasspy.report as rp
from rockmasspy.cli import main as cli

# Reutiliza el catálogo y las tablas del ejemplo 02 (la carpeta tiene guion: no se puede importar como paquete).
_spec = importlib.util.spec_from_file_location(
    "_ejemplo02_tabla", Path(__file__).resolve().parents[1] / "02-tabla-por-labor" / "tabla.py")
tabla = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tabla)

DATUM = "WGS84 UTM 18S"
# Galería (RMR89, luz 3.5 m), tajeo (celdas GSI, luz 6 m) y una rampa que no tiene tabla (Foco 2).
_GALERIA = [(0, 72), (20, 65), (40, 55), (60, 41), (80, 33), (100, 18)]
_TAJEO = ["LF/B", "F/R", "MF/R", "IF/P", "T/MP"]


def filas_sinteticas() -> list[list]:
    """12 tramos en 2 labores, con coordenadas inventadas; la primera fila es la cabecera de la plantilla."""
    filas = [list(rm.TRAMO_COLUMNS)]
    base = dict.fromkeys(rm.TRAMO_COLUMNS)

    def fila(**kw):
        d = {**base, "datum": DATUM, "cota_m": 3500.0, "fecha_evaluacion": "2026-11-01", **kw}
        filas.append([d[c] for c in rm.TRAMO_COLUMNS])

    for i, (ini, rmr) in enumerate(_GALERIA):
        fila(id_tramo=f"G{i + 1:02d}", tipo_labor="galería", labor_codigo="LAB-A", luz_m=3.5, rmr_valor=rmr,
             rmr_edicion="RMR89", progresiva_inicio_m=ini, progresiva_fin_m=ini + 20, este_m=500000.0 + ini,
             norte_m=8600000.0 + 0.5 * ini)
    for i, celda in enumerate(_TAJEO):
        fila(id_tramo=f"T{i + 1:02d}", tipo_labor="tajeo", labor_codigo="LAB-B", luz_m=6.0, gsi_celda=celda,
             progresiva_inicio_m=10 * i, progresiva_fin_m=10 * i + 10, este_m=500200.0, norte_m=8600100.0 + 10 * i)
    fila(id_tramo="R01", tipo_labor="rampa", labor_codigo="LAB-A", luz_m=4.0, rmr_valor=50, rmr_edicion="RMR89",
         progresiva_inicio_m=120, progresiva_fin_m=140, este_m=500120.0, norte_m=8600060.0)
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
    escribir_tramos(filas_sinteticas(), out_dir)
    cat = tabla.catalogo()
    tablas = [tabla.tabla_galeria(cat), tabla.tabla_tajeo(cat)]
    for nombre, t in (("galeria", tablas[0]), ("tajeo", tablas[1])):
        rm.save_json(t, out_dir / f"{nombre}.json")

    tramos = rm.load_tramos(out_dir / "tramos.xlsx")
    assert [t.id_tramo for t in rm.load_tramos(out_dir / "tramos.csv")] == [t.id_tramo for t in tramos]
    resultados = rm.classify_tramos(tramos, tablas)
    resumen = rm.summarize(resultados)
    rm.save_results(resultados, out_dir / "resultados.xlsx")

    memoria = rp.build_memoria(resultados, tablas, title="Informe sintético", author="", date="2026-11-01")
    anexo = rp.build_anexo39b(resultados, tablas, title="Anexo 39 B sintético", labor_type="galería",
                              author="", date="2026-11-01")
    rp.write_html(memoria, out_dir / "memoria.html")
    rp.write_docx(memoria, out_dir / "memoria.docx")
    rp.write_html(anexo, out_dir / "anexo39b.html")
    rp.write_docx(anexo, out_dir / "anexo39b.docx")

    # La misma tubería por la CLI; sale 2 porque hay un tramo sin tabla (rampa).
    comun = [str(out_dir / "tramos.xlsx"), "--tables", str(out_dir / "galeria.json"), str(out_dir / "tajeo.json")]
    codigos = {
        "classify": cli(["classify", *comun, "-o", str(out_dir / "resultados_cli.csv")]),
        "report": cli(["report", *comun, "-o", str(out_dir / "memoria_cli.html")]),
    }
    archivos = ["tramos.xlsx", "tramos.csv", "resultados.xlsx", "memoria.html", "memoria.docx", "anexo39b.html",
                "anexo39b.docx", "resultados_cli.csv", "memoria_cli.html"]
    return {"files": archivos, "total": resumen.total, "classified": resumen.classified,
            "unclassified": resumen.unclassified, "exit_codes": codigos}


if __name__ == "__main__":
    import tempfile
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp())
    destino.mkdir(parents=True, exist_ok=True)
    r = main(destino)
    print(f"tramos: {r['total']} (clasificados {r['classified']}, sin clasificar {r['unclassified']})")
    print("archivos:", ", ".join(r["files"]), "->", destino)
