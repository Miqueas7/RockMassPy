"""Ejemplo 17: elementos de contorno 2D (DDM) frente a Kirsch, herradura con Hoek-Brown, pilar entre tajeos y UBC.

Todo es sintético. Solo imprime conteos y valores; las figuras van a la carpeta de salida (por omisión, temporal).
Uso: python main.py [carpeta_de_salida]
"""
import math
import sys
import tempfile
from pathlib import Path

import rockmasspy as rm
from rockmasspy import bem
from rockmasspy.viz import plot_bem, plot_bem_boundary

out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="rmp17_"))
out.mkdir(parents=True, exist_ok=True)


def ring(r, n=64):
    return [(r * math.cos(2 * math.pi * (k - 0.5) / n), r * math.sin(2 * math.pi * (k - 0.5) / n)) for k in range(n)]


# (a) Kirsch frente al DDM: error máximo relativo al σθ máximo, en el contorno y en el campo
print("Caso a: Kirsch (círculo de radio 1, p = 30 MPa)")
for k in (1.0, 0.5):
    sol = rm.bem_solve(rm.BemInput(contours=[rm.BemContour(vertices=ring(1.0))], sigma1_mpa=30, sigma3_mpa=30 * k,
                                   alpha_deg=90.0, e_mpa=10000, nu=0.2, max_element_m=0.1))
    b = rm.bem_boundary(sol)
    errs = {}
    for ang in (0, 45, 90):  # se toma el elemento más cercano a cada ángulo
        i = min(range(len(b.x)), key=lambda j: abs((math.degrees(math.atan2(b.y[j], b.x[j])) - ang + 180) % 360 - 180))
        ex = rm.kirsch_stress(30, k, 1, 1.0, ang).sigma_theta
        errs[f"borde {ang}°"] = abs(b.sigma_tt_mpa[i] - ex) / 60
    for r in (1.5, 2.0):
        ths = [2 * math.pi * i / 72 for i in range(72)]
        f = rm.bem_field(sol, [(r * math.cos(t), r * math.sin(t)) for t in ths])
        e = 0.0
        for p, t in zip(f, ths):
            ex = rm.kirsch_stress(30, k, 1, r, math.degrees(t))
            c, s = math.cos(t), math.sin(t)
            e = max(e, abs(p.sxx * s * s + p.syy * c * c - 2 * p.sxy * s * c - ex.sigma_theta) / 60)
        errs[f"campo r={r}R"] = e
    print(f"  K={k}: " + ", ".join(f"{n} {v:.2%}" for n, v in errs.items()))

# (b) herradura con Hoek-Brown (GSI, mi, D)
hb = bem.BemMaterial("HB", sigma_ci_mpa=60, gsi=50, mi=10, d=0.0)
h = bem.analyze_bem([bem.horseshoe(0, 0, 5, 3)], sigma1_mpa=20, sigma3_mpa=8, alpha_deg=90, e_mpa=20000, nu=0.25,
                    material=hb)
print(f"Caso b: herradura HB, SF mínimo {h.min_sf:.2f}, puntos en tracción {h.tension_count}")
plot_bem(h, out / "herradura_sf.png")
plot_bem_boundary(h, out / "herradura_borde.png")

def fmt(v):
    return "ninguno" if v is None else f"{v:.2f}"


# (c) dos tajeos con un pilar: SF mínimo del pilar y aviso de malla gruesa
a, c = bem.rectangle(-8, 0, 6, 10, n_per_side=1), bem.rectangle(8, 0, 6, 10, n_per_side=1)
pil = [(x, y) for x in (-2, -1, 0, 1, 2) for y in (-4, 0, 4)]
mc = bem.BemMaterial("MC", c_mpa=3, phi_deg=35)
for nombre, el in (("gruesa", 12.0), ("fina", 0.5)):
    r = bem.analyze_bem([a, c], sigma1_mpa=30, sigma3_mpa=15, alpha_deg=90, e_mpa=30000, nu=0.2, material=mc,
                        points=pil, max_element_m=el)
    avisos = "con aviso de malla gruesa" if any("too coarse" in w for w in r.warnings) else "sin aviso de malla gruesa"
    print(f"Caso c: pilar, malla {nombre} ({el} m): SF mínimo {fmt(r.min_sf)}, SF mínimo en puntos dudosos {fmt(r.min_sf_coarse)}, {avisos}")
    if nombre == "fina":
        plot_bem(r, out / "pilar_sf.png")

# (d) caso del laboratorio de UBC
ex = [[(570, 1050), (571, 1055), (567, 1072), (556, 1085), (545, 1085), (544, 1081), (563, 1055), (565, 1050)],
      [(600, 1015), (600, 1025), (595, 1036), (583, 1036), (582, 1032), (595, 1015)],
      [(531, 1048), (538, 1048), (538, 1052), (531, 1052)],
      [(531, 1012), (538, 1012), (538, 1016), (531, 1016)]]
u = bem.analyze_bem(ex, sigma1_mpa=40, sigma3_mpa=20, alpha_deg=0, sigma_z_mpa=30, e_mpa=30000, nu=0.2,
                    material=bem.BemMaterial("HB", sigma_ci_mpa=40, mb=5, s=0.02, a=0.503))
print(f"Caso d: UBC, {len(ex)} excavaciones, SF mínimo {u.min_sf:.2f}, avisos {len(u.warnings)}")
plot_bem(u, out / "ubc_sf.png")
print(f"Figuras: {len(list(out.glob('*.png')))}")
