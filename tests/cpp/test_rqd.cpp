#include <gtest/gtest.h>

#include <stdexcept>

#include "rockmasspy/q_system.hpp"
#include "rockmasspy/rmr89.hpp"
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
// I3: estas piezas suman 3.0000000000000004 por redondeo; el RQD no pasa de 100 y Q/RMR lo aceptan.
TEST(Rqd, CoreSumRoundingClampedTo100) {
    const double rqd = rqd_from_core({0.45, 0.13, 0.68, 0.37, 0.47, 0.29, 0.33, 0.28}, 3.0).rqd_pct;
    EXPECT_LE(rqd, 100.0);
    EXPECT_NO_THROW(q_value({rqd, 4, 3, 1, 1, 1}));
    Rmr89Input in; in.ucs_mpa = 120; in.rqd_pct = rqd; in.spacing_m = 0.5; in.joint_condition_rating = 20; in.water = Water::Dry;
    EXPECT_NO_THROW(rmr89(in));
}
