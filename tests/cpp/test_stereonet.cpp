#include <gtest/gtest.h>

#include <cmath>
#include <limits>
#include <stdexcept>
#include <string>

#include "error_of.hpp"
#include "rockmasspy/stereonet.hpp"

using namespace rockmasspy;

namespace {
double adiff(double a, double b) {
    double d = std::fabs(std::fmod(a - b, 360.0));
    return d > 180.0 ? 360.0 - d : d;
}
void expect_line(const std::optional<LineOrientation>& l, double trend, double plunge, double tol = 1.0) {
    ASSERT_TRUE(l.has_value());
    EXPECT_LE(adiff(l->trend_deg, trend), tol);
    EXPECT_NEAR(l->plunge_deg, plunge, tol);
}
}  // namespace

TEST(Stereonet, PoleAndPlane) {
    auto p = pole_of({180, 60});
    EXPECT_NEAR(p.trend_deg, 0, 1e-12);
    EXPECT_NEAR(p.plunge_deg, 30, 1e-12);
    p = pole_of({350, 20});
    EXPECT_NEAR(p.trend_deg, 170, 1e-12);
    EXPECT_NEAR(p.plunge_deg, 70, 1e-12);
    auto q = plane_of(pole_of({360, 30}));
    EXPECT_NEAR(q.dip_direction_deg, 0, 1e-12);
    EXPECT_NEAR(q.dip_deg, 30, 1e-12);
    q = plane_of(pole_of({123.4, 56.7}));
    EXPECT_NEAR(q.dip_direction_deg, 123.4, 1e-9);
    EXPECT_NEAR(q.dip_deg, 56.7, 1e-9);
}

TEST(Stereonet, Projections) {
    EXPECT_NEAR(project({0, 45}, Projection::EqualAngle).y, 0.41421356, 1e-8);
    EXPECT_NEAR(project({0, 45}, Projection::EqualArea).y, 0.54119610, 1e-8);
    for (auto p : {Projection::EqualAngle, Projection::EqualArea}) {
        auto c = project({70, 90}, p);
        EXPECT_NEAR(c.x, 0, 1e-12);
        EXPECT_NEAR(c.y, 0, 1e-12);
        auto e = project({90, 0}, p);
        EXPECT_NEAR(e.x, 1, 1e-12);
        EXPECT_NEAR(e.y, 0, 1e-12);
        auto l = unproject(project({200, 33}, p), p);
        EXPECT_NEAR(l.trend_deg, 200, 1e-9);
        EXPECT_NEAR(l.plunge_deg, 33, 1e-9);
    }
    EXPECT_THROW(unproject({1.0, 0.1}, Projection::EqualArea), std::invalid_argument);
}

TEST(Stereonet, PublishedIntersections) {  // Riquelme et al. 2016, Tabla 4, p. 21
    PlaneOrientation f1{325, 87}, f2{119, 20}, f3{234, 83}, f4{62, 62};
    expect_line(plane_intersection(f1, f2), 55, 9);
    expect_line(plane_intersection(f1, f4), 49, 61);
    expect_line(plane_intersection(f2, f3), 146, 18);
    expect_line(plane_intersection(f2, f4), 142, 19);
    expect_line(plane_intersection(f3, f4), 145, 12);
    PlaneOrientation s1{323, 89}, s2{135, 26}, s3{250, 76}, s4{41, 57};
    expect_line(plane_intersection(s1, s2), 53, 4);
    expect_line(plane_intersection(s1, s4), 51, 57);
    expect_line(plane_intersection(s2, s3), 166, 23);
    expect_line(plane_intersection(s2, s4), 114, 24);
}

TEST(Stereonet, IntersectionProperties) {
    PlaneOrientation a{325, 87}, b{119, 20};
    auto ab = plane_intersection(a, b);
    auto ba = plane_intersection(b, a);
    ASSERT_TRUE(ab && ba);
    EXPECT_NEAR(ab->trend_deg, ba->trend_deg, 1e-9);
    EXPECT_NEAR(ab->plunge_deg, ba->plunge_deg, 1e-9);
    EXPECT_NEAR(angle_between(pole_of(a), *ab), 90, 1e-9);
    EXPECT_NEAR(angle_between(pole_of(b), *ab), 90, 1e-9);
    EXPECT_FALSE(plane_intersection(a, a));
    EXPECT_FALSE(plane_intersection({10, 90}, {190, 90}));  // verticales paralelos, opuestos
    EXPECT_FALSE(plane_intersection({10, 40}, {10, 40.0}));
}

TEST(Stereonet, EdgesOfDomain) {
    auto p = pole_of({360, 30});
    EXPECT_NEAR(p.trend_deg, 180, 1e-12);
    // dip 90: dirección 90 y 270 dan el mismo eje
    EXPECT_NEAR(angle_between(pole_of({90, 90}), pole_of({270, 90})), 0, 1e-9);
    for (const auto& pt : great_circle({40, 0}, Projection::EqualAngle, 11))
        EXPECT_NEAR(std::hypot(pt.x, pt.y), 1, 1e-9);
    // plano vertical: un diámetro (pasa por el centro y todos los puntos sobre una recta)
    auto g = great_circle({90, 90}, Projection::EqualArea, 181);
    ASSERT_EQ(g.size(), 181u);
    for (const auto& pt : g) EXPECT_NEAR(pt.x, 0, 1e-9);
    EXPECT_NEAR(g[90].y, 0, 1e-9);
    EXPECT_NEAR(std::fabs(g[0].y), 1, 1e-9);
    EXPECT_NEAR(g[0].y, -g[180].y, 1e-9);
    EXPECT_THROW(great_circle({0, 30}, Projection::EqualArea, 2), std::invalid_argument);
}

TEST(Stereonet, Validation) {
    EXPECT_NE(error_of([] { pole_of({0, 95}); }).find("dip_deg"), std::string::npos);
    EXPECT_NE(error_of([] { pole_of({-5, 30}); }).find("dip_direction_deg"), std::string::npos);
    const double nan = std::numeric_limits<double>::quiet_NaN();
    const double inf = std::numeric_limits<double>::infinity();
    EXPECT_NE(error_of([&] { pole_of({nan, 30}); }).find("dip_direction_deg"), std::string::npos);
    EXPECT_NE(error_of([&] { pole_of({10, inf}); }).find("dip_deg"), std::string::npos);
    EXPECT_NE(error_of([&] { plane_of({nan, 30}); }).find("trend_deg"), std::string::npos);
    EXPECT_NE(error_of([] { plane_of({10, 91}); }).find("plunge_deg"), std::string::npos);
    EXPECT_NE(error_of([] { project({361, 10}, Projection::EqualArea); }).find("trend_deg"), std::string::npos);
    EXPECT_NE(error_of([&] { unproject({nan, 0}, Projection::EqualArea); }).find("x"), std::string::npos);
}
