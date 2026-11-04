#include <gtest/gtest.h>

#include <cmath>
#include <limits>
#include <vector>

#include "error_of.hpp"
#include "rockmasspy/newmark.hpp"

using namespace rockmasspy;

namespace {
const double kInf = std::numeric_limits<double>::infinity();
const double kNan = std::numeric_limits<double>::quiet_NaN();
const double kG = 9.80665;

// Pulso rectangular sintético: A en t <= t0 (con holgura de medio paso), luego ceros hasta `total`.
std::vector<double> rect(double A, double t0, double dt, double total) {
    std::vector<double> a;
    for (int i = 0; i * dt <= total + 1e-12; ++i) a.push_back(i * dt <= t0 + 1e-9 ? A : 0.0);
    return a;
}
NewmarkInput make(std::vector<double> acc, double dt, double ky) {
    NewmarkInput in;
    in.acceleration_g = std::move(acc);
    in.dt_s = dt;
    in.ky = ky;
    return in;
}
// Solución cerrada del pulso rectangular con ky < A. Durante t0 la aceleración relativa es (A - ky) g, así que
// v(t0) = (A - ky) g t0 y d1 = (A - ky) g t0² / 2. Después a = 0 y desacelera a ky g: se detiene tras
// v(t0) / (ky g) y recorre d2 = v(t0)² / (2 ky g) = (A - ky)² g t0² / (2 ky). Suma: d = g t0² A (A - ky) / (2 ky).
double rect_closed(double A, double t0, double ky) { return kG * t0 * t0 * A * (A - ky) / (2.0 * ky); }
}  // namespace

TEST(Newmark, PulsoRectangular) {
    EXPECT_NEAR(rect_closed(0.3, 0.5, 0.1), 0.73550, 1e-5);
    const auto r = newmark_rigid_block(make(rect(0.3, 0.5, 1e-4, 2.0), 1e-4, 0.1));
    EXPECT_NEAR(r.displacement_m, 0.73550, 0.005 * 0.73550);
    EXPECT_NEAR(r.max_velocity_m_s, 0.2 * kG * 0.5, 0.005 * 0.2 * kG * 0.5);
    EXPECT_NEAR(r.time_of_max_s, 0.5, 2e-4);
    EXPECT_DOUBLE_EQ(r.displacement_history_m.back(), r.displacement_m);
    EXPECT_EQ(r.displacement_history_m.front(), 0.0);
    EXPECT_TRUE(r.warnings.empty());
    EXPECT_EQ(r.info.method_id, "Newmark-RigidBlock");
    EXPECT_EQ(r.info.verification, Verification::Secondary);
    EXPECT_NE(r.info.source.find("Newmark (1965)"), std::string::npos);
    const auto c = newmark_rigid_block(make(rect(0.3, 0.5, 1e-3, 2.0), 1e-3, 0.1));
    EXPECT_NEAR(c.displacement_m, 0.73550, 0.01 * 0.73550);
}

TEST(Newmark, HistorialNoDecreciente) {
    const auto r = newmark_rigid_block(make(rect(0.3, 0.5, 1e-3, 2.0), 1e-3, 0.1));
    ASSERT_EQ(r.displacement_history_m.size(), rect(0.3, 0.5, 1e-3, 2.0).size());
    for (std::size_t i = 1; i < r.displacement_history_m.size(); ++i)
        EXPECT_GE(r.displacement_history_m[i], r.displacement_history_m[i - 1]);
}

TEST(Newmark, KySobreElPicoDaCero) {
    for (double ky : {0.3, 0.5}) {
        const auto r = newmark_rigid_block(make(rect(0.3, 0.5, 1e-3, 1.0), 1e-3, ky));
        EXPECT_EQ(r.displacement_m, 0.0);
        EXPECT_EQ(r.max_velocity_m_s, 0.0);
        ASSERT_EQ(r.notes.size(), 1u);
        EXPECT_NE(r.notes[0].find("does not slide"), std::string::npos);
    }
}

TEST(Newmark, RegistroQueTerminaDeslizandoAvisa) {
    const auto r = newmark_rigid_block(make(rect(0.3, 1.0, 1e-3, 1.0), 1e-3, 0.1));
    ASSERT_EQ(r.warnings.size(), 1u);
    EXPECT_NE(r.warnings[0].find("still sliding"), std::string::npos);
}

TEST(Newmark, EscalaIgualARegistroMultiplicado) {
    auto in = make(rect(0.15, 0.5, 1e-3, 2.0), 1e-3, 0.1);
    in.scale = 2.0;
    const auto a = newmark_rigid_block(in);
    const auto b = newmark_rigid_block(make(rect(0.3, 0.5, 1e-3, 2.0), 1e-3, 0.1));
    EXPECT_DOUBLE_EQ(a.displacement_m, b.displacement_m);
}

TEST(Newmark, AmbosSentidos) {
    // +0.3 g por 0.5 s, pausa de 2 s, -0.5 g por 0.4 s, ceros: el invertido manda (1.569 m contra 0.7355 m).
    const double dt = 1e-4;
    std::vector<double> acc;
    for (int i = 0; i * dt <= 6.0 + 1e-12; ++i) {
        const double t = i * dt;
        acc.push_back(t <= 0.5 + 1e-9 ? 0.3 : (t >= 2.5 - 1e-9 && t <= 2.9 + 1e-9 ? -0.5 : 0.0));
    }
    auto in = make(acc, dt, 0.1);
    const auto orig = newmark_rigid_block(in);
    EXPECT_NEAR(orig.displacement_m, rect_closed(0.3, 0.5, 0.1), 0.005 * rect_closed(0.3, 0.5, 0.1));
    EXPECT_TRUE(orig.notes.empty());
    in.both_directions = true;
    const auto both = newmark_rigid_block(in);
    EXPECT_NEAR(both.displacement_m, rect_closed(0.5, 0.4, 0.1), 0.005 * rect_closed(0.5, 0.4, 0.1));
    ASSERT_EQ(both.notes.size(), 1u);
    EXPECT_NE(both.notes[0].find("inverted record governs"), std::string::npos);
    for (auto& x : acc) x = -x;
    const auto neg = newmark_rigid_block(make(acc, dt, 0.1));
    EXPECT_DOUBLE_EQ(both.displacement_m, neg.displacement_m);
    in.acceleration_g = acc;  // ahora el original es el mayor
    const auto back = newmark_rigid_block(in);
    EXPECT_NE(back.notes[0].find("original record governs"), std::string::npos);
}

TEST(Newmark, Lanza) {
    const auto ok = rect(0.3, 0.5, 1e-3, 1.0);
    EXPECT_NE(error_of([&] { newmark_rigid_block(make(ok, 1e-3, 0.0)); }).find("'ky' must be strictly positive (> 0)"),
              std::string::npos);
    EXPECT_NE(error_of([&] { newmark_rigid_block(make(ok, 1e-3, -0.1)); }).find("'ky'"), std::string::npos);
    EXPECT_NE(error_of([&] { newmark_rigid_block(make(ok, 1e-3, kNan)); }).find("'ky'"), std::string::npos);
    EXPECT_NE(error_of([&] { newmark_rigid_block(make(ok, 0.0, 0.1)); }).find("'dt_s'"), std::string::npos);
    EXPECT_NE(error_of([&] { newmark_rigid_block(make(ok, -1e-3, 0.1)); }).find("'dt_s'"), std::string::npos);
    EXPECT_NE(error_of([&] { newmark_rigid_block(make(ok, kNan, 0.1)); }).find("'dt_s'"), std::string::npos);
    EXPECT_NE(error_of([&] { newmark_rigid_block(make({}, 1e-3, 0.1)); }).find("'acceleration_g'"), std::string::npos);
    EXPECT_NE(error_of([&] { newmark_rigid_block(make({0.2}, 1e-3, 0.1)); }).find("'acceleration_g'"),
              std::string::npos);
    auto bad = ok;
    bad[7] = kNan;
    EXPECT_NE(error_of([&] { newmark_rigid_block(make(bad, 1e-3, 0.1)); }).find("'acceleration_g[7]'"),
              std::string::npos);
    bad[7] = kInf;
    EXPECT_NE(error_of([&] { newmark_rigid_block(make(bad, 1e-3, 0.1)); }).find("'acceleration_g[7]'"),
              std::string::npos);
    auto in = make(ok, 1e-3, 0.1);
    in.scale = 0.0;
    EXPECT_NE(error_of([&] { newmark_rigid_block(in); }).find("'scale'"), std::string::npos);
    in.scale = -1.0;
    EXPECT_NE(error_of([&] { newmark_rigid_block(in); }).find("'scale'"), std::string::npos);
    EXPECT_NE(error_of([] { newmark_rigid_block(NewmarkInput{}); }).find("'dt_s'"), std::string::npos);
}
