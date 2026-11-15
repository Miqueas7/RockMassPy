#include <gtest/gtest.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <iostream>
#include <utility>
#include <vector>

#include "error_of.hpp"
#include "rockmasspy/bem2d.hpp"
#include "rockmasspy/excavation.hpp"

using namespace rockmasspy;

namespace {
constexpr double kPi = 3.14159265358979323846;
using Pts = std::vector<std::pair<double, double>>;

/// Nodos en ángulo paramétrico uniforme; el punto medio del elemento 0 queda en t = 0 (FORMULAS §7).
Pts ellipse_pts(int n, double a, double b, double cx = 0.0, double cy = 0.0, double t0 = 0.0) {
    Pts p;
    for (int k = 0; k < n; ++k) {
        const double t = 2 * kPi * (k - 0.5) / n + t0;
        p.push_back({cx + a * std::cos(t), cy + b * std::sin(t)});
    }
    return p;
}

BemInput input(std::vector<Pts> polys, double s1, double s3, double alpha = 90.0) {
    BemInput in;
    for (auto& p : polys) in.contours.push_back({std::move(p), 0});
    in.sigma1_mpa = s1;
    in.sigma3_mpa = s3;
    in.alpha_deg = alpha;
    in.e_mpa = 10000;
    in.nu = 0.2;
    in.max_element_m = 10;  // un elemento por lado: los nodos ya los da la curva
    return in;
}

double hoop(const BemBoundary& b, std::size_t i) { return b.sigma_tt_mpa[i]; }

/// σr y σθ (compresión positiva) en el ángulo th a partir del tensor cartesiano.
std::pair<double, double> polar(const BemPointStress& s, double th) {
    const double c = std::cos(th), sn = std::sin(th);
    return {s.sxx * c * c + s.syy * sn * sn + 2 * s.sxy * sn * c, s.sxx * sn * sn + s.syy * c * c - 2 * s.sxy * sn * c};
}
}  // namespace

TEST(Bem2d, KirschBordeHidrostatico128) {  // FORMULAS §7.1: Hooke 0.83 %
    const auto b = bem_boundary(bem_solve(input({ellipse_pts(128, 1, 1)}, 30, 30)));
    ASSERT_EQ(b.sigma_tt_mpa.size(), 128u);
    for (std::size_t i = 0; i < 128; ++i) EXPECT_NEAR(hoop(b, i), 60.0, 0.01 * 60.0);
}

TEST(Bem2d, KirschKMedio128) {  // corona 3σh − σv y hastial 3σv − σh; error sobre máx|σθ| = 75 (§7.1: 0.66 %)
    const auto b = bem_boundary(bem_solve(input({ellipse_pts(128, 1, 1)}, 30, 15)));
    const double tol = 0.01 * 75.0;
    EXPECT_NEAR(hoop(b, 0), 3 * 30 - 15, tol);   // hastial (θ = 0)
    EXPECT_NEAR(hoop(b, 32), 3 * 15 - 30, tol);  // corona (θ = 90°)
    for (std::size_t i = 0; i < 128; ++i) {
        const double th = std::atan2(b.y[i], b.x[i]) * 180 / kPi;
        EXPECT_NEAR(hoop(b, i), kirsch_stress(30, 0.5, 1, 1, th).sigma_theta, tol);
    }
}

TEST(Bem2d, KirschCampo64) {  // r = 1.5R y 2R, 72 ángulos, error sobre máx|σθ| (§7.1: ≤ 0.581 %)
    for (double k : {1.0, 0.5}) {
        const auto sol = bem_solve(input({ellipse_pts(64, 1, 1)}, 30, 30 * k));
        for (double r : {1.5, 2.0}) {
            Pts pts;
            for (int i = 0; i < 72; ++i) pts.push_back({r * std::cos(2 * kPi * i / 72), r * std::sin(2 * kPi * i / 72)});
            const auto f = bem_field(sol, pts);
            double err = 0, smax = 0;
            for (int i = 0; i < 72; ++i) {
                const double th = 2 * kPi * i / 72;
                const auto ex = kirsch_stress(30, k, 1, r, th * 180 / kPi);
                const auto [sr, st] = polar(f[i], th);
                EXPECT_FALSE(f[i].inside);
                EXPECT_FALSE(f[i].corrected);
                err = std::max({err, std::abs(sr - ex.sigma_r), std::abs(st - ex.sigma_theta)});
                smax = std::max(smax, std::abs(ex.sigma_theta));
            }
            EXPECT_LT(err / smax, 0.006) << "K " << k << " r " << r;
        }
    }
}

TEST(Bem2d, Rs2Problema1) {  // a = 1, p = 30: 60.25 y 3.62 mm con 256; Richardson 60.00
    const auto s256 = bem_solve(input({ellipse_pts(256, 1, 1)}, 30, 30));
    const auto b256 = bem_boundary(s256);
    const auto b128 = bem_boundary(bem_solve(input({ellipse_pts(128, 1, 1)}, 30, 30)));
    for (std::size_t i = 0; i < 256; ++i) {
        EXPECT_NEAR(hoop(b256, i), 60.25, 0.05);
        const double ur = -(b256.ux_m[i] * b256.x[i] + b256.uy_m[i] * b256.y[i]) / std::hypot(b256.x[i], b256.y[i]);
        EXPECT_NEAR(ur * 1000, 3.62, 0.02);  // convergencia, positiva hacia adentro
    }
    EXPECT_NEAR(2 * hoop(b256, 0) - hoop(b128, 0), 60.00, 0.05);
    EXPECT_EQ(s256.info.method_id, "BEM-DDM-Crouch-Starfield-1983");
    EXPECT_EQ(s256.info.verification, Verification::Secondary);
}

TEST(Bem2d, Elipse256) {  // a = 2, b = 1, σ1 = 20 vertical, σ3 = 10 (§7.3: 90.98 y 0.05)
    const auto b = bem_boundary(bem_solve(input({ellipse_pts(256, 2, 1)}, 20, 10)));
    EXPECT_NEAR(hoop(b, 0), 90.98, 0.1);
    EXPECT_NEAR(hoop(b, 64), 0.05, 0.05);
    for (int k = 16; k < 256; k += 32) {  // 8 puntos intermedios, contra Inglis con ángulo polar
        const double th = std::atan2(b.y[k], b.x[k]) * 180 / kPi;
        EXPECT_NEAR(hoop(b, k), ellipse_boundary_stress(20, 10, 2, 1, th), 0.015 * 90.0) << k;
    }
}

TEST(Bem2d, DosHuecosLing) {  // radio 1, p = 1, gap/r = 1, 512 por hueco (§7.4)
    const int n = 512;
    const auto b = bem_boundary(bem_solve(input({ellipse_pts(n, 1, 1, 1.5, 0), ellipse_pts(n, 1, 1, -1.5, 0, kPi)}, 1, 1)));
    EXPECT_NEAR(hoop(b, n / 2), 2.8875, 0.003 * 2.8875);  // punto del pilar del hueco derecho
    // θ bipolar = π/2 donde x² + y² = α² (α² = 1.25): cos t = −2/3; interpolación lineal entre puntos medios
    const double ts = std::acos(-2.0 / 3.0), step = 2 * kPi / n;
    const int k = static_cast<int>(ts / step);
    const double w = ts / step - k;
    EXPECT_NEAR((1 - w) * hoop(b, k) + w * hoop(b, k + 1), 1.7313, 0.003 * 1.7313);
}

TEST(Bem2d, OrientacionYPuntoDeCierre) {  // test_orientation_and_closing_point
    const Pts ccw = ellipse_pts(128, 1, 1);
    Pts cw(ccw.rbegin(), ccw.rend());
    cw.push_back(cw.front());
    const auto sa = bem_solve(input({ccw}, 30, 15, 70));
    const auto sb = bem_solve(input({cw}, 30, 15, 70));
    ASSERT_EQ(sa.elements.size(), sb.elements.size());
    const auto ba = bem_boundary(sa), bb = bem_boundary(sb);
    for (std::size_t i = 0; i < ba.x.size(); ++i) {
        EXPECT_NEAR(ba.x[i], bb.x[i], 1e-12);
        EXPECT_NEAR(ba.sigma_tt_mpa[i], bb.sigma_tt_mpa[i], 1e-12);
        EXPECT_NEAR(ba.ux_m[i], bb.ux_m[i], 1e-12);
    }
    const Pts pts{{1.5, 0.2}, {-0.3, 2.0}};
    const auto fa = bem_field(sa, pts), fb = bem_field(sb, pts);
    for (std::size_t i = 0; i < pts.size(); ++i) EXPECT_NEAR(fa[i].sigma1, fb[i].sigma1, 1e-12);
}

TEST(Bem2d, PuntoSobreElBorde) {  // test_point_on_boundary
    const Pts poly = ellipse_pts(128, 1, 1);
    const auto sol = bem_solve(input({poly}, 30, 15));
    const auto& e = sol.elements[5];
    const auto f = bem_field(sol, {poly[7], {e.xm, e.ym}, {0.0, 0.0}, {1.02, 0.0}});
    for (int i = 0; i < 2; ++i) {
        EXPECT_FALSE(f[i].inside);
        EXPECT_TRUE(f[i].corrected);
        for (double v : {f[i].sxx, f[i].syy, f[i].sxy, f[i].szz, f[i].sigma1, f[i].sigma3, f[i].angle1_deg})
            EXPECT_TRUE(std::isfinite(v));
    }
    // en el borde la tracción es nula: σ3 ≈ 0 y σ1 = σθ del borde
    EXPECT_NEAR(f[1].sigma3, 0.0, 1e-9);
    EXPECT_NEAR(f[1].sigma1, bem_boundary(sol).sigma_tt_mpa[5], 1e-9);
    EXPECT_TRUE(f[2].inside);  // centro del hueco: enmascarado
    EXPECT_TRUE(std::isnan(f[2].sigma1));
    EXPECT_TRUE(f[3].corrected);  // a menos de un elemento del borde
    EXPECT_NEAR(f[3].sigma1, kirsch_stress(30, 0.5, 1, 1.02, 0).sigma_theta, 0.02 * 75);
}

TEST(Bem2d, CampoInSituYAngulo) {  // lejos del hueco vuelve al campo in situ; α es el ángulo de σ1 desde x
    const auto sol = bem_solve(input({ellipse_pts(64, 1, 1)}, 30, 10, 30));
    const auto f = bem_field(sol, {{200.0, 150.0}});
    EXPECT_NEAR(f[0].sigma1, 30, 0.01);
    EXPECT_NEAR(f[0].sigma3, 10, 0.01);
    EXPECT_NEAR(f[0].angle1_deg, 30, 0.05);
    EXPECT_NEAR(f[0].szz, 0.2 * 40, 0.01);  // deformación plana por omisión
    auto in = input({ellipse_pts(64, 1, 1)}, 30, 10, 30);
    in.sigma_z_mpa = 25;
    EXPECT_NEAR(bem_field(bem_solve(in), {{200.0, 150.0}})[0].szz, 25, 0.01);
}

TEST(Bem2d, UnSoloContornoNoEsSingular) {  // restricción de traslación (§1.5): falló sin ella con 256 y K = 1
    EXPECT_NO_THROW(bem_solve(input({ellipse_pts(256, 1, 1)}, 30, 30)));
}

TEST(Bem2d, Discretizacion) {
    const Pts sq{{0, 0}, {2, 0}, {2, 2}, {0, 2}};
    const auto els = bem_discretize({{sq, 0}}, 0.5);
    ASSERT_EQ(els.size(), 16u);
    for (const auto& e : els) EXPECT_NEAR(e.length, 0.5, 1e-12);
    EXPECT_EQ(bem_discretize({{sq, 6}}, 0.5).size(), 24u);  // la sugerencia sube el número por lado
    const Pts cw{{0, 0}, {0, 2}, {2, 2}, {2, 0}, {0, 0}};
    const auto e2 = bem_discretize({{cw, 0}}, 1.0);
    ASSERT_EQ(e2.size(), 8u);
    double area = 0;
    for (const auto& e : e2) area += e.x1 * e.y2 - e.x2 * e.y1;
    EXPECT_GT(area, 0);  // antihorario
}

TEST(Bem2d, Errores) {
    auto has = [](const std::string& msg, const std::string& name) {
        return msg.find("'" + name + "'") != std::string::npos && msg.find("Received") == std::string::npos;
    };
    EXPECT_TRUE(has(error_of([] { bem_discretize({{{{0, 0}, {1, 0}}, 0}}, 1.0); }), "vertices"));
    EXPECT_TRUE(has(error_of([] { bem_discretize({{{{0, 0}, {1, 0}, {0, 0}}, 0}}, 1.0); }), "vertices"));
    const Pts bow{{0, 0}, {2, 2}, {2, 0}, {0, 2}};  // se cruza a sí mismo
    EXPECT_TRUE(has(error_of([&] { bem_discretize({{bow, 0}}, 1.0); }), "contours"));
    const Pts a{{0, 0}, {2, 0}, {2, 2}, {0, 2}}, b{{1, 1}, {3, 1}, {3, 3}, {1, 3}};
    EXPECT_TRUE(has(error_of([&] { bem_discretize({{a, 0}, {b, 0}}, 1.0); }), "contours"));
    const Pts inner{{0.5, 0.5}, {1, 0.5}, {1, 1}};
    EXPECT_TRUE(has(error_of([&] { bem_discretize({{a, 0}, {inner, 0}}, 1.0); }), "contours"));
    EXPECT_TRUE(has(error_of([] { bem_discretize({}, 1.0); }), "contours"));
    EXPECT_TRUE(has(error_of([&] { bem_discretize({{a, 0}}, 0.0); }), "max_element_m"));
    EXPECT_TRUE(has(error_of([&] { bem_discretize({{a, 0}}, 1e-6); }), "max_element_m"));  // demasiados elementos
    auto bad = input({a}, 30, 15);
    bad.e_mpa = 0;
    EXPECT_TRUE(has(error_of([&] { bem_solve(bad); }), "e_mpa"));
    for (double nu : {-0.1, 0.5, 0.7}) {
        bad = input({a}, 30, 15);
        bad.nu = nu;
        EXPECT_TRUE(has(error_of([&] { bem_solve(bad); }), "nu"));
    }
    EXPECT_TRUE(has(error_of([&] { bem_solve(input({a}, 10, 15)); }), "sigma3_mpa"));
    BemInput blank;
    blank.contours = {{a, 0}};
    EXPECT_FALSE(error_of([&] { bem_solve(blank); }).empty());
}

TEST(Bem2d, Rendimiento) {  // 2 contornos × 256 elementos; meta < 2 s (se mide, la prueba solo exige que termine)
    const auto t0 = std::chrono::steady_clock::now();
    const auto sol = bem_solve(input({ellipse_pts(256, 1, 1, 3, 0), ellipse_pts(256, 1, 1, -3, 0)}, 30, 15));
    const auto b = bem_boundary(sol);
    const double s = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    std::cout << "[bem2d] 2 x 256 elementos: " << s << " s\n";
    EXPECT_EQ(b.sigma_tt_mpa.size(), 512u);
}
