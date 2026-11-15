#include <gtest/gtest.h>

#include <cmath>
#include <limits>

#include "error_of.hpp"
#include "rockmasspy/excavation.hpp"

using namespace rockmasspy;

namespace {
const double kNan = std::numeric_limits<double>::quiet_NaN();
EinsteinSchwartzInput rs2_p7(double theta) {
    EinsteinSchwartzInput in;
    in.sigma_v_mpa = 15; in.k_ratio = 2; in.e_rock_mpa = 6000; in.nu_rock = 0.2;
    in.e_lining_mpa = 20000; in.nu_lining = 0.2; in.thickness_m = 0.5; in.radius_m = 2.5; in.theta_deg = theta;
    return in;
}
}  // namespace

TEST(Kirsch, BordeHidrostatico) {  // RS2-S problema 1
    const auto b = kirsch_boundary(30, 1);
    EXPECT_NEAR(b.crown_mpa, 60, 1e-9);
    EXPECT_NEAR(b.sidewall_mpa, 60, 1e-9);
    const auto s = kirsch_stress(30, 1, 1, 1, 0);
    EXPECT_NEAR(s.sigma_r, 0, 1e-9);
    EXPECT_NEAR(s.sigma_theta, 60, 1e-9);
    const auto f = kirsch_stress(30, 1, 1, 5, 0);  // recálculo propio, FORMULAS §1.3
    EXPECT_NEAR(f.sigma_r, 28.8, 1e-9);
    EXPECT_NEAR(f.sigma_theta, 31.2, 1e-9);
    EXPECT_EQ(s.info.method_id, "Kirsch-1898");
}

TEST(Kirsch, KDistintoDeUno) {
    const auto b = kirsch_boundary(10, 0.5);
    EXPECT_NEAR(b.crown_mpa, 5, 1e-9);
    EXPECT_NEAR(b.sidewall_mpa, 25, 1e-9);
    EXPECT_NEAR(kirsch_stress(10, 0.5, 2, 2, 0).sigma_theta, 25, 1e-9);
    EXPECT_NEAR(kirsch_stress(10, 0.5, 2, 2, 90).sigma_theta, 5, 1e-9);
    EXPECT_NEAR(kirsch_stress(10, 0.5, 2, 3, 0).tau_r_theta, 0, 1e-9);
    EXPECT_NEAR(kirsch_stress(10, 0.5, 2, 3, 90).tau_r_theta, 0, 1e-9);
}

TEST(Kirsch, Errores) {
    const auto e1 = error_of([] { kirsch_stress(10, 1, 0, 1, 0); });
    EXPECT_NE(e1.find("'radius_m'"), std::string::npos);
    const auto e2 = error_of([] { kirsch_stress(10, 1, 2, 1.5, 0); });
    EXPECT_NE(e2.find("'r_m'"), std::string::npos);
    EXPECT_EQ(e2.find("1.5"), std::string::npos);
    EXPECT_FALSE(error_of([] { kirsch_stress(kNan, 1, 2, 3, 0); }).empty());
}

TEST(Ellipse, CirculoReproduceKirsch) {
    EXPECT_NEAR(ellipse_boundary_stress(20, 10, 1, 1, 0), 50, 1e-9);
    EXPECT_NEAR(ellipse_boundary_stress(20, 10, 1, 1, 90), 10, 1e-9);
}

TEST(Ellipse, HuecoArmonico) {
    for (double th : {0.0, 0.3 * 180 / 3.14159265358979, 0.9 * 180 / 3.14159265358979, 90.0})
        EXPECT_NEAR(ellipse_boundary_stress(20, 10, 1, 2, th), 30.0, 1e-9);
}

TEST(Ellipse, Extremos) {
    const auto e = ellipse_ends(20, 0.5, 4, 2);  // a = 2, b = 1
    EXPECT_NEAR(e.sidewall_mpa, 90.0, 1e-9);
    EXPECT_NEAR(e.crown_mpa, 0.0, 1e-9);
    EXPECT_NEAR(ellipse_boundary_stress(20, 10, 2, 1, 0), 90.0, 1e-9);
    EXPECT_NEAR(ellipse_boundary_stress(20, 10, 2, 1, 90), 0.0, 1e-9);
    const std::string err = error_of([] { ellipse_boundary_stress(20, 10, 1, 0, 0); });
    EXPECT_NE(err.find("'b_m'"), std::string::npos);
}

TEST(EinsteinSchwartz, RS2Problema7) {
    const auto r0 = einstein_schwartz(rs2_p7(0));
    EXPECT_NEAR(r0.c_star, 1.5, 1e-9);
    EXPECT_NEAR(r0.f_star, 450, 1e-9);
    EXPECT_NEAR(r0.n_mn, 14.61, 0.01);
    EXPECT_NEAR(r0.m_mnm, -0.703, 0.001);
    const auto r45 = einstein_schwartz(rs2_p7(45));
    EXPECT_NEAR(r45.n_mn, 25.61, 0.01);
    EXPECT_NEAR(r45.m_mnm, 0, 0.001);
    const auto r90 = einstein_schwartz(rs2_p7(90));
    EXPECT_NEAR(r90.n_mn, 36.62, 0.01);
    EXPECT_NEAR(r90.m_mnm, 0.703, 0.001);
    EXPECT_EQ(r0.info.method_id, "Lining-Einstein-Schwartz-1979");
}

TEST(EinsteinSchwartz, Errores) {
    auto in = rs2_p7(0);
    in.thickness_m = 0;
    EXPECT_NE(error_of([&] { einstein_schwartz(in); }).find("'thickness_m'"), std::string::npos);
    EXPECT_NE(error_of([] { einstein_schwartz({}); }).find("'sigma_v_mpa'"), std::string::npos);
}

TEST(Squeezing, HoekMarinosPRE) {
    const auto s = hoek_marinos(0.6, 4, 0, 2);  // sigma_cm/po = 0.15
    EXPECT_NEAR(s.plastic_radius_m, 7.37, 0.01);
    EXPECT_NEAR(s.strain_pct, 8.89, 0.01);
    EXPECT_NEAR(s.wall_displacement_m, 0.178, 0.001);
    EXPECT_EQ(s.squeezing_class, 'D');
    EXPECT_TRUE(s.in_fit_range);
    const auto s2 = hoek_marinos(0.6, 4, 1, 2);  // pi/po = 0.25
    EXPECT_NEAR(s2.strain_pct, 1.96, 0.01);
    EXPECT_EQ(s2.squeezing_class, 'B');
    EXPECT_FALSE(hoek_marinos(2.4, 4, 0, 2).in_fit_range);  // 0.6
    EXPECT_EQ(s.info.method_id, "Squeezing-Hoek-Marinos-2000");
}

TEST(Squeezing, Errores) {
    EXPECT_NE(error_of([] { hoek_marinos(1, 0, 0, 2); }).find("'p0_mpa'"), std::string::npos);
    EXPECT_NE(error_of([] { hoek_marinos(1, 4, -1, 2); }).find("'pi_mpa'"), std::string::npos);
    EXPECT_NE(error_of([] { hoek_marinos(1, 4, 0, 0); }).find("'radius_m'"), std::string::npos);
}
