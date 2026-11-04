"""Equilibrio límite 2D de dos secciones inventadas: un tajo de dos estratos y un botadero sobre una capa débil.

Necesita los extras: pip install "rockmasspy[io,viz,report]". La librería calcula, el ingeniero decide.
Todo es sintético: la geometría, los materiales y el registro de aceleraciones (un seno amortiguado generado aquí).
Imprime solo conteos, FS y nombres de archivo, nunca el contenido de los archivos de entrada.
"""
import csv
import math
import sys
from pathlib import Path

import rockmasspy as rm
import rockmasspy.report as rp
from rockmasspy.cli import main as cli

# Geometria (kN, kPa, m). T1: tajo de 80 m a 45 grados, la cara mira a la derecha; 15 m de suelo residual sobre roca.
# B1: botadero de 30 m a 1.5H:1V sobre 1.5 m de arcilla y luego la fundación; nivel freático en la base del botadero.
_GEOMETRIA = [
    ("T1", "superficie", [(0, 100), (60, 100), (140, 20), (220, 20)]),
    ("T1", "contacto", [(0, 85), (220, 85)]),
    ("B1", "superficie", [(0, 50), (60, 50), (105, 20), (200, 20)]),
    ("B1", "base_botadero", [(0, 20), (200, 20)]),
    ("B1", "base_arcilla", [(0, 18.5), (200, 18.5)]),
    ("B1", "arcilla", [(0, 19.25), (200, 19.25)]),  # línea débil: la búsqueda de bloque pone ahí su tramo de base
    ("B1", "piezometrica", [(0, 27), (105, 20), (200, 19.5)]),
]
_ESTRATOS = [["T1", 1, "residual", "contacto"], ["T1", 2, "roca", None],
             ["B1", 1, "desmonte", "base_botadero"], ["B1", 2, "arcilla", "base_arcilla"], ["B1", 3, "fundacion", None]]
# Solo se escriben las columnas que cada modelo usa
_MATERIALES = [
    dict(material="residual", modelo="mohr_coulomb", peso_unitario_kn_m3=21, cohesion_kpa=50, friccion_grados=32),
    dict(material="roca", modelo="hoek_brown", peso_unitario_kn_m3=25, sigma_ci_mpa=8, gsi=30, mi=10),
    dict(material="desmonte", modelo="mohr_coulomb", peso_unitario_kn_m3=19, cohesion_kpa=5, friccion_grados=38),
    dict(material="arcilla", modelo="mohr_coulomb", peso_unitario_kn_m3=18, cohesion_kpa=12, friccion_grados=21),
    dict(material="fundacion", modelo="mohr_coulomb", peso_unitario_kn_m3=22, cohesion_kpa=50, friccion_grados=35),
]
_ANALISIS = [
    dict(id_analisis="A1", id_seccion="T1", metodos="bishop;gle", superficie="circular", malla_x_min=70,
         malla_x_max=170, malla_y_min=100, malla_y_max=200, base_modelo_m=0, tajadas=25),
    dict(id_analisis="A2", id_seccion="B1", metodos="spencer;gle", superficie="bloque",
         linea_debil="arcilla", base_modelo_m=0, kh=0.1, registro="S1"),
]
# Registro sintético: a(t) = A e^(-t/tau) sin(2 pi f t), 20 s cada 0.01 s. No es un sismo real.
AMPLITUD_G, FRECUENCIA_HZ, TAU_S, DT_S, DURACION_S = 0.30, 1.5, 3.0, 0.01, 20.0


def registro_sintetico() -> list[tuple[float, float]]:
    n = int(round(DURACION_S / DT_S)) + 1
    t = [round(i * DT_S, 6) for i in range(n)]
    return [(x, AMPLITUD_G * math.exp(-x / TAU_S) * math.sin(2 * math.pi * FRECUENCIA_HZ * x)) for x in t]


def _escribir(ruta: Path, cabecera, filas) -> None:
    with open(ruta, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(cabecera)
        w.writerows(["" if v is None else v for v in f] for f in filas)


HOJAS = {"Geometria": "Geometria.csv", "Estratos": "Estratos.csv", "Materiales_LE": "Materiales_LE.csv",
         "Analisis_LE": "Analisis_LE.csv", "Sismos": "Sismos.csv"}


def escribir_entradas(out_dir: Path) -> dict:
    _escribir(out_dir / HOJAS["Geometria"], rm.GEOMETRY_COLUMNS,
              [[sec, linea, x, y] for sec, linea, pts in _GEOMETRIA for x, y in pts])
    _escribir(out_dir / HOJAS["Estratos"], rm.LAYER_COLUMNS, _ESTRATOS)
    _escribir(out_dir / HOJAS["Materiales_LE"], rm.MATERIAL_COLUMNS,
              [[m.get(c) for c in rm.MATERIAL_COLUMNS] for m in _MATERIALES])
    _escribir(out_dir / HOJAS["Analisis_LE"], rm.ANALYSIS_COLUMNS,
              [[a.get(c) for c in rm.ANALYSIS_COLUMNS] for a in _ANALISIS])
    _escribir(out_dir / HOJAS["Sismos"], rm.RECORD_COLUMNS, [["S1", t, a] for t, a in registro_sintetico()])
    return {hoja: out_dir / nombre for hoja, nombre in HOJAS.items()}


def main(out_dir: Path) -> dict:
    out_dir = Path(out_dir)
    # 1. Entradas sintéticas: 2 secciones, 5 estratos, 5 materiales, 2 análisis y un registro.
    hojas = escribir_entradas(out_dir)
    # 2. Evaluación: búsqueda circular en el tajo; de bloque, ky y Newmark en el botadero.
    rs = rm.assess_le(hojas)
    rm.save_le_results(rs, out_dir / "equilibrio_resultados.csv")
    archivos = [*HOJAS.values(), "equilibrio_resultados.csv"]
    try:  # matplotlib es opcional: la sección de cada análisis y el Newmark del botadero
        from rockmasspy.viz import save_figure
        for r in rs:
            nombre = f"seccion_le_{r.order}.png"
            save_figure(rp.le_figure(r, "es"), out_dir / nombre)
            archivos.append(nombre)
            if r.newmark is not None:
                nombre = f"newmark_{r.order}.png"
                save_figure(rp.newmark_figure(r, "es"), out_dir / nombre)
                archivos.append(nombre)
    except ImportError:
        pass
    rep = rp.build_slope_report([], title="Equilibrio límite sintético", lang="es", le=rs)
    rp.write_html(rep, out_dir / "equilibrio.html")
    archivos.append("equilibrio.html")
    try:
        rp.write_docx(rep, out_dir / "equilibrio.docx")
        archivos.append("equilibrio.docx")
    except ImportError:  # python-docx es opcional
        pass
    # 3. Lo mismo por la CLI.
    cli_exit = cli(["le", "--geometry", str(hojas["Geometria"]), "--layers", str(hojas["Estratos"]),
                    "--materials", str(hojas["Materiales_LE"]), "--analyses", str(hojas["Analisis_LE"]),
                    "--records", str(hojas["Sismos"])])
    botadero = rs[1]
    return {"le_counts": rm.le_counts(rs),
            "fs": [{x.info.method_id: x.factor_of_safety for x in r.results} for r in rs],  # por orden de análisis
            "fs_min": [r.fs_min for r in rs], "fs_static_botadero": botadero.yield_.fs_static,
            "ky": botadero.yield_.ky, "newmark_m": botadero.newmark.displacement_m,
            "attention": [rm.le_attention(r) for r in rs], "cli_exit": cli_exit, "files": archivos}


if __name__ == "__main__":
    import tempfile
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp())
    destino.mkdir(parents=True, exist_ok=True)
    r = main(destino)
    c = r["le_counts"]
    print("análisis:", c["analyses"], "| circular", c["circular"], "| bloque", c["block"], "| con Newmark",
          c["with_newmark"], "| con FS <= 1:", c["fs_below_1"], "| avisos", c["warnings"], "| notas", c["notes"])
    for k, fs in enumerate(r["fs"], start=1):
        print(f"análisis {k}:", ", ".join(f"{m} {v:.3f}" for m, v in fs.items()))
    print(f"botadero: FS de la crítica estática {r['fs_static_botadero']:.3f}, ky {r['ky']:.4f}, "
          f"Newmark {r['newmark_m'] * 100:.1f} cm")
    print(f"código de salida de la CLI: {r['cli_exit']}")
    print("archivos:", ", ".join(r["files"]), "->", destino)
