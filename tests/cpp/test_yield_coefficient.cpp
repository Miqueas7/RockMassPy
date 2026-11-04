#include <gtest/gtest.h>

#include <cmath>
#include <string>

#include "rockmasspy/slip_search.hpp"
#include "rockmasspy/yield_coefficient.hpp"

using namespace rockmasspy;

namespace {
LeMaterial mc(double g, double c, double phi) {
    LeMaterial m;
    m.unit_weight = g; m.cohesion = c; m.friction_deg = phi;
    return m;
}
std::vector<Point2> mirror(const std::vector<Point2>& p) {
    std::vector<Point2> q(p.rbegin(), p.rend());
    for (auto& v : q) v.x = -v.x;
    return q;
}
SlipSurface circle(double xc, double yc, double r) {
    SlipSurface f;
    f.circle = Circle{xc, yc, r};
    return f;
}
bool has(const std::vector<std::string>& v, const std::string& s) {
    for (const auto& w : v)
        if (w.find(s) != std::string::npos) return true;
    return false;
}
// Fredlund y Krahn (1977), Slide problema 21, seco
LeSection fk() {
    LeSection s;
    s.surface = {{0, 60}, {60, 60}, {140, 20}, {180, 20}};
    s.layers = {LeLayer{{}, 0}};
    s.materials = {mc(120, 600, 20)};
    return s;
}
// ACADS 1(c)/1(d), Slide problemas 3 y 4 (contactos de la figura 3.1, como en test_slip_search.cpp)
LeSection acads1c(double kh) {
    LeSection s;
    s.surface = {{20, 25}, {30, 25}, {50, 35}, {70, 35}};
    s.materials = {mc(19.5, 0, 38), mc(19.5, 5.3, 23), mc(19.5, 7.2, 20)};
    s.layers = {LeLayer{{{20, 25}, {30, 25}, {40, 27}, {50, 29}, {54, 31}, {70, 31}}, 0},
                LeLayer{{{20, 25}, {30, 25}, {40, 27}, {52, 24}, {70, 24}}, 1}, LeLayer{{}, 2}};
    s.model_base_y = 20;
    s.kh = kh;
    return s;
}
}  // namespace

TEST(YieldCoefficient, FredlundKrahnBishopGivesFsOne) {
    const auto r = le_yield_coefficient(fk(), circle(120, 90, 80), LeMethod::Bishop);
    ASSERT_TRUE(r.ky.has_value());
    EXPECT_GT(*r.ky, 0.0);
    EXPECT_LT(*r.ky, 1.0);
    EXPECT_NEAR(r.fs_static, 2.0756, 2e-3);
    LeSection s = fk();
    s.kh = *r.ky;
    EXPECT_NEAR(*le_factor_of_safety(s, circle(120, 90, 80), LeMethod::Bishop).factor_of_safety, 1.0, 1e-6);
    EXPECT_EQ(r.info.verification, Verification::Secondary);
    EXPECT_TRUE(r.warnings.empty());
}

TEST(YieldCoefficient, ReflectedSectionGivesSameKy) {
    LeSection m = fk();
    m.surface = mirror(m.surface);
    const auto a = le_yield_coefficient(fk(), circle(120, 90, 80), LeMethod::Spencer);
    const auto b = le_yield_coefficient(m, circle(-120, 90, 80), LeMethod::Spencer);
    ASSERT_TRUE(a.ky && b.ky);
    EXPECT_NEAR(*a.ky, *b.ky, 1e-6);
}

// Slide 1(d): Bishop 1.016 con kh 0.15, así que el ky de Bishop en ese círculo queda cerca de 0.15
TEST(YieldCoefficient, Acads1dBishopCircle) {
    CircularGrid g;
    g.x_min = 22.8; g.x_max = 43.7; g.y_min = 42.3; g.y_max = 62.6;
    SearchOptions o;
    o.method = LeMethod::Bishop;
    const auto sr = search_circular(acads1c(0.15), g, o);
    ASSERT_TRUE(sr.surface.circle.has_value());
    const auto r = le_yield_coefficient(acads1c(0.15), sr.surface, LeMethod::Bishop);
    ASSERT_TRUE(r.ky.has_value());
    EXPECT_NEAR(*r.ky, 0.15, 0.02);
}

TEST(YieldCoefficient, StaticFailureGivesZero) {
    LeSection s = fk();
    s.materials[0].cohesion = 0.0;
    s.materials[0].friction_deg = 5.0;
    const auto r = le_yield_coefficient(s, circle(120, 90, 80), LeMethod::Bishop);
    ASSERT_TRUE(r.ky.has_value());
    EXPECT_EQ(*r.ky, 0.0);
    EXPECT_TRUE(has(r.warnings, "static factor of safety at or below 1"));
}

TEST(YieldCoefficient, StrongSlopeGivesNoKyWithNote) {
    LeSection s = fk();
    s.materials[0].cohesion = 1e6;
    const auto r = le_yield_coefficient(s, circle(120, 90, 80), LeMethod::Bishop);
    EXPECT_FALSE(r.ky.has_value());
    EXPECT_TRUE(has(r.notes, "kh = 1"));
}

TEST(YieldCoefficient, NonConvergenceGivesNoKyWithWarning) {
    LeOptions o;
    o.max_iterations = 1;
    const auto r = le_yield_coefficient(fk(), circle(120, 90, 80), LeMethod::Spencer, o);
    EXPECT_FALSE(r.ky.has_value());
    EXPECT_TRUE(has(r.warnings, "ky not found"));
}
