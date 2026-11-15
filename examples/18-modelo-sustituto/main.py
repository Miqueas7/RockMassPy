"""Ejemplo 18: modelo sustituto de un talud planar. Todo es sintético; solo imprime números.

Uso: python main.py [carpeta]   (por omisión, una temporal; ahí queda el CSV de corridas)
"""
import sys
import tempfile
from pathlib import Path

import numpy as np

from rockmasspy import probabilistic as pb
from rockmasspy.predictive.surrogate import SurrogateData, fit_surrogate, load_runs, surrogate_pof, validate_surrogate
from rockmasspy.predictive.surrogate_bench import planar_base, planar_runs

out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp())
out.mkdir(parents=True, exist_ok=True)

# 1. Corridas guardadas como CSV, como si las hubiera exportado Slide2 (10 escenarios con su propia geometría)
runs = planar_runs(300, seed=7)
csv = out / "corridas.csv"
with open(csv, "w", encoding="utf-8") as f:
    f.write(",".join(runs.names) + ",fs,escenario\n")
    for x, y, g in zip(runs.X, runs.y, runs.groups):
        f.write(",".join(f"{v:.6g}" for v in x) + f",{y:.6g},{g}\n")
data = load_runs(csv, output="fs", group="escenario")
print(f"Corridas leídas: {len(data.y)} con {len(data.names)} entradas")

# 2. Validación: por escenario (agrupada) frente a aleatoria; la agrupada es la honesta
print("\nValidación (RMSE de FS; modelo de la media = referencia)")
for kind in ("rbf", "poly2"):
    for etiqueta, d in (("agrupada", data), ("aleatoria", SurrogateData(X=data.X, y=data.y, names=data.names))):
        v = validate_surrogate(d, kind=kind)
        print(f"  {kind:5s} {etiqueta:9s}: RMSE {v.rmse:.3f} (media {v.rmse_mean_model:.3f}), R2 {v.r2:.3f}, "
              f"útil: {'sí' if v.useful else 'no'}")

# 3. PoF con el sustituto frente a la verdad (el mismo modelo planar con run_probabilistic)
variables = {"cohesion": pb.normal(10, 3, 2, 25), "friction_deg": pb.normal(33, 3, 20, 45),
             "water_fill": pb.uniform(0, 1)}
rbf, poly2 = fit_surrogate(data, kind="rbf"), fit_surrogate(data, kind="poly2")
base = planar_base()  # las entradas no muestreadas quedan en la media de entrenamiento: la verdad igual
for name in ("plane_dip_deg", "height_m"):
    setattr(base, name, float(rbf.mean[rbf.names.index(name)]))
truth = pb.run_probabilistic("planar", base, variables, n=5000, seed=1).pof
print(f"\nPoF de verdad (modelo planar, 5000 muestras): {truth:.4f}")
for kind, s in (("rbf", rbf), ("poly2", poly2)):
    r = surrogate_pof(s, variables, n=5000, seed=1)
    print(f"  {kind:5s}: PoF {r.pof:.4f} ({r.pof / truth:.2f} veces la verdad), cotas {r.pof_lower:.4f} a "
          f"{r.pof_upper:.4f}, fuera de dominio {r.n_out_of_domain}")
print("  poly2 puede validar bien y aun así sesgar la PoF: por eso el sustituto por omisión es rbf")

# 3b. Colas más anchas que las corridas: las muestras fuera del dominio se excluyen y la verdad queda entre las cotas
anchas = {**variables, "cohesion": pb.normal(10, 6, 2, 40)}
truth2 = pb.run_probabilistic("planar", base, anchas, n=5000, seed=1).pof
r = surrogate_pof(rbf, anchas, n=5000, seed=1)
print(f"\nColas anchas, rbf: PoF {r.pof:.4f}, cotas [{r.pof_lower:.4f}, {r.pof_upper:.4f}], fuera de dominio "
      f"{r.n_out_of_domain}, verdad {truth2:.4f}, verdad dentro de las cotas: {r.pof_lower <= truth2 <= r.pof_upper}")

# 4. Una extrapolación se rechaza: la cohesión pedida sale del rango de las corridas
fuera = np.tile(rbf.mean, (1, 1))
fuera[0, rbf.names.index("cohesion")] = 60.0
p = rbf.predict(fuera)
print(f"\nPredicción fuera del dominio: FS = {p.y[0]}, dentro del dominio: {bool(p.in_domain[0])}")
