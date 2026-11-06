"""Ejemplo 13: la mina sintética de la Fase 5 por la auditoría y los niveles 1, 2 y 3, medida contra su verdad.

Necesita los extras: pip install "rockmasspy[io,ml]". La librería recomienda, el ingeniero decide.
Todo es sintético: `synthetic_mine("base")` arma una mina calibrada con la literatura (≈ 800 tramos, 5 zonas) y
guarda su verdad (`MineTruth`). Es un BANCO DE PRUEBAS: lo que se ajusta aquí nunca se entrega como modelo, ni
da coeficientes por defecto. Ningún número viene de una mina.
Imprime solo conteos, estados, coeficientes y tasas, nunca filas ni ids.
"""
import sys
from collections import Counter
from pathlib import Path

import rockmasspy as rm
from rockmasspy.predictive import (audit_practice, fit_performance, fit_site_correlation, recommend,
                                   synthetic_mine)
from rockmasspy.predictive.synthetic import SUPPORT_TYPES

SEMILLA, SEMILLA_PRUEBA = 30, 1030  # la mina del ajuste y la de las labores nuevas (misma receta, otra semilla)
# Umbral de ejemplo, el del banco: P(falla) aceptable de 0.10 en 365 días. Lo fija el ingeniero (no hay valor por
# defecto); con otro umbral la elección cambia.
UMBRAL, HORIZONTE_DIAS = 0.10, 365
TIPOS = tuple(s.codigo_tipo for s in SUPPORT_TYPES)  # I…V, del más liviano al más pesado
COSTO = {s.codigo_tipo: s.elementos.relative_cost for s in SUPPORT_TYPES}  # I 1.0 … V 6.0
# Categoría de la carta Q (NGI) → tipo de la mina sintética, la misma del generador. En tu mina la defines tú: la
# librería no trae la equivalencia entre tus tipos y las categorías de la carta.
CARTA_A_TIPO = {1: "I", 2: "I", 3: "II", 4: "III", 5: "IV"}  # 6 o más: V


def carta(t) -> str:
    return CARTA_A_TIPO.get(rm.read_q_chart(t.q_valor, t.luz_m / t.esr).category, "V")


def contra_verdad(pares, p_verdad, optimo):
    """Pares (tramo, tipo): % demasiado liviano (P verdadera > umbral) y sobrecosto neto frente al óptimo de verdad
    (el tipo más liviano con P verdadera ≤ umbral), solo en los tramos que tienen óptimo."""
    if not pares:
        return {"n": 0, "liviano": None, "sobrecosto": None}
    liviano = sum(p_verdad[i][c] > UMBRAL for i, c in pares)
    con_opt = [(i, c) for i, c in pares if optimo[i] is not None]
    c_opt = sum(COSTO[optimo[i]] for i, _ in con_opt)
    return {"n": len(pares), "liviano": liviano / len(pares),
            "sobrecosto": sum(COSTO[c] for _, c in con_opt) / c_opt - 1 if c_opt else None}


def main(out_dir: Path, n_boot: int = 500) -> dict:
    out_dir = Path(out_dir)
    # 1. La mina base con su verdad, guardada con la plantilla y leída como la de una mina real
    historico, verdad = synthetic_mine("base", seed=SEMILLA)
    rm.save_history_xlsx(historico, out_dir / "mina_base.xlsx")
    h = rm.load_history(out_dir / "mina_base.xlsx")
    audit = rm.audit_history(h)
    # 2. Nivel 1 (la recta RMR–ln Q emerge de los componentes: la verdad la informa), nivel 2 y nivel 3
    n1 = fit_site_correlation(h, "rmr_from_q", n_boot=n_boot, seed=SEMILLA).mine
    practica = audit_practice(h, n_boot=n_boot, seed=SEMILLA)
    modelo = fit_performance(h, n_boot=n_boot, seed=SEMILLA)
    # 3. Labores nuevas: una segunda mina del mismo escenario (zonas y labores que el ajuste no vio)
    h2, verdad2 = synthetic_mine("base", seed=SEMILLA_PRUEBA)
    nuevos = h2.tramos
    recs = recommend(modelo, nuevos, threshold=UMBRAL, exposure_days=HORIZONTE_DIAS)
    # 4. Contra la verdad: P verdadera de cada tipo (labor nueva en la misma zona) y el óptimo de verdad
    p_verdad = [{c: verdad2.p_fail(t.id_tramo, c, HORIZONTE_DIAS) for c in TIPOS} for t in nuevos]
    optimo = [next((c for c in TIPOS if p[c] <= UMBRAL), None) for p in p_verdad]
    instalado = {t.id_tramo: t.installed_type for t in verdad2.tramos}
    elegidos = [(i, r.chosen) for i, r in enumerate(recs) if r.chosen is not None]
    en_elegidos = [i for i, _ in elegidos]
    comparacion = {
        "modelo": contra_verdad(elegidos, p_verdad, optimo),
        "carta_en_elegidos": contra_verdad([(i, carta(nuevos[i])) for i in en_elegidos], p_verdad, optimo),
        "carta": contra_verdad([(i, carta(t)) for i, t in enumerate(nuevos)], p_verdad, optimo),
        "instalado": contra_verdad([(i, instalado[t.id_tramo]) for i, t in enumerate(nuevos)], p_verdad, optimo),
    }
    return {
        "tramos": len(h.tramos), "tramos_nuevos": len(nuevos),
        "fallas": sum(t.failed for t in verdad.tramos),
        "audit": rm.history_audit_counts(audit),
        "nivel1": (n1.a, n1.a_ci, n1.status, verdad.rmr_lnq_slope),
        "nivel2": (practica.status, practica.verdicts, practica.consistency, practica.consistency_verdict),
        "nivel3": {"calibracion": modelo.calibration, "forma": modelo.form, "zone_sd": modelo.zone_sd,
                   "zone_sd_upper": modelo.zone_sd_upper(), "avisos": modelo.warnings,
                   "bloqueos": modelo.recommendation_blockers},
        "motivos": Counter((r.reason or "chosen").split(":")[0] for r in recs),
        "sin_optimo": sum(o is None for o in optimo),
        "comparacion": comparacion,
        "files": ["mina_base.xlsx"],
    }


def _pct(x):
    return "—" if x is None else f"{100 * x:.1f} %"


def imprimir(r: dict) -> None:
    """Solo agregados: conteos, estados, coeficientes y tasas."""
    c = r["audit"]
    print(f"\nmina base: {r['tramos']} tramos, {r['fallas']} fallas, {c['findings']} hallazgos de auditoría")
    a, ci, estado, a_v = r["nivel1"]
    print(f"nivel 1, RMR–ln Q de la mina: pendiente {a:.2f} (IC {ci[0]:.2f}; {ci[1]:.2f}), {estado}; "
          f"verdad {a_v:.2f}")
    est, ver, cons, cons_v = r["nivel2"]
    print(f"nivel 2: {est}, ln Q {ver['ln_q']}, ln De {ver['ln_de']}, consistencia {cons:.3f} ({cons_v})")
    n3 = r["nivel3"]
    print(f"nivel 3: {n3['calibracion']}, forma {n3['forma']}, σ_z {n3['zone_sd']:.2f} "
          f"(cota {n3['zone_sd_upper']:.2f}), bloqueos: {list(n3['bloqueos']) or 'ninguno'}")
    for aviso in n3["avisos"]:
        print("  aviso:", aviso)
    print(f"recomendación en {r['tramos_nuevos']} tramos nuevos (umbral {UMBRAL}, {HORIZONTE_DIAS} días):")
    for motivo, n in r["motivos"].most_common():
        print(f"  {n:4d}  {motivo}")
    print(f"contra la verdad ({r['sin_optimo']} tramos sin ningún tipo bajo el umbral):")
    for nombre, m in r["comparacion"].items():
        print(f"  {nombre:18s} {m['n']:4d} tramos, demasiado liviano {_pct(m['liviano'])}, "
              f"sobrecosto {_pct(m['sobrecosto'])}")


if __name__ == "__main__":
    import tempfile
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp())
    destino.mkdir(parents=True, exist_ok=True)
    imprimir(main(destino))
    print("archivos en", destino)
