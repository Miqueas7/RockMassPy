#include <gtest/gtest.h>

#include <stdexcept>

#include "rockmasspy/gsi.hpp"

using namespace rockmasspy;

TEST(Gsi, Quantified2013) {
    EXPECT_DOUBLE_EQ(gsi_from_jcond89_rqd(22, 70).gsi, 68.0);
    EXPECT_DOUBLE_EQ(gsi_from_jcond76_rqd(25, 100).gsi, 100.0);
    EXPECT_DOUBLE_EQ(jcond89_from_jr_ja(3, 1), 26.25);
    EXPECT_THROW(gsi_from_jcond89_rqd(31, 70), std::invalid_argument);
    EXPECT_THROW(gsi_from_jcond76_rqd(26, 70), std::invalid_argument);
    EXPECT_THROW(gsi_from_jcond89_rqd(10, 101), std::invalid_argument);
    EXPECT_THROW(jcond89_from_jr_ja(3, 0), std::invalid_argument);
}

TEST(Gsi, Info) {
    auto r = gsi_from_jcond89_rqd(22, 70);
    EXPECT_EQ(r.info.method_id, "GSI-2013");
    EXPECT_EQ(r.info.verification, Verification::Primary);
    EXPECT_TRUE(r.warnings.empty());
}
TEST(Gsi, RqdFractionWarns) {
    const auto r = gsi_from_jcond89_rqd(18, 0.7);
    ASSERT_EQ(r.warnings.size(), 1u);
    EXPECT_EQ(r.warnings[0], "rqd_pct <= 1: RQD is a percentage (0-100); check it is not a fraction");
    EXPECT_EQ(gsi_from_jcond76_rqd(18, 0.7).warnings.size(), 1u);
    EXPECT_TRUE(gsi_from_jcond89_rqd(18, 0.0).warnings.empty());
}
