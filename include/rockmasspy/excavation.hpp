/**
 * @file excavation.hpp
 * @brief Excavaciones subterráneas en forma cerrada: Kirsch, borde de la elipse, revestimiento de Einstein y Schwartz
 *        y squeezing de Hoek y Marinos.
 *
 * Fuentes (ecuaciones en docs/investigacion/FORMULAS_FASE8B.md §1, §2, §10 y §11.3): Kirsch (1898) según RS2-S p. 8 y
 * CC02 p. 26; elipse de Inglis (1913) según CC02 p. 26 (extremos deducidos de la misma fórmula); Einstein y Schwartz
 * (1979) según RS2-S p. 41; Hoek y Marinos (2000) según PRE ec. 8-9 y RST Tabla A-1. Los originales no se leyeron:
 * por eso PrimaryLaterAuthors.
 *
 * Convención: compresión positiva; MPa, m y MN por metro de túnel; deformación plana; ángulos en grados.
 * p es el esfuerzo vertical, K·p el horizontal; θ se mide desde el eje horizontal. Los mensajes de error nombran el
 * parámetro y nunca repiten el valor recibido.
 */

#pragma once

#include <cmath>
#include <stdexcept>
#include <string>
#include <utility>

#include "rockmasspy/method_info.hpp"
#include "rockmasspy/validation.hpp"

namespace rockmasspy {

namespace excavation_detail {
constexpr double kPi = 3.14159265358979323846;
inline double rad(double deg) { return deg * kPi / 180.0; }

[[noreturn]] inline void fail(const std::string& name, const std::string& what) {
    throw std::invalid_argument("Domain error [RockMassPy]: parameter '" + name + "' " + what);
}
/// Como validation::require_positive, pero sin repetir el valor.
inline void positive(double v, const std::string& name) {
    validation::require_finite(v, name);
    if (!(v > 0.0)) fail(name, "must be strictly positive (> 0)");
}
inline void non_negative(double v, const std::string& name) {
    validation::require_finite(v, name);
    if (v < 0.0) fail(name, "must not be negative (>= 0)");
}
}  // namespace excavation_detail

// ---------------------------------------------------------------- Kirsch (§1)

struct KirschStress {
    double sigma_r, sigma_theta, tau_r_theta;  // MPa
    MethodInfo info;
};
struct KirschBoundary {
    double crown_mpa, sidewall_mpa;
    MethodInfo info;
};

inline MethodInfo kirsch_info() {
    return {"Kirsch-1898", Verification::PrimaryLaterAuthors,
            "Kirsch (1898) as reproduced in RS2-S p. 8 and CC02 p. 26; originals not read"};
}

/// Esfuerzos de Kirsch en (r, θ) alrededor de un hueco circular, con p vertical y K·p horizontal.
inline KirschStress kirsch_stress(double p_mpa, double k_ratio, double radius_m, double r_m, double theta_deg) {
    using namespace excavation_detail;
    validation::require_finite(p_mpa, "p_mpa");
    non_negative(k_ratio, "k_ratio");
    positive(radius_m, "radius_m");
    validation::require_finite(r_m, "r_m");
    if (r_m < radius_m) fail("r_m", "must be at least 'radius_m'");
    validation::require_finite(theta_deg, "theta_deg");
    const double p1 = k_ratio * p_mpa, p2 = p_mpa;  // horizontal, vertical
    const double s = (radius_m / r_m) * (radius_m / r_m), s2 = s * s;
    const double c2 = std::cos(2.0 * rad(theta_deg)), sn2 = std::sin(2.0 * rad(theta_deg));
    return {(p1 + p2) / 2 * (1 - s) + (p1 - p2) / 2 * (1 - 4 * s + 3 * s2) * c2,
            (p1 + p2) / 2 * (1 + s) - (p1 - p2) / 2 * (1 + 3 * s2) * c2,
            -(p1 - p2) / 2 * (1 + 2 * s - 3 * s2) * sn2, kirsch_info()};
}

/// σθ en el borde: hastial 3p − K·p, corona 3K·p − p.
inline KirschBoundary kirsch_boundary(double p_mpa, double k_ratio) {
    validation::require_finite(p_mpa, "p_mpa");
    excavation_detail::non_negative(k_ratio, "k_ratio");
    return {3 * k_ratio * p_mpa - p_mpa, 3 * p_mpa - k_ratio * p_mpa, kirsch_info()};
}

// ---------------------------------------------------------------- Elipse (§2)

struct EllipseEnds {
    double crown_mpa, sidewall_mpa;
    MethodInfo info;
};

inline MethodInfo ellipse_info() {
    return {"Ellipse-Inglis-1913", Verification::PrimaryLaterAuthors,
            "Inglis (1913) as adapted in CC02 p. 26 Fig. 1c; axis ends deduced from the same formula"};
}

/// σθ en el borde de una elipse de semiejes a (horizontal) y b (vertical); σ1 vertical, σ3 horizontal.
inline double ellipse_boundary_stress(double sigma1_mpa, double sigma3_mpa, double a_m, double b_m, double theta_deg) {
    using namespace excavation_detail;
    validation::require_finite(sigma1_mpa, "sigma1_mpa");
    validation::require_finite(sigma3_mpa, "sigma3_mpa");
    positive(a_m, "a_m");
    positive(b_m, "b_m");
    validation::require_finite(theta_deg, "theta_deg");
    const double s2 = std::pow(std::sin(rad(theta_deg)), 2), c2 = std::pow(std::cos(rad(theta_deg)), 2);
    const double sum = sigma1_mpa + sigma3_mpa;
    return sum - ((a_m - b_m) * sum + (a_m + b_m) * (sigma1_mpa - sigma3_mpa)) * (a_m * s2 - b_m * c2) /
                     (a_m * a_m * s2 + b_m * b_m * c2);
}

/// Extremos de los ejes con q = W/H: hastial p(1 − K + 2q), corona p(K − 1 + 2K/q).
inline EllipseEnds ellipse_ends(double p_mpa, double k_ratio, double width_m, double height_m) {
    using namespace excavation_detail;
    validation::require_finite(p_mpa, "p_mpa");
    non_negative(k_ratio, "k_ratio");
    positive(width_m, "width_m");
    positive(height_m, "height_m");
    const double q = width_m / height_m;
    return {p_mpa * (k_ratio - 1 + 2 * k_ratio / q), p_mpa * (1 - k_ratio + 2 * q), ellipse_info()};
}

// ---------------------------------------------------------------- Einstein y Schwartz (§11.3)

struct EinsteinSchwartzInput {
    double sigma_v_mpa = validation::unset, k_ratio = validation::unset;
    double e_rock_mpa = validation::unset, nu_rock = validation::unset;
    double e_lining_mpa = validation::unset, nu_lining = validation::unset;
    double thickness_m = validation::unset, radius_m = validation::unset, theta_deg = validation::unset;
};

struct LiningForces {
    double n_mn, m_mnm;  // empuje y momento por metro de túnel
    double c_star, f_star;
    MethodInfo info;
};

/// Revestimiento elástico en medio elástico con campo no hidrostático (A = t, I = t³/12 por metro).
inline LiningForces einstein_schwartz(const EinsteinSchwartzInput& in) {
    using namespace excavation_detail;
    validation::require_finite(in.sigma_v_mpa, "sigma_v_mpa");
    non_negative(in.k_ratio, "k_ratio");
    positive(in.e_rock_mpa, "e_rock_mpa");
    positive(in.e_lining_mpa, "e_lining_mpa");
    positive(in.thickness_m, "thickness_m");
    positive(in.radius_m, "radius_m");
    validation::require_finite(in.theta_deg, "theta_deg");
    for (const auto& [v, nm] : {std::pair<double, const char*>{in.nu_rock, "nu_rock"},
                                std::pair<double, const char*>{in.nu_lining, "nu_lining"}}) {
        validation::require_finite(v, nm);
        if (v < 0.0 || v >= 0.5) fail(nm, "must be within [0, 0.5)");
    }
    const double a = in.radius_m, nu = in.nu_rock, K = in.k_ratio;
    const double A = in.thickness_m, I = std::pow(in.thickness_m, 3) / 12.0;
    const double ratio = in.e_rock_mpa * (1 - in.nu_lining * in.nu_lining) / (in.e_lining_mpa * (1 - nu * nu));
    const double C = ratio * a / A, F = ratio * a * a * a / I;
    const double beta = (C * (6 + F) * (1 - nu) + 2 * F * nu) / (3 * C + 3 * F + 2 * C * F * (1 - nu));
    const double b2 = C * (1 - nu) / (2 * (C * (1 - nu) + 4 * nu - 6 * beta - 3 * beta * C * (1 - nu)));
    const double a2 = beta * b2;
    const double a0 = C * F * (1 - nu) / (C + F + C * F * (1 - nu));
    const double c2t = std::cos(2 * rad(in.theta_deg)), sv = in.sigma_v_mpa;
    return {a * sv / 2 * ((1 + K) * (1 - a0) + (1 - K) * (1 + 2 * a2) * c2t),
            a * a * sv / 4 * (1 - K) * (1 - 2 * a2 + 2 * b2) * c2t, C, F,
            {"Lining-Einstein-Schwartz-1979", Verification::PrimaryLaterAuthors,
             "Einstein and Schwartz (1979) as reproduced in RS2-S p. 41 (problem 7); original not read"}};
}

// ---------------------------------------------------------------- Squeezing (§10)

struct Squeezing {
    double strain_pct, plastic_radius_m, wall_displacement_m;
    char squeezing_class;  // 'A'..'E'
    bool in_fit_range;     // σcm/p0 <= 0.5 y pi/p0 <= 0.5 (Fig. 7 de PRE); fuera es una nota, no un error
    MethodInfo info;
};

/// ε % y rp de Hoek y Marinos (2000) con clases A-E (RST Tabla A-1).
inline Squeezing hoek_marinos(double sigma_cm_mpa, double p0_mpa, double pi_mpa, double radius_m) {
    using namespace excavation_detail;
    positive(sigma_cm_mpa, "sigma_cm_mpa");
    positive(p0_mpa, "p0_mpa");
    non_negative(pi_mpa, "pi_mpa");
    positive(radius_m, "radius_m");
    const double x = sigma_cm_mpa / p0_mpa, y = pi_mpa / p0_mpa;
    const double pct = (0.2 - 0.25 * y) * std::pow(x, 2.4 * y - 2.0);  // la ecuación 8 ya da ε en %
    const double rp = (1.25 - 0.625 * y) * std::pow(x, y - 0.57);
    const char cls = pct < 1 ? 'A' : pct < 2.5 ? 'B' : pct < 5 ? 'C' : pct < 10 ? 'D' : 'E';
    return {pct, rp * radius_m, pct / 100.0 * radius_m, cls, x <= 0.5 && y <= 0.5,
            {"Squeezing-Hoek-Marinos-2000", Verification::PrimaryLaterAuthors,
             "Hoek and Marinos (2000) as reproduced in PRE eq. 8-9 and RST Table A-1; original not read"}};
}

}  // namespace rockmasspy
