/**
 * @file lining.hpp
 * @brief Diagramas de capacidad M-N y Q-N de un revestimiento (shotcrete o cercha) y sección compuesta cercha + shotcrete.
 *
 * Fuente (ecuaciones en docs/investigacion/FORMULAS_FASE8B.md §11.1, KL08 Apéndice 2, pp. 47-51): Hoek, Carranza-Torres,
 * Diederichs y Corkum (2008), que reproduce a Carranza-Torres y Diederichs (2009); el original no se leyó, por eso
 * PrimaryLaterAuthors. Son envolventes elásticas de sección no fisurada, sin interacción M-N plástica.
 *
 * Convención: compresión positiva, σt negativa; MPa, m y MN por metro de túnel. Los mensajes de error nombran el
 * parámetro y nunca repiten el valor recibido.
 */

#pragma once

#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "rockmasspy/method_info.hpp"
#include "rockmasspy/validation.hpp"

namespace rockmasspy {

namespace lining_detail {
[[noreturn]] inline void fail(const std::string& name, const std::string& what) {
    throw std::invalid_argument("Domain error [RockMassPy]: parameter '" + name + "' " + what);
}
/// Como validation::require_positive, pero sin repetir el valor.
inline void positive(double v, const std::string& name) {
    validation::require_finite(v, name);
    if (!(v > 0.0)) fail(name, "must be strictly positive (> 0)");
}
}  // namespace lining_detail

struct LiningSection {
    double area_m2 = validation::unset, inertia_m4 = validation::unset, thickness_m = validation::unset;
    double sigma_c_mpa = validation::unset, sigma_t_mpa = validation::unset;  // σt negativa
};

struct LiningForce {
    double n_mn = 0, m_mnm = 0, q_mn = 0;
};

struct CapacityEnvelope {
    double n_max, n_min, n_cr, m_max;                 // MN y MN·m por metro
    std::vector<std::pair<double, double>> vertices;  // (N, M): (Nmax,0), (Ncr,+Mmax), (Nmin,0), (Ncr,-Mmax)
    MethodInfo info;
};

inline MethodInfo lining_capacity_info() {
    return {"Lining-capacity-Carranza-Torres-Diederichs-2009", Verification::PrimaryLaterAuthors,
            "Carranza-Torres and Diederichs (2009) as reproduced in KL08 Appendix 2 pp. 47-51; original not read"};
}

inline void validate_section(const LiningSection& s, double fs) {
    using namespace lining_detail;
    positive(s.area_m2, "area_m2");
    positive(s.inertia_m4, "inertia_m4");
    positive(s.thickness_m, "thickness_m");
    positive(s.sigma_c_mpa, "sigma_c_mpa");
    validation::require_finite(s.sigma_t_mpa, "sigma_t_mpa");
    if (!(s.sigma_t_mpa < 0.0)) fail("sigma_t_mpa", "must be negative (tension is negative)");
    positive(fs, "fs");
}

/// Rombo M-N (A2.13-A2.16) con σ/FS.
inline CapacityEnvelope capacity_mn(const LiningSection& s, double fs) {
    validate_section(s, fs);
    const double n_max = s.area_m2 * s.sigma_c_mpa / fs, n_min = s.area_m2 * s.sigma_t_mpa / fs;
    const double n_cr = s.area_m2 * (s.sigma_c_mpa + s.sigma_t_mpa) / (2 * fs);
    const double m_max = (s.sigma_c_mpa - s.sigma_t_mpa) / fs * s.inertia_m4 / s.thickness_m;
    return {n_max, n_min, n_cr, m_max, {{n_max, 0}, {n_cr, m_max}, {n_min, 0}, {n_cr, -m_max}}, lining_capacity_info()};
}

/// Cortante crítico (A2.23): por encima no queda empuje que lo resista.
inline double q_crit(const LiningSection& s, double fs) {
    validate_section(s, fs);
    return s.area_m2 / fs * std::sqrt(-4 * s.sigma_c_mpa * s.sigma_t_mpa / 9.0);
}

/// Empuje N admisible con el cortante Q (A2.21-A2.22), en compresión o en tracción.
inline double shear_capacity_n(const LiningSection& s, double q_mn, double fs, bool compression) {
    validate_section(s, fs);
    validation::require_finite(q_mn, "q_mn");
    if (std::abs(q_mn) > q_crit(s, fs)) lining_detail::fail("q_mn", "exceeds the critical shear of the section");
    const double sig = compression ? s.sigma_c_mpa : s.sigma_t_mpa;
    return sig * s.area_m2 / fs - 9 * q_mn * q_mn * fs / (4 * sig * s.area_m2);
}

struct CapacityCheck {
    std::vector<int> outside;  // índices de los pares fuera del rombo
    bool all_inside;
    MethodInfo info;
};

/// Qué pares (N, M) caen fuera del rombo M-N (el borde cuenta como dentro). No revisa Q.
inline CapacityCheck check_capacity(const LiningSection& s, const std::vector<LiningForce>& forces, double fs) {
    const auto env = capacity_mn(s, fs);
    CapacityCheck out{{}, true, lining_capacity_info()};
    for (std::size_t i = 0; i < forces.size(); ++i) {
        validation::require_finite(forces[i].n_mn, "n_mn");
        validation::require_finite(forces[i].m_mnm, "m_mnm");
        const double n = forces[i].n_mn;
        const double span = n >= env.n_cr ? env.n_max - env.n_cr : env.n_cr - env.n_min;
        const double lim = env.m_max * (1 - std::abs(n - env.n_cr) / span);
        if (n > env.n_max || n < env.n_min || std::abs(forces[i].m_mnm) > lim + 1e-12) out.outside.push_back((int)i);
    }
    out.all_inside = out.outside.empty();
    return out;
}

// ---------------------------------------------------------------- Sección compuesta (A2.1-A2.10, A2.24-A2.29)

struct ElasticSection {
    double e_mpa = validation::unset, nu = validation::unset, area_m2 = validation::unset, inertia_m4 = validation::unset;
};

struct CompositeSection {
    double d_eq, k_eq, t_eq, e_eq;  // rigidez axial y flexional equivalentes, espesor y módulo equivalentes
    double d_steel, k_steel, d_shotcrete, k_shotcrete, n_sets_per_m, radius_m;
};

struct SplitForces {
    double n_steel, m_steel, q_steel, n_shotcrete, m_shotcrete, q_shotcrete;
};

/// D = E·A/(1−ν²), K = E·I/(1−ν²); Deq = n(Dst+Dsh), Keq = n(Kst+Ksh), teq = √(12Keq/Deq), Eeq = Deq/(b·teq) con b = 1 m.
/// La cercha se da por cercha (A, I de un perfil) y el shotcrete por metro de túnel; n = cerchas por metro.
inline CompositeSection composite(const ElasticSection& steel, const ElasticSection& shotcrete, double n_sets_per_m,
                                  double radius_m) {
    using namespace lining_detail;
    const std::pair<const ElasticSection*, const char*> parts[] = {{&steel, "steel"}, {&shotcrete, "shotcrete"}};
    for (const auto& [p, nm] : parts) {
        const std::string n = nm;
        positive(p->e_mpa, n + ".e_mpa");
        validation::require_finite(p->nu, n + ".nu");
        if (p->nu < 0.0 || p->nu >= 0.5) fail(n + ".nu", "must be within [0, 0.5)");
        positive(p->area_m2, n + ".area_m2");
        positive(p->inertia_m4, n + ".inertia_m4");
    }
    positive(n_sets_per_m, "n_sets_per_m");
    positive(radius_m, "radius_m");
    const double dst = steel.e_mpa * steel.area_m2 / (1 - steel.nu * steel.nu);
    const double kst = steel.e_mpa * steel.inertia_m4 / (1 - steel.nu * steel.nu);
    const double dsh = shotcrete.e_mpa * shotcrete.area_m2 / (1 - shotcrete.nu * shotcrete.nu);
    const double ksh = shotcrete.e_mpa * shotcrete.inertia_m4 / (1 - shotcrete.nu * shotcrete.nu);
    const double deq = n_sets_per_m * (dst + dsh), keq = n_sets_per_m * (kst + ksh);
    const double teq = std::sqrt(12 * keq / deq);
    return {deq, keq, teq, deq / teq, dst, kst, dsh, ksh, n_sets_per_m, radius_m};
}

/// Reparto de N, M y Q a la cercha y al shotcrete (A2.24-A2.29; A2.27 es Nsh, errata de rótulo de KL08).
inline SplitForces split_forces(const CompositeSection& c, double n_mn, double m_mnm, double q_mn) {
    validation::require_finite(n_mn, "n_mn");
    validation::require_finite(m_mnm, "m_mnm");
    validation::require_finite(q_mn, "q_mn");
    const double n = c.n_sets_per_m, ds = c.d_steel + c.d_shotcrete, ks = c.k_steel + c.k_shotcrete;
    const double corr = m_mnm * (c.d_shotcrete * c.k_steel - c.d_steel * c.k_shotcrete) / (n * c.radius_m * ds * ks);
    return {n_mn * c.d_steel / (n * ds) + corr, m_mnm * c.k_steel / (n * ks), q_mn * c.k_steel / (n * ks),
            n_mn * c.d_shotcrete / (n * ds) - corr, m_mnm * c.k_shotcrete / (n * ks), q_mn * c.k_shotcrete / (n * ks)};
}

}  // namespace rockmasspy
