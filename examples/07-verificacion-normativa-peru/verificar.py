"""Verificación contra el perfil normativo de Perú (DS 024-2016-EM) con datos sintéticos.

Necesita los extras: pip install "rockmasspy[io,viz,report]". La librería recomienda, el ingeniero decide.
Imprime solo conteos y nombres de archivo, nunca el contenido de los archivos de entrada.
"""
import csv
import sys
from pathlib import Path

import rockmasspy as rm
import rockmasspy.report as rp
from rockmasspy.cli import main as cli
from rockmasspy.design_inputs import load_design_inputs
from rockmasspy.normative import get_profile
from rockmasspy.verify import verify

PERFIL, FECHA = "PE-DS024-2016", "2026-11-02"

# Cada hoja de diseño trae al menos una fila que no cumple (todo inventado).
_DISENO = {
    "Estaciones_refugio": (
        ["id_refugio", "tipo", "rmr", "distancia_frente_m", "area_m2", "aforo", "sostenido"],
        [["R01", "roca", 70, 400, 30, 20, "no"],      # cumple
         ["R02", "roca", 55, 350, 30, 20, "no"],      # RMR bajo 60 sin sostenimiento: no cumple
         ["R03", "roca", 65, 620, 30, 20, "no"],      # más de 500 m del frente: no cumple
         ["R04", "movil", 65, 300, 12, 10, "no"]]),   # 1.2 m2 por persona: no cumple
    "Refugios_peatonales": (
        ["id_via", "via", "geometria", "espaciado_max_m"],
        [["V01", "galeria", "", 50],                  # justo 50 m: cumple
         ["V02", "galeria", "", 65],                  # no cumple
         ["V03", "rampa", "curva", 30.5]]),           # curva a 30.5 m: no cumple
    "Resumen_QC": (
        ["periodo", "sostenimiento", "instalados", "ensayados"],
        [["2026-09", "pernos", 100, 1],               # 1 %: cumple
         ["2026-10", "pernos", 101, 1]]),             # menos de 1 %: no cumple
    "Factores_seguridad": (
        ["id_analisis", "plazo", "fs"],
        [["A01", "corto", 1.1], ["A02", "mediano", 1.2], ["A03", "largo", 1.5]]),  # los dos últimos piden atención
    "Autosoporte": (
        ["tipo_labor", "autosoporte_h"],
        [["galeria", 12], ["rampa", 40]]),            # 12 h: pide atención
}

# (id, tipo, luz, RMR, Q) de 8 tramos inventados; el último tiene la luz fuera del rango de su tabla.
_TRAMOS = [
    ("G01", "galería", 3.5, 72, None), ("G02", "galería", 3.5, 65, None), ("G03", "galería", 3.2, 55, None),
    ("G04", "galería", 3.8, 41, None), ("G05", "galería", 3.5, 33, None),
    ("P01", "rampa", 4.5, None, 6.0), ("P02", "rampa", 5.0, None, 2.5), ("P03", "rampa", 7.5, None, 0.8),
]

# Tres caras de un tajeo inventado.
_CARAS = [
    dict(id_superficie="C01", q_prima=12.0, ucs_mpa=120, sigma1_mpa=30, dif_buz_junta_deg=60,
         modo_falla="gravedad", inclinacion_cara_deg=0, ancho_m=6, largo_m=20),
    dict(id_superficie="C02", q_prima=3.0, ucs_mpa=100, sigma1_mpa=30, dif_buz_junta_deg=30,
         modo_falla="gravedad", inclinacion_cara_deg=90, ancho_m=25, largo_m=40),
    dict(id_superficie="C03", q_prima=6.0, ucs_mpa=110, sigma1_mpa=20, dif_buz_junta_deg=50,
         modo_falla="deslizamiento", buz_junta_deg=60, ancho_m=15, largo_m=30),
]


def _csv(ruta: Path, cabecera, filas) -> None:
    with open(ruta, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(cabecera)
        w.writerows(["" if v is None else v for v in f] for f in filas)


def escribir_entradas(out_dir: Path) -> dict:
    cat = rm.SupportCatalog([rm.SupportType("I", 1, "sin sostenimiento sistemático"),
                             rm.SupportType("II", 2, "pernos puntuales", bolt=rm.Bolt("split-set", 1.8, 1.5)),
                             rm.SupportType("III", 3, "pernos y shotcrete", bolt=rm.Bolt("helicoidal", 2.4, 1.0),
                                            shotcrete=rm.Shotcrete(50))])
    galeria = rm.LaborTable("galería", cat, rm.RangeTable("RMR", "RMR89", [
        rm.RangeClass(60, 100, "I", "I"), rm.RangeClass(40, 60, "II", "II"), rm.RangeClass(0, 40, "III", "III")]),
        span_m=(3.0, 4.0), author="ejemplo", date="2026-11-02")
    rampa = rm.LaborTable("rampa", cat, rm.RangeTable("Q", "Q-NGI-2025", [
        rm.RangeClass(4, 1000, "I", "I"), rm.RangeClass(1, 4, "II", "II"), rm.RangeClass(0, 1, "III", "III")]),
        span_m=(4.0, 6.0), author="ejemplo", date="2026-11-02")
    for nombre, t in (("galeria", galeria), ("rampa", rampa)):
        rm.save_json(t, out_dir / f"{nombre}.json")
    base = dict.fromkeys(rm.TRAMO_COLUMNS)
    filas = []
    for i, (idt, tipo, luz, rmr, q) in enumerate(_TRAMOS):
        d = {**base, "id_tramo": idt, "tipo_labor": tipo, "luz_m": luz, "rmr_valor": rmr, "rmr_edicion": "RMR89" if rmr else None,
             "q_valor": q, "q_edicion": "Q-NGI-2025" if q else None, "fecha_evaluacion": "2026-11-01",
             "progresiva_inicio_m": 20 * i, "progresiva_fin_m": 20 * i + 20, "datum": "WGS84 UTM 18S", "cota_m": 3500.0}
        filas.append([d[c] for c in rm.TRAMO_COLUMNS])
    _csv(out_dir / "Tramos.csv", rm.TRAMO_COLUMNS, filas)
    _csv(out_dir / "Superficies.csv", rm.SURFACE_COLUMNS, [[c.get(k) for k in rm.SURFACE_COLUMNS] for c in _CARAS])
    for hoja, (cab, filas) in _DISENO.items():
        _csv(out_dir / f"{hoja}.csv", cab, filas)
    return {"tables": [out_dir / "galeria.json", out_dir / "rampa.json"]}


def main(out_dir: Path) -> dict:
    out_dir = Path(out_dir)
    # 1. Entradas sintéticas: dos tablas, 8 tramos, 3 caras y los cinco CSV de diseño.
    tablas = [rm.load_table(p) for p in escribir_entradas(out_dir)["tables"]]
    tramos = rm.load_tramos(out_dir / "Tramos.csv")
    resultados = rm.add_q_chart_reference(rm.classify_tramos(tramos, tablas), {"*": "C"})
    caras = rm.assess_stope_surfaces(rm.load_stope_surfaces(out_dir / "Superficies.csv"))
    diseno = load_design_inputs([out_dir / f"{h}.csv" for h in _DISENO])
    # 2. Verificación con el perfil Perú y su informe.
    v = verify(get_profile(PERFIL), as_of=FECHA, tables=tablas, results=resultados, stopes=caras, design=diseno)
    rep = rp.build_verification_report(v, title="Verificación sintética", date=FECHA)
    archivos = [f"{h}.csv" for h in _DISENO] + ["Tramos.csv", "Superficies.csv", "galeria.json", "rampa.json"]
    rp.write_html(rep, out_dir / "verificacion.html")
    archivos.append("verificacion.html")
    try:
        rp.write_docx(rep, out_dir / "verificacion.docx")
        archivos.append("verificacion.docx")
    except ImportError:  # python-docx es opcional
        pass
    # 3. Lo mismo por la CLI.
    cli_exit = cli(["verify", "--profile", PERFIL, "--as-of", FECHA, "--tables", *map(str, (out_dir / "galeria.json", out_dir / "rampa.json")),
                    "--tramos", str(out_dir / "Tramos.csv"), "--surfaces", str(out_dir / "Superficies.csv"),
                    "--design", *(str(out_dir / f"{h}.csv") for h in _DISENO), "--report", str(out_dir / "verificacion_cli.html")])
    archivos.append("verificacion_cli.html")
    return {"counts": v.counts(), "verify_exit": v.exit_code, "cli_exit": cli_exit, "files": archivos}


if __name__ == "__main__":
    import tempfile
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp())
    destino.mkdir(parents=True, exist_ok=True)
    r = main(destino)
    print("estados:", ", ".join(f"{k} {n}" for k, n in r["counts"].items()))
    print(f"códigos de salida: verify {r['verify_exit']}, CLI {r['cli_exit']}")
    print("archivos:", ", ".join(r["files"]), "->", destino)
