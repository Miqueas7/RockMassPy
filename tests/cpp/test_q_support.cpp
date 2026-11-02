#include <gtest/gtest.h>

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

#include "rockmasspy/q_support.hpp"

using namespace rockmasspy;

static bool has(const SupportFormulaResult& r, const std::string& w) {
    return std::find(r.warnings.begin(), r.warnings.end(), w) != r.warnings.end();
}

// Cámara de chancado de Hoek (PRE cap. 3): Q 4.5, B 15 m, ESR 1.6.
TEST(QSupport, HoekCrusherChamber) {
    auto s = max_unsupported_span(4.5, 1.6);
    EXPECT_NEAR(s.value, 5.840298, 1e-6); EXPECT_EQ(s.unit, "m");
    EXPECT_EQ(s.info.method_id, "Q-Barton1980");
    EXPECT_EQ(bolt_length_barton1980(15, 1.6).value, 3.40625);
    auto p = roof_pressure_grimstad_barton(4.5, 4, 3);
    EXPECT_NEAR(p.value, 0.269203, 1e-6);
    EXPECT_EQ(p.unit, "");
    EXPECT_TRUE(has(p, "unit not stated in the cited source (Hoek ch. 3, eq. 5); confirm before use"));
}

TEST(QSupport, UnitCaseAndVerification) {
    EXPECT_EQ(max_unsupported_span(1, 1).value, 2.0);
    EXPECT_EQ(max_unsupported_span(1, 1).info.verification, Verification::Secondary);
    EXPECT_EQ(bolt_length_barton1980(15, 1.6).info.verification, Verification::Secondary);
    EXPECT_EQ(bolt_length_barton1980(15, 1.6).info.method_id, "Q-Barton1980");
    auto p = roof_pressure_grimstad_barton(4.5, 4, 3);
    EXPECT_EQ(p.info.verification, Verification::Secondary);
    EXPECT_EQ(p.info.method_id, "Q-GrimstadBarton1993");
}

TEST(QSupport, RejectsImpossibleInputs) {
    const double nan = std::nan(""), inf = std::numeric_limits<double>::infinity();
    for (double bad : {nan, inf, 0.0}) {
        EXPECT_THROW(max_unsupported_span(bad, 1), std::invalid_argument);
        EXPECT_THROW(max_unsupported_span(1, bad), std::invalid_argument);
        EXPECT_THROW(bolt_length_barton1980(bad, 1), std::invalid_argument);
        EXPECT_THROW(bolt_length_barton1980(10, bad), std::invalid_argument);
        EXPECT_THROW(roof_pressure_grimstad_barton(bad, 4, 3), std::invalid_argument);
        EXPECT_THROW(roof_pressure_grimstad_barton(1, bad, 3), std::invalid_argument);
        EXPECT_THROW(roof_pressure_grimstad_barton(1, 4, bad), std::invalid_argument);
    }
    EXPECT_THROW(roof_pressure_grimstad_barton(1, 4, 0.4), std::invalid_argument);
    EXPECT_THROW(roof_pressure_grimstad_barton(1, 61, 3), std::invalid_argument);
}

TEST(QSupport, Warnings) {
    EXPECT_TRUE(max_unsupported_span(1000, 1).warnings.empty());
    EXPECT_TRUE(has(max_unsupported_span(1001, 1), "Q outside 0.001-1000"));
    EXPECT_TRUE(max_unsupported_span(0.001, 1).warnings.empty());
    EXPECT_TRUE(has(roof_pressure_grimstad_barton(1001, 4, 3), "Q outside 0.001-1000"));
    EXPECT_TRUE(has(max_unsupported_span(1, 6), "ESR outside 0.5-5 (NGI Table 4-1)"));
    EXPECT_TRUE(has(bolt_length_barton1980(10, 0.4), "ESR outside 0.5-5 (NGI Table 4-1)"));
    EXPECT_TRUE(max_unsupported_span(1, 5).warnings.empty());
}
