#include <gtest/gtest.h>

#include <cmath>
#include <vector>

#include "error_of.hpp"
#include "rockmasspy/smr.hpp"

using namespace rockmasspy;

namespace {
const PlaneOrientation kFace{133, 72};  // Riquelme et al. (2016), Tabla 4
const auto kDis = SmrFunctions::Discrete;
const auto kCon = SmrFunctions::Continuous;
const auto kNormal = SlopeExcavation::NormalBlastingOrMechanical;

struct Row { SmrMode mode; double dir, dip, rmr, a, b, c, f1, f2, f3, smr; int cls; };
SmrMode P = SmrMode::Planar, T = SmrMode::Toppling, W = SmrMode::Wedge;
const std::vector<Row> kRows = {  // campo, SfM y láser de la Tabla 4
    {T, 325, 87, 44, 12, 87, 159, 0.70, 1, -25, 26, 4}, {T, 234, 83, 42, 79, 83, 155, 0.15, 1, -25, 38, 4},
    {P, 62, 62, 47, 71, 62, -10, 0.15, 1, -60, 38, 4},   {W, 55, 9, 44, 78, 9, -63, 0.15, 0.15, -60, 42, 3},
    {W, 49, 61, 44, 84, 61, -11, 0.15, 1, -60, 35, 4},   {W, 146, 18, 42, 13, 18, -54, 0.70, 0.15, -60, 35, 4},
    {W, 142, 19, 45, 9, 19, -53, 0.85, 0.15, -60, 37, 4}, {W, 145, 12, 42, 12, 12, -60, 0.70, 0.15, -60, 35, 4},
    {P, 135, 26, 45, 2, 26, -46, 1, 0.40, -60, 21, 4},   {T, 250, 76, 42, 63, 76, 148, 0.15, 1, -25, 38, 4},
    {T, 41, 57, 47, 88, 57, 129, 0.15, 1, -25, 43, 3},   {W, 166, 23, 42, 33, 23, -49, 0.15, 0.40, -60, 38, 4},
    {W, 114, 24, 45, 19, 24, -48, 0.70, 0.40, -60, 28, 4}, {T, 321, 87, 44, 8, 87, 159, 0.85, 1, -25, 22, 4},
    {P, 121, 16, 45, 12, 16, -56, 0.70, 0.15, -60, 38, 4}, {W, 139, 15, 42, 6, 15, -57, 0.85, 0.15, -60, 34, 4},
    {W, 113, 16, 45, 20, 16, -56, 0.70, 0.15, -60, 38, 4},
};
}  // namespace

TEST(Smr, Riquelme2016Table4) {
    for (const auto& w : kRows) {
        const auto a = smr_angles(w.mode, w.dir, w.dip, kFace);
        EXPECT_NEAR(a.a_deg, w.a, 0.5);
        EXPECT_NEAR(a.b_deg, w.b, 0.5);
        EXPECT_NEAR(a.c_deg, w.c, 0.5);
        const auto r = smr(w.rmr, w.mode, kDis, kNormal, a);
        EXPECT_EQ(r.f1, w.f1);
        EXPECT_EQ(r.f2, w.f2);
        EXPECT_EQ(r.f3, w.f3);
        EXPECT_EQ(std::floor(r.smr + 1e-9), w.smr);  // la tabla trunca
        EXPECT_EQ(r.smr_class, w.cls);
    }
}

TEST(Smr, BoundaryConventionDifferenceWithRiquelme) {
    // SfM J1 323/89 (A = 10): la tabla usa F1 = 0.70 (SMR 26); nuestra regla da 0.85. Campo J2 119/20 (B = 20):
    // la tabla usa F2 = 0.15 (SMR 38); nuestra regla da 0.40. No es errata: convención de SMRTool en el límite.
    auto r = smr(44, SmrMode::Toppling, kDis, kNormal, smr_angles(SmrMode::Toppling, 323, 89, kFace));
    EXPECT_EQ(r.f1, 0.85);
    EXPECT_NEAR(r.smr, 22.75, 1e-9);
    EXPECT_EQ(r.smr_class, 4);
    r = smr(45, SmrMode::Planar, kDis, kNormal, smr_angles(SmrMode::Planar, 119, 20, kFace));
    EXPECT_EQ(r.f2, 0.40);
    EXPECT_NEAR(r.smr, 28.2, 1e-9);
    EXPECT_EQ(r.smr_class, 4);
}

TEST(Smr, Tomas2006DiscreteProducts) {
    for (auto a : {SmrAngles{29, 21, -1}, SmrAngles{21, 29, -9}}) {
        const auto r = smr(50, SmrMode::Planar, kDis, kNormal, a);
        EXPECT_NEAR(r.f1 * r.f2 * r.f3, -8, 1e-9);
    }
}

TEST(Smr, ContinuousFormulas) {
    auto f = [](SmrMode m, SmrAngles a) { return smr(60, m, kCon, kNormal, a); };
    EXPECT_NEAR(f(SmrMode::Planar, {0, 45, 0}).f1, 0.997207, 1e-4);
    EXPECT_NEAR(f(SmrMode::Planar, {0, 0, 0}).f2, 0.158961, 1e-4);
    EXPECT_NEAR(f(SmrMode::Planar, {0, 90, 0}).f2, 0.995601, 1e-4);
    EXPECT_NEAR(f(SmrMode::Planar, {0, 45, -30}).f3, -59.3636, 1e-4);
    EXPECT_NEAR(f(SmrMode::Toppling, {0, 45, 130}).f3, -25.0413, 1e-4);
    EXPECT_EQ(f(SmrMode::Toppling, {0, 45, 130}).f2, 1.0);
    const auto r = f(SmrMode::Planar, {21, 29, -9});
    EXPECT_NEAR(r.f1 * r.f2 * r.f3, -15.975, 1e-3);  // no -7: ese valor es de las funciones de 2006
    const auto s = smr(60, SmrMode::Planar, kCon, kNormal, smr_angles(SmrMode::Planar, 180, 45, {180, 60}));
    EXPECT_NEAR(s.smr, 6.2368, 1e-3);
    EXPECT_EQ(s.smr_class, 5);
}

TEST(Smr, DiscreteLimits) {
    auto f = [](SmrMode m, SmrAngles a) { return smr(50, m, kDis, kNormal, a); };
    EXPECT_EQ(f(SmrMode::Planar, {10, 45, 20}).f1, 0.85);
    EXPECT_EQ(f(SmrMode::Planar, {20, 45, 20}).f1, 0.70);
    EXPECT_EQ(f(SmrMode::Planar, {5, 45, 20}).f1, 1.00);
    EXPECT_EQ(f(SmrMode::Planar, {40, 20, 20}).f2, 0.40);
    EXPECT_EQ(f(SmrMode::Planar, {40, 45, 20}).f2, 1.00);
    EXPECT_EQ(f(SmrMode::Planar, {40, 45, 0}).f3, -25);
    EXPECT_EQ(f(SmrMode::Planar, {40, 45, 0.5}).f3, -6);
    EXPECT_EQ(f(SmrMode::Planar, {40, 45, -10}).f3, -60);
    EXPECT_EQ(f(SmrMode::Toppling, {40, 45, 110}).f3, -6);
    EXPECT_EQ(f(SmrMode::Toppling, {40, 45, 120}).f3, -25);
    EXPECT_EQ(smr_class(20.5), 5);
    EXPECT_EQ(smr_class(21), 4);
    EXPECT_EQ(smr_class(80.5), 2);
    EXPECT_EQ(smr_class(81), 1);
}

TEST(Smr, F4AndProbabilityAndInfo) {
    const SmrAngles a{40, 45, 20};
    const double expect[] = {15, 10, 8, 0, -8};
    int i = 0;
    for (auto e : {SlopeExcavation::NaturalSlope, SlopeExcavation::Presplitting, SlopeExcavation::SmoothBlasting, kNormal,
                   SlopeExcavation::DeficientBlasting})
        EXPECT_EQ(smr(50, SmrMode::Planar, kDis, e, a).f4, expect[i++]);
    EXPECT_EQ(smr(50, SmrMode::Planar, kDis, kNormal, a).failure_probability, 0.4);
    EXPECT_EQ(smr(50, SmrMode::Planar, kDis, kNormal, a).info.method_id, "SMR-Romana1985");
    EXPECT_EQ(smr(50, SmrMode::Wedge, kDis, kNormal, a).info.verification, Verification::Secondary);
    EXPECT_EQ(smr(50, SmrMode::Wedge, kCon, kNormal, a).info.method_id, "SMR-Tomas2007");
}

TEST(Smr, OutOfRangeAndErrors) {
    const SmrAngles a{40, 45, 20};
    const auto r = smr(100, SmrMode::Planar, kDis, SlopeExcavation::NaturalSlope, a);
    EXPECT_EQ(r.smr, 115);
    EXPECT_EQ(r.smr_class, 1);
    ASSERT_EQ(r.warnings.size(), 1u);
    EXPECT_EQ(r.warnings[0], "SMR outside 0-100");
    auto bad = [&](double rmr, SmrMode m, SmrAngles x) {
        return !error_of([&] { smr(rmr, m, kDis, kNormal, x); }).empty();
    };
    EXPECT_TRUE(bad(101, SmrMode::Planar, a));
    EXPECT_TRUE(bad(std::nan(""), SmrMode::Planar, a));
    EXPECT_TRUE(bad(50, SmrMode::Planar, {190, 45, 20}));
    EXPECT_TRUE(bad(50, SmrMode::Planar, {40, 45, 100}));
    EXPECT_TRUE(bad(50, SmrMode::Toppling, {40, 45, -5}));
    EXPECT_FALSE(bad(50, SmrMode::Toppling, {40, 45, 150}));
}
