"""Ejemplo 15: túneles, convergencia-confinamiento (GRC, LDP, sostenimiento), coherencia de Hoek-Brown y capacidad M-N.

Todo es sintético, salvo el RST Ejemplo 1, que es un caso publicado (RocScience, RocSupport Tutorial).
Uso: python main.py [carpeta_de_salida]
"""
import sys
import tempfile
from pathlib import Path

import rockmasspy as rm
from rockmasspy.excavation import TunnelInput, analyze_tunnel
from rockmasspy.hb_consistency import check_hoek_brown
from rockmasspy.support_capacity import hoek_psm, load_support_capacity

HOJA = """codigo;tipo;psm_mpa;eps_sm;espesor_m;e_mpa;nu;sigma_c_mpa;sigma_t_mpa;espaciamiento_m;item_hoek
ZZSENT-PB;bolt;;;;;;;;1.0;34 mm rockbolt
ZZSENT-SC;shotcrete;;;0.05;25000;0.2;35;3.5;;Concrete or shotcrete lining 50 mm 28 days 35 MPa
"""


def resumen(titulo: str, r) -> None:
    fs = "sin cruce" if r.interaction is None or r.interaction.fs is None else f"{r.interaction.fs:.2f}"
    print(f"{titulo}: FS {fs}, rp {r.rp_m:.2f} m, ε {r.strain_pct:.2f} %, clase {r.squeezing.squeezing_class}")
    for aviso in (*r.warnings, *r.notes):
        print(f"  aviso: {aviso}")


def main(carpeta: Path) -> int:
    carpeta.mkdir(parents=True, exist_ok=True)
    hoja = carpeta / "capacidades.csv"
    hoja.write_text(HOJA, encoding="utf-8")
    caps = load_support_capacity(hoja)

    # 1. RST Ejemplo 1: Hoek-Brown (a != 0.5, equivalente Mohr-Coulomb), perno de 34 mm, LDP de Chern
    rst = TunnelInput(radius_m=6, p0_mpa=1.62, nu=0.3, criterion="HB", sigma_ci_mpa=7, gsi=15, mi=10, d=0.0)
    perno = caps["ZZSENT-PB"]
    resumen("RST Ejemplo 1", analyze_tunnel(rst, supports=[perno], install_distance_m=3, ldp="CHERN1998",
                                            combination="rocsupport3"))

    # 2. Túnel sintético en Mohr-Coulomb con dilatancia; perno y shotcrete combinados por rigidez
    mc = TunnelInput(radius_m=4, p0_mpa=5.0, nu=0.25, criterion="MC", e_mpa=1500, c_mpa=1.2, phi_deg=30, psi_deg=5)
    for nombre, soporte in (("Perno + shotcrete", [caps["ZZSENT-PB"], caps["ZZSENT-SC"]]), ("Solo perno", [perno])):
        resumen(f"MC sintético, {nombre}", analyze_tunnel(mc, supports=soporte, install_distance_m=2,
                                                          support_diameter_m=8))
    resumen("MC sintético, sin sostenimiento", analyze_tunnel(mc))
    print(f"  psm del perno de la hoja: {hoek_psm('34 mm rockbolt', spacing_m=1.0):.3f} MPa")

    # 3. Coherencia de una tabla Hoek-Brown inventada: mb y s salen con D = 0, pero la tabla declara D = 0.5
    p = rm.hb_params(40, 20, 0.0, rm.HbEdition.HB2002)
    c = check_hoek_brown(gsi=40, mi=20, d=0.5, mb=p.mb, s=p.s, a=p.a)
    print(f"Coherencia Hoek-Brown: incoherentes {list(c.mismatches)}, D implícito {c.implied_d:.2f}")
    for nota in c.notes:
        print(f"  nota: {nota}")

    # 4. Diagrama de capacidad M-N de un shotcrete y los pares (N, M) de Einstein y Schwartz
    s = rm.LiningSection()
    s.area_m2, s.inertia_m4, s.thickness_m, s.sigma_c_mpa, s.sigma_t_mpa = 0.2, 0.2**3 / 12, 0.2, 35, -3.5
    cap = rm.capacity_mn(s, 1)
    fuerzas = []
    for th in (0, 45, 90):
        e = rm.EinsteinSchwartzInput()
        e.sigma_v_mpa, e.k_ratio, e.e_rock_mpa, e.nu_rock = 3, 1.5, 3000, 0.25
        e.e_lining_mpa, e.nu_lining, e.thickness_m, e.radius_m, e.theta_deg = 25000, 0.2, 0.2, 3.0, th
        r = rm.einstein_schwartz(e)
        f = rm.LiningForce()
        f.n_mn, f.m_mnm = r.n_mn, r.m_mnm
        fuerzas.append(f)
        print(f"  θ = {th:2d}°: N {r.n_mn:.2f} MN, M {r.m_mnm:+.3f} MN·m")
    chk = rm.check_capacity(s, fuerzas, 1)
    print(f"Shotcrete 0.2 m: Nmax {cap.n_max:.2f} MN; pares fuera del diagrama: {len(chk.outside)} de {len(fuerzas)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="ej15_"))))
