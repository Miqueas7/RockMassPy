"""Parte 2 del ejemplo 12: auditoría de la práctica (nivel 2), modelo de desempeño (nivel 3) y recomendación.

Necesita los extras: pip install "rockmasspy[io,ml,viz,report]". La librería recomienda, el ingeniero decide.
Todo es sintético: `synthetic_history` arma un histórico grande (8 zonas, 96 labores, unos 1400 tramos) con un
efecto real del sitio sobre la falla, así que el nivel 3 queda «propio del sitio». Ningún número viene de una mina.
Imprime solo conteos, estados, coeficientes y nombres de archivo, nunca filas ni ids del histórico.
"""
import dataclasses
import sys
from pathlib import Path

import rockmasspy as rm
import rockmasspy.report as rp
from rockmasspy.predictive import (KINDS, audit_practice, fit_performance, fit_site_correlation, load_model,
                                   recommend, save_model, save_practice_results, save_recommendations,
                                   synthetic_history)

SEMILLA = 0
# Umbral de ejemplo: lo fija el ingeniero según el costo de una falla en su labor (no hay valor por defecto).
# Aquí, P(falla) aceptable de 0.35 en un horizonte de 365 días; con otro umbral la elección cambia.
UMBRAL, HORIZONTE_DIAS = 0.35, 365


def main(out_dir: Path, n_boot: int = 2000) -> dict:
    out_dir = Path(out_dir)
    # 1. El histórico grande, guardado con las hojas de la plantilla y leído como el de una mina real
    historico, _ = synthetic_history(seed=SEMILLA, n_zones=8, labors_per_zone=12, tramos_per_labor=15)
    rm.save_history_xlsx(historico, out_dir / "historico_grande.xlsx")
    h = rm.load_history(out_dir / "historico_grande.xlsx")
    audit = rm.audit_history(h)
    # 2. Nivel 1 (como en la parte 1), nivel 2 (describe la práctica, no recomienda) y nivel 3 (desempeño)
    ajustes = [fit_site_correlation(h, k, n_boot=n_boot) for k in KINDS]
    practica = audit_practice(h, n_boot=n_boot)
    modelo = fit_performance(h, n_boot=n_boot)
    # 3. El modelo en JSON: coeficientes, rangos, métricas y conteos; nunca filas ni ids
    save_model(modelo, out_dir / "modelo.json")
    modelo = load_model(out_dir / "modelo.json")
    # 4. Tramos nuevos (sintéticos, de otra semilla) y la recomendación con el umbral del ingeniero
    otros, _ = synthetic_history(seed=99, n_zones=1, labors_per_zone=2, tramos_per_labor=4)
    nuevos = tuple(dataclasses.replace(t, id_tramo=f"N{i:03d}") for i, t in enumerate(otros.tramos[:6], 1))
    rm.save_history_xlsx(rm.History(nuevos, (), ()), out_dir / "tramos_nuevos.xlsx")
    recs = recommend(modelo, rm.load_history(out_dir / "tramos_nuevos.xlsx").tramos, threshold=UMBRAL,
                     exposure_days=HORIZONTE_DIAS, practice=practica)
    # 5. Resultados por tramo (sí llevan el id_tramo: se quedan en la carpeta protegida) e informe completo
    res = out_dir / "resultados"
    res.mkdir(exist_ok=True)
    escritos = [save_practice_results(practica, res / "practice_results.csv"),
                save_recommendations(recs, res / "recomendaciones.csv")]
    rep = rp.build_history_report(audit, ajustes, history=h, practice=practica, performance=modelo,
                                  threshold=UMBRAL, exposure_days=HORIZONTE_DIAS, lang="es")
    archivos = ["historico_grande.xlsx", "modelo.json", "tramos_nuevos.xlsx",
                rp.write_html(rep, out_dir / "prediccion.html").name]
    try:
        archivos.append(rp.write_docx(rep, out_dir / "prediccion.docx").name)
    except ImportError:
        pass
    archivos += [f"resultados/{p.name}" for p in escritos]
    return {
        "tramos": len(h.tramos),
        "practice": {"verdicts": practica.verdicts, "status": practica.status, "outside": len(practica.outside_set),
                     "beyond_chart": practica.beyond_chart},
        "calibration": modelo.calibration,
        "coefficients": modelo.coefficients,
        "interaction_ref": modelo.interaction_ref,  # None en la forma aditiva
        "recommendations": [(r.chosen, r.reason, r.extrapolation) for r in recs],
        "files": archivos,
    }


if __name__ == "__main__":
    import tempfile
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp())
    destino.mkdir(parents=True, exist_ok=True)
    r = main(destino)
    p = r["practice"]
    print(f"\nhistórico: {r['tramos']} tramos")
    print(f"nivel 2: {p['status']}, ln Q {p['verdicts']['ln_q']}, ln De {p['verdicts']['ln_de']}, "
          f"{p['outside']} tramos fuera de su conjunto conforme (describe la práctica, no recomienda)")
    print(f"nivel 3: calibración {r['calibration']}")
    for name, b in r["coefficients"].items():
        print(f"  {name}: {b:.4g}")
    if r["interaction_ref"] is not None:  # la columna de la interacción no es ln Q × rango a secas
        q_max, k_max = r["interaction_ref"]
        print(f"  (ln_q:support_rank multiplica (ln Q − {q_max:.4g})·(rango − {k_max:g}): la calidad y el rango "
              "medidos desde sus máximos del entrenamiento, así la columna es ≥ 0 y su coeficiente ≥ 0 dice que el "
              "sostenimiento ayuda más en peor roca; 0 = sin interacción)")
    print(f"recomendación (umbral {UMBRAL}, {HORIZONTE_DIAS} días):")
    for i, (tipo, motivo, alerta) in enumerate(r["recommendations"], 1):
        print(f"  tramo nuevo {i}: {tipo or 'sin elección: ' + motivo}" + (" (alerta de extrapolación)" if alerta
                                                                            else ""))
    print("archivos en", destino)
