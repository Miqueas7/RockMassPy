/**
 * @file stereonet.hpp
 * @brief Geometría de la red estereográfica: orientaciones, polo y plano, intersección y proyecciones.
 *
 * Convención (resolución R2): un plano es {dirección de buzamiento, buzamiento}; una línea es
 * {tendencia, inmersión} en el hemisferio inferior; vectores con x = norte, y = este, z = abajo;
 * una dirección o tendencia 360 se guarda como 0; la proyección tiene radio 1 con el norte arriba
 * (x de la figura = este). Es geometría de la esfera, sin MethodInfo (resolución R23).
 */

#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <optional>
#include <string>
#include <vector>

#include "rockmasspy/method_info.hpp"
#include "rockmasspy/validation.hpp"

namespace rockmasspy {

enum class Projection { EqualAngle, EqualArea };

struct PlaneOrientation {
    double dip_direction_deg;
    double dip_deg;
};
struct LineOrientation {
    double trend_deg;
    double plunge_deg;
};
struct Point2 {
    double x;
    double y;
};

namespace stereonet_detail {
inline constexpr double pi = 3.14159265358979323846;
inline double rad(double d) { return d * pi / 180.0; }
inline double deg(double r) { return r * 180.0 / pi; }

/// Lleva un ángulo a [0, 360); 360 vuelve como 0 y -0 como 0.
inline double wrap(double a) {
    a = std::fmod(a, 360.0);
    if (a < 0.0) a += 360.0;
    return a >= 360.0 ? 0.0 : a + 0.0;
}

inline void check(double azimuth, double inclination, const char* az_name, const char* inc_name) {
    validation::require_in_range(azimuth, 0.0, 360.0, az_name);
    validation::require_in_range(inclination, 0.0, 90.0, inc_name);
}
inline void check(const PlaneOrientation& p) { check(p.dip_direction_deg, p.dip_deg, "dip_direction_deg", "dip_deg"); }
inline void check(const LineOrientation& l) { check(l.trend_deg, l.plunge_deg, "trend_deg", "plunge_deg"); }

using Vec = std::array<double, 3>;  // norte, este, abajo

inline Vec vec(const LineOrientation& l) {
    const double t = rad(l.trend_deg), p = rad(l.plunge_deg);
    return {std::cos(p) * std::cos(t), std::cos(p) * std::sin(t), std::sin(p)};
}
/// canonical_axis: una línea horizontal es un eje, así que su tendencia se lleva a [0, 180) (misma regla para
/// (a, b) y (b, a)); great_circle la deja en falso porque ahí los extremos del rumbo son puntos distintos del disco.
inline LineOrientation line_of(Vec v, bool canonical_axis = false) {  // v unitario con z >= 0
    const double z = std::max(v[2], 0.0);
    if (canonical_axis && z < 1e-12) {
        const double t = wrap(deg(std::atan2(v[1], v[0])));
        const double h = t >= 180.0 ? t - 180.0 : t;
        return {h > 180.0 - 1e-9 ? 0.0 : h, 0.0};  // 179.999999999 es 0 con ruido
    }
    const double h = std::hypot(v[0], v[1]);
    if (canonical_axis && h < 1e-12) return {0.0, 90.0};  // vertical: tendencia indiferente, se fija en 0
    return {wrap(deg(std::atan2(v[1], v[0]))), deg(std::atan2(z, h))};
}
}  // namespace stereonet_detail

/// Polo de un plano: tendencia = dirección + 180, inmersión = 90 - buzamiento.
inline LineOrientation pole_of(PlaneOrientation plane) {
    stereonet_detail::check(plane);
    return {stereonet_detail::wrap(plane.dip_direction_deg + 180.0), 90.0 - plane.dip_deg};
}

/// Plano de un polo (inversa de pole_of).
inline PlaneOrientation plane_of(LineOrientation pole) {
    stereonet_detail::check(pole);
    return {stereonet_detail::wrap(pole.trend_deg + 180.0), 90.0 - pole.plunge_deg};
}

/// Ángulo entre dos ejes, en [0, 90]: una línea y su opuesta son el mismo eje.
inline double angle_between(LineOrientation a, LineOrientation b) {
    stereonet_detail::check(a);
    stereonet_detail::check(b);
    const auto u = stereonet_detail::vec(a), v = stereonet_detail::vec(b);
    const double dot = std::fabs(u[0] * v[0] + u[1] * v[1] + u[2] * v[2]);
    const double cx = u[1] * v[2] - u[2] * v[1], cy = u[2] * v[0] - u[0] * v[2], cz = u[0] * v[1] - u[1] * v[0];
    // atan2 conserva la precisión cerca de 0 y 90 grados, donde acos pierde cifras
    return stereonet_detail::deg(std::atan2(std::sqrt(cx * cx + cy * cy + cz * cz), dot));
}

/// Intersección de dos planos (producto vectorial de las normales, al hemisferio inferior);
/// nullopt si son paralelos (norma < 1e-9).
inline std::optional<LineOrientation> plane_intersection(PlaneOrientation a, PlaneOrientation b) {
    using namespace stereonet_detail;
    const auto n = vec(pole_of(a)), m = vec(pole_of(b));
    Vec c{n[1] * m[2] - n[2] * m[1], n[2] * m[0] - n[0] * m[2], n[0] * m[1] - n[1] * m[0]};
    const double norm = std::sqrt(c[0] * c[0] + c[1] * c[1] + c[2] * c[2]);
    if (norm < 1e-9) return std::nullopt;
    const double s = (c[2] < 0.0 ? -1.0 : 1.0) / norm;
    return line_of({c[0] * s, c[1] * s, c[2] * s}, true);
}

/// Radio en el disco unitario para una inmersión dada.
inline double stereonet_radius(double plunge_deg, Projection p) {
    const double half = stereonet_detail::rad(45.0 - plunge_deg / 2.0);
    return p == Projection::EqualAngle ? std::tan(half) : std::sqrt(2.0) * std::sin(half);
}

/// Proyecta una línea al disco unitario (x = este, y = norte).
inline Point2 project(LineOrientation line, Projection p) {
    stereonet_detail::check(line);
    const double r = stereonet_radius(line.plunge_deg, p), t = stereonet_detail::rad(line.trend_deg);
    return {r * std::sin(t), r * std::cos(t)};
}

/// Inversa de project; lanza si el punto cae fuera del disco unitario.
inline LineOrientation unproject(Point2 point, Projection p) {
    using namespace stereonet_detail;
    validation::require_finite(point.x, "x");
    validation::require_finite(point.y, "y");
    const double r2 = point.x * point.x + point.y * point.y;
    const double r = std::sqrt(r2);
    validation::require(r2 <= 1.0 + 1e-12, "point", "must lie inside the unit disk (radius <= 1)", r);
    const double colat = p == Projection::EqualAngle ? 2.0 * std::atan(r) : 2.0 * std::asin(std::min(1.0, r / std::sqrt(2.0)));
    const double plunge = std::clamp(90.0 - deg(colat), 0.0, 90.0);
    return {r < 1e-15 ? 0.0 : wrap(deg(std::atan2(point.x, point.y))), plunge};
}

/// n puntos del gran círculo de un plano, de un extremo del rumbo al otro por la línea de máxima pendiente.
inline std::vector<Point2> great_circle(PlaneOrientation plane, Projection p, int n = 181) {
    using namespace stereonet_detail;
    check(plane);
    validation::require(n >= 3, "n", "must be at least 3", n);
    const double dd = rad(plane.dip_direction_deg), dip = rad(plane.dip_deg);
    // u: línea de rumbo (horizontal); v: máxima pendiente. Cada punto es cos(f) u + sin(f) v, f en [0, pi].
    const Vec u{std::cos(dd - pi / 2), std::sin(dd - pi / 2), 0.0};
    const Vec v{std::cos(dip) * std::cos(dd), std::cos(dip) * std::sin(dd), std::sin(dip)};
    std::vector<Point2> out;
    out.reserve(n);
    for (int i = 0; i < n; ++i) {
        const double f = pi * i / (n - 1), c = std::cos(f), s = std::sin(f);
        out.push_back(project(line_of({c * u[0] + s * v[0], c * u[1] + s * v[1], c * u[2] + s * v[2]}), p));
    }
    return out;
}

struct FisherStats {
    LineOrientation mean;
    int n;
    double resultant_length;
    std::optional<double> kappa;
    std::optional<double> alpha95_deg;
    MethodInfo info;
    std::vector<std::string> warnings;
};

/// Estadística de Fisher de polos tratados como ejes (Tauxe et al., ec. 11.14-11.17).
inline FisherStats fisher_stats(const std::vector<LineOrientation>& poles) {
    using namespace stereonet_detail;
    validation::require(!poles.empty(), "poles", "must not be empty", 0.0);
    std::vector<Vec> v;
    v.reserve(poles.size());
    for (const auto& p : poles) {
        check(p);
        v.push_back(vec(p));
    }
    const auto dot = [](const Vec& a, const Vec& b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; };
    const auto sum = [&](const Vec& ref) {  // suma con cada polo en el hemisferio de ref
        Vec s{0, 0, 0};
        for (const auto& u : v) {
            const double sg = dot(u, ref) < 0.0 ? -1.0 : 1.0;
            for (int i = 0; i < 3; ++i) s[i] += sg * u[i];
        }
        return s;
    };
    const auto norm = [](const Vec& a) { return std::sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2]); };
    Vec s = sum(v[0]);
    s = sum(s);  // realinea a la media y recalcula
    const double r = norm(s);  // R >= 1: el primer polo tiene producto punto >= 0 con cada otro tras alinear, y la 2.ª pasada solo lo aumenta
    Vec m{s[0] / r, s[1] / r, s[2] / r};
    if (m[2] < 0.0) m = {-m[0], -m[1], -m[2]};
    const int n = static_cast<int>(poles.size());
    FisherStats out{line_of(m, true), n, r, std::nullopt, std::nullopt,
                    {"Fisher1953-set-statistics", Verification::Secondary,
                     "Tauxe et al., Essentials of Paleomagnetism (web edition, CC BY 4.0), section 11.2.1, eqs. "
                     "11.14-11.17: mean of unit vectors, k = (N-1)/(N-R), alpha95 with p = 0.05; Fisher (1953) not "
                     "read; poles treated as axes"},
                    {}};
    if (n == 1) return out;
    if (n - r <= 1e-12) {
        out.kappa = std::numeric_limits<double>::infinity();
        out.alpha95_deg = 0.0;
        return out;
    }
    out.kappa = (n - 1) / (n - r);
    const double arg = 1.0 - ((n - r) / r) * (std::pow(1.0 / 0.05, 1.0 / (n - 1)) - 1.0);
    if (arg < -1.0)
        out.warnings.push_back("alpha95 undefined: poles too dispersed for their number");
    else
        out.alpha95_deg = deg(std::acos(std::min(1.0, arg)));
    return out;
}

/// Densidad de polos por círculo de conteo de Schmidt: % de polos por 1 % del área del hemisferio.
inline std::vector<double> pole_density(const std::vector<LineOrientation>& poles,
                                        const std::vector<LineOrientation>& at, double area_fraction = 0.01) {
    using namespace stereonet_detail;
    validation::require(!poles.empty(), "poles", "must not be empty", 0.0);
    validation::require(area_fraction > 0.0 && area_fraction <= 0.5, "area_fraction", "must be in (0, 0.5]",
                        area_fraction);
    std::vector<Vec> v;
    v.reserve(poles.size());
    for (const auto& p : poles) {
        check(p);
        v.push_back(vec(p));
    }
    const double cos_theta = 1.0 - area_fraction;  // theta = acos(1 - area_fraction)
    std::vector<double> out;
    out.reserve(at.size());
    for (const auto& a : at) {
        check(a);
        const Vec c = vec(a);
        int count = 0;
        for (const auto& u : v)
            if (std::fabs(u[0] * c[0] + u[1] * c[1] + u[2] * c[2]) >= cos_theta) ++count;
        out.push_back(100.0 * count / static_cast<double>(v.size()) * (0.01 / area_fraction));
    }
    return out;
}

}  // namespace rockmasspy
