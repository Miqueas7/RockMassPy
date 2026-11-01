#include <gtest/gtest.h>

#include <cmath>

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
    EXPECT_DOUBLE_EQ(wall_q(20, 5, 10, false), 100);  EXPECT_DOUBLE_EQ(wall_q(5, 5, 10, false), 12.5);
    EXPECT_DOUBLE_EQ(wall_q(0.5, 5, 10, false), 0.5); EXPECT_DOUBLE_EQ(wall_q(0.5, 5, 10, false, QEdition::NGI2015), 1.25);
    EXPECT_DOUBLE_EQ(wall_q(20, 12, 10, false), 20);  EXPECT_DOUBLE_EQ(wall_q(5, 5, 10, true), 5);
    EXPECT_DOUBLE_EQ(wall_q(10, 5, 10, false), 25);   // límite: 2.5·Q, no 5·Q
    EXPECT_THROW(wall_q(0, 5, 10, false), std::invalid_argument);
}
TEST(QSystem, EsrRuleLowQ) {
    auto d = equivalent_dimension(10, 1.6, 0.05, 'C'); EXPECT_DOUBLE_EQ(d.esr_used, 1.0); EXPECT_DOUBLE_EQ(d.de_m, 10); EXPECT_EQ(d.warnings.size(), 1u);
    EXPECT_DOUBLE_EQ(equivalent_dimension(10, 3.0, 0.05, 'A').esr_used, 3.0);
    EXPECT_THROW(equivalent_dimension(10, 1.6, 1, 'H'), std::invalid_argument);
}
