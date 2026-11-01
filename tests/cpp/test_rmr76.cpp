#include <gtest/gtest.h>

#include <functional>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "error_of.hpp"
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
    EXPECT_EQ(r.warnings[0], "no orientation adjustment applied: rmr is the basic rating");
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
TEST(Rmr76, UnsetFieldsThrowWithTheirName) {
    EXPECT_THROW(rmr76(Rmr76Input{}), std::invalid_argument);
    EXPECT_NO_THROW(rmr76(base76()));
    const double nan = std::numeric_limits<double>::quiet_NaN();
    const std::vector<std::pair<std::string, std::function<void(Rmr76Input&)>>> cases = {
        {"rqd_pct", [=](Rmr76Input& in) { in.rqd_pct = nan; }},
        {"spacing_m", [=](Rmr76Input& in) { in.spacing_m = nan; }},
        {"condition", [](Rmr76Input& in) { in.condition.reset(); }},
        {"water", [](Rmr76Input& in) { in.water.reset(); }},
    };
    for (const auto& [name, unset] : cases) {
        auto in = base76(); unset(in);
        EXPECT_NE(error_of([&] { rmr76(in); }).find("'" + name + "'"), std::string::npos) << name;
    }
}
TEST(Rmr76, HugeUcsWarnsAboutUnits) {
    auto in = base76(); in.ucs_mpa = 401; in.orientation = OrientationClass::Fair;
    auto r = rmr76(in);
    ASSERT_EQ(r.warnings.size(), 1u);
    EXPECT_EQ(r.warnings[0], "ucs_mpa > 400: check the unit is MPa (not kg/cm2)");
    in.ucs_mpa = 400;
    EXPECT_TRUE(rmr76(in).warnings.empty());
}
TEST(Rmr76, OutOfRangeWarns) {
    Rmr76Input in; in.ucs_mpa = 1; in.rqd_pct = 10; in.spacing_m = 0.03;
    in.condition = JointCondition76::SoftGougeOrWide; in.water = Water76::Severe;
    in.orientation = OrientationClass::VeryUnfavourable;
    auto r = rmr76(in);
    EXPECT_LT(r.rmr, 0);
    ASSERT_EQ(r.warnings.size(), 1u);
    EXPECT_EQ(r.warnings[0], "rmr outside 0-100 after adjustments");
}
