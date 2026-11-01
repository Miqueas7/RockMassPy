/**
 * @file rqd.hpp
 * @brief RQD (Rock Quality Designation): por testigo, por frecuencia de discontinuidades (Priest-Hudson)
 *        y por conteo volumétrico Jv (Palmström).
 *
 * Valor justo en el umbral de 0.10 m: el trozo cuenta (criterio de Deere, trozos >= umbral).
 */

#pragma once

#include <cmath>
#include <stdexcept>
#include <string>
#include <vector>

#include "rockmasspy/method_info.hpp"
#include "rockmasspy/validation.hpp"

namespace rockmasspy {

struct RqdResult {
    double rqd_pct;
    MethodInfo info;
    std::vector<std::string> warnings;
};

enum class JvMethod { Palmstrom1982, Palmstrom2005 };

/// RQD de una corrida de testigo: suma de trozos >= umbral sobre la longitud de la corrida.
inline RqdResult rqd_from_core(const std::vector<double>& piece_lengths_m, double run_length_m,
                               double threshold_m = 0.10) {
    validation::require_positive(run_length_m, "run_length_m");
    validation::require_positive(threshold_m, "threshold_m");
    double total = 0.0, sound = 0.0;
    for (double p : piece_lengths_m) {
        validation::require_non_negative(p, "piece_lengths_m");
        total += p;
        if (p >= threshold_m) sound += p;
    }
    if (total > run_length_m * (1.0 + 1e-9))
        throw std::invalid_argument(
            "Domain error [RockMassPy]: parameter 'piece_lengths_m' sums to more than 'run_length_m'");
    return {100.0 * sound / run_length_m,
            {"RQD-Deere", Verification::Secondary, "Deere (1964); Deere & Deere (1988)"},
            {}};
}

/// RQD = 100 e^(-t lambda) (t lambda + 1), lambda en discontinuidades por metro.
inline RqdResult rqd_priest_hudson(double lambda_per_m, double threshold_m = 0.10) {
    validation::require_non_negative(lambda_per_m, "lambda_per_m");
    validation::require_positive(threshold_m, "threshold_m");
    const double tl = threshold_m * lambda_per_m;
    return {100.0 * std::exp(-tl) * (tl + 1.0),
            {"RQD-PH1976", Verification::Primary,
             "Priest & Hudson (1976), as given in Hoek, Carter & Diederichs (2013)"},
            {}};
}

/// RQD desde Jv (juntas por m3): 1982 -> 115 - 3.3 Jv; 2005 -> 110 - 2.5 Jv. Se recorta a [0, 100].
inline RqdResult rqd_from_jv(double jv, JvMethod method = JvMethod::Palmstrom2005) {
    validation::require_non_negative(jv, "jv");
    RqdResult r{};
    double raw;
    if (method == JvMethod::Palmstrom1982) {
        raw = 115.0 - 3.3 * jv;
        r.info = {"RQD-P1982", Verification::Primary, "Palmstrom (1982), as given in Hoek, Carter & Diederichs (2013)"};
    } else {
        raw = 110.0 - 2.5 * jv;
        r.info = {"RQD-P2005", Verification::Secondary, "Palmstrom (2005)"};
    }
    r.rqd_pct = raw < 0.0 ? 0.0 : (raw > 100.0 ? 100.0 : raw);
    if (r.rqd_pct != raw) r.warnings.push_back("RQD clipped to [0, 100]: Jv outside the correlation range");
    return r;
}

}  // namespace rockmasspy
