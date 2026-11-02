#include <gtest/gtest.h>

#include <algorithm>
#include <cmath>
#include <limits>

#include "error_of.hpp"
#include "rockmasspy/q_slope.hpp"

using namespace rockmasspy;

namespace {
// Componentes: (80/9)·(1.5·0.75)·(0.7/2.5) = 2.8
QSlopeInput base() {
    QSlopeInput in;
    in.rqd_pct = 80; in.jn = 9; in.jr_a = 1.5; in.ja_a = 1; in.o_factor_a = 0.75; in.jwice = 0.7; in.srf_a = 2.5;
    return in;
}
bool has(const std::vector<std::string>& v, const std::string& s) {
    return std::any_of(v.begin(), v.end(), [&](const std::string& x) { return x.find(s) != std::string::npos; });
}
}  // namespace

TEST(QSlopeBeta, Equation3Anchors) {  // Bar y Barton (2018) p. 896
    EXPECT_NEAR(q_slope_beta(10), 85, 1e-12);
    EXPECT_NEAR(q_slope_beta(1), 65, 1e-12);
    EXPECT_NEAR(q_slope_beta(0.1), 45, 1e-12);
    EXPECT_NEAR(q_slope_beta(0.01), 25, 1e-12);
}

TEST(QSlopeBeta, Table12) {  // Tabla 12, p. 899
    EXPECT_NEAR(q_slope_beta(0.60), 60.563, 1e-3);
    EXPECT_NEAR(q_slope_beta(1.50), 68.522, 1e-3);
    EXPECT_NEAR(q_slope_beta(4.22 * 0.75), 75.007, 1e-3);
    EXPECT_EQ(std::lround(q_slope_beta(0.60)), 61);
    EXPECT_EQ(std::lround(q_slope_beta(1.50)), 69);
    EXPECT_EQ(std::lround(q_slope_beta(4.22 * 0.75)), 75);
    EXPECT_NEAR(4.22 * 0.75, 3.165, 1e-12);
}

TEST(QSlopeBeta, RejectsNonPositive) {
    EXPECT_NE(error_of([] { q_slope_beta(0); }), "");
    EXPECT_NE(error_of([] { q_slope_beta(-1); }), "");
}

TEST(QSlope, Components) {
    const auto r = q_slope(base());
    EXPECT_NEAR(r.q_slope, 2.8, 1e-9);
    EXPECT_NEAR(r.beta_deg, 73.943, 1e-3);
    EXPECT_NEAR(r.jr_ja_0, 1.125, 1e-12);
    EXPECT_DOUBLE_EQ(r.srf_slope, 2.5);
    EXPECT_DOUBLE_EQ(r.rqd_used, 80);
    EXPECT_FALSE(r.beta_capped);
    EXPECT_EQ(r.info.method_id, "Q-slope-BarBarton2017");
    EXPECT_EQ(r.info.verification, Verification::PrimaryLaterAuthors);
    EXPECT_TRUE(r.warnings.empty());
}

TEST(QSlope, SetBMultipliesSetA) {
    auto in = base();
    in.jr_b = 2; in.ja_b = 1; in.o_factor_b = 0.9;
    const auto r = q_slope(in);
    EXPECT_NEAR(r.jr_ja_0, 2.025, 1e-12);
    EXPECT_TRUE(has(r.notes, "(Jr/Ja)0 is the product of sets A and B (wedge, Bar and Barton 2018 p. 894)"));
    EXPECT_TRUE(r.warnings.empty());
}

TEST(QSlope, SrfIsMaximum) {
    auto in = base();
    in.srf_a = 2.5; in.srf_b = 5; in.srf_c = 2;
    EXPECT_DOUBLE_EQ(q_slope(in).srf_slope, 5);
    in.srf_a.reset(); in.srf_b.reset();
    EXPECT_DOUBLE_EQ(q_slope(in).srf_slope, 2);
}

TEST(QSlope, RqdBelowTenTakenAsTen) {
    auto in = base();
    in.rqd_pct = 0;
    const auto r = q_slope(in);
    EXPECT_DOUBLE_EQ(r.rqd_used, 10);
    EXPECT_TRUE(has(r.notes, "RQD below 10 taken as 10 (Bar & Barton 2018, Table 1)"));
    EXPECT_TRUE(r.warnings.empty());
    in.rqd_pct = 10;
    EXPECT_TRUE(q_slope(in).notes.empty());
}

TEST(QSlope, BetaCappedAt90) {  // Q-slope 20 -> 91.02
    QSlopeInput in;
    in.rqd_pct = 100; in.jn = 2; in.jr_a = 1; in.ja_a = 1; in.o_factor_a = 1; in.jwice = 1; in.srf_a = 2.5;
    const auto r = q_slope(in);
    EXPECT_NEAR(r.q_slope, 20, 1e-9);
    EXPECT_NEAR(q_slope_beta(r.q_slope), 91.0206, 1e-3);
    EXPECT_DOUBLE_EQ(r.beta_deg, 90);
    EXPECT_TRUE(r.beta_capped);
    EXPECT_FALSE(r.notes.empty());
    EXPECT_TRUE(r.warnings.empty());
}

TEST(QSlope, BetaFloorAtZeroWarns) {  // Q-slope ~3e-5 -> beta negativo
    QSlopeInput in;
    in.rqd_pct = 10; in.jn = 20; in.jr_a = 0.5; in.ja_a = 20; in.o_factor_a = 1; in.jwice = 0.05; in.srf_a = 20;
    const auto r = q_slope(in);
    EXPECT_LT(r.q_slope, 1e-3);
    EXPECT_DOUBLE_EQ(r.beta_deg, 0);
    EXPECT_FALSE(r.beta_capped);
    EXPECT_TRUE(has(r.warnings, "Q-slope outside"));
    EXPECT_TRUE(has(r.warnings, "beta below 0"));
}

TEST(QSlope, Throws) {
    auto bad = [](auto edit) { auto in = base(); edit(in); return error_of([&] { q_slope(in); }); };
    EXPECT_NE(bad([](QSlopeInput& i) { i.rqd_pct = 120; }), "");
    EXPECT_NE(bad([](QSlopeInput& i) { i.rqd_pct = -1; }), "");
    EXPECT_NE(bad([](QSlopeInput& i) { i.jn = 0; }), "");
    EXPECT_NE(bad([](QSlopeInput& i) { i.jr_a = -1; }), "");
    EXPECT_NE(bad([](QSlopeInput& i) { i.ja_a = 0; }), "");
    EXPECT_NE(bad([](QSlopeInput& i) { i.o_factor_a = 0; }), "");
    EXPECT_NE(bad([](QSlopeInput& i) { i.jwice = 0; }), "");
    EXPECT_NE(bad([](QSlopeInput& i) { i.srf_a = 0; }), "");
    EXPECT_NE(bad([](QSlopeInput& i) { i.rqd_pct = unset; }), "");
    EXPECT_NE(bad([](QSlopeInput& i) { i.jn = unset; }), "");
    EXPECT_NE(bad([](QSlopeInput& i) { i.jwice = std::numeric_limits<double>::infinity(); }), "");
    EXPECT_NE(bad([](QSlopeInput& i) { i.jr_b = 2; }), "");  // set B a medias
    EXPECT_NE(bad([](QSlopeInput& i) { i.jr_b = 2; i.ja_b = 1; }), "");
    EXPECT_NE(bad([](QSlopeInput& i) { i.jr_b = 2; i.ja_b = 1; i.o_factor_b = 0; }), "");
    EXPECT_NE(bad([](QSlopeInput& i) { i.srf_a.reset(); }), "");  // ningún SRF
    EXPECT_NE(bad([](QSlopeInput& i) { i.srf_b = -2; }), "");
}

TEST(QSlope, NaNInOptionalFieldThrowsNamingIt) {
    const double nan = std::numeric_limits<double>::quiet_NaN();
    const auto msg = [&](auto edit) { auto in = base(); edit(in); return error_of([&] { q_slope(in); }); };
    EXPECT_NE(msg([&](QSlopeInput& i) { i.srf_b = nan; }).find("srf_b"), std::string::npos);
    EXPECT_NE(msg([&](QSlopeInput& i) { i.srf_c = nan; }).find("srf_c"), std::string::npos);
    EXPECT_NE(msg([&](QSlopeInput& i) { i.srf_a = nan; }).find("srf_a"), std::string::npos);
    EXPECT_NE(msg([&](QSlopeInput& i) { i.jr_b = nan; i.ja_b = 1; i.o_factor_b = 1; }).find("jr_b"), std::string::npos);
    EXPECT_NE(msg([&](QSlopeInput& i) { i.jr_b = 1; i.ja_b = nan; i.o_factor_b = 1; }).find("ja_b"), std::string::npos);
    EXPECT_NE(msg([&](QSlopeInput& i) { i.jr_b = 1; i.ja_b = 1; i.o_factor_b = nan; }).find("o_factor_b"), std::string::npos);
    EXPECT_NE(msg([&](QSlopeInput& i) { i.srf_b = std::numeric_limits<double>::infinity(); }), "");
}

TEST(QSlope, OutOfTableWarnsWithoutThrowing) {
    auto in = base();
    in.jwice = 2.5;
    EXPECT_TRUE(has(q_slope(in).warnings, "jwice"));
    in = base();
    in.srf_a = 1.5;
    EXPECT_TRUE(has(q_slope(in).warnings, "srf_a"));
    in = base();
    in.jn = 25;
    EXPECT_TRUE(has(q_slope(in).warnings, "jn"));
    in = base();
    in.jr_b = 6; in.ja_b = 1; in.o_factor_b = 0.9;
    EXPECT_TRUE(has(q_slope(in).warnings, "jr_b"));
}
