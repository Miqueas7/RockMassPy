/**
 * @file slip_search.hpp
 * @brief Búsqueda de la superficie crítica: malla de centros con radios (circular) y búsqueda de bloque sobre una
 *        línea débil (no circular), las dos con afinado por búsqueda de patrón. Solo llama a le_factor_of_safety.
 *
 * Fuente (Secondary): Slide2 Verification Manual (2022), problemas 1, 3, 4 (ACADS 1(a), 1(c), 1(d)) y 7 (ACADS 3(a)).
 *
 * Marco: la búsqueda trabaja con la cara mirando a -x (el pie a la izquierda, como el problema 7 de Slide). Si los
 * extremos de la superficie dicen que la cara mira a +x, refleja (x -> -x) la sección, la malla y la línea débil, busca
 * y devuelve todo en las coordenadas del usuario; si los extremos están a la misma cota, no refleja. Así una sección
 * reflejada (con su malla o su línea débil reflejadas y los mismos ángulos) da el mismo FS bit a bit.
 *
 * Circular: centros en (nx + 1)(ny + 1) nudos; por centro, n_radii radios entre r_lo, el mayor de (tangente a la cota
 * más alta de la superficie menos 0.5) y (distancia del centro a la superficie, el primero que la toca), y r_hi, el
 * tangente a model_base_y (o a la cota más baja de la superficie si no hay base). Reparto por profundidad cuadrático,
 * r_k = r_lo + (r_hi - r_lo)(k / (n_radii - 1))²: la mitad de los radios cae en el primer cuarto del rango, para no
 * perder los mínimos someros. Multiarranque: semilla = el mejor círculo de cada centro; en orden de FS se eligen hasta
 * 5, saltando la que tenga el centro vecino de malla (8 vecinos) de una ya elegida o el radio a menos de un paso de
 * radio (el mayor de los dos contiguos) de una ya elegida; se afina cada una y manda la mejor.
 *
 * Bloque, convención de ángulos (la de Slide, antihorario desde +x, en el marco con la cara hacia -x): se toman dos
 * puntos de la línea débil (n_points posiciones igualmente espaciadas en x; el izquierdo antes que el derecho); desde
 * el izquierdo sale una recta hacia arriba y hacia el pie con ángulo en [left_angle_min, left_angle_max] ⊂ (90, 180)
 * (135-155: entre 25° y 45° sobre la horizontal), desde el derecho otra hacia arriba y hacia la cresta con ángulo en
 * [right_angle_min, right_angle_max] ⊂ (0, 90) (45-65 sobre la horizontal), hasta cortar la superficie. La polilínea
 * es (corte del pie, punto izquierdo, vértices de la línea débil entre ambos, punto derecho, corte de la cresta). Si la
 * cara mira a +x, «izquierdo» y «derecho» se leen en la sección reflejada: el izquierdo sigue siendo el lado del pie.
 *
 * Afinado: búsqueda de patrón con pasos 1, 0.25, 0.05 y 0.01 de la escala h (circular: el mayor paso de la malla, sobre
 * xc, yc y R; bloque: el espaciado de las posiciones, sobre los vértices interiores en x e y y los extremos en x,
 * deslizando sobre la superficie). Direcciones: con hasta 3 parámetros, las 26 de {-1, 0, 1}³ sin el origen; con más,
 * los ejes y las diagonales de cada par de parámetros (los valles diagonales atascan a una búsqueda solo por ejes).
 * Acepta una dirección si baja el FS en más de 1e-9. El paso 0.01 se agregó al 1-0.25-0.05 del plan: con 20 posiciones
 * en ACADS 3(a), 0.05 h = 0.17 m no deja bajar la base hasta el piso de la capa débil de 0.5 m. En el bloque, el afinado
 * descarta las polilíneas cuyos tramos extremos salen de los ángulos dados de su lado.
 *
 * Se descartan, y se cuentan en `discarded`, las superficies que no forman masa, las de masa menor que min_mass_area,
 * las que no convergen o dan FS vacío y las que traen el aviso «m-alpha below 0.2» (estas también en
 * `discarded_malpha`, con una nota). Si el centro crítico final no queda dentro de la malla (en su borde o fuera),
 * aviso «critical centre on the edge of the search grid». Los avisos de la crítica se copian a los de la búsqueda.
 * `top` guarda las 10 mejores de la malla o del bloque (y la afinada delante si mejora), en orden de FS. Todo es
 * determinista: mismo orden de evaluación, sin azar ni hilos.
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

#include "rockmasspy/limit_equilibrium.hpp"

namespace rockmasspy {

/// nx, ny: intervalos de la malla de centros; n_radii: radios por centro.
struct CircularGrid {
    double x_min = validation::unset, x_max = validation::unset, y_min = validation::unset, y_max = validation::unset;
    int nx = 20, ny = 20, n_radii = 11;
};

/// Ángulos en grados, antihorario desde +x en el marco con la cara hacia -x (ver la cabecera).
struct BlockSearch {
    std::vector<Point2> weak_line;
    int n_points = 20;
    double left_angle_min = 135.0, left_angle_max = 155.0, right_angle_min = 45.0, right_angle_max = 65.0;
    int n_angles = 5;
};

struct SearchOptions {
    LeMethod method = LeMethod::Bishop;
    LeOptions le;
    bool refine = true;
    double min_mass_area = 0.0;
};

struct SearchResult {
    LeResult best;        // FS vacío si ninguna superficie sirvió
    SlipSurface surface;  // la crítica, en coordenadas del usuario
    int evaluated = 0, discarded = 0, discarded_malpha = 0;  // discarded_malpha está incluido en discarded
    std::vector<std::pair<SlipSurface, double>> top;
    MethodInfo info;
    std::vector<std::string> warnings, notes;
};

namespace search_detail {
using le_detail::Poly;
constexpr std::size_t kTop = 10;
constexpr double kDeg = le_detail::kPi / 180.0;

inline LeSection mirrored(LeSection s) {
    s.surface = le_detail::mirror(s.surface);
    for (auto& l : s.layers)
        if (!l.bottom.empty()) l.bottom = le_detail::mirror(l.bottom);
    if (s.piezometric) s.piezometric = le_detail::mirror(*s.piezometric);
    return s;
}
inline SlipSurface mirrored(SlipSurface f) {
    if (f.circle) f.circle->xc = -f.circle->xc;
    if (f.polyline) f.polyline = le_detail::mirror(*f.polyline);
    return f;
}
/// La cara mira a +x: hay que reflejar para llegar al marco de la búsqueda.
inline bool faces_plus_x(const LeSection& s) { return s.surface.front().y > s.surface.back().y; }

inline void validate(const LeSection& s, const SearchOptions& o) {
    SlipSurface probe;
    probe.circle = Circle{0.0, 0.0, 1.0};  // solo para validar la sección y las opciones
    le_detail::validate(s, probe, o.le);
    validation::require_non_negative(o.min_mass_area, "min_mass_area");
    // un estrato corto descartaría en silencio cada superficie que lo cruce
    for (std::size_t k = 0; k < s.layers.size(); ++k)
        if (!s.layers[k].bottom.empty() && !le_detail::covers(s.layers[k].bottom, s.surface.front().x, s.surface.back().x))
            le_detail::fail(le_detail::at("layers", k) + ".bottom", "must cover the x range of the ground surface");
}

inline bool has_malpha(const LeResult& r) {
    for (const auto& w : r.warnings)
        if (w.find("m-alpha") != std::string::npos) return true;
    return false;
}

/// FS de una superficie, o vacío si se descarta. Los errores de geometría descartan; los de «not implemented», no.
struct Evaluator {
    const LeSection& section;
    const SearchOptions& options;
    int evaluated = 0, discarded = 0, discarded_malpha = 0;

    std::optional<double> reject() {
        ++evaluated;
        ++discarded;
        return std::nullopt;
    }

    std::optional<double> operator()(const SlipSurface& f) {
        ++evaluated;
        try {
            const LeResult r = le_factor_of_safety(section, f, options.method, options.le);
            if (r.factor_of_safety && r.converged && r.sliding_mass_area >= options.min_mass_area) {
                if (!has_malpha(r)) return r.factor_of_safety;
                ++discarded_malpha;
            }
        } catch (const std::invalid_argument& e) {
            if (std::string(e.what()).find("not implemented") != std::string::npos) throw;
        }
        ++discarded;
        return std::nullopt;
    }
};

using Top = std::vector<std::pair<SlipSurface, double>>;
inline void keep(Top& top, const SlipSurface& f, double F) {
    const auto it = std::upper_bound(top.begin(), top.end(), F, [](double v, const auto& p) { return v < p.second; });
    if (static_cast<std::size_t>(it - top.begin()) >= kTop) return;
    top.insert(it, {f, F});
    if (top.size() > kTop) top.pop_back();
}

/// Direcciones de la búsqueda de patrón: {-1, 0, 1}^n sin el origen si n <= 3; si no, ejes y diagonales por pares.
inline std::vector<std::vector<double>> directions(std::size_t n) {
    std::vector<std::vector<double>> out;
    if (n <= 3) {
        int total = 1;
        for (std::size_t i = 0; i < n; ++i) total *= 3;
        for (int code = 0; code < total; ++code) {
            std::vector<double> d(n);
            for (std::size_t i = 0, c = code; i < n; ++i, c /= 3) d[i] = static_cast<double>(c % 3) - 1.0;
            if (std::any_of(d.begin(), d.end(), [](double v) { return v != 0.0; })) out.push_back(d);
        }
        return out;
    }
    for (std::size_t i = 0; i < n; ++i)
        for (double s : {1.0, -1.0}) {
            std::vector<double> d(n, 0.0);
            d[i] = s;
            out.push_back(d);
        }
    for (std::size_t i = 0; i < n; ++i)
        for (std::size_t j = i + 1; j < n; ++j)
            for (double si : {1.0, -1.0})
                for (double sj : {1.0, -1.0}) {
                    std::vector<double> d(n, 0.0);
                    d[i] = si;
                    d[j] = sj;
                    out.push_back(d);
                }
    return out;
}

/// Búsqueda de patrón: en cada paso recorre las direcciones y acepta la primera mejora, hasta que ninguna mejora.
template <class Eval>
std::vector<double> pattern_search(std::vector<double> p, double& best, double h, Eval&& eval) {
    const auto dirs = directions(p.size());
    for (double step : {1.0, 0.25, 0.05, 0.01}) {
        bool improved = true;
        for (int it = 0; improved && it < 1000; ++it) {  // tope solo por seguridad
            improved = false;
            for (const auto& d : dirs) {
                auto q = p;
                for (std::size_t i = 0; i < q.size(); ++i) q[i] += d[i] * step * h;
                const auto F = eval(q);
                if (F && *F < best - 1e-9) {
                    best = *F;
                    p = std::move(q);
                    improved = true;
                }
            }
        }
    }
    return p;
}

inline double distance_to(const Poly& g, double x, double y) {
    double d = std::numeric_limits<double>::infinity();
    for (std::size_t i = 0; i + 1 < g.size(); ++i) {
        const double ex = g[i + 1].x - g[i].x, ey = g[i + 1].y - g[i].y;
        const double t = std::clamp(((x - g[i].x) * ex + (y - g[i].y) * ey) / (ex * ex + ey * ey), 0.0, 1.0);
        d = std::min(d, std::hypot(x - g[i].x - t * ex, y - g[i].y - t * ey));
    }
    return d;
}

/// Primer corte de la recta que sale de p con ángulo deg (antihorario desde +x) con la superficie, sobre ella.
inline std::optional<Point2> ray_hit(const Poly& g, Point2 p, double deg) {
    const double dx = std::cos(deg * kDeg), dy = std::sin(deg * kDeg);
    double best = std::numeric_limits<double>::infinity();
    for (std::size_t i = 0; i + 1 < g.size(); ++i) {
        const double ex = g[i + 1].x - g[i].x, ey = g[i + 1].y - g[i].y, den = dx * ey - dy * ex;
        if (std::fabs(den) < 1e-15) continue;
        const double wx = g[i].x - p.x, wy = g[i].y - p.y;
        const double t = (wx * ey - wy * ex) / den, s = (wx * dy - wy * dx) / den;
        if (t > le_detail::kTol && s >= -1e-12 && s <= 1.0 + 1e-12) best = std::min(best, t);
    }
    if (!std::isfinite(best)) return std::nullopt;
    const double x = p.x + best * dx;
    return Point2{x, le_detail::interp(g, x)};
}

inline std::vector<double> spread(double lo, double hi, int n) {
    std::vector<double> v;
    for (int k = 0; k < n; ++k) v.push_back(n == 1 ? 0.5 * (lo + hi) : lo + (hi - lo) * k / (n - 1));
    return v;
}

inline SlipSurface circle_of(double xc, double yc, double r) {
    SlipSurface f;
    f.circle = Circle{xc, yc, r};
    return f;
}

/// Polilínea de bloque desde sus parámetros: x del extremo izquierdo, (x, y) de los interiores, x del derecho; los
/// extremos van sobre la superficie.
inline SlipSurface polyline_of(const Poly& g, const std::vector<double>& p) {
    Poly q{{p.front(), le_detail::interp(g, p.front())}};
    for (std::size_t i = 1; i + 1 < p.size(); i += 2) q.push_back({p[i], p[i + 1]});
    q.push_back({p.back(), le_detail::interp(g, p.back())});
    SlipSurface f;
    f.polyline = std::move(q);
    return f;
}

/// Arma el resultado en coordenadas del usuario y recalcula la crítica en la sección original (tajadas del usuario).
inline SearchResult finish(const LeSection& user, bool mirror, const SearchOptions& o, const Evaluator& ev,
                           const std::optional<SlipSurface>& best, const Top& top, MethodInfo info) {
    SearchResult out;
    out.evaluated = ev.evaluated;
    out.discarded = ev.discarded;
    out.discarded_malpha = ev.discarded_malpha;
    out.info = std::move(info);
    if (ev.discarded_malpha > 0)
        out.notes.push_back(std::to_string(ev.discarded_malpha) + " slip surfaces discarded for m-alpha below 0.2");
    for (const auto& [f, F] : top) out.top.emplace_back(mirror ? mirrored(f) : f, F);
    if (best) {
        out.surface = mirror ? mirrored(*best) : *best;
        out.best = le_factor_of_safety(user, out.surface, o.method, o.le);
        out.warnings = out.best.warnings;
    } else {
        out.best = LeResult{std::nullopt, o.method, std::nullopt, 0, false, {}, 0.0, le_detail::info(o.method), {}, {}};
        out.warnings.push_back("no valid slip surface found");
    }
    return out;
}
}  // namespace search_detail

inline SearchResult search_circular(const LeSection& section, const CircularGrid& grid,
                                    const SearchOptions& options = {}) {
    using namespace search_detail;
    using namespace validation;
    validate(section, options);
    require_finite(grid.x_min, "grid.x_min");
    require_finite(grid.y_min, "grid.y_min");
    require_finite(grid.x_max, "grid.x_max");
    require_finite(grid.y_max, "grid.y_max");
    require(grid.x_max > grid.x_min, "grid.x_max", "must be greater than grid.x_min", grid.x_max);
    require(grid.y_max > grid.y_min, "grid.y_max", "must be greater than grid.y_min", grid.y_max);
    require(grid.nx >= 1, "grid.nx", "must be at least 1", grid.nx);
    require(grid.ny >= 1, "grid.ny", "must be at least 1", grid.ny);
    require(grid.n_radii >= 2, "grid.n_radii", "must be at least 2", grid.n_radii);

    const bool mir = faces_plus_x(section);
    const LeSection s = mir ? mirrored(section) : section;
    const double x0 = mir ? -grid.x_max : grid.x_min, x1 = mir ? -grid.x_min : grid.x_max;
    const double y0 = grid.y_min, y1 = grid.y_max;
    const Poly& g = s.surface;
    double ytop = g.front().y, ylow = g.front().y;
    for (const auto& q : g) {
        ytop = std::max(ytop, q.y);
        ylow = std::min(ylow, q.y);
    }
    if (s.model_base_y) ylow = *s.model_base_y;

    struct Seed {
        double F, xc, yc, r, dr;
        int i, j;
    };
    Evaluator ev{s, options};
    Top top;
    std::vector<Seed> seeds;  // el mejor círculo de cada centro
    for (int i = 0; i <= grid.nx; ++i)
        for (int j = 0; j <= grid.ny; ++j) {
            const double xc = x0 + (x1 - x0) * i / grid.nx, yc = y0 + (y1 - y0) * j / grid.ny;
            const double r_lo = std::max(yc - (ytop - 0.5), distance_to(g, xc, yc)), r_hi = yc - ylow;
            if (!(r_hi > r_lo)) continue;
            std::vector<double> radii;
            for (int k = 0; k < grid.n_radii; ++k) {
                const double t = static_cast<double>(k) / (grid.n_radii - 1);
                radii.push_back(r_lo + (r_hi - r_lo) * t * t);
            }
            std::optional<Seed> sd;
            for (std::size_t k = 0; k < radii.size(); ++k) {
                const SlipSurface f = circle_of(xc, yc, radii[k]);
                const auto F = ev(f);
                if (!F) continue;
                keep(top, f, *F);
                if (!sd || *F < sd->F) {
                    const double dr = std::max(k > 0 ? radii[k] - radii[k - 1] : 0.0,
                                               k + 1 < radii.size() ? radii[k + 1] - radii[k] : 0.0);
                    sd = Seed{*F, xc, yc, radii[k], dr, i, j};
                }
            }
            if (sd) seeds.push_back(*sd);
        }
    std::stable_sort(seeds.begin(), seeds.end(), [](const Seed& a, const Seed& b) { return a.F < b.F; });
    std::optional<Circle> best;
    double bestF = std::numeric_limits<double>::infinity();
    if (!seeds.empty()) {
        best = Circle{seeds[0].xc, seeds[0].yc, seeds[0].r};
        bestF = seeds[0].F;
    }
    if (options.refine) {
        std::vector<Seed> chosen;
        for (const auto& c : seeds) {
            if (chosen.size() == 5) break;
            const bool near = std::any_of(chosen.begin(), chosen.end(), [&](const Seed& o) {
                return (std::abs(c.i - o.i) <= 1 && std::abs(c.j - o.j) <= 1) || std::fabs(c.r - o.r) <= o.dr;
            });
            if (!near) chosen.push_back(c);
        }
        const double h = std::max((x1 - x0) / grid.nx, (y1 - y0) / grid.ny), F0 = bestF;
        for (const auto& c : chosen) {
            double F = c.F;
            const auto p = pattern_search({c.xc, c.yc, c.r}, F, h,
                                          [&](const std::vector<double>& q) { return ev(circle_of(q[0], q[1], q[2])); });
            if (F < bestF) {
                bestF = F;
                best = Circle{p[0], p[1], p[2]};
            }
        }
        if (bestF < F0) keep(top, circle_of(best->xc, best->yc, best->radius), bestF);
    }
    std::optional<SlipSurface> bs;
    if (best) bs = circle_of(best->xc, best->yc, best->radius);
    auto out = finish(section, mir, options, ev, bs, top,
                      {"Circular-Grid-Search", Verification::Secondary,
                       "Slide2 Verification Manual (2022) problems 1, 3, 4: grid of centres with radii; "
                       "multistart pattern-search refinement"});
    if (best && !(best->xc > x0 && best->xc < x1 && best->yc > y0 && best->yc < y1))
        out.warnings.push_back("critical centre on the edge of the search grid");
    return out;
}

inline SearchResult search_block(const LeSection& section, const BlockSearch& block,
                                 const SearchOptions& options = {}) {
    using namespace search_detail;
    using namespace validation;
    validate(section, options);
    le_detail::check_poly(block.weak_line, "weak_line");
    require(block.n_points >= 2, "n_points", "must be at least 2", block.n_points);
    require(block.n_angles >= 1, "n_angles", "must be at least 1", block.n_angles);
    auto angles = [](double lo, double hi, double a, double b, const std::string& n) {
        require_finite(lo, n + "_min");
        require_finite(hi, n + "_max");
        require(lo > a && lo < b, n + "_min", "must be within (" + detail::num(a) + ", " + detail::num(b) + ")", lo);
        require(hi > a && hi < b, n + "_max", "must be within (" + detail::num(a) + ", " + detail::num(b) + ")", hi);
        require(hi >= lo, n + "_max", "must not be less than " + n + "_min", hi);
    };
    angles(block.left_angle_min, block.left_angle_max, 90.0, 180.0, "left_angle");
    angles(block.right_angle_min, block.right_angle_max, 0.0, 90.0, "right_angle");

    const bool mir = faces_plus_x(section);
    const LeSection s = mir ? mirrored(section) : section;
    const Poly& g = s.surface;
    const Poly weak = mir ? le_detail::mirror(block.weak_line) : block.weak_line;
    std::vector<Point2> pts;  // posiciones de la línea débil bajo la superficie
    for (double x : spread(weak.front().x, weak.back().x, block.n_points)) {
        const Point2 p{x, le_detail::interp(weak, x)};
        if (x > g.front().x && x < g.back().x && p.y < le_detail::interp(g, x) - le_detail::kTol) pts.push_back(p);
    }
    const auto left = spread(block.left_angle_min, block.left_angle_max, block.n_angles);
    const auto right = spread(block.right_angle_min, block.right_angle_max, block.n_angles);

    Evaluator ev{s, options};
    Top top;
    std::vector<double> best;  // parámetros de polilínea_of
    double bestF = std::numeric_limits<double>::infinity();
    for (std::size_t i = 0; i < pts.size(); ++i)
        for (std::size_t j = i + 1; j < pts.size(); ++j)
            for (double a : left)
                for (double b : right) {
                    const auto hl = ray_hit(g, pts[i], a), hr = ray_hit(g, pts[j], b);
                    if (!hl || !hr) {  // sin corte con la superficie no hay masa: se cuenta como descartada
                        ev.reject();
                        continue;
                    }
                    std::vector<double> p{hl->x, pts[i].x, pts[i].y};
                    for (const auto& q : weak)
                        if (q.x > pts[i].x + le_detail::kTol && q.x < pts[j].x - le_detail::kTol) {
                            p.push_back(q.x);
                            p.push_back(q.y);
                        }
                    p.insert(p.end(), {pts[j].x, pts[j].y, hr->x});
                    const SlipSurface f = polyline_of(g, p);
                    const auto F = ev(f);
                    if (!F) continue;
                    keep(top, f, *F);
                    if (*F < bestF) {
                        bestF = *F;
                        best = p;
                    }
                }
    if (!best.empty() && options.refine) {
        const double h = (weak.back().x - weak.front().x) / (block.n_points - 1), F0 = bestF;
        // los tramos extremos no salen de los ángulos dados (si no, el afinado cae en masas de pie empinado y mα bajo)
        auto in_angles = [&](const Poly& q) {
            const std::size_t n = q.size();
            const double toe = std::atan2(q[0].y - q[1].y, q[0].x - q[1].x) / kDeg,
                         crest = std::atan2(q[n - 1].y - q[n - 2].y, q[n - 1].x - q[n - 2].x) / kDeg;
            return toe >= block.left_angle_min - 1e-9 && toe <= block.left_angle_max + 1e-9 &&
                   crest >= block.right_angle_min - 1e-9 && crest <= block.right_angle_max + 1e-9;
        };
        const auto p = pattern_search(best, bestF, h, [&](const std::vector<double>& q) {
            const SlipSurface f = polyline_of(g, q);
            return in_angles(*f.polyline) ? ev(f) : ev.reject();
        });
        if (bestF < F0) {
            best = p;
            keep(top, polyline_of(g, p), bestF);
        }
    }
    std::optional<SlipSurface> bs;
    if (!best.empty()) bs = polyline_of(g, best);
    return finish(section, mir, options, ev, bs, top,
                  {"Block-Search", Verification::Secondary,
                   "Slide2 Verification Manual (2022) problem 7: two points on a weak line with projection angles; "
                   "pattern-search refinement of the vertices"});
}

}  // namespace rockmasspy
