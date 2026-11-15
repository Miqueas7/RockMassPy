"""Ejemplo 16: resultados de Slide2, RS2 y FLAC3D frente a los criterios, los métodos, el monitoreo y RocData.

Todo es sintético (ids ZZSENT). Escribe los archivos de entrada en la carpeta de salida, los lee con
`load_external` y solo imprime conteos: los ids van a las tablas de resultados, no a la pantalla.
Uso: python main.py [carpeta_de_salida]
"""
import sys
import tempfile
from pathlib import Path

from rockmasspy.criteria import assess_criteria, criteria_assignments
from rockmasspy.excavation import TunnelInput, analyze_tunnel
from rockmasspy.external import (check_rocdata, compare_methods, compare_monitoring, load_external,
                                 load_rocdata_table)
from rockmasspy.normative import get_profile
from rockmasspy.support_capacity import SupportCapacity, hoek_psm

S = "ZZSENT"
# Tipo Slide2: tabla ancha, una columna por magnitud (el encabezado lleva la unidad), un FS por método y sección
SLIDE2 = f"""modelo,escenario,tipo_objeto,id,metodo,Factor of Safety (-),escala,consecuencia
T1,estatico,section,SEC1-{S},bishop,1.62,global,alta
T1,estatico,section,SEC1-{S},spencer,1.66,global,alta
T1,estatico,section,SEC2-{S},bishop,1.18,global,alta
T1,estatico,section,SEC2-{S},spencer,1.55,global,alta
"""
# Tipo RS2: SRF y strength factor por etapa (un SRF siempre se trata como método «ssr»)
RS2 = f"""modelo,escenario,etapa,tipo_objeto,id,SRF,Strength Factor (-),escala,consecuencia
T1,estatico,E2,section,SEC1-{S},1.60,,global,alta
T1,estatico,E2,section,SEC3-{S},1.31,,global,alta
T1,estatico,E2,point,PT1-{S},,0.85,,
"""
ROCDATA = f"""material,GSI,mi,D,mb,s,a,Unit Weight (MN/m3)
ZZSENT-ROCA-A,60,10,0,2.3965,0.011744,0.50284,0.027
ZZSENT-ROCA-B,40,20,0.5,2.0,0.0013,0.5,0.027
"""
MONITOREO = f"""id,etapa,Convergence (%)
T1-{S},E2,1.9
"""


def main(carpeta: Path) -> int:
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, texto in (("slide2.csv", SLIDE2), ("rs2.csv", RS2), ("rocdata.csv", ROCDATA),
                          ("monitoreo.csv", MONITOREO)):
        (carpeta / nombre).write_text(texto, encoding="utf-8")

    slide = load_external(carpeta / "slide2.csv", defaults={"program": "Slide2"})
    rs2 = load_external(carpeta / "rs2.csv", defaults={"program": "RS2"})
    todo = type(slide)(slide.records + rs2.records, slide.warnings + rs2.warnings, slide.notes + rs2.notes)
    print(f"Registros leídos: Slide2 {len(slide.records)}, RS2 {len(rs2.records)}")

    perfil = get_profile("READ-STACEY-2009")
    checks = assess_criteria(perfil, assignments=criteria_assignments(external=todo), external=todo,
                             ssr_policy="warn", as_of="2026-11-14")
    estados = {e: sum(c.status == e for c in checks) for e in ("meets", "fails", "not_verifiable")}
    print(f"Chequeos: {len(checks)} ({estados['meets']} cumplen, {estados['fails']} no cumplen, "
          f"{estados['not_verifiable']} no verificables), {sum(c.needs_attention for c in checks)} piden atención")

    comparados = compare_methods(todo)
    print(f"Métodos comparados: {len(comparados)} objetos, {sum(c.warning is not None for c in comparados)} con aviso")

    inp = TunnelInput(radius_m=6, p0_mpa=1.62, nu=0.3, criterion="HB", sigma_ci_mpa=7, gsi=15, mi=10, d=0.0)
    perno = SupportCapacity("B34", "bolt", psm_mpa=hoek_psm("34 mm rockbolt", spacing_m=1.0), eps_sm=0.002)
    modelo = analyze_tunnel(inp, supports=[perno], install_distance_m=3, ldp="CHERN1998", combination="rocsupport3")
    medido = load_external(carpeta / "monitoreo.csv", column_map={"Convergence": "convergence_pct"})
    comp = compare_monitoring(medido, {f"T1-{S}": modelo})
    print(f"Monitoreo: {len(comp)} medidas comparadas, {sum(c.warning is not None for c in comp)} con aviso")

    roc = check_rocdata(load_rocdata_table(carpeta / "rocdata.csv"))
    print(f"RocData: {len(roc)} filas, {sum(bool(c.mismatches) for c in roc)} con parámetros incoherentes")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="ej16_"))))
