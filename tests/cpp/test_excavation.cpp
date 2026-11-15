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

// ---------------------------------------------------------------- GRC (Tarea 2)

namespace {
GrcMcInput rsv5(double c, double p0, double psi = 0) {
    GrcMcInput in;
    in.radius_m = 1; in.p0_mpa = p0; in.e_mpa = 10000; in.nu = 0.2; in.c_mpa = c; in.phi_deg = 30; in.psi_deg = psi;
    return in;
}
GrcMcInput soria(double psi) {
    GrcMcInput in;
    in.radius_m = 5; in.p0_mpa = 4.05; in.e_mpa = 446; in.nu = 0.3; in.c_mpa = 1; in.phi_deg = 37; in.psi_deg = psi;
    return in;
}
GrcMcInput rst1() {
    GrcMcInput in;
    in.radius_m = 6; in.p0_mpa = 1.62; in.e_mpa = 352.817; in.nu = 0.3; in.c_mpa = 0.2; in.phi_deg = 25.6394;
    in.sigma_cm_override_mpa = 0.46927;
    return in;
}
}  // namespace

TEST(GrcMc, RsvProblema5RadioPlastico) {
    EXPECT_NEAR(grc_mc_plastic_radius(rsv5(3.45, 30), 0), 1.735, 0.0005);
    EXPECT_NEAR(grc_mc_plastic_radius(rsv5(3.45, 20), 0), 1.474, 0.0005);
    EXPECT_NEAR(grc_mc_plastic_radius(rsv5(5, 30), 0), 1.494, 0.0005);
    EXPECT_NEAR(grc_mc_plastic_radius(rsv5(5, 20), 0), 1.286, 0.0005);
}

TEST(GrcMc, RsvDesplazamientoConDilatancia) {  // lectura de gráfica RSV Fig. 5-1 / recálculo FORMULAS §3.4
    EXPECT_NEAR(grc_mc_displacement(rsv5(3.45, 30, 0), 0) * 1000, 8.24, 0.01);
    EXPECT_NEAR(grc_mc_displacement(rsv5(3.45, 30, 30), 0) * 1000, 19.09, 0.01);
}

TEST(GrcMc, SoriaMedina) {
    EXPECT_NEAR(grc_mc_plastic_radius(soria(6), 0), 5.8573, 0.0001);
    EXPECT_NEAR(grc_mc_displacement(soria(6), 0) * 1000, 68.049, 0.001);
    EXPECT_NEAR(grc_mc_displacement(soria(0), 0) * 1000, 67.00, 0.01);  // Hoek PRE ec. 7
}

TEST(GrcMc, RstEjemplo1) {
    const auto in = rst1();
    EXPECT_NEAR(grc_mc_plastic_radius(in, 0), 13.78, 0.01);
    EXPECT_NEAR(grc_mc_displacement(in, 0) / 6 * 100, 2.030, 0.001);
    const auto r = grc_mc(in);
    EXPECT_EQ(r.info.method_id, "GRC-HB-equivalent-MC");
    EXPECT_EQ(r.info.verification, Verification::Secondary);
    EXPECT_FALSE(r.notes.empty());
    EXPECT_EQ(grc_mc(rsv5(3.45, 30)).info.method_id, "GRC-MC-Salencon-1969");
}

TEST(GrcMc, DesdeHoekBrown) {
    const auto in = grc_mc_from_hb(7, 15, 10, 0, 1.62, 6, 0.3, HbEdition::HB2002);
    EXPECT_NEAR(in.e_mpa, 352.817, 0.001);
    EXPECT_NEAR(in.sigma_cm_override_mpa, 0.46927, 0.00001);
    EXPECT_NEAR(in.phi_deg, 25.6394, 0.0001);
    EXPECT_NEAR(grc_mc_plastic_radius(in, 0), 13.78, 0.01);
}

TEST(GrcMc, PreFigura4) {  // recálculo de FORMULAS §3.4 (no el ajuste de 8 puntos de la hoja): k 2.437, σcm 0.694
    GrcMcInput in;
    in.radius_m = 3; in.p0_mpa = 2; in.e_mpa = 749.9; in.nu = 0.3;
    in.phi_deg = 24.717136120807158;  // recálculo del ajuste lineal de 8 puntos, sin redondear
    in.c_mpa = 0.22212309682455694; in.sigma_cm_override_mpa = 0.6935429667893569;
    const auto r = grc_mc(in);
    EXPECT_NEAR(r.p_crit_mpa, 0.962, 0.001);
    EXPECT_NEAR(r.rp_unsupported_m, 6.433, 0.001);
    EXPECT_NEAR(r.u_max_m, 0.03060, 0.00001);
}

TEST(GrcMc, CurvaMonotona) {
    for (const auto& in : {rsv5(3.45, 30, 30), soria(6), rst1()}) {
        const auto r = grc_mc(in, 80);
        ASSERT_EQ(r.curve.size(), 80u);
        EXPECT_NEAR(r.curve.front().pi_mpa, in.p0_mpa, 1e-12);
        EXPECT_NEAR(r.curve.front().u_m, 0, 1e-12);
        EXPECT_EQ(r.curve.back().pi_mpa, 0);
        for (size_t i = 1; i < r.curve.size(); ++i) EXPECT_GE(r.curve[i].u_m, r.curve[i - 1].u_m - 1e-12);
    }
}

TEST(GrcMc, TodoElastico) {  // p0 tan bajo que pcr <= 0
    auto in = rsv5(3.45, 1);
    const auto r = grc_mc(in);
    EXPECT_LE(r.p_crit_mpa, 0);
    EXPECT_DOUBLE_EQ(r.rp_unsupported_m, 1.0);
    EXPECT_NEAR(r.u_max_m, 1.0 * (1 + 0.2) * 1.0 / 10000, 1e-12);
    for (const auto& p : r.curve) {
        EXPECT_TRUE(std::isfinite(p.u_m));
        EXPECT_NEAR(p.u_m, (1.0 - p.pi_mpa) * 1.2 / 10000, 1e-12);
    }
}

TEST(GrcMc, Degenerado) {
    auto in = rsv5(3.45, 30);
    in.phi_deg = 0.5;
    const auto e1 = error_of([&] { grc_mc_displacement(in, 0); });
    EXPECT_NE(e1.find("'phi_deg'"), std::string::npos);
    EXPECT_EQ(e1.find("0.5"), std::string::npos);
    in = rsv5(0, 30);
    EXPECT_NE(error_of([&] { grc_mc_displacement(in, 0); }).find("'c_mpa'"), std::string::npos);
    EXPECT_NE(error_of([&] { grc_mc(in); }).find("'c_mpa'"), std::string::npos);
    EXPECT_TRUE(std::isfinite(grc_mc_displacement(in, 5)));  // c = 0 con pi > 0 sí se resuelve
    EXPECT_NE(error_of([] { grc_mc(GrcMcInput{}); }).find("'radius_m'"), std::string::npos);
    EXPECT_NE(error_of([] { grc_mc(rsv5(3.45, 30), 1); }).find("'n_points'"), std::string::npos);
}

TEST(GrcHb, CarranzaTorresCC02) {
    GrcHbInput in;
    in.radius_m = 3.82; in.p0_mpa = 30; in.g_mpa = 1000; in.nu = 0.25; in.sigma_ci_mpa = 30; in.mb = 1.7; in.s = 3.9e-3;
    const double pi = 5;
    EXPECT_NEAR(grc_hb(in).p_crit_mpa, 15.78, 0.01);
    EXPECT_NEAR(grc_hb_plastic_radius(in, pi) / 3.82, 1.623, 0.0005);
    EXPECT_NEAR(grc_hb_displacement(in, pi), 0.0835, 0.0001);
    // Pi_cr = 0.3108 en las unidades normalizadas
    EXPECT_NEAR((grc_hb(in).p_crit_mpa / (1.7 * 30) + 3.9e-3 / (1.7 * 1.7)), 0.3108, 0.0001);
    const auto r = grc_hb(in);
    EXPECT_EQ(r.info.method_id, "GRC-HB-Carranza-Torres-Fairhurst-2000");
    for (size_t i = 1; i < r.curve.size(); ++i) EXPECT_GE(r.curve[i].u_m, r.curve[i - 1].u_m - 1e-12);
}

TEST(GrcHb, ElasticoYErrores) {
    GrcHbInput in;
    in.radius_m = 3; in.p0_mpa = 1; in.g_mpa = 5000; in.nu = 0.25; in.sigma_ci_mpa = 100; in.mb = 5; in.s = 0.1;
    const auto r = grc_hb(in);
    EXPECT_DOUBLE_EQ(r.rp_unsupported_m, 3.0);
    EXPECT_NEAR(r.u_max_m, 3.0 / 10000, 1e-12);
    in.mb = 0;
    EXPECT_NE(error_of([&] { grc_hb(in); }).find("'mb'"), std::string::npos);
}

TEST(Hb1982, RS2Problema3) {
    Hb1982Input in;
    in.p0_mpa = 30; in.radius_m = 1; in.sigma_c_mpa = 100; in.m = 2.515; in.s = 0.003865; in.mr = 0.5; in.sr = 1e-5;
    EXPECT_NEAR(hb1982_plastic_radius(in), 2.168, 0.001);
    const auto s = hb1982_stress(in, 5);
    EXPECT_NEAR(s.sigma_r, 25.8, 0.1);
    EXPECT_NEAR(s.sigma_theta, 34.2, 0.1);
    EXPECT_NEAR(hb1982_stress(in, 1).sigma_r, 0, 1e-9);
    EXPECT_EQ(s.info.method_id, "HB-1982-brittle");
    in.m = -1;
    EXPECT_NE(error_of([&] { hb1982_plastic_radius(in); }).find("'m'"), std::string::npos);
}

TEST(Reed, RS2Problema30) {  // ro = 4 y q = 100: la Tabla 30.1 del manual trae errata (ro 2, q 30), FORMULAS §14
    ReedInput in;
    in.q_mpa = 100; in.radius_m = 4; in.c_peak_mpa = 30; in.c_res_mpa = 5; in.phi_deg = 30; in.pi_mpa = 0;
    EXPECT_NEAR(reed_plastic_radius(in), 7.77, 0.01);
    EXPECT_NEAR(reed_stress(in, 4).sigma_theta, 17.3, 0.1);
    EXPECT_NEAR(reed_stress(in, 4).sigma_r, 0, 1e-9);
    EXPECT_EQ(reed_stress(in, 4).info.method_id, "Reed-1986");
    EXPECT_NEAR(reed_stress(in, 14).sigma_r, 76.6, 0.1);
    EXPECT_NEAR(reed_stress(in, 14).sigma_theta, 123.4, 0.1);
    in.q_mpa = 30; in.radius_m = 2;  // con los datos erróneos no plastifica
    EXPECT_DOUBLE_EQ(reed_plastic_radius(in), 2.0);
    EXPECT_NEAR(reed_stress(in, 2).sigma_theta, 60, 1e-9);
    in.phi_deg = 0;
    EXPECT_NE(error_of([&] { reed_plastic_radius(in); }).find("'phi_deg'"), std::string::npos);
}

TEST(Reed, SinCohesionResidualNiPresion) {
    ReedInput in;
    in.q_mpa = 100; in.radius_m = 4; in.c_peak_mpa = 30; in.c_res_mpa = 0; in.phi_deg = 30; in.pi_mpa = 0;
    const auto e = error_of([&] { reed_plastic_radius(in); });
    EXPECT_NE(e.find("'c_res_mpa'"), std::string::npos);
    EXPECT_EQ(e.find("30"), std::string::npos);
    in.pi_mpa = 1;  // con presión interna sí se resuelve
    EXPECT_TRUE(std::isfinite(reed_plastic_radius(in)));
}
