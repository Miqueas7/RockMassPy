/**
 * @file q_support.hpp
 * @brief Fórmulas clásicas del sistema Q para sostenimiento [V2: fuente secundaria].
 *
 * Tomadas de Hoek, Practical Rock Engineering, cap. 3, ecs. 3-5 (pp. 18-19), que las atribuye a
 * Barton, Loset, Lien y Lunde (1980) y a Grimstad y Barton (1993). El manual NGI no las trae.
 */

#pragma once

#include <cmath>
#include <string>
#include <vector>

#include "rockmasspy/method_info.hpp"
#include "rockmasspy/validation.hpp"

namespace rockmasspy {

struct SupportFormulaResult {
    double value;
    std::string unit;
    MethodInfo info;
    std::vector<std::string> warnings;
};

namespace detail_qs {
inline MethodInfo barton1980(const char* eq) {
    return {"Q-Barton1980", Verification::Secondary,
            std::string("Hoek, Practical Rock Engineering, ch. 3, ") + eq +
                ", p. 18 (after Barton, Loset, Lien and Lunde 1980); not in the NGI manuals"};
}
inline void q_warn(double q, std::vector<std::string>& w) {
    if (q < 0.001 || q > 1000.0) w.push_back("Q outside 0.001-1000");
}
inline void esr_warn(double esr, std::vector<std::string>& w) {
    if (esr < 0.5 || esr > 5.0) w.push_back("ESR outside 0.5-5 (NGI Table 4-1)");
}
}  // namespace detail_qs

/// Luz máxima sin sostenimiento: 2·ESR·Q^0.4 (m).
inline SupportFormulaResult max_unsupported_span(double q, double esr) {
    validation::require_positive(q, "q");
    validation::require_positive(esr, "esr");
    SupportFormulaResult r{2.0 * esr * std::pow(q, 0.4), "m", detail_qs::barton1980("eq. 4"), {}};
    detail_qs::q_warn(q, r.warnings);
    detail_qs::esr_warn(esr, r.warnings);
    return r;
}

/// Longitud de perno del techo: 2 + 0.15·B/ESR (m).
inline SupportFormulaResult bolt_length_barton1980(double span_m, double esr) {
    validation::require_positive(span_m, "span_m");
    validation::require_positive(esr, "esr");
    SupportFormulaResult r{2.0 + 0.15 * span_m / esr, "m", detail_qs::barton1980("eq. 3"), {}};
    detail_qs::esr_warn(esr, r.warnings);
    return r;
}

/// Presión de sostenimiento del techo: 2·sqrt(Jn)·Q^(-1/3) / (3·Jr). La fuente no dice la unidad.
inline SupportFormulaResult roof_pressure_grimstad_barton(double q, double jn, double jr) {
    validation::require_positive(q, "q");
    validation::require_positive(jn, "jn");
    validation::require_in_range(jn, 0.0, 60.0, "jn");
    validation::require_in_range(jr, 0.5, 5.0, "jr");
    SupportFormulaResult r{2.0 * std::sqrt(jn) * std::pow(q, -1.0 / 3.0) / (3.0 * jr), "",
                           {"Q-GrimstadBarton1993", Verification::Secondary,
                            "Hoek, Practical Rock Engineering, ch. 3, eq. 5, p. 19 (after Grimstad and Barton 1993)"},
                           {"unit not stated in the cited source (Hoek ch. 3, eq. 5); confirm before use"}};
    detail_qs::q_warn(q, r.warnings);
    return r;
}

}  // namespace rockmasspy
