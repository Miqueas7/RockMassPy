/**
 * @file q_slope.hpp
 * @brief Q-slope de Bar y Barton y el ángulo de talud sin soporte beta = 20·log10(Q-slope) + 65.
 *
 * Fuente: Bar y Barton (2018), Periodica Polytechnica Civ. Eng. 62(4) 893-900: ec. 1 (p. 894), ec. 3 (p. 896),
 * Tablas 1-9 (pp. 894-896). Los parámetros se dan como números; un valor fuera de tabla avisa y nunca lanza (R15).
 * Las tablas de O, Jwice y SRF viven en Python (q_slope_tables.py).
 */

#pragma once

#include <algorithm>
#include <cmath>
#include <string>
#include <vector>

#include "rockmasspy/method_info.hpp"
#include "rockmasspy/validation.hpp"

namespace rockmasspy {

using validation::unset;

/// Set B (jr_b, ja_b, o_factor_b) es opcional pero va completo; basta con dar un SRF.
struct QSlopeInput {
    double rqd_pct = unset, jn = unset, jr_a = unset, ja_a = unset, o_factor_a = unset;
    double jr_b = unset, ja_b = unset, o_factor_b = unset;
    double jwice = unset;
    double srf_a = unset, srf_b = unset, srf_c = unset;
};

struct QSlopeResult {
    double q_slope = 0, beta_deg = 0, rqd_used = 0, jr_ja_0 = 0, srf_slope = 0;
    bool beta_capped = false;
    MethodInfo info;
    std::vector<std::string> warnings, notes;
};

/// Ec. 3 (p. 896), sin recorte.
inline double q_slope_beta(double q_slope) {
    validation::require_positive(q_slope, "q_slope");
    return 20.0 * std::log10(q_slope) + 65.0;
}

inline QSlopeResult q_slope(const QSlopeInput& in) {
    using validation::require_in_range;
    using validation::require_positive;
    require_in_range(in.rqd_pct, 0.0, 100.0, "rqd_pct");
    require_positive(in.jn, "jn");
    require_positive(in.jr_a, "jr_a");
    require_positive(in.ja_a, "ja_a");
    require_positive(in.o_factor_a, "o_factor_a");
    require_positive(in.jwice, "jwice");
    const bool b_given[] = {!std::isnan(in.jr_b), !std::isnan(in.ja_b), !std::isnan(in.o_factor_b)};
    const int n_b = b_given[0] + b_given[1] + b_given[2];
    if (n_b != 0 && n_b != 3)
        validation::detail::fail("jr_b/ja_b/o_factor_b", "must be given all together or none (incomplete set B)", n_b);
    if (n_b == 3) {
        require_positive(in.jr_b, "jr_b");
        require_positive(in.ja_b, "ja_b");
        require_positive(in.o_factor_b, "o_factor_b");
    }
    const double srfs[] = {in.srf_a, in.srf_b, in.srf_c};
    const char* srf_names[] = {"srf_a", "srf_b", "srf_c"};
    double srf = 0;
    bool any_srf = false;
    for (int i = 0; i < 3; ++i) {
        if (std::isnan(srfs[i])) continue;
        require_positive(srfs[i], srf_names[i]);
        srf = any_srf ? std::max(srf, srfs[i]) : srfs[i];
        any_srf = true;
    }
    if (!any_srf) validation::detail::fail("srf_a/srf_b/srf_c", "at least one SRF must be given", validation::unset);

    QSlopeResult r;
    r.info = {"Q-slope-BarBarton2017", Verification::PrimaryLaterAuthors,
              "Bar & Barton (2018) Periodica Polytechnica Civ. Eng. 62(4) 893-900: eq. 1 (p. 894), eq. 3 (p. 896), "
              "Tables 1-9 (pp. 894-896); SRFslope = max(SRFa, SRFb, SRFc) (p. 895)"};
    r.rqd_used = in.rqd_pct;
    if (in.rqd_pct < 10.0) {
        r.rqd_used = 10.0;
        r.notes.push_back("RQD below 10 taken as 10 (Bar & Barton 2018, Table 1)");
    }
    // en cuña, la resistencia es el producto de los dos conjuntos (p. 894)
    r.jr_ja_0 = in.jr_a / in.ja_a * in.o_factor_a;
    if (n_b == 3) r.jr_ja_0 *= in.jr_b / in.ja_b * in.o_factor_b;
    r.srf_slope = srf;
    r.q_slope = (r.rqd_used / in.jn) * r.jr_ja_0 * (in.jwice / srf);

    const auto out = [&](double v, double lo, double hi, const char* name) {
        if (!std::isnan(v) && (v < lo || v > hi))
            r.warnings.push_back(std::string(name) + " " + validation::detail::num(v) + " outside the table range [" +
                                 validation::detail::num(lo) + ", " + validation::detail::num(hi) + "]");
    };
    out(in.jn, 0.5, 20, "jn");
    out(in.jr_a, 0, 5, "jr_a");
    out(in.jr_b, 0, 5, "jr_b");
    out(in.ja_a, 0.75, 20, "ja_a");
    out(in.ja_b, 0.75, 20, "ja_b");
    out(in.o_factor_a, 0.25, 2, "o_factor_a");
    out(in.o_factor_b, 0.5, 1.5, "o_factor_b");
    out(in.jwice, 0, 1.95, "jwice");
    out(in.srf_a, 2.5, 20, "srf_a");
    out(in.srf_b, 1, 20, "srf_b");
    out(in.srf_c, 1, 24, "srf_c");
    if (r.q_slope < 0.001 || r.q_slope > 1000)
        r.warnings.push_back("Q-slope outside 0.001-1000 (Bar & Barton 2018, p. 893)");

    r.beta_deg = q_slope_beta(r.q_slope);
    if (r.beta_deg > 90.0) {
        r.beta_deg = 90.0;
        r.beta_capped = true;
        r.notes.push_back("beta capped at 90 degrees");
    } else if (r.beta_deg < 0.0) {
        r.beta_deg = 0.0;
        r.warnings.push_back("beta below 0 degrees, taken as 0");
    }
    return r;
}

}  // namespace rockmasspy
