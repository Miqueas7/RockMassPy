#include <gtest/gtest.h>

#include <cmath>
#include <limits>
#include <stdexcept>

#include "rockmasspy/correlations.hpp"

using namespace rockmasspy;

TEST(Correlations, Values) {
    EXPECT_NEAR(correlate(Correlation::RmrFromQ_Bieniawski1976, 4.5).value, 9 * std::log(4.5) + 44, 1e-12);
    EXPECT_NEAR(correlate(Correlation::RmrFromQ_Huang2026, 4.5).value, 56.387, 1e-3);
    EXPECT_NEAR(correlate(Correlation::GsiFromQPrime_Hoek1995, 10).value, 64.723, 1e-3);
    EXPECT_DOUBLE_EQ(correlate(Correlation::GsiFromRmr89Prime_HoekDiederichs2006, 64).value, 59);
    EXPECT_DOUBLE_EQ(correlate(Correlation::GsiFromRmr76Prime_HoekDiederichs2006, 60).value, 60);
    EXPECT_NEAR(correlate(Correlation::Rmr14FromRmr89_Osinergmin2017, 59).value, 66.9, 1e-9);
    EXPECT_DOUBLE_EQ(correlate(Correlation::Rmr76FromRmr89_Osinergmin2017, 59).value, 54);
}

TEST(Correlations, InfoAndLabels) {
    auto r = correlate(Correlation::RmrFromQ_Huang2026, 4.5);
    EXPECT_EQ(r.info.method_id, "RmrFromQ_Huang2026");
    EXPECT_EQ(r.info.verification, Verification::Secondary);
    EXPECT_EQ(r.from, "Q");
    EXPECT_EQ(r.to, "RMR89");
    auto g = correlate(Correlation::GsiFromRmr89Prime_HoekDiederichs2006, 64);
    EXPECT_EQ(g.info.verification, Verification::Primary);
    EXPECT_EQ(g.from, "RMR89'");
    EXPECT_EQ(g.to, "GSI");
    ASSERT_EQ(g.warnings.size(), 1u);
    EXPECT_EQ(g.warnings[0],
              "global correlation: high scatter; calibrate a site correlation (Osinergmin 2017, 3.2.3.9)");
}

TEST(Correlations, ValidityLimitsThrow) {
    EXPECT_THROW(correlate(Correlation::GsiFromRmr89Prime_HoekDiederichs2006, 23), std::invalid_argument);
    EXPECT_THROW(correlate(Correlation::GsiFromRmr76Prime_HoekDiederichs2006, 18), std::invalid_argument);
    EXPECT_THROW(correlate(Correlation::RmrFromQ_Bieniawski1976, 0.0), std::invalid_argument);
    EXPECT_THROW(correlate(Correlation::Rmr14FromRmr89_Osinergmin2017, 101), std::invalid_argument);
    EXPECT_THROW(correlate(Correlation::RmrFromQ_Bieniawski1976, std::numeric_limits<double>::quiet_NaN()),
                 std::invalid_argument);
}

TEST(Correlations, ClipsAndWarns) {
    auto r = correlate(Correlation::GsiFromQPrime_Hoek1995, 1000);
    EXPECT_DOUBLE_EQ(r.value, 100);
    ASSERT_EQ(r.warnings.size(), 2u);
    EXPECT_EQ(r.warnings[1], "result clipped to [0, 100]");
    auto lo = correlate(Correlation::RmrFromQ_Bieniawski1976, 0.001);  // 44 + 9 ln(0.001) < 0
    EXPECT_DOUBLE_EQ(lo.value, 0);
    EXPECT_EQ(lo.warnings.size(), 2u);
}

TEST(Correlations, NoChaining) {
    auto rmr = correlate(Correlation::RmrFromQ_Bieniawski1976, 4.5);
    EXPECT_THROW(correlate(Correlation::GsiFromRmr89Prime_HoekDiederichs2006, rmr), std::invalid_argument);
}
