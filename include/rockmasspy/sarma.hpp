/**
 * @file sarma.hpp
 * @brief Sarma con tajadas no verticales: cuñas rígidas, equilibrio de fuerzas, FS y aceleración crítica Kc.
 *
 * Fuente (Secondary): Sarma (1979) y Hoek (1987) no se leyeron; se comprueba contra el Slide Sarma Verification
 * Manual (Rocscience 2016), problema 4, y contra el bloque planar de Hoek con una sola cuña.
 * Sección: la `LeSection` de la 3C (estratos, materiales Mohr-Coulomb, ru o piezométrica, kh). Hoek-Brown, agua
 * encharcada sobre el terreno y grieta de tracción lanzan «not supported in Sarma» (R5).
 * Geometría: `base` es la polilínea de la superficie de falla con x creciente y extremos sobre (o encima de) el terreno;
 * la masa va entre sus dos cortes con el terreno, sin tramos de aire. Cada vértice interior es el pie de una interfaz
 * recta que sube con su ángulo hasta el primer corte con el terreno.
 * Ángulos: en grados, antihorario desde +x en las coordenadas de la sección del usuario (90 = vertical), uno por
 * vértice interior de `base`, en (0, 180). Como en la 3C, el núcleo detecta hacia dónde mira la cara y, si mira a la
 * izquierda, refleja x -> -x por dentro (marco interno con la cara a la derecha); ahí el ángulo pasa a 180 - θ. Así una
 * sección reflejada con θ -> 180 - θ da el mismo FS y el mismo Kc. Los ángulos del resultado salen en las
 * coordenadas del usuario, y las cuñas de izquierda a derecha en x del usuario.
 * Cuñas: polígono entre su tramo de base, sus dos interfaces (o el extremo de la masa) y el terreno; el peso es el
 * área por estrato (recorte del polígono contra la base efectiva de cada estrato, la misma de la 3C) por su γ.
 * Resistencia: la base toma el material de su punto medio (en un contacto, el candidato más débil por τ con su σn'
 * de la solución, hasta 3 pasadas, como la 3C); la interfaz toma c y tan φ ponderados por longitud a lo largo de la
 * interfaz, por estrato (R3).
 * Agua: fuerza de poros normal a cada base e interfaz, integral exacta de u por tramos lineales: con piezométrica,
 * u = γw·max(y_piezo - y, 0) (el ru se ignora, nota); sin ella, u = ru·σv con σv el peso de los estratos sobre el
 * punto y el ru del material del punto.
 * Cinemática: la cuña del pie se mueve a lo largo de su base hacia el pie; las demás, a lo largo de su base con la
 * velocidad relativa paralela a la interfaz. Una velocidad <= 0 lanza «inadmissible mechanism at interface k».
 * El cortante de la base se opone al movimiento de la cuña; el de cada interfaz, al movimiento relativo.
 * Solución: para F fijo, sistema lineal 2n x 2n en N', E' y K (fuerza horizontal K·W hacia la cara). K baja con F;
 * el FS es el F con K = kh, por bisección en 1/F con intervalo; Kc = K con F = 1 (si sale <= 0, Kc = 0 con aviso).
 * N' < 0 en una base o E' < 0 en una interfaz da un aviso agregado. Sin resistencia, FS = 0; si con resistencia nula
 * K >= kh, la masa no se mueve hacia la cara (FS vacío, nota). Sin convergencia: FS vacío y aviso.
 * Optimización (opcional): búsqueda de patrón sobre los ángulos, dentro de [angle_min_deg, angle_max_deg] en las
 * coordenadas del usuario, que minimiza el FS; los ángulos que dan una geometría o cinemática inválida se descartan.
 * El Kc se da con los ángulos del FS mínimo.
 * Fuerzas de cada cuña: base_shear_strength es la resistencia disponible c l + N' tan φ; interface_shear_right es el
 * cortante movilizado (c L + E' tan φ) / FS de la interfaz del lado derecho (en x del usuario).
 */

#pragma once

#include <algorithm>
#include <cmath>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

#include "rockmasspy/limit_equilibrium.hpp"

namespace rockmasspy {

struct SarmaInput {
    std::vector<Point2> base;
    std::vector<double> interface_angles_deg;
};

struct SarmaOptions {
    double tolerance = 1e-6;
    int max_iterations = 200;
    bool optimize_angles = false;
    double angle_min_deg = 20, angle_max_deg = 160;
};

struct SarmaWedge {
    double area, weight, base_normal, base_shear_strength, interface_normal_right, interface_shear_right;
    int base_material;
};

struct SarmaResult {
    std::optional<double> factor_of_safety;
    std::optional<double> critical_acceleration;
    std::vector<double> interface_angles_deg;
    std::vector<SarmaWedge> wedges;
    MethodInfo info;
    std::vector<std::string> warnings, notes;
};

namespace sarma_detail {
using le_detail::at;
using le_detail::fail;
using le_detail::interp;
using le_detail::kPi;
using le_detail::kTol;
using le_detail::Poly;

struct V2 {
    double x, y;
};
inline V2 operator-(Point2 a, Point2 b) { return {a.x - b.x, a.y - b.y}; }
inline V2 unit(V2 v) {
    const double n = std::hypot(v.x, v.y);
    return {v.x / n, v.y / n};
}
inline double cross(V2 a, V2 b) { return a.x * b.y - a.y * b.x; }

/// Sección en el marco interno (cara a la derecha) y lo que no depende de los ángulos.
struct Model {
    const LeSection* s = nullptr;
    le_detail::Geo g;
    bool reflected = false;
    double xl = 0, xr = 0, size = 1;
    std::vector<Point2> bverts;  // base dentro de la masa: corte izquierdo, vértices interiores, corte derecho
    std::vector<const Poly*> lines;  // terreno, bases de estratos y piezométrica
    std::vector<double> xbreaks;     // vértices de las líneas y sus cortes entre sí
};

/// Base efectiva del estrato k en x (la de la 3C: nunca sobre el terreno ni sobre la de un estrato superior).
inline double eff_bottom(const Model& m, std::size_t k, double x) {
    double y = interp(m.g.ground, x);
    for (std::size_t i = 0; i <= k; ++i) y = std::min(y, interp(m.g.bottoms[i], x));
    return y;
}

/// Materiales del punto (más de uno en un contacto), como el de la base de una tajada de la 3C.
inline std::vector<int> materials_at(const Model& m, double x, double y) {
    std::vector<int> cand;
    double top = interp(m.g.ground, x);
    for (std::size_t k = 0; k < m.g.bottoms.size(); ++k) {
        const double bot = m.g.bottoms[k].empty() ? -std::numeric_limits<double>::infinity()
                                                  : std::min(top, interp(m.g.bottoms[k], x));
        if (y >= bot - kTol && y <= top + kTol) cand.push_back(m.g.material[k]);
        top = bot;
    }
    if (cand.empty()) fail("base", "passes below the bottom of the last layer");
    return cand;
}

inline double sigma_v(const Model& m, double x, double y) {
    double top = interp(m.g.ground, x), sv = 0.0;
    for (std::size_t k = 0; k < m.g.bottoms.size() && top > y; ++k) {
        const double bot = m.g.bottoms[k].empty() ? -std::numeric_limits<double>::infinity()
                                                  : std::min(top, interp(m.g.bottoms[k], x));
        sv += m.s->materials[m.g.material[k]].unit_weight * std::max(0.0, top - std::max(y, bot));
        top = bot;
    }
    return sv;
}

inline double pore(const Model& m, double x, double y) {
    if (m.g.piezo) return m.s->water_unit_weight * std::max(interp(*m.g.piezo, x) - y, 0.0);
    double ru = 0.0;
    for (int k : materials_at(m, x, y)) ru = std::max(ru, m.s->materials[k].ru);
    return ru * sigma_v(m, x, y);
}

/// Tramos del segmento P-Q en los que todas las líneas son lineales y no cruzan el segmento; f(punto medio, largo).
template <class F>
void pieces(const Model& m, Point2 P, Point2 Q, F f) {
    std::vector<double> ts{0.0, 1.0};
    if (Q.x != P.x)
        for (double xb : m.xbreaks) {
            const double t = (xb - P.x) / (Q.x - P.x);
            if (t > 0.0 && t < 1.0) ts.push_back(t);
        }
    std::sort(ts.begin(), ts.end());
    auto pt = [&](double t) { return Point2{P.x + t * (Q.x - P.x), P.y + t * (Q.y - P.y)}; };
    std::vector<double> all = ts;
    for (std::size_t i = 0; i + 1 < ts.size(); ++i)
        for (const Poly* L : m.lines) {
            const Point2 a = pt(ts[i]), b = pt(ts[i + 1]);
            const double da = a.y - interp(*L, a.x), db = b.y - interp(*L, b.x);
            if ((da > 0.0 && db < 0.0) || (da < 0.0 && db > 0.0)) all.push_back(ts[i] + (ts[i + 1] - ts[i]) * da / (da - db));
        }
    std::sort(all.begin(), all.end());
    const double len = std::hypot(Q.x - P.x, Q.y - P.y);
    for (std::size_t i = 0; i + 1 < all.size(); ++i)
        if (all[i + 1] > all[i]) f(pt(0.5 * (all[i] + all[i + 1])), (all[i + 1] - all[i]) * len);
}

/// Integral de u a lo largo del segmento (u es lineal en cada tramo: el punto medio es exacto).
inline double pore_force(const Model& m, Point2 P, Point2 Q) {
    double U = 0.0;
    pieces(m, P, Q, [&](Point2 c, double l) { U += pore(m, c.x, c.y) * l; });
    return U;
}

inline double area(const std::vector<Point2>& p) {
    double a = 0.0;
    for (std::size_t i = 0; i < p.size(); ++i) {
        const Point2& u = p[i];
        const Point2& v = p[(i + 1) % p.size()];
        a += u.x * v.y - v.x * u.y;
    }
    return 0.5 * std::fabs(a);
}

/// Sutherland-Hodgman contra el semiplano h(p) >= 0 (h lineal).
template <class H>
std::vector<Point2> clip(const std::vector<Point2>& p, H h) {
    std::vector<Point2> out;
    for (std::size_t i = 0; i < p.size(); ++i) {
        const Point2& a = p[i];
        const Point2& b = p[(i + 1) % p.size()];
        const double ha = h(a), hb = h(b);
        if (ha >= 0.0) out.push_back(a);
        if ((ha >= 0.0) != (hb >= 0.0)) {
            const double t = ha / (ha - hb);
            out.push_back({a.x + t * (b.x - a.x), a.y + t * (b.y - a.y)});
        }
    }
    return out;
}

/// Área del polígono sobre la base efectiva del estrato k (lineal entre cortes consecutivos de xbreaks).
inline double area_above(const Model& m, const std::vector<Point2>& poly, std::size_t k) {
    double lo = poly.front().x, hi = lo;
    for (const auto& q : poly) {
        lo = std::min(lo, q.x);
        hi = std::max(hi, q.x);
    }
    std::vector<double> xs{lo, hi};
    for (double x : m.xbreaks)
        if (x > lo && x < hi) xs.push_back(x);
    std::sort(xs.begin(), xs.end());
    double A = 0.0;
    for (std::size_t i = 0; i + 1 < xs.size(); ++i) {
        const double a = xs[i], b = xs[i + 1];
        if (b <= a) continue;
        const double ya = eff_bottom(m, k, a), yb = eff_bottom(m, k, b);
        auto q = clip(poly, [&](Point2 p) { return p.x - a; });
        q = clip(q, [&](Point2 p) { return b - p.x; });
        q = clip(q, [&](Point2 p) { return p.y - (ya + (yb - ya) * (p.x - a) / (b - a)); });
        if (q.size() >= 3) A += area(q);
    }
    return A;
}

inline Model make_model(const LeSection& s, const SarmaInput& in) {
    using namespace le_detail;
    SlipSurface f;
    f.polyline = in.base;
    validate(s, f, LeOptions{});
    for (std::size_t i = 0; i < s.materials.size(); ++i)
        if (s.materials[i].model == StrengthModel::HoekBrown)
            fail(at("materials", i) + ".model", "Hoek-Brown is not supported in Sarma");
    if (s.crack) fail("crack", "tension crack is not supported in Sarma");
    Model m;
    m.s = &s;
    const Geo g0 = make_geo(s, f, false);
    Mass ms = find_mass(g0);
    const double yl = interp(g0.ground, ms.xl), yr = interp(g0.ground, ms.xr);
    if (std::fabs(yl - yr) <= kTol) fail("surface", "is level at both ends of the sliding mass: the face direction is undefined");
    m.reflected = yr > yl;
    m.g = make_geo(s, f, m.reflected);
    if (m.reflected) ms = find_mass(m.g);
    if (ms.air) fail("base", "must stay below the ground surface between its two cuts with it");
    m.xl = ms.xl;
    m.xr = ms.xr;
    const Poly& b = *m.g.polyline;
    m.size = std::hypot(b.back().x - b.front().x, b.back().y - b.front().y);
    for (std::size_t k = 0; k < m.g.bottoms.size(); ++k)
        if (!m.g.bottoms[k].empty() && !covers(m.g.bottoms[k], m.xl, m.xr))
            fail(at("layers", k) + ".bottom", "does not cover the sliding mass");
    if (m.g.piezo && !covers(*m.g.piezo, m.xl, m.xr)) fail("piezometric", "does not cover the sliding mass");
    if (m.g.base_y)
        for (const auto& q : b)
            if (q.x >= m.xl && q.x <= m.xr && q.y < *m.g.base_y - kTol) fail("base", "goes below model_base_y");
    // vértices interiores dentro de la masa, en el orden del marco interno
    const std::size_t nv = in.base.size() - 2;
    m.bverts.push_back({m.xl, interp(b, m.xl)});
    for (std::size_t i = 1; i + 1 < b.size(); ++i) {
        const std::size_t user = m.reflected ? nv - i : i - 1;
        if (!(b[i].x > m.xl + kTol && b[i].x < m.xr - kTol && interp(m.g.ground, b[i].x) - b[i].y > kTol))
            fail(at("base", user + 1), "must lie below the ground surface inside the sliding mass");
        m.bverts.push_back(b[i]);
    }
    m.bverts.push_back({m.xr, interp(b, m.xr)});
    m.lines.push_back(&m.g.ground);
    for (const auto& bt : m.g.bottoms)
        if (!bt.empty()) m.lines.push_back(&bt);
    if (m.g.piezo) m.lines.push_back(&*m.g.piezo);
    for (std::size_t i = 0; i < m.lines.size(); ++i) {
        for (const auto& q : *m.lines[i]) m.xbreaks.push_back(q.x);
        for (std::size_t j = i + 1; j < m.lines.size(); ++j)
            for (double x : poly_cuts(*m.lines[i], *m.lines[j])) m.xbreaks.push_back(x);
    }
    sort_unique(m.xbreaks);
    if (m.g.piezo) {  // agua encharcada: la piezométrica sobre el terreno en algún punto de la masa
        std::vector<double> xs{m.xl, m.xr};
        for (double x : m.xbreaks)
            if (x > m.xl && x < m.xr) xs.push_back(x);
        for (double x : xs)
            if (interp(*m.g.piezo, x) - interp(m.g.ground, x) > kTol)
                fail("piezometric", "ponded water above the ground surface is not supported in Sarma");
    }
    return m;
}

/// Cuña en el marco interno, de la cresta (0) al pie (n - 1).
struct Wedge {
    std::vector<Point2> poly;
    Point2 L, R;  // tramo de base, de izquierda a derecha
    V2 t, nrm;    // dirección del movimiento (de L a R) y normal hacia la cuña
    double l, area, W, U;
    std::vector<int> cand;
    int mat;
    double c, tf;
};
/// Interfaz j entre la cuña j (izquierda) y la j + 1 (derecha), del vértice V al terreno T.
struct Interface {
    Point2 V, T;
    V2 d, nn, tau;  // dirección hacia arriba, normal hacia la cuña derecha, cortante sobre la cuña derecha
    double L, c, tf, U;
    bool mixed;
};
struct Mechanism {
    std::vector<Wedge> w;
    std::vector<Interface> f;
};

inline bool segments_cross(Point2 a, Point2 b, Point2 c, Point2 d) {
    const double d1 = cross(b - a, c - a), d2 = cross(b - a, d - a), d3 = cross(d - c, a - c), d4 = cross(d - c, b - c);
    return ((d1 > 0) != (d2 > 0)) && ((d3 > 0) != (d4 > 0)) && d1 != 0 && d2 != 0 && d3 != 0 && d4 != 0;
}

/// Geometría, pesos, resistencias, agua y velocidades para unos ángulos del marco interno. Lanza si no es admisible.
inline Mechanism make_mechanism(const Model& m, const std::vector<double>& angles) {
    const std::size_t ni = angles.size(), n = ni + 1;
    auto user = [&](std::size_t j) { return m.reflected ? ni - 1 - j : j; };
    const LeSection& s = *m.s;
    const double tol = 1e-9 * m.size;
    Mechanism mech;
    // velocidades compatibles desde la cuña del pie; s_j > 0 equivale a que la interfaz entre en la masa por su vértice
    // (entre la base hacia el pie y la base hacia la cresta), así que se revisa antes que el corte con el terreno
    std::vector<V2> dirs(ni), taus(ni);
    V2 v = unit(m.bverts[ni + 1] - m.bverts[ni]);
    for (std::size_t j = ni; j-- > 0;) {
        const double th = angles[j] * kPi / 180.0;
        const V2 t = unit(m.bverts[j + 1] - m.bverts[j]), d{std::cos(th), std::sin(th)};
        const double det = cross(d, t);  // [t, -d] [s; r] = v
        const double sj = det != 0.0 ? cross(d, v) / det : 0.0, r = det != 0.0 ? cross(t, v) / det : 0.0;
        if (!(sj > 1e-12))
            fail(at("interface_angles_deg", user(j)), "inadmissible mechanism at interface " + std::to_string(user(j)));
        // la cuña derecha se mueve -r d respecto de la izquierda: el cortante sobre ella va en +sign(r) d
        dirs[j] = d;
        taus[j] = r < 0.0 ? V2{-d.x, -d.y} : d;
        v = {sj * t.x, sj * t.y};
    }
    for (std::size_t j = 0; j < ni; ++j) {
        Interface I{};
        I.V = m.bverts[j + 1];
        I.d = dirs[j];
        I.tau = taus[j];
        const std::string name = at("interface_angles_deg", user(j));
        // primer corte del rayo con el terreno
        double best = std::numeric_limits<double>::infinity();
        const Poly& gr = m.g.ground;
        for (std::size_t k = 0; k + 1 < gr.size(); ++k) {
            const V2 e = gr[k + 1] - gr[k], w = gr[k] - I.V;
            const double den = cross(I.d, e);
            if (den == 0.0) continue;
            const double t = cross(w, e) / den, u = cross(w, I.d) / den;
            if (t > tol && u >= -1e-12 && u <= 1.0 + 1e-12) best = std::min(best, t);
        }
        if (!std::isfinite(best)) fail(name, "interface does not cut the ground surface");
        I.T = {I.V.x + best * I.d.x, I.V.y + best * I.d.y};
        I.L = best;
        if (!(I.T.x > m.xl + tol && I.T.x < m.xr - tol))
            fail(name, "interface does not cut the ground surface inside the sliding mass");
        for (std::size_t k = 0; k + 1 < m.bverts.size(); ++k)
            if (k != j && k != j + 1 && segments_cross(I.V, I.T, m.bverts[k], m.bverts[k + 1]))
                fail(name, "interface crosses the base");
        I.nn = {I.d.y, -I.d.x};
        mech.f.push_back(I);
    }
    for (std::size_t j = 0; j + 1 < ni; ++j)
        if (!(mech.f[j + 1].T.x > mech.f[j].T.x + tol) || segments_cross(mech.f[j].V, mech.f[j].T, mech.f[j + 1].V, mech.f[j + 1].T)) {
            const std::size_t a = std::min(user(j), user(j + 1)), b = std::max(user(j), user(j + 1));
            fail("interface_angles_deg", "interfaces " + std::to_string(a) + " and " + std::to_string(b) + " cross");
        }
    // cuñas
    for (std::size_t i = 0; i < n; ++i) {
        Wedge w{};
        w.L = m.bverts[i];
        w.R = m.bverts[i + 1];
        const double xa = i ? mech.f[i - 1].T.x : m.xl, xb = i < ni ? mech.f[i].T.x : m.xr;
        w.poly = {w.L, w.R};
        if (i < ni) w.poly.push_back(mech.f[i].T);
        for (auto it = m.g.ground.rbegin(); it != m.g.ground.rend(); ++it)
            if (it->x < xb - kTol && it->x > xa + kTol) w.poly.push_back(*it);
        if (i) w.poly.push_back(mech.f[i - 1].T);
        w.area = area(w.poly);
        if (!(w.area > 1e-12 * m.size * m.size))
            fail("interface_angles_deg", "wedge " + std::to_string(m.reflected ? ni - i : i) + " has no area");
        double prev = 0.0;
        for (std::size_t k = 0; k < m.g.bottoms.size(); ++k) {
            const double above = m.g.bottoms[k].empty() ? w.area : area_above(m, w.poly, k);
            w.W += s.materials[m.g.material[k]].unit_weight * std::max(0.0, above - prev);
            prev = std::max(prev, above);
        }
        if (w.area - prev > 1e-9 * w.area) fail("base", "passes below the bottom of the last layer");
        w.t = unit(w.R - w.L);
        w.nrm = {-w.t.y, w.t.x};
        w.l = std::hypot(w.R.x - w.L.x, w.R.y - w.L.y);
        w.U = pore_force(m, w.L, w.R);
        w.cand = materials_at(m, 0.5 * (w.L.x + w.R.x), 0.5 * (w.L.y + w.R.y));
        mech.w.push_back(w);
    }
    for (auto& I : mech.f) {
        double cl = 0.0, tl = 0.0;
        int first = -1;
        pieces(m, I.V, I.T, [&](Point2 p, double len) {
            const int k = materials_at(m, p.x, p.y).front();
            const auto& mm = s.materials[k];
            cl += mm.cohesion * len;
            tl += std::tan(mm.friction_deg * kPi / 180.0) * len;
            if (first < 0) first = k;
            else if (k != first) I.mixed = true;
        });
        I.c = cl / I.L;
        I.tf = tl / I.L;
        I.U = pore_force(m, I.V, I.T);
    }
    return mech;
}

/// Eliminación gaussiana con pivoteo parcial; vacío si la matriz es singular.
inline std::optional<std::vector<double>> solve_linear(std::vector<std::vector<double>> A, std::vector<double> b) {
    const std::size_t n = b.size();
    double scale = 0.0;
    for (const auto& row : A)
        for (double v : row) scale = std::max(scale, std::fabs(v));
    if (!(scale > 0.0)) return std::nullopt;
    for (std::size_t c = 0; c < n; ++c) {
        std::size_t p = c;
        for (std::size_t r = c + 1; r < n; ++r)
            if (std::fabs(A[r][c]) > std::fabs(A[p][c])) p = r;
        if (!(std::fabs(A[p][c]) > 1e-13 * scale)) return std::nullopt;
        std::swap(A[p], A[c]);
        std::swap(b[p], b[c]);
        for (std::size_t r = c + 1; r < n; ++r) {
            const double f = A[r][c] / A[c][c];
            for (std::size_t k = c; k < n; ++k) A[r][k] -= f * A[c][k];
            b[r] -= f * b[c];
        }
    }
    std::vector<double> x(n);
    for (std::size_t c = n; c-- > 0;) {
        double v = b[c];
        for (std::size_t k = c + 1; k < n; ++k) v -= A[c][k] * x[k];
        x[c] = v / A[c][c];
    }
    for (double v : x)
        if (!std::isfinite(v)) return std::nullopt;
    return x;
}

/// N'_0..N'_{n-1}, E'_0..E'_{n-2} y K con resistencias divididas por F = 1/phi.
inline std::optional<std::vector<double>> solve_at(Mechanism& me, const LeSection& s, double phi) {
    const std::size_t n = me.w.size(), N = 2 * n;
    for (auto& w : me.w) {
        w.mat = w.cand.front();
        w.c = s.materials[w.mat].cohesion;
        w.tf = std::tan(s.materials[w.mat].friction_deg * kPi / 180.0);
    }
    std::optional<std::vector<double>> x;
    for (int pass = 0; pass < 3; ++pass) {
        std::vector<std::vector<double>> A(N, std::vector<double>(N, 0.0));
        std::vector<double> b(N, 0.0);
        for (std::size_t i = 0; i < n; ++i) {
            const Wedge& w = me.w[i];
            const double kx = w.U * w.nrm.x - w.c * w.l * phi * w.t.x, ky = w.U * w.nrm.y - w.c * w.l * phi * w.t.y - w.W;
            A[2 * i][i] += w.nrm.x - w.tf * phi * w.t.x;
            A[2 * i + 1][i] += w.nrm.y - w.tf * phi * w.t.y;
            b[2 * i] -= kx;
            b[2 * i + 1] -= ky;
            A[2 * i][N - 1] += w.W;
        }
        for (std::size_t j = 0; j + 1 < n; ++j) {
            const Interface& I = me.f[j];
            for (auto [i, sign] : {std::pair<std::size_t, double>{j + 1, 1.0}, {j, -1.0}}) {
                A[2 * i][n + j] += sign * (I.nn.x + I.tf * phi * I.tau.x);
                A[2 * i + 1][n + j] += sign * (I.nn.y + I.tf * phi * I.tau.y);
                b[2 * i] -= sign * (I.U * I.nn.x + I.c * I.L * phi * I.tau.x);
                b[2 * i + 1] -= sign * (I.U * I.nn.y + I.c * I.L * phi * I.tau.y);
            }
        }
        x = solve_linear(A, b);
        if (!x) return x;
        bool same = true;
        for (std::size_t i = 0; i < n; ++i) {  // contacto: el candidato más débil por τ con el σn' de la solución
            auto& w = me.w[i];
            if (w.cand.size() < 2) continue;
            const double sn = std::max((*x)[i] / w.l, 0.0);
            int best = w.mat;
            double tau = w.c + sn * w.tf;
            for (int k : w.cand) {
                const auto& mm = s.materials[k];
                const double t = mm.cohesion + sn * std::tan(mm.friction_deg * kPi / 180.0);
                if (t < tau) {
                    tau = t;
                    best = k;
                }
            }
            if (best != w.mat) {
                same = false;
                w.mat = best;
                w.c = s.materials[best].cohesion;
                w.tf = std::tan(s.materials[best].friction_deg * kPi / 180.0);
            }
        }
        if (same) break;
    }
    return x;
}

struct Eval {
    Mechanism me;
    std::optional<double> F, Kc;
    std::optional<std::vector<double>> x;  // solución con F = FS
    bool backward = false, failed = false, static_fail = false;
};

inline Eval evaluate(const Model& m, const std::vector<double>& angles, const SarmaOptions& o) {
    Eval e;
    e.me = make_mechanism(m, angles);
    const double kh = m.s->kh;
    auto K = [&](double phi) -> std::optional<double> {
        const auto x = solve_at(e.me, *m.s, phi);
        if (!x) return std::nullopt;
        return x->back();
    };
    if (const auto k1 = K(1.0)) {
        e.Kc = std::max(*k1, 0.0);
        e.static_fail = *k1 <= 0.0;
    }
    const auto K0 = K(0.0);
    if (!K0) {
        e.failed = true;
        return e;
    }
    bool strength = false;
    for (const auto& w : e.me.w)
        for (int k : w.cand) strength = strength || m.s->materials[k].cohesion > 0.0 || m.s->materials[k].friction_deg > 0.0;
    for (const auto& I : e.me.f) strength = strength || I.c > 0.0 || I.tf > 0.0;
    if (*K0 >= kh) {
        e.backward = true;
        return e;
    }
    if (!strength) {
        e.F = 0.0;
        e.x = solve_at(e.me, *m.s, 0.0);
        return e;
    }
    double lo = 0.0, hi = 1.0;
    for (int k = 0;; ++k) {
        const auto v = K(hi);
        if (!v || k > 64) {
            e.failed = true;
            return e;
        }
        if (*v > kh) break;
        lo = hi;
        hi *= 2.0;
    }
    bool done = false;
    for (int it = 0; it < o.max_iterations && !done; ++it) {
        const double mid = 0.5 * (lo + hi);
        const auto v = K(mid);
        if (!v) {
            e.failed = true;
            return e;
        }
        (*v > kh ? hi : lo) = mid;
        done = lo > 0.0 && 1.0 / lo - 1.0 / hi < o.tolerance;
    }
    if (!done) {
        e.failed = true;
        return e;
    }
    e.F = 0.5 * (1.0 / lo + 1.0 / hi);
    e.x = solve_at(e.me, *m.s, 1.0 / *e.F);
    if (!e.x) {
        e.failed = true;
        e.F.reset();
    }
    return e;
}

inline MethodInfo info() {
    return {"Sarma-NonVertical", Verification::Secondary,
            "Sarma (1979) non-vertical slices as described in Hoek (1987), both not read; rigid wedges, force "
            "equilibrium, checked against Slide Sarma Verification problem 4 and against Hoek's planar block with one "
            "wedge"};
}
}  // namespace sarma_detail

inline SarmaResult sarma_fs(const LeSection& section, const SarmaInput& input, const SarmaOptions& options = {}) {
    using namespace sarma_detail;
    using namespace validation;
    require_positive(options.tolerance, "tolerance");
    require(options.tolerance <= 1e-3, "tolerance", "must be at most 1e-3", options.tolerance);
    require(options.max_iterations >= 1, "max_iterations", "must be at least 1", options.max_iterations);
    require_finite(options.angle_min_deg, "angle_min_deg");
    require_finite(options.angle_max_deg, "angle_max_deg");
    require(options.angle_min_deg > 0.0 && options.angle_min_deg < options.angle_max_deg, "angle_min_deg",
            "must be within (0, angle_max_deg)", options.angle_min_deg);
    require(options.angle_max_deg < 180.0, "angle_max_deg", "must be below 180", options.angle_max_deg);
    if (input.base.size() < 2) fail("base", "needs at least two points");
    const std::size_t ni = input.base.size() - 2;
    require(input.interface_angles_deg.size() == ni, "interface_angles_deg",
            "needs one angle per interior vertex of the base", static_cast<double>(input.interface_angles_deg.size()));
    for (std::size_t k = 0; k < ni; ++k) {
        const double a = input.interface_angles_deg[k];
        require_finite(a, at("interface_angles_deg", k));
        require(a > 0.0 && a < 180.0, at("interface_angles_deg", k), "must be within (0, 180)", a);
    }
    const Model m = make_model(section, input);
    // ángulos del marco interno, en su orden (reflejar invierte el orden de los vértices y θ -> 180 - θ)
    auto to_internal = [&](const std::vector<double>& u) {
        std::vector<double> a(u);
        if (m.reflected) {
            std::reverse(a.begin(), a.end());
            for (double& v : a) v = 180.0 - v;
        }
        return a;
    };
    std::vector<double> angles = to_internal(input.interface_angles_deg);
    SarmaResult out{std::nullopt, std::nullopt, {}, {}, info(), {}, {}};
    Eval e = evaluate(m, angles, options);
    if (options.optimize_angles && ni > 0 && e.F) {
        const double lo = m.reflected ? 180.0 - options.angle_max_deg : options.angle_min_deg;
        const double hi = m.reflected ? 180.0 - options.angle_min_deg : options.angle_max_deg;
        for (double& a : angles) a = std::clamp(a, lo, hi);
        e = evaluate(m, angles, options);
        // búsqueda de patrón: paso de 8 grados que se parte a la mitad hasta 1e-3
        int evals = 0;
        for (double step = 8.0; step >= 1e-3 && e.F && evals < 5000;) {
            bool improved = false;
            for (std::size_t j = 0; j < ni && !improved; ++j)
                for (double sign : {1.0, -1.0}) {
                    std::vector<double> trial = angles;
                    trial[j] += sign * step;
                    if (trial[j] < lo || trial[j] > hi) continue;
                    ++evals;
                    try {
                        Eval t = evaluate(m, trial, options);
                        if (t.F && *t.F < *e.F - 1e-12) {
                            angles = trial;
                            e = std::move(t);
                            improved = true;
                            break;
                        }
                    } catch (const std::invalid_argument&) {  // geometría o cinemática inválida: se descarta
                    }
                }
            if (!improved) step *= 0.5;
        }
        out.notes.push_back("interface angles optimized by pattern search for the minimum factor of safety");
    } else if (options.optimize_angles && ni > 0) {
        out.notes.push_back("interface angles not optimized: no factor of safety at the given angles");
    }
    // ángulos de vuelta al marco del usuario
    out.interface_angles_deg = angles;
    if (m.reflected) {
        std::reverse(out.interface_angles_deg.begin(), out.interface_angles_deg.end());
        for (double& v : out.interface_angles_deg) v = 180.0 - v;
    }
    if (e.backward) out.notes.push_back(le_detail::kBackward);
    if (e.failed) out.warnings.push_back("Sarma did not converge");
    out.factor_of_safety = e.F;
    out.critical_acceleration = e.Kc;
    if (!e.Kc) out.warnings.push_back("critical acceleration not found: the force system is singular at F = 1");
    else if (e.static_fail) out.warnings.push_back("static factor of safety at or below 1: critical acceleration taken as 0");
    const std::size_t n = e.me.w.size();
    if (e.x) {
        int neg = 0;
        for (std::size_t i = 0; i < 2 * n - 1; ++i) neg += (*e.x)[i] < 0.0;
        if (neg > 0)
            out.warnings.push_back("negative effective normal force in " + std::to_string(neg) + " bases or interfaces");
    }
    if (section.piezometric)
        for (const auto& mm : section.materials)
            if (mm.ru > 0.0) {
                out.notes.push_back("piezometric line given: the ru of the materials is ignored");
                break;
            }
    if (std::any_of(e.me.f.begin(), e.me.f.end(), [](const Interface& I) { return I.mixed; }))
        out.notes.push_back("interfaces crossing several materials: c and tan(phi) weighted by length along the interface");
    for (std::size_t i = 0; i < n; ++i) {
        const Wedge& w = e.me.w[i];
        SarmaWedge p{w.area, w.W, 0, 0, 0, 0, w.mat};
        const std::optional<std::size_t> right =
            m.reflected ? (i > 0 ? std::optional<std::size_t>(i - 1) : std::nullopt)
                        : (i + 1 < n ? std::optional<std::size_t>(i) : std::nullopt);
        if (e.x) {
            const auto& x = *e.x;
            p.base_normal = x[i];
            p.base_shear_strength = w.c * w.l + x[i] * w.tf;
            if (right) {
                const Interface& I = e.me.f[*right];
                const double E = x[n + *right];
                p.interface_normal_right = E;
                p.interface_shear_right = *e.F > 0.0 ? (I.c * I.L + E * I.tf) / *e.F : 0.0;
            }
        }
        out.wedges.push_back(p);
    }
    if (m.reflected) std::reverse(out.wedges.begin(), out.wedges.end());
    return out;
}

}  // namespace rockmasspy
