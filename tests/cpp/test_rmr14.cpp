#include <gtest/gtest.h>

#include <cmath>
#include <stdexcept>

#include "rockmasspy/rmr14.hpp"

using namespace rockmasspy;

static Rmr14Input base14() {
    Rmr14Input in; in.strength_rating = 10; in.joints_per_m_rating = 30; in.continuity_m = 2.0;
    in.roughness = Roughness14::Rough; in.infilling = Infilling14::HardUnder5mm; in.alteration = Alteration14::Moderately;
    in.water = Water::Damp; in.id2_pct = 90; in.orientation = OrientationClass::Fair;
    return in;
}

TEST(Rmr14, BasicWithFaceFactor) {
    auto in = base14(); in.ice = 50.0;
    auto r = rmr14(in);
    EXPECT_EQ(r.basic, 10 + 30 + (4 + 3 + 5 + 3) + 10 + 10);    // 75
    EXPECT_EQ(r.f0, -5); EXPECT_DOUBLE_EQ(r.fe, 1.0); EXPECT_NEAR(r.fs, 1.15, 1e-12);
    EXPECT_NEAR(r.rmr, 70 * 1.15, 1e-9); EXPECT_EQ(r.rmr_class.roman, "I");
    EXPECT_EQ(r.info.method_id, "RMR14"); EXPECT_TRUE(r.warnings.empty());
}
TEST(Rmr14, NoIceWarnsAndFsIsOne) {
    auto r = rmr14(base14());
    EXPECT_DOUBLE_EQ(r.fs, 1.0); EXPECT_NEAR(r.rmr, 70.0, 1e-12);
    ASSERT_EQ(r.warnings.size(), 1u);
    EXPECT_EQ(r.warnings[0], "Fs not evaluated (no ICE): elastic face assumed");
}
TEST(Rmr14, NoOrientationBehavesLikeRmr89) {
    auto in = base14(); in.orientation.reset(); in.ice = 80.0;
    auto r = rmr14(in);
    EXPECT_EQ(r.f0, 0); EXPECT_NEAR(r.rmr, 75.0, 1e-12);
    ASSERT_EQ(r.warnings.size(), 1u);
    EXPECT_EQ(r.warnings[0], "no orientation adjustment: rmr is the basic RMR14");
}
TEST(Rmr14, ClassRatings) {
    EXPECT_EQ(rating_continuity14(1.0), 4); EXPECT_EQ(rating_continuity14(0.9), 5);
    EXPECT_EQ(rating_continuity14(3.0), 2); EXPECT_EQ(rating_continuity14(10.0), 0);
}
TEST(Rmr14, Id2ErrataFixed) {
    EXPECT_EQ(rating_id2_14(90), 10); EXPECT_EQ(rating_id2_14(85), 8);
    EXPECT_EQ(rating_id2_14(60), 4); EXPECT_EQ(rating_id2_14(30), 0);
    EXPECT_THROW(rating_id2_14(101), std::invalid_argument);
}
TEST(Rmr14, FsLimits) { EXPECT_DOUBLE_EQ(fs_face(15), 1.3); EXPECT_DOUBLE_EQ(fs_face(70), 1.0); EXPECT_DOUBLE_EQ(fs_face(10), 1.3); }
TEST(Rmr14, IceFormulaBranches) {
    double e = std::exp((60.0 - 100.0) / 24.0);
    EXPECT_NEAR(ice_bieniawski_celada(60, 50, 1.0, 300, 1.0), 3704 * 50 * e / (2.0 * 300), 1e-9);
    EXPECT_NEAR(ice_bieniawski_celada(60, 50, 1.5, 300, 1.0), 3704 * 50 * e / (3.5 * 300), 1e-9);
    EXPECT_THROW(ice_bieniawski_celada(60, 50, 0.0, 300, 1.0), std::invalid_argument);
    EXPECT_THROW(ice_bieniawski_celada(101, 50, 1.0, 300, 1.0), std::invalid_argument);
}
TEST(Rmr14, TbmNotYetSupported) {
    auto in = base14(); in.excavation = Excavation::Tbm; EXPECT_THROW(rmr14(in), std::invalid_argument);
}
TEST(Rmr14, ChartRatingsOutOfRangeThrow) {
    auto in = base14(); in.strength_rating = 16; EXPECT_THROW(rmr14(in), std::invalid_argument);
    in = base14(); in.joints_per_m_rating = -1; EXPECT_THROW(rmr14(in), std::invalid_argument);
    in = base14(); in.ice = -1.0; EXPECT_THROW(rmr14(in), std::invalid_argument);
}
