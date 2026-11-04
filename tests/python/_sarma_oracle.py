"""Sarma independiente del núcleo (del revisor de la 3D) y el generador de secciones al azar, para la prueba de barrido.

Marco: cara a la derecha. Sección: dict con ground [(x, y)], layers [(bottom | None, mat)], mats [(g, c, phi, ru)],
piezo | None, kh y gw. Integración numérica (Gauss) en lugar de los recortes exactos del núcleo; el FS es el primer
corte K(phi) = kh desde phi = 1/F = 0 sin cruzar un cambio de signo del determinante (la rama física).
"""
import math

import numpy as np

GL_X, GL_W = np.polynomial.legendre.leggauss(8)
SEG_N = 20


def interp(poly, x):
    """Como np.interp (constante fuera del rango), en Python puro: las polilíneas tienen pocos puntos."""
    if x <= poly[0][0]:
        return float(poly[0][1])
    for (x1, y1), (x2, y2) in zip(poly, poly[1:]):
        if x <= x2:
            return float(y1 + (y2 - y1) * (x - x1) / (x2 - x1))
    return float(poly[-1][1])


def eff_bottom(sec, k, x):
    y = interp(sec["ground"], x)
    for i in range(k + 1):
        b = sec["layers"][i][0]
        if b is None:
            return -math.inf
        y = min(y, interp(b, x))
    return y


def layer_at(sec, x, y):
    top = interp(sec["ground"], x)
    for k, (_, m) in enumerate(sec["layers"]):
        bot = eff_bottom(sec, k, x)
        if bot <= y <= top + 1e-9:
            return m
        top = bot
    raise ValueError("below last layer")


def sigma_v(sec, x, y):
    top = interp(sec["ground"], x)
    sv = 0.0
    for k, (_, m) in enumerate(sec["layers"]):
        bot = eff_bottom(sec, k, x)
        if top <= y:
            break
        sv += sec["mats"][m][0] * max(0.0, top - max(y, bot))
        top = bot
    return sv


def pore(sec, x, y):
    if sec.get("piezo") is not None:
        return sec["gw"] * max(interp(sec["piezo"], x) - y, 0.0)
    return sec["mats"][layer_at(sec, x, y)][3] * sigma_v(sec, x, y)


def seg_integral(sec, f, P, Q):
    """∫ f ds a lo largo de P-Q con Gauss compuesto, cortado en los cruces con las líneas de la sección."""
    lines = [sec["ground"]] + [b for b, _ in sec["layers"] if b] + ([sec["piezo"]] if sec.get("piezo") else [])
    P, Q = np.asarray(P, float), np.asarray(Q, float)
    L = float(np.hypot(*(Q - P)))
    br = {0.0, 1.0}
    ts = np.linspace(0, 1, 801)
    for line in lines:
        def h(t):
            p = P + t * (Q - P)
            return p[1] - interp(line, p[0])
        hv = [y - interp(line, x) for x, y in zip((P[0] + ts * (Q[0] - P[0])).tolist(),
                                                   (P[1] + ts * (Q[1] - P[1])).tolist())]
        for i in range(len(ts) - 1):
            if hv[i] == 0:
                br.add(ts[i])
            elif hv[i] * hv[i + 1] < 0:
                a, b = ts[i], ts[i + 1]
                for _ in range(60):
                    m = 0.5 * (a + b)
                    (a, b) = (m, b) if h(m) * hv[i] > 0 else (a, m)
                br.add(0.5 * (a + b))
        if Q[0] != P[0]:
            for x, _ in line:
                t = (x - P[0]) / (Q[0] - P[0])
                if 0 < t < 1:
                    br.add(t)
    br = sorted(br)
    edges = []
    for a, b in zip(br[:-1], br[1:]):
        edges += list(np.linspace(a, b, max(2, int(SEG_N * (b - a)) + 1))[:-1])
    edges.append(1.0)
    tot = 0.0
    for a, b in zip(edges[:-1], edges[1:]):
        for xi, wi in zip(GL_X, GL_W):
            p = P + (0.5 * (a + b) + 0.5 * (b - a) * xi) * (Q - P)
            tot += wi * 0.5 * (b - a) * f(p[0], p[1])
    return tot * L


def vertical_intervals(poly, x):
    ys = []
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        if (x1 <= x < x2) or (x2 <= x < x1):
            ys.append(y1 + (y2 - y1) * (x - x1) / (x2 - x1))
    ys.sort()
    return list(zip(ys[0::2], ys[1::2]))


def wedge_weight(sec, poly, n=600):
    xs = [p[0] for p in poly]
    lo, hi = min(xs), max(xs)
    brk = sorted(set([lo, hi] + xs + [p[0] for b, _ in sec["layers"] if b for p in b] + [p[0] for p in sec["ground"]]))
    brk = [x for x in brk if lo <= x <= hi]
    W = 0.0
    for a, b in zip(brk[:-1], brk[1:]):
        if b - a < 1e-12:
            continue
        edges = np.linspace(a, b, max(4, int(n * (b - a) / (hi - lo)) + 1))
        for e0, e1 in zip(edges[:-1], edges[1:]):
            for xi, wi in zip(GL_X, GL_W):
                x = 0.5 * (e0 + e1) + 0.5 * (e1 - e0) * xi
                w = wi * 0.5 * (e1 - e0)
                for y0, y1 in vertical_intervals(poly, x):
                    top = interp(sec["ground"], x)
                    for k, (_, m) in enumerate(sec["layers"]):
                        bot = eff_bottom(sec, k, x)
                        W += w * sec["mats"][m][0] * max(0.0, min(y1, top) - max(y0, bot))
                        top = bot
    return W


def ray_ground(sec, V, th):
    d = np.array([math.cos(th), math.sin(th)])
    g = sec["ground"]
    best = math.inf
    for (x1, y1), (x2, y2) in zip(g[:-1], g[1:]):
        M = np.array([[d[0], -(x2 - x1)], [d[1], -(y2 - y1)]])
        if abs(np.linalg.det(M)) < 1e-14:
            continue
        t, u = np.linalg.solve(M, np.array([x1 - V[0], y1 - V[1]]))
        if t > 1e-9 and -1e-12 <= u <= 1 + 1e-12:
            best = min(best, t)
    if not math.isfinite(best):
        raise ValueError("no ground cut")
    return np.asarray(V) + best * d


def build(sec, base, angles_deg):
    """Cuñas de la cresta (izq.) al pie (der.); base con extremos sobre el terreno."""
    base = [np.asarray(p, float) for p in base]
    n = len(base) - 1
    T = [ray_ground(sec, base[j + 1], math.radians(angles_deg[j])) for j in range(n - 1)]
    for j in range(n - 2):
        if not T[j + 1][0] > T[j][0]:
            raise ValueError("cross")
    wedges = []
    for i in range(n):
        L, R = base[i], base[i + 1]
        xa = T[i - 1][0] if i else L[0]
        xb = T[i][0] if i < n - 1 else R[0]
        poly = [tuple(L), tuple(R)]
        if i < n - 1:
            poly.append(tuple(T[i]))
        poly += [tuple(p) for p in reversed(sec["ground"]) if xa + 1e-9 < p[0] < xb - 1e-9]
        if i:
            poly.append(tuple(T[i - 1]))
        t = (R - L) / np.linalg.norm(R - L)
        _, c, phi, _ = sec["mats"][layer_at(sec, *(0.5 * (L + R)))]
        wedges.append(dict(t=t, nrm=np.array([-t[1], t[0]]), l=float(np.linalg.norm(R - L)), W=wedge_weight(sec, poly),
                           c=c, tf=math.tan(math.radians(phi)), U=seg_integral(sec, lambda x, y: pore(sec, x, y), L, R)))
    ifs = []
    for j in range(n - 1):
        V, Tj = base[j + 1], T[j]
        Lj = float(np.linalg.norm(Tj - V))
        cl = seg_integral(sec, lambda x, y: sec["mats"][layer_at(sec, x, y)][1], V, Tj)
        tl = seg_integral(sec, lambda x, y: math.tan(math.radians(sec["mats"][layer_at(sec, x, y)][2])), V, Tj)
        U = seg_integral(sec, lambda x, y: pore(sec, x, y), V, Tj)
        d = (Tj - V) / Lj
        ifs.append(dict(d=d, n=np.array([d[1], -d[0]]), L=Lj, c=cl / Lj, tf=tl / Lj, U=U))
    # cinemática: v_j - v_{j+1} = r_j d_j, v_i = s_i t_i
    s = [0.0] * n
    s[-1] = 1.0
    for j in range(n - 2, -1, -1):
        sj, rj = np.linalg.solve(np.column_stack([wedges[j]["t"], -ifs[j]["d"]]), s[j + 1] * wedges[j + 1]["t"])
        if sj <= 0:
            raise ValueError("inadmissible")
        s[j] = sj
        rel_right = -rj * ifs[j]["d"]  # velocidad de la derecha respecto de la izquierda
        ifs[j]["tau_right"] = -rel_right / np.linalg.norm(rel_right) if rj != 0 else np.zeros(2)
    return wedges, ifs


def matrix(wedges, ifs, F):
    n = len(wedges)
    A = np.zeros((2 * n, 2 * n))
    b = np.zeros(2 * n)
    for i, w in enumerate(wedges):
        A[2 * i:2 * i + 2, i] += w["nrm"] - w["tf"] / F * w["t"]
        b[2 * i:2 * i + 2] -= w["U"] * w["nrm"] - w["c"] * w["l"] / F * w["t"] + np.array([0.0, -w["W"]])
        A[2 * i, 2 * n - 1] += w["W"]
    for j, I in enumerate(ifs):
        f_coef = I["n"] + I["tf"] / F * I["tau_right"]
        f_const = I["U"] * I["n"] + I["c"] * I["L"] / F * I["tau_right"]
        for i, sg in ((j + 1, 1.0), (j, -1.0)):
            A[2 * i:2 * i + 2, n + j] += sg * f_coef
            b[2 * i:2 * i + 2] -= sg * f_const
    return A, b


def physical(w, f, kh, dphi=0.002, phimax=20.0):
    """FS: primer corte K(phi) = kh desde phi = 0 sin cruzar un polo; (FS, 'ok' | 'pole' | 'backward' | 'none')."""
    def K(p):
        A, b = matrix(w, f, 1.0 / p if p > 0 else 1e12)
        return np.linalg.solve(A, b)[-1]

    def det(p):
        return np.linalg.det(matrix(w, f, 1.0 / p if p > 0 else 1e12)[0])

    if K(0.0) >= kh:
        return None, "backward"
    p, d0 = 0.0, det(0.0)
    while p < phimax:
        p1 = p + dphi
        d1 = det(p1)
        if np.sign(d1) != np.sign(d0):
            return None, "pole"
        if K(p1) >= kh:
            a, b = p, p1
            for _ in range(80):
                m = 0.5 * (a + b)
                (a, b) = (m, b) if K(m) < kh else (a, m)
            return 1.0 / (0.5 * (a + b)), "ok"
        p, d0 = p1, d1
    return None, "none"


def sarma_phys(sec, base, angles):
    """(FS, por qué, Kc o None si hay polo en [0, 1], N' y E' con F = 1)."""
    w, f = build(sec, base, angles)
    F, why = physical(w, f, sec["kh"])
    ds = {np.sign(np.linalg.det(matrix(w, f, 1.0 / p if p > 0 else 1e12)[0])) for p in np.linspace(0, 1, 501)}
    x1 = np.linalg.solve(*matrix(w, f, 1.0))
    return F, why, (x1[-1] if len(ds) == 1 else None), x1[:-1]


def gen(rng):
    """Sección al azar con cara a la derecha (o None si no sirve): (sección, base, ángulos)."""
    H = rng.uniform(20, 80)
    face = rng.uniform(25, 60)
    xc = -H / math.tan(math.radians(face))
    ground = [(-1000, H), (xc, H)]
    if rng.random() < 0.5:  # quiebre en la cara
        f = rng.uniform(0.3, 0.7)
        ground.append((xc * f + rng.uniform(-0.1, 0.1) * abs(xc), H * f))
    ground += [(0, 0), (1000, 0)]
    xL = xc - rng.uniform(0.3, 1.5) * H
    xR = rng.choice([0.0, rng.uniform(0, 0.3) * H])
    nv = rng.randint(1, 4)
    sag = rng.uniform(0.15, 0.4) * H
    base = [(xL, H)]
    for u in sorted(rng.uniform(0.1, 0.9) for _ in range(nv)):
        base.append((xL + u * (xR - xL), H + u * (0 - H) - sag * 4 * u * (1 - u) * rng.uniform(0.8, 1.2)))
    base.append((xR, 0.0))
    for x, y in base[1:-1]:
        if not y < interp(ground, x) - 0.5:
            return None
    for (x0, y0), (x1, y1) in zip(base[:-1], base[1:]):  # sin tramos de aire
        for u in np.linspace(0.001, 0.999, 400):
            if y0 + u * (y1 - y0) > interp(ground, x0 + u * (x1 - x0)) - 1e-6:
                return None
    nlay = rng.randint(1, 2)
    mats = [(rng.uniform(18, 27), rng.choice([0, rng.uniform(0, 50)]), rng.uniform(20, 40), 0.0) for _ in range(nlay)]
    water = rng.choice(["dry", "ru", "piezo"])
    if water == "ru":
        mats = [(g, c, p, rng.uniform(0, 0.4)) for g, c, p, _ in mats]
    if nlay == 2:
        y0 = rng.uniform(-0.2, 0.6) * H
        sl = rng.uniform(-0.15, 0.15)
        layers = [([(-1000, y0 - sl * 1000), (1000, y0 + sl * 1000)], 0), (None, 1)]
    else:
        layers = [(None, 0)]
    piezo = None
    if water == "piezo":
        fh = rng.uniform(0.2, 0.8)
        piezo = [(-1000, fh * H), (xc, fh * H), (0, -0.5), (1000, -0.5)]
        for x, y in ground:
            if -1000 < x < 1000 and interp(piezo, x) > y:
                return None
    sec = dict(ground=ground, layers=layers, mats=mats, piezo=piezo, kh=rng.choice([0.0, rng.uniform(0, 0.2)]), gw=9.81)
    ang = []  # alrededor de la bisectriz de la base en cada vértice, con ruido
    for j in range(1, len(base) - 1):
        a = math.degrees(math.atan2(base[j][1] - base[j - 1][1], base[j][0] - base[j - 1][0]))
        b = math.degrees(math.atan2(base[j + 1][1] - base[j][1], base[j + 1][0] - base[j][0]))
        ang.append(min(170, max(10, 90 + 0.5 * (a + b) + rng.uniform(-25, 25))))
    return sec, base, ang


def midpoint_on_contact(sec, base):
    """Un tramo de base con su punto medio en un contacto (ahí el núcleo elige el material más débil y el oráculo no)."""
    if len(sec["layers"]) < 2:
        return False
    for P0, P1 in zip(base[:-1], base[1:]):
        mx, my = 0.5 * (P0[0] + P1[0]), 0.5 * (P0[1] + P1[1])
        if abs(my - min(interp(sec["ground"], mx), interp(sec["layers"][0][0], mx))) < 1e-6:
            return True
    return False
