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
#include <optional>
#include <string>
#include <vector>

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
inline LineOrientation line_of(Vec v) {  // v unitario con z >= 0
    const double z = std::clamp(v[2], 0.0, 1.0);
    return {wrap(deg(std::atan2(v[1], v[0]))), deg(std::asin(z))};
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
    return line_of({c[0] * s, c[1] * s, c[2] * s});
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
    validation::require(r2 <= 1.0 + 1e-12, "x", "point must lie inside the unit disk (x^2 + y^2 <= 1)", point.x);
    const double r = std::sqrt(r2);
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

}  // namespace rockmasspy
