/**
 * @file smr.hpp
 * @brief SMR de Romana (1985) discreto y de Tomás et al. (2007) continuo, con rotura planar, vuelco y cuña.
 *
 * Fuentes: Tomás, Romana y Serón (2017), Bol. SEMSIG 190: ec. 1 (p. 25), Tablas 1-2 (p. 26), Tabla 3 (p. 27),
 * ec. 4-7 (p. 28, atan en grados). Cuña: Tomás et al. (2006) pp. 89-90 y Riquelme et al. (2016) Tabla 2.
 * Un valor justo en un límite toma el lado menos favorable (R10); C = 0 exacto es su propia clase (-25).
 * No se copia código de SMRTool (GPL).
 */

#pragma once

#include <algorithm>
#include <cmath>
#include <string>
#include <vector>

#include "rockmasspy/method_info.hpp"
#include "rockmasspy/stereonet.hpp"
#include "rockmasspy/validation.hpp"

namespace rockmasspy {

enum class SmrMode { Planar, Toppling, Wedge };
enum class SmrFunctions { Discrete, Continuous };
enum class SlopeExcavation { NaturalSlope, Presplitting, SmoothBlasting, NormalBlastingOrMechanical, DeficientBlasting };

struct SmrAngles {
    double a_deg;
    double b_deg;
    double c_deg;
};

struct SmrResult {
    double smr;
    double f1, f2, f3, f4;
    int smr_class;
    double failure_probability;
    SmrMode mode;
    SmrFunctions functions;
    SmrAngles angles;
    MethodInfo info;
    std::vector<std::string> warnings;
};

/// A, B y C. En planar y vuelco (direction, dip) son los de la junta; en cuña, los de la intersección.
inline SmrAngles smr_angles(SmrMode mode, double direction_deg, double dip_deg, PlaneOrientation face) {
    validation::require_in_range(direction_deg, 0.0, 360.0, "direction_deg");
    validation::require_in_range(dip_deg, 0.0, 90.0, "dip_deg");
    stereonet_detail::check(face);
    const bool toppling = mode == SmrMode::Toppling;
    double d = std::fabs(stereonet_detail::wrap(direction_deg - face.dip_direction_deg - (toppling ? 180.0 : 0.0)));
    if (d > 180.0) d = 360.0 - d;
    return {d, dip_deg, toppling ? dip_deg + face.dip_deg : dip_deg - face.dip_deg};
}

/// Clase I a V como 1 a 5; el hueco entre rangos (p. ej. 20.5) toma la clase peor (R13).
inline int smr_class(double smr) {
    validation::require_finite(smr, "smr");
    return smr >= 81 ? 1 : smr >= 61 ? 2 : smr >= 41 ? 3 : smr >= 21 ? 4 : 5;
}

inline double smr_f4(SlopeExcavation e) {
    switch (e) {
        case SlopeExcavation::NaturalSlope: return 15;
        case SlopeExcavation::Presplitting: return 10;
        case SlopeExcavation::SmoothBlasting: return 8;
        case SlopeExcavation::NormalBlastingOrMechanical: return 0;
        default: return -8;
    }
}

inline SmrResult smr(double rmr_basic, SmrMode mode, SmrFunctions functions, SlopeExcavation excavation, SmrAngles angles) {
    validation::require_in_range(rmr_basic, 0.0, 100.0, "rmr_basic");
    validation::require_in_range(angles.a_deg, 0.0, 180.0, "a_deg");
    validation::require_in_range(angles.b_deg, 0.0, 90.0, "b_deg");
    const bool top = mode == SmrMode::Toppling;
    if (top) validation::require_in_range(angles.c_deg, 0.0, 180.0, "c_deg");
    else validation::require_in_range(angles.c_deg, -90.0, 90.0, "c_deg");
    const double A = angles.a_deg, B = angles.b_deg, C = angles.c_deg;
    double f1, f2, f3;
    if (functions == SmrFunctions::Discrete) {
        f1 = A > 30 ? 0.15 : A > 20 ? 0.40 : A > 10 ? 0.70 : A > 5 ? 0.85 : 1.00;
        f2 = top ? 1.0 : B < 20 ? 0.15 : B < 30 ? 0.40 : B < 35 ? 0.70 : B < 45 ? 0.85 : 1.00;
        if (top) f3 = C < 110 ? 0 : C < 120 ? -6 : -25;
        else f3 = C > 10 ? 0 : C > 0 ? -6 : C == 0 ? -25 : C > -10 ? -50 : -60;
    } else {
        const auto at = [](double x) { return stereonet_detail::deg(std::atan(x)); };
        f1 = 16.0 / 25.0 - (3.0 / 500.0) * at((A - 17.0) / 10.0);
        f2 = top ? 1.0 : 9.0 / 16.0 + at(0.17 * B - 5.0) / 195.0;
        f3 = top ? -13.0 - at(C - 120.0) / 7.0 : -30.0 + at(C) / 3.0;
    }
    const double f4 = smr_f4(excavation);
    SmrResult r{rmr_basic + f1 * f2 * f3 + f4, f1, f2, f3, f4, 0, 0, mode, functions, angles, {}, {}};
    r.smr_class = smr_class(r.smr);
    static const double pof[] = {0, 0, 0.2, 0.4, 0.6, 0.9};
    r.failure_probability = pof[r.smr_class];
    if (r.smr > 100 || r.smr < 0) r.warnings.push_back("SMR outside 0-100");
    if (functions == SmrFunctions::Continuous)
        r.info = {"SMR-Tomas2007", Verification::PrimaryLaterAuthors,
                  "Tomas et al. (2007) continuous functions as given in Tomas, Romana & Seron (2017): eqs. 4-7 (p. 28), "
                  "atan in degrees; planar and wedge per p. 27"};
    else if (mode == SmrMode::Wedge)
        r.info = {"SMR-Romana1985-wedge", Verification::Secondary,
                  "wedge adaptation (Anbalagan et al. 1992) as given in Tomas et al. (2006) Rev. Soc. Geol. Espana "
                  "19(1-2) pp. 89-90 and Riquelme et al. (2016) IJRMMS 84 Table 2"};
    else
        r.info = {"SMR-Romana1985", Verification::PrimaryLaterAuthors,
                  "Romana (1985) as given in Tomas, Romana & Seron (2017) Bol. SEMSIG 190: eq. 1 (p. 25), Tables 1-2 "
                  "(p. 26), Table 3 (p. 27)"};
    return r;
}

}  // namespace rockmasspy
