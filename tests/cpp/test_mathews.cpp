#include <gtest/gtest.h>

#include <cmath>
#include <limits>
#include <stdexcept>
#include <string>

#include "rockmasspy/mathews.hpp"

using namespace rockmasspy;

TEST(MathewsA, Puntos) {
    EXPECT_EQ(mathews_factor_a(100, 50).value, 0.1);
    EXPECT_NEAR(mathews_factor_a(100, 25).value, 0.325, 1e-12);
    EXPECT_EQ(mathews_factor_a(100, 10).value, 1.0);
    EXPECT_EQ(mathews_factor_a(100, 5).value, 1.0);
    EXPECT_EQ(mathews_factor_a(100, 0).value, 1.0);   // relajación (R4)
    EXPECT_EQ(mathews_factor_a(100, -5).value, 1.0);
}

TEST(MathewsC, Gravedad) {
    EXPECT_EQ(mathews_factor_c_gravity(0).value, 2.0);
    EXPECT_NEAR(mathews_factor_c_gravity(90).value, 8.0, 1e-12);
    EXPECT_NEAR(mathews_factor_c_gravity(60).value, 5.0, 1e-12);
    EXPECT_NEAR(mathews_factor_c_gravity(45).value, 3.757359, 1e-6);
}

TEST(MathewsC, Deslizamiento) {
    EXPECT_EQ(mathews_factor_c_sliding(20).value, 8.0);
    EXPECT_EQ(mathews_factor_c_sliding(30).value, 8.0);
    EXPECT_NEAR(mathews_factor_c_sliding(60).value, 5.0, 1e-12);
    EXPECT_NEAR(mathews_factor_c_sliding(90).value, 2.0, 1e-12);
}

TEST(MathewsHR, Valores) {
    EXPECT_EQ(hydraulic_radius(100, 40), 2.5);
    EXPECT_NEAR(hydraulic_radius_rect(10, 20), 3.333333, 1e-6);
    EXPECT_EQ(hydraulic_radius_rect(30, 15), 5.0);
}

TEST(MathewsHR, AreaImposible) {  // Foco 1
    try {
        hydraulic_radius(130, 40);
        FAIL() << "debía lanzar";
    } catch (const std::invalid_argument& e) {
        EXPECT_NE(std::string(e.what()).find("area too large"), std::string::npos);
    }
    EXPECT_NO_THROW(hydraulic_radius(127, 40));
}

TEST(MathewsFoco4, Rechazos) {
    const double nan = std::numeric_limits<double>::quiet_NaN();
    const double inf = std::numeric_limits<double>::infinity();
    EXPECT_THROW(mathews_factor_a(nan, 10), std::invalid_argument);
    EXPECT_THROW(mathews_factor_a(100, nan), std::invalid_argument);
    EXPECT_THROW(mathews_factor_a(100, inf), std::invalid_argument);
    EXPECT_THROW(mathews_factor_a(0, 10), std::invalid_argument);
    EXPECT_THROW(mathews_factor_c_gravity(-1), std::invalid_argument);
    EXPECT_THROW(mathews_factor_c_gravity(91), std::invalid_argument);
    EXPECT_THROW(mathews_factor_c_gravity(nan), std::invalid_argument);
    EXPECT_THROW(mathews_factor_c_sliding(90.5), std::invalid_argument);
    EXPECT_THROW(mathews_factor_c_sliding(inf), std::invalid_argument);
    EXPECT_THROW(hydraulic_radius(nan, 40), std::invalid_argument);
    EXPECT_THROW(hydraulic_radius(100, 0), std::invalid_argument);
    EXPECT_THROW(hydraulic_radius_rect(0, 5), std::invalid_argument);
    EXPECT_THROW(hydraulic_radius_rect(5, inf), std::invalid_argument);
}

TEST(MathewsInfo, Fuente) {
    for (const auto& r : {mathews_factor_a(100, 25), mathews_factor_c_gravity(45), mathews_factor_c_sliding(45)}) {
        EXPECT_EQ(r.info.method_id, "Mathews-Potvin1988");
        EXPECT_EQ(r.info.verification, Verification::Primary);
    }
}
