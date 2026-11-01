#include <gtest/gtest.h>

#include <limits>
#include <stdexcept>

#include "rockmasspy/rmr76.hpp"

using namespace rockmasspy;

static Rmr76Input base76() {
    Rmr76Input in; in.ucs_mpa = 120; in.rqd_pct = 80; in.spacing_m = 0.5;
    in.condition = JointCondition76::SlightlyRoughSlightlyWeathered; in.water = Water76::CompletelyDry;
    return in;
}

TEST(Rmr76, SpacingAndTotal) {
    EXPECT_EQ(rating_spacing76(3.0), 25); EXPECT_EQ(rating_spacing76(0.3), 10);
    EXPECT_EQ(rating_spacing76(3.1), 30); EXPECT_EQ(rating_spacing76(0.05), 5);
    auto r = rmr76(base76());
    EXPECT_EQ(r.basic, 12 + 17 + 20 + 20 + 10); EXPECT_EQ(r.info.method_id, "RMR76");
    EXPECT_EQ(r.adjustment, 0); EXPECT_EQ(r.rmr, 79);
    ASSERT_EQ(r.warnings.size(), 1u);
    EXPECT_EQ(r.warnings[0], "no orientation adjustment: rmr is the basic RMR76");
}

// A.16 difiere de RMR89 en los rangos de resistencia (A.16 manda).
TEST(Rmr76, StrengthBandsFollowAnnexA16) {
    EXPECT_EQ(rating_ucs76(201), 15); EXPECT_EQ(rating_ucs76(200), 12);
    EXPECT_EQ(rating_ucs76(100), 7);  EXPECT_EQ(rating_ucs76(25), 2);
    EXPECT_EQ(rating_ucs76(10), 1);   EXPECT_EQ(rating_ucs76(3), 0);
    EXPECT_EQ(rating_is50_76(8.5), 15); EXPECT_EQ(rating_is50_76(8), 12); EXPECT_EQ(rating_is50_76(1.5), 4);
    EXPECT_THROW(rating_is50_76(1.0), std::invalid_argument);
}

TEST(Rmr76, OrientationAndFractionWarning) {
    auto in = base76(); in.orientation = OrientationClass::Unfavourable; in.rqd_pct = 0.8;
    auto r = rmr76(in);
    EXPECT_EQ(r.adjustment, -10);
    ASSERT_EQ(r.warnings.size(), 1u);
    EXPECT_EQ(r.warnings[0], "rqd_pct <= 1: RQD is a percentage (0-100); check it is not a fraction");
}

TEST(Rmr76, Validation) {
    auto in = base76(); in.is50_mpa = 5; EXPECT_THROW(rmr76(in), std::invalid_argument);
    in = base76(); in.ucs_mpa.reset(); EXPECT_THROW(rmr76(in), std::invalid_argument);
    in = base76(); in.spacing_m = 0; EXPECT_THROW(rmr76(in), std::invalid_argument);
    in = base76(); in.rqd_pct = 101; EXPECT_THROW(rmr76(in), std::invalid_argument);
    in = base76(); in.rqd_pct = std::numeric_limits<double>::quiet_NaN(); EXPECT_THROW(rmr76(in), std::invalid_argument);
}
