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
    EXPECT_EQ(r.warnings[0], "no orientation adjustment applied: rmr is the basic rating");
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
TEST(Rmr14, FsLimits) { EXPECT_NEAR(fs_face(15), 1.2865, 1e-12); EXPECT_DOUBLE_EQ(fs_face(14.9), 1.3); EXPECT_DOUBLE_EQ(fs_face(70), 1.0); EXPECT_DOUBLE_EQ(fs_face(10), 1.3); }
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
TEST(Rmr14, UnsetFieldsThrowWithTheirName) {
    EXPECT_THROW(rmr14(Rmr14Input{}), std::invalid_argument);
    const double nan = std::numeric_limits<double>::quiet_NaN();
    const std::vector<std::pair<std::string, std::function<void(Rmr14Input&)>>> cases = {
        {"strength_rating", [=](Rmr14Input& in) { in.strength_rating = nan; }},
        {"joints_per_m_rating", [=](Rmr14Input& in) { in.joints_per_m_rating = nan; }},
        {"continuity_m", [=](Rmr14Input& in) { in.continuity_m = nan; }},
        {"roughness", [](Rmr14Input& in) { in.roughness.reset(); }},
        {"infilling", [](Rmr14Input& in) { in.infilling.reset(); }},
        {"alteration", [](Rmr14Input& in) { in.alteration.reset(); }},
        {"water", [](Rmr14Input& in) { in.water.reset(); }},
        {"id2_pct", [=](Rmr14Input& in) { in.id2_pct = nan; }},
    };
    for (const auto& [name, unset] : cases) {
        auto in = base14(); unset(in);
        EXPECT_NE(error_of([&] { rmr14(in); }).find("'" + name + "'"), std::string::npos) << name;
    }
}
TEST(Rmr14, FractionalChartRating) {
    auto in = base14(); in.strength_rating = 12.4; in.ice = 80.0;
    EXPECT_NEAR(rmr14(in).basic, 77.4, 1e-12);
}
TEST(Rmr14, OverHundredWarns) {
    Rmr14Input in; in.strength_rating = 15; in.joints_per_m_rating = 40; in.continuity_m = 0.5;
    in.roughness = Roughness14::VeryRough; in.infilling = Infilling14::HardUnder5mm; in.alteration = Alteration14::Unaltered;
    in.water = Water::Dry; in.id2_pct = 90; in.orientation = OrientationClass::VeryFavourable; in.ice = 10.0;
    auto r = rmr14(in);
    EXPECT_NEAR(r.rmr, 130.0, 1e-9);
    ASSERT_EQ(r.warnings.size(), 1u);
    EXPECT_EQ(r.warnings[0], "rmr outside 0-100 after adjustments");
}
TEST(Rmr14, NegativeWarns) {
    Rmr14Input in; in.strength_rating = 0; in.joints_per_m_rating = 0; in.continuity_m = 30;
    in.roughness = Roughness14::Slickensided; in.infilling = Infilling14::SoftOver5mm; in.alteration = Alteration14::Decomposed;
    in.water = Water::Flowing; in.id2_pct = 0; in.orientation = OrientationClass::VeryUnfavourable; in.ice = 10.0;
    auto r = rmr14(in);
    EXPECT_LT(r.rmr, 0.0);
    ASSERT_EQ(r.warnings.size(), 1u);
    EXPECT_EQ(r.warnings[0], "rmr outside 0-100 after adjustments");
}
