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
    EXPECT_EQ(correlate(Correlation::RmrFromQ_Bieniawski1976, 4.5).to, "RMR76");   // ajustada con el RMR de 1976
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

TEST(Correlations, CustomLogLinear) {
    CustomCorrelation c{"mineA-RMR-Q", "Q", "RMR89", CorrelationForm::LogLinear, 7.5, 47.0, 0.01, 100.0, "site fit 2026"};
    auto r = correlate_custom(c, 4.5);
    EXPECT_NEAR(r.value, 7.5 * std::log(4.5) + 47.0, 1e-12);
    EXPECT_EQ(r.info.method_id, "site:mineA-RMR-Q");
    EXPECT_EQ(r.info.verification, Verification::UserDefined);
    EXPECT_TRUE(r.warnings.empty());
    EXPECT_EQ(correlate_custom(c, 500.0).warnings.size(), 1u);  // fuera del rango calibrado
    EXPECT_THROW(correlate_custom(c, 0.0), std::invalid_argument);
    EXPECT_THROW(correlate_custom(c, r), std::invalid_argument);  // sin encadenar
}

TEST(Correlations, CustomLinearClipsGsi) {
    CustomCorrelation c{"g", "RMR89", "GSI", CorrelationForm::Linear, 1.0, 10.0, 0, 100, ""};
    auto r = correlate_custom(c, 95);
    EXPECT_DOUBLE_EQ(r.value, 100);
    EXPECT_EQ(r.warnings.size(), 1u);
}

TEST(Correlations, CustomValidationAndEquality) {
    CustomCorrelation ok{"g", "A", "B", CorrelationForm::Linear, 1.0, 0.0, 0, 100, ""};
    auto bad = [&](auto mut) { auto c = ok; mut(c); return c; };
    EXPECT_THROW(correlate_custom(bad([](auto& c) { c.name = ""; }), 1.0), std::invalid_argument);
    EXPECT_THROW(correlate_custom(bad([](auto& c) { c.from = ""; }), 1.0), std::invalid_argument);
    EXPECT_THROW(correlate_custom(bad([](auto& c) { c.to = ""; }), 1.0), std::invalid_argument);
    EXPECT_THROW(correlate_custom(bad([](auto& c) { c.valid_min = 100; }), 1.0), std::invalid_argument);
    EXPECT_THROW(correlate_custom(CustomCorrelation{}, 1.0), std::invalid_argument);
    EXPECT_THROW(correlate_custom(ok, std::numeric_limits<double>::quiet_NaN()), std::invalid_argument);
    EXPECT_TRUE(ok == ok);
    EXPECT_FALSE(ok == bad([](auto& c) { c.a = 2.0; }));
}
