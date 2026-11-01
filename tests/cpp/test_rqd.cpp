#include <gtest/gtest.h>

#include <stdexcept>

#include "rockmasspy/rqd.hpp"

using namespace rockmasspy;

TEST(Rqd, PriestHudson)      { EXPECT_NEAR(rqd_priest_hudson(10.0).rqd_pct, 73.5759, 1e-4); }
TEST(Rqd, PriestHudsonZero)  { EXPECT_DOUBLE_EQ(rqd_priest_hudson(0.0).rqd_pct, 100.0); }
TEST(Rqd, Jv2005)            { auto r = rqd_from_jv(10.0); EXPECT_DOUBLE_EQ(r.rqd_pct, 85.0);
                               EXPECT_EQ(r.info.method_id, "RQD-P2005"); EXPECT_EQ(r.info.verification, Verification::Secondary); }
TEST(Rqd, Jv1982)            { EXPECT_DOUBLE_EQ(rqd_from_jv(10.0, JvMethod::Palmstrom1982).rqd_pct, 82.0); }
TEST(Rqd, JvClipsWithWarning){ auto hi = rqd_from_jv(0.0); EXPECT_DOUBLE_EQ(hi.rqd_pct, 100.0); EXPECT_EQ(hi.warnings.size(), 1u);
                               auto lo = rqd_from_jv(50.0); EXPECT_DOUBLE_EQ(lo.rqd_pct, 0.0); EXPECT_EQ(lo.warnings.size(), 1u); }
TEST(Rqd, CoreThresholdCounts){ EXPECT_NEAR(rqd_from_core({0.25, 0.05, 0.30, 0.08, 0.10}, 1.0).rqd_pct, 65.0, 1e-9); }
TEST(Rqd, CorePiecesLongerThanRunThrow){ EXPECT_THROW(rqd_from_core({0.8, 0.5}, 1.0), std::invalid_argument); }
TEST(Rqd, NegativeLambdaThrows){ EXPECT_THROW(rqd_priest_hudson(-1.0), std::invalid_argument); }
