/**
 * @file bem2d.hpp
 * @brief Elementos de contorno 2D: método de desplazamiento discontinuo (DDM) de elemento constante, en deformación
 *        plana, medio infinito, elástico e isótropo, con campo in situ uniforme y excavaciones libres de tracciones.
 *
 * Fuentes (ecuaciones en docs/investigacion/FORMULAS_FASE8C.md §1 y §2): la solución de Crouch (1976) y Crouch y
 * Starfield (1983) según Yan (2004) ecs. 2-5 y Jo y Hurt (2013) ecs. 1-5, que concuerdan; organización del armado
 * según Martel (2003). El sistema orlado con la restricción de traslación (§1.5), el σtt del borde por Hooke (§1.8) y
 * el remedio cerca del borde (§1.9) son deducidos y comprobados con el prototipo: por eso Secondary.
 *
 * Convención: la API va en compresión positiva (MPa, m, grados); el núcleo trabaja en tracción positiva, como Crouch y
 * Starfield, y cambia el signo de todo esfuerzo en la frontera (§2). Los desplazamientos no cambian de signo y son
 * los inducidos por la excavación. alpha_deg es el ángulo de σ1 desde el eje x, en sentido antihorario. Los mensajes
 * de error nombran el parámetro y nunca repiten el valor recibido.
 */

#pragma once

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "rockmasspy/method_info.hpp"
#include "rockmasspy/validation.hpp"

namespace rockmasspy {

/// Polígono cerrado de una excavación. Se acepta en cualquier sentido y con el primer punto repetido al final.
/// elements_per_side_hint, si es mayor que cero, es el mínimo de elementos por lado.
struct BemContour {
    std::vector<std::pair<double, double>> vertices;
    int elements_per_side_hint = 0;
};

/// Elemento constante del nodo 1 al nodo 2 (recorrido antihorario); cos_b y sin_b dan la tangente.
struct BemElement {
    double x1, y1, x2, y2, xm, ym, length, cos_b, sin_b;
    int contour;
};

struct BemInput {
    std::vector<BemContour> contours;
    double sigma1_mpa = validation::unset, sigma3_mpa = validation::unset, alpha_deg = validation::unset;
    double sigma_z_mpa = validation::unset;  // sin dato: la de deformación plana del campo inicial, ν(σxx⁰ + σyy⁰)
    double e_mpa = validation::unset, nu = validation::unset, max_element_m = validation::unset;
};

struct BemSolution {
    std::vector<BemElement> elements;
    std::vector<double> dx, dy;  // DD en ejes locales del elemento (§1.1): dx tangencial (Ds), dy normal (Dn), en m
    double sxx0_mpa, syy0_mpa, sxy0_mpa, szz0_mpa;  // campo in situ, compresión positiva
    double e_mpa, nu;
    MethodInfo info;
};

/// Por elemento, en su punto medio: σtt del lado del material (compresión positiva) y desplazamiento inducido.
struct BemBoundary {
    std::vector<double> x, y, sigma_tt_mpa, ux_m, uy_m;
};

/// Esfuerzo en un punto, compresión positiva. sigma1 y sigma3 son los principales del plano; angle1_deg, el de σ1
/// desde el eje x. inside: dentro de una excavación (todo NaN). corrected: se aplicó el remedio de §1.9. coarse: el
/// punto está a menos de un elemento del borde pero el remedio no cabe (pilar más angosto que unos dos elementos):
/// se da el valor directo, finito pero con el error de §1.9; hay que afinar los elementos.
struct BemPointStress {
    double sxx, syy, sxy, szz, sigma1, sigma3, angle1_deg;
    bool inside;
    bool corrected;
    bool coarse;
};

inline MethodInfo bem_info() {
    return {"BEM-DDM-Crouch-Starfield-1983", Verification::Secondary,
            "Crouch and Starfield (1983) constant displacement discontinuity as reproduced in Yan (2004) eq. 2-5 and Jo "
            "and Hurt (2013) eq. 1-5; bordered system, boundary Hooke and near-boundary remedy deduced (FORMULAS_FASE8C "
            "§1.5, §1.8, §1.9)"};
}

namespace bem2d_detail {
constexpr double kPi = 3.14159265358979323846;
constexpr std::size_t kMaxElements = 2048;  // 4100 incógnitas: unos 130 MB de matriz densa

[[noreturn]] inline void fail(const std::string& name, const std::string& what) {
    throw std::invalid_argument("Domain error [RockMassPy]: parameter '" + name + "' " + what);
}
/// Como validation::require_positive, pero sin repetir el valor.
/// validation::require_finite repite el valor en el mensaje; aquí solo se nombra el parámetro.
inline void finite(double v, const std::string& name) {
    if (!std::isfinite(v)) fail(name, "must be a finite number (got NaN or infinity)");
}
inline void positive(double v, const std::string& name) {
    finite(v, name);
    if (!(v > 0.0)) fail(name, "must be strictly positive (> 0)");
}
inline void poisson(double v, const std::string& name) {
    finite(v, name);
    if (v < 0.0 || v >= 0.5) fail(name, "must be within [0, 0.5)");
}

using Pt = std::pair<double, double>;

inline double cross(const Pt& o, const Pt& a, const Pt& b) {
    return (a.first - o.first) * (b.second - o.second) - (a.second - o.second) * (b.first - o.first);
}
inline bool on_box(const Pt& p, const Pt& a, const Pt& b) {
    return std::min(a.first, b.first) <= p.first && p.first <= std::max(a.first, b.first) &&
           std::min(a.second, b.second) <= p.second && p.second <= std::max(a.second, b.second);
}
/// Los segmentos ab y cd se cortan o se tocan (también si son colineales y se solapan).
inline bool segments_meet(const Pt& a, const Pt& b, const Pt& c, const Pt& d) {
    const double d1 = cross(c, d, a), d2 = cross(c, d, b), d3 = cross(a, b, c), d4 = cross(a, b, d);
    if (((d1 > 0 && d2 < 0) || (d1 < 0 && d2 > 0)) && ((d3 > 0 && d4 < 0) || (d3 < 0 && d4 > 0))) return true;
    return (d1 == 0 && on_box(a, c, d)) || (d2 == 0 && on_box(b, c, d)) || (d3 == 0 && on_box(c, a, b)) ||
           (d4 == 0 && on_box(d, a, b));
}
/// Número de cruces de un rayo horizontal (punto en polígono; los puntos sobre el borde se tratan antes).
inline bool inside_polygon(double x, double y, const std::vector<Pt>& p) {
    bool in = false;
    for (std::size_t i = 0, j = p.size() - 1; i < p.size(); j = i++) {
        const auto& [xi, yi] = p[i];
        const auto& [xj, yj] = p[j];
        if ((yi > y) != (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) in = !in;
    }
    return in;
}

/// Primer elemento de cada contorno y, al final, el total (los elementos de un contorno son contiguos).
inline std::vector<std::size_t> offsets(const std::vector<BemElement>& els) {
    std::vector<std::size_t> off{0};
    for (std::size_t i = 1; i < els.size(); ++i)
        if (els[i].contour != els[i - 1].contour) off.push_back(i);
    off.push_back(els.size());
    return off;
}
/// Vecino siguiente (+1) o anterior (−1) del elemento i dentro de su contorno cerrado.
inline std::size_t neighbour(const std::vector<std::size_t>& off, const BemElement& e, std::size_t i, int step) {
    const std::size_t a = off[e.contour], n = off[e.contour + 1] - a;
    return a + (i - a + n + step) % n;
}

/// Esfuerzos y desplazamientos globales en un punto por un DD unitario.
struct Unit {
    double sxx, syy, sxy, ux, uy;
};

/// Influencia del elemento e en (x, y) por Ds = 1 (s) y por Dn = 1 (n), en tracción positiva (§1.2-1.4).
inline void influence(const BemElement& e, double x, double y, double nu, double g, Unit& s, Unit& n) {
    const double cb = e.cos_b, sb = e.sin_b, a = e.length / 2;
    const double xb = (x - e.xm) * cb + (y - e.ym) * sb;
    double yb = -(x - e.xm) * sb + (y - e.ym) * cb;
    // un punto sobre el propio elemento se toma en el lado del material, ȳ = 0− (§1.6); solo cambia u por f,y
    if (std::abs(yb) <= 1e-12 * a && std::abs(xb) < a) yb = -0.0;
    const double c = 1.0 / (4.0 * kPi * (1.0 - nu));
    const double xm = xb - a, xp = xb + a, y2 = yb * yb;
    const double r1 = xm * xm + y2, r2 = xp * xp + y2;
    // f y sus derivadas (§1.3); atan2 da el salto de f,y al cruzar el elemento
    const double fx = c * 0.5 * std::log(r1 / r2);
    const double fy = -c * (std::atan2(yb, xm) - std::atan2(yb, xp));
    const double fxy = c * (yb / r1 - yb / r2);
    const double fxx = c * (xm / r1 - xp / r2), fyy = -fxx;
    const double fxyy = c * ((xm * xm - y2) / (r1 * r1) - (xp * xp - y2) / (r2 * r2));
    const double fyyy = 2.0 * yb * c * (xm / (r1 * r1) - xp / (r2 * r2));
    const Unit ls{2 * g * (2 * fxy + yb * fxyy), 2 * g * (-yb * fxyy), 2 * g * (fyy + yb * fyyy),
                  2 * (1 - nu) * fy - yb * fxx, (1 - 2 * nu) * fx - yb * fxy};
    const Unit ln{2 * g * (fyy + yb * fyyy), 2 * g * (fyy - yb * fyyy), 2 * g * (-yb * fxyy),
                  -(1 - 2 * nu) * fx - yb * fxy, 2 * (1 - nu) * fy - yb * fyy};
    auto rot = [cb, sb](const Unit& l) {
        return Unit{l.sxx * cb * cb - 2 * l.sxy * sb * cb + l.syy * sb * sb,
                    l.sxx * sb * sb + 2 * l.sxy * sb * cb + l.syy * cb * cb,
                    (l.sxx - l.syy) * sb * cb + l.sxy * (cb * cb - sb * sb), l.ux * cb - l.uy * sb,
                    l.ux * sb + l.uy * cb};
    };
    s = rot(ls);
    n = rot(ln);
}

/// Tracción tangencial y normal sobre el elemento e (normal izquierda n = (−sin β, cos β)).
inline std::pair<double, double> traction(const BemElement& e, double sxx, double syy, double sxy) {
    const double tx = -sxx * e.sin_b + sxy * e.cos_b, ty = -sxy * e.sin_b + syy * e.cos_b;
    return {tx * e.cos_b + ty * e.sin_b, -tx * e.sin_b + ty * e.cos_b};
}

/// Eliminación de Gauss con pivoteo parcial sobre la matriz densa m (n × n, por filas): es la LU aplicada sobre la
/// marcha a un único lado derecho. Devuelve la solución en b.
inline void lu_solve(std::vector<double>& m, std::vector<double>& b, std::size_t n) {
    double amax = 0.0;
    for (double v : m) amax = std::max(amax, std::abs(v));
    for (std::size_t k = 0; k < n; ++k) {
        std::size_t p = k;
        for (std::size_t r = k + 1; r < n; ++r)
            if (std::abs(m[r * n + k]) > std::abs(m[p * n + k])) p = r;
        if (!(std::abs(m[p * n + k]) > 1e-13 * amax))
            throw std::runtime_error("Numerical error [RockMassPy]: the boundary element system is singular");
        if (p != k) {
            std::swap_ranges(m.begin() + k * n, m.begin() + (k + 1) * n, m.begin() + p * n);
            std::swap(b[k], b[p]);
        }
        const double* rk = &m[k * n];
        for (std::size_t r = k + 1; r < n; ++r) {
            double* rr = &m[r * n];
            const double l = rr[k] / rk[k];
            if (l == 0.0) continue;
            for (std::size_t j = k + 1; j < n; ++j) rr[j] -= l * rk[j];
            b[r] -= l * b[k];
        }
    }
    for (std::size_t k = n; k-- > 0;) {
        double s = b[k];
        for (std::size_t j = k + 1; j < n; ++j) s -= m[k * n + j] * b[j];
        b[k] = s / m[k * n + k];
    }
}

/// Distancia del punto al elemento y coordenada local t ∈ [−a, a] del pie.
inline std::pair<double, double> distance(const BemElement& e, double x, double y) {
    const double a = e.length / 2;
    const double t = std::clamp((x - e.xm) * e.cos_b + (y - e.ym) * e.sin_b, -a, a);
    return {std::hypot(x - (e.xm + t * e.cos_b), y - (e.ym + t * e.sin_b)), t};
}
}  // namespace bem2d_detail

/// Normaliza los contornos (sin punto de cierre, antihorarios, sin cruces) y divide cada lado en elementos de largo
/// ≤ max_element_m (§1.6, C3).
inline std::vector<BemElement> bem_discretize(const std::vector<BemContour>& contours, double max_element_m) {
    using namespace bem2d_detail;
    if (contours.empty()) fail("contours", "must contain at least one contour");
    positive(max_element_m, "max_element_m");
    std::vector<std::vector<Pt>> polys;
    std::vector<double> area2s, scales;
    for (const auto& c : contours) {
        std::vector<Pt> p = c.vertices;
        for (const auto& [x, y] : p) {
            finite(x, "vertices");
            finite(y, "vertices");
        }
        if (c.elements_per_side_hint < 0) fail("elements_per_side_hint", "must not be negative");
        if (p.size() < 3) fail("vertices", "must have at least 3 distinct points");
        double scale = 0.0;
        for (const auto& q : p)
            scale = std::max({scale, std::abs(q.first - p[0].first), std::abs(q.second - p[0].second)});
        const double tol = 1e-12 * scale;
        if (std::hypot(p.back().first - p[0].first, p.back().second - p[0].second) <= tol) p.pop_back();
        if (p.size() < 3) fail("vertices", "must have at least 3 distinct points");
        double area2 = 0.0;
        for (std::size_t i = 0; i < p.size(); ++i) {
            const Pt& q = p[(i + 1) % p.size()];
            if (std::hypot(q.first - p[i].first, q.second - p[i].second) <= tol)
                fail("vertices", "must not repeat consecutive points");
            area2 += p[i].first * q.second - q.first * p[i].second;
        }
        polys.push_back(std::move(p));
        area2s.push_back(area2);
        scales.push_back(scale);
    }
    // cruces propios y entre contornos; los lados vecinos de un mismo polígono comparten su vértice
    for (std::size_t a = 0; a < polys.size(); ++a)
        for (std::size_t b = a; b < polys.size(); ++b) {
            const auto &pa = polys[a], &pb = polys[b];
            for (std::size_t i = 0; i < pa.size(); ++i)
                for (std::size_t j = (a == b ? i + 1 : 0); j < pb.size(); ++j) {
                    if (a == b && (j == i + 1 || (i == 0 && j == pa.size() - 1))) continue;
                    if (segments_meet(pa[i], pa[(i + 1) % pa.size()], pb[j], pb[(j + 1) % pb.size()]))
                        fail("contours", "must not cross or touch themselves or each other");
                }
            if (a != b && (inside_polygon(pb[0].first, pb[0].second, pa) || inside_polygon(pa[0].first, pa[0].second, pb)))
                fail("contours", "must not lie inside one another");
        }
    // después de los cruces: un polígono que se cruza puede tener área neta nula
    for (std::size_t c = 0; c < polys.size(); ++c) {
        if (std::abs(area2s[c]) <= 1e-12 * scales[c] * scales[c]) fail("vertices", "must enclose a nonzero area");
        if (area2s[c] < 0.0) std::reverse(polys[c].begin(), polys[c].end());  // a antihorario: material en ȳ < 0
    }
    auto pieces = [&](const Pt& p, const Pt& q, int hint) {
        const double len = std::hypot(q.first - p.first, q.second - p.second);
        return std::max<double>({1.0, double(hint), std::ceil(len / max_element_m - 1e-9)});
    };
    double total = 0.0;  // se cuenta antes de reservar: un max_element_m diminuto agotaría la memoria
    for (std::size_t c = 0; c < polys.size(); ++c)
        for (std::size_t i = 0; i < polys[c].size(); ++i)
            total += pieces(polys[c][i], polys[c][(i + 1) % polys[c].size()], contours[c].elements_per_side_hint);
    if (total > double(kMaxElements))
        throw std::invalid_argument(
            "Domain error [RockMassPy]: parameters 'max_element_m' and 'elements_per_side_hint' give more than 2048 "
            "elements; use a larger 'max_element_m' or a smaller 'elements_per_side_hint'");
    std::vector<BemElement> els;
    for (std::size_t c = 0; c < polys.size(); ++c) {
        const auto& p = polys[c];
        for (std::size_t i = 0; i < p.size(); ++i) {
            const Pt &u = p[i], &v = p[(i + 1) % p.size()];
            const int m = static_cast<int>(pieces(u, v, contours[c].elements_per_side_hint));
            const double len = std::hypot(v.first - u.first, v.second - u.second) / m;
            const double cb = (v.first - u.first) / (len * m), sb = (v.second - u.second) / (len * m);
            for (int k = 0; k < m; ++k) {
                const double x1 = u.first + (v.first - u.first) * k / m, y1 = u.second + (v.second - u.second) * k / m;
                const double x2 = k + 1 == m ? v.first : u.first + (v.first - u.first) * (k + 1) / m;
                const double y2 = k + 1 == m ? v.second : u.second + (v.second - u.second) * (k + 1) / m;
                els.push_back({x1, y1, x2, y2, (x1 + x2) / 2, (y1 + y2) / 2, std::hypot(x2 - x1, y2 - y1), cb, sb,
                               static_cast<int>(c)});
            }
        }
    }
    return els;
}

/// Arma y resuelve el sistema orlado: tracción inducida = −tracción in situ en cada punto medio (§1.5) y, por
/// contorno, ΣL·Dx = 0 y ΣL·Dy = 0 en ejes globales, que quitan la traslación rígida del interior (núcleo exacto).
inline BemSolution bem_solve(const BemInput& in) {
    using namespace bem2d_detail;
    finite(in.sigma1_mpa, "sigma1_mpa");
    finite(in.sigma3_mpa, "sigma3_mpa");
    if (in.sigma3_mpa > in.sigma1_mpa) fail("sigma3_mpa", "must not exceed 'sigma1_mpa'");
    finite(in.alpha_deg, "alpha_deg");
    if (!std::isnan(in.sigma_z_mpa)) finite(in.sigma_z_mpa, "sigma_z_mpa");
    positive(in.e_mpa, "e_mpa");
    poisson(in.nu, "nu");
    BemSolution sol;
    sol.elements = bem_discretize(in.contours, in.max_element_m);
    sol.e_mpa = in.e_mpa;
    sol.nu = in.nu;
    sol.info = bem_info();
    // campo in situ desde σ1, σ3 y α (§1.7), compresión positiva
    const double mean = (in.sigma1_mpa + in.sigma3_mpa) / 2, half = (in.sigma1_mpa - in.sigma3_mpa) / 2;
    const double a2 = 2 * in.alpha_deg * kPi / 180;
    sol.sxx0_mpa = mean + half * std::cos(a2);
    sol.syy0_mpa = mean - half * std::cos(a2);
    sol.sxy0_mpa = half * std::sin(a2);
    sol.szz0_mpa = std::isnan(in.sigma_z_mpa) ? in.nu * (sol.sxx0_mpa + sol.syy0_mpa) : in.sigma_z_mpa;

    const auto& els = sol.elements;
    const std::size_t n = els.size(), nc = offsets(els).size() - 1, dim = 2 * n + 2 * nc;
    const double g = in.e_mpa / (2 * (1 + in.nu));
    std::vector<double> m(dim * dim, 0.0), b(dim, 0.0);
    double amax = 0.0;
    for (std::size_t i = 0; i < n; ++i) {
        for (std::size_t j = 0; j < n; ++j) {
            Unit us, un;
            influence(els[j], els[i].xm, els[i].ym, in.nu, g, us, un);
            const auto [ss, ns] = traction(els[i], us.sxx, us.syy, us.sxy);
            const auto [sn, nn] = traction(els[i], un.sxx, un.syy, un.sxy);
            m[i * dim + j] = ss;
            m[i * dim + n + j] = sn;
            m[(n + i) * dim + j] = ns;
            m[(n + i) * dim + n + j] = nn;
            amax = std::max({amax, std::abs(ss), std::abs(sn), std::abs(ns), std::abs(nn)});
        }
        // lado derecho: −t⁰ con el in situ en tracción positiva (σ⁰_núcleo = −σ⁰_API)
        const auto [t0s, t0n] = traction(els[i], -sol.sxx0_mpa, -sol.syy0_mpa, -sol.sxy0_mpa);
        b[i] = -t0s;
        b[n + i] = -t0n;
    }
    // restricciones [[A, Cᵀ], [C, 0]], escaladas a la magnitud de A para el pivoteo
    double lmax = 0.0;
    for (const auto& e : els) lmax = std::max(lmax, e.length);
    const double k = amax / lmax;
    for (std::size_t j = 0; j < n; ++j) {
        const auto& e = els[j];
        const std::size_t rx = 2 * n + 2 * e.contour, ry = rx + 1;
        const double cx_s = k * e.length * e.cos_b, cx_n = -k * e.length * e.sin_b;  // Dx = Ds cos β − Dn sin β
        const double cy_s = k * e.length * e.sin_b, cy_n = k * e.length * e.cos_b;   // Dy = Ds sin β + Dn cos β
        m[rx * dim + j] = cx_s;
        m[rx * dim + n + j] = cx_n;
        m[ry * dim + j] = cy_s;
        m[ry * dim + n + j] = cy_n;
        m[j * dim + rx] = cx_s;
        m[(n + j) * dim + rx] = cx_n;
        m[j * dim + ry] = cy_s;
        m[(n + j) * dim + ry] = cy_n;
    }
    lu_solve(m, b, dim);
    sol.dx.assign(b.begin(), b.begin() + n);
    sol.dy.assign(b.begin() + n, b.begin() + 2 * n);
    return sol;
}

/// σtt del borde por Hooke de deformación plana con la deformación tangencial del lado del material (§1.8; nunca el
/// valor en el punto medio, que promedia el material y el interior) y desplazamiento inducido del lado del material.
inline BemBoundary bem_boundary(const BemSolution& sol) {
    using namespace bem2d_detail;
    const auto& els = sol.elements;
    const std::size_t n = els.size();
    const double nu = sol.nu, g = sol.e_mpa / (2 * (1 + nu));
    BemBoundary out;
    out.ux_m.assign(n, 0.0);
    out.uy_m.assign(n, 0.0);
    for (std::size_t i = 0; i < n; ++i) {
        out.x.push_back(els[i].xm);
        out.y.push_back(els[i].ym);
        for (std::size_t j = 0; j < n; ++j) {
            Unit us, un;
            influence(els[j], els[i].xm, els[i].ym, nu, g, us, un);
            out.ux_m[i] += us.ux * sol.dx[j] + un.ux * sol.dy[j];
            out.uy_m[i] += us.uy * sol.dx[j] + un.uy * sol.dy[j];
        }
    }
    const auto off = offsets(els);
    for (std::size_t i = 0; i < n; ++i) {
        const auto& e = els[i];
        const std::size_t ip = neighbour(off, e, i, 1), im = neighbour(off, e, i, -1);
        const double ett = ((out.ux_m[ip] - out.ux_m[im]) * e.cos_b + (out.uy_m[ip] - out.uy_m[im]) * e.sin_b) /
                           std::hypot(els[ip].xm - els[im].xm, els[ip].ym - els[im].ym);
        // in situ en tracción positiva, en ejes del elemento
        const double cb = e.cos_b, sb = e.sin_b;
        const double s0tt = -(sol.sxx0_mpa * cb * cb + sol.syy0_mpa * sb * sb + 2 * sol.sxy0_mpa * sb * cb);
        const double s0nn = -(sol.sxx0_mpa * sb * sb + sol.syy0_mpa * cb * cb - 2 * sol.sxy0_mpa * sb * cb);
        const double stt = s0tt + 2 * g / (1 - nu) * ett - nu / (1 - nu) * s0nn;
        out.sigma_tt_mpa.push_back(-stt);  // a compresión positiva
    }
    return out;
}

/// Esfuerzos en puntos (compresión positiva). Dentro de una excavación: NaN e inside. A menos de un largo de
/// elemento del borde, remedio de §1.9 con c = 1: se interpola entre el tensor del borde (σnn = σnt = 0, σtt por
/// Hooke) y el punto Q a un largo de elemento hacia el material. σzz de deformación plana (C5).
inline std::vector<BemPointStress> bem_field(const BemSolution& sol, const std::vector<std::pair<double, double>>& pts) {
    using namespace bem2d_detail;
    const auto& els = sol.elements;
    const std::size_t n = els.size();
    const double nu = sol.nu, g = sol.e_mpa / (2 * (1 + nu));
    const auto off = offsets(els);
    std::vector<std::vector<Pt>> polys(off.size() - 1);
    for (const auto& e : els) polys[e.contour].push_back({e.x1, e.y1});
    std::vector<double> stt_b;  // solo si algún punto cae cerca del borde
    // tensor total en (x, y), compresión positiva
    auto direct = [&](double x, double y, double& sxx, double& syy, double& sxy) {
        double tx = 0, ty = 0, txy = 0;
        for (std::size_t j = 0; j < n; ++j) {
            Unit us, un;
            influence(els[j], x, y, nu, g, us, un);
            tx += us.sxx * sol.dx[j] + un.sxx * sol.dy[j];
            ty += us.syy * sol.dx[j] + un.syy * sol.dy[j];
            txy += us.sxy * sol.dx[j] + un.sxy * sol.dy[j];
        }
        sxx = sol.sxx0_mpa - tx;
        syy = sol.syy0_mpa - ty;
        sxy = sol.sxy0_mpa - txy;
    };
    std::vector<BemPointStress> out;
    out.reserve(pts.size());
    const double nan = std::numeric_limits<double>::quiet_NaN();
    // elemento más cercano: distancia, coordenada local del pie y su índice
    auto nearest = [&](double x, double y, double& d, double& t, std::size_t& i) {
        d = std::numeric_limits<double>::infinity();
        for (std::size_t j = 0; j < n; ++j) {
            const auto [dj, tj] = distance(els[j], x, y);
            if (dj < d) {
                d = dj;
                t = tj;
                i = j;
            }
        }
    };
    auto inside_any = [&](double x, double y) {
        for (const auto& p : polys)
            if (inside_polygon(x, y, p)) return true;
        return false;
    };
    for (const auto& [x, y] : pts) {
        finite(x, "points");
        finite(y, "points");
        std::size_t i = 0;
        double d = 0.0, t = 0.0;
        nearest(x, y, d, t, i);
        const double len = els[i].length;
        const bool on_boundary = d <= 1e-12 * len;  // la influencia es singular ahí: nunca se evalúa directo
        if (!on_boundary && inside_any(x, y)) {
            out.push_back({nan, nan, nan, nan, nan, nan, nan, true, false, false});
            continue;
        }
        BemPointStress r{};
        if (d >= len) {
            direct(x, y, r.sxx, r.syy, r.sxy);
        } else {
            if (stt_b.empty()) stt_b = bem_boundary(sol).sigma_tt_mpa;
            const auto& e = els[i];
            const std::size_t jn = neighbour(off, e, i, t >= 0 ? 1 : -1);
            const double w = std::abs(t) / ((len + els[jn].length) / 2);  // a lo largo del contorno, entre centros
            const double st = (1 - w) * stt_b[i] + w * stt_b[jn];
            const double bxx = st * e.cos_b * e.cos_b, byy = st * e.sin_b * e.sin_b, bxy = st * e.sin_b * e.cos_b;
            // Q = F + L·n_material; con recorrido antihorario el material queda a la derecha: (sin β, −cos β)
            const double qx = e.xm + t * e.cos_b + len * e.sin_b, qy = e.ym + t * e.sin_b - len * e.cos_b;
            double dq = 0.0, tq = 0.0;
            std::size_t iq = 0;
            if (!on_boundary) nearest(qx, qy, dq, tq, iq);
            // Q debe quedar en el material y a un elemento de todo borde; si no (pilar angosto, rincón entrante), el
            // remedio usaría un σ(Q) sin sentido o singular: se da el valor directo y se marca coarse
            if (!on_boundary && (dq < len * (1 - 1e-9) || inside_any(qx, qy))) {
                r.coarse = true;
                direct(x, y, r.sxx, r.syy, r.sxy);
            } else {
                r.corrected = true;
                double qxx = 0.0, qyy = 0.0, qxy = 0.0;
                if (!on_boundary) direct(qx, qy, qxx, qyy, qxy);  // sobre el borde pesa cero
                const double s = d / len;
                r.sxx = bxx + s * (qxx - bxx);
                r.syy = byy + s * (qyy - byy);
                r.sxy = bxy + s * (qxy - bxy);
            }
        }
        r.szz = sol.szz0_mpa + nu * ((r.sxx - sol.sxx0_mpa) + (r.syy - sol.syy0_mpa));
        const double c = (r.sxx + r.syy) / 2, rad = std::hypot((r.sxx - r.syy) / 2, r.sxy);
        r.sigma1 = c + rad;
        r.sigma3 = c - rad;
        r.angle1_deg = 0.5 * std::atan2(2 * r.sxy, r.sxx - r.syy) * 180 / kPi;
        out.push_back(r);
    }
    return out;
}

// ---- Strength factor (FORMULAS_FASE8C §3), compresión positiva ----

enum class SfCriterion { MohrCoulomb, HoekBrown };
/// RS2: la definición de Rocscience con los invariantes del tensor 3D (§3.2). Examine2D: la definición 2D de §3.3.
enum class SfMode { RS2, Examine2D };

/// Mohr-Coulomb usa c_mpa, phi_deg y tensile_mpa (T ≥ 0); Hoek-Brown usa sigma_ci_mpa, mb, s y a (T = s·σci/mb).
struct SfMaterial {
    SfCriterion criterion = SfCriterion::MohrCoulomb;
    double c_mpa = validation::unset, phi_deg = validation::unset, tensile_mpa = 0.0;
    double sigma_ci_mpa = validation::unset, mb = validation::unset, s = validation::unset, a = 0.5;
};

/// sf vacío si el punto está en tracción (σ3 < −T) o dentro de una excavación. Sin desviador, sf = +inf.
struct SfResult {
    std::optional<double> sf;
    bool tension = false;
};

inline MethodInfo strength_factor_info(SfMode mode) {
    if (mode == SfMode::RS2)
        return {"SF-RS2-3D", Verification::PrimaryLaterAuthors,
                "Rocscience Phase2 (RS2) theory, Strength Factor: Mohr-Coulomb p. 1 and Hoek-Brown a = 0.5 p. 3, from "
                "the stress invariants I1, J2 and the Lode angle; generalized Hoek-Brown by scaling the deviator at "
                "fixed I1 and Lode angle (FORMULAS_FASE8C §3.2, §3.4)"};
    return {"SF-2D-Examine2D", Verification::Secondary,
            "2D strength factor as described for Examine2D in Eberhardt, EOSC 433 Lab (UBC): shear strength over induced "
            "maximum shear at the same mean stress (sigma1 + sigma3)/2 (FORMULAS_FASE8C §3.3)"};
}

namespace bem2d_detail {
inline void check_material(const SfMaterial& m) {
    if (m.criterion == SfCriterion::MohrCoulomb) {
        finite(m.c_mpa, "c_mpa");
        if (m.c_mpa < 0.0) fail("c_mpa", "must not be negative");
        finite(m.phi_deg, "phi_deg");
        if (m.phi_deg < 0.0 || m.phi_deg >= 90.0) fail("phi_deg", "must be within [0, 90)");
        finite(m.tensile_mpa, "tensile_mpa");
        if (m.tensile_mpa < 0.0) fail("tensile_mpa", "must not be negative");
    } else {
        positive(m.sigma_ci_mpa, "sigma_ci_mpa");
        positive(m.mb, "mb");
        finite(m.s, "s");
        if (m.s < 0.0 || m.s > 1.0) fail("s", "must be within [0, 1]");
        positive(m.a, "a");
        if (m.a > 1.0) fail("a", "must be within (0, 1]");
    }
}

/// Resistencia a tracción T ≥ 0 (§3.4): la del usuario en Mohr-Coulomb; s·σci/mb en Hoek-Brown (HB02 ec. 7).
inline double tensile_cutoff(const SfMaterial& m) {
    return m.criterion == SfCriterion::MohrCoulomb ? m.tensile_mpa : m.s * m.sigma_ci_mpa / m.mb;
}

/// Raíz de g creciente en [lo, hi] con g(lo) < 0 < g(hi), por bisección hasta la precisión de máquina.
template <class G>
double bisect(G g, double lo, double hi) {
    for (int it = 0; it < 200 && hi - lo > 1e-15 * std::abs(hi); ++it) {
        const double mid = (lo + hi) / 2;
        (g(mid) < 0.0 ? lo : hi) = mid;
    }
    return (lo + hi) / 2;
}

/// SF de RS2 para Hoek-Brown generalizado (§3.4): factor k que escala la parte desviadora a I1 y Θ fijos hasta que
/// los principales escalados tocan σ1 = σ3 + σci(mb·σ3/σci + s)^a. Exige que ningún principal esté en tracción.
inline double hb_scaled_sf(const SfMaterial& m, double s1, double s3, double s2) {
    const double p = (s1 + s2 + s3) / 3;
    const double dmax = std::max({s1, s2, s3}) - p, dmin = std::min({s1, s2, s3}) - p;
    if (!(dmax > dmin)) return std::numeric_limits<double>::infinity();
    // con k = kt el principal menor llega a −T: más allá la potencia no existe y ya hay falla
    const double kt = (p + tensile_cutoff(m)) / -dmin;
    return bisect(
        [&](double k) {
            return k * (dmax - dmin) - m.sigma_ci_mpa * std::pow(std::max(0.0, m.mb * (p + k * dmin) / m.sigma_ci_mpa + m.s), m.a);
        },
        0.0, kt);
}
}  // namespace bem2d_detail

/// Strength factor en un punto (compresión positiva; σ2 es σz en deformación plana). RS2 arma el tensor diagonal
/// (σ1, σ3, σ2): los invariantes no dependen de los ejes, así que basta con los principales. La tracción se mira con
/// el menor de los tres principales en RS2 y con σ3 del plano en Examine2D, que no usa σz.
inline SfResult strength_factor(const SfMaterial& m, double sigma1, double sigma3, double sigma2, SfMode mode) {
    using namespace bem2d_detail;
    check_material(m);
    finite(sigma1, "sigma1");
    finite(sigma3, "sigma3");
    finite(sigma2, "sigma2");
    const double t = tensile_cutoff(m);
    const double hi = std::max(sigma1, sigma3), lo = std::min(sigma1, sigma3);
    if ((mode == SfMode::RS2 ? std::min(lo, sigma2) : lo) < -t) return {std::nullopt, true};
    const double inf = std::numeric_limits<double>::infinity();
    const bool mc = m.criterion == SfCriterion::MohrCoulomb;
    const double phi = mc ? m.phi_deg * kPi / 180 : 0.0;
    if (mode == SfMode::Examine2D) {
        const double sm = (hi + lo) / 2, tau = (hi - lo) / 2;
        if (!(tau > 0.0)) return {inf, false};
        // con T > c·cot φ el círculo puede salir del vértice de Mohr-Coulomb: SF 0, no negativo
        if (mc) return {std::max(0.0, (m.c_mpa * std::cos(phi) + sm * std::sin(phi)) / tau), false};
        const double tf = bisect(
            [&](double x) {
                return 2 * x - m.sigma_ci_mpa * std::pow(std::max(0.0, m.mb * (sm - x) / m.sigma_ci_mpa + m.s), m.a);
            },
            0.0, sm + t);
        return {tf / tau, false};
    }
    if (!mc && m.a != 0.5) return {hb_scaled_sf(m, hi, lo, sigma2), false};
    // invariantes de §3.2 con el tensor diagonal
    const double i1 = hi + lo + sigma2, q = i1 / 3;
    const double j2 = ((hi - lo) * (hi - lo) + (lo - sigma2) * (lo - sigma2) + (sigma2 - hi) * (sigma2 - hi)) / 6;
    if (!(j2 > 0.0)) return {inf, false};
    // Θ = (1/3)·asin(−3√3·J3 / (2·J2^1.5)) es, con los principales ordenados, tan Θ = (2σmed − σmax − σmin)/(√3(σmax −
    // σmin)): identidad exacta. El asin pierde √ε (~1e-8) cerca de Θ = ±π/6, es decir con σ2 igual a σ1 o a σ3
    const double smax3 = std::max(hi, sigma2), smin3 = std::min(lo, sigma2), smid = i1 - smax3 - smin3;
    const double th = std::atan((2 * smid - smax3 - smin3) / (std::sqrt(3.0) * (smax3 - smin3)));
    double smax;
    if (mc) {
        smax = (q * std::sin(phi) + m.c_mpa * std::cos(phi)) / (std::cos(th) + std::sin(th) * std::sin(phi) / std::sqrt(3.0));
    } else {
        const double k = (1 + std::tan(th) / std::sqrt(3.0)) * m.mb * m.sigma_ci_mpa / 8;
        // el radicando es ≥ 0 porque ningún principal está bajo −T (§3.4)
        smax = (std::sqrt(k * k + m.mb * m.sigma_ci_mpa * i1 / 12 + m.s * m.sigma_ci_mpa * m.sigma_ci_mpa / 4) - k) /
               std::cos(th);
    }
    return {std::max(0.0, smax / std::sqrt(j2)), false};
}

/// Strength factor de cada punto del campo con σ1, σ3 y σz (σ2). Los puntos dentro de una excavación dan sf vacío y
/// tension false; los coarse se calculan igual (su aviso es del análisis).
inline std::vector<SfResult> bem_strength_factor(const std::vector<BemPointStress>& pts, const SfMaterial& m,
                                                 SfMode mode) {
    bem2d_detail::check_material(m);
    std::vector<SfResult> out;
    out.reserve(pts.size());
    for (const auto& p : pts)
        out.push_back(p.inside ? SfResult{} : strength_factor(m, p.sigma1, p.sigma3, p.szz, mode));
    return out;
}

}  // namespace rockmasspy
