"""Tablas de sostenimiento por labor (datos inventados, de ninguna mina).

Una tabla RMR89 para galerías y una tabla de celdas GSI para tajeos. La librería recomienda,
el ingeniero decide. Guardar en YAML y Excel necesita el extra: pip install "rockmasspy[io]".
"""
from pathlib import Path

import rockmasspy as rm


def catalogo() -> rm.SupportCatalog:
    # Cinco tipos, del más liviano (1) al más pesado (5), con sus elementos.
    return rm.SupportCatalog([
        rm.SupportType("I", 1, "sin sostenimiento sistemático"),
        rm.SupportType("II", 2, "pernos puntuales", bolt=rm.Bolt("split-set", 1.8, 1.5)),
        rm.SupportType("III", 3, "pernos y malla", bolt=rm.Bolt("split-set", 2.1, 1.2), mesh="electrosoldada"),
        rm.SupportType("IV", 4, "pernos y shotcrete", bolt=rm.Bolt("helicoidal", 2.4, 1.0),
                       shotcrete=rm.Shotcrete(50)),
        rm.SupportType("V", 5, "pernos, shotcrete con fibra y cimbra", bolt=rm.Bolt("helicoidal", 2.4, 0.8),
                       shotcrete=rm.Shotcrete(100, fiber=True), arch="cimbra liviana"),
    ])


def tabla_galeria(cat: rm.SupportCatalog) -> rm.LaborTable:
    clases = [rm.RangeClass(80, 100, "I", "I"), rm.RangeClass(60, 80, "II", "II"),
              rm.RangeClass(40, 60, "III", "III"), rm.RangeClass(20, 40, "IV", "IV"),
              rm.RangeClass(0, 20, "V", "V")]
    return rm.LaborTable("galería", cat, rm.RangeTable("RMR", "RMR89", clases), span_m=(3.0, 4.0),
                         author="ejemplo", date="2026-11-01")


# Las 18 celdas que aplican en la cartilla; peor estructura (abajo) o peor condición (derecha)
# nunca lleva un sostenimiento más liviano.
CELDAS = {
    "LF/MB": "I", "LF/B": "I", "LF/R": "II", "LF/P": "III",
    "F/MB": "I", "F/B": "II", "F/R": "II", "F/P": "III", "F/MP": "IV",
    "MF/B": "II", "MF/R": "III", "MF/P": "IV", "MF/MP": "IV",
    "IF/R": "III", "IF/P": "IV", "IF/MP": "V",
    "T/P": "V", "T/MP": "V",
}


def tabla_tajeo(cat: rm.SupportCatalog) -> rm.LaborTable:
    chart = rm.GSI_CHARTS["GSI-Vallejo-Osinergmin2017"]
    cells = rm.CellTable(chart, [rm.CellClass(c, s) for c, s in CELDAS.items()])
    return rm.LaborTable("tajeo", cat, cells, span_m=(4.0, 8.0), author="ejemplo", date="2026-11-01")


def main(out_dir: Path) -> dict:
    out_dir = Path(out_dir)
    cat = catalogo()
    galeria, tajeo = tabla_galeria(cat), tabla_tajeo(cat)

    issues = {}
    for nombre, t in (("galería", galeria), ("tajeo", tajeo)):
        issues[nombre] = t.validate()
        for i in issues[nombre]:
            print(f"aviso [{nombre}] {i.kind}: {i.message}")

    g = galeria.classify(53)
    t = tajeo.classify(structure="MF", condition="R")
    print(f"galería RMR 53 (luz 3.5 m): clase {g.label}, sostenimiento {g.support.code}, base {g.base_edition}")
    print(f"tajeo MF/R (luz 6 m): celda {t.label}, sostenimiento {t.support.code}, base {t.base_edition}")

    ok = True
    for nombre, tabla in (("galeria", galeria), ("tajeo", tajeo)):
        for ext, guardar, leer in (("json", rm.save_json, rm.load_json), ("yaml", rm.save_yaml, rm.load_yaml),
                                   ("xlsx", rm.save_excel, rm.load_excel)):
            ruta = out_dir / f"{nombre}.{ext}"
            guardar(tabla, ruta)
            ok = ok and leer(ruta) == tabla
    print("roundtrip_ok", ok)

    return {"galeria_rmr53": g.support.code, "tajeo_MF/R": t.support.code,
            "issues_galeria": len(issues["galería"]), "issues_tajeo": len(issues["tajeo"]), "roundtrip_ok": ok}


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        main(Path(d))
