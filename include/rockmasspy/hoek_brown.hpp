/**
 * @file hoek_brown.hpp
 * @brief Criterio de Hoek-Brown (ediciones 2002 y 2018), Mohr-Coulomb equivalente y módulo del macizo.
 *
 * Las ecuaciones de mb, s, a, σc, σt, σcm y σ3max son las de Hoek, Carranza-Torres y Corkum (2002).
 * Entre las ediciones 2002 y 2018 cambia solo la etiqueta de trazabilidad y el aviso sobre D
 * (Hoek y Brown 2019: D se aplica solo a la zona dañada por voladura, no a todo el macizo).
 * Fuera de alcance: tablas de mi y MR, ajuste desde triaxiales y D por zona.
 */

#pragma once

#include <algorithm>
#include <cmath>
#include <string>
#include <vector>

#include "rockmasspy/method_info.hpp"
#include "rockmasspy/validation.hpp"

namespace rockmasspy {

enum class HbEdition { HB2002, HB2018 };
enum class HbApplication { Tunnel, Slope };

struct HbParams {
    double mb, s, a;
    MethodInfo info;
    std::vector<std::string> warnings;
};

inline HbParams hb_params(double gsi, double mi, double d, HbEdition edition = HbEdition::HB2018) {
    using namespace validation;
    require_positive(gsi, "gsi");
    require_in_range(gsi, 0.0, 100.0, "gsi");
    require_positive(mi, "mi");
    require_in_range(d, 0.0, 1.0, "d");
    HbParams p{};
    // Las mismas ecuaciones en las dos ediciones: Hoek y Brown (2019) repiten las de 2002 (ec. 4 a 6)
    p.mb = mi * std::exp((gsi - 100.0) / (28.0 - 14.0 * d));
    p.s = std::exp((gsi - 100.0) / (9.0 - 3.0 * d));
    p.a = 0.5 + (std::exp(-gsi / 15.0) - std::exp(-20.0 / 3.0)) / 6.0;
    if (edition == HbEdition::HB2002) {
        p.info = {"HB-2002", Verification::Primary, "Hoek, Carranza-Torres & Corkum (2002)"};
    } else {
        p.info = {"HB-2018", Verification::Primary, "Hoek & Brown (2019), JRMGE 11(3)"};
        if (d > 0.0)
            p.warnings.push_back(
                "D applies only to the blast-damaged zone, never to the whole rock mass (Hoek & Brown 2019, Table 2)");
    }
    return p;
}

inline double hb_ucs(double sigma_ci_mpa, const HbParams& p) {
    validation::require_positive(sigma_ci_mpa, "sigma_ci_mpa");
    return sigma_ci_mpa * std::pow(p.s, p.a);
}

/// Negativa: σt = −s·σci/mb.
inline double hb_tensile(double sigma_ci_mpa, const HbParams& p) {
    validation::require_positive(sigma_ci_mpa, "sigma_ci_mpa");
    return -p.s * sigma_ci_mpa / p.mb;
}

/// Lanza si σ3 < σt (la envolvente no existe en ese rango). En σ3 = σt la base puede salir −1e-17 por
/// redondeo y pow daría NaN: se recorta a 0.
inline double hb_sigma1(double sigma3_mpa, double sigma_ci_mpa, const HbParams& p) {
    validation::require_finite(sigma3_mpa, "sigma3_mpa");
    validation::require(sigma3_mpa >= hb_tensile(sigma_ci_mpa, p), "sigma3_mpa",
                        "must be >= the tensile strength of the rock mass", sigma3_mpa);
    return sigma3_mpa + sigma_ci_mpa * std::pow(std::max(0.0, p.mb * sigma3_mpa / sigma_ci_mpa + p.s), p.a);
}

struct NormalShear {
    double sigma_n_mpa;
    double tau_mpa;
};

/// Esfuerzos normal y de corte sobre la envolvente (Balmer; Hoek et al. 2002, ec. 8-10).
/// En σ3 = σt la derivada dσ1/dσ3 es infinita: se devuelve el límite (σt, 0). Lanza si σ3 < σt.
inline NormalShear hb_normal_shear(double sigma3_mpa, double sigma_ci_mpa, const HbParams& p) {
    const double s1 = hb_sigma1(sigma3_mpa, sigma_ci_mpa, p);  // valida σ3 y σci
    const double st = hb_tensile(sigma_ci_mpa, p);
    if (std::abs(sigma3_mpa - st) <= 1e-12 * std::max(1.0, std::abs(st))) return {st, 0.0};
    const double base = std::max(0.0, p.mb * sigma3_mpa / sigma_ci_mpa + p.s);
    const double d = 1.0 + p.a * p.mb * std::pow(base, p.a - 1.0);
    return {(s1 + sigma3_mpa) / 2.0 - (s1 - sigma3_mpa) / 2.0 * (d - 1.0) / (d + 1.0),
            (s1 - sigma3_mpa) * std::sqrt(d) / (d + 1.0)};
}

/// σcm: resistencia global del macizo (rango σt < σ3 < σci/4).
inline double hb_global_strength(double sigma_ci_mpa, const HbParams& p) {
    validation::require_positive(sigma_ci_mpa, "sigma_ci_mpa");
    const double a = p.a, mb = p.mb, s = p.s;
    return sigma_ci_mpa * (mb + 4.0 * s - a * (mb - 8.0 * s)) * std::pow(mb / 4.0 + s, a - 1.0) /
           (2.0 * (1.0 + a) * (2.0 + a));
}

/// σ3max' para túnel (0.47, −0.94) o talud (0.72, −0.91). El peso unitario va en MN/m3.
inline double hb_sigma3max(double sigma_cm_mpa, double unit_weight_mn_m3, double depth_or_height_m,
                           HbApplication app) {
    using namespace validation;
    require_positive(sigma_cm_mpa, "sigma_cm_mpa");
    require_positive(unit_weight_mn_m3, "unit_weight_mn_m3");
    require_max(unit_weight_mn_m3, 0.05, "unit_weight_mn_m3",
                "unit_weight_mn_m3 must be in MN/m3 (e.g. 0.027), got " + detail::num(unit_weight_mn_m3));
    require_positive(depth_or_height_m, "depth_or_height_m");
    const double ratio = sigma_cm_mpa / (unit_weight_mn_m3 * depth_or_height_m);
    return app == HbApplication::Tunnel ? 0.47 * std::pow(ratio, -0.94) * sigma_cm_mpa
                                        : 0.72 * std::pow(ratio, -0.91) * sigma_cm_mpa;
}

// La info y los avisos se copian de HbParams (así el aviso de D de HB-2018 llega a c' y φ'). Queda Primary
// porque reproduce los ejemplos resueltos HB-1 y HB-2 del paper.
struct MohrCoulombFit {
    double phi_deg;
    double cohesion_mpa;
    double sigma3max_mpa;
    MethodInfo info;
    std::vector<std::string> warnings;
};

inline MohrCoulombFit hb_mohr_coulomb(double sigma_ci_mpa, const HbParams& p, double sigma3max_mpa) {
    using namespace validation;
    require_positive(sigma_ci_mpa, "sigma_ci_mpa");
    require_positive(sigma3max_mpa, "sigma3max_mpa");
    const double a = p.a, mb = p.mb, s = p.s;
    const double s3n = sigma3max_mpa / sigma_ci_mpa;
    const double t = std::pow(s + mb * s3n, a - 1.0);
    const double k = 6.0 * a * mb * t;
    MohrCoulombFit r{};
    r.phi_deg = std::asin(k / (2.0 * (1.0 + a) * (2.0 + a) + k)) * 180.0 / std::acos(-1.0);
    r.cohesion_mpa = sigma_ci_mpa * ((1.0 + 2.0 * a) * s + (1.0 - a) * mb * s3n) * t /
                     ((1.0 + a) * (2.0 + a) * std::sqrt(1.0 + k / ((1.0 + a) * (2.0 + a))));
    r.sigma3max_mpa = sigma3max_mpa;
    r.info = p.info;
    r.warnings = p.warnings;
    if (sigma_ci_mpa > 400.0) r.warnings.push_back("sigma_ci_mpa > 400: check the unit is MPa (not kg/cm2)");
    return r;
}

struct ModulusResult {
    double value;
    std::string unit;
    MethodInfo info;
    std::vector<std::string> warnings;
};

/// Em en GPa (Hoek et al. 2002).
inline ModulusResult em_hoek2002(double gsi, double d, double sigma_ci_mpa) {
    using namespace validation;
    require_in_range(gsi, 0.0, 100.0, "gsi");
    require_in_range(d, 0.0, 1.0, "d");
    require_positive(sigma_ci_mpa, "sigma_ci_mpa");
    const double f = sigma_ci_mpa <= 100.0 ? std::sqrt(sigma_ci_mpa / 100.0) : 1.0;
    return {(1.0 - d / 2.0) * f * std::pow(10.0, (gsi - 10.0) / 40.0), "GPa",
            {"HB-2002", Verification::Secondary, "Hoek, Carranza-Torres & Corkum (2002)"}, {}};
}

/// Erm en MPa, ecuación simplificada (Hoek y Diederichs 2006).
inline ModulusResult erm_hoek_diederichs_simplified(double gsi, double d) {
    using namespace validation;
    require_in_range(gsi, 0.0, 100.0, "gsi");
    require_in_range(d, 0.0, 1.0, "d");
    return {100000.0 * (1.0 - d / 2.0) / (1.0 + std::exp((75.0 + 25.0 * d - gsi) / 11.0)), "MPa",
            {"HD-2006", Verification::Primary, "Hoek & Diederichs (2006)"}, {}};
}

/// Erm en MPa, ecuación generalizada con el módulo de la roca intacta Ei.
inline ModulusResult erm_hoek_diederichs_generalized(double gsi, double d, double ei_mpa) {
    using namespace validation;
    require_in_range(gsi, 0.0, 100.0, "gsi");
    require_in_range(d, 0.0, 1.0, "d");
    require_positive(ei_mpa, "ei_mpa");
    return {ei_mpa * (0.02 + (1.0 - d / 2.0) / (1.0 + std::exp((60.0 + 15.0 * d - gsi) / 11.0))), "MPa",
            {"HD-2006", Verification::Primary, "Hoek & Diederichs (2006)"}, {}};
}

}  // namespace rockmasspy
