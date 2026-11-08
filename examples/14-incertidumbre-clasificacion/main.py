"""Ejemplo 14: incertidumbre en las clasificaciones, por lote y para un solo RMR89 (continuo frente a discreto).

Todo es sintético. Uso: python main.py [carpeta_de_salida]
"""
import sys
import tempfile
from pathlib import Path

import rockmasspy as rm
from rockmasspy import probabilistic as pb

from escribir_entradas import escribir

CAT = rm.SupportCatalog([rm.SupportType("I", 1), rm.SupportType("II", 2), rm.SupportType("III", 3)])
RMR = rm.RangeTable("RMR", "RMR89", [rm.RangeClass(0, 40, "IV", "III"), rm.RangeClass(40, 60, "III", "II"),
                                      rm.RangeClass(60, 100, "II", "I")])
Q = rm.RangeTable("Q", "Q-NGI-2025", [rm.RangeClass(0, 1, "poor", "III"), rm.RangeClass(1, 10, "fair", "II"),
                                      rm.RangeClass(10, 1000, "good", "I")])
TABLAS = [rm.LaborTable("galeria", CAT, RMR), rm.LaborTable("crucero", CAT, Q)]


def main(carpeta: Path) -> int:
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = escribir(carpeta / "entradas.xlsx")
    resultados = rm.classify_tramos(rm.load_tramos(ruta), TABLAS, distributions=rm.load_tramo_distributions(ruta),
                                    iterations=2000, seed=1)
    rm.save_results(resultados, carpeta / "resultados.xlsx")
    print("Tramos con distribuciones: probabilidad de la clase más probable")
    for i, r in enumerate(resultados, 1):
        if r.probabilities is None:
            print(f"  tramo {i}: clase {r.label}, sin distribución (determinístico)")
        else:
            p = max(r.probabilities.values())
            print(f"  tramo {i}: clase {r.label}, probabilidad de la clase más probable {p:.0%}"
                  f" ({r.n_valid} muestras válidas)")

    print("RMR89 de un tramo: curvas discretas (tabla) frente a continuas (Kundu et al. 2020)")
    for nombre, modo in (("discretas", rm.RmrFunctions.Discrete), ("continuas", rm.RmrFunctions.Continuous)):
        base = rm.Rmr89Input()
        base.functions, base.ucs_mpa, base.rqd_pct, base.spacing_m = modo, 80.0, 70.0, 0.3
        base.joint_condition_rating, base.water = 20.0, rm.Water.Dry
        u = rm.classification_uncertainty(
            "RMR89", base, {"ucs_mpa": pb.normal(80, 15, 40, 120), "rqd_pct": pb.uniform(55, 85)},
            table=TABLAS[0], n=2000, seed=1)
        s = u.outputs["rmr"]
        print(f"  {nombre}: RMR media {s.mean:.1f}, p05 {s.p05:.1f}, p95 {s.p95:.1f}; "
              + "; ".join(f"{k} {v:.0%}" for k, v in u.class_probabilities.items() if v))
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="ej14_"))))
