/**
 * @file gsi.hpp
 * @brief GSI cuantificado (Hoek, Carter y Diederichs 2013, ARMA 13-672) desde JCond y RQD.
 *
 * GSI = 1.5·JCond89 + RQD/2  o  GSI = 2·JCond76 + RQD/2. La ecuación 3 del artículo
 * (coeficiente 52) no se incluye: su coeficiente no está verificado.
 */

#pragma once

#include <string>
#include <vector>

#include "rockmasspy/method_info.hpp"
#include "rockmasspy/validation.hpp"

namespace rockmasspy {

struct GsiResult {
    double gsi;
    MethodInfo info;
    std::vector<std::string> warnings;
};

inline MethodInfo gsi_info() {
    return {"GSI-2013", Verification::Primary, "Hoek, Carter & Diederichs (2013), ARMA 13-672"};
}

inline GsiResult gsi_from_jcond89_rqd(double jcond89, double rqd_pct) {
    validation::require_in_range(jcond89, 0.0, 30.0, "jcond89");
    validation::require_in_range(rqd_pct, 0.0, 100.0, "rqd_pct");
    return {1.5 * jcond89 + rqd_pct / 2.0, gsi_info(), {}};
}

inline GsiResult gsi_from_jcond76_rqd(double jcond76, double rqd_pct) {
    validation::require_in_range(jcond76, 0.0, 25.0, "jcond76");
    validation::require_in_range(rqd_pct, 0.0, 100.0, "rqd_pct");
    return {2.0 * jcond76 + rqd_pct / 2.0, gsi_info(), {}};
}

/// JCond89 = 35·(Jr/Ja)/(1 + Jr/Ja), con los rangos de Jr y Ja del sistema Q.
inline double jcond89_from_jr_ja(double jr, double ja) {
    validation::require_in_range(jr, 0.5, 5.0, "jr");
    validation::require_in_range(ja, 0.75, 20.0, "ja");
    const double x = jr / ja;
    return 35.0 * x / (1.0 + x);
}

}  // namespace rockmasspy
