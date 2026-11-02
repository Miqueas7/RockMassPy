"""Taludes de un tajo inventado: cinemática de Markland, SMR y Q-slope, con datos sintéticos.

Necesita los extras: pip install "rockmasspy[io,viz,report]". La librería recomienda, el ingeniero decide.
Imprime solo conteos y nombres de archivo, nunca el contenido de los archivos de entrada.
"""
import csv
import random
import sys
from pathlib import Path

import rockmasspy as rm
import rockmasspy.report as rp
from rockmasspy.cli import main as cli

# Tres familias inventadas (buzamiento, dirección de buzamiento), 25 polos cada una, dispersión de unos 8 grados.
# T01 tiene discontinuidades críticas para las caras 1 y 2; T02 buza hacia dentro del macizo, lejos de la cara 3.
_FAMILIAS = {"T01": (("J1", 45, 180), ("J2", 75, 0), ("J3", 60, 270)),
             "T02": (("J1", 25, 0), ("J2", 30, 45), ("J3", 28, 315))}
_DISPERSION = 8.0

_CABECERA_TALUDES = ["id_talud", "id_tramo", "buz_cara_grados", "dir_buz_cara_grados", "friccion_grados",
                     "limite_lateral_grados", "rmr_basico", "excavacion", "rqd_pct", "jn", "jr_a", "ja_a", "o_a",
                     "jwice", "srf_a"]
# Tres caras inventadas. La 1 y la 2 traen Q-slope (la 1 queda más empinada que su β); la 3 no lo trae y no tiene nada crítico.
_TALUDES = [
    ["TL1", "T01", 60, 180, 30, 30, 55, "voladura_normal", 70, 9, 1.0, 4, 1.0, 0.7, 2.5],
    ["TL2", "T01", 70, 90, 30, 30, 65, "precorte", 85, 6, 2, 1, 1.0, 1.0, 2.5],
    ["TL3", "T02", 45, 180, 35, 30, 75, "natural", None, None, None, None, None, None, None],
]


def _escribir(ruta: Path, cabecera, filas) -> None:
    with open(ruta, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(cabecera)
        w.writerows(["" if v is None else v for v in f] for f in filas)


def escribir_entradas(out_dir: Path) -> None:
    rnd = random.Random(8)
    filas = []
    for tramo, familias in _FAMILIAS.items():
        for familia, buz, dir_buz in familias:
            for _ in range(25):
                b = min(89.0, max(1.0, rnd.gauss(buz, _DISPERSION)))
                d = rnd.gauss(dir_buz, _DISPERSION) % 360.0
                filas.append([tramo, familia, round(b, 1), round(d, 1)])
    _escribir(out_dir / "Familias.csv", ["id_tramo", "familia", "buzamiento_grados", "dir_buzamiento_grados"], filas)
    _escribir(out_dir / "Taludes.csv", _CABECERA_TALUDES, _TALUDES)


def main(out_dir: Path) -> dict:
    out_dir = Path(out_dir)
    # 1. Entradas sintéticas: 150 planos en dos tramos y tres caras.
    escribir_entradas(out_dir)
    caras = rm.load_slope_faces(out_dir / "Taludes.csv")
    planos = rm.load_families(out_dir / "Familias.csv")
    # 2. Evaluación: cinemática, SMR (discreto y continuo) y Q-slope por talud.
    resultados = rm.assess_slopes(caras, planos)
    rm.save_slope_results(resultados, out_dir / "resultados.csv")
    archivos = ["Familias.csv", "Taludes.csv", "resultados.csv"]
    try:  # matplotlib es opcional: un estereograma por modo crítico de la primera cara
        from rockmasspy.viz import save_figure
        for modo in (None, *rp.slope_modes(resultados[0])):
            nombre = f"estereograma_1_{modo or 'densidad'}.png"
            save_figure(rp.slope_figure(resultados[0], modo, "es"), out_dir / nombre)
            archivos.append(nombre)
    except ImportError:
        pass
    rep = rp.build_slope_report(resultados, title="Taludes sintéticos", lang="es")
    rp.write_html(rep, out_dir / "taludes.html")
    archivos.append("taludes.html")
    try:
        rp.write_docx(rep, out_dir / "taludes.docx")
        archivos.append("taludes.docx")
    except ImportError:  # python-docx es opcional
        pass
    # 3. Lo mismo por la CLI.
    cli_exit = cli(["slope", "--faces", str(out_dir / "Taludes.csv"), "--families", str(out_dir / "Familias.csv")])
    return {"counts": rm.slope_counts(resultados), "cli_exit": cli_exit, "files": archivos}


if __name__ == "__main__":
    import tempfile
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp())
    destino.mkdir(parents=True, exist_ok=True)
    r = main(destino)
    c = r["counts"]
    print("taludes:", c["slopes"], "| planar", c["planar"], "| cuña", c["wedge_primary"], "+", c["wedge_secondary"],
          "| volteo flexural", c["flexural_toppling"],
          "| volteo directo", c["direct_toppling"], "+", c["direct_toppling_oblique"])
    print(f"código de salida de la CLI: {r['cli_exit']}")
    print("archivos:", ", ".join(r["files"]), "->", destino)
