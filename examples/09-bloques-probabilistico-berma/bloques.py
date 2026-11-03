"""Bloques de un tajo inventado: planar con PoF y retroanálisis, cuña, volteo y banco-berma, con datos sintéticos.

Necesita los extras: pip install "rockmasspy[io,viz,report]". La librería calcula, el ingeniero decide.
Los números salen de casos publicados (Hoek 2023 cap. 9, SWedge, Goodman y Bray 1976, Ryan y Pryor 2000) pasados a kN.
Imprime solo conteos y nombres de archivo, nunca el contenido de los archivos de entrada.
"""
import csv
import sys
from pathlib import Path

import rockmasspy as rm
import rockmasspy.report as rp
from rockmasspy.cli import main as cli

SEMILLA = 9
ITERACIONES = 5000

# Familias: una fila por plano, así que la media de Fisher es el plano mismo.
# T01: P1 35/180 (el plano de Sau Mau Ping), P2 60/180 (más empinado que la cara 1: no forma bloque) y V1 para el volteo.
# T02: las dos juntas de la cuña CU-2 de SWedge (Priest 1993, ej. 1).
_FAMILIAS = [["T01", "P1", 35, 180], ["T01", "P2", 60, 180], ["T01", "V1", 75, 0],
             ["T02", "J1", 47, 203], ["T02", "J2", 52, 287]]
_CABECERA_TALUDES = ["id_talud", "id_tramo", "buz_cara_grados", "dir_buz_cara_grados", "friccion_grados",
                     "limite_lateral_grados", "rmr_basico", "excavacion"]
# TL1: cara de Sau Mau Ping (50/180); TL2: cara de la cuña CU-2 (60/230); TL3: cara de 65 grados del banco de Ryan y Pryor.
_TALUDES = [["TL1", "T01", 50, 180, 35, 30, 60, "voladura_normal"],
            ["TL2", "T02", 60, 230, 35, 30, 60, "voladura_normal"],
            ["TL3", "T01", 65, 180, 35, 30, 60, "voladura_normal"]]

# Bloques (kN, kPa, kN/m3, m). Solo se escriben las columnas que cada modelo usa.
_BLOQUES = [
    # B1: Sau Mau Ping (RocPlane problema 1): grieta crítica al 90 % de agua, sismo 0.08, retroanálisis; FS 1.065
    dict(id_bloque="B1", id_talud="TL1", modelo="planar", altura_m=60, peso_unitario_kn_m3=27, peso_agua_kn_m3=10,
         familia_1="P1", cohesion_1_kpa=100, friccion_1_grados=35, dist_grieta_m=15.3358, llenado_agua=0.9, kh=0.08,
         retroanalisis="si"),
    # B2: cuña CU-2 (SWedge problema 6): FS 1.4966
    dict(id_bloque="B2", id_talud="TL2", modelo="cuña", altura_m=6.7978, peso_unitario_kn_m3=26, familia_1="J1",
         familia_2="J2", cohesion_1_kpa=10, friccion_1_grados=40, cohesion_2_kpa=20, friccion_2_grados=35,
         presion_1_kpa=5, presion_2_kpa=15, carga_kn=180, carga_tendencia_grados=168, carga_inmersion_grados=70,
         buz_sup_grados=5, dir_sup_grados=225),
    # B3: volteo con la geometría regular de VO-1 (Goodman y Bray ejemplo 1b, cable en el pie); FS 0.99986 (publicado 1.0)
    dict(id_bloque="B3", id_talud="TL3", modelo="volteo", peso_unitario_kn_m3=25, friccion_1_grados=33.02,
         ancho_bloque_m=10, buz_base_grados=30, a1_m=5, a2_m=5, b_m=1, n_bloques=16, bloque_cresta=10,
         soporte_kn_m=2013, soporte_inclinacion_grados=0),
    # B4: berma de 12 m en un banco de 12 m con cara de 65 grados; el ancho requerido es el de Ritchie (6.9 m)
    dict(id_bloque="B4", id_talud="TL3", modelo="berma", altura_banco_m=12, ancho_berma_m=12),
    # B5: plano de 60 grados bajo una cara de 50: el bloque no se forma
    dict(id_bloque="B5", id_talud="TL1", modelo="planar", altura_m=30, peso_unitario_kn_m3=27, familia_1="P2",
         cohesion_1_kpa=50, friccion_1_grados=30),
]
# Las cinco variables de Sau Mau Ping (Hoek 2023, cap. 9; c de 10 t/m2 pasada a 100 kPa) y la cara de la berma
_DISTRIBUCIONES = [
    ["B1", "friccion_1_grados", "normal", 35, 5, 15, 70],
    ["B1", "cohesion_1_kpa", "normal", 100, 20, 0, 250],
    ["B1", "dist_grieta_m", "normal", 15.3, 4, 0, 35.34],
    ["B1", "llenado_agua", "exponencial", 0.5, "", 0, 1],
    ["B1", "kh", "exponencial", 0.08, "", 0, 0.16],
    ["B4", "buz_cara_grados", "normal", 65, 10, 39, 81],
]


def _escribir(ruta: Path, cabecera, filas) -> None:
    with open(ruta, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(cabecera)
        w.writerows(["" if v is None else v for v in f] for f in filas)


def escribir_entradas(out_dir: Path) -> None:
    _escribir(out_dir / "Familias.csv", ["id_tramo", "familia", "buzamiento_grados", "dir_buzamiento_grados"],
              _FAMILIAS)
    _escribir(out_dir / "Taludes.csv", _CABECERA_TALUDES, _TALUDES)
    _escribir(out_dir / "Bloques.csv", rm.BLOCK_COLUMNS, [[b.get(c) for c in rm.BLOCK_COLUMNS] for b in _BLOQUES])
    _escribir(out_dir / "Distribuciones.csv", rm.DISTRIBUTION_COLUMNS, _DISTRIBUCIONES)


def main(out_dir: Path) -> dict:
    out_dir = Path(out_dir)
    # 1. Entradas sintéticas: 5 planos, 3 caras, 5 bloques y 6 variables aleatorias.
    escribir_entradas(out_dir)
    caras = rm.load_slope_faces(out_dir / "Taludes.csv")
    planos = rm.load_families(out_dir / "Familias.csv")
    # 2. Evaluación: cinemática de la 3A y luego los bloques (PoF con hipercubo latino, semilla 9).
    taludes = rm.assess_slopes(caras, planos)
    bloques = rm.assess_blocks(rm.load_blocks(out_dir / "Bloques.csv"), taludes,
                               rm.load_distributions(out_dir / "Distribuciones.csv"),
                               iterations=ITERACIONES, sampling="lhs", seed=SEMILLA)
    rm.save_block_results(bloques, out_dir / "bloques_resultados.csv")
    archivos = ["Familias.csv", "Taludes.csv", "Bloques.csv", "Distribuciones.csv", "bloques_resultados.csv"]
    try:  # matplotlib es opcional: histograma del FS y curva de PoF del planar
        from rockmasspy.viz import save_figure
        for tipo in ("hist", "cdf"):
            nombre = f"fs_{tipo}_1.png"
            save_figure(rp.block_figure(bloques[0], tipo, "es"), out_dir / nombre)
            archivos.append(nombre)
    except ImportError:
        pass
    rep = rp.build_slope_report(taludes, title="Bloques sintéticos", lang="es", blocks=bloques)
    rp.write_html(rep, out_dir / "bloques.html")
    archivos.append("bloques.html")
    try:
        rp.write_docx(rep, out_dir / "bloques.docx")
        archivos.append("bloques.docx")
    except ImportError:  # python-docx es opcional
        pass
    # 3. Lo mismo por la CLI.
    cli_exit = cli(["slope", "--faces", str(out_dir / "Taludes.csv"), "--families", str(out_dir / "Familias.csv"),
                    "--blocks", str(out_dir / "Bloques.csv"), "--distributions", str(out_dir / "Distribuciones.csv"),
                    "--iterations", str(ITERACIONES), "--seed", str(SEMILLA)])
    return {"block_counts": rm.block_counts(bloques), "pof_planar": bloques[0].probabilistic.pof,
            "fs": [b.fs for b in bloques], "retro_phi_c0": bloques[0].back_analysis.friction_at_zero_cohesion_deg,
            "berm_reliability": bloques[3].berm.reliability.reliability, "cli_exit": cli_exit, "files": archivos}


if __name__ == "__main__":
    import tempfile
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp())
    destino.mkdir(parents=True, exist_ok=True)
    r = main(destino)
    c = r["block_counts"]
    print("bloques:", c["blocks"], "| planar", c["planar"], "| cuña", c["wedge"], "| volteo", c["toppling"],
          "| berma", c["berm"], "| formados", c["formed"], "| con FS <= 1:", c["fs_below_1"])
    print(f"PoF del planar: {r['pof_planar'] * 100:.1f} % (semilla {SEMILLA}, {ITERACIONES} muestras)")
    print(f"confiabilidad de la berma: {r['berm_reliability'] * 100:.1f} %")
    print(f"código de salida de la CLI: {r['cli_exit']}")
    print("archivos:", ", ".join(r["files"]), "->", destino)
