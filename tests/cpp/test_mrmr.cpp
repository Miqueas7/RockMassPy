#include <gtest/gtest.h>

#include <cmath>
#include <limits>
#include <stdexcept>
#include <string>

#include "rockmasspy/mrmr.hpp"

using namespace rockmasspy;

TEST(Mrmr90Ratings, Irs) {
    EXPECT_EQ(rating_irs90(185), 18);
    EXPECT_EQ(rating_irs90(185.5), 20);
    EXPECT_EQ(rating_irs90(165), 18);
    EXPECT_EQ(rating_irs90(164.5), 16);
    EXPECT_EQ(rating_irs90(100), 10);
    EXPECT_EQ(rating_irs90(1), 1);
    EXPECT_EQ(rating_irs90(0.5), 0);
    EXPECT_THROW(rating_irs90(-1), std::invalid_argument);
}

TEST(Mrmr90Ratings, Rqd) {
    EXPECT_EQ(rating_rqd90(97), 15);
    EXPECT_EQ(rating_rqd90(96.5), 14);
    EXPECT_EQ(rating_rqd90(75), 12);
    EXPECT_EQ(rating_rqd90(3.5), 0);
    EXPECT_THROW(rating_rqd90(101), std::invalid_argument);
}

TEST(Mrmr90Spacing, Ecuaciones) {
    // Errata p. 259: Laubscher imprime 0.88 x 25 = 22 y su ecuacion da 0.8985; con dos familias imprime 0.81 x 0.86
    // y la ecuacion da 0.82 x 0.88 (17 contra 18.04); el ejemplo de tres familias imprime 14. Se usan las ecuaciones.
    EXPECT_NEAR(rating_joint_spacing90({0.5}), 22.463202, 1e-6);
    EXPECT_NEAR(rating_joint_spacing90({1.0, 0.5}), 18.040731, 1e-6);
    EXPECT_NEAR(rating_joint_spacing90({3.0, 0.5, 1.0}), 13.551970, 1e-6);
    EXPECT_DOUBLE_EQ(rating_joint_spacing90({2.0}), 25.0);  // factor acotado a 1
    EXPECT_DOUBLE_EQ(rating_joint_spacing90({0.5, 1.0, 3.0, 5.0}), rating_joint_spacing90({0.5, 1.0, 3.0}));
    EXPECT_THROW(rating_joint_spacing90({}), std::invalid_argument);
    EXPECT_THROW(rating_joint_spacing90({1.0, 0.0}), std::invalid_argument);
}

TEST(Mrmr90Ff, Tabla) {
    EXPECT_EQ(rating_ff90(1.0, 3), 26);
    EXPECT_EQ(rating_ff90(1.2, 3), 24);  // fila 1.5
    EXPECT_EQ(rating_ff90(0.05, 1), 40);
    EXPECT_EQ(rating_ff90(45, 1), 0);
    EXPECT_EQ(rating_ff90(1.0, 3, 50), 21);  // FF/m corregido 2.0
    EXPECT_EQ(rating_ff90(1.0, 5), 26);      // mas de 3 familias se toma como 3
    EXPECT_THROW(rating_ff90(1.0, 0), std::invalid_argument);
    EXPECT_THROW(rating_ff90(1.0, 2, 0.0), std::invalid_argument);
    EXPECT_THROW(rating_ff90(1.0, 2, 101.0), std::invalid_argument);
}

TEST(Mrmr90JointCondition, Producto) {
    // Errata p. 261: el ejemplo rotula A = 70 y B = 65; la tabla da 75 y 60 y el producto, 27 %, calza.
    JointCondition90 j;
    j.large = JointExpressionLarge::Straight;
    j.small = JointExpressionSmall::SmoothPlanar;
    j.filling = JointFilling90::SoftMedium;
    j.water = JointWater90::Dry;
    EXPECT_NEAR(joint_condition90(j), 10.8, 1e-9);
    j.water.reset();
    EXPECT_THROW(joint_condition90(j), std::invalid_argument);
    JointCondition90 k;
    k.large = JointExpressionLarge::MultiWavyDirectional;
    k.small = JointExpressionSmall::RoughStepped;
    k.water = JointWater90::Dry;
    k.altered_wall = true;
    EXPECT_NEAR(joint_condition90(k), 40 * 1.0 * 0.95 * 0.75, 1e-9);
}

TEST(Mrmr90Adjustments, Tablas) {
    EXPECT_EQ(weathering_adjustment90(Weathering90::Slight, 0.25), 88);
    EXPECT_EQ(weathering_adjustment90(Weathering90::Slight, 2.5), 92);
    EXPECT_EQ(weathering_adjustment90(Weathering90::High, 10), 78);
    EXPECT_EQ(blasting_adjustment90(Blasting90::Poor), 80);
    EXPECT_EQ(blasting_adjustment90(Blasting90::Boring), 100);
}

TEST(Mrmr90Class, Subclases) {
    EXPECT_EQ(laubscher_class(46.35), "3B");
    EXPECT_EQ(laubscher_class(26.59), "4B");
    EXPECT_EQ(laubscher_class(80.5), "2A");
    EXPECT_EQ(laubscher_class(91), "1A");
    EXPECT_EQ(laubscher_class(0), "5B");
    EXPECT_EQ(laubscher_class(11), "5A");
}

static Mrmr90Input synthetic() {
    Mrmr90Input in;
    in.irs_mpa = 100;
    in.rqd_pct = 75;
    in.spacings_m = {0.5, 1.0, 3.0};
    in.joint_condition = 10.8;
    in.weathering_pct = 85;
    in.orientation_pct = 75;
    in.stress_pct = 100;
    in.blasting_pct = 90;
    return in;
}

TEST(Mrmr90, CasoSintetico) {  // ejemplo de la p. 266
    const auto r = mrmr90(synthetic());
    EXPECT_NEAR(r.rmr, 46.351970, 1e-6);
    EXPECT_EQ(r.rmr_class, "3B");
    EXPECT_NEAR(r.adjustment, 0.57375, 1e-12);
    EXPECT_NEAR(r.mrmr, 26.594443, 1e-6);
    EXPECT_EQ(r.mrmr_class, "4B");
    EXPECT_TRUE(r.warnings.empty());
    EXPECT_TRUE(std::isnan(r.ff_rating));
    EXPECT_EQ(r.info.method_id, "MRMR-Laubscher1990");
}

TEST(Mrmr90, ViaFf) {
    Mrmr90Input in = synthetic();
    in.rqd_pct = validation::unset;
    in.spacings_m.clear();
    in.ff_per_m = 50;
    in.joint_sets = 2;
    const auto r = mrmr90(in);
    EXPECT_TRUE(std::isnan(r.rqd_rating));
    EXPECT_EQ(r.ff_rating, 0);
    ASSERT_EQ(r.warnings.size(), 1u);
    EXPECT_EQ(r.warnings[0], "FF/m above Table I (40 per m): rating 0");
}

TEST(Mrmr90, Errores) {
    const std::string msg = "pass rqd_pct and spacings_m, or ff_per_m and joint_sets";
    Mrmr90Input both = synthetic();
    both.ff_per_m = 5;
    both.joint_sets = 2;
    Mrmr90Input none = synthetic();
    none.rqd_pct = validation::unset;
    none.spacings_m.clear();
    for (const auto& in : {both, none}) {
        try {
            mrmr90(in);
            FAIL();
        } catch (const std::invalid_argument& e) {
            EXPECT_EQ(std::string(e.what()), msg);
        }
    }
    const double nan = std::numeric_limits<double>::quiet_NaN();
    Mrmr90Input a = synthetic(); a.irs_mpa = nan;
    Mrmr90Input b = synthetic(); b.joint_condition = nan;
    Mrmr90Input c = synthetic(); c.stress_pct = nan;
    Mrmr90Input d = synthetic(); d.joint_condition = 41;
    Mrmr90Input e = synthetic(); e.blasting_pct = 0;
    for (const auto& in : {a, b, c, d, e}) EXPECT_THROW(mrmr90(in), std::invalid_argument);
}

TEST(Mrmr90, AvisosDeAjuste) {
    Mrmr90Input in = synthetic();
    in.orientation_pct = 50;
    in.stress_pct = 130;
    const auto r = mrmr90(in);
    ASSERT_EQ(r.warnings.size(), 2u);
    EXPECT_EQ(r.warnings[0], "orientation adjustment outside 63-100 % (Laubscher 1990, p. 266)");
    EXPECT_EQ(r.warnings[1], "induced stress adjustment outside 60-120 % (Laubscher 1990, p. 266)");
}
