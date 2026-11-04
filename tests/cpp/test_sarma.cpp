#include <gtest/gtest.h>

#include <cmath>
#include <limits>
#include <string>

#include "error_of.hpp"
#include "rockmasspy/planar.hpp"
#include "rockmasspy/sarma.hpp"

using namespace rockmasspy;

namespace {
const double kPi = 3.14159265358979323846;
const double kNan = std::numeric_limits<double>::quiet_NaN();

LeMaterial mc(double g, double c, double phi, double ru = 0.0) {
    LeMaterial m;
    m.unit_weight = g; m.cohesion = c; m.friction_deg = phi; m.ru = ru;
    return m;
}
std::vector<Point2> mirror(const std::vector<Point2>& p) {
    std::vector<Point2> q(p.rbegin(), p.rend());
    for (auto& v : q) v.x = -v.x;
    return q;
}
bool has(const std::vector<std::string>& v, const std::string& s) {
    for (const auto& w : v)
        if (w.find(s) != std::string::npos) return true;
    return false;
}

// Slide Sarma Verification, problema 4 (Hoek 1987): pila de desmonte sobre piso cizallado; la masa baja hacia -x.
// El último tramo de la base se prolonga sobre la recta (108, 6.4)-(128, 67) hasta pasar el terreno: la librería
// corta la base donde cruza el terreno (el (128, 67) rotulado queda 0.67 m bajo él).
LeSection problem4() {
    LeSection s;
    s.surface = {{-50, -2.97}, {0, 0}, {111.4, 76.5}, {229.545, 13.6815}, {250, 14.9}};
    s.materials = {mc(15.7, 10, 6), mc(15.7, 100, 42)};  // 0 piso cizallado, 1 desmonte
    s.layers = {LeLayer{{{-50, -2.97}, {0, 0}, {250, 14.9}}, 1}, LeLayer{{}, 0}};
    return s;
}
SarmaInput problem4_input(double angle = 116.5) {
    return {{{0, 0}, {108, 6.4}, {130, 6.4 + 22 * 60.6 / 20}}, {angle}};
}

// Bloque planar de Hoek como una cuña: cara a la derecha, pie en (0, 0), superficie superior horizontal en H.
LeSection planar_section(double H, double face, double g, double c, double phi, double kh, double ru = 0.0) {
    LeSection s;
    s.surface = {{-400, H}, {-H / std::tan(face * kPi / 180), H}, {0, 0}, {100, 0}};
    s.materials = {mc(g, c, phi, ru)};
    s.layers = {LeLayer{{}, 0}};
    s.kh = kh;
    return s;
}
SarmaInput planar_base(double H, double plane) { return {{{-H / std::tan(plane * kPi / 180), H}, {0, 0}}, {}}; }
PlanarInput planar_in(double H, double face, double plane, double g, double c, double phi, double kh) {
    PlanarInput in;
    in.height_m = H; in.face_dip_deg = face; in.plane_dip_deg = plane; in.unit_weight = g; in.cohesion = c;
    in.friction_deg = phi; in.kh = kh;
    return in;
}
}  // namespace

TEST(Sarma, Problem4DryWithGivenInterface) {
    const auto r = sarma_fs(problem4(), problem4_input());
    ASSERT_TRUE(r.factor_of_safety.has_value());
    EXPECT_NEAR(*r.factor_of_safety, 1.1977, 2e-3);
    EXPECT_NEAR(*r.factor_of_safety, 1.198, 0.01 * 1.198);
    ASSERT_EQ(r.wedges.size(), 2u);
    EXPECT_EQ(r.wedges[0].base_material, 0);  // tramo sobre el contacto: el piso cizallado
    EXPECT_EQ(r.wedges[1].base_material, 1);
    EXPECT_GT(r.wedges[0].interface_normal_right, 0.0);
    EXPECT_EQ(r.wedges[1].interface_normal_right, 0.0);
    EXPECT_NEAR(r.interface_angles_deg[0], 116.5, 1e-12);
    EXPECT_EQ(r.info.method_id, "Sarma-NonVertical");
    EXPECT_EQ(r.info.verification, Verification::Secondary);
    EXPECT_TRUE(r.warnings.empty());
}

TEST(Sarma, Problem4OptimizedInterface) {
    SarmaOptions o;
    o.optimize_angles = true;
    const auto r = sarma_fs(problem4(), problem4_input(), o);
    ASSERT_TRUE(r.factor_of_safety.has_value());
    EXPECT_LE(*r.factor_of_safety, 1.1977);
    EXPECT_LE(*r.factor_of_safety, *sarma_fs(problem4(), problem4_input()).factor_of_safety);
    EXPECT_GE(*r.factor_of_safety, 1.18);
    EXPECT_GT(r.interface_angles_deg[0], 100.0);
    EXPECT_LT(r.interface_angles_deg[0], 130.0);
    EXPECT_TRUE(has(r.notes, "pattern search"));
}

TEST(Sarma, CriticalAccelerationGivesFsOne) {
    const auto r = sarma_fs(problem4(), problem4_input());
    ASSERT_TRUE(r.critical_acceleration.has_value());
    EXPECT_GT(*r.critical_acceleration, 0.0);
    LeSection s = problem4();
    s.kh = *r.critical_acceleration;
    EXPECT_NEAR(*sarma_fs(s, problem4_input()).factor_of_safety, 1.0, 1e-6);
}

TEST(Sarma, ReflectedSectionGivesSameResult) {
    const LeSection a = problem4();
    LeSection b = a;
    b.surface = mirror(a.surface);
    b.layers[0].bottom = mirror(a.layers[0].bottom);
    SarmaInput ib = problem4_input();
    ib.base = mirror(ib.base);
    ib.interface_angles_deg = {180.0 - 116.5};
    const auto ra = sarma_fs(a, problem4_input()), rb = sarma_fs(b, ib);
    EXPECT_NEAR(*ra.factor_of_safety, *rb.factor_of_safety, 1e-9);
    EXPECT_NEAR(*ra.critical_acceleration, *rb.critical_acceleration, 1e-9);
    EXPECT_NEAR(rb.interface_angles_deg[0], 63.5, 1e-9);
    ASSERT_EQ(rb.wedges.size(), 2u);
    EXPECT_NEAR(ra.wedges[0].weight, rb.wedges[1].weight, 1e-6);
    EXPECT_NEAR(ra.wedges[0].interface_normal_right, rb.wedges[0].interface_normal_right, 1e-6);
}

// PL-1 de RocPlane (Sau Mau Ping) y los tres casos de Watts y West, secos, contra planar_fs a ±1e-6
TEST(Sarma, OneWedgeIsHoekPlanarDry) {
    EXPECT_NEAR(*sarma_fs(planar_section(60, 50, 0.027, 0.1, 35, 0.08), planar_base(60, 35)).factor_of_safety,
                *planar_fs(planar_in(60, 50, 35, 0.027, 0.1, 35, 0.08)).factor_of_safety, 1e-6);
    const double rows[3][3] = {{0, 20, 0.36397}, {1.1025, 20, 0.64361}, {2.2051, 35, 1.25951}};
    for (const auto& w : rows) {
        const double want = *planar_fs(planar_in(95, 85, 45, 0.18192, w[0], w[1], 0)).factor_of_safety;
        EXPECT_NEAR(want, w[2], 1e-5);
        EXPECT_NEAR(*sarma_fs(planar_section(95, 85, 0.18192, w[0], w[1], 0), planar_base(95, 45)).factor_of_safety,
                    want, 1e-6);
    }
}

// PL-1 saturado sin grieta: U = γw H² / (4 sin ψp) (Hoek). Con una sola cuña solo cuenta la U total, así que un ru
// con ru·W / cos ψp = U la reproduce exacta: 0.818425.
TEST(Sarma, OneWedgeIsPl1Saturated) {
    const double H = 60, pp = 35 * kPi / 180, g = 0.027, gw = 0.01;
    const double W = 0.5 * g * H * H * (1 / std::tan(pp) - 1 / std::tan(50 * kPi / 180));
    const double U = gw * H * H / (4 * std::sin(pp));
    const auto r = sarma_fs(planar_section(H, 50, g, 0.1, 35, 0.08, U * std::cos(pp) / W), planar_base(H, 35));
    EXPECT_NEAR(*r.factor_of_safety, 0.818425, 1e-6);
    EXPECT_NEAR(r.wedges[0].weight, 28.6278, 1e-4);
    // piezométrica en el terreno: U = γw·área / cos ψp, igual a la de planar_fs con water_fill = 2 (1 - tan ψp / tan ψf)
    LeSection s = planar_section(H, 50, g, 0.1, 35, 0.08);
    s.piezometric = s.surface;
    s.water_unit_weight = gw;
    auto in = planar_in(H, 50, 35, g, 0.1, 35, 0.08);
    in.water_fill = 2 * (1 - std::tan(pp) / std::tan(50 * kPi / 180));
    in.water_unit_weight = gw;
    EXPECT_NEAR(*sarma_fs(s, planar_base(H, 35)).factor_of_safety, *planar_fs(in).factor_of_safety, 1e-6);
}

TEST(Sarma, NotSupportedCases) {
    LeSection hb = problem4();
    hb.materials[1].model = StrengthModel::HoekBrown;
    hb.materials[1].hb = hb_params_from_constants(1, 0.01, 0.5);
    hb.materials[1].sigma_ci = 1000;
    EXPECT_NE(error_of([&] { sarma_fs(hb, problem4_input()); }).find("not supported in Sarma"), std::string::npos);
    LeSection crack = problem4();
    crack.crack = LeTensionCrack{5, 0};
    EXPECT_NE(error_of([&] { sarma_fs(crack, problem4_input()); }).find("not supported in Sarma"), std::string::npos);
    LeSection pond = planar_section(60, 50, 0.027, 0.1, 35, 0);
    pond.piezometric = std::vector<Point2>{{-400, 60}, {100, 10}};  // sobre el terreno al pie
    EXPECT_NE(error_of([&] { sarma_fs(pond, planar_base(60, 35)); }).find("not supported in Sarma"), std::string::npos);
}

namespace {
// Dos vértices interiores bajo una cara a la derecha
LeSection two_vertex_section() {
    LeSection s;
    s.surface = {{-100, 50}, {-40, 50}, {0, 0}, {50, 0}};
    s.materials = {mc(20, 10, 30)};
    s.layers = {LeLayer{{}, 0}};
    return s;
}
SarmaInput two_vertex(double a0, double a1) { return {{{-90, 50}, {-60, 20}, {-30, 5}, {0, 0}}, {a0, a1}}; }
}  // namespace

TEST(Sarma, ThreeWedgesSolve) {
    const auto r = sarma_fs(two_vertex_section(), two_vertex(80, 85));
    ASSERT_TRUE(r.factor_of_safety.has_value());
    EXPECT_GT(*r.factor_of_safety, 0.0);
    EXPECT_EQ(r.wedges.size(), 3u);
    double area = 0;
    for (const auto& w : r.wedges) area += w.area;
    // área de la masa entre el terreno y la base (shoelace del polígono cerrado)
    const std::vector<Point2> mass{{-90, 50}, {-60, 20}, {-30, 5}, {0, 0}, {-40, 50}};
    EXPECT_NEAR(area, sarma_detail::area(mass), 1e-9);
}

TEST(Sarma, InvalidInterfacesThrow) {
    const auto s = two_vertex_section();
    EXPECT_NE(error_of([&] { sarma_fs(s, two_vertex(30, 120)); }).find("interfaces 0 and 1 cross"), std::string::npos);
    EXPECT_NE(error_of([&] { sarma_fs(s, two_vertex(80, 150)); }).find("does not cut the ground surface"),
              std::string::npos);
    EXPECT_NE(error_of([&] { sarma_fs(s, two_vertex(0, 90)); }).find("must be within (0, 180)"), std::string::npos);
    EXPECT_NE(error_of([&] { sarma_fs(s, two_vertex(80, 180)); }).find("must be within (0, 180)"), std::string::npos);
    EXPECT_NE(error_of([&] { sarma_fs(s, two_vertex(kNan, 90)); }).find("interface_angles_deg[0]"), std::string::npos);
    EXPECT_NE(error_of([&] { sarma_fs(s, {two_vertex(80, 85).base, {80}}); }).find("one angle per interior vertex"),
              std::string::npos);
    // en el problema 4 la base sube a 71.7° hacia la cresta: una interfaz a 60° apunta fuera de la masa
    EXPECT_NE(error_of([&] { sarma_fs(problem4(), problem4_input(60)); }).find("inadmissible mechanism at interface 0"),
              std::string::npos);
    SarmaInput nan_base = two_vertex(80, 85);
    nan_base.base[1].y = kNan;
    EXPECT_NE(error_of([&] { sarma_fs(s, nan_base); }), "");
    LeSection nan_section = s;
    nan_section.materials[0].cohesion = kNan;
    EXPECT_NE(error_of([&] { sarma_fs(nan_section, two_vertex(80, 85)); }).find("cohesion"), std::string::npos);
    SarmaInput above = two_vertex(80, 85);
    above.base[1] = {-60, 55};  // sobre el terreno
    EXPECT_NE(error_of([&] { sarma_fs(s, above); }), "");
}

TEST(Sarma, NoStrengthAndBackward) {
    LeSection s = planar_section(60, 50, 0.027, 0, 0, 0);
    EXPECT_EQ(*sarma_fs(s, planar_base(60, 35)).factor_of_safety, 0.0);
    // la cuña del pie sube y lleva un estrato pesado: sin resistencia la masa no se mueve hacia la cara
    LeSection up;
    up.surface = {{-100, 10}, {-50, 5}, {-40, -20}, {0, 0}, {100, 0}};
    up.materials = {mc(1, 10, 30), mc(100, 10, 30)};
    up.layers = {LeLayer{{{-100, -200}, {-46, -30}, {-40, -15}, {0, -5}, {100, -5}}, 0}, LeLayer{{}, 1}};
    const auto r = sarma_fs(up, {{{-50, 5}, {-40, -22}, {0, 0}}, {90}});
    EXPECT_FALSE(r.factor_of_safety.has_value());
    EXPECT_TRUE(has(r.notes, "does not move towards the face"));
}
