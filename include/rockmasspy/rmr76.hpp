/**
 * @file rmr76.hpp
 * @brief RMR76 (Bieniawski 1976): puntajes por parámetro y suma básica con ajuste por orientación.
 *
 * Regla de límites: un valor justo en el límite de un rango toma el puntaje menos favorable.
 * Los rangos de resistencia del Anexo A.16 difieren de los de RMR89 (A.15), por eso aquí van los propios.
 * RQD, agua y ajuste por orientación coinciden con RMR89 y se reutilizan.
 * Fuente: transcripción de Osinergmin (2017), Anexo A.16 (verificación secundaria).
 */

#pragma once

#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

#include "rockmasspy/method_info.hpp"
#include "rockmasspy/rmr89.hpp"
#include "rockmasspy/validation.hpp"

namespace rockmasspy {

enum class JointCondition76 {
    VeryRoughTight, SlightlyRoughSlightlyWeathered, SlightlyRoughHighlyWeathered, SlickensidedOrThinGouge,
    SoftGougeOrWide
};
enum class Water76 { CompletelyDry, Damp, ModeratePressure, Severe };

inline int rating_ucs76(double ucs_mpa) {
    validation::require_non_negative(ucs_mpa, "ucs_mpa");
    if (ucs_mpa > 200.0) return 15;
    if (ucs_mpa > 100.0) return 12;
    if (ucs_mpa > 50.0) return 7;
    if (ucs_mpa > 25.0) return 4;
    if (ucs_mpa > 10.0) return 2;
    if (ucs_mpa > 3.0) return 1;
    return 0;
}

/// Is50 <= 1 MPa no tiene puntaje: se usa UCS.
inline int rating_is50_76(double is50_mpa) {
    validation::require_non_negative(is50_mpa, "is50_mpa");
    if (is50_mpa > 8.0) return 15;
    if (is50_mpa > 4.0) return 12;
    if (is50_mpa > 2.0) return 7;
    if (is50_mpa > 1.0) return 4;
    throw std::invalid_argument("Domain error [RockMassPy]: parameter 'is50_mpa': Is50 <= 1 MPa: use UCS instead");
}

inline int rating_spacing76(double spacing_m) {
    validation::require_positive(spacing_m, "spacing_m");
    if (spacing_m > 3.0) return 30;
    if (spacing_m > 1.0) return 25;
    if (spacing_m > 0.3) return 20;
    if (spacing_m > 0.05) return 10;
    return 5;
}

/// Exactamente uno de ucs_mpa/is50_mpa.
struct Rmr76Input {
    std::optional<double> ucs_mpa, is50_mpa;
    double rqd_pct = 0.0;
    double spacing_m = 1.0;
    JointCondition76 condition = JointCondition76::VeryRoughTight;
    Water76 water = Water76::CompletelyDry;
    std::optional<OrientationClass> orientation;
    Application application = Application::Tunnel;
};

struct Rmr76Result {
    int r_strength, r_rqd, r_spacing, r_condition, r_water;
    int basic;
    int adjustment;
    int rmr;
    RmrClass rmr_class;
    MethodInfo info;
    std::vector<std::string> warnings;
};

inline Rmr76Result rmr76(const Rmr76Input& in) {
    if (in.ucs_mpa.has_value() == in.is50_mpa.has_value())
        throw std::invalid_argument("Domain error [RockMassPy]: give exactly one of 'ucs_mpa' or 'is50_mpa'");

    static const int cond[] = {25, 20, 12, 6, 0}, water[] = {10, 7, 4, 0};
    Rmr76Result r{};
    r.r_strength = in.ucs_mpa ? rating_ucs76(*in.ucs_mpa) : rating_is50_76(*in.is50_mpa);
    r.r_rqd = rating_rqd89(in.rqd_pct);  // mismos rangos en A.16
    r.r_spacing = rating_spacing76(in.spacing_m);
    r.r_condition = cond[static_cast<int>(in.condition)];
    r.r_water = water[static_cast<int>(in.water)];
    r.basic = r.r_strength + r.r_rqd + r.r_spacing + r.r_condition + r.r_water;

    if (in.rqd_pct > 0.0 && in.rqd_pct <= 1.0)
        r.warnings.push_back("rqd_pct <= 1: RQD is a percentage (0-100); check it is not a fraction");
    if (in.orientation) {
        r.adjustment = orientation_adjustment(*in.orientation, in.application);
    } else {
        r.adjustment = 0;
        r.warnings.push_back("no orientation adjustment: rmr is the basic RMR76");
    }
    r.rmr = r.basic + r.adjustment;
    r.rmr_class = rmr_class(r.rmr);
    r.info = {"RMR76", Verification::Secondary, "Bieniawski (1976), as transcribed in Osinergmin (2017), Annex A.16"};
    return r;
}

}  // namespace rockmasspy
