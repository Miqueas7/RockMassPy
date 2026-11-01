#include <gtest/gtest.h>

#include <cmath>
#include <limits>
#include <stdexcept>

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
    EXPECT_EQ(r.warnings[0], "no orientation adjustment: rmr is the basic RMR89'");
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
