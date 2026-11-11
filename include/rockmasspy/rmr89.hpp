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

#include <algorithm>
#include <cmath>
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

// Curvas continuas ajustadas a las cartas de Bieniawski (1989): Kundu et al. (2020), IJRMMS 129:104280.
// Sin redondeo ni saltos: solo se recorta al rango del puntaje.
// La ecuación publicada usa |x - c|; max(x - c, 0) mantiene la curva monótona y es idéntico para x >= c.
// Constantes de la Tabla 3 del artículo; QuickRMR 1.0.0 usa -0.1 en el UCS y 0.442 en las juntas/m del RMR14.
inline double rating_ucs89_continuous(double ucs_mpa) {
    validation::require_non_negative(ucs_mpa, "ucs_mpa");
    return std::clamp(0.42 * std::pow(std::max(ucs_mpa - 0.01, 0.0), 0.65) - 0.01, 0.0, 15.0);
}

/// Is50 <= 1 MPa no tiene puntaje, igual que en la tabla.
inline double rating_is50_89_continuous(double is50_mpa) {
    validation::require_non_negative(is50_mpa, "is50_mpa");
    if (is50_mpa <= 1.0)
        throw std::invalid_argument("Domain error [RockMassPy]: parameter 'is50_mpa': Is50 <= 1 MPa: use UCS instead");
    return std::clamp(-13.0 + 28.0 / (1.0 + std::pow(10.0, 0.02 - 0.15 * is50_mpa)), 0.0, 15.0);
}

inline double rating_rqd89_continuous(double rqd_pct) {
    validation::require_in_range(rqd_pct, 0.0, 100.0, "rqd_pct");
    return std::clamp(0.317 * std::pow(std::max(rqd_pct - 0.07, 0.0), 0.9) - 0.02, 0.0, 20.0);
}

/// La ecuación original usa mm; aquí el espaciamiento entra en m.
inline double rating_spacing89_continuous(double spacing_m) {
    validation::require_non_negative(spacing_m, "spacing_m");
    return std::clamp(1.94 * std::pow(1000.0 * spacing_m, 0.316) - 1.5, 0.0, 20.0);
}

// Condición de juntas y agua (Tabla 3 del artículo). La rugosidad entra como JRC (Barton y Choubey) y el
// intemperismo como índice *I5 (Matthews et al.), porque la tabla de Bieniawski los describe solo con palabras.
inline double rating_persistence89_continuous(double persistence_m) {
    validation::require_non_negative(persistence_m, "persistence_m");
    return std::clamp(1.0 / (0.166 + 0.05 * persistence_m), 0.0, 6.0);
}

inline double rating_aperture89_continuous(double aperture_mm) {
    validation::require_non_negative(aperture_mm, "aperture_mm");
    return std::clamp(1.0 / (0.166 + 0.25 * aperture_mm), 0.0, 6.0);
}

inline double rating_roughness89_continuous(double jrc) {
    validation::require_in_range(jrc, 0.0, 20.0, "jrc");
    return 0.3 * jrc;
}

/// Espesor del relleno en mm (0 = sin relleno); `soft` elige la curva de relleno blando.
inline double rating_infilling89_continuous(double infilling_mm, bool soft) {
    validation::require_non_negative(infilling_mm, "infilling_mm");
    const double x = infilling_mm;
    return std::clamp(soft ? 162.0 / (27.0 + x * x * x) : 6.0 - 4.0 * std::pow(x, 4) / (256.0 + std::pow(x, 4)),
                      0.0, 6.0);
}

/// *I5 en %: 100·(Ru5 − Rw1)/Ru5 con el martillo Schmidt tipo N.
inline double rating_weathering89_continuous(double i5_pct) {
    validation::require_in_range(i5_pct, 0.0, 100.0, "i5_pct");
    return std::clamp(6.3 / (1.0 + std::pow(10.0, 0.032 * i5_pct - 1.3)), 0.0, 6.0);
}

/// Caudal por cada 10 m de túnel, en l/min.
inline double rating_inflow89_continuous(double inflow_l_min) {
    validation::require_non_negative(inflow_l_min, "inflow_l_min");
    return std::clamp(165.0 / (inflow_l_min + 11.0), 0.0, 15.0);
}

/// Presión de agua en la junta entre el esfuerzo principal mayor. El eje de la Fig. 5e dice MPa, pero sus
/// escalones (0.1, 0.2, 0.5) son los de esa razón en Bieniawski (1989).
inline double rating_water_pressure89_continuous(double pressure_ratio) {
    validation::require_non_negative(pressure_ratio, "pressure_ratio");
    return std::clamp(2.4 / (pressure_ratio + 0.15) - 1.0, 0.0, 15.0);
}

struct JointCondition89Continuous {
    double persistence_m = validation::unset;
    double aperture_mm = validation::unset;
    double jrc = validation::unset;
    double infilling_mm = validation::unset;
    bool soft_infilling = false;
    double i5_pct = validation::unset;
};

/// Suma de las cinco curvas (0-30): se pasa a Rmr89Input.joint_condition_rating.
inline double jcond89_continuous(const JointCondition89Continuous& j) {
    return rating_persistence89_continuous(j.persistence_m) + rating_aperture89_continuous(j.aperture_mm) +
           rating_roughness89_continuous(j.jrc) + rating_infilling89_continuous(j.infilling_mm, j.soft_infilling) +
           rating_weathering89_continuous(j.i5_pct);
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

/// Exactamente uno de ucs_mpa/is50_mpa, uno de joint_condition/joint_condition_rating (0-30) y uno de
/// water/water_rating (0-15).
struct Rmr89Input {
    std::optional<double> ucs_mpa, is50_mpa;
    double rqd_pct = validation::unset;
    double spacing_m = validation::unset;
    std::optional<JointCondition89> joint_condition;
    std::optional<double> joint_condition_rating;
    std::optional<Water> water;
    std::optional<double> water_rating;
    std::optional<OrientationClass> orientation;
    Application application = Application::Tunnel;
    RmrFunctions functions = RmrFunctions::Discrete;
};

struct Rmr89Result {
    double r_strength, r_rqd, r_spacing;
    double r_condition;
    double r_water;
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
    const bool cont = in.functions == RmrFunctions::Continuous;
    if (cont) {
        r.r_strength = in.ucs_mpa ? rating_ucs89_continuous(*in.ucs_mpa) : rating_is50_89_continuous(*in.is50_mpa);
        r.r_rqd = rating_rqd89_continuous(in.rqd_pct);
        r.r_spacing = rating_spacing89_continuous(in.spacing_m);
    } else {
        r.r_strength = in.ucs_mpa ? rating_ucs89(*in.ucs_mpa) : rating_is50_89(*in.is50_mpa);
        r.r_rqd = rating_rqd89(in.rqd_pct);
        r.r_spacing = rating_spacing89(in.spacing_m);
    }
    if (in.joint_condition) {
        r.r_condition = jcond89(*in.joint_condition);
    } else {
        validation::require_in_range(*in.joint_condition_rating, 0.0, 30.0, "joint_condition_rating");
        r.r_condition = *in.joint_condition_rating;
    }
    if (in.water && in.water_rating)
        throw std::invalid_argument("Domain error [RockMassPy]: give exactly one of 'water' or 'water_rating'");
    if (in.water_rating) {
        validation::require_in_range(*in.water_rating, 0.0, 15.0, "water_rating");
        r.r_water = *in.water_rating;
    } else {
        r.r_water = rating_water89(validation::require_set(in.water, "water"));
    }
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
    if (cont)
        r.info = {"RMR89-continuous", Verification::Secondary,
                  "Kundu et al. (2020), continuous functions fitted to Bieniawski (1989) charts"};
    else
        r.info = {"RMR89", Verification::Secondary, "Bieniawski (1989), as transcribed in Osinergmin (2017), Annex A.15"};
    return r;
}

}  // namespace rockmasspy
