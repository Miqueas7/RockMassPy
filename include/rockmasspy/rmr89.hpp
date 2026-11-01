/**
 * @file rmr89.hpp
 * @brief RMR89 (Bieniawski 1989): puntajes por parámetro, suma básica y ajuste por orientación.
 *
 * Regla de límites: un valor justo en el límite de un rango toma el puntaje menos favorable
 * (por ejemplo UCS = 100 MPa puntúa 7, no 12; RQD = 90 puntúa 17, no 20).
 * Sin dato: las medidas valen NaN y los enums obligatorios van vacíos; un campo olvidado lanza con su nombre.
 * Fuente: transcripción de Osinergmin (2017), Anexo A.15 (verificación secundaria).
 */

#pragma once

#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

#include "rockmasspy/method_info.hpp"
#include "rockmasspy/rmr_common.hpp"
#include "rockmasspy/validation.hpp"

namespace rockmasspy {

enum class Roughness { VeryRough, Rough, SlightlyRough, Smooth, Slickensided };
enum class Infilling { None, HardUnder5mm, HardOver5mm, SoftUnder5mm, SoftOver5mm };
enum class Weathering { Unweathered, Slightly, Moderately, Highly, Decomposed };

struct JointCondition89 {
    double persistence_m = validation::unset;
    double aperture_mm = validation::unset;
    std::optional<Roughness> roughness;
    std::optional<Infilling> infilling;
    std::optional<Weathering> weathering;
};

inline int rating_ucs89(double ucs_mpa) {
    validation::require_non_negative(ucs_mpa, "ucs_mpa");
    if (ucs_mpa > 250.0) return 15;
    if (ucs_mpa > 100.0) return 12;
    if (ucs_mpa > 50.0) return 7;
    if (ucs_mpa > 25.0) return 4;
    if (ucs_mpa > 5.0) return 2;
    if (ucs_mpa > 1.0) return 1;
    return 0;
}

/// Is50 <= 1 MPa no tiene puntaje: se usa UCS.
inline int rating_is50_89(double is50_mpa) {
    validation::require_non_negative(is50_mpa, "is50_mpa");
    if (is50_mpa > 10.0) return 15;
    if (is50_mpa > 4.0) return 12;
    if (is50_mpa > 2.0) return 7;
    if (is50_mpa > 1.0) return 4;
    throw std::invalid_argument("Domain error [RockMassPy]: parameter 'is50_mpa': Is50 <= 1 MPa: use UCS instead");
}

inline int rating_rqd89(double rqd_pct) {
    validation::require_in_range(rqd_pct, 0.0, 100.0, "rqd_pct");
    if (rqd_pct > 90.0) return 20;
    if (rqd_pct > 75.0) return 17;
    if (rqd_pct > 50.0) return 13;
    if (rqd_pct > 25.0) return 8;
    return 3;
}

inline int rating_spacing89(double spacing_m) {
    validation::require_positive(spacing_m, "spacing_m");
    if (spacing_m > 2.0) return 20;
    if (spacing_m > 0.6) return 15;
    if (spacing_m > 0.2) return 10;
    if (spacing_m > 0.06) return 8;
    return 5;
}

/// Suma de persistencia, apertura, rugosidad, relleno e intemperismo (0-30).
inline int jcond89(const JointCondition89& j) {
    validation::require_non_negative(j.persistence_m, "persistence_m");
    validation::require_non_negative(j.aperture_mm, "aperture_mm");
    static const int rough[] = {6, 5, 3, 1, 0}, fill[] = {6, 4, 2, 2, 0}, weather[] = {6, 5, 3, 1, 0};
    const int persistence = j.persistence_m < 1.0 ? 6 : j.persistence_m < 3.0 ? 4 : j.persistence_m < 10.0 ? 2
                            : j.persistence_m < 20.0 ? 1 : 0;
    const int aperture = j.aperture_mm == 0.0 ? 6 : j.aperture_mm < 0.1 ? 5 : j.aperture_mm < 1.0 ? 4
                         : j.aperture_mm < 5.0 ? 1 : 0;
    using validation::require_set;
    return persistence + aperture + rough[static_cast<int>(require_set(j.roughness, "roughness"))] +
           fill[static_cast<int>(require_set(j.infilling, "infilling"))] +
           weather[static_cast<int>(require_set(j.weathering, "weathering"))];
}

inline int rating_water89(Water w) {
    static const int table[] = {15, 10, 7, 4, 0};
    return table[static_cast<int>(w)];
}

/// Exactamente uno de ucs_mpa/is50_mpa y uno de joint_condition/joint_condition_rating (0-30).
struct Rmr89Input {
    std::optional<double> ucs_mpa, is50_mpa;
    double rqd_pct = validation::unset;
    double spacing_m = validation::unset;
    std::optional<JointCondition89> joint_condition;
    std::optional<double> joint_condition_rating;
    std::optional<Water> water;
    std::optional<OrientationClass> orientation;
    Application application = Application::Tunnel;
};

struct Rmr89Result {
    int r_strength, r_rqd, r_spacing;
    double r_condition;
    int r_water;
    double basic;
    double adjustment;
    double rmr;
    RmrClass rmr_class;
    MethodInfo info;
    std::vector<std::string> warnings;
};

inline Rmr89Result rmr89(const Rmr89Input& in) {
    if (in.ucs_mpa.has_value() == in.is50_mpa.has_value())
        throw std::invalid_argument("Domain error [RockMassPy]: give exactly one of 'ucs_mpa' or 'is50_mpa'");
    if (in.joint_condition.has_value() == in.joint_condition_rating.has_value())
        throw std::invalid_argument(
            "Domain error [RockMassPy]: give exactly one of 'joint_condition' or 'joint_condition_rating'");

    Rmr89Result r{};
    r.r_strength = in.ucs_mpa ? rating_ucs89(*in.ucs_mpa) : rating_is50_89(*in.is50_mpa);
    r.r_rqd = rating_rqd89(in.rqd_pct);
    r.r_spacing = rating_spacing89(in.spacing_m);
    if (in.joint_condition) {
        r.r_condition = jcond89(*in.joint_condition);
    } else {
        validation::require_in_range(*in.joint_condition_rating, 0.0, 30.0, "joint_condition_rating");
        r.r_condition = *in.joint_condition_rating;
    }
    r.r_water = rating_water89(validation::require_set(in.water, "water"));
    r.basic = r.r_strength + r.r_rqd + r.r_spacing + r.r_condition + r.r_water;

    if (in.ucs_mpa && *in.ucs_mpa > 400.0)
        r.warnings.push_back("ucs_mpa > 400: check the unit is MPa (not kg/cm2)");
    if (in.rqd_pct > 0.0 && in.rqd_pct <= 1.0)
        r.warnings.push_back("rqd_pct <= 1: RQD is a percentage (0-100); check it is not a fraction");
    if (in.orientation) {
        r.adjustment = orientation_adjustment(*in.orientation, in.application);
    } else {
        r.adjustment = 0;
        r.warnings.push_back("no orientation adjustment applied: rmr is the basic rating");
    }
    r.rmr = r.basic + r.adjustment;
    if (r.rmr < 0.0 || r.rmr > 100.0) r.warnings.push_back("rmr outside 0-100 after adjustments");
    r.rmr_class = rmr_class(r.rmr);
    r.info = {"RMR89", Verification::Secondary, "Bieniawski (1989), as transcribed in Osinergmin (2017), Annex A.15"};
    return r;
}

}  // namespace rockmasspy
