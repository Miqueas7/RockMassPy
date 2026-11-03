#include <gtest/gtest.h>

#include <cmath>
#include <functional>
#include <limits>
#include <string>

#include "error_of.hpp"
#include "rockmasspy/toppling.hpp"

using namespace rockmasspy;

namespace {
const double kNan = std::numeric_limits<double>::quiet_NaN();
const double kInf = std::numeric_limits<double>::infinity();
const double kPi = 3.14159265358979323846;

// Goodman y Bray (1976), ejemplo 1: 16 bloques, cresta en el 10, a1 = a2 = 5 m, b = 1 m
TopplingInput ex1(double phi = 38.15, double support = 0.5) {
    TopplingInput in;
    in.heights_m = goodman_bray_heights(16, 10, 5, 5, 1);
    in.block_width_m = 10; in.base_dip_deg = 30; in.a1_m = 5; in.a2_m = 5; in.crest_block = 10;
    in.unit_weight = 25; in.friction_deg = phi; in.support_force = support;
    return in;
}
double fs(double phi, double support) { return toppling_fs(ex1(phi, support)).factor_of_safety; }
bool has(const std::vector<std::string>& v, const std::string& s) {
    for (const auto& x : v) if (x.find(s) != std::string::npos) return true;
    return false;
}
// P_n (n = 1..15) = fuerza que el bloque n+1 transmite al bloque n = p_lower del bloque n+1 (índice n)
double P(const TopplingForces& f, int n) { return f.blocks[n].p_lower; }
}  // namespace

TEST(Toppling, HeightsOfExample) {
    const auto y = goodman_bray_heights(16, 10, 5, 5, 1);
    const double expect[16] = {4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 34, 28, 22, 16, 10, 4};
    ASSERT_EQ(y.size(), 16u);
    for (int i = 0; i < 16; ++i) EXPECT_DOUBLE_EQ(y[i], expect[i]);
    EXPECT_FALSE(error_of([] { goodman_bray_heights(16, 10, 5, 5, 5); }).empty());   // y1 = 0
    EXPECT_FALSE(error_of([] { goodman_bray_heights(16, 10, 5, 20, 1); }).empty());  // cae bajo cero
}

TEST(Toppling, Table1) {
    const auto f = toppling_forces(ex1(), 0.7855);
    for (int n : {15, 14, 13}) {
        EXPECT_EQ(f.blocks[n].state, TopplingState::Stable);  // el bloque n+1 produce P_n
        EXPECT_EQ(P(f, n), 0.0);
    }
    const double exp_p[] = {292.5, 825.7, 1556.0, 2826.7, 3922.2, 4594.8, 4837.0, 4637.5, 3978.1, 2825.6};
    for (int i = 0; i < 10; ++i) {  // P12 .. P3
        EXPECT_NEAR(P(f, 12 - i), exp_p[i], 0.2) << "P" << 12 - i;
        EXPECT_EQ(f.blocks[12 - i].state, TopplingState::Toppling);
    }
    EXPECT_NEAR(P(f, 2), 1413.5, 0.2);
    EXPECT_NEAR(P(f, 1), 472.2, 0.2);
    EXPECT_EQ(f.blocks[2].state, TopplingState::Sliding);
    EXPECT_EQ(f.blocks[1].state, TopplingState::Sliding);
    EXPECT_NEAR(f.blocks[12].normal, 4533.4, 0.2);
    EXPECT_NEAR(f.blocks[12].shear, 2457.5, 0.2);
    EXPECT_NEAR(f.support_toppling, -1486.8, 0.2);
    EXPECT_NEAR(f.support_sliding, 0.47, 0.01);
    auto in = ex1(); in.support_force = 0.469;
    const auto g = toppling_forces(in, 0.7855);
    EXPECT_NEAR(g.blocks[0].normal, 1237.1, 0.2);
    EXPECT_NEAR(g.blocks[0].shear, 971.8, 0.2);
}

TEST(Toppling, Table2) {
    auto in = ex1(); in.support_force = 2013;
    const auto f = toppling_forces(in, 0.650);
    EXPECT_NEAR(P(f, 1), 4260.3, 0.2);
    EXPECT_NEAR(f.support_sliding, 2012.9, 0.2);
    EXPECT_NEAR(f.blocks[0].normal, 4641.7, 0.3);
    EXPECT_NEAR(f.blocks[0].shear, 3017.1, 0.3);
}

TEST(Toppling, VO1) {
    EXPECT_NEAR(fs(38.15, 0.5), 1.000, 1e-3);
    EXPECT_NEAR(fs(33.02, 2013), 1.000, 1e-3);
    EXPECT_NEAR(fs(38.66, 0.5), 1.018, 1e-3);
    EXPECT_NEAR(fs(38.66, 2013), 1.231, 1e-3);
    const auto r = toppling_fs(ex1(38.66, 2013));
    EXPECT_EQ(r.info.verification, Verification::Primary);
    EXPECT_EQ(r.info.method_id, "Toppling-GoodmanBray1976");
    EXPECT_NEAR(r.friction_required, std::tan(38.66 * kPi / 180) / r.factor_of_safety, 1e-12);
    EXPECT_FALSE(r.fs_bounded);
    EXPECT_FALSE(r.capped);
    EXPECT_NEAR(r.forces.support_required, 2013, 1e-3);
}

TEST(Toppling, ZeroForceTopBlockIsNotStable) {
    // y = dx / tan(alpha): Pt = 0 salvo ruido; el bloque no es estable y su P es 0
    TopplingInput in;
    in.heights_m = {20.0, 10.0 / std::tan(30.0 * kPi / 180.0)};
    in.block_width_m = 10; in.base_dip_deg = 30; in.a1_m = 0; in.a2_m = 0; in.crest_block = 1;
    in.unit_weight = 25; in.friction_deg = 40;
    const auto f = toppling_forces(in, 0.7);
    EXPECT_EQ(f.blocks[1].state, TopplingState::Toppling);
    EXPECT_NEAR(f.blocks[1].p_lower, 0.0, 1e-9);
}

TEST(Toppling, Bounds) {
    auto r = toppling_fs(ex1(60, 1e9));
    EXPECT_EQ(r.factor_of_safety, 100.0);
    EXPECT_FALSE(r.fs_bounded);
    EXPECT_TRUE(r.capped);
    EXPECT_TRUE(has(r.notes, "toppling FS above 100"));
    EXPECT_TRUE(r.warnings.empty());  // sin (8)-(9) en el mu artificial
    auto in = ex1(20, 0.0);
    in.base_dip_deg = 60;  // no se sostiene con mu < 1
    r = toppling_fs(in);
    EXPECT_TRUE(r.fs_bounded);
    EXPECT_FALSE(r.capped);
    EXPECT_LT(r.factor_of_safety, std::tan(20 * kPi / 180) + 1e-6);
    EXPECT_TRUE(has(r.warnings, "support is insufficient for any friction coefficient below 1; FS is an upper bound"));
}

TEST(Toppling, MonotoneInMuAndSupport) {
    double prev = 1e300;
    for (double mu = 0.3; mu < 0.99; mu += 0.05) {
        const double s = toppling_forces(ex1(), mu).support_required;
        EXPECT_LE(s, prev + 1e-9);
        prev = s;
    }
    prev = 0;
    for (double t : {0.0, 1.0, 100.0, 1000.0, 2013.0, 4000.0}) {
        const double v = fs(38.66, t);
        EXPECT_GE(v, prev - 1e-9);
        prev = v;
    }
}

TEST(Toppling, WarningsDoNotEchoValues) {
    auto in = ex1(20, 0.0);
    in.base_dip_deg = 60;
    const auto r = toppling_fs(in);
    ASSERT_FALSE(r.warnings.empty());
    std::vector<std::string> vals;
    for (double v : {in.block_width_m, in.base_dip_deg, in.a1_m, in.a2_m, in.unit_weight, in.friction_deg,
                     r.friction_required, r.factor_of_safety})
        vals.push_back(std::to_string(static_cast<int>(v)) + ".");
    for (double v : in.heights_m) vals.push_back(std::to_string(v).substr(0, 5));
    for (const auto& w : r.warnings) {
        EXPECT_EQ(w.find("0.36"), std::string::npos);
        for (const auto& v : vals) EXPECT_EQ(w.find(v), std::string::npos) << v;
    }
}

TEST(Toppling, TieOfLabelDoesNotFlipWarning) {
    // T* = soporte exacto en el que el bloque 4 empata Pt = Ps; el aviso (8)-(9) no depende del signo del ruido
    const double T = 771.5239216;
    const auto a = toppling_fs(ex1(38.66, T - 1e-6)), b = toppling_fs(ex1(38.66, T + 1e-6));
    EXPECT_EQ(a.warnings, b.warnings);
}

TEST(Toppling, TopBlockNoiseKeepsToppling) {
    for (double s : {1 - 1e-12, 1.0, 1 + 1e-12}) {
        TopplingInput in;
        in.heights_m = {20.0 * s, 10.0 / std::tan(30.0 * kPi / 180.0) * s};
        in.block_width_m = 10; in.base_dip_deg = 30; in.a1_m = 0; in.a2_m = 0; in.crest_block = 1;
        in.unit_weight = 25; in.friction_deg = 40;
        const auto f = toppling_forces(in, 0.7);
        EXPECT_EQ(f.blocks[1].state, TopplingState::Toppling) << s;
        EXPECT_NEAR(f.blocks[1].p_lower, 0.0, 1e-6) << s;
    }
}

TEST(Toppling, SupportDirection) {
    for (double d : {60.0, 70.0}) {  // sin soporte la dirección no importa
        auto in = ex1(38.66, 0.0);
        in.support_angle_deg = d;
        EXPECT_NO_THROW(toppling_fs(in));
    }
    auto in = ex1(38.66, 100.0);
    in.support_angle_deg = -80;  // alpha + delta = -50: fuera de (-45, 90) con soporte
    EXPECT_NE(error_of([&] { toppling_fs(in); }).find("support_angle_deg"), std::string::npos);
    for (double mu : {0.3, 0.8, 0.85}) EXPECT_FALSE(error_of([&] { toppling_forces(in, mu); }).empty());
    in.support_angle_deg = -74;  // alpha + delta = -44: dentro; ningún mu lanza en la búsqueda
    EXPECT_NO_THROW(toppling_fs(in));
    in.support_angle_deg = 59;  // alpha + delta = 89
    EXPECT_NO_THROW(toppling_fs(in));
    in.support_angle_deg = 60;  // alpha + delta = 90
    EXPECT_FALSE(error_of([&] { toppling_fs(in); }).empty());
}

TEST(Toppling, RejectsBadInput) {
    const auto bad = [](const std::function<void(TopplingInput&)>& m) {
        auto in = ex1();
        m(in);
        return error_of([&] { toppling_fs(in); });
    };
    EXPECT_FALSE(bad([](auto& i) { i.heights_m.clear(); }).empty());
    EXPECT_FALSE(bad([](auto& i) { i.heights_m[3] = 0; }).empty());
    EXPECT_FALSE(bad([](auto& i) { i.crest_block = 0; }).empty());
    EXPECT_FALSE(bad([](auto& i) { i.crest_block = 17; }).empty());
    EXPECT_FALSE(bad([](auto& i) { i.base_dip_deg = 0; }).empty());
    EXPECT_FALSE(bad([](auto& i) { i.base_dip_deg = 90; }).empty());
    EXPECT_FALSE(bad([](auto& i) { i.friction_deg = 0; }).empty());
    EXPECT_FALSE(bad([](auto& i) { i.support_height_m = 5.0; }).empty());  // y1 = 4
    EXPECT_NE(bad([](auto& i) { i.a1_m = 8; }).find("block 2: L_n must be positive"), std::string::npos);
    const std::pair<const char*, std::function<void(TopplingInput&, double)>> fields[] = {
        {"block_width_m", [](auto& i, double v) { i.block_width_m = v; }},
        {"base_dip_deg", [](auto& i, double v) { i.base_dip_deg = v; }},
        {"a1_m", [](auto& i, double v) { i.a1_m = v; }},
        {"a2_m", [](auto& i, double v) { i.a2_m = v; }},
        {"unit_weight", [](auto& i, double v) { i.unit_weight = v; }},
        {"friction_deg", [](auto& i, double v) { i.friction_deg = v; }},
        {"support_force", [](auto& i, double v) { i.support_force = v; }},
        {"support_angle_deg", [](auto& i, double v) { i.support_angle_deg = v; }},
        {"support_height_m", [](auto& i, double v) { i.support_height_m = v; }},
        {"heights_m[5]", [](auto& i, double v) { i.heights_m[5] = v; }},
    };
    for (const auto& [name, set] : fields)
        for (double v : {kNan, kInf}) {
            const auto msg = bad([&](auto& i) { set(i, v); });
            EXPECT_NE(msg.find(name), std::string::npos) << name;
        }
    TopplingInput empty;  // campos sin dato (NaN por defecto) lanzan con su nombre
    empty.heights_m = {4, 8};
    empty.crest_block = 1;
    EXPECT_NE(error_of([&] { toppling_fs(empty); }).find("block_width_m"), std::string::npos);
}
