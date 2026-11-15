/**
 * @file excavation.hpp
 * @brief Excavaciones subterráneas en forma cerrada: Kirsch, borde de la elipse, revestimiento de Einstein y Schwartz,
 *        squeezing de Hoek y Marinos, GRC, LDP, sostenimiento (SCC) y su FS en el cruce con la GRC.
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
#include <algorithm>
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "rockmasspy/hoek_brown.hpp"
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
inline void poisson(double v, const std::string& name) {
    validation::require_finite(v, name);
    if (v < 0.0 || v >= 0.5) fail(name, "must be within [0, 0.5)");
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
    // la ecuación 8 ya da ε en %; con pi/p0 >= 0.8 saldría negativa: el sostenimiento detiene el squeezing (ε = 0)
    const double pct = std::max(0.0, (0.2 - 0.25 * y) * std::pow(x, 2.4 * y - 2.0));
    const double rp = std::max(1.0, (1.25 - 0.625 * y) * std::pow(x, y - 0.57));  // la zona plástica no baja de R
    const char cls = pct < 1 ? 'A' : pct < 2.5 ? 'B' : pct < 5 ? 'C' : pct < 10 ? 'D' : 'E';
    return {pct, rp * radius_m, pct / 100.0 * radius_m, cls, x <= 0.5 && y <= 0.5,
            {"Squeezing-Hoek-Marinos-2000", Verification::PrimaryLaterAuthors,
             "Hoek and Marinos (2000) as reproduced in PRE eq. 8-9 and RST Table A-1; original not read"}};
}

// ---------------------------------------------------------------- GRC (§3, §4.1)

struct GrcPoint {
    double pi_mpa, u_m;
};

struct GrcResult {
    double p_crit_mpa;            // si es <= 0 el terreno no plastifica con pi >= 0
    std::vector<GrcPoint> curve;  // de pi = p0 a pi = 0
    double rp_unsupported_m, u_max_m;
    MethodInfo info;
    std::vector<std::string> notes;
};

struct GrcMcInput {
    double radius_m = validation::unset, p0_mpa = validation::unset, e_mpa = validation::unset;
    double nu = validation::unset, c_mpa = validation::unset, phi_deg = validation::unset;
    double psi_deg = 0.0;
    /// Solo para el modo «equivalente RocSupport» (D2): reemplaza a 2c·cosφ/(1−sinφ) por el σcm global de Hoek-Brown.
    double sigma_cm_override_mpa = validation::unset;
};

struct GrcHbInput {  // a = 0.5
    double radius_m = validation::unset, p0_mpa = validation::unset, g_mpa = validation::unset;
    double nu = validation::unset, sigma_ci_mpa = validation::unset, mb = validation::unset, s = validation::unset;
    double psi_deg = 0.0;
};

namespace excavation_detail {
struct McState {
    double k, kpsi, q, pcr, g;
};
inline void check_pi(double pi, double p0) {
    non_negative(pi, "pi_mpa");
    if (pi > p0) fail("pi_mpa", "must not exceed 'p0_mpa'");
}
inline void check_psi(double psi) {
    validation::require_finite(psi, "psi_deg");
    if (psi < 0.0 || psi >= 90.0) fail("psi_deg", "must be within [0, 90) degrees");
}
inline McState mc_state(const GrcMcInput& in, double pi) {
    positive(in.radius_m, "radius_m");
    positive(in.p0_mpa, "p0_mpa");
    positive(in.e_mpa, "e_mpa");
    poisson(in.nu, "nu");
    validation::require_finite(in.phi_deg, "phi_deg");
    if (in.phi_deg < 1.0 || in.phi_deg >= 90.0) fail("phi_deg", "must be within [1, 90) degrees");
    check_psi(in.psi_deg);
    const bool ovr = !std::isnan(in.sigma_cm_override_mpa);
    non_negative(in.c_mpa, "c_mpa");
    if (ovr) non_negative(in.sigma_cm_override_mpa, "sigma_cm_override_mpa");
    check_pi(pi, in.p0_mpa);
    const double sp = std::sin(rad(in.phi_deg)), sps = std::sin(rad(in.psi_deg));
    McState st{};
    st.k = (1 + sp) / (1 - sp);
    st.kpsi = (1 + sps) / (1 - sps);
    st.q = ovr ? in.sigma_cm_override_mpa : 2 * in.c_mpa * std::cos(rad(in.phi_deg)) / (1 - sp);
    st.pcr = (2 * in.p0_mpa - st.q) / (1 + st.k);
    st.g = in.e_mpa / (2 * (1 + in.nu));
    // sin cohesión la fórmula de rp se divide por cero con pi = 0
    if (st.q <= 0.0 && pi <= 0.0) fail(ovr ? "sigma_cm_override_mpa" : "c_mpa", "must be positive when pi_mpa is 0");
    return st;
}

template <class Disp, class Rad>
inline GrcResult grc_curve(double p0, double p_crit, int n_points, MethodInfo info, Disp disp, Rad rad_fn) {
    if (n_points < 2) fail("n_points", "must be at least 2");
    GrcResult r{p_crit, {}, rad_fn(0.0), disp(0.0), std::move(info), {}};
    for (int i = 0; i < n_points; ++i) {
        const double pi = i == n_points - 1 ? 0.0 : p0 * (1.0 - double(i) / (n_points - 1));
        r.curve.push_back({pi, disp(pi)});
    }
    return r;
}
}  // namespace excavation_detail

/// Radio plástico de Salençon / Duncan Fama (la dilatancia no lo cambia); R si pi >= pcr.
inline double grc_mc_plastic_radius(const GrcMcInput& in, double pi_mpa) {
    const auto st = excavation_detail::mc_state(in, pi_mpa);
    if (pi_mpa >= st.pcr) return in.radius_m;
    return in.radius_m * std::pow(2 * (in.p0_mpa * (st.k - 1) + st.q) / ((1 + st.k) * ((st.k - 1) * pi_mpa + st.q)),
                                  1 / (st.k - 1));
}

/// Convergencia de la pared (positiva hacia adentro): elástica de PRE ec. 5, plástica de Salençon con Kψ (RS2-S p. 15).
inline double grc_mc_displacement(const GrcMcInput& in, double pi_mpa) {
    const auto st = excavation_detail::mc_state(in, pi_mpa);
    if (pi_mpa >= st.pcr) return in.radius_m * (in.p0_mpa - pi_mpa) / (2 * st.g);
    const double k = st.k, kp = st.kpsi, nu = in.nu;
    const double x = pi_mpa + st.q / (k - 1);
    const double ratio = grc_mc_plastic_radius(in, pi_mpa) / in.radius_m;
    return in.radius_m / (2 * st.g) *
           ((2 * nu - 1) * (in.p0_mpa + st.q / (k - 1)) + (1 - nu) * (k * k - 1) / (k + kp) * x * std::pow(ratio, k + kp) +
            ((1 - nu) * (k * kp + 1) / (k + kp) - nu) * x);
}

inline GrcResult grc_mc(const GrcMcInput& in, int n_points = 50) {
    const bool ovr = !std::isnan(in.sigma_cm_override_mpa);
    GrcResult r = excavation_detail::grc_curve(
        in.p0_mpa, excavation_detail::mc_state(in, in.p0_mpa).pcr, n_points,
        ovr ? MethodInfo{"GRC-HB-equivalent-MC", Verification::Secondary,
                         "RocSupport-style Mohr-Coulomb equivalent of Hoek-Brown (RST example 1; FORMULAS 3.4)"}
            : MethodInfo{"GRC-MC-Salencon-1969", Verification::PrimaryLaterAuthors,
                         "Salencon (1969) as reproduced in RS2-S p. 14-15 and Hoek PRE eq. 1-7; original not read"},
        [&](double pi) { return grc_mc_displacement(in, pi); }, [&](double pi) { return grc_mc_plastic_radius(in, pi); });
    if (ovr)
        r.notes.push_back(
            "equivalent Mohr-Coulomb mixes the global rock mass strength with the friction angle of the tunnel fit, as "
            "RocSupport does");
    return r;
}

/// Equivalente Mohr-Coulomb al estilo RocSupport (D2): σcm global, φ y c del ajuste con σ3max de túneles
/// (0.47·σcm·(σcm/p0)^−0.94, Hoek-Carranza-Torres-Corkum 2002) y Erm de 2002.
inline GrcMcInput grc_mc_from_hb(double sigma_ci_mpa, double gsi, double mi, double d, double p0_mpa, double radius_m,
                                 double nu, HbEdition edition) {
    excavation_detail::positive(p0_mpa, "p0_mpa");
    const HbParams p = hb_params(gsi, mi, d, edition);
    const double scm = hb_global_strength(sigma_ci_mpa, p);
    const double s3max = 0.47 * scm * std::pow(scm / p0_mpa, -0.94);
    const MohrCoulombFit fit = hb_mohr_coulomb(sigma_ci_mpa, p, s3max);
    GrcMcInput in;
    in.radius_m = radius_m;
    in.p0_mpa = p0_mpa;
    in.e_mpa = em_hoek2002(gsi, d, sigma_ci_mpa).value * 1000.0;
    in.nu = nu;
    in.c_mpa = fit.cohesion_mpa;
    in.phi_deg = fit.phi_deg;
    in.sigma_cm_override_mpa = scm;
    return in;
}

namespace excavation_detail {
struct HbState {
    double so, pi_cr_norm, pi_cr, mbs;
};
inline HbState hb_state(const GrcHbInput& in, double pi) {
    positive(in.radius_m, "radius_m");
    positive(in.p0_mpa, "p0_mpa");
    positive(in.g_mpa, "g_mpa");
    poisson(in.nu, "nu");
    positive(in.sigma_ci_mpa, "sigma_ci_mpa");
    positive(in.mb, "mb");
    non_negative(in.s, "s");
    check_psi(in.psi_deg);
    check_pi(pi, in.p0_mpa);
    HbState h{};
    h.mbs = in.mb * in.sigma_ci_mpa;
    const double s0 = in.s / (in.mb * in.mb);
    h.so = in.p0_mpa / h.mbs + s0;
    h.pi_cr_norm = std::pow(1 - std::sqrt(1 + 16 * h.so), 2) / 16;
    h.pi_cr = (h.pi_cr_norm - s0) * h.mbs;
    return h;
}
}  // namespace excavation_detail

/// Radio plástico de Carranza-Torres y Fairhurst; R si pi >= pi_cr.
inline double grc_hb_plastic_radius(const GrcHbInput& in, double pi_mpa) {
    const auto h = excavation_detail::hb_state(in, pi_mpa);
    if (pi_mpa >= h.pi_cr) return in.radius_m;
    const double pn = pi_mpa / h.mbs + in.s / (in.mb * in.mb);
    return in.radius_m * std::exp(2 * (std::sqrt(h.pi_cr_norm) - std::sqrt(pn)));
}

/// Convergencia de la pared de Carranza-Torres y Fairhurst (CC02 ec. 5-11), pequeñas deformaciones.
inline double grc_hb_displacement(const GrcHbInput& in, double pi_mpa) {
    using excavation_detail::rad;
    const auto h = excavation_detail::hb_state(in, pi_mpa);
    if (pi_mpa >= h.pi_cr) return (in.p0_mpa - pi_mpa) * in.radius_m / (2 * in.g_mpa);
    const double sps = std::sin(rad(in.psi_deg)), kp = (1 + sps) / (1 - sps), nu = in.nu;
    const double ratio = grc_hb_plastic_radius(in, pi_mpa) / in.radius_m, ln = std::log(ratio);
    const double dso = h.so - h.pi_cr_norm, pw = std::pow(ratio, kp + 1);
    const double f = (kp - 1) / (kp + 1) + 2 / (kp + 1) * pw + (1 - 2 * nu) / (4 * dso) * ln * ln -
                     ((1 - 2 * nu) / (kp + 1) * std::sqrt(h.pi_cr_norm) / dso +
                      (1 - nu) / 2 * (kp - 1) / ((kp + 1) * (kp + 1)) / dso) *
                         ((kp + 1) * ln - pw + 1);
    return f * in.radius_m * (in.p0_mpa - h.pi_cr) / (2 * in.g_mpa);
}

inline GrcResult grc_hb(const GrcHbInput& in, int n_points = 50) {
    return excavation_detail::grc_curve(
        in.p0_mpa, excavation_detail::hb_state(in, in.p0_mpa).pi_cr, n_points,
        {"GRC-HB-Carranza-Torres-Fairhurst-2000", Verification::PrimaryLaterAuthors,
         "Carranza-Torres and Fairhurst (2000) as reproduced in CC02 p. 53-55 eq. 5-11; original not read"},
        [&](double pi) { return grc_hb_displacement(in, pi); }, [&](double pi) { return grc_hb_plastic_radius(in, pi); });
}

// ---------------------------------------------------------------- Esfuerzos de HB 1982 y de Reed (§4.2, §6.1)

struct RadialStress {
    double sigma_r, sigma_theta;
    MethodInfo info;
};

struct Hb1982Input {
    double p0_mpa = validation::unset, radius_m = validation::unset, sigma_c_mpa = validation::unset;
    double m = validation::unset, s = validation::unset, mr = validation::unset, sr = validation::unset;
    double pi_mpa = 0.0;
};

namespace excavation_detail {
inline void hb1982_check(const Hb1982Input& in) {
    positive(in.p0_mpa, "p0_mpa");
    positive(in.radius_m, "radius_m");
    positive(in.sigma_c_mpa, "sigma_c_mpa");
    positive(in.m, "m");
    non_negative(in.s, "s");
    positive(in.mr, "mr");
    non_negative(in.sr, "sr");
    non_negative(in.pi_mpa, "pi_mpa");
}
inline double hb1982_m_factor(const Hb1982Input& in) {
    return 0.5 * std::sqrt(std::pow(in.m / 4, 2) + in.m * in.p0_mpa / in.sigma_c_mpa + in.s) - in.m / 8;
}
}  // namespace excavation_detail

/// Radio re del contorno elastoplástico (HB 1982 con resistencia residual); R si no hay zona plástica.
inline double hb1982_plastic_radius(const Hb1982Input& in) {
    excavation_detail::hb1982_check(in);
    const double sc = in.sigma_c_mpa, mr = in.mr, sr = in.sr, M = excavation_detail::hb1982_m_factor(in);
    const double n = 2 / (mr * sc) * std::sqrt(mr * sc * in.p0_mpa + sr * sc * sc - mr * sc * sc * M);
    const double re = in.radius_m * std::exp(n - 2 / (mr * sc) * std::sqrt(mr * sc * in.pi_mpa + sr * sc * sc));
    return std::max(re, in.radius_m);
}

inline MethodInfo hb1982_info() {
    return {"HB-1982-brittle", Verification::PrimaryLaterAuthors,
            "Hoek and Brown (1982) with residual strength as reproduced in RS2-S p. 22 (problem 3); original not read"};
}

inline RadialStress hb1982_stress(const Hb1982Input& in, double r_m) {
    const double re = hb1982_plastic_radius(in);
    validation::require_finite(r_m, "r_m");
    if (r_m < in.radius_m) excavation_detail::fail("r_m", "must be at least 'radius_m'");
    const double sc = in.sigma_c_mpa;
    if (r_m < re) {
        const double l = std::log(r_m / in.radius_m), b = std::sqrt(in.mr * sc * in.pi_mpa + in.sr * sc * sc);
        const double sr_ = in.mr * sc / 4 * l * l + l * b + in.pi_mpa;
        return {sr_, sr_ + std::sqrt(in.mr * sc * sr_ + in.sr * sc * sc), hb1982_info()};
    }
    // sin zona plástica el contorno elástico pasa por la presión interna
    const double sre = re > in.radius_m ? in.p0_mpa - excavation_detail::hb1982_m_factor(in) * sc : in.pi_mpa;
    const double d = (in.p0_mpa - sre) * (re / r_m) * (re / r_m);
    return {in.p0_mpa - d, in.p0_mpa + d, hb1982_info()};
}

struct ReedInput {
    double q_mpa = validation::unset, radius_m = validation::unset, c_peak_mpa = validation::unset;
    double c_res_mpa = validation::unset, phi_deg = validation::unset, pi_mpa = 0.0;
};

namespace excavation_detail {
struct ReedState {
    double k, sc, pp, rbar;
};
inline ReedState reed_state(const ReedInput& in) {
    positive(in.q_mpa, "q_mpa");
    positive(in.radius_m, "radius_m");
    positive(in.c_peak_mpa, "c_peak_mpa");
    non_negative(in.c_res_mpa, "c_res_mpa");
    non_negative(in.pi_mpa, "pi_mpa");
    validation::require_finite(in.phi_deg, "phi_deg");
    if (in.phi_deg < 1.0 || in.phi_deg >= 90.0) fail("phi_deg", "must be within [1, 90) degrees");
    // sin cohesión residual ni presión interna, p' = 0 y r̄ se divide por cero
    if (in.c_res_mpa == 0.0 && in.pi_mpa == 0.0) fail("c_res_mpa", "must be positive when pi_mpa is 0");
    const double sp = std::sin(rad(in.phi_deg)), cp = std::cos(rad(in.phi_deg));
    ReedState s{};
    s.k = (1 + sp) / (1 - sp);
    s.sc = 2 * in.c_peak_mpa * cp / (1 - sp);
    s.pp = 2 * in.c_res_mpa * cp / (1 - sp) / (s.k - 1);
    const double ratio = (s.pp + (2 * in.q_mpa - s.sc) / (s.k + 1)) / (in.pi_mpa + s.pp);
    s.rbar = ratio > 1.0 ? in.radius_m * std::pow(ratio, 1 / (s.k - 1)) : in.radius_m;
    return s;
}
}  // namespace excavation_detail

/// Radio r̄ del contorno elastoplástico de Reed; ro si no hay zona plástica.
inline double reed_plastic_radius(const ReedInput& in) { return excavation_detail::reed_state(in).rbar; }

inline MethodInfo reed_info() {
    return {"Reed-1986", Verification::PrimaryLaterAuthors,
            "Reed (1986) brittle-plastic stresses as reproduced in RS2-S p. 176 (problem 30); original not read"};
}

inline RadialStress reed_stress(const ReedInput& in, double r_m) {
    const auto s = excavation_detail::reed_state(in);
    validation::require_finite(r_m, "r_m");
    if (r_m < in.radius_m) excavation_detail::fail("r_m", "must be at least 'radius_m'");
    if (r_m < s.rbar) {
        const double t = (in.pi_mpa + s.pp) * std::pow(r_m / in.radius_m, s.k - 1);
        return {t - s.pp, s.k * t - s.pp, reed_info()};
    }
    if (s.rbar > in.radius_m) {
        const double a = std::pow(s.rbar / r_m, 2) * ((s.k - 1) * in.q_mpa + s.sc) / (s.k + 1);
        return {in.q_mpa - a, in.q_mpa + a, reed_info()};
    }
    const double a = std::pow(in.radius_m / r_m, 2) * (in.q_mpa - in.pi_mpa);  // todo elástico: σr(ro) = pi
    return {in.q_mpa - a, in.q_mpa + a, reed_info()};
}

// ---------------------------------------------------------------- LDP (§7)

/// X* = x/R con x positivo detrás del frente (dentro del túnel ya excavado) y negativo delante.
enum class Ldp { PANET1995, UNLU_GERCEK2003, CHERN1998, VD2009 };

inline MethodInfo ldp_info(Ldp model) {
    static const char* const ids[] = {"LDP-Panet-1995", "LDP-Unlu-Gercek-2003", "LDP-Chern-1998",
                                      "LDP-Vlachopoulos-Diederichs-2009"};
    static const char* const who[] = {"Panet (1995)", "Unlu and Gercek (2003)", "Fit to Chern et al. (1998)",
                                      "Vlachopoulos and Diederichs (2009)"};
    const int i = static_cast<int>(model);
    return {ids[i], Verification::PrimaryLaterAuthors,
            std::string(who[i]) + " as reproduced in KL08 Appendix 1 eq. A1.1-A1.7; original not read"};
}

namespace excavation_detail {
inline void ldp_check(double rp_over_r, double nu) {
    validation::require_finite(rp_over_r, "rp_over_r");
    if (rp_over_r < 1.0) fail("rp_over_r", "must be at least 1");
    poisson(nu, "nu");
}
}  // namespace excavation_detail

/// u/umax en X* (KL08 ec. A1.1-A1.7). rp_over_r es el radio plástico sin sostenimiento (solo VD2009); nu, solo
/// Unlu-Gercek.
inline double ldp_ratio(Ldp model, double x_over_r, double rp_over_r, double nu) {
    using namespace excavation_detail;
    validation::require_finite(x_over_r, "x_over_r");
    ldp_check(rp_over_r, nu);
    const double x = x_over_r;
    switch (model) {
        case Ldp::PANET1995:
            if (x < 0.0) fail("x_over_r", "must not be negative for PANET1995 (it starts at the face)");
            return 0.25 + 0.75 * (1 - std::pow(3 / (3 + 4 * x), 2));
        case Ldp::UNLU_GERCEK2003: {
            const double u0 = 0.22 * nu + 0.19;
            if (x <= 0.0) return u0 + (-0.22 * nu - 0.19) * (1 - std::exp((0.73 * nu + 0.81) * x));
            const double bb = 0.39 * nu + 0.65;
            return u0 + (-0.22 * nu + 0.81) * (1 - std::pow(bb / (bb + x), 2));
        }
        case Ldp::CHERN1998:
            return std::pow(1 + std::exp(-x / 1.10), -1.7);
        case Ldp::VD2009: {
            const double u0 = std::exp(-0.15 * rp_over_r) / 3;
            return x <= 0.0 ? u0 * std::exp(x) : 1 - (1 - u0) * std::exp(-3 * x / (2 * rp_over_r));
        }
    }
    fail("ldp", "is not a known LDP model");
}

/// X* a la que el LDP de Vlachopoulos y Diederichs llega a u/umax = ratio (las demás no tienen inversa cerrada).
inline double ldp_distance(Ldp model, double ratio, double rp_over_r, double nu) {
    using namespace excavation_detail;
    if (model != Ldp::VD2009) fail("ldp", "has no closed-form inverse; only VD2009 is supported");
    validation::require_finite(ratio, "ratio");
    if (!(ratio > 0.0 && ratio < 1.0)) fail("ratio", "must be within (0, 1)");
    ldp_check(rp_over_r, nu);
    const double u0 = std::exp(-0.15 * rp_over_r) / 3;
    return ratio < u0 ? std::log(ratio / u0) : -2.0 / 3.0 * rp_over_r * std::log((1 - ratio) / (1 - u0));
}

// ---------------------------------------------------------------- SCC y cruce con la GRC (§8, §9)

/// Sostenimiento elástico-perfectamente plástico: p = stiffness·(u − u_in)/R hasta psm (rigidez en MPa por u/R).
struct SupportElement {
    std::string code;
    double psm_mpa = validation::unset, stiffness_mpa = validation::unset;
};

inline MethodInfo scc_info() {
    return {"SCC-elastic-perfectly-plastic", Verification::PrimaryLaterAuthors,
            "RocSupport support model (psm, eps_sm) as described in RST pp. 32-36 and the RocSupport help"};
}

/// Rigidez = psm/εsm (RST p. 36); eps_sm como fracción (0.002 = 0.2 %).
inline SupportElement support_from_eps(const std::string& code, double psm_mpa, double eps_sm) {
    excavation_detail::positive(psm_mpa, "psm_mpa");
    excavation_detail::positive(eps_sm, "eps_sm");
    return {code, psm_mpa, psm_mpa / eps_sm};
}

/// Rigidez del anillo grueso [V2, Secondary: UBC según Harrison y Hudson (2000)]; la psm la da el usuario.
inline double thick_ring_stiffness(double e_mpa, double nu, double radius_m, double thickness_m) {
    using namespace excavation_detail;
    positive(e_mpa, "e_mpa");
    poisson(nu, "nu");
    positive(radius_m, "radius_m");
    positive(thickness_m, "thickness_m");
    if (thickness_m >= radius_m) fail("thickness_m", "must be less than 'radius_m'");
    const double a2 = radius_m * radius_m, b2 = (radius_m - thickness_m) * (radius_m - thickness_m);
    return e_mpa / (1 + nu) * (a2 - b2) / ((1 - 2 * nu) * a2 + b2);
}

/// STIFFNESS: rigideces sumadas y cada elemento contra su psm (Oreste 2009). ROCSUPPORT3: psm sumado y εsm
/// promediado (RST pp. 37-38). ROCSUPPORT: psm sumado y εsm máximo (ayuda de RocSupport actual).
enum class Combination { STIFFNESS, ROCSUPPORT3, ROCSUPPORT };

/// En los modos RocSupport junta los elementos en uno solo; en STIFFNESS los devuelve tal cual.
inline std::vector<SupportElement> combine_supports(const std::vector<SupportElement>& elements, Combination mode) {
    using namespace excavation_detail;
    if (elements.empty()) fail("elements", "must contain at least one support");
    for (const auto& e : elements) {
        positive(e.psm_mpa, "psm_mpa");
        positive(e.stiffness_mpa, "stiffness_mpa");
    }
    if (mode == Combination::STIFFNESS) return elements;
    SupportElement c{"", 0.0, 0.0};
    double eps = 0.0;
    for (const auto& e : elements) {
        c.code += (c.code.empty() ? "" : "+") + e.code;
        c.psm_mpa += e.psm_mpa;
        const double ei = e.psm_mpa / e.stiffness_mpa;
        eps = mode == Combination::ROCSUPPORT3 ? eps + ei / double(elements.size()) : std::max(eps, ei);
    }
    c.stiffness_mpa = c.psm_mpa / eps;
    return {c};
}

struct Interaction {
    bool found = false;
    double p_eq_mpa = 0.0, u_eq_m = 0.0;
    std::optional<double> fs;           // D6: con la recta elástica prolongada si algún elemento fluye
    std::vector<double> fs_by_element;  // psm_i/p_i en el cruce de la recta elástica
    bool elastic = false;
    double rp_eq_m = 0.0, strain_eq_pct = 0.0;
    MethodInfo info;
    std::vector<std::string> warnings;
};

namespace excavation_detail {
template <class Disp, class Rad>
inline Interaction interaction(double radius, double p0, Disp disp, Rad rp_fn, const std::vector<SupportElement>& elements,
                               double u_install_m, Combination mode, std::optional<Ldp> ldp) {
    const auto els = combine_supports(elements, mode);
    non_negative(u_install_m, "u_install_m");
    const double umax = disp(0.0);  // valida la entrada de la GRC
    const bool rs = mode != Combination::STIFFNESS;
    Interaction r;
    r.info = {"Support-interaction", rs ? Verification::Secondary : Verification::PrimaryLaterAuthors,
              rs ? "GRC-SCC crossing (RST pp. 14-15, 36) with RocSupport combination of supports (RST pp. 37-38, help)"
                 : "GRC-SCC crossing (RST pp. 14-15, 36) with summed stiffness of supports (Oreste 2009 eq. 24-25)"};
    if (ldp && (*ldp == Ldp::PANET1995 || *ldp == Ldp::UNLU_GERCEK2003) && rp_fn(0.0) > 2 * radius)
        r.warnings.push_back("LDP not valid for Rp > 2R; use VD2009");
    if (u_install_m >= umax) {
        r.u_eq_m = umax;
        r.rp_eq_m = rp_fn(0.0);
        r.strain_eq_pct = umax / radius * 100;
        r.warnings.push_back("support does not intersect the ground reaction curve");
        return r;
    }
    // Bisección en pi, equivalente a hacerla en u sin invertir la GRC: g(pi) = pi − p_SCC(u(pi)) crece con pi.
    auto cross = [&](bool capped) {
        double lo = 0.0, hi = p0;
        // tope relativo a la raíz: con instalación muy tardía la presión del cruce puede ser ínfima
        for (int i = 0; i < 400 && hi - lo > 1e-13 * hi; ++i) {
            const double mid = 0.5 * (lo + hi), du = std::max(disp(mid) - u_install_m, 0.0) / radius;
            double s = 0.0;
            for (const auto& e : els) s += capped ? std::min(e.stiffness_mpa * du, e.psm_mpa) : e.stiffness_mpa * du;
            (mid > s ? hi : lo) = mid;
        }
        return lo;  // g(lo) <= 0 garantiza u(lo) > u_in: Δu y el FS quedan positivos
    };
    const double p_lin = cross(false), du_lin = (disp(p_lin) - u_install_m) / radius;
    for (const auto& e : els) r.fs_by_element.push_back(e.psm_mpa / (e.stiffness_mpa * du_lin));
    r.fs = *std::min_element(r.fs_by_element.begin(), r.fs_by_element.end());
    r.elastic = *r.fs >= 1.0;
    r.found = true;
    r.p_eq_mpa = r.elastic ? p_lin : cross(true);  // si algo fluye, el equilibrio real cae en la meseta
    r.u_eq_m = disp(r.p_eq_mpa);
    r.rp_eq_m = rp_fn(r.p_eq_mpa);
    r.strain_eq_pct = r.u_eq_m / radius * 100;
    return r;
}
}  // namespace excavation_detail

/// Cruce de la GRC de Mohr-Coulomb con el sostenimiento instalado cuando la pared ya convergió u_install_m. Con
/// `ldp` se añade el aviso de D4 si el modelo no vale para el radio plástico de esta GRC.
inline Interaction interaction_mc(const GrcMcInput& in, const std::vector<SupportElement>& elements, double u_install_m,
                                  Combination mode, std::optional<Ldp> ldp = std::nullopt) {
    return excavation_detail::interaction(
        in.radius_m, in.p0_mpa, [&](double pi) { return grc_mc_displacement(in, pi); },
        [&](double pi) { return grc_mc_plastic_radius(in, pi); }, elements, u_install_m, mode, ldp);
}

inline Interaction interaction_hb(const GrcHbInput& in, const std::vector<SupportElement>& elements, double u_install_m,
                                  Combination mode, std::optional<Ldp> ldp = std::nullopt) {
    return excavation_detail::interaction(
        in.radius_m, in.p0_mpa, [&](double pi) { return grc_hb_displacement(in, pi); },
        [&](double pi) { return grc_hb_plastic_radius(in, pi); }, elements, u_install_m, mode, ldp);
}

}  // namespace rockmasspy
