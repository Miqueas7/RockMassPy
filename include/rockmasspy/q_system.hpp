/**
 * @file q_system.hpp
 * @brief Sistema Q de Barton (NGI 2015 rev. 2022 y NGI 2025): Q, Q', clase, Q de paredes y dimensión equivalente De.
 *
 * Regla de límites: un valor justo en el límite de una clase toma la clase menos favorable
 * (Q = 10 exacto es "C Fair", no "B Good"). Por defecto manda la edición 2025.
 * Las tablas de letras (Jn, Jr, Ja, Jw, SRF) viven en python/rockmasspy/q_tables.py.
 * Fuente: manuales públicos del NGI (verificación primaria).
 */

#pragma once

#include <algorithm>
#include <stdexcept>
#include <string>
#include <vector>

#include "rockmasspy/method_info.hpp"
#include "rockmasspy/validation.hpp"

namespace rockmasspy {

enum class QEdition { NGI2015, NGI2025 };

/// jn hasta 60 incluye 3·Jn de intersecciones.
struct QInput {
    double rqd_pct = 100.0, jn = 1.0, jr = 1.0, ja = 1.0, jw = 1.0, srf = 1.0;
    QInput() = default;
    QInput(double rqd_pct, double jn, double jr, double ja, double jw, double srf)
        : rqd_pct(rqd_pct), jn(jn), jr(jr), ja(ja), jw(jw), srf(srf) {}
};

struct QResult {
    double q, q_base, rqd_used;
    std::string rock_class;
    MethodInfo info;
    std::vector<std::string> warnings;
};

inline QResult q_value(const QInput& in, QEdition edition = QEdition::NGI2025) {
    validation::require_in_range(in.rqd_pct, 0.0, 100.0, "rqd_pct");
    validation::require_positive(in.jn, "jn");
    validation::require_in_range(in.jn, 0.0, 60.0, "jn");
    validation::require_in_range(in.jr, 0.5, 5.0, "jr");
    validation::require_in_range(in.ja, 0.75, 20.0, "ja");
    validation::require_in_range(in.jw, 0.05, 1.0, "jw");
    validation::require_in_range(in.srf, 0.5, 400.0, "srf");

    QResult r{};
    r.rqd_used = std::max(in.rqd_pct, 10.0);
    r.q_base = (r.rqd_used / in.jn) * (in.jr / in.ja);
    r.q = r.q_base * (in.jw / in.srf);

    const double q = r.q;
    const bool v2025 = edition == QEdition::NGI2025;
    if (!v2025 && q > 400.0) r.rock_class = "A Exceptionally good";
    else if (!v2025 && q > 100.0) r.rock_class = "A Extremely good";
    else if (q > 40.0) r.rock_class = "A Very good";
    else if (q > 10.0) r.rock_class = "B Good";
    else if (q > 4.0) r.rock_class = "C Fair";
    else if (q > 1.0) r.rock_class = "D Poor";
    else if (q > 0.1) r.rock_class = "E Very poor";
    else if (q > 0.01) r.rock_class = "F Extremely poor";
    else r.rock_class = "G Exceptionally poor";

    if (in.rqd_pct > 0.0 && in.rqd_pct <= 1.0)
        r.warnings.push_back("rqd_pct <= 1: RQD is a percentage (0-100); check it is not a fraction");
    if (q < 0.001 || q > 1000.0) r.warnings.push_back("Q outside 0.001-1000");

    r.info = {v2025 ? "Q-NGI-2025" : "Q-NGI-2015", Verification::Primary,
              v2025 ? "NGI (2025) Using the Q-system" : "NGI (2015, rev. 2022) Using the Q-system"};
    return r;
}

/// Q para dimensionar las paredes (NGI 2025 Tabla 4-2; 2015 Tabla 8, sin la regla de altura).
inline double wall_q(double q, double wall_height_m, double span_m, bool high_stress,
                     QEdition edition = QEdition::NGI2025) {
    validation::require_positive(q, "q");
    validation::require_positive(wall_height_m, "wall_height_m");
    validation::require_positive(span_m, "span_m");
    const bool v2025 = edition == QEdition::NGI2025;
    if (v2025 && wall_height_m > span_m) return q;
    if (q > 10.0) return 5.0 * q;
    if (q > (v2025 ? 1.0 : 0.1)) return high_stress ? q : 2.5 * q;
    return q;
}

struct EquivalentDimension {
    double de_m, esr_used;
    std::vector<std::string> warnings;
};

/// De = luz o altura / ESR. Categoría ESR 'A'-'G' (NGI Tabla 4-1).
inline EquivalentDimension equivalent_dimension(double span_or_height_m, double esr, double q, char esr_category) {
    validation::require_positive(span_or_height_m, "span_or_height_m");
    validation::require_positive(esr, "esr");
    validation::require_positive(q, "q");
    if (esr_category < 'A' || esr_category > 'G')
        throw std::invalid_argument("Domain error [RockMassPy]: parameter 'esr_category' must be one of A-G");
    EquivalentDimension d{};
    d.esr_used = esr;
    if (q <= 0.1 && (esr_category == 'B' || esr_category == 'C' || esr_category == 'D')) {
        d.esr_used = 1.0;
        d.warnings.push_back("ESR set to 1.0 because Q <= 0.1 (NGI Table 4-1)");
    }
    d.de_m = span_or_height_m / d.esr_used;
    return d;
}

}  // namespace rockmasspy
