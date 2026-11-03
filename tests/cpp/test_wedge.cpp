#include <gtest/gtest.h>

#include <array>
#include <cmath>
#include <limits>
#include <string>

#include "error_of.hpp"
#include "rockmasspy/wedge.hpp"

using namespace rockmasspy;

namespace {
const double kNan = std::numeric_limits<double>::quiet_NaN();
const double kInf = std::numeric_limits<double>::infinity();
const double kPi = 3.14159265358979323846;

WedgeJoint jt(double dd, double dip, double c, double phi, double u = 0.0) {
    WedgeJoint j;
    j.plane = {dd, dip}; j.cohesion = c; j.friction_deg = phi; j.water_pressure = u;
    return j;
}
WedgeInput mk(WedgeJoint a, WedgeJoint b, PlaneOrientation face, PlaneOrientation upper, double h, double g) {
    WedgeInput in;
    in.joint1 = a; in.joint2 = b; in.face = face; in.upper = upper; in.height_m = h; in.unit_weight = g;
    return in;
}
// SWedge, problema 6 (Priest ej. 1), MN y m
WedgeInput cu2() {
    auto in = mk(jt(203, 47, 0.010, 40, 0.005), jt(287, 52, 0.020, 35, 0.015), {230, 60}, {225, 5}, 6.7978, 0.026);
    in.external_force = 0.18; in.external_direction = {168, 70};
    return in;
}
// SWedge, problema 7 (Priest ej. 2)
WedgeInput cu3() {
    return mk(jt(65, 74, 0.015, 32, 0.025), jt(186, 41, 0.005, 40, 0.015), {134, 65}, {122, 11}, 6.8471, 0.025);
}
WedgeInput dry(PlaneOrientation a, PlaneOrientation b, double phi1, double phi2, PlaneOrientation face,
               PlaneOrientation upper = {180, 0}) {
    return mk(jt(a.dip_direction_deg, a.dip_deg, 0, phi1), jt(b.dip_direction_deg, b.dip_deg, 0, phi2), face, upper, 10, 0.026);
}
double fs(const WedgeInput& in) { return *wedge_fs(in).factor_of_safety; }
bool has(const WedgeResult& r, const std::string& s) {
    for (const auto& n : r.notes) if (n == s) return true;
    return false;
}
}  // namespace

TEST(Wedge, Cu2DosPlanos) {
    const auto r = wedge_fs(cu2());
    EXPECT_NEAR(*r.factor_of_safety, 1.4966, 1e-4);
    EXPECT_EQ(r.mode, WedgeMode::TwoPlanes);
    EXPECT_NEAR(r.volume, 45.201, 1e-3);
    EXPECT_NEAR(r.weight, 1.175, 1e-3);
    EXPECT_NEAR(r.area1, 41.147, 1e-3);
    EXPECT_NEAR(r.area2, 20.428, 1e-3);
    EXPECT_NEAR(r.face_area, 38.955, 1e-3);
    EXPECT_NEAR(r.upper_area, 21.242, 1e-3);
    EXPECT_NEAR(r.normal1, 0.407, 1e-3);
    EXPECT_NEAR(r.normal2, 0.251, 1e-3);
    EXPECT_NEAR(r.driving_force, 0.893, 1e-3);
    EXPECT_NEAR(r.resisting_force, 1.337, 1e-3);
    ASSERT_TRUE(r.intersection.has_value());
    EXPECT_NEAR(r.intersection->trend_deg, 239.4, 0.1);
    EXPECT_NEAR(r.intersection->plunge_deg, 40.8, 0.1);
    EXPECT_EQ(r.info.verification, Verification::Secondary);
    EXPECT_EQ(r.info.method_id, "Wedge-Tetrahedral-Vector");
    EXPECT_TRUE(r.warnings.empty());
}

TEST(Wedge, Cu3UnPlano) {
    const auto r = wedge_fs(cu3());
    EXPECT_NEAR(*r.factor_of_safety, 0.8493, 1e-4);
    EXPECT_EQ(r.mode, WedgeMode::PlaneTwo);
    EXPECT_NEAR(r.normal2, 0.793, 1e-3);
    EXPECT_NEAR(r.driving_force, 1.117, 1e-3);
    EXPECT_NEAR(r.resisting_force, 0.949, 1e-3);
    EXPECT_NEAR(r.weight, 2.044, 1e-3);
    EXPECT_NEAR(r.area1, 34.393, 1e-3);
    EXPECT_NEAR(r.area2, 56.613, 1e-3);
    EXPECT_NEAR(r.face_area, 30.012, 1e-3);
    EXPECT_NEAR(r.upper_area, 40.263, 1e-3);
    EXPECT_NEAR(r.volume, 81.741, 1e-3);
}

TEST(Wedge, KumsarYSwedge) {
    EXPECT_NEAR(fs(dry({195, 45}, {105, 70}, 30, 30, {160, 70})), 0.7123, 1e-4);
    auto c4 = dry({33.5, 75}, {248, 75}, 40.8, 40.8, {337.5, 75});
    EXPECT_NEAR(fs(c4), 2.0203, 1e-4);
    c4.kh = 0.3303;
    EXPECT_NEAR(fs(c4), 0.9872, 1e-4);
    auto p2 = dry({119, 50}, {241, 50}, 35, 35, {180, 70});
    EXPECT_NEAR(fs(p2), 1.6325, 1e-4);
    p2.kh = 0.2365;
    EXPECT_NEAR(fs(p2), 1.0001, 5e-4);
}

TEST(Wedge, KovariFritz) {
    const double dips[] = {42.7, 45, 47.5}, phis[] = {33, 35, 37}, plunge[] = {35.645, 37.852, 40.301};
    for (int k = 0; k < 3; ++k) {
        const auto r = wedge_fs(dry({141, dips[k]}, {219, dips[k]}, phis[k], phis[k], {180, 70}));
        EXPECT_NEAR(r.intersection->plunge_deg, plunge[k], 2e-3);
        EXPECT_NEAR(*r.factor_of_safety, 1.0, 0.01);
    }
}

TEST(Wedge, SimetricaSecaSinCohesion) {
    for (double dip : {35.0, 50.0, 70.0})
        for (double delta : {20.0, 45.0, 70.0}) {
            const PlaneOrientation a{180 - delta, dip}, b{180 + delta, dip};
            // �ngulo entre las normales que miran hacia dentro de la cu�a (hacia arriba); puede ser obtuso
            const auto up = [](PlaneOrientation p) {
                const double t = (p.dip_direction_deg + 180) * kPi / 180, d = p.dip_deg * kPi / 180;
                return std::array<double, 3>{std::sin(d) * std::cos(t), std::sin(d) * std::sin(t), -std::cos(d)};
            };
            const auto ua = up(a), ub = up(b);
            const double theta = std::acos(ua[0] * ub[0] + ua[1] * ub[1] + ua[2] * ub[2]) * 180 / kPi;
            const double xi = (180.0 - theta) / 2.0;
            const auto r = wedge_fs(dry(a, b, 30, 30, {180, 75}));
            const double tpsi = std::tan(r.intersection->plunge_deg * kPi / 180.0);
            EXPECT_NEAR(*r.factor_of_safety, std::tan(30 * kPi / 180) / (tpsi * std::sin(xi * kPi / 180)), 1e-9);
        }
}

TEST(Wedge, Cu1HoekNoDependeDeLaCara) {
    for (PlaneOrientation face : {PlaneOrientation{185, 60}, {170, 75}, {185, 80}}) {
        const double v = fs(dry({105, 40}, {235, 70}, 20, 30, face, {185, 0}));
        EXPECT_NEAR(v, 1.1935, 1e-4);
        EXPECT_LT(std::fabs(v - 1.18) / 1.18, 0.03);
    }
}

TEST(Wedge, JuntaVerticalEnLosDosSentidos) {
    const auto ref = wedge_fs(mk(jt(110, 90, 0.01, 30), jt(230, 50, 0.01, 30), {180, 70}, {180, 0}, 10, 0.026));
    const auto alt = wedge_fs(mk(jt(290, 90, 0.01, 30), jt(230, 50, 0.01, 30), {180, 70}, {180, 0}, 10, 0.026));
    ASSERT_TRUE(ref.factor_of_safety && alt.factor_of_safety);
    EXPECT_NEAR(*ref.factor_of_safety, *alt.factor_of_safety, 1e-12);
    EXPECT_EQ(ref.mode, alt.mode);
    EXPECT_NE(ref.mode, WedgeMode::NotFormed);
    // la misma junta como segunda
    const auto sw = wedge_fs(mk(jt(230, 50, 0.01, 30), jt(290, 90, 0.01, 30), {180, 70}, {180, 0}, 10, 0.026));
    EXPECT_NEAR(*sw.factor_of_safety, *ref.factor_of_safety, 1e-12);
}

TEST(Wedge, IntersectionHorizontalNoAfloraArriba) {
    for (double dd : {0.0, 180.0}) {
        const auto r = wedge_fs(mk(jt(dd, 0, 0, 30), jt(150, 60, 0, 30), {180, 70}, {180, 0}, 10, 0.026));
        EXPECT_EQ(r.mode, WedgeMode::NotFormed);
        EXPECT_FALSE(r.factor_of_safety.has_value());
        EXPECT_TRUE(has(r, "wedge not formed: the intersection does not outcrop on the upper slope"));
        EXPECT_TRUE(r.warnings.empty());
    }
}

TEST(Wedge, Giro) {
    const auto base = cu2();
    const double f0 = fs(base);
    for (double rot : {17.0, 123.0, 301.0}) {
        auto in = base;
        for (auto* p : {&in.joint1.plane, &in.joint2.plane, &in.face, &in.upper})
            p->dip_direction_deg = std::fmod(p->dip_direction_deg + rot, 360.0);
        in.external_direction.trend_deg = std::fmod(in.external_direction.trend_deg + rot, 360.0);
        const auto r = wedge_fs(in);
        EXPECT_NEAR(*r.factor_of_safety, f0, 1e-10);
        EXPECT_EQ(r.mode, WedgeMode::TwoPlanes);
    }
}

TEST(Wedge, LimiteNormalCeroDeUnaJunta) {
    auto base = cu2();
    base.joint1.water_pressure = 0.0; base.joint2.water_pressure = 0.0;  // CU-2 seco
    const auto d0 = wedge_fs(base);
    ASSERT_EQ(d0.mode, WedgeMode::TwoPlanes);
    const double u = d0.normal1 / d0.area1;
    auto lo = base, hi = base;
    lo.joint1.water_pressure = u * (1.0 - 1e-12);
    hi.joint1.water_pressure = u * (1.0 + 1e-12);
    const double f_lo = fs(lo), f_hi = fs(hi);
    EXPECT_NEAR(f_lo, f_hi, 1e-9);
    // y es el menor de los dos modos vecinos, lejos del límite
    auto two = base, one = base;
    two.joint1.water_pressure = u * (1.0 - 1e-4);
    one.joint1.water_pressure = u * (1.0 + 1e-4);
    EXPECT_EQ(wedge_fs(two).mode, WedgeMode::TwoPlanes);
    EXPECT_EQ(wedge_fs(one).mode, WedgeMode::PlaneTwo);
    EXPECT_LE(f_lo, std::min(fs(two), fs(one)) + 1e-3);
    EXPECT_LT(f_lo, std::max(fs(two), fs(one)) + 1e-9);
}

TEST(Wedge, NoFormada) {
    auto a = cu2(); a.face = {50, 60};  // tendencia opuesta a la cara
    auto b = cu2(); b.face = {230, 30};  // la intersección buza más que el buzamiento aparente de la cara
    auto c = cu2(); c.joint1.plane = c.face;  // junta paralela a la cara, del lado menos favorable
    for (const auto& in : {a, b, c}) {
        const auto r = wedge_fs(in);
        EXPECT_EQ(r.mode, WedgeMode::NotFormed);
        EXPECT_FALSE(r.factor_of_safety.has_value());
        EXPECT_TRUE(has(r, "wedge not formed: the intersection does not daylight in the face"));
        EXPECT_TRUE(r.warnings.empty());
    }
    for (const auto& in : {mk(jt(203, 47, 0, 30), jt(203, 47, 0, 30), {230, 60}, {225, 5}, 6, 0.026),
                           mk(jt(110, 90, 0, 30), jt(290, 90, 0, 30), {230, 60}, {225, 5}, 6, 0.026)}) {
        const auto r = wedge_fs(in);
        EXPECT_EQ(r.mode, WedgeMode::NotFormed);
        EXPECT_FALSE(r.factor_of_safety.has_value());
        EXPECT_TRUE(has(r, "wedge not formed: parallel joints"));
        EXPECT_TRUE(r.warnings.empty());
    }
    // talud superior que se levanta tanto como la intersección: no aflora arriba
    auto d = dry({141, 45}, {219, 45}, 30, 30, {180, 70}, {180, 38});
    const auto rd = wedge_fs(d);
    EXPECT_EQ(rd.mode, WedgeMode::NotFormed);
    EXPECT_TRUE(has(rd, "wedge not formed: the intersection does not outcrop on the upper slope"));
}

TEST(Wedge, Despegue) {
    auto in = cu2();
    in.joint1.water_pressure = 0.05; in.joint2.water_pressure = 0.05;
    const auto r = wedge_fs(in);
    EXPECT_EQ(r.mode, WedgeMode::Lifting);
    ASSERT_TRUE(r.factor_of_safety.has_value());
    EXPECT_EQ(*r.factor_of_safety, 0.0);
    ASSERT_EQ(r.warnings.size(), 1u);
    EXPECT_EQ(r.warnings[0], "wedge lifts off both joints");
}

TEST(Wedge, SinFuerzaQueDeslizaDaInfinito) {
    auto in = dry({141, 45}, {219, 45}, 35, 35, {180, 70});
    const auto r0 = wedge_fs(in);
    const double psi = r0.intersection->plunge_deg * kPi / 180.0;
    in.external_force = r0.weight * std::tan(psi);  // empuje horizontal contra la intersección que anula lo que desliza
    in.external_direction = {0, 0};
    const auto r = wedge_fs(in);
    EXPECT_EQ(r.mode, WedgeMode::TwoPlanes);
    ASSERT_TRUE(r.factor_of_safety.has_value());
    EXPECT_TRUE(std::isinf(*r.factor_of_safety));
    EXPECT_FALSE(r.notes.empty());
    EXPECT_TRUE(r.warnings.empty());
}

TEST(Wedge, Validacion) {
    auto bad = [](auto mut, const char* name) {
        auto in = cu2();
        mut(in);
        const std::string e = error_of([&] { wedge_fs(in); });
        EXPECT_NE(e.find(name), std::string::npos) << name << " -> " << e;
    };
    bad([](WedgeInput& i) { i.joint1.plane.dip_deg = kNan; }, "joint1.plane.dip_deg");
    bad([](WedgeInput& i) { i.joint2.plane.dip_direction_deg = kInf; }, "joint2.plane.dip_direction_deg");
    bad([](WedgeInput& i) { i.joint2.plane.dip_deg = kNan; }, "joint2.plane.dip_deg");
    bad([](WedgeInput& i) { i.joint1.plane.dip_direction_deg = kNan; }, "joint1.plane.dip_direction_deg");
    bad([](WedgeInput& i) { i.face.dip_deg = kNan; }, "face.dip_deg");
    bad([](WedgeInput& i) { i.face.dip_direction_deg = kNan; }, "face.dip_direction_deg");
    bad([](WedgeInput& i) { i.upper.dip_deg = kNan; }, "upper.dip_deg");
    bad([](WedgeInput& i) { i.upper.dip_direction_deg = kNan; }, "upper.dip_direction_deg");
    bad([](WedgeInput& i) { i.joint1.cohesion = kNan; }, "joint1.cohesion");
    bad([](WedgeInput& i) { i.joint2.cohesion = kNan; }, "joint2.cohesion");
    bad([](WedgeInput& i) { i.joint1.friction_deg = kNan; }, "joint1.friction_deg");
    bad([](WedgeInput& i) { i.joint2.friction_deg = kNan; }, "joint2.friction_deg");
    bad([](WedgeInput& i) { i.joint1.water_pressure = kNan; }, "joint1.water_pressure");
    bad([](WedgeInput& i) { i.joint2.water_pressure = kNan; }, "joint2.water_pressure");
    bad([](WedgeInput& i) { i.height_m = kNan; }, "height_m");
    bad([](WedgeInput& i) { i.unit_weight = kNan; }, "unit_weight");
    bad([](WedgeInput& i) { i.kh = kNan; }, "kh");
    bad([](WedgeInput& i) { i.external_force = kNan; }, "external_force");
    bad([](WedgeInput& i) { i.external_direction.trend_deg = kNan; }, "external_direction.trend_deg");
    bad([](WedgeInput& i) { i.external_direction.plunge_deg = kInf; }, "external_direction.plunge_deg");
    bad([](WedgeInput& i) { i.joint1.plane.dip_deg = 95; }, "joint1.plane.dip_deg");
    bad([](WedgeInput& i) { i.joint2.friction_deg = 90; }, "joint2.friction_deg");
    bad([](WedgeInput& i) { i.height_m = 0; }, "height_m");
    bad([](WedgeInput& i) { i.unit_weight = 0; }, "unit_weight");
    bad([](WedgeInput& i) { i.kh = -0.1; }, "kh");
    bad([](WedgeInput& i) { i.kh = 1.1; }, "kh");
    bad([](WedgeInput& i) { i.joint2.water_pressure = -1; }, "joint2.water_pressure");
    bad([](WedgeInput& i) { i.joint1.cohesion = -1; }, "joint1.cohesion");
    bad([](WedgeInput& i) { i.external_force = -1; }, "external_force");
    bad([](WedgeInput& i) { i.joint1.plane.dip_direction_deg = 361; }, "joint1.plane.dip_direction_deg");
}
