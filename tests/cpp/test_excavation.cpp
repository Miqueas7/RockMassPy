#include <gtest/gtest.h>

#include <algorithm>
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

TEST(Squeezing, FueraDelAjusteAcotado) {
    const auto s = hoek_marinos(1, 4, 3.6, 2);  // pi/p0 = 0.9: la ecuación 8 daría ε < 0
    EXPECT_EQ(s.strain_pct, 0.0);
    EXPECT_EQ(s.wall_displacement_m, 0.0);
    EXPECT_EQ(s.squeezing_class, 'A');
    EXPECT_FALSE(s.in_fit_range);
    EXPECT_GE(s.plastic_radius_m, 2.0);
    EXPECT_EQ(hoek_marinos(12, 4, 0, 2).plastic_radius_m, 2.0);  // σcm/p0 = 3: la ecuación 9 daría rp < R
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

// ---------------------------------------------------------------- LDP, SCC e interacción (Tarea 3)

TEST(Ldp, ValoresDeControl) {  // recálculo de FORMULAS §7
    const double xs[] = {-1, 0, 1};
    const double vd1[] = {0.1055, 0.2869, 0.8409}, vd25[] = {0.0843, 0.2291, 0.5769}, ch[] = {0.1199, 0.3078, 0.5624};
    for (int i = 0; i < 3; ++i) {
        EXPECT_NEAR(ldp_ratio(Ldp::VD2009, xs[i], 1, 0.3), vd1[i], 0.0001);
        EXPECT_NEAR(ldp_ratio(Ldp::VD2009, xs[i], 2.5, 0.3), vd25[i], 0.0001);
        EXPECT_NEAR(ldp_ratio(Ldp::CHERN1998, xs[i], 2.5, 0.3), ch[i], 0.0001);
    }
    EXPECT_NEAR(ldp_ratio(Ldp::PANET1995, 0, 1, 0.3), 0.2500, 0.0001);
    EXPECT_NEAR(ldp_ratio(Ldp::PANET1995, 1, 1, 0.3), 0.8622, 0.0001);
    EXPECT_NEAR(ldp_ratio(Ldp::PANET1995, 2, 1, 0.3), 0.9442, 0.0001);
    EXPECT_NEAR(ldp_ratio(Ldp::VD2009, 0, 2, 0.3), 0.247, 0.0005);  // KL08 p. 9: «un cuarto»
    // Unlu-Gercek: u0/umax = 0.22ν + 0.19 en el frente, 0 lejos delante y 1 lejos detrás
    EXPECT_NEAR(ldp_ratio(Ldp::UNLU_GERCEK2003, 0, 1, 0.3), 0.256, 1e-12);
    EXPECT_NEAR(ldp_ratio(Ldp::UNLU_GERCEK2003, -60, 1, 0.3), 0.0, 1e-9);
    EXPECT_NEAR(ldp_ratio(Ldp::UNLU_GERCEK2003, 1e6, 1, 0.3), 1.0, 1e-9);
    EXPECT_EQ(ldp_info(Ldp::PANET1995).method_id, "LDP-Panet-1995");
    EXPECT_EQ(ldp_info(Ldp::UNLU_GERCEK2003).method_id, "LDP-Unlu-Gercek-2003");
    EXPECT_EQ(ldp_info(Ldp::CHERN1998).method_id, "LDP-Chern-1998");
    EXPECT_EQ(ldp_info(Ldp::VD2009).method_id, "LDP-Vlachopoulos-Diederichs-2009");
}

TEST(Ldp, InversaYErrores) {
    for (double rs : {1.0, 2.5})
        for (double x : {-1.0, -0.2, 0.0, 0.7, 3.0})
            EXPECT_NEAR(ldp_distance(Ldp::VD2009, ldp_ratio(Ldp::VD2009, x, rs, 0.3), rs, 0.3), x, 1e-9);
    EXPECT_NE(error_of([] { ldp_distance(Ldp::CHERN1998, 0.5, 2, 0.3); }).find("'ldp'"), std::string::npos);
    const auto e = error_of([] { ldp_distance(Ldp::VD2009, 1.5, 2, 0.3); });
    EXPECT_NE(e.find("'ratio'"), std::string::npos);
    EXPECT_EQ(e.find("1.5"), std::string::npos);
    EXPECT_NE(error_of([] { ldp_ratio(Ldp::PANET1995, -1, 1, 0.3); }).find("'x_over_r'"), std::string::npos);
    EXPECT_NE(error_of([] { ldp_ratio(Ldp::VD2009, 0, 0.5, 0.3); }).find("'rp_over_r'"), std::string::npos);
}

namespace {
const char* kD4 = "LDP not valid for Rp > 2R; use VD2009";
const char* kD6 = "support does not intersect the ground reaction curve";
bool has(const std::vector<std::string>& v, const char* s) { return std::find(v.begin(), v.end(), s) != v.end(); }
// RST Ejemplo 1: perno de 34 mm a 1 × 1 m instalado a 3 m del frente (X* = 0.5)
Interaction rst1_bolt(Ldp ldp, Combination mode = Combination::ROCSUPPORT3,
                      std::vector<SupportElement> els = {support_from_eps("B34", 0.354, 0.002)}) {
    const auto in = rst1();
    const double umax = grc_mc_displacement(in, 0), rs = grc_mc_plastic_radius(in, 0) / in.radius_m;
    return interaction_mc(in, els, ldp_ratio(ldp, 3.0 / 6.0, rs, in.nu) * umax, mode, ldp);
}
}  // namespace

TEST(Interaccion, RstEjemplo1) {  // FORMULAS §9
    const auto r = rst1_bolt(Ldp::CHERN1998);
    ASSERT_TRUE(r.found);
    ASSERT_TRUE(r.fs.has_value());
    EXPECT_NEAR(*r.fs, 1.838, 0.001);
    EXPECT_NEAR(r.p_eq_mpa, 0.1926, 0.0001);
    EXPECT_NEAR(r.rp_eq_m, 10.02, 0.01);
    EXPECT_NEAR(r.strain_eq_pct, 0.989, 0.001);
    EXPECT_TRUE(r.elastic);
    EXPECT_EQ(r.fs_by_element.size(), 1u);
    EXPECT_EQ(r.info.method_id, "Support-interaction");
    EXPECT_EQ(r.info.verification, Verification::Secondary);  // modo RocSupport
    EXPECT_TRUE(r.warnings.empty());
    EXPECT_NEAR(*rst1_bolt(Ldp::VD2009).fs, 1.92, 0.01);
    EXPECT_NEAR(*rst1_bolt(Ldp::PANET1995).fs, 5.24, 0.01);
}

TEST(Interaccion, Combinacion) {  // FORMULAS §8.5: perno de 34 mm + shotcrete de 50 mm a 28 días, D = 12
    const std::vector<SupportElement> els = {support_from_eps("B34", 0.354, 0.002), support_from_eps("SC50", 0.325, 0.001)};
    const auto c3 = combine_supports(els, Combination::ROCSUPPORT3);
    ASSERT_EQ(c3.size(), 1u);
    EXPECT_NEAR(c3[0].psm_mpa, 0.679, 1e-9);
    EXPECT_NEAR(c3[0].psm_mpa / c3[0].stiffness_mpa, 0.0015, 1e-12);
    const auto c = combine_supports(els, Combination::ROCSUPPORT);
    EXPECT_NEAR(c[0].psm_mpa, 0.679, 1e-9);
    EXPECT_NEAR(c[0].psm_mpa / c[0].stiffness_mpa, 0.002, 1e-12);
    EXPECT_EQ(combine_supports(els, Combination::STIFFNESS).size(), 2u);

    const auto in = rst1();
    const double u_in = ldp_ratio(Ldp::CHERN1998, 0.5, grc_mc_plastic_radius(in, 0) / 6, 0.3) * grc_mc_displacement(in, 0);
    const auto r = interaction_mc(in, els, u_in, Combination::STIFFNESS);
    ASSERT_TRUE(r.found);
    ASSERT_EQ(r.fs_by_element.size(), 2u);
    EXPECT_EQ(r.info.verification, Verification::PrimaryLaterAuthors);
    double sum = 0, fs = 1e300;
    for (size_t i = 0; i < 2; ++i) {
        const double pi_ = els[i].stiffness_mpa * (r.u_eq_m - u_in) / 6;
        sum += pi_;
        EXPECT_NEAR(r.fs_by_element[i], els[i].psm_mpa / pi_, 1e-6 * r.fs_by_element[i]);
        fs = std::min(fs, els[i].psm_mpa / pi_);
    }
    EXPECT_NEAR(*r.fs, fs, 1e-12);
    EXPECT_NEAR(sum, r.p_eq_mpa, 1e-6 * r.p_eq_mpa);
    EXPECT_NEAR(grc_mc_displacement(in, r.p_eq_mpa), r.u_eq_m, 1e-12);
}

TEST(Interaccion, AnilloGruesoUBC) {  // FORMULAS §8.2 [V2]
    const double k = thick_ring_stiffness(30000, 0.25, 1.85, 0.15);
    EXPECT_NEAR(k, 2777.5, 0.5);
    GrcMcInput in;  // GRC elástica con G = 2 GPa (E = 5000, ν = 0.25), p0 = 20
    in.radius_m = 1.85; in.p0_mpa = 20; in.e_mpa = 5000; in.nu = 0.25; in.c_mpa = 100; in.phi_deg = 30;
    EXPECT_NEAR(grc_mc_displacement(in, 0) * 1000, 9.25, 1e-9);
    const auto r = interaction_mc(in, {{"lining", 50.0, k}}, 0.001, Combination::STIFFNESS);
    EXPECT_NEAR(r.u_eq_m * 1000, 5.869, 0.001);
    EXPECT_NEAR(r.p_eq_mpa, 7.310, 0.001);
    EXPECT_TRUE(r.elastic);
    EXPECT_NE(error_of([] { thick_ring_stiffness(30000, 0.25, 1.85, 2); }).find("'thickness_m'"), std::string::npos);
}

TEST(Interaccion, CruceMasAllaDelLimiteElastico) {  // D6: se prolonga la recta elástica
    const auto r = rst1_bolt(Ldp::CHERN1998, Combination::STIFFNESS, {{"weak", 0.1, 500.0}});
    ASSERT_TRUE(r.found);
    EXPECT_FALSE(r.elastic);
    ASSERT_TRUE(r.fs.has_value());
    // FS con la recta elástica prolongada (D6), recalculado aparte por bisección de 500·(u(p) − u_in)/R = p
    EXPECT_NEAR(*r.fs, 0.46355, 1e-5);
    EXPECT_NEAR(r.p_eq_mpa, 0.1, 1e-9);  // el equilibrio real cae en la meseta plástica
    EXPECT_NEAR(r.u_eq_m, grc_mc_displacement(rst1(), 0.1), 1e-9);
}

TEST(Interaccion, InstaladoDemasiadoTarde) {  // test_interaction_installed_too_late
    const auto in = rst1();
    const double umax = grc_mc_displacement(in, 0);
    for (double u_in : {umax, 2 * umax}) {
        const auto r = interaction_mc(in, {support_from_eps("B34", 0.354, 0.002)}, u_in, Combination::ROCSUPPORT3);
        EXPECT_FALSE(r.found);
        EXPECT_FALSE(r.fs.has_value());
        EXPECT_TRUE(r.fs_by_element.empty());
        EXPECT_TRUE(has(r.warnings, kD6));
    }
    // casi al final: sí hay cruce, con presión ínfima, y el FS es positivo y finito (antes salía negativo)
    for (double f : {1e-12, 1e-14}) {
        const auto r = interaction_mc(in, {support_from_eps("B34", 0.354, 0.002)}, umax * (1 - f),
                                      Combination::ROCSUPPORT3);
        ASSERT_TRUE(r.found);
        ASSERT_TRUE(r.fs.has_value());
        EXPECT_TRUE(std::isfinite(*r.fs));
        EXPECT_GT(*r.fs, 0.0);
        EXPECT_GT(r.fs_by_element[0], 0.0);
        EXPECT_TRUE(r.elastic);
    }
}

TEST(Interaccion, AvisoLdpD4) {  // Panet con rp/R = 3
    auto in = rst1();
    in.sigma_cm_override_mpa = 0.29343;
    const double rs = grc_mc_plastic_radius(in, 0) / 6;
    EXPECT_NEAR(rs, 3.0, 0.01);
    const double u_in = ldp_ratio(Ldp::PANET1995, 0.5, rs, 0.3) * grc_mc_displacement(in, 0);
    const std::vector<SupportElement> b = {support_from_eps("B34", 0.354, 0.002)};
    EXPECT_TRUE(has(interaction_mc(in, b, u_in, Combination::ROCSUPPORT3, Ldp::PANET1995).warnings, kD4));
    EXPECT_TRUE(has(interaction_mc(in, b, u_in, Combination::ROCSUPPORT3, Ldp::UNLU_GERCEK2003).warnings, kD4));
    EXPECT_FALSE(has(interaction_mc(in, b, u_in, Combination::ROCSUPPORT3, Ldp::VD2009).warnings, kD4));
    EXPECT_TRUE(interaction_mc(in, b, u_in, Combination::ROCSUPPORT3).warnings.empty());
}

TEST(Interaccion, HoekBrownYErrores) {
    GrcHbInput in;
    in.radius_m = 3.82; in.p0_mpa = 30; in.g_mpa = 1000; in.nu = 0.25; in.sigma_ci_mpa = 30; in.mb = 1.7; in.s = 3.9e-3;
    const auto r = interaction_hb(in, {{"lining", 100.0, 3000.0}}, 0.01, Combination::STIFFNESS);
    ASSERT_TRUE(r.found);
    EXPECT_TRUE(r.elastic);
    EXPECT_NEAR(grc_hb_displacement(in, r.p_eq_mpa), r.u_eq_m, 1e-12);
    EXPECT_NEAR(3000.0 * (r.u_eq_m - 0.01) / 3.82, r.p_eq_mpa, 1e-6 * r.p_eq_mpa);
    EXPECT_NEAR(r.rp_eq_m, grc_hb_plastic_radius(in, r.p_eq_mpa), 1e-12);
    EXPECT_NE(error_of([&] { interaction_hb(in, {}, 0, Combination::STIFFNESS); }).find("'elements'"), std::string::npos);
    EXPECT_NE(error_of([&] { interaction_hb(in, {{"x", 0.0, 1.0}}, 0, Combination::STIFFNESS); }).find("'psm_mpa'"),
              std::string::npos);
    EXPECT_NE(error_of([&] { interaction_hb(in, {{"x", 1.0, 1.0}}, -1, Combination::STIFFNESS); }).find("'u_install_m'"),
              std::string::npos);
    EXPECT_NE(error_of([] { support_from_eps("x", 1, 0); }).find("'eps_sm'"), std::string::npos);
    EXPECT_EQ(scc_info().method_id, "SCC-elastic-perfectly-plastic");
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
