#include <gtest/gtest.h>

#include <string>

#include "error_of.hpp"
#include "rockmasspy/kinematics.hpp"

using namespace rockmasspy;

namespace {
const KinematicInput kIn{{180, 60}, 30, 20};
KinematicInput with(double phi, double lim, double face_dip = 60) { return {{180, face_dip}, phi, lim}; }
}  // namespace

TEST(Kinematics, Planar) {
    EXPECT_TRUE(check_plane({180, 45}, kIn).planar);
    EXPECT_FALSE(check_plane({180, 25}, kIn).planar);   // fricción
    EXPECT_FALSE(check_plane({180, 70}, kIn).planar);   // no aflora
    EXPECT_FALSE(check_plane({0, 45}, kIn).planar);
    const auto oblique = check_plane({210, 45}, kIn);
    EXPECT_FALSE(oblique.planar);
    EXPECT_TRUE(oblique.planar_no_limits);
    EXPECT_TRUE(check_plane({200, 45}, kIn).planar);    // |Δ| = L
    EXPECT_TRUE(check_plane({180, 30}, kIn).planar);    // βj = φ
}

TEST(Kinematics, FlexuralToppling) {
    EXPECT_TRUE(check_plane({0, 70}, kIn).flexural_toppling);
    EXPECT_FALSE(check_plane({0, 50}, kIn).flexural_toppling);
    EXPECT_TRUE(check_plane({0, 60}, kIn).flexural_toppling);  // justo en el plano límite
    EXPECT_FALSE(check_plane({30, 70}, kIn).flexural_toppling);
    EXPECT_TRUE(check_plane({30, 70}, with(30, 30)).flexural_toppling);
    const auto flat = with(30, 20, 30);  // βs = φ: nada es crítico
    for (double dd : {0.0, 90.0, 180.0}) EXPECT_FALSE(check_plane({dd, 80}, flat).flexural_toppling);
}

TEST(Kinematics, Wedge) {
    EXPECT_TRUE(check_intersection({180, 40}, kIn).wedge_primary);
    auto c = check_intersection({240, 25}, kIn);
    EXPECT_TRUE(c.wedge_secondary);
    EXPECT_FALSE(c.wedge_primary);
    EXPECT_TRUE(check_intersection({240, 35}, kIn).wedge_primary);  // sin límites laterales
    c = check_intersection({180, 25}, kIn);
    EXPECT_FALSE(c.wedge_primary || c.wedge_secondary);
    c = check_intersection({270, 10}, kIn);
    EXPECT_FALSE(c.wedge_primary || c.wedge_secondary);
}

TEST(Kinematics, DirectToppling) {
    EXPECT_TRUE(check_intersection({0, 45}, kIn).direct_toppling);
    EXPECT_FALSE(check_intersection({0, 20}, kIn).direct_toppling);
    EXPECT_TRUE(check_intersection({0, 30}, kIn).direct_toppling);  // inmersión = 90 - βs
    auto c = check_intersection({90, 85}, kIn);
    EXPECT_TRUE(c.direct_toppling_oblique);
    EXPECT_FALSE(c.direct_toppling);
    c = check_intersection({90, 50}, kIn);
    EXPECT_FALSE(c.direct_toppling || c.direct_toppling_oblique);
    EXPECT_EQ(check_plane({180, 45}, kIn).direct_toppling_base_zone, 1);
    EXPECT_EQ(check_plane({180, 20}, kIn).direct_toppling_base_zone, 2);
    EXPECT_EQ(check_plane({250, 20}, kIn).direct_toppling_base_zone, 3);
    EXPECT_EQ(check_plane({0, 20}, kIn).direct_toppling_base_zone, 0);
}

TEST(Kinematics, Analysis) {
    // 0 y 1 de familias distintas; 2 sin familia; 3 paralelo al 0 (otra familia): sin intersección
    const std::vector<PlaneOrientation> p{{180, 45}, {0, 70}, {100, 50}, {180, 45}};
    const auto r = kinematic_analysis(p, {0, 1, -1, 1}, kIn);
    EXPECT_EQ(r.n_planes, 4);
    EXPECT_EQ(r.n_parallel_pairs, 1);
    EXPECT_EQ(r.n_intersections, 4);  // 6 pares, menos el par 1-3 (misma familia), menos el paralelo 0-3
    EXPECT_EQ(r.pair_a.size(), 4u);
    EXPECT_EQ(r.planar, 2);
    ASSERT_EQ(r.notes.size(), 1u);
    EXPECT_EQ(r.notes[0], "1 parallel plane pairs give no intersection");
    ASSERT_EQ(r.methods.size(), 4u);
    for (const auto& m : r.methods) EXPECT_EQ(m.verification, Verification::Secondary);
}

TEST(Kinematics, Validation) {
    EXPECT_NE(error_of([] { check_plane({180, 45}, with(0, 20)); }).find("friction_deg"), std::string::npos);
    EXPECT_NE(error_of([] { check_plane({180, 45}, with(90, 20)); }).find("friction_deg"), std::string::npos);
    EXPECT_NE(error_of([] { check_plane({180, 45}, with(30, 0)); }).find("lateral_limit_deg"), std::string::npos);
    EXPECT_NE(error_of([] { check_plane({180, 45}, with(30, 90)); }).find("lateral_limit_deg"), std::string::npos);
    EXPECT_NE(error_of([] { check_plane({180, 45}, with(30, 20, 0)); }).find("dip_deg"), std::string::npos);
    EXPECT_NE(error_of([] { kinematic_analysis({{0, 10}}, {0, 1}, kIn); }).find("groups"), std::string::npos);
}
