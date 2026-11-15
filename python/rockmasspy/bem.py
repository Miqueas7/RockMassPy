"""Análisis de esfuerzos por elementos de contorno (DDM 2D): formas de ayuda, grilla, strength factor y avisos.

El núcleo C++ (`bem_solve`, `bem_boundary`, `bem_field`) resuelve; aquí se arma la entrada, se enmascara el interior,
se calcula el strength factor y se levantan los avisos. Compresión positiva, MPa y m; ángulos en grados.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from . import _rockmasspy_core as rm

NOTE_ELASTIC = "elastic analysis: strength factor below 1 marks overstress, not failure extent"
WARN_CURVATURE = "elements too coarse for the boundary curvature"
WARN_CORRECTED = "points near the boundary corrected"
WARN_TENSION = "tension zone present"
WARN_COARSE = ("elements too coarse for a narrow pillar or a re-entrant corner; values next to those walls are "
               "unreliable — refine max_element_m")

# La regla de FORMULAS §5 es L <= 0.04·rho, pero con 128 elementos en un círculo L = 0.049·rho; el umbral 0.05 deja
# pasar el valor por omisión y avisa de lo más grueso que eso.
CURVATURE_LIMIT = 0.05
SMOOTH_TURN_DEG = 20.0  # vértices con giro mayor se tratan como esquinas (sin radio de curvatura)


# ---------------------------------------------------------------- formas de ayuda
def circle(cx: float, cy: float, r: float, n: int = 128) -> list[tuple[float, float]]:
    """Círculo con nodos en ángulo uniforme (el punto medio del primer elemento queda en el eje +x)."""
    return ellipse(cx, cy, r, r, n)


def ellipse(cx: float, cy: float, a: float, b: float, n: int = 256) -> list[tuple[float, float]]:
    """Elipse de semiejes a (x) y b (y), nodos en ángulo paramétrico uniforme, antihorario."""
    ts = [2 * math.pi * (k - 0.5) / n for k in range(n)]
    return [(cx + a * math.cos(t), cy + b * math.sin(t)) for t in ts]


def rectangle(cx: float, cy: float, w: float, h: float, n_per_side: int = 32) -> list[tuple[float, float]]:
    """Rectángulo centrado en (cx, cy), antihorario, con `n_per_side` tramos por lado."""
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
    out: list[tuple[float, float]] = []
    for (ax, ay), (bx, by) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        out += [(ax + (bx - ax) * k / n_per_side, ay + (by - ay) * k / n_per_side) for k in range(n_per_side)]
    return out


def horseshoe(cx: float, cy: float, w: float, h_wall: float, n: int = 128) -> list[tuple[float, float]]:
    """Herradura: piso plano en y = cy (centrado en cx), paredes verticales de altura h_wall y bóveda semicircular de
    radio w/2; antihorario. `n` es el número de nodos de la bóveda; piso y paredes llevan n/4 tramos."""
    r, m = w / 2, max(n // 4, 1)
    out = [(cx - r + w * k / m, cy) for k in range(m)]  # piso, izquierda a derecha
    out += [(cx + r, cy + h_wall * k / m) for k in range(m)]  # pared derecha, subiendo
    out += [(cx + r * math.cos(t), cy + h_wall + r * math.sin(t)) for t in (math.pi * k / n for k in range(n))]
    out += [(cx - r, cy + h_wall - h_wall * k / m) for k in range(m)]  # pared izquierda, bajando
    return out


# ---------------------------------------------------------------- material
@dataclass
class BemMaterial:
    """Criterio de falla para el strength factor: "MC" (c, phi, T) o "HB" (sigma_ci con mb, s, a o con gsi, mi, d)."""

    criterion: str
    c_mpa: float | None = None
    phi_deg: float | None = None
    tensile_mpa: float = 0.0
    sigma_ci_mpa: float | None = None
    gsi: float | None = None
    mi: float | None = None
    d: float = 0.0
    mb: float | None = None
    s: float | None = None
    a: float | None = None
    hb_edition: str = "HB2002"

    def __post_init__(self):
        if self.criterion not in ("MC", "HB"):
            raise ValueError("BemMaterial: 'criterion' must be 'MC' or 'HB'")
        if self.criterion == "MC":
            if self.c_mpa is None or self.phi_deg is None:
                raise ValueError("BemMaterial: 'c_mpa' and 'phi_deg' are required for criterion 'MC'")
            return
        if self.sigma_ci_mpa is None:
            raise ValueError("BemMaterial: 'sigma_ci_mpa' is required for criterion 'HB'")
        if self.gsi is not None and self.mi is not None:
            if self.hb_edition not in ("HB2002", "HB2018"):
                raise ValueError("BemMaterial: 'hb_edition' must be 'HB2002' or 'HB2018'")
            p = rm.hb_params(self.gsi, self.mi, self.d, rm.HbEdition[self.hb_edition])
            self.mb, self.s, self.a = p.mb, p.s, p.a
        elif self.mb is None or self.s is None:
            raise ValueError("BemMaterial: criterion 'HB' needs 'gsi' and 'mi', or 'mb' and 's'")
        elif self.a is None:
            self.a = 0.5

    def to_core(self) -> rm.SfMaterial:
        if self.criterion == "MC":
            return rm.SfMaterial(criterion=rm.SfCriterion.MohrCoulomb, c_mpa=self.c_mpa, phi_deg=self.phi_deg,
                                 tensile_mpa=self.tensile_mpa)
        return rm.SfMaterial(criterion=rm.SfCriterion.HoekBrown, sigma_ci_mpa=self.sigma_ci_mpa, mb=self.mb,
                             s=self.s, a=self.a)


# ---------------------------------------------------------------- resultados
@dataclass
class BemBoundaryResult:
    """Por elemento: punto medio, esfuerzo tangencial y desplazamiento del lado del material."""
    x: list[float]
    y: list[float]
    sigma_tt: list[float]
    ux: list[float]
    uy: list[float]


@dataclass
class BemFieldResult:
    """Por punto (grilla en orden de filas, y luego x). Los puntos dentro de una excavación llevan NaN y sf None;
    `sf` None también en tracción; sf puede ser inf (campo hidrostático)."""
    x: list[float]
    y: list[float]
    sigma1: list[float]
    sigma3: list[float]
    sigma_z: list[float]
    angle1: list[float]
    sf: list[float | None]
    tension: list[bool]
    inside: list[bool]
    coarse: list[bool]
    corrected: list[bool]


@dataclass
class BemResult:
    boundary: BemBoundaryResult
    field: BemFieldResult
    min_sf: float | None  # solo puntos fuera, finitos y no `coarse`
    min_sf_location: tuple[float, float] | None  # solo aquí: nunca en avisos ni errores
    min_sf_coarse: float | None  # mínimo entre los puntos `coarse`
    tension_count: int
    info: object
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    needs_attention: bool = False
    excavations: list = field(default_factory=list)  # polígonos de entrada, para dibujar el contorno real


# ---------------------------------------------------------------- análisis
def _dist(p, q):
    return math.hypot(p[0] - q[0], p[1] - q[1])


def _perimeter(poly):
    return sum(_dist(poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))


def _core_error(exc: ValueError) -> ValueError:
    """Traduce los nombres de parámetro del núcleo a los de esta API (el mensaje no lleva valores)."""
    msg = str(exc)
    if "elements_per_side_hint" in msg:
        return ValueError("parameter 'excavations' gives more than 2048 elements; use a larger 'max_element_m'")
    return ValueError(re.sub(r"'(contours|vertices)'", "'excavations'", msg))


def _coarse_curvature(polys, max_el: float) -> bool:
    """True si en algún vértice suave (giro < 20°) el elemento vecino mide más de CURVATURE_LIMIT·rho."""
    for p in polys:
        n = len(p)
        if p[0] == p[-1]:
            p = p[:-1]
            n -= 1
        sides = [_dist(p[i], p[(i + 1) % n]) for i in range(n)]
        elen = [s / max(math.ceil(s / max_el), 1) for s in sides]
        for i in range(n):
            a, b, c = p[i - 1], p[i], p[(i + 1) % n]
            ab, bc, ca = _dist(a, b), _dist(b, c), _dist(c, a)
            area2 = abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
            if area2 < 1e-12 * ab * bc or ab == 0 or bc == 0:
                continue  # colineal: radio infinito
            turn = math.degrees(math.acos(max(-1.0, min(1.0, ((b[0] - a[0]) * (c[0] - b[0]) +
                                                              (b[1] - a[1]) * (c[1] - b[1])) / (ab * bc)))))
            if turn >= SMOOTH_TURN_DEG:
                continue
            rho = ab * bc * ca / (2 * area2)
            if max(elen[i - 1], elen[i]) > CURVATURE_LIMIT * rho:
                return True
    return False


def analyze_bem(excavations, *, sigma1_mpa: float, sigma3_mpa: float, alpha_deg: float = 90.0,
                sigma_z_mpa: float | None = None, e_mpa: float, nu: float, material: BemMaterial | None = None,
                grid: tuple | None = None, points=None, max_element_m: float | None = None,
                sf_mode: str = "rs2") -> BemResult:
    """Esfuerzos alrededor de excavaciones 2D en medio elástico infinito (deformación plana, sin gravedad).

    `excavations`: lista de polígonos (listas de (x, y)); `grid` = (xmin, xmax, ymin, ymax, nx, ny) o `points`;
    sin ninguno, una caja de 3 veces la extensión de las excavaciones con 60 × 60 puntos.
    `max_element_m` por omisión: max(menor perímetro / 128, perímetro total / 2000). `sf_mode`: "rs2" o "examine2d".
    """
    polys = [[(float(x), float(y)) for x, y in p] for p in excavations]
    if not polys:
        raise ValueError("parameter 'excavations' must not be empty")
    if sf_mode not in ("rs2", "examine2d"):
        raise ValueError("parameter 'sf_mode' must be 'rs2' or 'examine2d'")
    if grid is not None and points is not None:
        raise ValueError("parameters 'grid' and 'points' are mutually exclusive")
    if max_element_m is None:
        # el tope de 2048 elementos limita el cociente entre el perímetro total y el elemento
        max_element_m = max(min(_perimeter(p) for p in polys) / 128, sum(_perimeter(p) for p in polys) / 2000)
    try:
        sol = rm.bem_solve(rm.BemInput(
            contours=[rm.BemContour(vertices=p) for p in polys], sigma1_mpa=sigma1_mpa, sigma3_mpa=sigma3_mpa,
            alpha_deg=alpha_deg, sigma_z_mpa=math.nan if sigma_z_mpa is None else sigma_z_mpa, e_mpa=e_mpa, nu=nu,
            max_element_m=max_element_m))
    except ValueError as exc:
        raise _core_error(exc) from None
    b = rm.bem_boundary(sol)

    if points is None:
        if grid is None:
            xs = [x for p in polys for x, _ in p]
            ys = [y for p in polys for _, y in p]
            cx, cy, w, h = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, max(xs) - min(xs), max(ys) - min(ys)
            grid = (cx - 1.5 * w, cx + 1.5 * w, cy - 1.5 * h, cy + 1.5 * h, 60, 60)
        xmin, xmax, ymin, ymax, nx, ny = grid
        if not (float(nx).is_integer() and float(ny).is_integer()):
            raise ValueError("parameter 'grid' needs integer nx and ny")
        nx, ny = int(nx), int(ny)
        if nx < 2 or ny < 2 or not (xmax > xmin and ymax > ymin):
            raise ValueError("parameter 'grid' needs xmin < xmax, ymin < ymax and nx, ny of at least 2")
        points = [(xmin + (xmax - xmin) * i / (nx - 1), ymin + (ymax - ymin) * j / (ny - 1))
                  for j in range(ny) for i in range(nx)]
    pts = [(float(x), float(y)) for x, y in points]
    st = rm.bem_field(sol, pts)

    sf: list[float | None] = [None] * len(pts)
    tension = [False] * len(pts)
    if material is not None:
        mode = rm.SfMode.RS2 if sf_mode == "rs2" else rm.SfMode.Examine2D
        mat = material.to_core()
        for k, (s, p) in enumerate(zip(st, pts)):
            if s.inside:
                continue
            r = rm.strength_factor(mat, s.sigma1, s.sigma3, s.szz, mode)
            sf[k], tension[k] = r.sf, bool(r.tension)
    else:
        tension = [(not s.inside) and s.sigma3 < 0 for s in st]

    nan = math.nan
    fld = BemFieldResult(
        x=[p[0] for p in pts], y=[p[1] for p in pts],
        sigma1=[nan if s.inside else s.sigma1 for s in st], sigma3=[nan if s.inside else s.sigma3 for s in st],
        sigma_z=[nan if s.inside else s.szz for s in st], angle1=[nan if s.inside else s.angle1_deg for s in st],
        sf=sf, tension=tension, inside=[bool(s.inside) for s in st], coarse=[bool(s.coarse) for s in st],
        corrected=[bool(s.corrected) for s in st])

    def finite(k):
        return sf[k] is not None and math.isfinite(sf[k])

    ok = [k for k in range(len(pts)) if finite(k) and not fld.coarse[k]]
    kmin = min(ok, key=lambda k: sf[k]) if ok else None
    cs = [sf[k] for k in range(len(pts)) if finite(k) and fld.coarse[k]]
    tension_count = sum(tension)

    warnings: list[str] = []
    if _coarse_curvature(polys, max_element_m):
        warnings.append(WARN_CURVATURE)
    if any(c and not i for c, i in zip(fld.corrected, fld.inside)):
        warnings.append(WARN_CORRECTED)
    if tension_count:
        warnings.append(WARN_TENSION)
    if any(fld.coarse):
        warnings.append(WARN_COARSE)
    min_sf = None if kmin is None else sf[kmin]
    return BemResult(
        boundary=BemBoundaryResult(list(b.x), list(b.y), list(b.sigma_tt_mpa), list(b.ux_m), list(b.uy_m)),
        field=fld, min_sf=min_sf, min_sf_location=None if kmin is None else pts[kmin],
        min_sf_coarse=min(cs) if cs else None, tension_count=tension_count, info=sol.info, warnings=warnings,
        notes=[NOTE_ELASTIC],
        needs_attention=bool((min_sf is not None and min_sf < 1) or tension_count or any(fld.coarse)),
        excavations=polys)


# ---------------------------------------------------------------- lectura de excavaciones
def load_excavations(path, sheet: str = "Excavaciones") -> list[list[tuple[float, float]]]:
    """Polígonos de la hoja `Excavaciones` (columnas id, orden, x, y) de un .xlsx o .csv (coma decimal con ';').

    Un polígono por id, con los vértices en el orden de `orden`. Los ids solo agrupan: no salen en ningún mensaje.
    """
    from pathlib import Path

    from .csv_io import _CsvSource
    from .excel_io import _open, _sheet_rows

    p = Path(path)
    src = _CsvSource({sheet: p}) if p.suffix.lower() == ".csv" else _open(p)
    try:
        try:
            rows = _sheet_rows(src, sheet, ("id", "orden", "x", "y"), {"id", "orden", "x", "y"}, {"orden", "x", "y"})
        except ValueError as exc:  # el mensaje de celda trae el valor leído: no se repite
            raise ValueError(re.sub(r", got '.*'$", "", str(exc))) from None
    finally:
        if hasattr(src, "wb"):
            src.wb.close()
    groups: dict[str, list] = {}
    for _, r in rows:
        groups.setdefault(r["id"], []).append((r["orden"], r["x"], r["y"]))
    if any(len({o for o, _, _ in g}) != len(g) for g in groups.values()):
        raise ValueError(f"sheet '{sheet}': duplicate value in column 'orden' within an excavation")
    if not groups:
        raise ValueError(f"sheet '{sheet}': no excavations found")
    return [[(x, y) for _, x, y in sorted(g)] for g in groups.values()]
