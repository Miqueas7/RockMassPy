/**
 * @file correlations.hpp
 * @brief Correlaciones globales entre sistemas (RMR, Q, GSI). Son orientativas y dispersas.
 *
 * Toda correlación lleva un aviso fijo de dispersión. No se encadenan: convertir a partir
 * del resultado de otra correlación lanza error; el usuario debe pasar un valor medido
 * (Osinergmin 2017, 3.2.3.9). El resultado se recorta a [0, 100] con aviso.
 */

#pragma once

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>
#include <vector>

#include "rockmasspy/method_info.hpp"
#include "rockmasspy/validation.hpp"

namespace rockmasspy {

enum class Correlation {
    RmrFromQ_Bieniawski1976,
    RmrFromQ_Huang2026,
    GsiFromQPrime_Hoek1995,
    GsiFromRmr89Prime_HoekDiederichs2006,
    GsiFromRmr76Prime_HoekDiederichs2006,
    Rmr14FromRmr89_Osinergmin2017,
    Rmr76FromRmr89_Osinergmin2017
};

struct CorrelationResult {
    double value;
    std::string from, to;
    MethodInfo info;
    std::vector<std::string> warnings;
};

inline CorrelationResult correlate(Correlation c, double x) {
    using namespace validation;
    require_finite(x, "value");
    double v = 0.0;
    CorrelationResult r{};
    auto set = [&](const char* id, Verification ver, const char* src, const char* from, const char* to) {
        r.info = {id, ver, src};
        r.from = from;
        r.to = to;
    };
    switch (c) {
        case Correlation::RmrFromQ_Bieniawski1976:
            require_positive(x, "q");
            v = 9.0 * std::log(x) + 44.0;
            set("RmrFromQ_Bieniawski1976", Verification::Secondary, "Bieniawski (1976)", "Q", "RMR76");  // ajustada con RMR76
            break;
        case Correlation::RmrFromQ_Huang2026:
            require_positive(x, "q");
            v = 6.70 * std::log(x) + 46.31;
            set("RmrFromQ_Huang2026", Verification::Secondary, "Huang et al. (2026), Crossref abstract", "Q",
                "RMR89");
            break;
        case Correlation::GsiFromQPrime_Hoek1995:
            require_positive(x, "q_prime");
            v = 9.0 * std::log(x) + 44.0;
            set("GsiFromQPrime_Hoek1995", Verification::Secondary, "Hoek, Kaiser & Bawden (1995)", "Q'", "GSI");
            break;
        case Correlation::GsiFromRmr89Prime_HoekDiederichs2006:
            require_in_range(x, 0.0, 100.0, "rmr89_prime");
            if (x <= 23.0) validation::detail::fail("rmr89_prime", "must be > 23 for this correlation", x);
            v = x - 5.0;
            set("GsiFromRmr89Prime_HoekDiederichs2006", Verification::Primary, "Hoek & Diederichs (2006)",
                "RMR89'", "GSI");
            break;
        case Correlation::GsiFromRmr76Prime_HoekDiederichs2006:
            require_in_range(x, 0.0, 100.0, "rmr76_prime");
            if (x <= 18.0) validation::detail::fail("rmr76_prime", "must be > 18 for this correlation", x);
            v = x;
            set("GsiFromRmr76Prime_HoekDiederichs2006", Verification::Primary, "Hoek & Diederichs (2006)",
                "RMR76'", "GSI");
            break;
        case Correlation::Rmr14FromRmr89_Osinergmin2017:
            require_in_range(x, 0.0, 100.0, "rmr89");
            v = 1.1 * x + 2.0;
            set("Rmr14FromRmr89_Osinergmin2017", Verification::Secondary, "Osinergmin (2017), Table 3-11",
                "RMR89", "RMR14");
            break;
        case Correlation::Rmr76FromRmr89_Osinergmin2017:
            require_in_range(x, 0.0, 100.0, "rmr89");
            v = x - 5.0;
            set("Rmr76FromRmr89_Osinergmin2017", Verification::Secondary, "Osinergmin (2017), Table 3-11",
                "RMR89", "RMR76");
            break;
    }
    r.warnings.push_back("global correlation: high scatter; calibrate a site correlation (Osinergmin 2017, 3.2.3.9)");
    r.value = std::clamp(v, 0.0, 100.0);
    if (r.value != v) r.warnings.push_back("result clipped to [0, 100]");
    return r;
}

/// Siempre lanza: una correlación no se alimenta con el resultado de otra.
[[noreturn]] inline CorrelationResult correlate(Correlation, const CorrelationResult&) {
    throw std::invalid_argument(
        "correlations must not be chained: convert from a measured value (Osinergmin 2017, 3.2.3.9)");
}

}  // namespace rockmasspy
