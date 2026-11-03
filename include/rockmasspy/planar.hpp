/**
 * @file planar.hpp
 * @brief Falla planar de Hoek y Bray con grieta de tracción, agua, sismo, carga externa y perno; grieta crítica y retroanálisis.
 *
 * Fuente: Hoek, «A slope stability problem in Hong Kong» (Practical Rock Engineering): ec. 1-11 (pp. 5-7), por metro de
 * talud, equilibrio de fuerzas por el centroide. Perno y fuerza externa se proyectan sobre el plano (R5); superficie
 * superior horizontal y grieta vertical a distancia b de la cresta (R3). Agua: con grieta zw = f z (ec. 10-11); sin
 * grieta U = f * ec. 4 (R4, generalización nuestra). Comprobado contra RocPlane Verification Manual (2022).
 * Un valor justo en un límite toma el lado menos favorable con holgura 1e-9 (R3, R6). Los avisos no repiten valores.
 */

#pragma once

#include <cmath>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

#include "rockmasspy/method_info.hpp"
#include "rockmasspy/validation.hpp"

namespace rockmasspy {

enum class BoltMode { Active, Passive };

struct PlanarInput {
    double height_m = validation::unset, face_dip_deg = validation::unset, plane_dip_deg = validation::unset;
    double unit_weight = validation::unset, cohesion = validation::unset, friction_deg = validation::unset;
    std::optional<double> tension_crack_distance_m;  // distancia horizontal b detrás de la cresta; vacío = sin grieta
    double water_fill = 0.0;                         // [0, 1]: zw/z con grieta; escala de U sin grieta
    double water_unit_weight = validation::unset;    // obligatoria si water_fill > 0
    double kh = 0.0;                                 // [0, 1], horizontal hacia afuera
    double bolt_force = 0.0, bolt_plunge_deg = 0.0;  // inmersión bajo la horizontal, hacia dentro del talud
    BoltMode bolt_mode = BoltMode::Active;
    double external_force = 0.0, external_angle_deg = 0.0;  // 0 horizontal hacia afuera, 90 vertical hacia abajo
};

struct TensionCrack {
    double depth_m;
    double distance_m;
};

struct PlanarResult {
    std::optional<double> factor_of_safety;
    bool formed;
    double tension_crack_depth_m, weight, base_area, uplift_force, crack_water_force;
    double normal_force, driving_force, resisting_force;
    MethodInfo info;
    std::vector<std::string> warnings, notes;
};

struct PlanarBackAnalysis {
    std::vector<double> friction_deg, cohesion;
    std::optional<double> friction_at_zero_cohesion_deg;
    MethodInfo info;
    std::vector<std::string> notes;
};

namespace planar_detail {
constexpr double kPi = 3.14159265358979323846;
constexpr double kTol = 1e-9;
inline double rad(double d) { return d * kPi / 180.0; }
inline double deg(double r) { return r * 180.0 / kPi; }
inline double cot(double d) { return 1.0 / std::tan(rad(d)); }

inline MethodInfo info() {
    return {"Planar-HoekBray", Verification::PrimaryLaterAuthors,
            "Hoek, 'A slope stability problem in Hong Kong' (Practical Rock Engineering): eqs. 1-11 (pp. 5-7), per "
            "metre, force equilibrium through the centroid; bolt and external force resolved on the plane, checked "
            "against RocPlane Verification Manual (2022) problems 1, 6, 7, 8 and bolt problem 2"};
}

inline void check_geometry(double h, double face, double plane) {
    validation::require_positive(h, "height_m");
    validation::require_finite(face, "face_dip_deg");
    validation::require(face > 0.0 && face <= 90.0, "face_dip_deg", "must be within (0, 90]", face);
    validation::require_finite(plane, "plane_dip_deg");
    validation::require(plane > 0.0 && plane < 90.0, "plane_dip_deg", "must be within (0, 90)", plane);
}

inline void check(const PlanarInput& in, bool strength) {
    check_geometry(in.height_m, in.face_dip_deg, in.plane_dip_deg);
    validation::require_positive(in.unit_weight, "unit_weight");
    if (strength) {
        validation::require_non_negative(in.cohesion, "cohesion");
        validation::require_finite(in.friction_deg, "friction_deg");
        validation::require(in.friction_deg >= 0.0 && in.friction_deg < 90.0, "friction_deg",
                            "must be within [0, 90)", in.friction_deg);
    }
    validation::require_in_range(in.water_fill, 0.0, 1.0, "water_fill");
    // NaN es el valor por defecto («sin dato») y solo se exige con agua; el infinito nunca vale
    if (in.water_fill > 0.0) validation::require_positive(in.water_unit_weight, "water_unit_weight");
    else if (std::isinf(in.water_unit_weight)) validation::require_finite(in.water_unit_weight, "water_unit_weight");
    validation::require_in_range(in.kh, 0.0, 1.0, "kh");
    validation::require_non_negative(in.bolt_force, "bolt_force");
    validation::require_in_range(in.bolt_plunge_deg, -90.0, 90.0, "bolt_plunge_deg");
    validation::require_non_negative(in.external_force, "external_force");
    validation::require_finite(in.external_angle_deg, "external_angle_deg");
    validation::require(in.external_angle_deg > -180.0 && in.external_angle_deg <= 180.0, "external_angle_deg",
                        "must be within (-180, 180]", in.external_angle_deg);
    if (in.tension_crack_distance_m) validation::require_non_negative(*in.tension_crack_distance_m, "tension_crack_distance_m");
}

inline bool is_formed(const PlanarInput& in) { return in.plane_dip_deg < in.face_dip_deg - kTol; }

struct Forces {
    double z = 0, W = 0, A = 0, U = 0, V = 0, N = 0, D = 0, passive = 0;  // N incluye perno y externa; D ya descuenta el perno activo
};

/// Vectores en la sección (x afuera, z arriba) resueltos a mano sobre el plano: abajo del plano (cos ψ, -sin ψ),
/// compresión sobre el plano -(Fx sin ψ + Fz cos ψ).
inline Forces forces(const PlanarInput& in) {
    const double H = in.height_m, pp = rad(in.plane_dip_deg), g = in.unit_weight;
    const double cf = cot(in.face_dip_deg), cp = cot(in.plane_dip_deg);
    Forces f;
    if (in.tension_crack_distance_m) {
        const double b = *in.tension_crack_distance_m;
        if (b > H * (cp - cf) + kTol)
            throw std::invalid_argument(
                "Domain error [RockMassPy]: parameter 'tension_crack_distance_m' the crack must meet the sliding plane "
                "(distance exceeds the maximum for this geometry)");
        f.z = H - (b + H * cf) * std::tan(pp);
        if (f.z < 0.0) f.z = 0.0;  // ruido de coma flotante en b = bmax
        const double r = f.z / H;
        f.A = (H - f.z) / std::sin(pp);
        f.W = 0.5 * g * H * H * ((1.0 - r * r) * cp - cf);
        if (in.water_fill > 0.0) {
            const double zw = in.water_fill * f.z;
            f.U = 0.5 * in.water_unit_weight * zw * f.A;
            f.V = 0.5 * in.water_unit_weight * zw * zw;
        }
    } else {
        f.A = H / std::sin(pp);
        f.W = 0.5 * g * H * H * (cp - cf);
        if (in.water_fill > 0.0) f.U = in.water_fill * in.water_unit_weight * H * H / (4.0 * std::sin(pp));
    }
    const double th = rad(in.bolt_plunge_deg), be = rad(in.external_angle_deg);
    const double tc = in.bolt_force * std::cos(pp + th), ts = in.bolt_force * std::sin(pp + th);
    f.N = f.W * (std::cos(pp) - in.kh * std::sin(pp)) - f.U - f.V * std::sin(pp) + ts +
          in.external_force * std::sin(be - pp);
    f.D = f.W * (std::sin(pp) + in.kh * std::cos(pp)) + f.V * std::cos(pp) + in.external_force * std::cos(pp - be);
    if (in.bolt_mode == BoltMode::Active) f.D -= tc;
    else f.passive = tc;
    return f;
}
}  // namespace planar_detail

/// Grieta de tracción crítica de un talud seco: ec. 6 y 7 (p. 6). Exige ψp < ψf.
inline TensionCrack critical_tension_crack(double height_m, double face_dip_deg, double plane_dip_deg) {
    using namespace planar_detail;
    check_geometry(height_m, face_dip_deg, plane_dip_deg);
    validation::require(plane_dip_deg < face_dip_deg - kTol, "plane_dip_deg", "must be below face_dip_deg",
                        plane_dip_deg);
    const double cf = cot(face_dip_deg), cp = cot(plane_dip_deg);
    return {height_m * (1.0 - std::sqrt(cf / cp)), height_m * (std::sqrt(cf * cp) - cf)};
}

inline PlanarResult planar_fs(const PlanarInput& in) {
    using namespace planar_detail;
    check(in, true);
    PlanarResult r{std::nullopt, false, 0, 0, 0, 0, 0, 0, 0, 0, info(), {}, {}};
    if (!is_formed(in)) {
        r.notes.push_back("planar block not formed: the plane does not daylight in the face");
        return r;
    }
    r.formed = true;
    const Forces f = forces(in);
    r.tension_crack_depth_m = f.z;
    r.weight = f.W;
    r.base_area = f.A;
    r.uplift_force = f.U;
    r.crack_water_force = f.V;
    r.normal_force = f.N;
    r.driving_force = f.D;
    double friction = f.N * std::tan(rad(in.friction_deg));
    if (f.N < 0.0) {
        friction = 0.0;
        r.warnings.push_back("effective normal force on the plane is negative: friction taken as zero");
    }
    r.resisting_force = in.cohesion * f.A + friction + f.passive;
    if (f.D <= 1e-12 * f.W) {
        r.factor_of_safety = std::numeric_limits<double>::infinity();
        r.notes.push_back("no driving force on the block");
    } else {
        r.factor_of_safety = r.resisting_force / f.D;
    }
    return r;
}

/// Cohesión que da FS = 1 para cada fricción (ignora in.cohesion e in.friction_deg); descarta las de c < 0.
inline PlanarBackAnalysis planar_back_analysis(const PlanarInput& in, const std::vector<double>& friction_deg) {
    using namespace planar_detail;
    check(in, false);
    if (friction_deg.empty())
        throw std::invalid_argument("Domain error [RockMassPy]: parameter 'friction_deg' must not be empty");
    for (double p : friction_deg) {
        validation::require_finite(p, "friction_deg");
        validation::require(p >= 0.0 && p < 90.0, "friction_deg", "must be within [0, 90)", p);
    }
    if (!is_formed(in))
        throw std::invalid_argument("Domain error [RockMassPy]: the planar block is not formed (plane_dip_deg is not below face_dip_deg)");
    const Forces f = forces(in);
    PlanarBackAnalysis out{{}, {}, std::nullopt, info(), {}};
    const double np = std::fmax(f.N, 0.0);
    bool dropped = false;
    for (double p : friction_deg) {
        const double c = (f.D - np * std::tan(rad(p)) - f.passive) / f.A;
        if (c >= 0.0) {
            out.friction_deg.push_back(p);
            out.cohesion.push_back(c);
        } else {
            dropped = true;
        }
    }
    if (dropped) out.notes.push_back("friction angles that would need negative cohesion were discarded");
    if (f.N > 0.0 && f.D - f.passive > 0.0) out.friction_at_zero_cohesion_deg = deg(std::atan((f.D - f.passive) / f.N));
    return out;
}

}  // namespace rockmasspy
