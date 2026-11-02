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

inline void validate(const KinematicInput& in) {
    check(in.face);
    validation::require(in.face.dip_deg > 0.0, "face.dip_deg", "must be greater than 0", in.face.dip_deg);
    validation::require_finite(in.friction_deg, "friction_deg");
    validation::require(in.friction_deg > 0.0 && in.friction_deg < 90.0, "friction_deg", "must be within (0, 90)",
                        in.friction_deg);
    validation::require_finite(in.lateral_limit_deg, "lateral_limit_deg");
    validation::require(in.lateral_limit_deg > 0.0 && in.lateral_limit_deg < 90.0, "lateral_limit_deg",
                        "must be within (0, 90)", in.lateral_limit_deg);
}
}  // namespace kinematics_detail

inline PlaneChecks check_plane(PlaneOrientation plane, const KinematicInput& in) {
    using namespace kinematics_detail;
    validate(in);
    check(plane);
    const double bs = in.face.dip_deg, bj = plane.dip_deg, phi = in.friction_deg, lim = in.lateral_limit_deg;
    const double delta = sdiff(plane.dip_direction_deg, in.face.dip_direction_deg);
    const bool daylights = toward(delta) && tand(bj) <= tand(bs) * cosd(delta);
    PlaneChecks r{};
    r.planar_no_limits = daylights && bj >= phi;
    r.planar = r.planar_no_limits && std::fabs(delta) <= lim;
    const double dp = sdiff(pole_of(plane).trend_deg, in.face.dip_direction_deg);
    r.flexural_toppling = bs > phi && std::fabs(dp) <= lim && tand(90.0 - bj) <= tand(bs - phi) * cosd(dp);
    if (r.planar)
        r.direct_toppling_base_zone = 1;
    else if (toward(delta) && bj < phi)
        r.direct_toppling_base_zone = std::fabs(delta) <= lim ? 2 : 3;
    return r;
}

inline IntersectionChecks check_intersection(LineOrientation line, const KinematicInput& in) {
    using namespace kinematics_detail;
    validate(in);
    check(line);
    const double bs = in.face.dip_deg, phi = in.friction_deg, lim = in.lateral_limit_deg, pl = line.plunge_deg;
    const double delta = sdiff(line.trend_deg, in.face.dip_direction_deg);
    IntersectionChecks r{line, false, false, false, false};
    const bool daylights = toward(delta) && tand(pl) <= tand(bs) * cosd(delta);
    r.wedge_primary = pl >= phi && daylights;
    r.wedge_secondary = !r.wedge_primary && toward(delta) && pl < phi && tand(phi) * cosd(delta) <= tand(pl) &&
                        daylights;
    r.direct_toppling = std::fabs(sdiff(line.trend_deg, in.face.dip_direction_deg + 180.0)) <= lim && pl >= 90.0 - bs;
    r.direct_toppling_oblique = !r.direct_toppling && pl >= 90.0 - phi;
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
            if (line->plunge_deg < 1e-9) {  // horizontal: de t y t + 180 se toma la más cercana a la dirección de la cara
                const double t2 = wrap(line->trend_deg + 180.0);
                if (std::fabs(sdiff(t2, in.face.dip_direction_deg)) < std::fabs(sdiff(line->trend_deg, in.face.dip_direction_deg)))
                    line->trend_deg = t2;
            }
            // vertical: la tendencia es indiferente (plane_intersection la fija en 0); se toma la de volteo directo, sin cuña
            if (line->plunge_deg > 90.0 - 1e-9) line->trend_deg = wrap(in.face.dip_direction_deg + 180.0);
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
