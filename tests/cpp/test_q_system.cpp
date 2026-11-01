#include <gtest/gtest.h>

#include <cmath>
#include <functional>
#include <string>
#include <utility>
#include <vector>

#include "error_of.hpp"
#include "rockmasspy/q_system.hpp"

using namespace rockmasspy;

// Caso publicado: Hoek, PRE cap. 3, cámara de chancado (RQD 90, Jn 4, Jr 3, Ja 1, Jw 1, SRF 15). Q = 4.5.
TEST(QSystem, HoekCrusherChamber) {
    auto r = q_value({90, 4, 3, 1, 1, 15});
    EXPECT_NEAR(r.q, 4.5, 5e-3); EXPECT_NEAR(r.q_base, 67.5, 1e-9); EXPECT_EQ(r.rock_class, "C Fair");
    EXPECT_EQ(r.info.method_id, "Q-NGI-2025");
    EXPECT_NEAR(equivalent_dimension(15, 1.6, r.q, 'C').de_m, 9.375, 1e-9);   // publicado 9.4
}
TEST(QSystem, ErrataNotUsed) { EXPECT_NEAR(q_value({50, 4, 3, 1, 1, 15}).q, 2.5, 1e-9); }  // Hoek imprime 2.9
TEST(QSystem, LowRqdRaisedTo10) { auto r = q_value({5, 4, 1, 1, 1, 1}); EXPECT_DOUBLE_EQ(r.rqd_used, 10); EXPECT_DOUBLE_EQ(r.q, 2.5); }
TEST(QSystem, ClassBoundaryIsConservative) {
    EXPECT_EQ(q_value({100, 2.5, 1, 4, 1, 1}).rock_class, "C Fair");    // Q = 10 exacto
    EXPECT_EQ(q_value({100, 0.5, 4, 0.75, 1, 1}, QEdition::NGI2015).rock_class, "A Exceptionally good"); // Q ~ 1067
    EXPECT_EQ(q_value({100, 0.5, 4, 0.75, 1, 1}).rock_class, "A Very good");
    EXPECT_EQ(q_value({100, 0.5, 4, 0.75, 1, 1}, QEdition::NGI2015).info.method_id, "Q-NGI-2015");
}
TEST(QSystem, IntersectionJnAndOutOfRangeWarn) {
    EXPECT_NO_THROW(q_value({90, 45, 1, 1, 1, 1}));
    EXPECT_EQ(q_value({10, 20, 0.5, 20, 0.05, 400}).warnings.size(), 1u);  // Q ~ 1.6e-6
    EXPECT_EQ(q_value({10, 20, 0.5, 20, 0.05, 400}).warnings[0], "Q outside 0.001-1000");
    EXPECT_THROW(q_value({90, 4, 3, 1, 1.2, 1}), std::invalid_argument);   // Jw > 1
    EXPECT_THROW(q_value({std::nan(""), 4, 3, 1, 1, 1}), std::invalid_argument);
}
TEST(QSystem, RqdFractionWarns) {
    auto r = q_value({0.7, 4, 3, 1, 1, 1});
    ASSERT_GE(r.warnings.size(), 1u);
    EXPECT_EQ(r.warnings[0], "rqd_pct <= 1: RQD is a percentage (0-100); check it is not a fraction");
}
TEST(QSystem, WallQ) {
    EXPECT_DOUBLE_EQ(wall_q(20, 5, 10, false).q_wall, 100);  EXPECT_DOUBLE_EQ(wall_q(5, 5, 10, false).q_wall, 12.5);
    EXPECT_DOUBLE_EQ(wall_q(0.5, 5, 10, false).q_wall, 0.5); EXPECT_DOUBLE_EQ(wall_q(0.5, 5, 10, false, QEdition::NGI2015).q_wall, 1.25);
    EXPECT_DOUBLE_EQ(wall_q(20, 12, 10, false).q_wall, 20);  EXPECT_DOUBLE_EQ(wall_q(5, 5, 10, true).q_wall, 5);
    EXPECT_DOUBLE_EQ(wall_q(10, 5, 10, false).q_wall, 25);   // límite: 2.5·Q, no 5·Q
    EXPECT_THROW(wall_q(0, 5, 10, false), std::invalid_argument);
}
TEST(QSystem, WallQFactorAndInfo) {
    EXPECT_DOUBLE_EQ(wall_q(20, 5, 10, false).factor, 5.0);
    EXPECT_DOUBLE_EQ(wall_q(5, 5, 10, false).factor, 2.5);
    EXPECT_DOUBLE_EQ(wall_q(5, 5, 10, true).factor, 1.0);
    EXPECT_EQ(wall_q(5, 5, 10, false).info.method_id, "Q-NGI-2025");
    EXPECT_EQ(wall_q(5, 5, 10, false, QEdition::NGI2015).info.method_id, "Q-NGI-2015");
}
TEST(QSystem, EquivalentDimensionInfo) {
    auto d25 = equivalent_dimension(15, 1.6, 4.5, 'C');
    EXPECT_EQ(d25.info.method_id, "Q-NGI-2025"); EXPECT_EQ(d25.info.verification, Verification::Primary);
    EXPECT_EQ(d25.info.source, "NGI (2025) Using the Q-system, Table 4-1");
    auto d15 = equivalent_dimension(15, 1.6, 4.5, 'C', QEdition::NGI2015);
    EXPECT_EQ(d15.info.method_id, "Q-NGI-2015");
    EXPECT_EQ(d15.info.source, "NGI (2015, rev. 2022) Using the Q-system, Table 7");
}
TEST(QSystem, EsrRuleLowQ) {
    auto d = equivalent_dimension(10, 1.6, 0.05, 'C'); EXPECT_DOUBLE_EQ(d.esr_used, 1.0); EXPECT_DOUBLE_EQ(d.de_m, 10); EXPECT_EQ(d.warnings.size(), 1u);
    EXPECT_DOUBLE_EQ(equivalent_dimension(10, 3.0, 0.05, 'A').esr_used, 3.0);
    EXPECT_THROW(equivalent_dimension(10, 1.6, 1, 'H'), std::invalid_argument);
    EXPECT_DOUBLE_EQ(equivalent_dimension(10, 1.6, 0.05, 'c').esr_used, 1.0);   // minúscula = 'C'
}
TEST(QSystem, UnsetFieldsThrowWithTheirName) {
    EXPECT_THROW(q_value(QInput{}), std::invalid_argument);
    const double nan = std::nan("");
    const std::vector<std::pair<std::string, std::function<void(QInput&)>>> cases = {
        {"rqd_pct", [=](QInput& in) { in.rqd_pct = nan; }}, {"jn", [=](QInput& in) { in.jn = nan; }},
        {"jr", [=](QInput& in) { in.jr = nan; }},           {"ja", [=](QInput& in) { in.ja = nan; }},
        {"jw", [=](QInput& in) { in.jw = nan; }},           {"srf", [=](QInput& in) { in.srf = nan; }},
    };
    for (const auto& [name, unset] : cases) {
        QInput in{90, 4, 3, 1, 1, 15}; unset(in);
        EXPECT_NE(error_of([&] { q_value(in); }).find("'" + name + "'"), std::string::npos) << name;
    }
}
