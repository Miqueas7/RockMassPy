#include <gtest/gtest.h>

#include <cmath>
#include <functional>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "error_of.hpp"
#include "rockmasspy/rmr14.hpp"
#include "rockmasspy/rmr89.hpp"

using namespace rockmasspy;

// Caso publicado: Hoek, Practical Rock Engineering, cap. 3 (granito). RMR = 59.
TEST(Rmr89, HoekGraniteExample) {
    Rmr89Input in; in.is50_mpa = 8.0; in.rqd_pct = 70; in.spacing_m = 0.30;
    in.joint_condition = JointCondition89{2.0, 0.5, Roughness::SlightlyRough, Infilling::None, Weathering::Slightly};
    in.water = Water::Wet;
    in.orientation = tunnel_orientation_class(StrikeRelation::PerpendicularDriveAgainstDip, 60.0);
    auto r = rmr89(in);
    EXPECT_EQ(r.r_strength, 12); EXPECT_EQ(r.r_rqd, 13); EXPECT_EQ(r.r_spacing, 10);
    EXPECT_EQ(r.r_condition, 22); EXPECT_EQ(r.r_water, 7);
    EXPECT_EQ(r.basic, 64); EXPECT_EQ(r.adjustment, -5); EXPECT_EQ(r.rmr, 59); EXPECT_EQ(r.rmr_class.roman, "III");
    EXPECT_EQ(r.info.method_id, "RMR89");
}
TEST(Rmr89, BoundaryTakesLessFavourable) {
    EXPECT_EQ(rating_ucs89(100.0), 7);  EXPECT_EQ(rating_rqd89(90.0), 17); EXPECT_EQ(rating_rqd89(75.0), 13);
    EXPECT_EQ(rating_spacing89(0.6), 10); EXPECT_EQ(rating_spacing89(2.0), 15);
    EXPECT_EQ(jcond89({1.0, 0.1, Roughness::Rough, Infilling::None, Weathering::Unweathered}), 4 + 4 + 5 + 6 + 6);
    EXPECT_EQ(rmr_class(80.0).roman, "II"); EXPECT_EQ(rmr_class(20.0).roman, "V");
}
TEST(Rmr89, OrientationMatrix) {
    EXPECT_EQ(tunnel_orientation_class(StrikeRelation::Parallel, 50), OrientationClass::VeryUnfavourable);
    EXPECT_EQ(tunnel_orientation_class(StrikeRelation::PerpendicularDriveWithDip, 30), OrientationClass::Favourable);
    EXPECT_EQ(tunnel_orientation_class(StrikeRelation::Parallel, 10), OrientationClass::Fair);
    EXPECT_EQ(orientation_adjustment(OrientationClass::VeryUnfavourable, Application::Slope), -60);
}
TEST(Rmr89, TotalConditionRatingAndNoOrientation) {
    Rmr89Input in; in.ucs_mpa = 120; in.rqd_pct = 80; in.spacing_m = 0.5; in.joint_condition_rating = 20; in.water = Water::Dry;
    auto r = rmr89(in); EXPECT_EQ(r.rmr, 12 + 17 + 10 + 20 + 15); EXPECT_EQ(r.adjustment, 0); EXPECT_EQ(r.warnings.size(), 1u);
    EXPECT_EQ(r.warnings[0], "no orientation adjustment applied: rmr is the basic rating");
}
TEST(Rmr89, RqdAsFractionWarns) {
    Rmr89Input in; in.ucs_mpa = 120; in.rqd_pct = 0.7; in.spacing_m = 0.5; in.joint_condition_rating = 20;
    in.water = Water::Dry; in.orientation = OrientationClass::Fair;
    auto r = rmr89(in); ASSERT_EQ(r.warnings.size(), 1u); EXPECT_NE(r.warnings[0].find("fraction"), std::string::npos);
}
TEST(Rmr89, AmbiguousInputsThrow) {
    Rmr89Input in; in.ucs_mpa = 120; in.is50_mpa = 5; in.rqd_pct = 80; in.spacing_m = 0.5; in.joint_condition_rating = 20; in.water = Water::Dry;
    EXPECT_THROW(rmr89(in), std::invalid_argument);
    in.is50_mpa.reset(); in.joint_condition_rating = 31; EXPECT_THROW(rmr89(in), std::invalid_argument);
}
TEST(Rmr89, InvalidInputsThrow) {
    Rmr89Input in; in.ucs_mpa = 120; in.rqd_pct = 80; in.spacing_m = 0.5; in.joint_condition_rating = 20; in.water = Water::Dry;
    in.rqd_pct = std::numeric_limits<double>::quiet_NaN(); EXPECT_THROW(rmr89(in), std::invalid_argument);
    in.rqd_pct = 101; EXPECT_THROW(rmr89(in), std::invalid_argument);
    in.rqd_pct = 80; in.spacing_m = 0; EXPECT_THROW(rmr89(in), std::invalid_argument);
    in.spacing_m = 0.5; in.ucs_mpa.reset(); in.is50_mpa = 1.0; EXPECT_THROW(rmr89(in), std::invalid_argument);
    EXPECT_THROW(tunnel_orientation_class(StrikeRelation::Parallel, 91), std::invalid_argument);
    EXPECT_THROW(jcond89({-1.0, 0.0, Roughness::Rough, Infilling::None, Weathering::Unweathered}), std::invalid_argument);
}
TEST(Rmr89, OrientationBoundaryIsConservative) {
    using S = StrikeRelation; using O = OrientationClass;
    EXPECT_EQ(tunnel_orientation_class(S::PerpendicularDriveWithDip, 20), O::Fair);
    EXPECT_EQ(tunnel_orientation_class(S::PerpendicularDriveWithDip, 45), O::Favourable);
    EXPECT_EQ(tunnel_orientation_class(S::PerpendicularDriveAgainstDip, 20), O::Unfavourable);
    EXPECT_EQ(tunnel_orientation_class(S::PerpendicularDriveAgainstDip, 45), O::Unfavourable);
    EXPECT_EQ(tunnel_orientation_class(S::Parallel, 20), O::Fair);
    EXPECT_EQ(tunnel_orientation_class(S::Parallel, 45), O::VeryUnfavourable);
    EXPECT_EQ(tunnel_orientation_class(S::PerpendicularDriveAgainstDip, 60), O::Fair);
}
TEST(Rmr89, RmrClassRejectsNonFinite) {
    EXPECT_THROW(rmr_class(std::nan("")), std::invalid_argument);
    EXPECT_THROW(rmr_class(std::numeric_limits<double>::infinity()), std::invalid_argument);
}
// I1: un campo olvidado lanza con su nombre, nunca toma el valor más favorable.
TEST(Rmr89, UnsetFieldsThrowWithTheirName) {
    EXPECT_THROW(rmr89(Rmr89Input{}), std::invalid_argument);
    const auto full = [] {
        Rmr89Input in; in.ucs_mpa = 120; in.rqd_pct = 80; in.spacing_m = 0.5; in.water = Water::Dry;
        in.joint_condition = JointCondition89{2.0, 0.5, Roughness::Rough, Infilling::None, Weathering::Slightly};
        return in;
    };
    EXPECT_NO_THROW(rmr89(full()));
    const double nan = std::numeric_limits<double>::quiet_NaN();
    const std::vector<std::pair<std::string, std::function<void(Rmr89Input&)>>> cases = {
        {"rqd_pct", [=](Rmr89Input& in) { in.rqd_pct = nan; }},
        {"spacing_m", [=](Rmr89Input& in) { in.spacing_m = nan; }},
        {"water", [](Rmr89Input& in) { in.water.reset(); }},
        {"persistence_m", [=](Rmr89Input& in) { in.joint_condition->persistence_m = nan; }},
        {"aperture_mm", [=](Rmr89Input& in) { in.joint_condition->aperture_mm = nan; }},
        {"roughness", [](Rmr89Input& in) { in.joint_condition->roughness.reset(); }},
        {"infilling", [](Rmr89Input& in) { in.joint_condition->infilling.reset(); }},
        {"weathering", [](Rmr89Input& in) { in.joint_condition->weathering.reset(); }},
    };
    for (const auto& [name, unset] : cases) {
        auto in = full(); unset(in);
        EXPECT_NE(error_of([&] { rmr89(in); }).find("'" + name + "'"), std::string::npos) << name;
    }
    EXPECT_NE(error_of([] { jcond89(JointCondition89{}); }).find("'persistence_m'"), std::string::npos);
}
// I2: el puntaje de condición acepta decimales (celdas de Excel).
TEST(Rmr89, FractionalConditionRating) {
    Rmr89Input in; in.ucs_mpa = 120; in.rqd_pct = 80; in.spacing_m = 0.5; in.joint_condition_rating = 18.5;
    in.water = Water::Dry; in.orientation = OrientationClass::Fair;
    auto r = rmr89(in);
    EXPECT_DOUBLE_EQ(r.r_condition, 18.5); EXPECT_DOUBLE_EQ(r.rmr, 12 + 17 + 10 + 18.5 + 15 - 5);
    in.joint_condition_rating = std::numeric_limits<double>::quiet_NaN(); EXPECT_THROW(rmr89(in), std::invalid_argument);
}
// M5: un talud con ajuste -60 baja de 0.
TEST(Rmr89, OutOfRangeAfterAdjustmentWarns) {
    Rmr89Input in; in.ucs_mpa = 0.5; in.rqd_pct = 10; in.spacing_m = 0.05; in.joint_condition_rating = 0;
    in.water = Water::Flowing; in.orientation = OrientationClass::VeryUnfavourable; in.application = Application::Slope;
    auto r = rmr89(in);
    EXPECT_DOUBLE_EQ(r.rmr, 8 - 60);
    ASSERT_EQ(r.warnings.size(), 1u);
    EXPECT_EQ(r.warnings[0], "rmr outside 0-100 after adjustments");
}
TEST(Rmr89, HugeUcsWarnsAboutUnits) {
    Rmr89Input in; in.ucs_mpa = 401; in.rqd_pct = 80; in.spacing_m = 0.5; in.joint_condition_rating = 20; in.water = Water::Dry;
    in.orientation = OrientationClass::Fair;
    auto r = rmr89(in);
    ASSERT_EQ(r.warnings.size(), 1u);
    EXPECT_EQ(r.warnings[0], "ucs_mpa > 400: check the unit is MPa (not kg/cm2)");
    in.ucs_mpa = 400;
    EXPECT_TRUE(rmr89(in).warnings.empty());
}

// Curvas continuas de Kundu et al. (2020); valores calculados con las ecuaciones.
TEST(Rmr89Continuous, CurveValues) {
    EXPECT_NEAR(rating_ucs89_continuous(1), 0.3173, 1e-4);    EXPECT_NEAR(rating_ucs89_continuous(50), 5.2398, 1e-4);
    EXPECT_NEAR(rating_ucs89_continuous(90), 7.7248, 1e-4);   EXPECT_NEAR(rating_ucs89_continuous(100), 8.2796, 1e-4);
    EXPECT_NEAR(rating_ucs89_continuous(250), 15.0, 1e-4);    EXPECT_NEAR(rating_ucs89_continuous(300), 15.0, 1e-4);
    EXPECT_NEAR(rating_ucs89_continuous(0), 0.0, 1e-12);
    EXPECT_NEAR(rating_rqd89_continuous(25), 5.7094, 1e-4);   EXPECT_NEAR(rating_rqd89_continuous(65), 13.5400, 1e-4);
    EXPECT_NEAR(rating_rqd89_continuous(100), 19.9687, 1e-4);
    EXPECT_NEAR(rating_spacing89_continuous(0.2), 8.8497, 1e-4);  EXPECT_NEAR(rating_spacing89_continuous(0.25), 9.6058, 1e-4);
    EXPECT_NEAR(rating_spacing89_continuous(0.6), 13.1453, 1e-4); EXPECT_NEAR(rating_spacing89_continuous(3), 20.0, 1e-4);
    EXPECT_NEAR(rating_spacing89_continuous(0), 0.0, 1e-12);      EXPECT_LE(rating_spacing89_continuous(5), 20.0);
    EXPECT_NEAR(rating_is50_89_continuous(2), 5.3630, 1e-4);  EXPECT_NEAR(rating_is50_89_continuous(10), 14.1026, 1e-4);
}
TEST(Rmr89Continuous, Rmr14Helpers) {
    EXPECT_NEAR(rmr14_joints_per_m_rating(0), 40.0, 1e-12);   EXPECT_NEAR(rmr14_joints_per_m_rating(5), 27.2778, 1e-4);
    EXPECT_NEAR(rmr14_joints_per_m_rating(40), 4.5630, 1e-4); EXPECT_NEAR(rmr14_strength_rating(90), 7.7248, 1e-4);
}
TEST(Rmr89Continuous, ErrorsNameTheParameter) {
    EXPECT_NE(error_of([] { rating_ucs89_continuous(-1); }).find("ucs_mpa"), std::string::npos);
    EXPECT_NE(error_of([] { rating_rqd89_continuous(-1); }).find("rqd_pct"), std::string::npos);
    EXPECT_NE(error_of([] { rating_spacing89_continuous(-1); }).find("spacing_m"), std::string::npos);
    EXPECT_NE(error_of([] { rating_is50_89_continuous(-1); }).find("is50_mpa"), std::string::npos);
    EXPECT_NE(error_of([] { rating_is50_89_continuous(1); }).find("Is50 <= 1 MPa"), std::string::npos);
    EXPECT_NE(error_of([] { rmr14_joints_per_m_rating(-1); }).find("n_per_m"), std::string::npos);
}
TEST(Rmr89Continuous, ReadmeExample) {
    Rmr89Input in; in.ucs_mpa = 90; in.rqd_pct = 65; in.spacing_m = 0.25; in.joint_condition_rating = 18;
    in.water = Water::Damp; in.orientation = OrientationClass::Fair; in.application = Application::Tunnel;
    EXPECT_NEAR(rmr89(in).rmr, 53.0, 1e-9);
    EXPECT_EQ(rmr89(in).info.method_id, "RMR89");
    in.functions = RmrFunctions::Continuous;
    auto r = rmr89(in);
    EXPECT_NEAR(r.rmr, 53.8707, 1e-4); EXPECT_EQ(r.info.method_id, "RMR89-continuous"); EXPECT_EQ(r.rmr_class.roman, "III");
}
