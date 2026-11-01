#include <gtest/gtest.h>

#include <limits>
#include <stdexcept>

#include "rockmasspy/hoek_brown.hpp"

using namespace rockmasspy;

// HB-1 y HB-2: Hoek, Carranza-Torres y Corkum (2002), sección 7. El paper no publica γ: se usa 0.027 MN/m³
// (con ese valor se reproduce lo publicado; ver VALIDACION_Y_TAJO_ABIERTO.md §A.1).
TEST(HoekBrown, HB1Tunnel) {
    auto p = hb_params(45, 10, 0, HbEdition::HB2002);
    EXPECT_NEAR(p.mb, 1.40256, 5e-6); EXPECT_NEAR(p.s, 2.21808e-3, 5e-9); EXPECT_NEAR(p.a, 0.508086, 5e-7);
    double scm = hb_global_strength(50, p);                       EXPECT_NEAR(scm, 7.8098, 5e-5);
    double s3 = hb_sigma3max(scm, 0.027, 100, HbApplication::Tunnel);
    auto mc = hb_mohr_coulomb(50, p, s3);
    EXPECT_NEAR(mc.phi_deg, 47.16, 0.05); EXPECT_NEAR(mc.cohesion_mpa, 0.58, 0.005);
}
TEST(HoekBrown, HB2Slope) {
    auto p = hb_params(45, 10, 1, HbEdition::HB2002);
    double s3 = hb_sigma3max(hb_global_strength(50, p), 0.027, 100, HbApplication::Slope);
    auto mc = hb_mohr_coulomb(50, p, s3);
    EXPECT_NEAR(mc.phi_deg, 27.61, 0.05); EXPECT_NEAR(mc.cohesion_mpa, 0.35, 0.005);
}
TEST(HoekBrown, PracticalRockEngineeringCases) {   // HB-4 a HB-7; tolerancia = media unidad del último dígito publicado
    auto b = hb_params(75, 16.3, 0); EXPECT_NEAR(b.mb, 6.675, 5e-4); EXPECT_NEAR(b.s, 0.062, 5e-4); EXPECT_NEAR(b.a, 0.501, 5e-4);
    EXPECT_NEAR(hb_params(75, 28, 0).mb, 11.46, 1e-2);   // publicado truncado: 11.4656
    auto n = hb_params(65, 15, 0); EXPECT_NEAR(n.mb, 4.3, 0.05); EXPECT_NEAR(n.s, 0.02, 5e-3); EXPECT_NEAR(n.a, 0.5, 0.05);
    auto at = hb_params(20, 9.6, 0); EXPECT_NEAR(at.mb, 0.55, 5e-3); EXPECT_NEAR(at.s, 1e-4, 5e-5);
}
TEST(HoekBrown, DerivedStrengths) {
    auto p = hb_params(45, 10, 0, HbEdition::HB2002);
    EXPECT_NEAR(hb_ucs(50, p), 2.24130, 5e-5); EXPECT_NEAR(hb_tensile(50, p), -0.07907, 5e-5);
    EXPECT_NEAR(hb_sigma1(0.0, 50, p), hb_ucs(50, p), 1e-12);
    EXPECT_THROW(hb_sigma1(-1.0, 50, p), std::invalid_argument);
}
TEST(HoekBrown, Edition2018WarnsOnD) {
    EXPECT_EQ(hb_params(45, 10, 0.5).warnings.size(), 1u); EXPECT_EQ(hb_params(45, 10, 0).warnings.size(), 0u);
    EXPECT_EQ(hb_params(45, 10, 0.5, HbEdition::HB2002).warnings.size(), 0u);
    EXPECT_EQ(hb_params(45, 10, 0).info.method_id, "HB-2018");
}
TEST(HoekBrown, UnitWeightInKnThrows) { EXPECT_THROW(hb_sigma3max(7.8, 27.0, 100, HbApplication::Tunnel), std::invalid_argument); }
TEST(HoekBrown, UnitWeightMessage) {
    try {
        hb_sigma3max(7.8, 27.0, 100, HbApplication::Tunnel);
        FAIL();
    } catch (const std::invalid_argument& e) {
        EXPECT_NE(std::string(e.what()).find("unit_weight_mn_m3 must be in MN/m3 (e.g. 0.027), got 27"), std::string::npos);
    }
}
TEST(HoekBrown, Validation) {
    const double nan = std::numeric_limits<double>::quiet_NaN();
    EXPECT_THROW(hb_params(0, 10, 0), std::invalid_argument);
    EXPECT_THROW(hb_params(101, 10, 0), std::invalid_argument);
    EXPECT_THROW(hb_params(nan, 10, 0), std::invalid_argument);
    EXPECT_THROW(hb_params(45, 0, 0), std::invalid_argument);
    EXPECT_THROW(hb_params(45, 10, 1.1), std::invalid_argument);
    auto p = hb_params(45, 10, 0);
    EXPECT_THROW(hb_ucs(0, p), std::invalid_argument);
    EXPECT_THROW(hb_sigma1(nan, 50, p), std::invalid_argument);
    EXPECT_THROW(hb_sigma3max(0, 0.027, 100, HbApplication::Slope), std::invalid_argument);
    EXPECT_THROW(hb_sigma3max(7.8, 0, 100, HbApplication::Slope), std::invalid_argument);
    EXPECT_THROW(hb_sigma3max(7.8, 0.027, 0, HbApplication::Slope), std::invalid_argument);
    EXPECT_THROW(hb_mohr_coulomb(50, p, 0), std::invalid_argument);
    EXPECT_THROW(erm_hoek_diederichs_generalized(45, 0, 0), std::invalid_argument);
    EXPECT_THROW(em_hoek2002(45, 2, 50), std::invalid_argument);
}
// Módulos: valores calculados por nosotros con la fórmula publicada (no hay ejemplo resuelto).
TEST(HoekBrown, Moduli) {
    EXPECT_NEAR(erm_hoek_diederichs_simplified(45, 0).value, 6138.31, 0.01);
    EXPECT_NEAR(erm_hoek_diederichs_simplified(45, 1).value, 334.643, 0.001);
    EXPECT_NEAR(erm_hoek_diederichs_generalized(45, 0, 20000).value, 4473.00, 0.01);
    EXPECT_NEAR(em_hoek2002(45, 0, 50).value, 5.30255, 1e-5); EXPECT_NEAR(em_hoek2002(45, 0, 150).value, 7.49894, 1e-5);
    EXPECT_EQ(em_hoek2002(45, 0, 50).info.verification, Verification::Secondary);
    EXPECT_EQ(em_hoek2002(45, 0, 50).unit, "GPa");
    EXPECT_EQ(erm_hoek_diederichs_simplified(45, 0).unit, "MPa");
    EXPECT_EQ(erm_hoek_diederichs_simplified(45, 0).info.method_id, "HD-2006");
}
