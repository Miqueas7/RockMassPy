"""Histórico sintético de una mina inventada: auditoría de ingesta y correlaciones propias del sitio (nivel 1).

Necesita los extras: pip install "rockmasspy[io,ml,viz,report]". La librería calcula, el ingeniero decide.
Todo es sintético: el histórico lo arma `synthetic_history` con un mecanismo conocido (RMR = 9 ln Q + 44 y
GSI = RMR − 5, más el efecto de cada labor y el ruido). Ningún número viene de una mina.
Imprime solo conteos, estados, coeficientes y nombres de archivo, nunca filas del histórico.
"""
import sys
from pathlib import Path

import rockmasspy as rm
import rockmasspy.report as rp
from rockmasspy.predictive import KINDS, fit_site_correlation, save_site_correlations, synthetic_history

SEMILLA = 12


def main(out_dir: Path) -> dict:
    out_dir = Path(out_dir)
    # 1. El histórico sintético, guardado con las hojas de la plantilla (Tramos, Tipos_sostenimiento, Desempeno)
    historico, verdad = synthetic_history(seed=SEMILLA)
    xlsx = out_dir / "historico.xlsx"
    rm.save_history_xlsx(historico, xlsx)
    # 2. Se lee como se leería el de una mina real y se audita
    h = rm.load_history(xlsx)
    audit = rm.audit_history(h)
    # 3. Nivel 1: los tres pares, por litología y para toda la mina
    ajustes = [fit_site_correlation(h, k) for k in KINDS]
    # 4. El informe (HTML siempre; Word si tienes python-docx)
    rep = rp.build_history_report(audit, ajustes, history=h, lang="es")
    archivos = ["historico.xlsx", rp.write_html(rep, out_dir / "historico.html").name]
    try:
        archivos.append(rp.write_docx(rep, out_dir / "historico.docx").name)
    except ImportError:
        pass
    # 5. Los resultados, como los escribe `rockmass history --output`: hallazgos, correlaciones y el JSON (solo
    #    los ajustes «sitio») para pegar en las tablas por labor
    res = out_dir / "resultados"
    res.mkdir(exist_ok=True)
    escritos = [rm.save_history_findings(audit, res / "history_findings.csv"), *save_site_correlations(ajustes, res)]
    archivos += [f"resultados/{p.name}" for p in escritos]
    return {
        "counts": rm.history_audit_counts(audit),
        "ready": {f"{r.level} {r.item}": r.ready for r in audit.readiness},
        "fits": {r.kind: [(f.label, f.n, f.n_labors, f.status) for f in rp.site_fits(r)] for r in ajustes},
        "mine": {r.kind: (r.mine.a, r.mine.b, r.mine.a_ci) for r in ajustes},
        "truth": {"rmr_from_q": (verdad.rmr_a, verdad.rmr_b), "gsi_from_rmr": (verdad.gsi_c, verdad.gsi_d)},
        "files": archivos,
    }


if __name__ == "__main__":
    import tempfile
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp())
    destino.mkdir(parents=True, exist_ok=True)
    r = main(destino)
    c = r["counts"]
    print(f"\nhistórico: {c['tramos']} tramos, {c['support_types']} tipos, {c['inspections']} inspecciones, "
          f"{c['findings']} hallazgos, {c['items_ready']} de {len(r['ready'])} ítems listos")
    for kind, (a, b, ci) in r["mine"].items():
        verdad = r["truth"].get(kind)
        extra = f" (verdad a {verdad[0]:g}, b {verdad[1]:g})" if verdad else ""
        print(f"{kind} mina: a {a:.3f} (IC {ci[0]:.3f}; {ci[1]:.3f}), b {b:.2f}{extra}")
    print("archivos en", destino)
