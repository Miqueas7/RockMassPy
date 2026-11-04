/**
 * @file limit_equilibrium.hpp
 * @brief Equilibrio límite 2D por tajadas verticales sobre una superficie dada (círculo o polilínea): Ordinario,
 *        Bishop simplificado, Janbu simplificado, Spencer y Morgenstern-Price/GLE.
 *
 * Fuentes (todas Secondary): Slide2 Verification Manual (2022), problemas 1 y 21 (Fredlund y Krahn 1977, ACADS);
 * Morgenstern-Price y Spencer: para cada λ, F es la raíz con intervalo de la ecuación de fuerzas de Zhu, Lee, Qian y
 * Chen (2005), no leído; λ como raíz de la ecuación de momentos (barrido desde 0 mientras el residuo baje y regula
 * falsi con bisección).
 * Límite conocido del barrido de λ: cada lado avanza solo mientras |g| (residuo de momentos) baje, porque más allá de un
 * máximo de |g| aparecían raíces espurias (ACADS 3(a): λ -2.0, F 0.22 con Bishop 3.7). Una raíz física que esté más
 * allá de un máximo de |g| no se encuentra; en ese caso el resultado es FS vacío con el aviso de no convergencia.
 * Convenciones: x horizontal, y hacia arriba, unidades coherentes. Se trabaja con un origen local (UTM sin pérdida de
 * precisión). La cara puede mirar a cualquier lado: el núcleo detecta el sentido y refleja (x -> -x) por dentro, así
 * que una sección reflejada da el mismo FS y el mismo λ.
 * «Hacia atrás» se decide una vez, con la fuerza o el momento motor; sin resistencia, FS = 0; un iterado no positivo o
 * no finito da FS vacío con el aviso «<method> did not converge».
 * Tajadas (R2): bordes en los vértices de la superficie, de las bases de estratos y de la polilínea, y en los cortes de
 * la superficie de falla con los contactos; base en cuerda; peso exacto por trapecios (Simpson por tramos lineales).
 * α > 0 cuando la base baja hacia el pie. Ordinario con N' = W cos α - kh W sin α - u l (F&K, R3).
 * Agua (R11): con línea piezométrica, u = γw·max(y_piezo - y_base, 0) en el punto medio de la base y el ru de los
 * materiales se ignora (nota); sin ella, u = ru·W/b con el ru del material de la base. Los vértices de la piezométrica
 * y sus cortes con la superficie de falla son bordes de tajada.
 * Agua encharcada (R16): donde la piezométrica queda sobre el terreno (lago de tajo, poza), la presión
 * p = γw·max(y_piezo - y_terreno, 0) actúa normal al terreno hacia la masa. Por tajada: peso p_med·b hacia abajo y
 * empuje p_med·b·(pendiente del terreno) hacia la masa, en el centroide del trapecio de presiones sobre el tramo de
 * terreno (los cortes piezométrica-terreno son bordes, así p es lineal en cada tajada). Entra como carga externa en
 * todos los métodos: en N' y en la fuerza motora (Ordinario, Janbu, R y T de Spencer/M-P), en el momento respecto del
 * centro (Bishop) y en la ecuación de momentos de Zhu con su brazo desde el medio de la base. Nota «ponded water...».
 * Talud sumergido: Bishop y Janbu dan el FS del talud con peso γ - γw; la suma de fuerzas sobre las bases no cierra el
 * agua entre tajadas, así que con agua encharcada Spencer y M-P deciden «hacia atrás» también con la fuerza horizontal
 * de Janbu, y el Ordinario sin fuerza motora da FS vacío con su nota (no «does not move towards the face»).
 * Grieta de tracción (R8): vertical, de profundidad fija zc bajo la superficie. La superficie de falla se corta donde
 * la línea a zc bajo el terreno la encuentra por primera vez desde la cresta; la masa termina ahí en una cara
 * vertical. Con llenado f, el agua es una fuerza horizontal P = ½γw(f·zc)² hacia el pie, a f·zc/3 sobre el fondo de la
 * grieta, aplicada a la tajada de la grieta como fuerza externa: momento en Bishop, fuerza horizontal en Janbu, R y T
 * de esa tajada y su momento en Spencer/M-P (equivale a la E de borde sin cortante), y en el Ordinario proyectada sobre
 * la base de esa tajada como kh·W (nota). Si la línea a zc no corta la superficie de falla, la grieta no actúa (nota);
 * tampoco si el corte del lado de la cresta queda a menos de 1e-9 del borde de la masa (grieta casi nula, nota).
 * Janbu corregido (R4): FS = f0·FS_Janbu, f0 = 1 + b1 (d/L - 1.4 (d/L)²); d es la mayor distancia de la superficie de
 * falla a la cuerda entre sus extremos y L el largo de la cuerda; b1 = 0.69 si todas las bases tienen c > 0 y φ > 0,
 * 0.50 si todas tienen c = 0, 0.31 si todas tienen φ = 0, y 0.69 con nota si se mezclan. Fuente secundaria (Abramson
 * et al. 2002, no leído).
 * Hoek-Brown no lineal: en cada iteración la base toma el c y el φ tangentes a la envolvente de Balmer (Hoek et al.
 * 2002, ec. 8-10, `hb_normal_shear`) en el σn' = N'/l de la iteración anterior; σ3 se busca por bisección en
 * [σt, max(σn', 0)] y tan φ = (k - 1)/(2√k) con k = dσ1/dσ3. Arranque: tangentes en el σn' del Ordinario de cada
 * tajada (Spencer y M-P arrancan en el σn' de Bishop convergido, si lo hay). La recta pasa por el punto de la
 * envolvente, así que el FS convergido no depende de la pendiente: la tangente solo guía la iteración. Una base con σn' <= σt no resiste (τ = 0, aviso agregado). Se itera hasta que el FS cambie menos que la
 * tolerancia y los σn' de las bases de Hoek-Brown menos que tolerancia·σci; si no, FS vacío y aviso. El Ordinario no
 * itera (su N' no depende de la resistencia). Unidades: `sigma_ci` va en la unidad de esfuerzo de la sección (kPa si
 * γ está en kN/m³ y la geometría en m). make_slices deja c y φ en 0 en las bases de Hoek-Brown (dependen de σn').
 * Fuente: Carranza-Torres y Hormazábal (2020), similitud de la Tabla 1 (Secondary); su FS 2.01 no se reproduce.
 */

#pragma once

#include <algorithm>
#include <cmath>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>
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

/// Constantes de Hoek-Brown dadas directamente (sin GSI), como en Carranza-Torres y Hormazábal (2020).
inline HbParams hb_params_from_constants(double mb, double s, double a) {
    using namespace validation;
    require_positive(mb, "mb");
    require_in_range(s, 0.0, 1.0, "s");
    require_positive(a, "a");
    require(a <= 1.0, "a", "must be within (0, 1]", a);
    return {mb, s, a, {"HB-constants", Verification::Primary, "Hoek, Carranza-Torres & Corkum (2002); mb, s, a given"}, {}};
}

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

/// Origen local: centro del rango x de la superficie y su cota mínima. Se resta al entrar, así las coordenadas UTM no
/// pierden precisión; reflejar la sección refleja el origen exactamente.
inline Point2 local_origin(const LeSection& s) {
    double ymin = s.surface.front().y;
    for (const auto& q : s.surface) ymin = std::min(ymin, q.y);
    return {0.5 * (s.surface.front().x + s.surface.back().x), ymin};
}

/// Traslada al origen local y, si toca, refleja x -> -x (invirtiendo el orden).
inline Poly to_local(const Poly& p, Point2 o, bool reflect) {
    Poly q;
    for (const auto& v : p) q.push_back({v.x - o.x, v.y - o.y});
    if (reflect) {
        std::reverse(q.begin(), q.end());
        for (auto& v : q) v.x = -v.x;
    }
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
    std::optional<Poly> piezo;
};

inline Geo make_geo(const LeSection& s, const SlipSurface& f, bool reflect) {
    const Point2 o = local_origin(s);
    Geo g;
    g.ground = to_local(s.surface, o, reflect);
    for (const auto& l : s.layers) {
        g.bottoms.push_back(l.bottom.empty() ? l.bottom : to_local(l.bottom, o, reflect));
        g.material.push_back(l.material);
    }
    if (s.model_base_y) g.base_y = *s.model_base_y - o.y;
    if (f.circle) {
        const double xc = f.circle->xc - o.x;
        g.circle = Circle{reflect ? -xc : xc, f.circle->yc - o.y, f.circle->radius};
    }
    if (f.polyline) g.polyline = to_local(*f.polyline, o, reflect);
    if (s.piezometric) g.piezo = to_local(*s.piezometric, o, reflect);
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

/// x donde dos polilíneas se cortan o se tocan, en su rango x común.
inline std::vector<double> poly_cuts(const Poly& p, const Poly& s) {
    std::vector<double> xs;
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
    sort_unique(xs);
    return xs;
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
        xs = poly_cuts(p, *g.polyline);
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
    // tolerancia del corte relativa al tamaño de la superficie de falla, no a las coordenadas
    const double size = g.circle ? g.circle->radius
                                 : std::hypot(g.polyline->back().x - g.polyline->front().x,
                                              g.polyline->back().y - g.polyline->front().y);
    const double xl = parts.front().first, xr = parts.back().second;
    if (std::fabs(d(xl)) > 1e-7 * size || std::fabs(d(xr)) > 1e-7 * size) fail("slip_surface", kNoCut);
    return {xl, xr, parts.size() > 1};
}

/// Una tajada en el marco interno.
struct Slice {
    double xa, xb, ya, yb, sa, ca, alpha, b, l, area, W, xg, yg, u;
    std::vector<int> cand;  // materiales candidatos de la base (más de uno si cae en un contacto)
    int mat = -1;           // -1: aire
    double c = 0.0, tf = 0.0;
    bool tension = false;  // base de Hoek-Brown con σn' <= σt
    std::optional<double> tangent_at;  // σn' donde se tomó la última tangente de Hoek-Brown
    double Np = 0.0, E = 0.0, X = 0.0;
    double Px = 0.0, Py = 0.0;  // fuerza horizontal externa hacia el pie (agua de la grieta) y la cota de su línea
    // agua encharcada sobre el terreno (R16): peso Qv hacia abajo y empuje Qh (+x hacia el pie), aplicados en (qx, qy)
    double Qv = 0.0, Qh = 0.0, qx = 0.0, qy = 0.0;
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
        if (g.piezo) {
            t.u = s.water_unit_weight * std::max(interp(*g.piezo, xm) - ym, 0.0);
            // p = γw·(y_piezo - y_terreno)⁺ es lineal en la tajada (los cortes piezométrica-terreno son bordes): la
            // resultante p_med·b por la normal del terreno va en el centroide del trapecio de presiones
            auto p = [&](double x) {
                const double d = interp(*g.piezo, x) - interp(g.ground, x);
                return d > kTol ? s.water_unit_weight * d : 0.0;
            };
            const double pa = p(xa), pb = p(xb);
            if (pa + pb > 0.0) {
                t.Qv = 0.5 * (pa + pb) * t.b;
                t.Qh = t.Qv * (interp(g.ground, xb) - interp(g.ground, xa)) / t.b;  // pendiente < 0 en la cara: hacia la masa
                t.qx = xa + t.b * (pa + 2.0 * pb) / (3.0 * (pa + pb));
                t.qy = interp(g.ground, t.qx);
            }
        } else {
            double ru = 0.0;
            for (int m : t.cand) ru = std::max(ru, s.materials[m].ru);
            t.u = ru * W / t.b;
        }
        const auto& m = s.materials[t.mat];
        if (m.model == StrengthModel::MohrCoulomb) {
            t.c = m.cohesion;
            t.tf = std::tan(m.friction_deg * kPi / 180.0);
        }
    }
    return t;
}

struct Strength {
    double c, tf;
    bool tension;
};

/// c y tan φ tangentes a la envolvente de Balmer en σn'; σn' <= σt (o un punto sin tangente finita): sin resistencia.
inline Strength hb_tangent(const LeMaterial& m, double sn) {
    const HbParams& p = *m.hb;
    const double sci = *m.sigma_ci, st = hb_tensile(sci, p);
    if (!(sn > st)) return {0.0, 0.0, true};
    // σn(σ3) crece con σ3 y σn(σ3) >= σ3 para σ3 >= 0: la raíz está en [σt, max(σn', 0)]
    double lo = st, hi = std::max(sn, 0.0);
    for (int k = 0; k < 200 && hi - lo > 1e-15 * (std::fabs(lo) + std::fabs(hi)); ++k) {
        const double mid = 0.5 * (lo + hi);
        (hb_normal_shear(mid, sci, p).sigma_n_mpa < sn ? lo : hi) = mid;
    }
    const NormalShear ns = hb_normal_shear(hi, sci, p);
    const double k = 1.0 + p.a * p.mb * std::pow(std::max(0.0, p.mb * hi / sci + p.s), p.a - 1.0);
    const double tf = (k - 1.0) / (2.0 * std::sqrt(k)), c = ns.tau_mpa - ns.sigma_n_mpa * tf;
    if (!std::isfinite(tf) || !std::isfinite(c)) return {0.0, 0.0, true};
    return {c, tf, false};
}

inline bool any_hb(const LeSection& s) {
    for (const auto& m : s.materials)
        if (m.model == StrengthModel::HoekBrown) return true;
    return false;
}

/// Resistencia de la base en el σn' de la iteración: el candidato más débil por τ (más de uno si cae en un contacto) y,
/// con Hoek-Brown, las tangentes en ese σn'. Mohr-Coulomb compara con σn' >= 0, como en la tarea 1.
inline void choose(std::vector<Slice>& sl, const LeSection& s) {
    for (auto& t : sl) {
        if (t.cand.empty()) continue;
        if (t.cand.size() < 2 && s.materials[t.cand.front()].model == StrengthModel::MohrCoulomb) continue;
        const double sn = t.Np / t.l;
        double best = std::numeric_limits<double>::infinity();
        for (int m : t.cand) {
            const auto& mm = s.materials[m];
            Strength k{};
            double tau = 0.0;
            if (mm.model == StrengthModel::HoekBrown) {
                // la tangente queda sobre la envolvente cóncava: el σn' linealizado puede saltar bajo σt sin estar en
                // tracción; entonces el punto de la tangente baja solo hasta la mitad del camino a σt
                double at = sn;
                const double st = hb_tensile(*mm.sigma_ci, *mm.hb);
                if (sn <= st && t.tangent_at && *t.tangent_at > st) at = st + 0.5 * (*t.tangent_at - st);
                k = hb_tangent(mm, at);
                if (m == t.cand.front()) t.tangent_at = at;
                tau = k.tension ? 0.0 : k.c + sn * k.tf;
            } else {
                k = {mm.cohesion, std::tan(mm.friction_deg * kPi / 180.0), false};
                tau = mm.cohesion + std::max(sn, 0.0) * k.tf;
            }
            if (tau < best) {
                best = tau;
                t.mat = m;
                t.c = k.c;
                t.tf = k.tf;
                t.tension = k.tension;
            }
        }
    }
}

/// Mayor cambio de σn' en las bases de Hoek-Brown, relativo a su σci; deja los σn' actuales en prev.
inline double hb_change(const std::vector<Slice>& sl, const LeSection& s, std::vector<double>& prev) {
    double d = 0.0;
    for (std::size_t i = 0; i < sl.size(); ++i) {
        const auto& t = sl[i];
        const double sn = t.Np / t.l;
        if (t.mat >= 0 && s.materials[t.mat].model == StrengthModel::HoekBrown)
            d = std::max(d, std::fabs(sn - prev[i]) / *s.materials[t.mat].sigma_ci);
        prev[i] = sn;
    }
    return d;
}
inline std::vector<double> normal_stresses(const std::vector<Slice>& sl) {
    std::vector<double> v;
    for (const auto& t : sl) v.push_back(t.Np / t.l);
    return v;
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
            require_positive(m.hb->mb, n + ".hb.mb");
            require_in_range(m.hb->s, 0.0, 1.0, n + ".hb.s");
            require_positive(m.hb->a, n + ".hb.a");
            require(m.hb->a <= 1.0, n + ".hb.a", "must be within (0, 1]", m.hb->a);
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
    require(o.tolerance <= 1e-3, "tolerance", "must be at most 1e-3", o.tolerance);
    require(o.max_iterations >= 1, "max_iterations", "must be at least 1", o.max_iterations);
    if (o.function == InterSliceFunction::Points) {
        const auto& fp = o.function_points;
        if (fp.size() < 2) fail("function_points", "needs at least two points with the Points function");
        bool positive = false;
        for (std::size_t i = 0; i < fp.size(); ++i) {
            const std::string n = at("function_points", i);
            require_in_range(fp[i].x, 0.0, 1.0, n + ".x");
            require_non_negative(fp[i].y, n + ".y");
            if (i > 0) require(fp[i].x > fp[i - 1].x, n + ".x", "must be strictly increasing", fp[i].x);
            positive = positive || fp[i].y > 0.0;
        }
        require(fp.front().x == 0.0, "function_points[0].x", "must be 0", fp.front().x);
        require(fp.back().x == 1.0, at("function_points", fp.size() - 1) + ".x", "must be 1", fp.back().x);
        if (!positive) fail("function_points", "needs some f > 0");
    }
}

struct Built {
    std::vector<Slice> slices;
    bool reflected = false, air = false;
    Point2 origin{};
    std::vector<std::string> notes;
};

inline Built build(const LeSection& s, const SlipSurface& f, int n_slices) {
    const Geo g0 = make_geo(s, f, false);
    Mass m = find_mass(g0);
    const double yl = interp(g0.ground, m.xl), yr = interp(g0.ground, m.xr);
    if (std::fabs(yl - yr) <= kTol)
        fail("surface", "is level at both ends of the sliding mass: the face direction is undefined");
    Built out;
    out.origin = local_origin(s);
    out.reflected = yr > yl;  // la superficie sube: la cara mira a la izquierda
    const Geo g = make_geo(s, f, out.reflected);
    if (out.reflected) m = find_mass(g);
    out.air = m.air;
    double xl = m.xl;
    const double xr = m.xr;
    // grieta: la línea a zc bajo el terreno corta la superficie de falla; el primer corte desde la cresta (izquierda)
    double crack_force = 0.0, crack_y = 0.0;
    if (s.crack) {
        const double zc = s.crack->depth_m;
        Poly line = g.ground;
        for (auto& q : line) q.y -= zc;
        double xk = std::numeric_limits<double>::infinity();
        if (zc > 0.0)
            for (double x : slip_cuts(g, line))
                if (x > xl - kTol && x < xr - kTol) xk = std::min(xk, x);
        if (std::isfinite(xk) && xk <= xl + kTol) {
            // grieta casi nula: el corte del lado de la cresta cae sobre xl y el siguiente sería el del pie
            out.notes.push_back("tension crack too shallow to cut the slip surface inside the mass: crack ignored");
        } else if (std::isfinite(xk)) {
            xl = xk;
            const double hw = s.crack->water_fill * zc;
            crack_force = 0.5 * s.water_unit_weight * hw * hw;
            crack_y = slip_y(g, xk) + hw / 3.0;
        } else {
            out.notes.push_back("tension crack does not reach the slip surface: crack ignored");
        }
    }
    for (std::size_t k = 0; k < g.bottoms.size(); ++k)
        if (!g.bottoms[k].empty() && !covers(g.bottoms[k], xl, xr))
            fail(at("layers", k) + ".bottom", "does not cover the sliding mass");
    if (g.piezo && !covers(*g.piezo, xl, xr)) fail("piezometric", "does not cover the sliding mass");
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
    if (g.piezo) lines.push_back(&*g.piezo);
    for (const Poly* p : lines) {
        for (const auto& q : *p)
            if (inside(q.x)) xs.push_back(q.x);
        for (double x : slip_cuts(g, *p))
            if (inside(x)) xs.push_back(x);
    }
    if (g.piezo)  // donde la piezométrica sale sobre el terreno empieza el agua encharcada
        for (double x : poly_cuts(*g.piezo, g.ground))
            if (inside(x)) xs.push_back(x);
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
    out.slices.front().Px = crack_force;
    out.slices.front().Py = crack_y;
    return out;
}

inline LeSlice to_public(const Slice& t, const Slice* left, bool reflected, Point2 o, const LeSection& s) {
    LeSlice out{};
    out.alpha_deg = t.alpha * 180.0 / kPi;
    out.base_length = t.l;
    out.weight = t.W;
    out.pore_pressure = t.u;
    out.cohesion = t.mat >= 0 ? t.c : 0.0;
    out.friction_deg = t.mat < 0 ? 0.0
                       : s.materials[t.mat].model == StrengthModel::HoekBrown ? std::atan(t.tf) * 180.0 / kPi
                                                                              : s.materials[t.mat].friction_deg;
    out.normal_force = t.Np;
    out.shear_strength = t.c * t.l + t.Np * t.tf;
    out.material = t.mat;
    if (reflected) {
        out.x_left = o.x - t.xb;
        out.x_right = o.x - t.xa;
        out.base_y_left = t.yb + o.y;
        out.base_y_right = t.ya + o.y;
        out.interslice_normal_right = left ? left->E : 0.0;
        out.interslice_shear_right = left ? left->X : 0.0;
    } else {
        out.x_left = t.xa + o.x;
        out.x_right = t.xb + o.x;
        out.base_y_left = t.ya + o.y;
        out.base_y_right = t.yb + o.y;
        out.interslice_normal_right = t.E;
        out.interslice_shear_right = t.X;
    }
    return out;
}

inline std::vector<LeSlice> to_public(const std::vector<Slice>& sl, bool reflected, Point2 o, const LeSection& s) {
    std::vector<LeSlice> out;
    for (std::size_t i = 0; i < sl.size(); ++i)
        out.push_back(to_public(sl[i], i ? &sl[i - 1] : nullptr, reflected, o, s));
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
            return {"Janbu-Corrected", Verification::Secondary,
                    slide + "; f0 = 1 + b1 (d/L - 1.4 (d/L)^2), b1 0.69/0.50/0.31 (Abramson et al. 2002, not read); "
                            "Janbu (1973) not read"};
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
    bool explained = false;  // FS vacío con su nota (masa hacia atrás, polilínea recta): no es «did not converge»
    int bad_m_alpha = 0;     // tajadas con mα <= 0 en el último iterado de un cálculo que no convergió
    std::vector<std::string> notes;
};

/// Cargas de la tajada: vertical (peso más agua encharcada) y horizontal hacia el pie (sismo, grieta y empuje del agua).
inline double vertical_load(const Slice& t) { return t.W + t.Qv; }
inline double horizontal_load(const Slice& t, double kh) { return kh * t.W + t.Px + t.Qh; }
/// Fuerza motora a lo largo de la base sin fuerzas entre tajadas.
inline double driving_force(const Slice& t, double kh) {
    return vertical_load(t) * t.sa + horizontal_load(t, kh) * t.ca;
}
/// N' de la base por equilibrio vertical sin cortante entre tajadas (Bishop y Janbu).
inline double vertical_normal(const Slice& t, double F) {
    const double ma = t.ca + t.sa * t.tf / F;
    return (vertical_load(t) - t.u * t.b - t.c * t.l * t.sa / F) / ma;
}
/// N' sin fuerzas entre tajadas (la del Ordinario): peso, sismo y fuerzas externas proyectados sobre la normal.
inline double ordinary_normal(const Slice& t, double kh) {
    return vertical_load(t) * t.ca - horizontal_load(t, kh) * t.sa - t.u * t.l;
}
inline void ordinary_normals(std::vector<Slice>& sl, double kh) {
    for (auto& t : sl) t.Np = std::max(0.0, ordinary_normal(t, kh));
}
/// Ninguna tajada resiste: con fuerza motora, FS = 0.
inline bool no_strength(const std::vector<Slice>& sl) {
    for (const auto& t : sl)
        if (t.c > 0.0 || t.tf > 0.0) return false;
    return true;
}
inline int m_alpha_count(const std::vector<Slice>& sl, double F, double limit, bool or_equal) {
    int k = 0;
    for (const auto& t : sl) {
        const double ma = t.ca + t.sa * t.tf / F;
        if (t.mat >= 0 && (or_equal ? ma <= limit : ma < limit)) ++k;
    }
    return k;
}
inline Solve backward() {
    Solve r;
    r.explained = true;
    r.notes.push_back(kBackward);
    return r;
}

inline Solve ordinary(std::vector<Slice>& sl, const LeSection& s) {
    ordinary_normals(sl, s.kh);
    choose(sl, s);
    double num = 0.0, den = 0.0;
    int clipped = 0;
    for (const auto& t : sl) {
        num += t.c * t.l + t.Np * t.tf;
        den += driving_force(t, s.kh);
        clipped += t.mat >= 0 && ordinary_normal(t, s.kh) < 0.0;
    }
    if (!(den > 0.0)) {
        if (std::none_of(sl.begin(), sl.end(), [](const Slice& t) { return t.Qv > 0.0; })) return backward();
        Solve r;  // talud sumergido: la suma sobre las bases ignora el agua entre tajadas
        r.explained = true;
        r.notes.push_back("Ordinary: no driving force along the bases with the ponded water load (the method neglects "
                          "the water between slices)");
        return r;
    }
    Solve r;
    if (sl.front().Px > 0.0)
        r.notes.push_back("Ordinary: the crack water force acts on the crack slice, projected on its base like the "
                          "seismic force");
    r.iterations = 1;
    r.F = num / den;
    r.converged = true;
    if (clipped > 0)
        r.notes.push_back("effective normal force below zero in " + std::to_string(clipped) +
                          " slices: friction taken as zero there");
    return r;
}

/// Centro de momentos de Bishop: el del círculo o, con polilínea, el del círculo por los extremos y el punto más
/// alejado bajo la cuerda que los une (R7). Coordenadas locales, así x² + y² no pierde precisión.
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
    // circuncentro con a como origen
    const double bx = b.x - a.x, by = b.y - a.y, cx = c.x - a.x, cy = c.y - a.y;
    const double D = 2.0 * (bx * cy - by * cx), b2 = bx * bx + by * by, c2 = cx * cx + cy * cy;
    return Point2{a.x + (cy * b2 - by * c2) / D, a.y + (bx * c2 - cx * b2) / D};
}

/// Bishop (momentos respecto de O con brazos exactos de la cuerda) o Janbu simplificado (fuerzas horizontales).
inline Solve bishop_janbu(std::vector<Slice>& sl, const LeSection& s, const Geo& g, const LeOptions& o, bool bishop) {
    Solve r;
    const double kh = s.kh;
    std::vector<double> aS(sl.size(), 0.0), aN(sl.size(), 0.0);
    double driving = 0.0;
    if (bishop) {
        const auto O = bishop_centre(g, sl);
        if (!O) {
            r.explained = true;
            r.notes.push_back("Bishop needs a curved slip surface: the polyline is straight");
            return r;
        }
        for (std::size_t i = 0; i < sl.size(); ++i) {
            const auto& t = sl[i];
            const double mx = 0.5 * (t.xa + t.xb) - O->x, my = 0.5 * (t.ya + t.yb) - O->y;
            aS[i] = -(mx * t.sa + my * t.ca);
            aN[i] = mx * t.ca - my * t.sa;
            driving += t.W * (O->x - t.xg) + kh * t.W * (O->y - t.yg) + t.Px * (O->y - t.Py) +
                       t.Qv * (O->x - t.qx) + t.Qh * (O->y - t.qy);
        }
    } else {
        for (const auto& t : sl) driving += vertical_load(t) * t.sa / t.ca + horizontal_load(t, kh);
    }
    if (!(driving > 0.0)) return backward();
    if (bishop && g.polyline)
        r.notes.push_back("Bishop on a non-circular surface: moments about the centre of the circle through the ends "
                          "and the deepest point");
    ordinary_normals(sl, kh);
    choose(sl, s);
    if (no_strength(sl)) {
        for (auto& t : sl) t.Np = vertical_normal(t, std::numeric_limits<double>::infinity());
        r.F = 0.0;
        r.converged = true;
        r.iterations = 1;
        return r;
    }
    // arranque en el FS del Ordinario: con φ alto, partir de 1 deja mα <= 0 en el primer iterado
    double F = 1.0, on = 0.0, od = 0.0;
    for (const auto& t : sl) {
        on += t.c * t.l + t.Np * t.tf;
        od += driving_force(t, kh);
    }
    if (od > 0.0 && on / od > 0.0 && std::isfinite(on / od)) F = on / od;
    std::vector<double> prev = normal_stresses(sl);
    for (r.iterations = 1; r.iterations <= o.max_iterations; ++r.iterations) {
        choose(sl, s);
        for (auto& t : sl) t.Np = vertical_normal(t, F);
        double num = 0.0, den = driving;
        for (std::size_t i = 0; i < sl.size(); ++i) {
            const auto& t = sl[i];
            const double S = t.c * t.l + t.Np * t.tf;
            if (bishop) {
                num += aS[i] * S;
                den += aN[i] * (t.Np + t.u * t.l);
            } else {
                num += S / t.ca;
            }
        }
        const double Fn = num / den;
        if (!(den > 0.0) || !(Fn > 0.0) || !std::isfinite(Fn)) {
            r.bad_m_alpha = m_alpha_count(sl, F, 0.0, true);
            return r;
        }
        const double dsn = hb_change(sl, s, prev);
        if (std::fabs(Fn - F) < o.tolerance && dsn < o.tolerance) {
            r.F = Fn;
            r.converged = true;
            for (auto& t : sl) t.Np = vertical_normal(t, Fn);
            return r;
        }
        F = Fn;
    }
    r.iterations = o.max_iterations;
    r.bad_m_alpha = m_alpha_count(sl, F, 0.0, true);
    return r;
}

inline double interslice_f(const LeOptions& o, bool spencer, double t, bool reflected) {
    if (spencer || o.function == InterSliceFunction::Constant) return 1.0;
    if (o.function == InterSliceFunction::HalfSine) return std::sin(kPi * t);
    return interp(o.function_points, reflected ? 1.0 - t : t);
}

/// Spencer y Morgenstern-Price. Para cada λ, F es la raíz con intervalo de la ecuación de fuerzas (recurrencia de
/// Zhu et al. 2005); λ es la raíz de la ecuación de momentos g, buscada barriendo desde 0 hacia afuera mientras |g|
/// baje hasta un cambio de signo, y cerrada con regula falsi (Illinois) alternada con bisección. kh entra en R, T y el
/// momento (brazo del centroide).
inline Solve gle(std::vector<Slice>& sl, const LeSection& s, const LeOptions& o, bool spencer, bool reflected,
                 double F0, const std::vector<Slice>* seed = nullptr) {
    Solve r;
    const std::size_t n = sl.size();
    const double kh = s.kh, x0 = sl.front().xa, x1 = sl.back().xb;
    std::vector<double> fb(n), R(n), T(n), Phi(n);
    for (std::size_t i = 0; i < n; ++i) fb[i] = interslice_f(o, spencer, (sl[i].xb - x0) / (x1 - x0), reflected);
    ordinary_normals(sl, kh);
    // con Hoek-Brown, las primeras tangentes salen de las N' de Bishop convergido si las hay (las del Ordinario dan
    // tangentes casi verticales en las tajadas delgadas y Spencer no encuentra λ)
    if (seed && any_hb(s))
        for (std::size_t i = 0; i < n; ++i) sl[i].Np = (*seed)[i].Np;
    choose(sl, s);
    double driving = 0.0;
    double horizontal = 0.0;  // fuerza motora horizontal de Janbu: ahí el agua entre tajadas se cancela
    bool pond = false;
    for (const auto& t : sl) {
        driving += driving_force(t, kh);
        horizontal += vertical_load(t) * t.sa / t.ca + horizontal_load(t, kh);
        pond = pond || t.Qv > 0.0;
    }
    // con agua encharcada la suma sobre las bases no cierra el agua entre tajadas (talud sumergido: < 0 con la masa
    // empujada hacia la cara); se decide con la horizontal
    if (!(driving > 0.0) && !(pond && horizontal > 0.0)) return backward();
    if (no_strength(sl)) {
        for (auto& t : sl) t.Np = ordinary_normal(t, kh);
        r.F = 0.0;
        r.lambda = 0.0;
        r.converged = true;
        r.iterations = 1;
        return r;
    }
    auto phi = [&](const Slice& t, double f, double lam, double F) {
        return (t.sa - lam * f * t.ca) * t.tf + (t.ca + lam * f * t.sa) * F;
    };
    double last_F = F0;
    const double F_cap = 1e3 * F0;  // F0 es el de Bishop (o 1): techo del intervalo de F
    // residuo de la ecuación de fuerzas, recurrencia de Zhu: e = E Φ del último borde = F Σ T Π Ψ - Σ R Π Ψ, que debe
    // ser nulo; d = Σ T Π Ψ
    auto force_residual = [&](double lam, double F, double& d) {
        double e = 0.0;
        d = 0.0;
        for (std::size_t i = 0; i < n; ++i) {
            const double psi = i ? phi(sl[i], fb[i - 1], lam, F) / phi(sl[i - 1], fb[i - 1], lam, F) : 0.0;
            e = psi * e + F * T[i] - R[i];
            d = psi * d + T[i];
        }
        return e;
    };
    // F de la ecuación de fuerzas para un λ dado: raíz de e(F) con intervalo y cambio de signo. e es continua mientras
    // ninguna Φ de los bordes (denominadores de Ψ) cruce cero; Φ es lineal en F, así que ese dominio es un intervalo,
    // que se corta a (0, 1e3 F_Bishop]. El intervalo se abre desde el F de arranque hacia los dos lados con pasos que
    // se duplican y se cierra con Illinois alternado con bisección. Sin raíz (o con Σ T Π Ψ <= 0 en ella), el λ no sirve.
    auto force_F = [&](double lam, double F) -> std::optional<double> {
        double lo = 0.0, hi = F_cap;
        for (std::size_t i = 0; i + 1 < n; ++i) {
            const double a = (sl[i].sa - lam * fb[i] * sl[i].ca) * sl[i].tf, b = sl[i].ca + lam * fb[i] * sl[i].sa;
            if (b > 0.0) lo = std::max(lo, -a / b);
            else if (b < 0.0) hi = std::min(hi, -a / b);
            else if (!(a > 0.0)) return std::nullopt;
        }
        const double pad = 1e-12 * std::max(1.0, hi);
        lo += pad;
        hi -= pad;
        if (!(hi > lo)) return std::nullopt;
        double d = 0.0;
        auto ev = [&](double x) {
            ++r.iterations;
            return force_residual(lam, x, d);
        };
        const double xs = std::clamp(F, lo, hi);
        const double es = ev(xs);
        if (!std::isfinite(es)) return std::nullopt;
        double a = xs, ea = es, b = xs, eb = es;
        if (es != 0.0) {
            // pasos desde xs que se duplican, alternando arriba y abajo, hasta el primer cambio de signo
            double up = xs, eu = es, dn = xs, edn = es, step = 0.02 * std::max(xs, 1e-3 * F0);
            bool found = false;
            for (int k = 0; k < 64 && !found && (up < hi || dn > lo); ++k, step *= 2.0) {
                if (up < hi) {
                    const double x = std::min(xs + step, hi), ex = ev(x);
                    if (!std::isfinite(ex)) return std::nullopt;
                    if ((ex > 0.0) != (eu > 0.0) || ex == 0.0) {
                        a = up, ea = eu, b = x, eb = ex, found = true;
                        break;
                    }
                    up = x, eu = ex;
                }
                if (dn > lo) {
                    const double x = std::max(xs - step, lo), ex = ev(x);
                    if (!std::isfinite(ex)) return std::nullopt;
                    if ((ex > 0.0) != (edn > 0.0) || ex == 0.0) {
                        a = x, ea = ex, b = dn, eb = edn, found = true;
                        break;
                    }
                    dn = x, edn = ex;
                }
            }
            if (!found) return std::nullopt;
            // Illinois alternado con bisección: el intervalo se reduce al menos a la mitad cada dos pasos
            double fa = ea, fbv = eb;
            int keep = 0;
            const double tol = std::min(o.tolerance, 1e-9) * std::max(1.0, b);
            for (int it = 0; eb != 0.0 && ea != 0.0 && b - a > tol; ++it) {
                if (it >= o.max_iterations) return std::nullopt;
                double x = 0.5 * (a + b);
                if (it % 2 == 0 && fbv != fa) {
                    const double rf = (a * fbv - b * fa) / (fbv - fa);
                    if (rf > a && rf < b) x = rf;
                }
                const double ex = ev(x);
                if (!std::isfinite(ex)) return std::nullopt;
                if (ex == 0.0) {
                    a = b = x, ea = eb = 0.0;
                    break;
                }
                if ((ex > 0.0) == (ea > 0.0)) {
                    a = x, ea = fa = ex;
                    if (keep == 1) fbv *= 0.5;
                    keep = 1;
                } else {
                    b = x, eb = fbv = ex;
                    if (keep == -1) fa *= 0.5;
                    keep = -1;
                }
            }
        }
        const double root = std::fabs(ea) <= std::fabs(eb) ? a : b;
        force_residual(lam, root, d);
        if (!(d > 0.0) || !(root > 0.0)) return std::nullopt;
        last_F = root;
        return root;
    };
    // fuerzas entre tajadas (borde derecho; E = 0 en los extremos) y residuo de momentos λ Σ b (f E + f E) - Σ [...]
    auto residual = [&](double lam, double F) {
        double EPhi = 0.0;
        for (std::size_t i = 0; i + 1 < n; ++i) {
            Phi[i] = phi(sl[i], fb[i], lam, F);
            const double psi = i ? phi(sl[i], fb[i - 1], lam, F) / Phi[i - 1] : 0.0;
            EPhi = psi * EPhi + F * T[i] - R[i];
            sl[i].E = EPhi / Phi[i];
        }
        sl[n - 1].E = 0.0;
        double num = 0.0, den = 0.0;
        for (std::size_t i = 0; i < n; ++i) {
            const auto& t = sl[i];
            const double El = i ? sl[i - 1].E : 0.0, fl = i ? fb[i - 1] : 0.0;
            const double xm = 0.5 * (t.xa + t.xb), ym = 0.5 * (t.ya + t.yb), hc = t.yg - ym;  // brazos desde el medio de la base
            num += t.b * (t.E + El) * std::tan(t.alpha) + 2.0 * kh * t.W * hc + 2.0 * t.Px * (t.Py - ym) +
                   2.0 * t.Qv * (t.qx - xm) + 2.0 * t.Qh * (t.qy - ym);
            den += t.b * (fb[i] * t.E + fl * El);
        }
        return lam * den - num;
    };
    struct Pt {
        double lam, F, g;
    };
    auto eval = [&](double lam, double F) -> std::optional<Pt> {
        ++r.iterations;
        const auto f = force_F(lam, F);
        if (!f) return std::nullopt;
        const double g = residual(lam, *f);
        if (!std::isfinite(g)) return std::nullopt;
        return Pt{lam, *f, g};
    };
    auto fail = [&] {
        r.F.reset();
        r.lambda.reset();
        r.converged = false;
        r.bad_m_alpha = m_alpha_count(sl, last_F, 0.0, true);
        return r;
    };
    // mínimo de |g| entre lo y hi (sección áurea), con mid del lado de lo que se cruza; si en el camino g cambia de
    // signo respecto de mid, devuelve ese intervalo
    auto dip = [&](const Pt& lo, const Pt& mid, const Pt& hi) -> std::optional<std::pair<Pt, Pt>> {
        const double sg = mid.g > 0.0 ? 1.0 : -1.0, gr = 0.5 * (std::sqrt(5.0) - 1.0);
        double x0 = lo.lam, x3 = hi.lam, x1 = x3 - gr * (x3 - x0), x2 = x0 + gr * (x3 - x0);
        auto e1 = eval(x1, mid.F);
        auto e2 = e1 ? eval(x2, e1->F) : std::nullopt;
        for (int it = 0; it < 40 && e1 && e2; ++it) {
            if (sg * e1->g <= 0.0) return std::pair<Pt, Pt>{mid, *e1};
            if (sg * e2->g <= 0.0) return std::pair<Pt, Pt>{mid, *e2};
            if (std::fabs(x3 - x0) <= o.tolerance) break;
            if (sg * e1->g < sg * e2->g) {
                x3 = x2, x2 = x1, e2 = e1, x1 = x3 - gr * (x3 - x0);
                e1 = eval(x1, e2->F);
            } else {
                x0 = x1, x1 = x2, e1 = e2, x2 = x0 + gr * (x3 - x0);
                e2 = eval(x2, e1->F);
            }
        }
        return std::nullopt;
    };
    const bool hb = any_hb(s);
    std::vector<double> prev = normal_stresses(sl);
    std::optional<double> F_pass;
    const int passes = hb ? o.max_iterations : 3;  // Mohr-Coulomb: hasta 3 pasadas por el material de los contactos
    for (int pass = 0; pass < passes; ++pass) {
        for (std::size_t i = 0; i < n; ++i) {
            const auto& t = sl[i];
            R[i] = ordinary_normal(t, kh) * t.tf + t.c * t.l;
            T[i] = driving_force(t, kh);
        }
        const auto p0 = eval(0.0, F0);
        if (!p0) return fail();
        // barrido de λ desde 0 hacia afuera (primero el lado positivo) hasta un cambio de signo
        std::optional<Pt> a, b;
        if (p0->g == 0.0) {
            a = b = p0;
        } else {
            Pt prev[2] = {*p0, *p0}, before[2] = {*p0, *p0}, first[2] = {*p0, *p0};
            bool alive[2] = {true, true}, moved[2] = {false, false};
            for (int k = 1; k <= 40 && !a && (alive[0] || alive[1]); ++k)
                for (int side = 0; side < 2 && !a; ++side) {
                    if (!alive[side]) continue;
                    // si la ecuación de fuerzas se rompe en el paso, se acerca con pasos partidos a la mitad
                    const double target = (side ? -0.1 : 0.1) * k;
                    double step = target - prev[side].lam;
                    for (int h = 0; h <= 6 && !a; ) {
                        const auto q = eval(prev[side].lam + step, prev[side].F);
                        if (!q) {
                            step *= 0.5;
                            ++h;
                        } else if ((q->g > 0.0) != (prev[side].g > 0.0)) {
                            a = prev[side];
                            b = q;
                        } else if (std::fabs(q->g) > std::fabs(prev[side].g)) {
                            // |g| vuelve a subir sin cambio de signo: las raíces más allá resultaron espurias (λ cerca
                            // de -2, F de 0.2 con Bishop 3.7 y un tercio de las bases bajo el vértice de Mohr-Coulomb,
                            // ACADS 3(a)); si venía bajando, dos raíces juntas pueden quedar entre las muestras y se
                            // busca el mínimo de |g| entre before y q
                            if (moved[side]) {
                                if (const auto c = dip(before[side], prev[side], *q)) {
                                    a = c->first;
                                    b = c->second;
                                }
                            } else {
                                first[side] = *q;
                            }
                            alive[side] = false;
                            break;
                        } else {
                            before[side] = prev[side];
                            prev[side] = *q;
                            moved[side] = true;
                            if (std::fabs(prev[side].lam - target) <= 1e-12) break;
                        }
                        if (h > 6) alive[side] = false;
                    }
                }
            // |g| subió en el primer paso de los dos lados: el mínimo está entre -0.1 y 0.1
            if (!a && !moved[0] && !moved[1] && first[0].lam != 0.0 && first[1].lam != 0.0)
                if (const auto c = dip(first[1], *p0, first[0])) {
                    a = c->first;
                    b = c->second;
                }
        }
        if (!a) return fail();
        // Illinois alternado con bisección: el intervalo se reduce al menos a la mitad cada dos pasos
        double ga = a->g, gb = b->g;
        int keep = 0;
        for (int it = 0; it < o.max_iterations && std::fabs(b->lam - a->lam) > o.tolerance; ++it) {
            double lam = 0.5 * (a->lam + b->lam);
            if (it % 2 == 0 && gb != ga) {
                const double rf = (a->lam * gb - b->lam * ga) / (gb - ga);
                if (rf > std::min(a->lam, b->lam) && rf < std::max(a->lam, b->lam)) lam = rf;
            }
            const auto q = eval(lam, std::fabs(a->g) < std::fabs(b->g) ? a->F : b->F);
            if (!q) return fail();
            if (q->g == 0.0) {
                a = b = q;
                break;
            }
            if ((q->g > 0.0) == (a->g > 0.0)) {
                a = q;
                ga = q->g;
                if (keep == 1) gb *= 0.5;
                keep = 1;
            } else {
                b = q;
                gb = q->g;
                if (keep == -1) ga *= 0.5;
                keep = -1;
            }
        }
        if (std::fabs(b->lam - a->lam) > o.tolerance) return fail();
        const Pt best = std::fabs(a->g) <= std::fabs(b->g) ? *a : *b;
        r.F = best.F;
        r.lambda = best.lam;
        residual(best.lam, best.F);
        // N' con las fuerzas entre tajadas, para el material de los contactos y la tabla
        for (std::size_t i = 0; i < n; ++i) {
            auto& t = sl[i];
            const double El = i ? sl[i - 1].E : 0.0, Xl = i ? best.lam * fb[i - 1] * El : 0.0;
            const double Xr = best.lam * fb[i] * t.E;
            t.Np = ordinary_normal(t, kh) - (El - t.E) * t.sa + (Xl - Xr) * t.ca;
            t.X = Xr;
        }
        r.converged = true;
        std::vector<int> mats;
        for (const auto& t : sl) mats.push_back(t.mat);
        choose(sl, s);
        bool same = true;
        for (std::size_t i = 0; i < n; ++i) same = same && mats[i] == sl[i].mat;
        if (hb) {
            const double dsn = hb_change(sl, s, prev);
            same = same && dsn < o.tolerance && F_pass && std::fabs(best.F - *F_pass) < o.tolerance;
            F_pass = best.F;
            if (!same && pass + 1 == passes) return fail();
        }
        if (same) break;
        F0 = best.F;
    }
    return r;
}

/// f0 de Janbu corregido: d es la mayor distancia de la superficie de falla bajo la cuerda entre sus extremos (en el
/// círculo, el punto más hondo exacto si cae dentro del arco), L el largo de la cuerda.
inline double janbu_f0(const Geo& g, const std::vector<Slice>& sl, const LeSection& s, std::vector<std::string>& notes) {
    const Point2 a{sl.front().xa, sl.front().ya}, c{sl.back().xb, sl.back().yb};
    const double L = std::hypot(c.x - a.x, c.y - a.y);
    auto dist = [&](double x, double y) { return ((c.y - a.y) * (x - a.x) - (c.x - a.x) * (y - a.y)) / L; };
    double d = 0.0;
    for (const auto& t : sl) d = std::max(d, dist(t.xb, t.yb));
    if (g.circle) {
        const Circle& k = *g.circle;
        const double nx = -(c.y - a.y) / L, ny = (c.x - a.x) / L;  // normal de la cuerda hacia arriba
        const double px = k.xc - k.radius * nx, py = k.yc - k.radius * ny;
        if (px > a.x && px < c.x && py <= k.yc) d = std::max(d, dist(px, py));
    }
    bool all_both = true, all_no_c = true, all_no_phi = true;
    for (const auto& t : sl) {
        if (t.mat < 0) continue;
        const auto& m = s.materials[t.mat];
        const bool hb = m.model == StrengthModel::HoekBrown;
        const bool has_c = hb || m.cohesion > 0.0, has_phi = hb || m.friction_deg > 0.0;
        all_both = all_both && has_c && has_phi;
        all_no_c = all_no_c && !has_c;
        all_no_phi = all_no_phi && !has_phi;
    }
    double b1 = 0.69;
    if (!all_both) {
        if (all_no_c) b1 = 0.50;
        else if (all_no_phi) b1 = 0.31;
        else notes.push_back("Janbu corrected: the bases mix cohesive and frictional materials, b1 = 0.69");
    }
    const double r = d / L;
    return 1.0 + b1 * (r - 1.4 * r * r);
}
}  // namespace le_detail

/// Tajadas de la masa deslizante (geometría, pesos, u y material de la base), sin fuerzas.
inline std::vector<LeSlice> make_slices(const LeSection& section, const SlipSurface& surface, int n_slices) {
    using namespace le_detail;
    LeOptions o;
    o.n_slices = n_slices;
    validate(section, surface, o);
    const Built b = build(section, surface, n_slices);
    return to_public(b.slices, b.reflected, b.origin, section);
}

inline LeResult le_factor_of_safety(const LeSection& section, const SlipSurface& surface, LeMethod method,
                                    const LeOptions& options = {}) {
    using namespace le_detail;
    validate(section, surface, options);
    Built b = build(section, surface, options.n_slices);
    const Geo g = make_geo(section, surface, b.reflected);
    auto& sl = b.slices;
    Solve r;
    std::optional<double> F_alpha;  // FS con el que se calcularon las N' (Janbu corregido: el simplificado)
    switch (method) {
        case LeMethod::Ordinary: r = ordinary(sl, section); break;
        case LeMethod::Bishop: r = bishop_janbu(sl, section, g, options, true); break;
        case LeMethod::JanbuSimplified: r = bishop_janbu(sl, section, g, options, false); break;
        case LeMethod::JanbuCorrected:
            r = bishop_janbu(sl, section, g, options, false);
            if (r.converged) {
                F_alpha = r.F;
                *r.F *= janbu_f0(g, sl, section, r.notes);
            }
            break;
        default: {
            auto tmp = sl;
            const Solve bi = bishop_janbu(tmp, section, g, options, true);
            r = gle(sl, section, options, method == LeMethod::Spencer, b.reflected,
                    bi.F && *bi.F > 0.0 ? *bi.F : 1.0, bi.converged ? &tmp : nullptr);
        }
    }
    LeResult out{std::nullopt, method, std::nullopt, r.iterations, r.converged, {}, 0.0, info(method), {}, b.notes};
    if (any_hb(section))
        out.info.source += "; Hoek-Brown by tangents to the Balmer envelope (Hoek et al. 2002), similarity checked "
                           "against Carranza-Torres & Hormazabal (2020)";
    out.notes.insert(out.notes.end(), r.notes.begin(), r.notes.end());
    if (section.piezometric)
        for (const auto& m : section.materials)
            if (m.ru > 0.0) {
                out.notes.push_back("piezometric line given: the ru of the materials is ignored");
                break;
            }
    if (std::any_of(sl.begin(), sl.end(), [](const Slice& t) { return t.Qv > 0.0; }))
        out.notes.push_back("ponded water above the ground surface modelled as a surface load");
    if (b.air)
        out.warnings.push_back("slip surface crosses the ground surface more than twice: the mass is taken between "
                               "the first and the last cut");
    // Hoek-Brown: una base que terminó bajo σt con la recta de su tangente (no con τ = 0) no tiene solución
    // consistente cerca (suele ser mα pequeño al pie): FS vacío, nunca un número a medias
    int tension = 0, at_limit = 0;
    if (r.converged)
        for (const auto& t : sl) {
            if (t.mat < 0 || section.materials[t.mat].model != StrengthModel::HoekBrown) continue;
            const auto& m = section.materials[t.mat];
            if (t.tension) ++tension;
            else if (t.Np / t.l <= hb_tensile(*m.sigma_ci, *m.hb)) ++at_limit;
        }
    if (at_limit > 0) {
        r.converged = false;
        out.converged = false;
        out.warnings.push_back(std::string(name(method)) + " did not converge (Hoek-Brown base at the tensile limit in " +
                               std::to_string(at_limit) + " slices)");
    } else if (!r.converged && !r.explained) {
        std::string w = std::string(name(method)) + " did not converge";
        if (r.bad_m_alpha > 0) w += " (m-alpha <= 0 in " + std::to_string(r.bad_m_alpha) + " slices)";
        out.warnings.push_back(w);
    }
    if (r.converged) {
        out.factor_of_safety = r.F;
        out.lambda = r.lambda;
        if (tension > 0)
            out.warnings.push_back("Hoek-Brown base in tension in " + std::to_string(tension) +
                                   " slices: shear strength taken as zero");
        if (method != LeMethod::Ordinary && *r.F > 0.0) {
            const int k = m_alpha_count(sl, F_alpha.value_or(*r.F), 0.2, false);
            if (k > 0)
                out.warnings.push_back("m-alpha below 0.2 in " + std::to_string(k) +
                                       " slices: results may be unreliable");
            int neg = 0;
            for (const auto& t : sl) neg += t.mat >= 0 && t.Np < 0.0;
            if (neg > 0) out.notes.push_back("effective normal force below zero in " + std::to_string(neg) + " slices");
        }
    }
    double thick = 0.0;
    for (const auto& t : sl) {
        out.sliding_mass_area += t.area;
        thick = std::max(thick, t.area / t.b);
    }
    const double width = sl.back().xb - sl.front().xa;
    const double chord = std::hypot(width, sl.back().yb - sl.front().ya);
    if (out.sliding_mass_area < 1e-6 * width * width || thick < 1e-6 * chord) out.notes.push_back("negligible sliding mass");
    out.slices = to_public(sl, b.reflected, b.origin, section);
    if (!out.factor_of_safety)
        for (auto& t : out.slices)
            t.normal_force = t.shear_strength = t.interslice_normal_right = t.interslice_shear_right = 0.0;
    return out;
}

}  // namespace rockmasspy
