/**
 * @file kinematics.hpp
 * @brief Pruebas cinemáticas de Markland: deslizamiento planar, cuña, volteo flexural y volteo directo.
 *
 * Criterios de la ayuda de Rocscience Dips v9 (fuente secundaria, `Secondary`; resoluciones R5 a R9). Todas las
 * comparaciones son inclusivas del lado crítico. Un plano va por {dirección de buzamiento, buzamiento} y una
 * intersección por {tendencia, inmersión}; Δ es la diferencia angular con signo contra la dirección de la cara αs.
 * Los porcentajes son factibilidad cinemática, no probabilidad de falla.
 */

#pragma once

#include <cmath>
#include <string>
#include <vector>

#include "rockmasspy/method_info.hpp"
#include "rockmasspy/stereonet.hpp"
#include "rockmasspy/validation.hpp"

namespace rockmasspy {

struct KinematicInput {
    PlaneOrientation face;     // buzamiento en (0, 90]
    double friction_deg;       // phi, en (0, 90)
    double lateral_limit_deg;  // L, en (0, 90)
};

struct PlaneChecks {
    bool planar;
    bool planar_no_limits;
    bool flexural_toppling;
    int direct_toppling_base_zone;  // 0 = ninguna, 1, 2 o 3
};

struct IntersectionChecks {
    LineOrientation line;
    bool wedge_primary;
    bool wedge_secondary;
    bool direct_toppling;
    bool direct_toppling_oblique;
};

namespace kinematics_detail {
using namespace stereonet_detail;

/// Diferencia angular con signo a - b, en (-180, 180].
inline double sdiff(double a, double b) {
    double d = wrap(a - b);
    return d > 180.0 ? d - 360.0 : d;
}
inline double tand(double d) { return std::tan(rad(d)); }
inline double cosd(double d) { return std::cos(rad(d)); }
/// cos Δ > 0 con holgura: Δ = 90 exacto no debe pasar por ruido de coma flotante.
inline bool toward(double delta) { return cosd(delta) > 1e-12; }

/// Holgura numérica del lado crítico: un valor justo en el límite (R5) no puede decidirlo el ruido.
inline constexpr double eps = 1e-9;

inline void validate(const KinematicInput& in) {
    validation::require_in_range(in.face.dip_direction_deg, 0.0, 360.0, "face.dip_direction_deg");
    validation::require_in_range(in.face.dip_deg, 0.0, 90.0, "face.dip_deg");
    validation::require(in.face.dip_deg > 0.0, "face.dip_deg", "must be greater than 0", in.face.dip_deg);
    validation::require_finite(in.friction_deg, "friction_deg");
    validation::require(in.friction_deg > 0.0 && in.friction_deg < 90.0, "friction_deg", "must be within (0, 90)",
                        in.friction_deg);
    validation::require_finite(in.lateral_limit_deg, "lateral_limit_deg");
    validation::require(in.lateral_limit_deg > 0.0 && in.lateral_limit_deg < 90.0, "lateral_limit_deg",
                        "must be within (0, 90)", in.lateral_limit_deg);
}
inline double dot(const Vec& a, const Vec& b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
/// Aflora: el vector no queda del lado del polo de la cara (equivale a tan(inmersión) <= tan(βs)·cos Δ).
inline bool daylights(const Vec& v, const KinematicInput& in) { return dot(v, vec(pole_of(in.face))) <= eps; }
}  // namespace kinematics_detail

inline PlaneChecks check_plane(PlaneOrientation plane, const KinematicInput& in) {
    using namespace kinematics_detail;
    validate(in);
    check(plane);
    const double bs = in.face.dip_deg, bj = plane.dip_deg, phi = in.friction_deg, lim = in.lateral_limit_deg;
    const double delta = sdiff(plane.dip_direction_deg, in.face.dip_direction_deg);
    const bool day = toward(delta) && daylights(vec({plane.dip_direction_deg, bj}), in);
    PlaneChecks r{};
    r.planar_no_limits = day && bj >= phi - eps;
    r.planar = r.planar_no_limits && std::fabs(delta) <= lim + eps;
    const double pole_trend = pole_of(plane).trend_deg;
    double dp = sdiff(pole_trend, in.face.dip_direction_deg);
    // buzamiento 90: polo horizontal, el mismo eje en t y t + 180; se toma el extremo menos favorable
    if (bj >= 90.0 - eps) dp = std::fmin(std::fabs(dp), std::fabs(sdiff(pole_trend + 180.0, in.face.dip_direction_deg)));
    r.flexural_toppling = bs > phi && std::fabs(dp) <= lim + eps && tand(90.0 - bj) <= tand(bs - phi) * cosd(dp) + eps;
    if (r.planar)
        r.direct_toppling_base_zone = 1;
    else if (toward(delta) && bj < phi)
        r.direct_toppling_base_zone = std::fabs(delta) <= lim + eps ? 2 : 3;
    return r;
}

namespace kinematics_detail {
inline IntersectionChecks eval_line(LineOrientation line, const KinematicInput& in) {
    const double bs = in.face.dip_deg, phi = in.friction_deg, lim = in.lateral_limit_deg, pl = line.plunge_deg;
    const double delta = sdiff(line.trend_deg, in.face.dip_direction_deg);
    const Vec v = vec(line);
    IntersectionChecks r{line, false, false, false, false};
    const bool day = toward(delta) && daylights(v, in);
    r.wedge_primary = pl >= phi - eps && day;
    // secundaria: sobre el círculo de buzamiento φ o por encima (tan φ·cos Δ <= tan(inmersión))
    const double below_phi_circle = dot(v, vec({in.face.dip_direction_deg + 180.0, 90.0 - phi}));
    r.wedge_secondary = !r.wedge_primary && toward(delta) && pl < phi - eps && below_phi_circle >= -eps && day;
    const double away = std::fabs(sdiff(line.trend_deg, in.face.dip_direction_deg + 180.0));
    r.direct_toppling = away <= lim + eps && pl >= 90.0 - bs - eps;
    // oblicua (zona 3): fuera de los límites laterales y dentro del cono de fricción de los planos base
    r.direct_toppling_oblique = !r.direct_toppling && pl >= 90.0 - phi - eps && away >= lim - eps;
    return r;
}
inline IntersectionChecks merge(IntersectionChecks a, const IntersectionChecks& b) {
    a.wedge_primary |= b.wedge_primary;
    a.wedge_secondary |= b.wedge_secondary;
    a.direct_toppling |= b.direct_toppling;
    a.direct_toppling_oblique |= b.direct_toppling_oblique;
    return a;
}
}  // namespace kinematics_detail

inline IntersectionChecks check_intersection(LineOrientation line, const KinematicInput& in) {
    using namespace kinematics_detail;
    validate(in);
    check(line);
    const double as = in.face.dip_direction_deg;
    if (line.plunge_deg > 90.0 - eps) {  // vertical: tendencia indiferente
        auto r = eval_line({wrap(as + 180.0), 90.0}, in);
        if (in.face.dip_deg > 90.0 - eps) r = merge(r, eval_line({wrap(as), 90.0}, in));  // cara vertical: también cuña
        r.direct_toppling_oblique = r.direct_toppling_oblique && !r.direct_toppling;  // exclusivas tras unir
        r.line = line;
        return r;
    }
    auto r = eval_line(line, in);
    // horizontal: eje, sin lado; se evalúan t y t + 180 y se unen las banderas
    if (line.plunge_deg < eps) r = merge(r, eval_line({wrap(line.trend_deg + 180.0), 0.0}, in));
    r.direct_toppling_oblique = r.direct_toppling_oblique && !r.direct_toppling;
    return r;
}

struct KinematicResult {
    std::vector<PlaneChecks> planes;
    std::vector<IntersectionChecks> intersections;
    std::vector<int> pair_a, pair_b;  // índices de los planos de cada intersección
    int n_planes = 0, n_intersections = 0, n_parallel_pairs = 0;
    int planar = 0, planar_no_limits = 0, flexural_toppling = 0;
    int wedge_primary = 0, wedge_secondary = 0, direct_toppling = 0, direct_toppling_oblique = 0;
    int base_zone_1 = 0, base_zone_2 = 0, base_zone_3 = 0;
    KinematicInput input{};
    std::vector<MethodInfo> methods;
    std::vector<std::string> notes;
};

/// groups[i] >= 0 es la familia del plano i y -1 es «sin familia». Intersecciones (R7): solo pares i < j de familias
/// distintas o con algún -1; los paralelos no entran y se cuentan.
inline KinematicResult kinematic_analysis(const std::vector<PlaneOrientation>& planes, const std::vector<int>& groups,
                                          const KinematicInput& in) {
    using namespace kinematics_detail;
    validate(in);
    validation::require(planes.size() == groups.size(), "groups", "must have the same length as planes",
                        static_cast<double>(groups.size()));
    for (int g : groups) validation::require(g >= -1, "groups", "entries must be >= -1", g);
    KinematicResult r;
    r.input = in;
    r.n_planes = static_cast<int>(planes.size());
    for (const auto& p : planes) {
        const auto c = check_plane(p, in);
        r.planes.push_back(c);
        r.planar += c.planar;
        r.planar_no_limits += c.planar_no_limits;
        r.flexural_toppling += c.flexural_toppling;
        r.base_zone_1 += c.direct_toppling_base_zone == 1;
        r.base_zone_2 += c.direct_toppling_base_zone == 2;
        r.base_zone_3 += c.direct_toppling_base_zone == 3;
    }
    for (std::size_t i = 0; i < planes.size(); ++i)
        for (std::size_t j = i + 1; j < planes.size(); ++j) {
            if (groups[i] >= 0 && groups[i] == groups[j]) continue;
            auto line = plane_intersection(planes[i], planes[j]);
            if (!line) {
                ++r.n_parallel_pairs;
                continue;
            }
            const auto c = check_intersection(*line, in);
            r.intersections.push_back(c);
            r.pair_a.push_back(static_cast<int>(i));
            r.pair_b.push_back(static_cast<int>(j));
            r.wedge_primary += c.wedge_primary;
            r.wedge_secondary += c.wedge_secondary;
            r.direct_toppling += c.direct_toppling;
            r.direct_toppling_oblique += c.direct_toppling_oblique;
        }
    r.n_intersections = static_cast<int>(r.intersections.size());
    const std::string src = "Rocscience Dips v9 help, kinematic analysis (accessed 2026-11-02)";
    r.methods = {
        {"Kinematic-PlanarSliding", Verification::Secondary,
         src + "; criteria attributed to Goodman (1980) and Hudson and Harrison (1997); originals not read"},
        {"Kinematic-WedgeSliding", Verification::Secondary, src + "; no lateral limits"},
        {"Kinematic-FlexuralToppling-Goodman1980", Verification::Secondary, src},
        {"Kinematic-DirectToppling-HudsonHarrison1997", Verification::Secondary, src + "; zones 1 and 2 merged"}};
    if (r.n_parallel_pairs > 0)
        r.notes.push_back(std::to_string(r.n_parallel_pairs) + " parallel plane pairs give no intersection");
    return r;
}

}  // namespace rockmasspy
