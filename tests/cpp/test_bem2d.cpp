#include <gtest/gtest.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <iostream>
#include <limits>
#include <tuple>
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
    bad.e_mpa = std::numeric_limits<double>::quiet_NaN();
    EXPECT_TRUE(has(error_of([&] { bem_solve(bad); }), "e_mpa"));
    EXPECT_TRUE(has(error_of([&] { bem_discretize({{a, 2000}}, 1.0); }), "elements_per_side_hint"));
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

namespace {
Pts rect(double x0, double x1, double y0, double y1) { return {{x0, y0}, {x1, y0}, {x1, y1}, {x0, y1}}; }

/// Dos cámaras de ancho bw y alto h con un pilar de ancho w; perfil horizontal y vertical por el pilar.
std::vector<BemPointStress> pillar(double w, double el, double bw, double h) {
    auto in = input({rect(-w / 2 - bw, -w / 2, -h / 2, h / 2), rect(w / 2, w / 2 + bw, -h / 2, h / 2)}, 30, 15);
    in.max_element_m = el;
    Pts pts;
    for (int i = 0; i <= 60; ++i) pts.push_back({-w / 2 - bw - 3 + (w + 2 * bw + 6) * i / 60.0, 0.0});
    for (int i = 0; i <= 20; ++i) pts.push_back({0.0, -h / 2 + h * i / 20.0});
    return bem_field(bem_solve(in), pts);
}
bool all_finite(const BemPointStress& p) {
    for (double v : {p.sxx, p.syy, p.sxy, p.szz, p.sigma1, p.sigma3, p.angle1_deg})
        if (!std::isfinite(v)) return false;
    return true;
}
}  // namespace

TEST(Bem2d, PilarAngostoSinNaN) {  // revisión: Q del remedio caía en la otra cámara (NaN o valor sin sentido)
    for (auto [w, el, bw, h] : {std::tuple{1.0, 1.0, 4.0, 4.0}, std::tuple{0.5, 1.0, 4.0, 4.0},
                                std::tuple{3.0, 3.0, 5.0, 6.0}}) {
        const auto f = pillar(w, el, bw, h);
        int coarse = 0;
        for (const auto& p : f) {
            if (p.inside) continue;
            EXPECT_TRUE(all_finite(p)) << w << " " << el;
            EXPECT_FALSE(p.coarse && p.corrected);
            coarse += p.coarse;
        }
        EXPECT_GT(coarse, 0) << w << " " << el;
        EXPECT_TRUE(f[61 + 10].coarse);  // centro del pilar
    }
}

TEST(Bem2d, PilarConMallaFinaSinCambio) {  // L = 0.25: el remedio cabe; centro del pilar 81.683 como antes
    const auto f = pillar(1.0, 0.25, 4.0, 4.0);
    for (const auto& p : f) EXPECT_FALSE(p.coarse);
    EXPECT_NEAR(f[61 + 10].syy, 81.683, 0.001);
}

TEST(Bem2d, Rendimiento) {  // 2 contornos × 256 elementos; meta < 2 s (se mide, la prueba solo exige que termine)
    const auto t0 = std::chrono::steady_clock::now();
    const auto sol = bem_solve(input({ellipse_pts(256, 1, 1, 3, 0), ellipse_pts(256, 1, 1, -3, 0)}, 30, 15));
    const auto b = bem_boundary(sol);
    const double s = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    std::cout << "[bem2d] 2 x 256 elementos: " << s << " s\n";
    EXPECT_EQ(b.sigma_tt_mpa.size(), 512u);
}

// ---- Strength factor (FORMULAS §3) ----
namespace {
SfMaterial mc(double c, double phi, double t = 0.0) {
    SfMaterial m;
    m.criterion = SfCriterion::MohrCoulomb;
    m.c_mpa = c;
    m.phi_deg = phi;
    m.tensile_mpa = t;
    return m;
}
SfMaterial hb(double mb, double s, double sci, double a = 0.5) {
    SfMaterial m;
    m.criterion = SfCriterion::HoekBrown;
    m.mb = mb;
    m.s = s;
    m.sigma_ci_mpa = sci;
    m.a = a;
    return m;
}
}  // namespace

TEST(StrengthFactor, SobreLaEnvolventeDaUno) {  // §3.2: SF = 1 con σ2 = σ3, σ1 y el promedio
    const double nphi = 3.0;  // φ = 30°
    for (double s3 : {0.0, 5.0, 20.0}) {
        const double s1m = s3 * nphi + 2 * 5 * std::sqrt(nphi), s1h = s3 + 100 * std::sqrt(10 * s3 / 100 + 1);
        for (auto [m, s1] : {std::pair{mc(5, 30), s1m}, std::pair{hb(10, 1, 100), s1h}})
            for (double s2 : {s3, s1, (s1 + s3) / 2})
                for (auto mode : {SfMode::RS2, SfMode::Examine2D}) {
                    const auto r = strength_factor(m, s1, s3, s2, mode);
                    ASSERT_TRUE(r.sf.has_value());
                    EXPECT_FALSE(r.tension);
                    EXPECT_NEAR(*r.sf, 1.0, 1e-9) << s3 << " " << s2;
                }
    }
}

TEST(StrengthFactor, EjemploRs2Y2D) {  // §3.3: σ1 = 40, σ3 = 10, σz = 10
    EXPECT_NEAR(strength_factor(mc(5, 30), 40, 10, 10, SfMode::RS2).sf.value(), 1.146, 0.001);
    EXPECT_NEAR(strength_factor(mc(5, 30), 40, 10, 10, SfMode::Examine2D).sf.value(), 1.122, 0.001);
    EXPECT_NEAR(strength_factor(hb(10, 1, 100), 40, 10, 10, SfMode::RS2).sf.value(), 2.457, 0.001);
    EXPECT_NEAR(strength_factor(hb(10, 1, 100), 40, 10, 10, SfMode::Examine2D).sf.value(), 2.075, 0.001);
}

TEST(StrengthFactor, ThetaPorAtanIgualQueAsin) {  // valores del prototipo sf.py (asin de J3) con Θ intermedio
    for (auto [s2, emc, ehb] : {std::tuple{17.0, 1.1339117330918675, 2.251652952653475},
                                std::tuple{33.0, 1.1120485929952364, 1.9402879793320835}}) {
        EXPECT_NEAR(strength_factor(mc(5, 30), 40, 10, s2, SfMode::RS2).sf.value(), emc, 1e-9);
        EXPECT_NEAR(strength_factor(hb(10, 1, 100), 40, 10, s2, SfMode::RS2).sf.value(), ehb, 1e-9);
    }
    EXPECT_NEAR(strength_factor(mc(5, 30, 5), 25, -3, 8, SfMode::RS2).sf.value(), 0.6911205199201623, 1e-9);
    EXPECT_NEAR(strength_factor(hb(10, 1, 100), 25, -3, 8, SfMode::RS2).sf.value(), 1.4173163179020543, 1e-9);
}

TEST(StrengthFactor, Traccion) {  // §3.4: σ3 < −T marca tracción y no da SF; HB: T = s·σci/mb = 10
    for (auto mode : {SfMode::RS2, SfMode::Examine2D}) {
        auto r = strength_factor(mc(5, 30, 1.0), 20, -1.5, 2, mode);
        EXPECT_TRUE(r.tension);
        EXPECT_FALSE(r.sf.has_value());
        r = strength_factor(mc(5, 30, 1.0), 20, -0.5, 2, mode);
        EXPECT_FALSE(r.tension);
        EXPECT_TRUE(r.sf.has_value());
        for (double a : {0.5, 0.55}) {
            r = strength_factor(hb(10, 1, 100, a), 20, -10.5, 2, mode);
            EXPECT_TRUE(r.tension);
            EXPECT_FALSE(r.sf.has_value());
            r = strength_factor(hb(10, 1, 100, a), 20, -9.5, 2, mode);
            EXPECT_FALSE(r.tension);
            ASSERT_TRUE(r.sf.has_value());
            EXPECT_GT(*r.sf, 0.0);
        }
    }
}

TEST(StrengthFactor, TraccionTopadaEnElVertice) {  // revisión: T > c·cot φ usa el vértice como corte, no SF = 0
    for (auto mode : {SfMode::RS2, SfMode::Examine2D}) {
        auto r = strength_factor(mc(0, 30, 1.0), 0.2, -0.8, -0.3, mode);  // c = 0: el vértice está en 0
        EXPECT_TRUE(r.tension);
        EXPECT_FALSE(r.sf.has_value());
        r = strength_factor(mc(1, 30, 5.0), 2, -1.7, -1.0, mode);  // c·cot φ = 1.732: justo dentro del vértice
        EXPECT_FALSE(r.tension);
        ASSERT_TRUE(r.sf.has_value());
        EXPECT_GT(*r.sf, 0.0);
        EXPECT_TRUE(std::isfinite(*r.sf));
        r = strength_factor(mc(1, 30, 5.0), 2, -1.8, -1.0, mode);  // pasa el vértice: tracción aunque T = 5
        EXPECT_TRUE(r.tension);
        EXPECT_FALSE(r.sf.has_value());
        r = strength_factor(mc(1, 0, 5.0), 2, -4.0, -1.0, mode);  // φ = 0: sin vértice, rige T
        EXPECT_FALSE(r.tension);
        r = strength_factor(mc(1, 0, 5.0), 2, -5.5, -1.0, mode);
        EXPECT_TRUE(r.tension);
    }
}

TEST(StrengthFactor, HidrostaticoEsInfinito) {  // sin desviador no hay corte: SF = +inf
    for (auto mode : {SfMode::RS2, SfMode::Examine2D}) {
        EXPECT_TRUE(std::isinf(strength_factor(mc(5, 30), 10, 10, 10, mode).sf.value()));
        EXPECT_TRUE(std::isinf(strength_factor(hb(10, 1, 100, 0.55), 10, 10, 10, mode).sf.value()));
    }
}

TEST(StrengthFactor, test_hb_general_matches_closed_form) {
    using bem2d_detail::hb_scaled_sf;
    const auto m5 = hb(10, 1, 100);
    for (auto [s1, s3, s2] : {std::tuple{40.0, 10.0, 10.0}, std::tuple{80.0, 2.0, 30.0}, std::tuple{15.0, -5.0, 0.0},
                              std::tuple{200.0, 30.0, 200.0}}) {
        const double closed = strength_factor(m5, s1, s3, s2, SfMode::RS2).sf.value();
        EXPECT_NEAR(hb_scaled_sf(m5, s1, s3, s2), closed, 1e-6) << s1;
        EXPECT_LT(std::abs(strength_factor(hb(10, 1, 100, 0.5001), s1, s3, s2, SfMode::RS2).sf.value() - closed), 1e-3);
    }
    const auto m55 = hb(10, 0.5, 100, 0.55);  // sobre la envolvente generalizada: SF = 1
    for (double s3 : {0.0, 5.0, 20.0}) {
        const double s1 = s3 + 100 * std::pow(10 * s3 / 100 + 0.5, 0.55);
        for (double s2 : {s3, s1, (s1 + s3) / 2})
            for (auto mode : {SfMode::RS2, SfMode::Examine2D})
                EXPECT_NEAR(strength_factor(m55, s1, s3, s2, mode).sf.value(), 1.0, 1e-6) << s3 << " " << s2;
    }
}

TEST(StrengthFactor, test_zero_horizontal_stress) {  // K = 0: la corona del círculo queda en tracción (MC, T = 0)
    const auto sol = bem_solve(input({ellipse_pts(128, 1, 1)}, 30, 0));
    const auto f = bem_field(sol, {{0.0, 1.1}, {0.0, -1.1}, {1.1, 0.0}, {0.0, 0.0}});
    const auto r = bem_strength_factor(f, mc(5, 30), SfMode::RS2);
    ASSERT_EQ(r.size(), 4u);
    EXPECT_TRUE(r[0].tension);
    EXPECT_TRUE(r[1].tension);
    EXPECT_FALSE(r[0].sf.has_value());
    EXPECT_FALSE(r[2].tension);  // hastial: compresión alta
    ASSERT_TRUE(r[2].sf.has_value());
    EXPECT_GT(*r[2].sf, 0.0);
    EXPECT_FALSE(r[3].tension);  // dentro de la excavación
    EXPECT_FALSE(r[3].sf.has_value());
}

TEST(StrengthFactor, ValidacionSinValores) {
    for (auto m : {mc(-1, 30), mc(5, 95), mc(5, 30, -0.25), hb(-7.5, 1, 100), hb(10, 1.25, 100), hb(10, 1, -3.5),
                   hb(10, 1, 100, 1.75)}) {
        const auto msg = error_of([&] { strength_factor(m, 40, 10, 10, SfMode::RS2); });
        EXPECT_NE(msg.find("Domain error"), std::string::npos);
        for (const char* v : {"-1", "95", "0.25", "7.5", "1.25", "3.5", "1.75"}) EXPECT_EQ(msg.find(v), std::string::npos) << msg;
    }
    EXPECT_NE(error_of([] { strength_factor(mc(5, 30), std::nan(""), 10, 10, SfMode::RS2); }).find("sigma1"),
              std::string::npos);
}

TEST(StrengthFactor, Info) {
    EXPECT_EQ(strength_factor_info(SfMode::RS2).method_id, "SF-RS2-3D");
    EXPECT_EQ(strength_factor_info(SfMode::RS2).verification, Verification::PrimaryLaterAuthors);
    EXPECT_EQ(strength_factor_info(SfMode::Examine2D).method_id, "SF-2D-Examine2D");
    EXPECT_EQ(strength_factor_info(SfMode::Examine2D).verification, Verification::Secondary);
}
