#include <gtest/gtest.h>

#include <cmath>
#include <limits>

#include "error_of.hpp"
#include "rockmasspy/planar.hpp"

using namespace rockmasspy;

namespace {
const double kInf = std::numeric_limits<double>::infinity();
const double kNan = std::numeric_limits<double>::quiet_NaN();
const double kPi = 3.14159265358979323846;

PlanarInput make(double h, double ff, double pp, double g, double c, double phi) {
    PlanarInput in;
    in.height_m = h; in.face_dip_deg = ff; in.plane_dip_deg = pp; in.unit_weight = g; in.cohesion = c; in.friction_deg = phi;
    return in;
}
// RocPlane, problema 1 (Sau Mau Ping), sin grieta y saturado
PlanarInput pl1() {
    auto in = make(60, 50, 35, 0.027, 0.1, 35);
    in.water_fill = 1; in.water_unit_weight = 0.01; in.kh = 0.08;
    return in;
}
double fs(const PlanarInput& in) { return *planar_fs(in).factor_of_safety; }
}  // namespace

TEST(Planar, Pl1SinGrieta) {
    const auto r = planar_fs(pl1());
    EXPECT_NEAR(*r.factor_of_safety, 0.818425, 1e-6);
    EXPECT_NEAR(r.weight, 28.6278, 1e-4);
    EXPECT_NEAR(r.base_area, 104.6068, 1e-4);
    EXPECT_NEAR(r.uplift_force, 15.6910, 1e-4);
    EXPECT_TRUE(r.formed);
    EXPECT_EQ(r.info.verification, Verification::PrimaryLaterAuthors);
    EXPECT_NE(r.info.source.find("Hoek"), std::string::npos);
}

// Errata del manual (p. 9): imprime zw 16.6082, U 4.4932, V 0.6280 y c 0.01; no se usan, valen los de la fórmula.
TEST(Planar, Pl2GrietaCritica) {
    const auto k = critical_tension_crack(60, 50, 35);
    EXPECT_NEAR(k.depth_m, 14.00915, 1e-5);
    EXPECT_NEAR(k.distance_m, 15.33576, 1e-5);
    auto in = pl1();
    in.tension_crack_distance_m = k.distance_m;
    in.water_fill = 0.9;
    const auto r = planar_fs(in);
    EXPECT_NEAR(*r.factor_of_safety, 1.065474, 1e-6);
    EXPECT_NEAR(r.uplift_force, 5.0548, 1e-4);
    EXPECT_NEAR(r.crack_water_force, 0.7948, 1e-4);
}

TEST(Planar, Pl3PernoYExterna) {
    auto in = make(30, 50, 35, 2.79, 7, 30);
    in.tension_crack_distance_m = 9; in.water_fill = 0.51; in.water_unit_weight = 0.981; in.kh = 0.10;
    in.external_force = 37; in.external_angle_deg = 90;
    EXPECT_NEAR(fs(in), 1.22233, 1e-5);
    in.bolt_force = 111; in.bolt_plunge_deg = 30; in.bolt_mode = BoltMode::Active;
    EXPECT_NEAR(fs(in), 1.50059, 1e-5);
}

TEST(Planar, Pl4Priest) {
    auto in = make(30, 60, 30, 2.5, 2, 30);
    in.tension_crack_distance_m = 8.660; in.water_fill = 0.25; in.water_unit_weight = 0.981;
    const auto r = planar_fs(in);
    EXPECT_NEAR(*r.factor_of_safety, 1.04898, 1e-5);
    EXPECT_NEAR(r.tension_crack_depth_m, 15.000, 1e-3);
}

TEST(Planar, WattsYWest) {
    const double rows[3][3] = {{0, 20, 0.36397}, {1.1025, 20, 0.64361}, {2.2051, 35, 1.25951}};
    for (const auto& w : rows) EXPECT_NEAR(fs(make(95, 85, 45, 0.18192, w[0], w[1])), w[2], 1e-5);
}

TEST(Planar, PernosRocPlane) {
    auto in = make(33, 65, 55, 0.026, 0, 35);
    EXPECT_NEAR(fs(in), 0.4903, 5e-5);
    in.bolt_force = 0.1; in.bolt_plunge_deg = 25;
    EXPECT_NEAR(fs(in), 0.5190, 5e-5);
    in.bolt_mode = BoltMode::Passive;
    EXPECT_NEAR(fs(in), 0.5221, 5e-5);
}

TEST(Planar, Retroanalisis) {
    const auto b = planar_back_analysis(pl1(), {30, 35, 40});
    ASSERT_EQ(b.cohesion.size(), 3u);
    EXPECT_NEAR(b.cohesion[0], 0.139329, 1e-6);
    EXPECT_NEAR(b.cohesion[1], 0.131758, 1e-6);
    EXPECT_NEAR(b.cohesion[2], 0.123200, 1e-6);
    EXPECT_NEAR(*b.friction_at_zero_cohesion_deg, 70.5924, 1e-4);
    auto in = pl1();
    in.cohesion = b.cohesion[1];
    EXPECT_NEAR(fs(in), 1.0, 1e-9);
    const auto none = planar_back_analysis(pl1(), {75, 80});
    EXPECT_TRUE(none.cohesion.empty());
    EXPECT_FALSE(none.notes.empty());
    EXPECT_TRUE(error_of([] { planar_back_analysis(pl1(), {}); }).find("friction_deg") != std::string::npos);
    auto nf = pl1();
    nf.plane_dip_deg = 50;
    EXPECT_FALSE(error_of([&] { planar_back_analysis(nf, {30}); }).empty());
}

TEST(Planar, NoFormado) {
    for (double pp : {50.0, 50.0 - 1e-12}) {
        auto in = pl1();
        in.plane_dip_deg = pp;
        const auto r = planar_fs(in);
        EXPECT_FALSE(r.formed);
        EXPECT_FALSE(r.factor_of_safety.has_value());
        EXPECT_TRUE(r.warnings.empty());
        ASSERT_EQ(r.notes.size(), 1u);
        EXPECT_EQ(r.notes[0], "planar block not formed: the plane does not daylight in the face");
    }
}

TEST(Planar, GrietaEnElLimite) {
    auto in = make(60, 50, 35, 0.027, 0.1, 35);
    const double bmax = 60 * (1 / std::tan(35 * kPi / 180) - 1 / std::tan(50 * kPi / 180));
    in.tension_crack_distance_m = bmax;
    EXPECT_NEAR(planar_fs(in).tension_crack_depth_m, 0.0, 1e-9);
    in.tension_crack_distance_m = bmax + 1e-6;
    const auto msg = error_of([&] { planar_fs(in); });
    EXPECT_NE(msg.find("tension_crack_distance_m"), std::string::npos);
    EXPECT_EQ(msg.find("Received"), std::string::npos);  // no repite el valor
}

TEST(Planar, NormalNegativaYSinFuerzaQueDesliza) {
    auto in = pl1();
    in.water_unit_weight = 0.1;
    const auto r = planar_fs(in);
    ASSERT_EQ(r.warnings.size(), 1u);
    EXPECT_EQ(r.warnings[0], "effective normal force on the plane is negative: friction taken as zero");
    EXPECT_NEAR(*r.factor_of_safety, 0.1 * r.base_area / r.driving_force, 1e-12);
    EXPECT_GT(*r.factor_of_safety, 0.0);
    auto b = make(60, 50, 35, 0.027, 0.1, 35);
    b.bolt_force = 1000; b.bolt_plunge_deg = 0;
    const auto s = planar_fs(b);
    EXPECT_EQ(*s.factor_of_safety, kInf);
    ASSERT_EQ(s.notes.size(), 1u);
    EXPECT_EQ(s.notes[0], "no driving force on the block");
}

TEST(Planar, Rechazos) {
    const auto bad = [](const char* name, auto mut) {
        auto in = pl1();
        mut(in);
        const auto msg = error_of([&] { planar_fs(in); });
        EXPECT_NE(msg.find(name), std::string::npos) << name;
    };
    for (double v : {kNan, kInf}) {
        bad("height_m", [v](PlanarInput& i) { i.height_m = v; });
        bad("face_dip_deg", [v](PlanarInput& i) { i.face_dip_deg = v; });
        bad("plane_dip_deg", [v](PlanarInput& i) { i.plane_dip_deg = v; });
        bad("unit_weight", [v](PlanarInput& i) { i.unit_weight = v; });
        bad("cohesion", [v](PlanarInput& i) { i.cohesion = v; });
        bad("friction_deg", [v](PlanarInput& i) { i.friction_deg = v; });
        bad("tension_crack_distance_m", [v](PlanarInput& i) { i.tension_crack_distance_m = v; });
        bad("water_fill", [v](PlanarInput& i) { i.water_fill = v; });
        bad("water_unit_weight", [v](PlanarInput& i) { i.water_unit_weight = v; });
        bad("kh", [v](PlanarInput& i) { i.kh = v; });
        bad("bolt_force", [v](PlanarInput& i) { i.bolt_force = v; });
        bad("bolt_plunge_deg", [v](PlanarInput& i) { i.bolt_plunge_deg = v; });
        bad("external_force", [v](PlanarInput& i) { i.external_force = v; });
        bad("external_angle_deg", [v](PlanarInput& i) { i.external_angle_deg = v; });
    }
    bad("height_m", [](PlanarInput& i) { i.height_m = 0; });
    bad("face_dip_deg", [](PlanarInput& i) { i.face_dip_deg = 0; });
    bad("face_dip_deg", [](PlanarInput& i) { i.face_dip_deg = 95; });
    bad("plane_dip_deg", [](PlanarInput& i) { i.plane_dip_deg = 0; });
    bad("plane_dip_deg", [](PlanarInput& i) { i.plane_dip_deg = 90; });
    bad("friction_deg", [](PlanarInput& i) { i.friction_deg = 90; });
    bad("water_fill", [](PlanarInput& i) { i.water_fill = 1.5; });
    bad("water_unit_weight", [](PlanarInput& i) { i.water_fill = 0.5; i.water_unit_weight = kNan; });
    bad("kh", [](PlanarInput& i) { i.kh = -0.1; });
    bad("bolt_plunge_deg", [](PlanarInput& i) { i.bolt_plunge_deg = 95; });
    bad("external_angle_deg", [](PlanarInput& i) { i.external_angle_deg = 200; });
    bad("bolt_force", [](PlanarInput& i) { i.bolt_force = -1; });
    bad("external_force", [](PlanarInput& i) { i.external_force = -1; });
    EXPECT_TRUE(error_of([] { critical_tension_crack(60, 35, 35); }).find("plane_dip_deg") != std::string::npos);
}

TEST(Planar, SinAguaNoExigePesoDelAgua) {
    const auto in = make(60, 50, 35, 0.027, 0.1, 35);  // water_unit_weight sin definir con agua 0
    EXPECT_TRUE(planar_fs(in).factor_of_safety.has_value());
}
