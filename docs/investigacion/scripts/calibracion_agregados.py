"""Agregados de calibración de la mina sintética a partir de bases públicas (solo estadísticas, nunca filas).

Uso (siempre con -I y rutas como argumentos; los datos descargados son no confiables):
    python -I calibracion_agregados.py <base> <archivo>
    <base> ∈ rockmass | mombilia | shirdel | luz_critica | hwstability | adoko | khimti

Imprime medias, desviaciones, cuantiles, proporciones por clase, correlaciones, pendientes y desviación residual.
No imprime nombres de minas, túneles ni filas. ROCKMass y Khimti-2 no tienen licencia: solo consulta interna.
"""
import math
import re
import sys

import numpy as np
import openpyxl

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def num(v):
    """Convierte a float; texto como '3,5' o '>20' → número o NaN."""
    if v is None or isinstance(v, bool):
        return math.nan
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"-?\d+(?:[.,]\d+)?", str(v))
    return float(m.group().replace(",", ".")) if m else math.nan


def hoja(path, nombre=None):
    """Cabecera = primera fila con ≥ 2 textos (igual que estructura.py)."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[nombre] if nombre else wb.worksheets[0]
    filas = [r for r in ws.iter_rows(values_only=True) if any(c not in (None, "") for c in r)]
    hi = next((i for i, r in enumerate(filas[:15]) if sum(isinstance(c, str) for c in r) >= 2), 0)
    cab = [str(c).strip() if c is not None else "" for c in filas[hi]]
    return cab, filas[hi + 1:]


def col(cab, filas, nombre, j=None):
    j = cab.index(nombre) if j is None else j
    return np.array([num(r[j]) if j < len(r) else math.nan for r in filas])


def resumen(etq, x):
    x = x[np.isfinite(x)]
    if len(x) == 0:
        print(f"  {etq}: sin datos"); return
    q = np.percentile(x, [5, 25, 50, 75, 95])
    print(f"  {etq}: n={len(x)} media={x.mean():.3g} de={x.std(ddof=1):.3g} "
          f"p5={q[0]:.3g} p25={q[1]:.3g} p50={q[2]:.3g} p75={q[3]:.3g} p95={q[4]:.3g}")


def proporciones(etq, x, cortes, nombres):
    x = x[np.isfinite(x)]
    k = np.digitize(x, cortes)
    txt = " ".join(f"{nombres[i]}={np.mean(k == i):.1%}" for i in range(len(nombres)))
    print(f"  {etq} (n={len(x)}): {txt}")


def ols(etq, x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if len(x) < 5:
        print(f"  {etq}: n={len(x)} insuficiente"); return None
    A = np.column_stack([x, np.ones_like(x)])
    (a, b), *_ = np.linalg.lstsq(A, y, rcond=None)
    res = y - (a * x + b)
    s = res.std(ddof=2)
    r = np.corrcoef(x, y)[0, 1]
    se_a = s / (x.std(ddof=1) * math.sqrt(len(x) - 1))
    print(f"  {etq}: n={len(x)} pendiente={a:.3f}±{se_a:.3f} intercepto={b:.2f} r={r:.3f} R2={r*r:.3f} "
          f"de_residual={s:.2f}")
    return a, b, s


def logit(etq, X, y, nombres):
    import statsmodels.api as sm
    ok = np.all(np.isfinite(X), axis=1) & np.isfinite(y)
    X, y = X[ok], y[ok]
    try:
        m = sm.Logit(y, sm.add_constant(X)).fit(disp=0)
    except Exception as e:  # separación completa u otra falla numérica
        print(f"  {etq}: no converge ({type(e).__name__})"); return
    p = m.predict(sm.add_constant(X))
    from scipy.stats import rankdata
    r = rankdata(p); n1 = y.sum(); n0 = len(y) - n1
    auc = (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
    coef = " ".join(f"{n}={c:.3f}±{s:.3f}" for n, c, s in zip(["const"] + nombres, m.params, m.bse))
    print(f"  {etq}: n={len(y)} eventos={int(n1)} {coef} AUC={auc:.3f} pseudoR2={m.prsquared:.3f}")


# ----------------------------------------------------------------------------------------------------------------
def rockmass(path):
    cab, f = hoja(path)
    paper = col(cab, f, "From Paper Index")
    rqd, rmr, q, gsi = (col(cab, f, n) for n in ("RQD", "RMR-89", "Q", "GSI"))
    q[q <= 0] = math.nan
    print("ROCKMass/9/5876 (TC304; sin licencia: solo agregados internos)")
    resumen("RQD", rqd); resumen("RMR89", rmr); resumen("log10 Q", np.log10(q)); resumen("GSI", gsi)
    proporciones("RMR89 por clase", rmr, [21, 41, 61, 81], ["V", "IV", "III", "II", "I"])
    proporciones("Q por clase NGI", np.log10(q), np.log10([0.01, 0.1, 1, 4, 10, 40, 100, 400]),
                 ["exc.mala", "ext.mala", "muy mala", "mala", "regular", "buena", "muy buena", "ext.buena", "exc.buena"])
    proporciones("GSI", gsi, [20, 40, 60, 80], ["<20", "20-40", "40-60", "60-80", ">80"])
    lnq = np.log(q)
    ols("RMR = a ln Q + b", lnq, rmr)
    ols("GSI = a RMR89 + b", rmr, gsi)
    ols("GSI = a ln Q + b", lnq, gsi)
    ols("RMR = a RQD + b", rqd, rmr)
    tipo = [r[cab.index("Rock Classification")] for r in f]
    for t in ("Igneous", "Sedimentary", "Metamorphic"):
        m = np.array([x == t for x in tipo])
        ols(f"RMR = a ln Q + b [{t}]", lnq[m], rmr[m])
    # efecto de estudio (≈ sitio): residuo medio por artículo con ≥ 10 pares, y pendientes por artículo
    a, b, s = ols("(global para efectos por estudio)", lnq, rmr)
    ok = np.isfinite(lnq) & np.isfinite(rmr)
    medias, pend, sdin = [], [], []
    for p in np.unique(paper[ok]):
        m = ok & (paper == p)
        if m.sum() >= 10:
            res = rmr[m] - (a * lnq[m] + b)
            medias.append(res.mean()); sdin.append(res.std(ddof=1))
            if np.ptp(lnq[m]) > 2:
                pend.append(np.polyfit(lnq[m], rmr[m], 1)[0])
    print(f"  estudios con >=10 pares RMR-Q: {len(medias)}; de del sesgo por estudio={np.std(medias, ddof=1):.2f}; "
          f"de residual dentro del estudio (mediana)={np.median(sdin):.2f}")
    if pend:
        resumen("pendiente RMR-lnQ por estudio (rango lnQ>2)", np.array(pend))
    ok = np.isfinite(rmr) & np.isfinite(gsi)
    a2, b2 = np.polyfit(rmr[ok], gsi[ok], 1)
    med2 = [np.mean(gsi[ok & (paper == p)] - (a2 * rmr[ok & (paper == p)] + b2))
            for p in np.unique(paper[ok]) if (ok & (paper == p)).sum() >= 10]
    print(f"  estudios con >=10 pares RMR-GSI: {len(med2)}; de del sesgo por estudio={np.std(med2, ddof=1):.2f}")
    d = gsi - rmr
    resumen("GSI − RMR89 (pares)", d[np.isfinite(d)])


def mombilia(path):
    cab, f = hoja(path, "Data Strain Literature")
    q, rmr, gsi = (col(cab, f, n) for n in ("Q", "RMR", "GSI"))
    eps = col(cab, f, "Tunnel strain, ɛ (%)")
    q[q <= 0] = math.nan
    print("Mombilia et al. 2025, túneles con squeezing (CC BY 4.0, v1 = v2 por sha256)")
    resumen("log10 Q", np.log10(q)); resumen("RMR", rmr); resumen("GSI", gsi); resumen("deformación %", eps)
    ols("RMR = a ln Q + b", np.log(q), rmr)
    ols("GSI = a RMR + b", rmr, gsi)
    ols("GSI = a ln Q + b", np.log(q), gsi)
    proporciones("deformación (Hoek 2001: <1, 1-2.5, 2.5-5, 5-10, >10 %)", eps, [1, 2.5, 5, 10],
                 ["sin", "menor", "severo", "muy severo", "extremo"])


def shirdel(path):
    cab, f = hoja(path)
    rmr, gsi = col(cab, f, "RMRa"), col(cab, f, "GSI 2013 [Hoek] Final")
    print("Shirdel 2025, Alborz central (CC BY 4.0; sin revisión por pares)")
    resumen("RMR ajustado", rmr); resumen("GSI 2013", gsi)
    ols("GSI = a RMR + b", rmr, gsi)
    resumen("GSI − RMR", gsi - rmr)
    if len(sys.argv) > 3:  # opcional: la base completa, para RQD y espaciamiento
        cab2, f2 = hoja(sys.argv[3])
        rqd, esp = col(cab2, f2, "RQD %"), col(cab2, f2, "Joint Spacing (cm)")
        resumen("RQD %", rqd); resumen("espaciamiento (cm)", esp)
        ok = np.isfinite(rqd) & np.isfinite(esp) & (esp > 0)
        print(f"  Spearman RQD vs ln espaciamiento: {np.corrcoef(np.argsort(np.argsort(rqd[ok])), np.argsort(np.argsort(esp[ok])))[0, 1]:+.2f}")


def luz_critica(path):
    cab, f = hoja(path)
    rmr, span, est = col(cab, f, "RMR (%)"), col(cab, f, "Span(m)"), col(cab, f, "Stability")
    print("Luz crítica UBC (García-Gonzalo et al. 2016, CC BY 4.0)")
    resumen("RMR", rmr); resumen("luz (m)", span)
    proporciones("RMR por clase", rmr, [21, 41, 61, 81], ["V", "IV", "III", "II", "I"])
    for c in (1, 2, 3):
        print(f"  clase {c}: {np.mean(est == c):.1%}")
    X = np.column_stack([rmr, np.log(span)])
    logit("P(inestable) [3 vs 1-2]", X, (est == 3).astype(float), ["RMR", "ln luz"])
    logit("P(no estable) [2-3 vs 1]", X, (est >= 2).astype(float), ["RMR", "ln luz"])
    m = est != 2
    logit("P(inestable) [3 vs 1, sin la clase 2]", X[m], (est[m] == 3).astype(float), ["RMR", "ln luz"])
    for lo, hi in ((0, 50), (50, 60), (60, 70), (70, 101)):
        k = (rmr >= lo) & (rmr < hi)
        if k.sum():
            print(f"  RMR {lo}-{hi}: n={k.sum()} estable={np.mean(est[k] == 1):.0%} pot.inest={np.mean(est[k] == 2):.0%} "
                  f"inest={np.mean(est[k] == 3):.0%} luz mediana={np.nanmedian(span[k]):.1f} m")


def hwstability(path):
    cab, f = hoja(path, "Manuscript")
    hr, elos, n_, dil = (col(cab, f, n) for n in ("HR (m)", "ELOS Actual (m)", "N'", "Dilution %"))
    depth = col(cab, f, "Depth of excavation")
    estado = np.array([str(r[13]).strip().lower() if len(r) > 13 else "" for r in f])
    y = np.where(estado == "unstable", 1.0, np.where(estado == "stable", 0.0, np.nan))
    print("HWStability (Papaioanou y Suorineni 2016, CC BY 4.0 vía Mendeley)")
    resumen("HR (m)", hr); resumen("N'", n_); resumen("ELOS (m)", elos); resumen("dilución %", dil)
    resumen("profundidad (m)", depth)
    proporciones("ELOS (m)", elos, [0.5, 1, 2, 3], ["<0.5", "0.5-1", "1-2", "2-3", ">3"])
    print(f"  inestable={np.nanmean(y):.1%}")
    logit("P(inestable)", np.column_stack([np.log(n_), np.log(hr)]), y, ["ln N'", "ln HR"])
    ok = np.isfinite(elos) & (elos > 0)
    ols("ln ELOS = a ln N' + b", np.log(n_[ok]), np.log(elos[ok]))
    ols("ln ELOS = a ln HR + b", np.log(hr[ok]), np.log(elos[ok]))


def adoko(path):
    """Tabla 11 del PDF ya pasada por `pdftotext -layout`: líneas que terminan en el estado."""
    hr, n_, qp, est = [], [], [], []
    for linea in open(path, encoding="utf-8", errors="replace"):
        m = re.search(r"(Stable|Unstable|Caved)\s*$", linea)
        if not m:
            continue
        nums = [float(x) for x in re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])", linea[:m.start()])]
        if len(nums) < 6:
            continue
        h, q_, a, b, c, nn = nums[-6:]
        if nn <= 0 or abs(q_ * a * b * c - nn) > 0.05 * nn + 0.05:  # N' = Q'·A·B·C: descarta líneas mal leídas
            continue
        hr.append(h); n_.append(nn); qp.append(q_); est.append(m.group(1))
    hr, n_, qp, est = map(np.array, (hr, n_, qp, est))
    print("Adoko et al. 2021, tajeos de Ghana (CC BY 4.0), filas válidas por N' = Q'ABC")
    print(f"  n={len(est)} estable={np.mean(est == 'Stable'):.1%} inestable={np.mean(est == 'Unstable'):.1%} "
          f"hundido={np.mean(est == 'Caved'):.1%}")
    resumen("HR (m)", hr); resumen("N'", n_); resumen("log10 Q'", np.log10(qp[qp > 0]))
    X = np.column_stack([np.log(n_), np.log(hr)])
    logit("P(no estable)", X, (est != "Stable").astype(float), ["ln N'", "ln HR"])
    logit("P(hundido)", X, (est == "Caved").astype(float), ["ln N'", "ln HR"])


def semivariograma(x, z, lags):
    """Semivariograma experimental 1D (pares por distancia, bins dados)."""
    d = np.abs(x[:, None] - x[None, :]); g = 0.5 * (z[:, None] - z[None, :]) ** 2
    iu = np.triu_indices(len(x), 1); d, g = d[iu], g[iu]
    out = []
    for lo, hi in zip(lags[:-1], lags[1:]):
        k = (d >= lo) & (d < hi)
        if k.sum() >= 30:
            out.append(((lo + hi) / 2, g[k].mean(), k.sum()))
    return np.array(out)


def ajusta_exp(v, var):
    from scipy.optimize import curve_fit
    f = lambda h, c0, c, a: c0 + c * (1 - np.exp(-3 * h / a))  # alcance práctico a
    try:
        (c0, c, a), _ = curve_fit(f, v[:, 0], v[:, 1], p0=[0.2 * var, 0.8 * var, 50], bounds=([0, 0, 1], [var * 3, var * 3, 5000]),
                                  sigma=1 / np.sqrt(v[:, 2]))
        return c0, c, a
    except Exception:
        return None


def khimti(path):
    cab, f = hoja(path)
    ch = col(cab, f, "Chainage")
    names = ("RQD", "Jn", "Jr", "Ja", "Jw", "SRF", "Q")
    v = {n: col(cab, f, n) for n in names}
    ob = col(cab, f, "Overbreak%", j=cab.index("Overbreak%"))
    pull = col(cab, f, "Pull(m)")
    print("Khimti-2 (Nepal), sobreexcavación por voladura (sin licencia válida: solo agregados internos)")
    for n in names[:-1]:
        x = v[n][np.isfinite(v[n])]
        vals, cnt = np.unique(x, return_counts=True)
        top = sorted(zip(cnt, vals), reverse=True)[:6]
        print(f"  {n}: " + " ".join(f"{val:g}={c / len(x):.0%}" for c, val in top))
    resumen("log10 Q", np.log10(v["Q"][v["Q"] > 0])); resumen("sobreexcavación %", ob); resumen("avance (m)", pull)
    from scipy.stats import spearmanr
    M = np.column_stack([v[n] for n in names[:-1]] + [np.log(v["Q"])])
    ok = np.all(np.isfinite(M), axis=1)
    rho = spearmanr(M[ok]).correlation
    lab = list(names[:-1]) + ["lnQ"]
    print("  Spearman entre componentes (n=%d):" % ok.sum())
    for i, a in enumerate(lab):
        print("   " + a.ljust(4) + " ".join(f"{rho[i, j]:+.2f}" for j in range(len(lab))))
    lnq = np.log(v["Q"])
    for etq, z in (("log10 Q", np.log10(v["Q"])), ("RQD", v["RQD"])):
        k = np.isfinite(ch) & np.isfinite(z)
        x, zz = ch[k], z[k]
        _, idx = np.unique(x, return_index=True)  # una observación por progresiva
        x, zz = x[idx], zz[idx]
        var = zz.var(ddof=1)
        sv = semivariograma(x, zz, np.arange(0, 400, 10.0))
        fit = ajusta_exp(sv, var)
        txt = (f"pepita={fit[0]:.3g} ({fit[0] / (fit[0] + fit[1]):.0%} de la meseta) meseta={fit[0] + fit[1]:.3g} "
               f"alcance práctico={fit[2]:.0f} m") if fit else "no ajusta"
        print(f"  variograma {etq}: n={len(x)} varianza={var:.3g} longitud={np.ptp(x):.0f} m; exponencial: {txt}")
        print("    γ(h) por 10 m: " + " ".join(f"{h:.0f}:{g:.3g}" for h, g, _ in sv[:12]))
        sv2 = semivariograma(x, zz, np.arange(0, 155, 5.0))  # estructura corta (las galerías miden decenas de m)
        fit2 = ajusta_exp(sv2, var)
        if fit2:
            print(f"    solo h<=150 m: pepita={fit2[0]:.3g} ({fit2[0] / (fit2[0] + fit2[1]):.0%}) meseta={fit2[0] + fit2[1]:.3g} "
                  f"alcance práctico={fit2[2]:.0f} m")
        dx = np.diff(np.sort(x))
        print(f"    separación entre progresivas: mediana={np.median(dx):.2f} m, p95={np.percentile(dx, 95):.1f} m, "
              f"huecos>20 m={int((dx > 20).sum())}")
    k = np.isfinite(ob) & np.isfinite(lnq)
    from scipy.stats import spearmanr as sp
    print(f"  Spearman sobreexcavación vs ln Q: {sp(ob[k], lnq[k]).correlation:+.2f}")
    k &= ob > 0
    ols("ln sobreexcavación% = a ln Q + b", lnq[k], np.log(ob[k]))
    # corridas: largo de tramos contiguos con Q < 0.1 (proxy de zonas de falla/corte)
    k = np.isfinite(ch) & np.isfinite(v["Q"])
    x, qq = ch[k], v["Q"][k]
    o = np.argsort(x); x, qq = x[o], qq[o]
    malo = qq < 0.1
    largos, ini = [], None
    for i in range(len(x)):
        if malo[i] and ini is None:
            ini = x[i]
        if ini is not None and (not malo[i] or i == len(x) - 1):
            largos.append(x[i] - ini); ini = None
    largos = np.array([l for l in largos if l > 0])
    print(f"  tramos contiguos con Q<0.1: {len(largos)} en {np.ptp(x):.0f} m "
          f"({len(largos) / np.ptp(x) * 1000:.1f} por km); proporción de longitud={malo.mean():.0%}")
    resumen("largo de tramos Q<0.1 (m)", largos)


if __name__ == "__main__":
    base, ruta = sys.argv[1], sys.argv[2]
    {"rockmass": rockmass, "mombilia": mombilia, "shirdel": shirdel, "luz_critica": luz_critica,
     "hwstability": hwstability, "adoko": adoko, "khimti": khimti}[base](ruta)
