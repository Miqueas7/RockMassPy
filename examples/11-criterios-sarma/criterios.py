"""Criterios de aceptación y Sarma sobre tres taludes inventados: un tajo, un botadero y un pad de lixiviación.

Necesita los extras: pip install "rockmasspy[io,viz,report]". La librería calcula, el ingeniero decide.
Todo es sintético: la geometría, los materiales, las familias, el registro de aceleraciones (un seno amortiguado) y la
tabla de criterios del botadero, que escribe el propio script. Ningún número viene de una mina.
Imprime solo conteos, estados, FS y nombres de archivo, nunca el contenido de los archivos de entrada.
"""
import csv
import math
import sys
from pathlib import Path

import rockmasspy as rm
import rockmasspy.report as rp
from rockmasspy.cli import main as cli
from rockmasspy.criteria import criteria_assignments, return_periods
from rockmasspy.limit_equilibrium import le_static_fs

SEMILLA = 11
ITERACIONES = 5000

# ---------------------------------------------------------------- (a) tajo: bloques de banco (3B)
# Una cara de banco de 15 m a 70 grados (rumbo de buzamiento 180) y un plano P1 de 40/180 que aflora en la cara.
_FAMILIAS = [["F01", "P1", 40, 180]]
_CABECERA_TALUDES = ["id_talud", "id_tramo", "buz_cara_grados", "dir_buz_cara_grados", "friccion_grados",
                     "limite_lateral_grados", "rmr_basico", "excavacion"]
_TALUDES = [["TB1", "F01", 70, 180, 33, 30, 55, "voladura_normal"]]
_BLOQUES = [
    # BQ1: bloque planar del banco, sin agua; FS determinístico y PoF con c y phi aleatorios
    dict(id_bloque="BQ1", id_talud="TB1", modelo="planar", altura_m=15, peso_unitario_kn_m3=26,
         familia_1="P1", cohesion_1_kpa=25, friccion_1_grados=32, escala="banco", consecuencia="media"),
    # BQ2: la berma del mismo banco: 15 m de banco, 10 m de berma; la cara del banco varía por la voladura
    dict(id_bloque="BQ2", id_talud="TB1", modelo="berma", altura_banco_m=15, ancho_berma_m=10,
         escala="banco", consecuencia="media"),
]
_DISTRIBUCIONES = [
    ["BQ1", "friccion_1_grados", "normal", 32, 5, 20, 48],
    ["BQ1", "cohesion_1_kpa", "normal", 25, 12, 0, 60],
    ["BQ2", "buz_cara_grados", "normal", 70, 5, 55, 85],
]

# ---------------------------------------------------------------- equilibrio límite (3C y 3D)
# kN, kPa y m; todas las caras miran a la derecha.
# T1 (a): talud global de 150 m a unos 45 grados en un solo material.
# B1 (b): botadero de 40 m a 37 grados sobre una ladera de 8 grados cubierta por 2 m de arcilla.
# P1 (c): pad de 30 m a 2H:1V sobre una geomembrana (capa de 1 m de interfaz) y su fundación.
_PENDIENTE = 0.14  # ladera del botadero, unos 8 grados


def _ladera(x, d=0.0):
    return round(50 - _PENDIENTE * x - d, 4)


_GEOMETRIA = [
    ("T1", "superficie", [(0, 200), (80, 200), (230, 50), (330, 50)]),
    ("B1", "superficie", [(0, 90), (60, 90), (139.34, _ladera(139.34)), (250, _ladera(250))]),
    ("B1", "base_botadero", [(0, _ladera(0)), (250, _ladera(250))]),
    ("B1", "base_arcilla", [(0, _ladera(0, 2)), (250, _ladera(250, 2))]),
    # la base de Sarma: escarpa en el desmonte, tramo por la mitad de la arcilla y salida al pie
    ("B1", "sarma", [(20, 90), (50, _ladera(50, 1)), (115, _ladera(115, 1)), (150, _ladera(150))]),
    ("P1", "superficie", [(0, 50), (60, 50), (120, 20), (220, 20)]),
    ("P1", "base_pad", [(0, 20), (220, 20)]),
    ("P1", "base_interfaz", [(0, 19), (220, 19)]),
    ("P1", "geomembrana", [(0, 19.5), (125, 19.5)]),  # línea débil bajo el pad: la búsqueda de bloque pone ahí su base
]
_ESTRATOS = [["T1", 1, "roca_global", None],
             ["B1", 1, "desmonte", "base_botadero"], ["B1", 2, "arcilla", "base_arcilla"], ["B1", 3, "ladera", None],
             ["P1", 1, "mineral", "base_pad"], ["P1", 2, "interfaz", "base_interfaz"], ["P1", 3, "fundacion", None]]
_MATERIALES = [
    dict(material="roca_global", modelo="mohr_coulomb", peso_unitario_kn_m3=26, cohesion_kpa=200, friccion_grados=36),
    dict(material="desmonte", modelo="mohr_coulomb", peso_unitario_kn_m3=19, cohesion_kpa=5, friccion_grados=37),
    dict(material="arcilla", modelo="mohr_coulomb", peso_unitario_kn_m3=18, cohesion_kpa=12, friccion_grados=18),
    dict(material="ladera", modelo="mohr_coulomb", peso_unitario_kn_m3=22, cohesion_kpa=60, friccion_grados=38),
    dict(material="mineral", modelo="mohr_coulomb", peso_unitario_kn_m3=18, cohesion_kpa=5, friccion_grados=38),
    dict(material="interfaz", modelo="mohr_coulomb", peso_unitario_kn_m3=18, cohesion_kpa=0, friccion_grados=20),
    dict(material="fundacion", modelo="mohr_coulomb", peso_unitario_kn_m3=21, cohesion_kpa=40, friccion_grados=35),
]
_ANALISIS = [
    # A1: global del tajo, circular, con kh y el período de retorno del art. 264 del DS 024
    dict(id_analisis="A1", id_seccion="T1", metodos="spencer;bishop", superficie="circular", malla_x_min=120,
         malla_x_max=340, malla_y_min=180, malla_y_max=420, base_modelo_m=0, tajadas=25, kh=0.1,
         escala="global", consecuencia="media", periodo_retorno_anios=100),
    # A2: botadero por Sarma con tres cuñas y ángulos de interfaz optimizados
    dict(id_analisis="A2", id_seccion="B1", superficie="sarma", linea_superficie="sarma", sarma_angulos="opt",
         base_modelo_m=0, kh=0.07, escala="botadero", consecuencia="media"),
    # A3: pad, búsqueda de bloque sobre la geomembrana, kh, ky y Newmark con el registro sintético
    dict(id_analisis="A3", id_seccion="P1", metodos="spencer", superficie="bloque", linea_debil="geomembrana",
         base_modelo_m=0, kh=0.16, registro="S1", escala="pad", consecuencia="media"),
]
# Criterios propios del botadero (R7): una tabla que escribe el usuario; aquí, inventada.
_CRITERIOS = [["botadero", "*", 1.3, 1.0, "", "", "criterio de diseño del proyecto, sintético"]]
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


HOJAS_LE = {"Geometria": "Geometria.csv", "Estratos": "Estratos.csv", "Materiales_LE": "Materiales_LE.csv",
            "Analisis_LE": "Analisis_LE.csv", "Sismos": "Sismos.csv"}
HOJAS_TAJO = ("Familias.csv", "Taludes.csv", "Bloques.csv", "Distribuciones.csv")


def escribir_entradas(out_dir: Path) -> dict:
    _escribir(out_dir / "Familias.csv", ["id_tramo", "familia", "buzamiento_grados", "dir_buzamiento_grados"],
              _FAMILIAS)
    _escribir(out_dir / "Taludes.csv", _CABECERA_TALUDES, _TALUDES)
    _escribir(out_dir / "Bloques.csv", rm.BLOCK_COLUMNS, [[b.get(c) for c in rm.BLOCK_COLUMNS] for b in _BLOQUES])
    _escribir(out_dir / "Distribuciones.csv", rm.DISTRIBUTION_COLUMNS, _DISTRIBUCIONES)
    _escribir(out_dir / HOJAS_LE["Geometria"], rm.GEOMETRY_COLUMNS,
              [[sec, linea, x, y] for sec, linea, pts in _GEOMETRIA for x, y in pts])
    _escribir(out_dir / HOJAS_LE["Estratos"], rm.LAYER_COLUMNS, _ESTRATOS)
    _escribir(out_dir / HOJAS_LE["Materiales_LE"], rm.MATERIAL_COLUMNS,
              [[m.get(c) for c in rm.MATERIAL_COLUMNS] for m in _MATERIALES])
    _escribir(out_dir / HOJAS_LE["Analisis_LE"], rm.ANALYSIS_COLUMNS,
              [[a.get(c) for c in rm.ANALYSIS_COLUMNS] for a in _ANALISIS])
    _escribir(out_dir / HOJAS_LE["Sismos"], rm.RECORD_COLUMNS, [["S1", t, a] for t, a in registro_sintetico()])
    _escribir(out_dir / "Criterios.csv", rm.CRITERIA_COLUMNS, _CRITERIOS)
    return {hoja: out_dir / nombre for hoja, nombre in HOJAS_LE.items()}


def _estados(checks) -> list[tuple[str, str, str]]:
    """(objeto por orden, regla, estado), sin ids: lo que el README muestra en su tabla."""
    return [(f"{c.object_kind} {c.order}" if c.order else c.object_kind, c.rule, c.status) for c in checks]


def main(out_dir: Path) -> dict:
    out_dir = Path(out_dir)
    # 1. Entradas sintéticas: un plano, una cara, dos bloques, tres variables, tres secciones, tres análisis,
    #    un registro y la tabla de criterios del botadero.
    hojas = escribir_entradas(out_dir)
    taludes = rm.assess_slopes(rm.load_slope_faces(out_dir / "Taludes.csv"), rm.load_families(out_dir / "Familias.csv"))
    bloques = rm.assess_blocks(rm.load_blocks(out_dir / "Bloques.csv"), taludes,
                               rm.load_distributions(out_dir / "Distribuciones.csv"),
                               iterations=ITERACIONES, sampling="lhs", seed=SEMILLA)
    le = rm.assess_le(hojas)
    global_, botadero, pad = le
    asg, tr = criteria_assignments(bloques, le), return_periods(le)
    # 2. Criterios: cada parte contra el suyo. Read y Stacey (tajo), Ryan y Pryor (berma), la tabla propia
    #    (botadero), NDEP (pad) y el art. 264 del DS 024 (PE-264, sobre todos los análisis).
    rs = rm.get_profile("READ-STACEY-2009")
    perfiles = {"READ-STACEY-2009": rs, "RYAN-PRYOR-2000": rm.get_profile("RYAN-PRYOR-2000"),
                "Criterios.csv": rm.load_criteria_table(out_dir / "Criterios.csv"), "NDEP-2021": rm.get_profile("NDEP-2021")}
    chequeos = {
        "READ-STACEY-2009": rm.assess_criteria(rs, blocks=bloques, le=le, assignments=asg, return_periods=tr),
        "RYAN-PRYOR-2000": rm.assess_criteria(perfiles["RYAN-PRYOR-2000"], blocks=bloques, assignments=asg),
        "Criterios.csv": rm.assess_criteria(perfiles["Criterios.csv"], le=[botadero], assignments=asg),
        "NDEP-2021": rm.assess_criteria(perfiles["NDEP-2021"], le=[pad], assignments=asg),
    }
    # la política de rangos: con «upper», la PoF del banco se compara con 50 % en vez de 25 %
    pof_upper = [c.status for c in rm.assess_criteria(rs, blocks=bloques, assignments=asg, range_policy="upper")
                 if c.rule == "slope_pof"]
    pe = [c for c in rm.assess_criteria(rm.get_profile("PE-DS024-2016"), le=le, assignments=asg, return_periods=tr)
          if c.rule == "pseudostatic_analysis_present"]
    rm.save_block_results(bloques, out_dir / "bloques_resultados.csv")
    rm.save_le_results(le, out_dir / "equilibrio_resultados.csv")
    rm.save_criteria_results([c for cs in chequeos.values() for c in cs] + pe, out_dir / "criterios_resultados.csv")
    archivos = [*HOJAS_TAJO, *HOJAS_LE.values(), "Criterios.csv", "bloques_resultados.csv",
                "equilibrio_resultados.csv", "criterios_resultados.csv"]
    try:  # matplotlib es opcional: la sección de cada análisis (las cuñas de Sarma en el botadero) y el Newmark del pad
        from rockmasspy.viz import save_figure
        for r in le:
            nombre = f"seccion_le_{r.order}.png"
            save_figure(rp.le_figure(r, "es"), out_dir / nombre)
            archivos.append(nombre)
            if r.newmark is not None:
                nombre = f"newmark_{r.order}.png"
                save_figure(rp.newmark_figure(r, "es"), out_dir / nombre)
                archivos.append(nombre)
    except ImportError:
        pass
    # 3. Informes: el completo del tajo con Read y Stacey y el art. 264 (todos los análisis, como la CLI) y uno
    #    por criterio para el botadero y el pad.
    informes = [
        ("criterios_tajo", "Taludes sintéticos frente a Read y Stacey", taludes, bloques, le, "READ-STACEY-2009", pe),
        ("criterios_botadero", "Botadero sintético frente a la tabla propia", [], [], [botadero], "Criterios.csv",
         None),
        ("criterios_pad", "Pad sintético frente a NDEP", [], [], [pad], "NDEP-2021", None),
    ]
    for nombre, titulo, tal, bl, an, clave, pchecks in informes:
        rep = rp.build_slope_report(tal, title=titulo, lang="es", blocks=bl, le=an, criteria=chequeos[clave],
                                    criteria_profile=perfiles[clave], profile_checks=pchecks)
        rp.write_html(rep, out_dir / f"{nombre}.html")
        archivos.append(f"{nombre}.html")
        if nombre == "criterios_tajo":
            try:
                rp.write_docx(rep, out_dir / f"{nombre}.docx")
                archivos.append(f"{nombre}.docx")
            except ImportError:  # python-docx es opcional
                pass
    # 4. Lo mismo por la CLI: los tres análisis contra Read y Stacey con el art. 264, y los bloques del banco.
    cli_le = cli(["le", "--geometry", str(hojas["Geometria"]), "--layers", str(hojas["Estratos"]),
                  "--materials", str(hojas["Materiales_LE"]), "--analyses", str(hojas["Analisis_LE"]),
                  "--records", str(hojas["Sismos"]), "--criteria", "READ-STACEY-2009", "--profile", "PE-DS024-2016",
                  "--criteria-output", str(out_dir / "criterios_le_cli.csv")])
    cli_slope = cli(["slope", "--faces", str(out_dir / "Taludes.csv"), "--families", str(out_dir / "Familias.csv"),
                     "--blocks", str(out_dir / "Bloques.csv"), "--distributions", str(out_dir / "Distribuciones.csv"),
                     "--iterations", str(ITERACIONES), "--seed", str(SEMILLA), "--criteria", "READ-STACEY-2009"])
    archivos.append("criterios_le_cli.csv")
    bq1, bq2 = bloques
    return {
        "counts": {k: rm.criteria_counts(v) for k, v in chequeos.items()},
        "states": {k: _estados(v) for k, v in chequeos.items()},
        "pe264": [c.status for c in pe], "pof_upper": pof_upper,
        "fs_bloque": bq1.fs, "pof_bloque": bq1.probabilistic.pof, "berm_reliability": bq2.berm.reliability.reliability,
        "fs_global_estatico": min(le_static_fs(global_)), "fs_global": global_.fs_min,
        "fs_botadero_estatico": le_static_fs(botadero)[0], "fs_botadero": botadero.fs_min,
        "kc_botadero": botadero.ky, "sarma_angulos": list(botadero.sarma.interface_angles_deg),
        "fs_pad_estatico": min(le_static_fs(pad)), "fs_pad": pad.fs_min, "ky_pad": pad.ky,
        "newmark_pad_m": pad.newmark.displacement_m,
        "kh": [r.kh for r in le], "le_attention": [rm.le_attention(r) for r in le], "cli_le": cli_le, "cli_slope": cli_slope,
        "files": archivos,
    }


if __name__ == "__main__":
    import tempfile
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp())
    destino.mkdir(parents=True, exist_ok=True)
    r = main(destino)
    for perfil, c in r["counts"].items():
        print(f"{perfil}: {c['checks']} chequeos | cumple {c['meets']} | no cumple {c['fails']} | "
              f"no verificable {c['not_verifiable']}")
    print("PE-264 (art. 264):", ", ".join(r["pe264"]), "| PoF del banco con --range-policy upper:",
          ", ".join(r["pof_upper"]))
    print(f"banco: FS {r['fs_bloque']:.3f}, PoF {r['pof_bloque'] * 100:.1f} %, "
          f"confiabilidad de berma {r['berm_reliability'] * 100:.1f} %")
    print(f"global: FS estático {r['fs_global_estatico']:.3f}, con kh {r['kh'][0]:g} {r['fs_global']:.3f}")
    print(f"botadero (Sarma): FS estático {r['fs_botadero_estatico']:.3f}, con kh {r['kh'][1]:g} {r['fs_botadero']:.3f}, "
          f"Kc {r['kc_botadero']:.4f}, ángulos " + "; ".join(f"{a:.1f}" for a in r["sarma_angulos"]))
    print(f"pad: FS estático {r['fs_pad_estatico']:.3f}, con kh {r['kh'][2]:g} {r['fs_pad']:.3f}, ky {r['ky_pad']:.4f}, "
          f"Newmark {r['newmark_pad_m'] * 100:.1f} cm")
    print(f"códigos de la CLI: le {r['cli_le']}, slope {r['cli_slope']}")
    print("archivos:", ", ".join(r["files"]), "->", destino)
