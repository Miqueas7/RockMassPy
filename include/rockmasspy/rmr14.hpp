/**
 * @file rmr14.hpp
 * @brief RMR14 según Celada et al. (2014): RMR = (RMRb + F0) * Fe * Fs, con ICE de Bieniawski y Celada.
 *
 * Regla de límites: un valor justo en el límite de un rango toma el puntaje menos favorable.
 * Resistencia y juntas por metro se leen de las curvas del método (no hay ecuación publicada):
 * se reciben como puntajes ya leídos. Fe de tuneladora queda pendiente: la tabla y la fórmula de la
 * fuente no coinciden. Errata corregida: Id2 > 85 puntúa 10 (la fuente dice «< 85»).
 * Fs en ICE = 15 toma la rama continua (1.3 − 0.6·0.15² = 1.2865), el valor menos favorable del límite.
 * Sin dato: las medidas y los puntajes valen NaN y los enums obligatorios van vacíos; un campo olvidado
 * lanza con su nombre.
 * Fuente: transcripción de Osinergmin (2017), Anexo A.14 (verificación secundaria).
 */

#pragma once

#include <algorithm>
#include <cmath>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

#include "rockmasspy/method_info.hpp"
#include "rockmasspy/rmr89.hpp"
#include "rockmasspy/validation.hpp"

namespace rockmasspy {

enum class Roughness14 { VeryRough, Rough, Smooth, Slickensided };
enum class Infilling14 { HardUnder5mm, HardOver5mm, SoftUnder5mm, SoftOver5mm };
enum class Alteration14 { Unaltered, Moderately, Highly, Decomposed };
enum class Excavation { DrillAndBlast, Tbm };

/// Ayudas con las curvas continuas de Kundu et al. (2020), IJRMMS 129:104280; el RMR14 sigue recibiendo puntajes.
inline double rmr14_strength_rating(double ucs_mpa) { return rating_ucs89_continuous(ucs_mpa); }

inline double rmr14_joints_per_m_rating(double n_per_m) {
    validation::require_non_negative(n_per_m, "n_per_m");
    return std::clamp(42.35 - 7.4 * std::pow(n_per_m, 0.443), 0.0, 40.0);
}

inline int rating_continuity14(double m) {
    validation::require_non_negative(m, "continuity_m");
    if (m < 1.0) return 5;
    if (m < 3.0) return 4;
    if (m < 10.0) return 2;
    return 0;
}

inline int rating_id2_14(double id2_pct) {
    validation::require_in_range(id2_pct, 0.0, 100.0, "id2_pct");
    if (id2_pct > 85.0) return 10;
    if (id2_pct > 60.0) return 8;
    if (id2_pct > 30.0) return 4;
    return 0;
}

/// Índice de comportamiento elástico (ICE); sigma_ci en MPa, profundidad en m.
inline double ice_bieniawski_celada(double rmr, double sigma_ci_mpa, double k0, double depth_m,
                                    double shape_factor_f) {
    validation::require_in_range(rmr, 0.0, 100.0, "rmr");
    validation::require_positive(sigma_ci_mpa, "sigma_ci_mpa");
    validation::require_positive(k0, "k0");
    validation::require_positive(depth_m, "depth_m");
    validation::require_positive(shape_factor_f, "shape_factor_f");
    const double num = 3704.0 * sigma_ci_mpa * std::exp((rmr - 100.0) / 24.0);
    const double den = (k0 <= 1.0 ? 3.0 - k0 : 3.0 * k0 - 1.0) * depth_m;
    return num / den * shape_factor_f;
}

inline double fs_face(double ice) {
    validation::require_non_negative(ice, "ice");
    if (ice < 15.0) return 1.3;
    if (ice < 70.0) return 1.3 - 0.6 * (ice / 100.0) * (ice / 100.0);
    return 1.0;
}

struct Rmr14Input {
    double strength_rating = validation::unset;      // 0-15, de la curva de UCS
    double joints_per_m_rating = validation::unset;  // 0-40, de la curva de juntas por metro
    double continuity_m = validation::unset;
    std::optional<Roughness14> roughness;
    std::optional<Infilling14> infilling;
    std::optional<Alteration14> alteration;
    std::optional<Water> water;
    double id2_pct = validation::unset;
    std::optional<OrientationClass> orientation;
    Excavation excavation = Excavation::DrillAndBlast;
    std::optional<double> ice;
};

struct Rmr14Result {
    double basic;
    int f0;
    double fe;
    double fs;
    double rmr;
    RmrClass rmr_class;
    MethodInfo info;
    std::vector<std::string> warnings;
};

inline Rmr14Result rmr14(const Rmr14Input& in) {
    if (in.excavation == Excavation::Tbm)
        throw std::invalid_argument("RMR14 Fe for TBM is pending verification against Celada et al. (2014)");
    validation::require_in_range(in.strength_rating, 0.0, 15.0, "strength_rating");
    validation::require_in_range(in.joints_per_m_rating, 0.0, 40.0, "joints_per_m_rating");
    if (in.ice) validation::require_non_negative(*in.ice, "ice");

    static const int rough[] = {5, 3, 1, 0}, fill[] = {5, 2, 2, 0}, alter[] = {5, 3, 1, 0};
    Rmr14Result r{};
    using validation::require_set;
    r.basic = in.strength_rating + in.joints_per_m_rating + rating_continuity14(in.continuity_m) +
              rough[static_cast<int>(require_set(in.roughness, "roughness"))] +
              fill[static_cast<int>(require_set(in.infilling, "infilling"))] +
              alter[static_cast<int>(require_set(in.alteration, "alteration"))] +
              rating_water89(require_set(in.water, "water")) + rating_id2_14(in.id2_pct);
    if (in.orientation) {
        r.f0 = orientation_adjustment(*in.orientation, Application::Tunnel);
    } else {
        r.f0 = 0;
        r.warnings.push_back("no orientation adjustment applied: rmr is the basic rating");
    }
    r.fe = 1.0;
    if (in.ice) {
        r.fs = fs_face(*in.ice);
    } else {
        r.fs = 1.0;
        r.warnings.push_back("Fs not evaluated (no ICE): elastic face assumed");
    }
    r.rmr = (r.basic + r.f0) * r.fe * r.fs;
    if (r.rmr < 0.0 || r.rmr > 100.0) r.warnings.push_back("rmr outside 0-100 after adjustments");
    r.rmr_class = rmr_class(r.rmr);
    r.info = {"RMR14", Verification::Secondary, "Celada et al. (2014), as transcribed in Osinergmin (2017), Annex A.14"};
    return r;
}

}  // namespace rockmasspy
