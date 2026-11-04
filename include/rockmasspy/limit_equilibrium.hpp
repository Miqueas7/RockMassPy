/**
 * @file limit_equilibrium.hpp
 * @brief Equilibrio límite 2D por tajadas verticales sobre una superficie dada (círculo o polilínea): Ordinario,
 *        Bishop simplificado, Janbu simplificado, Spencer y Morgenstern-Price/GLE.
 *
 * Fuentes (todas Secondary): Slide2 Verification Manual (2022), problemas 1 y 21 (Fredlund y Krahn 1977, ACADS);
 * Morgenstern-Price y Spencer con el algoritmo de Zhu, Lee, Qian y Chen (2005), no leído.
 * Convenciones: x horizontal, y hacia arriba, unidades coherentes. La cara puede mirar a cualquier lado: el núcleo
 * detecta el sentido y refleja (x -> -x) por dentro, así que una sección reflejada da el mismo FS y el mismo λ.
 * Tajadas (R2): bordes en los vértices de la superficie, de las bases de estratos y de la polilínea, y en los cortes de
 * la superficie de falla con los contactos; base en cuerda; peso exacto por trapecios (Simpson por tramos lineales).
 * α > 0 cuando la base baja hacia el pie. Ordinario con N' = W cos α - kh W sin α - u l (F&K, R3).
 * Pendiente de las tareas 2 y 3: línea piezométrica, grieta de tracción, f0 de Janbu corregido y Hoek-Brown: lanzan
 * «not implemented yet» en vez de dar un número.
 */

#pragma once

#include <algorithm>
#include <cmath>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

#include "rockmasspy/hoek_brown.hpp"
#include "rockmasspy/method_info.hpp"
#include "rockmasspy/stereonet.hpp"
#include "rockmasspy/validation.hpp"

namespace rockmasspy {

struct Circle {
    double xc = validation::unset, yc = validation::unset, radius = validation::unset;
};

enum class StrengthModel { MohrCoulomb, HoekBrown };

struct LeMaterial {
    double unit_weight = validation::unset;
    StrengthModel model = StrengthModel::MohrCoulomb;
    double cohesion = validation::unset, friction_deg = validation::unset;  // obligatorios con Mohr-Coulomb
    std::optional<HbParams> hb;                                              // Hoek-Brown (tarea 3)
    std::optional<double> sigma_ci;                                          // en la unidad de esfuerzo del resto
    double ru = 0.0;                                                         // [0, 1): u = ru · σv
};

/// Estratos de arriba hacia abajo: el k va entre la base del k - 1 (o la superficie) y su `bottom`.
struct LeLayer {
    std::vector<Point2> bottom;  // vacío solo en el último: hasta la base del modelo
    int material = -1;           // índice en LeSection::materials
};

struct LeTensionCrack {
    double depth_m = validation::unset;
    double water_fill = 0.0;
};

struct LeSection {
    std::vector<Point2> surface;
    std::vector<LeLayer> layers;
    std::vector<LeMaterial> materials;
    std::optional<double> model_base_y;
    std::optional<std::vector<Point2>> piezometric;  // tarea 2
    double water_unit_weight = 9.81;
    double kh = 0.0;  // [0, 1], horizontal hacia la cara
    std::optional<LeTensionCrack> crack;  // tarea 2
};

/// Exactamente uno de los dos.
struct SlipSurface {
    std::optional<Circle> circle;
    std::optional<std::vector<Point2>> polyline;
};

enum class LeMethod { Ordinary, Bishop, JanbuSimplified, JanbuCorrected, Spencer, MorgensternPrice };
enum class InterSliceFunction { Constant, HalfSine, Points };

struct LeOptions {
    int n_slices = 50;
    double tolerance = 1e-6;
    int max_iterations = 200;
    InterSliceFunction function = InterSliceFunction::HalfSine;  // solo Morgenstern-Price; Spencer usa f = 1
    std::vector<Point2> function_points;                         // x normalizado en [0, 1] de izquierda a derecha, f >= 0
};

/// Tajada en las coordenadas de la sección, de izquierda a derecha. normal_force es la normal efectiva N' de la base;
/// shear_strength es la resistencia disponible c l + N' tan φ (la movilizada es shear_strength / FS). Las fuerzas entre
/// tajadas (borde derecho) solo las llenan Spencer y Morgenstern-Price. material = -1 en un tramo de aire.
struct LeSlice {
    double x_left, x_right, base_y_left, base_y_right, alpha_deg, base_length, weight, pore_pressure, cohesion,
        friction_deg, normal_force, shear_strength, interslice_normal_right, interslice_shear_right;
    int material;
};

struct LeResult {
    std::optional<double> factor_of_safety;
    LeMethod method;
    std::optional<double> lambda;
    int iterations;
    bool converged;
    std::vector<LeSlice> slices;
    double sliding_mass_area;
    MethodInfo info;
    std::vector<std::string> warnings, notes;
};

namespace le_detail {
constexpr double kPi = 3.14159265358979323846;
constexpr double kTol = 1e-9;
using Poly = std::vector<Point2>;

[[noreturn]] inline void fail(const std::string& name, const std::string& what) {
    throw std::invalid_argument("Domain error [RockMassPy]: parameter '" + name + "' " + what);
}
[[noreturn]] inline void not_implemented(const std::string& name, int task) {
    fail(name, "is not implemented yet (task " + std::to_string(task) + ")");
}
inline std::string at(const std::string& name, std::size_t i) { return name + "[" + std::to_string(i) + "]"; }

inline void check_poly(const Poly& p, const std::string& name) {
    if (p.size() < 2) fail(name, "needs at least two points");
    for (std::size_t i = 0; i < p.size(); ++i) {
        validation::require_finite(p[i].x, at(name, i) + ".x");
        validation::require_finite(p[i].y, at(name, i) + ".y");
        if (i > 0) validation::require(p[i].x > p[i - 1].x, at(name, i) + ".x", "must be strictly increasing", p[i].x);
    }
}

/// Cota de la polilínea en x; fuera de su rango por menos de kTol toma el extremo.
inline double interp(const Poly& p, double x) {
    if (x <= p.front().x) return p.front().y;
    if (x >= p.back().x) return p.back().y;
    const auto it = std::upper_bound(p.begin(), p.end(), x, [](double v, const Point2& q) { return v < q.x; });
    const Point2& b = *it;
    const Point2& a = *(it - 1);
    return a.y + (b.y - a.y) * (x - a.x) / (b.x - a.x);
}
inline bool covers(const Poly& p, double lo, double hi) { return p.front().x <= lo + kTol && p.back().x >= hi - kTol; }

inline Poly mirror(const Poly& p) {
    Poly q(p.rbegin(), p.rend());
    for (auto& v : q) v.x = -v.x;
    return q;
}

/// Sección y superficie de falla en el marco interno (cara hacia la derecha).
struct Geo {
    Poly ground;
    std::vector<Poly> bottoms;
    std::vector<int> material;
    std::optional<double> base_y;
    std::optional<Circle> circle;
    std::optional<Poly> polyline;
};

inline Geo make_geo(const LeSection& s, const SlipSurface& f, bool reflect) {
    Geo g;
    g.ground = reflect ? mirror(s.surface) : s.surface;
    for (const auto& l : s.layers) {
        g.bottoms.push_back(reflect && !l.bottom.empty() ? mirror(l.bottom) : l.bottom);
        g.material.push_back(l.material);
    }
    g.base_y = s.model_base_y;
    if (f.circle) g.circle = Circle{reflect ? -f.circle->xc : f.circle->xc, f.circle->yc, f.circle->radius};
    if (f.polyline) g.polyline = reflect ? mirror(*f.polyline) : *f.polyline;
    return g;
}

inline double slip_y(const Geo& g, double x) {
    if (g.circle) {
        const Circle& c = *g.circle;
        const double d = c.radius * c.radius - (x - c.xc) * (x - c.xc);
        return c.yc - std::sqrt(std::max(d, 0.0));
    }
    return interp(*g.polyline, x);
}

inline void sort_unique(std::vector<double>& xs) {
    std::sort(xs.begin(), xs.end());
    std::vector<double> out;
    for (double x : xs)
        if (out.empty() || x > out.back() + kTol) out.push_back(x);
    xs = out;
}

/// x donde la superficie de falla corta o toca la polilínea p (rama inferior del círculo).
inline std::vector<double> slip_cuts(const Geo& g, const Poly& p) {
    std::vector<double> xs;
    if (g.circle) {
        const Circle& c = *g.circle;
        for (std::size_t i = 0; i + 1 < p.size(); ++i) {
            const double dx = p[i + 1].x - p[i].x, dy = p[i + 1].y - p[i].y;
            const double fx = p[i].x - c.xc, fy = p[i].y - c.yc;
            const double A = dx * dx + dy * dy, B = 2.0 * (fx * dx + fy * dy), C = fx * fx + fy * fy - c.radius * c.radius;
            const double disc = B * B - 4.0 * A * C;
            if (disc < 0.0) continue;
            const double sq = std::sqrt(disc);
            for (double t : {(-B - sq) / (2.0 * A), (-B + sq) / (2.0 * A)}) {
                if (t < -1e-12 || t > 1.0 + 1e-12) continue;
                if (p[i].y + t * dy <= c.yc + kTol) xs.push_back(p[i].x + t * dx);
            }
        }
    } else {
        const Poly& s = *g.polyline;
        const double lo = std::max(p.front().x, s.front().x), hi = std::min(p.back().x, s.back().x);
        std::vector<double> v{lo, hi};
        for (const auto& q : p)
            if (q.x > lo && q.x < hi) v.push_back(q.x);
        for (const auto& q : s)
            if (q.x > lo && q.x < hi) v.push_back(q.x);
        sort_unique(v);
        auto d = [&](double x) { return interp(p, x) - interp(s, x); };
        for (std::size_t i = 0; i < v.size(); ++i) {
            const double di = d(v[i]);
            if (std::fabs(di) <= kTol) xs.push_back(v[i]);
            if (i + 1 < v.size()) {
                const double dj = d(v[i + 1]);
                if ((di > kTol && dj < -kTol) || (di < -kTol && dj > kTol)) xs.push_back(v[i] + (v[i + 1] - v[i]) * di / (di - dj));
            }
        }
    }
    sort_unique(xs);
    return xs;
}

struct Mass {
    double xl, xr;
    bool air;  // tramos de aire entre el primer y el último corte
};

inline Mass find_mass(const Geo& g) {
    const Poly& gr = g.ground;
    double lo = gr.front().x, hi = gr.back().x;
    if (g.circle) {
        lo = std::max(lo, g.circle->xc - g.circle->radius);
        hi = std::min(hi, g.circle->xc + g.circle->radius);
    } else {
        const Poly& s = *g.polyline;
        if (!covers(gr, s.front().x, s.back().x)) fail("polyline", "must lie within the x range of the ground surface");
        if (interp(gr, s.front().x) - s.front().y > kTol || interp(gr, s.back().x) - s.back().y > kTol)
            fail("polyline", "must start and end on or above the ground surface");
        lo = s.front().x;
        hi = s.back().x;
    }
    const char* kNoCut = "slip surface does not cut the ground surface twice";
    if (hi <= lo) fail("slip_surface", kNoCut);
    std::vector<double> xs{lo, hi};
    for (double x : slip_cuts(g, gr))
        if (x >= lo && x <= hi) xs.push_back(x);
    for (const auto& q : gr)
        if (q.x > lo && q.x < hi) xs.push_back(q.x);
    if (g.polyline)
        for (const auto& q : *g.polyline)
            if (q.x > lo && q.x < hi) xs.push_back(q.x);
    sort_unique(xs);
    auto d = [&](double x) { return interp(gr, x) - slip_y(g, x); };
    std::vector<std::pair<double, double>> parts;  // tramos con suelo sobre la superficie de falla, ya unidos
    for (std::size_t i = 0; i + 1 < xs.size(); ++i) {
        if (d(0.5 * (xs[i] + xs[i + 1])) <= 0.0) continue;
        if (!parts.empty() && parts.back().second == xs[i]) parts.back().second = xs[i + 1];
        else parts.emplace_back(xs[i], xs[i + 1]);
    }
    if (parts.empty()) fail("slip_surface", kNoCut);
    double scale = 1.0;
    for (const auto& q : gr) scale = std::max({scale, std::fabs(q.x), std::fabs(q.y)});
    const double xl = parts.front().first, xr = parts.back().second;
    if (std::fabs(d(xl)) > 1e-7 * scale || std::fabs(d(xr)) > 1e-7 * scale) fail("slip_surface", kNoCut);
    return {xl, xr, parts.size() > 1};
}

/// Una tajada en el marco interno.
struct Slice {
    double xa, xb, ya, yb, sa, ca, alpha, b, l, area, W, xg, yg, u;
    std::vector<int> cand;  // materiales candidatos de la base (más de uno si cae en un contacto)
    int mat = -1;           // -1: aire
    double c = 0.0, tf = 0.0;
    double Np = 0.0, E = 0.0, X = 0.0;
};

/// Pesos, centroide y material de la base de la tajada [xa, xb].
inline Slice build_slice(const Geo& g, const LeSection& s, double xa, double xb) {
    Slice t{};
    t.xa = xa;
    t.xb = xb;
    t.ya = slip_y(g, xa);
    t.yb = slip_y(g, xb);
    t.b = xb - xa;
    t.l = std::hypot(t.b, t.ya - t.yb);
    t.alpha = std::atan2(t.ya - t.yb, t.b);
    t.sa = std::sin(t.alpha);
    t.ca = std::cos(t.alpha);
    // funciones lineales en la tajada: 0 base, 1 superficie, 2.. bases de estratos
    const std::size_t nb = g.bottoms.size();
    std::vector<double> fa{t.ya, interp(g.ground, xa)}, fb{t.yb, interp(g.ground, xb)};
    for (std::size_t k = 0; k < nb; ++k) {
        const bool has = !g.bottoms[k].empty();
        fa.push_back(has ? interp(g.bottoms[k], xa) : -std::numeric_limits<double>::infinity());
        fb.push_back(has ? interp(g.bottoms[k], xb) : -std::numeric_limits<double>::infinity());
    }
    std::vector<double> br{xa, xb};
    for (std::size_t i = 0; i < fa.size(); ++i)
        for (std::size_t j = i + 1; j < fa.size(); ++j) {
            if (!std::isfinite(fa[j])) continue;
            const double da = fa[i] - fa[j], db = fb[i] - fb[j];
            if ((da > 0.0 && db < 0.0) || (da < 0.0 && db > 0.0)) br.push_back(xa + t.b * da / (da - db));
        }
    std::sort(br.begin(), br.end());
    auto val = [&](std::size_t i, double x) {
        return std::isfinite(fa[i]) ? fa[i] + (fb[i] - fa[i]) * (x - xa) / t.b : fa[i];
    };
    // espesor y momentos de cada estrato en x
    std::vector<double> A(nb, 0.0), Mx(nb, 0.0), My(nb, 0.0);
    auto add = [&](double x, double w) {
        const double base = val(0, x);
        double top = val(1, x);
        for (std::size_t k = 0; k < nb; ++k) {
            const double bot = std::min(top, val(2 + k, x));
            const double lo = std::max(base, bot);
            const double th = std::max(0.0, top - lo);
            A[k] += w * th;
            Mx[k] += w * th * x;
            My[k] += w * th * 0.5 * (top + lo);
            top = bot;
        }
    };
    for (std::size_t i = 0; i + 1 < br.size(); ++i) {
        const double p = br[i], q = br[i + 1], h = (q - p) / 6.0;
        if (q - p <= 0.0) continue;
        add(p, h);
        add(0.5 * (p + q), 4.0 * h);
        add(q, h);
    }
    double W = 0.0, sx = 0.0, sy = 0.0;
    for (std::size_t k = 0; k < nb; ++k) {
        const double gam = s.materials[g.material[k]].unit_weight;
        t.area += A[k];
        W += gam * A[k];
        sx += gam * Mx[k];
        sy += gam * My[k];
    }
    const double xm = 0.5 * (xa + xb), ym = 0.5 * (t.ya + t.yb);
    t.W = W;
    t.xg = W > 0.0 ? sx / W : xm;
    t.yg = W > 0.0 ? sy / W : ym;
    // material de la base en el punto medio de la cuerda
    if (ym <= interp(g.ground, xm) + kTol) {
        double top = interp(g.ground, xm);
        for (std::size_t k = 0; k < nb; ++k) {
            const double bot = g.bottoms[k].empty() ? -std::numeric_limits<double>::infinity()
                                                    : std::min(top, interp(g.bottoms[k], xm));
            if (ym >= bot - kTol && ym <= top + kTol) t.cand.push_back(g.material[k]);
            top = bot;
        }
        if (t.cand.empty()) fail("slip_surface", "passes below the bottom of the last layer");
        t.mat = t.cand.front();
        double ru = 0.0;
        for (int m : t.cand) ru = std::max(ru, s.materials[m].ru);
        t.u = ru * W / t.b;
        const auto& m = s.materials[t.mat];
        t.c = m.cohesion;
        t.tf = std::tan(m.friction_deg * kPi / 180.0);
    }
    return t;
}

/// El candidato más débil por τ = c + σn' tan φ en el σn' de la iteración.
inline void choose(std::vector<Slice>& sl, const LeSection& s) {
    for (auto& t : sl) {
        if (t.cand.size() < 2) continue;
        const double sn = std::max(t.Np / t.l, 0.0);
        double best = std::numeric_limits<double>::infinity();
        for (int m : t.cand) {
            const auto& mm = s.materials[m];
            const double tf = std::tan(mm.friction_deg * kPi / 180.0), tau = mm.cohesion + sn * tf;
            if (tau < best) {
                best = tau;
                t.mat = m;
                t.c = mm.cohesion;
                t.tf = tf;
            }
        }
    }
}

inline void validate(const LeSection& s, const SlipSurface& f, const LeOptions& o) {
    using namespace validation;
    check_poly(s.surface, "surface");
    if (s.materials.empty()) fail("materials", "must not be empty");
    for (std::size_t i = 0; i < s.materials.size(); ++i) {
        const auto& m = s.materials[i];
        const std::string n = at("materials", i);
        require_positive(m.unit_weight, n + ".unit_weight");
        require_finite(m.ru, n + ".ru");
        require(m.ru >= 0.0 && m.ru < 1.0, n + ".ru", "must be within [0, 1)", m.ru);
        if (m.model == StrengthModel::MohrCoulomb) {
            require_non_negative(m.cohesion, n + ".cohesion");
            require_finite(m.friction_deg, n + ".friction_deg");
            require(m.friction_deg >= 0.0 && m.friction_deg < 90.0, n + ".friction_deg", "must be within [0, 90)",
                    m.friction_deg);
        } else {
            if (!m.hb) fail(n + ".hb", "is required for HoekBrown");
            if (!m.sigma_ci) fail(n + ".sigma_ci", "is required for HoekBrown");
            require_positive(*m.sigma_ci, n + ".sigma_ci");
        }
    }
    if (s.layers.empty()) fail("layers", "must not be empty");
    for (std::size_t k = 0; k < s.layers.size(); ++k) {
        const auto& l = s.layers[k];
        const std::string n = at("layers", k);
        require(l.material >= 0 && l.material < static_cast<int>(s.materials.size()), n + ".material",
                "must index an entry of materials", l.material);
        if (l.bottom.empty()) {
            if (k + 1 != s.layers.size()) fail(n + ".bottom", "may be empty only in the last layer");
        } else {
            check_poly(l.bottom, n + ".bottom");
        }
    }
    if (s.model_base_y) require_finite(*s.model_base_y, "model_base_y");
    require_positive(s.water_unit_weight, "water_unit_weight");
    require_in_range(s.kh, 0.0, 1.0, "kh");
    if (s.piezometric) check_poly(*s.piezometric, "piezometric");
    if (s.crack) {
        require_non_negative(s.crack->depth_m, "crack.depth_m");
        require_in_range(s.crack->water_fill, 0.0, 1.0, "crack.water_fill");
    }
    if (f.circle.has_value() == f.polyline.has_value()) fail("slip_surface", "needs exactly one of circle and polyline");
    if (f.circle) {
        require_finite(f.circle->xc, "circle.xc");
        require_finite(f.circle->yc, "circle.yc");
        require_positive(f.circle->radius, "circle.radius");
    } else {
        check_poly(*f.polyline, "polyline");
    }
    require(o.n_slices >= 5, "n_slices", "must be at least 5", o.n_slices);
    require_positive(o.tolerance, "tolerance");
    require(o.max_iterations >= 1, "max_iterations", "must be at least 1", o.max_iterations);
    if (o.function == InterSliceFunction::Points) {
        if (o.function_points.empty()) fail("function_points", "must not be empty with the Points function");
        for (std::size_t i = 0; i < o.function_points.size(); ++i) {
            const auto& p = o.function_points[i];
            const std::string n = at("function_points", i);
            require_in_range(p.x, 0.0, 1.0, n + ".x");
            require_non_negative(p.y, n + ".y");
            if (i > 0) require(p.x > o.function_points[i - 1].x, n + ".x", "must be strictly increasing", p.x);
        }
    }
    // lo que llega en las tareas 2 y 3: nunca un número a medias
    if (s.piezometric) not_implemented("piezometric", 2);
    if (s.crack) not_implemented("crack", 2);
    for (std::size_t i = 0; i < s.materials.size(); ++i)
        if (s.materials[i].model == StrengthModel::HoekBrown) not_implemented(at("materials", i) + ".model HoekBrown", 3);
}

struct Built {
    std::vector<Slice> slices;
    bool reflected = false, air = false;
};

inline Built build(const LeSection& s, const SlipSurface& f, int n_slices) {
    Mass m = find_mass(make_geo(s, f, false));
    const double yl = interp(s.surface, m.xl), yr = interp(s.surface, m.xr);
    if (std::fabs(yl - yr) <= kTol)
        fail("surface", "is level at both ends of the sliding mass: the face direction is undefined");
    Built out;
    out.reflected = yr > yl;  // la superficie sube: la cara mira a la izquierda
    const Geo g = make_geo(s, f, out.reflected);
    if (out.reflected) m = find_mass(g);
    out.air = m.air;
    const double xl = m.xl, xr = m.xr;
    for (std::size_t k = 0; k < g.bottoms.size(); ++k)
        if (!g.bottoms[k].empty() && !covers(g.bottoms[k], xl, xr))
            fail(at("layers", k) + ".bottom", "does not cover the sliding mass");
    if (g.base_y) {
        double ymin = std::min(slip_y(g, xl), slip_y(g, xr));
        if (g.circle && g.circle->xc > xl && g.circle->xc < xr) ymin = g.circle->yc - g.circle->radius;
        if (g.polyline)
            for (const auto& q : *g.polyline)
                if (q.x > xl && q.x < xr) ymin = std::min(ymin, q.y);
        if (ymin < *g.base_y - kTol) fail("slip_surface", "goes below model_base_y");
    }
    // bordes obligatorios
    std::vector<double> xs{xl, xr};
    auto inside = [&](double x) { return x > xl + kTol && x < xr - kTol; };
    std::vector<const Poly*> lines{&g.ground};
    for (const auto& b : g.bottoms)
        if (!b.empty()) lines.push_back(&b);
    for (const Poly* p : lines) {
        for (const auto& q : *p)
            if (inside(q.x)) xs.push_back(q.x);
        for (double x : slip_cuts(g, *p))
            if (inside(x)) xs.push_back(x);
    }
    if (g.polyline)
        for (const auto& q : *g.polyline)
            if (inside(q.x)) xs.push_back(q.x);
    sort_unique(xs);
    xs.back() = xr;
    // n_slices repartidas en proporción al largo de la superficie de falla en cada tramo, con bases de igual largo
    // dentro del tramo (en el círculo, igual ángulo): las tajadas empinadas salen angostas y la cuerda pierde menos
    auto theta = [&](double x) { return std::asin(std::clamp((x - g.circle->xc) / g.circle->radius, -1.0, 1.0)); };
    auto length = [&](double a, double b) {
        return g.circle ? g.circle->radius * (theta(b) - theta(a)) : std::hypot(b - a, slip_y(g, b) - slip_y(g, a));
    };
    double L = 0.0;
    for (std::size_t i = 0; i + 1 < xs.size(); ++i) L += length(xs[i], xs[i + 1]);
    std::vector<double> edges{xl};
    for (std::size_t i = 0; i + 1 < xs.size(); ++i) {
        const double a = xs[i], b = xs[i + 1];
        const int k = std::max(1, static_cast<int>(std::lround(n_slices * length(a, b) / L)));
        for (int j = 1; j < k; ++j) {
            const double x = g.circle ? g.circle->xc + g.circle->radius *
                                                           std::sin(theta(a) + (theta(b) - theta(a)) * j / k)
                                      : a + (b - a) * j / k;
            if (x > edges.back() + kTol && x < b - kTol) edges.push_back(x);
        }
        edges.push_back(b);
    }
    for (std::size_t i = 0; i + 1 < edges.size(); ++i) out.slices.push_back(build_slice(g, s, edges[i], edges[i + 1]));
    return out;
}

inline LeSlice to_public(const Slice& t, const Slice* left, bool reflected, const LeSection& s) {
    LeSlice o{};
    o.alpha_deg = t.alpha * 180.0 / kPi;
    o.base_length = t.l;
    o.weight = t.W;
    o.pore_pressure = t.u;
    o.cohesion = t.mat >= 0 ? t.c : 0.0;
    o.friction_deg = t.mat >= 0 ? s.materials[t.mat].friction_deg : 0.0;
    o.normal_force = t.Np;
    o.shear_strength = t.c * t.l + t.Np * t.tf;
    o.material = t.mat;
    if (reflected) {
        o.x_left = -t.xb;
        o.x_right = -t.xa;
        o.base_y_left = t.yb;
        o.base_y_right = t.ya;
        o.interslice_normal_right = left ? left->E : 0.0;
        o.interslice_shear_right = left ? left->X : 0.0;
    } else {
        o.x_left = t.xa;
        o.x_right = t.xb;
        o.base_y_left = t.ya;
        o.base_y_right = t.yb;
        o.interslice_normal_right = t.E;
        o.interslice_shear_right = t.X;
    }
    return o;
}

inline std::vector<LeSlice> to_public(const std::vector<Slice>& sl, bool reflected, const LeSection& s) {
    std::vector<LeSlice> out;
    for (std::size_t i = 0; i < sl.size(); ++i) out.push_back(to_public(sl[i], i ? &sl[i - 1] : nullptr, reflected, s));
    if (reflected) std::reverse(out.begin(), out.end());
    return out;
}

inline MethodInfo info(LeMethod m) {
    const std::string slide = "Slide2 Verification Manual (2022) problems 1, 21; Fredlund & Krahn (1977)";
    switch (m) {
        case LeMethod::Ordinary:
            return {"Ordinary-Fellenius", Verification::Secondary, slide + "; N' = W cos(a) - kh W sin(a) - u l (F&K)"};
        case LeMethod::Bishop:
            return {"Bishop-Simplified", Verification::Secondary, slide + "; Bishop (1955) not read"};
        case LeMethod::JanbuSimplified:
            return {"Janbu-Simplified", Verification::Secondary, slide + "; Janbu (1973) not read"};
        case LeMethod::JanbuCorrected:
            return {"Janbu-Corrected", Verification::Secondary, slide + "; Janbu (1973) not read"};
        case LeMethod::Spencer:
            return {"Spencer", Verification::Secondary,
                    slide + "; Zhu et al. (2005) algorithm with f(x) = 1; Spencer (1967) not read"};
        case LeMethod::MorgensternPrice:
            return {"Morgenstern-Price-GLE", Verification::Secondary,
                    slide + "; Zhu et al. (2005) algorithm; Morgenstern & Price (1965) not read"};
    }
    return {};
}

inline const char* name(LeMethod m) {
    switch (m) {
        case LeMethod::Ordinary: return "Ordinary";
        case LeMethod::Bishop: return "Bishop";
        case LeMethod::JanbuSimplified: return "Janbu simplified";
        case LeMethod::JanbuCorrected: return "Janbu corrected";
        case LeMethod::Spencer: return "Spencer";
        case LeMethod::MorgensternPrice: return "Morgenstern-Price";
    }
    return "";
}

inline const char* kBackward = "the sliding mass does not move towards the face";

struct Solve {
    std::optional<double> F, lambda;
    int iterations = 0;
    bool converged = false;
    std::vector<std::string> notes;
};

/// N' de la base por equilibrio vertical sin cortante entre tajadas (Bishop y Janbu).
inline double vertical_normal(const Slice& t, double F) {
    const double ma = t.ca + t.sa * t.tf / F;
    return (t.W - t.u * t.b - t.c * t.l * t.sa / F) / ma;
}
/// N' inicial sin fuerzas entre tajadas (la del Ordinario).
inline void ordinary_normals(std::vector<Slice>& sl, double kh) {
    for (auto& t : sl) t.Np = std::max(0.0, t.W * t.ca - kh * t.W * t.sa - t.u * t.l);
}

inline Solve ordinary(std::vector<Slice>& sl, const LeSection& s) {
    Solve r;
    ordinary_normals(sl, s.kh);
    choose(sl, s);
    double num = 0.0, den = 0.0;
    int clipped = 0;
    for (const auto& t : sl) {
        num += t.c * t.l + t.Np * t.tf;
        den += t.W * t.sa + s.kh * t.W * t.ca;
        clipped += t.mat >= 0 && t.W * t.ca - s.kh * t.W * t.sa - t.u * t.l < 0.0;
    }
    r.iterations = 1;
    if (den <= 0.0 || num / den <= 0.0) {
        r.notes.push_back(kBackward);
        return r;
    }
    r.F = num / den;
    r.converged = true;
    if (clipped > 0)
        r.notes.push_back("effective normal force below zero in " + std::to_string(clipped) +
                          " slices: friction taken as zero there");
    return r;
}

/// Centro de momentos de Bishop: el del círculo o, con polilínea, el del círculo por los extremos y el punto más
/// alejado bajo la cuerda que los une (R7).
inline std::optional<Point2> bishop_centre(const Geo& g, const std::vector<Slice>& sl) {
    if (g.circle) return Point2{g.circle->xc, g.circle->yc};
    const Point2 a{sl.front().xa, sl.front().ya}, c{sl.back().xb, sl.back().yb};
    const double L = std::hypot(c.x - a.x, c.y - a.y);
    Point2 b{};
    double depth = 0.0;
    for (const auto& t : sl) {
        const double d = ((c.x - a.x) * (t.ya - a.y) - (c.y - a.y) * (t.xa - a.x)) / L;  // < 0 bajo la cuerda
        if (-d > depth) {
            depth = -d;
            b = {t.xa, t.ya};
        }
    }
    if (depth <= kTol * std::max(1.0, L)) return std::nullopt;
    const double D = 2.0 * (a.x * (b.y - c.y) + b.x * (c.y - a.y) + c.x * (a.y - b.y));
    const double a2 = a.x * a.x + a.y * a.y, b2 = b.x * b.x + b.y * b.y, c2 = c.x * c.x + c.y * c.y;
    return Point2{(a2 * (b.y - c.y) + b2 * (c.y - a.y) + c2 * (a.y - b.y)) / D,
                  (a2 * (c.x - b.x) + b2 * (a.x - c.x) + c2 * (b.x - a.x)) / D};
}

/// Bishop (momentos respecto de O con brazos exactos de la cuerda) o Janbu simplificado (fuerzas horizontales).
inline Solve bishop_janbu(std::vector<Slice>& sl, const LeSection& s, const Geo& g, const LeOptions& o, bool bishop) {
    Solve r;
    const double kh = s.kh;
    std::vector<double> aS(sl.size(), 0.0), aN(sl.size(), 0.0);
    double D = 0.0;
    if (bishop) {
        const auto O = bishop_centre(g, sl);
        if (!O) {
            r.notes.push_back("Bishop needs a curved slip surface: the polyline is straight");
            return r;
        }
        if (g.polyline)
            r.notes.push_back("Bishop on a non-circular surface: moments about the centre of the circle through the "
                              "ends and the deepest point");
        for (std::size_t i = 0; i < sl.size(); ++i) {
            const auto& t = sl[i];
            const double mx = 0.5 * (t.xa + t.xb) - O->x, my = 0.5 * (t.ya + t.yb) - O->y;
            aS[i] = -(mx * t.sa + my * t.ca);
            aN[i] = mx * t.ca - my * t.sa;
            D += t.W * (O->x - t.xg) + kh * t.W * (O->y - t.yg);
        }
    }
    ordinary_normals(sl, kh);
    double F = 1.0;
    for (r.iterations = 1; r.iterations <= o.max_iterations; ++r.iterations) {
        choose(sl, s);
        for (auto& t : sl) t.Np = vertical_normal(t, F);
        double num = 0.0, den = bishop ? D : 0.0;
        for (std::size_t i = 0; i < sl.size(); ++i) {
            const auto& t = sl[i];
            const double S = t.c * t.l + t.Np * t.tf;
            if (bishop) {
                num += aS[i] * S;
                den += aN[i] * (t.Np + t.u * t.l);
            } else {
                num += S / t.ca;
                den += t.W * t.sa / t.ca + kh * t.W;
            }
        }
        if (!(den > 0.0) || !(num / den > 0.0) || !std::isfinite(num / den)) {
            r.notes.push_back(kBackward);
            return r;
        }
        const double Fn = num / den;
        if (std::fabs(Fn - F) < o.tolerance) {
            r.F = Fn;
            r.converged = true;
            for (auto& t : sl) t.Np = vertical_normal(t, Fn);
            return r;
        }
        F = Fn;
    }
    r.iterations = o.max_iterations;
    return r;
}

inline double interslice_f(const LeOptions& o, bool spencer, double t, bool reflected) {
    if (spencer || o.function == InterSliceFunction::Constant) return 1.0;
    if (o.function == InterSliceFunction::HalfSine) return std::sin(kPi * t);
    return interp(o.function_points, reflected ? 1.0 - t : t);
}

/// Spencer y Morgenstern-Price por el algoritmo de Zhu et al. (2005), con kh en R, T y el momento.
inline Solve zhu(std::vector<Slice>& sl, const LeSection& s, const LeOptions& o, bool spencer, bool reflected,
                 double F0) {
    Solve r;
    const std::size_t n = sl.size();
    const double kh = s.kh, x0 = sl.front().xa, x1 = sl.back().xb;
    std::vector<double> fb(n), R(n), T(n), Phi(n), Psi(n);
    for (std::size_t i = 0; i < n; ++i) fb[i] = interslice_f(o, spencer, (sl[i].xb - x0) / (x1 - x0), reflected);
    ordinary_normals(sl, kh);
    double F = F0, lam = 0.0;
    auto phi = [&](const Slice& t, double f, double F_) {
        return (t.sa - lam * f * t.ca) * t.tf + (t.ca + lam * f * t.sa) * F_;
    };
    for (r.iterations = 1; r.iterations <= o.max_iterations; ++r.iterations) {
        choose(sl, s);
        for (std::size_t i = 0; i < n; ++i) {
            const auto& t = sl[i];
            R[i] = (t.W * t.ca - kh * t.W * t.sa - t.u * t.l) * t.tf + t.c * t.l;
            T[i] = t.W * t.sa + kh * t.W * t.ca;
        }
        bool ok = false;
        for (int k = 0; k < o.max_iterations; ++k) {
            for (std::size_t i = 0; i + 1 < n; ++i) {
                Phi[i] = phi(sl[i], fb[i], F);
                Psi[i] = phi(sl[i + 1], fb[i], F) / Phi[i];
            }
            double num = R[n - 1], den = T[n - 1], p = 1.0;
            for (std::size_t i = n - 1; i-- > 0;) {
                p *= Psi[i];
                num += R[i] * p;
                den += T[i] * p;
            }
            if (!(den > 0.0) || !(num / den > 0.0) || !std::isfinite(num / den)) {
                r.notes.push_back(kBackward);
                return r;
            }
            const double Fn = num / den;
            const bool done = std::fabs(Fn - F) < o.tolerance;
            F = Fn;
            if (done) {
                ok = true;
                break;
            }
        }
        if (!ok) break;
        // fuerzas entre tajadas en el borde derecho de cada una; E = 0 en los dos extremos
        double EPhi = 0.0;
        for (std::size_t i = 0; i + 1 < n; ++i) {
            Phi[i] = phi(sl[i], fb[i], F);
            const double psi = i ? phi(sl[i], fb[i - 1], F) / Phi[i - 1] : 0.0;
            EPhi = psi * EPhi + F * T[i] - R[i];
            sl[i].E = EPhi / Phi[i];
        }
        sl[n - 1].E = 0.0;
        double num = 0.0, den = 0.0;
        for (std::size_t i = 0; i < n; ++i) {
            const auto& t = sl[i];
            const double El = i ? sl[i - 1].E : 0.0, fl = i ? fb[i - 1] : 0.0;
            const double hc = t.yg - 0.5 * (t.ya + t.yb);  // altura del centroide sobre el punto medio de la base
            num += t.b * (t.E + El) * std::tan(t.alpha) + 2.0 * kh * t.W * hc;
            den += t.b * (fb[i] * t.E + fl * El);
        }
        const double lamn = num / den;
        if (!std::isfinite(lamn)) break;
        // N' con las fuerzas entre tajadas, para el material de los contactos y la tabla
        for (std::size_t i = 0; i < n; ++i) {
            auto& t = sl[i];
            const double El = i ? sl[i - 1].E : 0.0, Xl = i ? lam * fb[i - 1] * El : 0.0, Xr = lam * fb[i] * t.E;
            t.Np = t.W * t.ca - kh * t.W * t.sa - (El - t.E) * t.sa + (Xl - Xr) * t.ca - t.u * t.l;
            t.X = Xr;
        }
        const bool done = std::fabs(lamn - lam) < o.tolerance;
        if (done) {
            r.F = F;
            r.lambda = lam;
            r.converged = true;
            return r;
        }
        lam = lamn;
    }
    r.iterations = std::min(r.iterations, o.max_iterations);
    return r;
}

inline int low_m_alpha(const std::vector<Slice>& sl, double F) {
    int k = 0;
    for (const auto& t : sl)
        if (t.mat >= 0 && t.ca + t.sa * t.tf / F < 0.2) ++k;
    return k;
}
}  // namespace le_detail

/// Tajadas de la masa deslizante (geometría, pesos, u y material de la base), sin fuerzas.
inline std::vector<LeSlice> make_slices(const LeSection& section, const SlipSurface& surface, int n_slices) {
    using namespace le_detail;
    LeOptions o;
    o.n_slices = n_slices;
    validate(section, surface, o);
    const Built b = build(section, surface, n_slices);
    return to_public(b.slices, b.reflected, section);
}

inline LeResult le_factor_of_safety(const LeSection& section, const SlipSurface& surface, LeMethod method,
                                    const LeOptions& options = {}) {
    using namespace le_detail;
    validate(section, surface, options);
    if (method == LeMethod::JanbuCorrected) not_implemented("method JanbuCorrected", 2);
    Built b = build(section, surface, options.n_slices);
    const Geo g = make_geo(section, surface, b.reflected);
    auto& sl = b.slices;
    Solve r;
    switch (method) {
        case LeMethod::Ordinary: r = ordinary(sl, section); break;
        case LeMethod::Bishop: r = bishop_janbu(sl, section, g, options, true); break;
        case LeMethod::JanbuSimplified: r = bishop_janbu(sl, section, g, options, false); break;
        default: {
            auto tmp = sl;
            const Solve bi = bishop_janbu(tmp, section, g, options, true);
            r = zhu(sl, section, options, method == LeMethod::Spencer, b.reflected, bi.F ? *bi.F : 1.0);
        }
    }
    LeResult out{std::nullopt, method, std::nullopt, r.iterations, r.converged, {}, 0.0, info(method), {}, r.notes};
    if (b.air)
        out.warnings.push_back("slip surface crosses the ground surface more than twice: the mass is taken between "
                               "the first and the last cut");
    if (!r.converged && r.notes.empty()) out.warnings.push_back(std::string(name(method)) + " did not converge");
    if (r.converged) {
        out.factor_of_safety = r.F;
        out.lambda = r.lambda;
        if (method != LeMethod::Ordinary) {
            const int k = low_m_alpha(sl, *r.F);
            if (k > 0)
                out.warnings.push_back("m-alpha below 0.2 in " + std::to_string(k) +
                                       " slices: results may be unreliable");
        }
    }
    for (const auto& t : sl) out.sliding_mass_area += t.area;
    out.slices = to_public(sl, b.reflected, section);
    return out;
}

}  // namespace rockmasspy
