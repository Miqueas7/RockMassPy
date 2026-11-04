#include <gtest/gtest.h>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <limits>
#include <random>
#include <string>

#include "error_of.hpp"
#include "rockmasspy/limit_equilibrium.hpp"

using namespace rockmasspy;

namespace {
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
LeSection one_layer(std::vector<Point2> surface, LeMaterial m) {
    LeSection s;
    s.surface = std::move(surface);
    s.layers = {LeLayer{{}, 0}};
    s.materials = {m};
    return s;
}
SlipSurface circle(double xc, double yc, double r) {
    SlipSurface f;
    f.circle = Circle{xc, yc, r};
    return f;
}
SlipSurface polyline(std::vector<Point2> p) {
    SlipSurface f;
    f.polyline = std::move(p);
    return f;
}
LeOptions opts(int n) {
    LeOptions o;
    o.n_slices = n;
    return o;
}
LeResult run(const LeSection& s, const SlipSurface& f, LeMethod m, int n = 50) {
    return le_factor_of_safety(s, f, m, opts(n));
}
double fs(const LeSection& s, const SlipSurface& f, LeMethod m, int n = 50) {
    const auto r = run(s, f, m, n);
    EXPECT_TRUE(r.factor_of_safety.has_value()) << le_detail::name(m);
    return r.factor_of_safety.value_or(kNan);
}

// Slide2 Verification Manual (2022), problema 21: Fredlund y Krahn (1977), unidades imperiales (psf, pcf, ft)
LeSection fk(double ru = 0.0) { return one_layer({{0, 60}, {60, 60}, {140, 20}, {180, 20}}, mc(120, 600, 20, ru)); }
SlipSurface fk_circle() { return circle(120, 90, 80); }

// ACADS 1(a), Slide problema 1: la cara mira a la izquierda; círculo crítico recalculado (30.16, 51.9, 26.9)
LeSection acads1a() {
    auto s = one_layer({{20, 25}, {30, 25}, {50, 35}, {70, 35}}, mc(20, 3, 19.6));
    s.model_base_y = 20;
    return s;
}

// ACADS 3(b), Slide problema 8: capa débil entre y = 26.5 y 27.0; superficie de la Tabla 8.2
LeSection acads3b() {
    LeSection s;
    s.surface = {{20, 27.75}, {43, 27.75}, {67.5, 40}, {84, 40}};
    s.materials = {mc(18.84, 28.5, 20), mc(18.84, 0, 10)};
    s.layers = {LeLayer{{{20, 27.0}, {63.5, 27.0}, {84, 27.0}}, 0}, LeLayer{{{20, 26.5}, {84, 26.5}}, 1}, LeLayer{{}, 0}};
    s.model_base_y = 20;
    return s;
}
std::vector<Point2> acads3b_slip() { return {{41.85, 27.75}, {44.0, 26.5}, {63.5, 27.0}, {73.31, 40.0}}; }

LeSection mirrored(LeSection s) {
    s.surface = mirror(s.surface);
    for (auto& l : s.layers)
        if (!l.bottom.empty()) l.bottom = mirror(l.bottom);
    return s;
}

const LeMethod kMethods[] = {LeMethod::Ordinary, LeMethod::Bishop, LeMethod::JanbuSimplified, LeMethod::Spencer,
                             LeMethod::MorgensternPrice};
}  // namespace

// Publicado F&K / recalculado con 400 tajadas. El Ordinario de Slide con ru (1.687) resta u de otra forma; manda F&K
// (N' = W cos α - u l, R3, con el recorte N' >= 0), que da 1.607.
TEST(LimitEquilibrium, FredlundKrahnDryAndRu) {
    struct Case { LeMethod m; double pub_dry, re_dry, pub_ru, re_ru; };
    const Case cases[] = {{LeMethod::Ordinary, 1.928, 1.9277, 1.607, 1.6062},
                          {LeMethod::Bishop, 2.080, 2.0756, 1.766, 1.7592},
                          {LeMethod::Spencer, 2.073, 2.0718, 1.761, 1.7574},
                          {LeMethod::MorgensternPrice, 2.076, 2.0714, 1.764, 1.7567}};
    for (int n : {50, 400})
        for (const auto& c : cases) {
            const double dry = fs(fk(), fk_circle(), c.m, n), wet = fs(fk(0.25), fk_circle(), c.m, n);
            EXPECT_NEAR(dry, c.pub_dry, 0.005 * c.pub_dry) << le_detail::name(c.m) << " n " << n;
            EXPECT_NEAR(dry, c.re_dry, 1e-3) << le_detail::name(c.m) << " n " << n;
            EXPECT_NEAR(wet, c.pub_ru, 0.005 * c.pub_ru) << le_detail::name(c.m) << " n " << n;
            // el Ordinario con ru va aparte (FredlundKrahnOrdinaryRuRecalculated)
            if (c.m != LeMethod::Ordinary) EXPECT_NEAR(wet, c.re_ru, 1e-3) << le_detail::name(c.m) << " n " << n;
        }
    const auto sp = run(fk(), fk_circle(), LeMethod::Spencer, 400);
    EXPECT_NEAR(*sp.lambda, 0.258, 2e-3);
    const auto mp = run(fk(), fk_circle(), LeMethod::MorgensternPrice, 400);
    EXPECT_NEAR(*mp.lambda, 0.323, 2e-3);
    EXPECT_TRUE(mp.converged);
    EXPECT_TRUE(mp.warnings.empty());
    // con ru, el Ordinario recorta N' < 0 cerca de la cresta y lo dice en una nota
    const auto ord = run(fk(0.25), fk_circle(), LeMethod::Ordinary);
    ASSERT_EQ(ord.notes.size(), 1u);
    EXPECT_NE(ord.notes[0].find("friction taken as zero"), std::string::npos);
    EXPECT_TRUE(run(fk(), fk_circle(), LeMethod::Ordinary).notes.empty());
}

// Ordinario con ru: N' = (W cos α - kh W sin α - u l)⁺ con nota (el recorte actúa cerca de la cresta). Recalculado con
// el recorte y 400 tajadas: 1.6073 (sin recorte saldría 1.6062); con 50 tajadas basta el ±0.5 % del 1.607 de F&K.
TEST(LimitEquilibrium, FredlundKrahnOrdinaryRuRecalculated) {
    EXPECT_NEAR(fs(fk(0.25), fk_circle(), LeMethod::Ordinary, 400), 1.6073, 1e-3);
}

TEST(LimitEquilibrium, Acads1aFixedCircle) {
    const auto f = circle(30.16, 51.9, 26.9);
    const double b = fs(acads1a(), f, LeMethod::Bishop), s = fs(acads1a(), f, LeMethod::Spencer),
                 m = fs(acads1a(), f, LeMethod::MorgensternPrice);
    EXPECT_NEAR(b, 0.9857, 2e-3);
    EXPECT_NEAR(s, 0.9846, 2e-3);
    EXPECT_NEAR(m, 0.9846, 2e-3);
    EXPECT_NEAR(b, 0.987, 0.01 * 0.987);
    EXPECT_NEAR(s, 0.986, 0.01 * 0.986);
    EXPECT_NEAR(m, 0.986, 0.01 * 0.986);
}

// El tramo de la base entre x = 43.14 y 44 (donde la superficie dada baja de 27.0 a 26.5) cae en la capa débil.
// Oráculo: lo recalculado asignando la capa débil por la cota de la base (Spencer 1.2758, M-P medio seno 1.2601) y
// Slide (1.277 y 1.262). La referencia ACADS 1.34 solo se anota: con los estratos no se reproduce (-4.8 %).
TEST(LimitEquilibrium, Acads3bGivenSurface) {
    const auto f = polyline(acads3b_slip());
    const double s = fs(acads3b(), f, LeMethod::Spencer), m = fs(acads3b(), f, LeMethod::MorgensternPrice);
    EXPECT_NEAR(s, 1.2758, 3e-3);
    EXPECT_NEAR(m, 1.2601, 3e-3);
    EXPECT_NEAR(s, 1.277, 0.005 * 1.277);
    EXPECT_NEAR(m, 1.262, 0.005 * 1.262);
}

TEST(LimitEquilibrium, ReflectedSectionGivesSameFsAndLambda) {
    const auto f3 = acads3b_slip();
    struct Pair { LeSection a, b; SlipSurface fa, fb; };
    const Pair pairs[] = {{fk(), mirrored(fk()), fk_circle(), circle(-120, 90, 80)},
                          {fk(0.25), mirrored(fk(0.25)), fk_circle(), circle(-120, 90, 80)},
                          {acads3b(), mirrored(acads3b()), polyline(f3), polyline(mirror(f3))}};
    for (const auto& p : pairs)
        for (LeMethod m : kMethods) {
            const auto ra = run(p.a, p.fa, m), rb = run(p.b, p.fb, m);
            ASSERT_TRUE(ra.factor_of_safety && rb.factor_of_safety) << le_detail::name(m);
            EXPECT_NEAR(*rb.factor_of_safety, *ra.factor_of_safety, 1e-9 * *ra.factor_of_safety) << le_detail::name(m);
            if (ra.lambda) {
                ASSERT_TRUE(rb.lambda.has_value());
                EXPECT_NEAR(*rb.lambda, *ra.lambda, 1e-9 * std::fabs(*ra.lambda));
            }
            EXPECT_NEAR(rb.sliding_mass_area, ra.sliding_mass_area, 1e-9 * ra.sliding_mass_area);
            // la tabla sale en las coordenadas de cada sección, de izquierda a derecha
            EXPECT_NEAR(rb.slices.front().x_left, -ra.slices.back().x_right, 1e-9);
            EXPECT_LT(rb.slices.front().x_left, rb.slices.back().x_right);
        }
}

TEST(LimitEquilibrium, WeightsAndSlices) {
    const auto a = run(fk(), fk_circle(), LeMethod::Bishop, 50), b = run(fk(), fk_circle(), LeMethod::Bishop, 400);
    EXPECT_NEAR(a.sliding_mass_area, b.sliding_mass_area, 1e-3 * b.sliding_mass_area);
    EXPECT_NEAR(b.sliding_mass_area, 2145.66, 0.5);  // prototipo con 400 tajadas: 2145.657
    double w = 0.0;
    for (const auto& t : a.slices) w += t.weight;
    EXPECT_NEAR(w, 120.0 * a.sliding_mass_area, 1e-9 * w);
    const auto sl = make_slices(fk(), fk_circle(), 50);
    EXPECT_GE(sl.size(), 45u);
    EXPECT_LE(sl.size(), 55u);
    for (std::size_t i = 1; i < sl.size(); ++i) EXPECT_DOUBLE_EQ(sl[i].x_left, sl[i - 1].x_right);
    // los vértices de la superficie (60 y 140) son bordes de tajada
    int hits = 0;
    for (const auto& t : sl) hits += (t.x_left == 60.0) + (t.x_left == 140.0);
    EXPECT_EQ(hits, 2);
    // con capas, el peso es la suma por estrato: una capa de γ doble arriba
    LeSection two = fk();
    two.materials.push_back(mc(240, 600, 20));
    two.layers = {LeLayer{{{0, 50}, {180, 50}}, 1}, LeLayer{{}, 0}};
    double w2 = 0.0;
    for (const auto& t : make_slices(two, fk_circle(), 400)) w2 += t.weight;
    EXPECT_GT(w2, w);
    auto zero = fk();
    zero.materials[0].unit_weight = 0.0;
    EXPECT_NE(error_of([&] { run(zero, fk_circle(), LeMethod::Bishop); }).find("materials[0].unit_weight"),
              std::string::npos);
}

TEST(LimitEquilibrium, OddSurfaces) {
    EXPECT_NE(error_of([] { run(fk(), circle(120, 200, 50), LeMethod::Bishop); })
                  .find("slip surface does not cut the ground surface twice"),
              std::string::npos);
    EXPECT_NE(error_of([] { run(fk(), polyline({{40, 60}, {100, 30}, {90, 25}, {150, 20}}), LeMethod::Spencer); })
                  .find("polyline"),
              std::string::npos);
    EXPECT_NE(error_of([] { run(fk(), polyline({{50, 50}, {100, 25}, {150, 20}}), LeMethod::Spencer); })
                  .find("polyline"),
              std::string::npos);
    // sale por la base del modelo
    auto low = acads1a();
    low.model_base_y = 30;
    EXPECT_NE(error_of([&] { run(low, circle(30.16, 51.9, 26.9), LeMethod::Bishop); }).find("model_base_y"),
              std::string::npos);
    // vértice de un contacto justo sobre la polilínea y corrido 1e-12
    auto moved = acads3b_slip();
    moved[2].x += 1e-12;
    for (LeMethod m : kMethods) {
        const double a = fs(acads3b(), polyline(acads3b_slip()), m), b = fs(acads3b(), polyline(moved), m);
        EXPECT_NEAR(a, b, 1e-9) << le_detail::name(m);
    }
    // más de dos cortes: la masa va del primero al último, con aviso
    auto notch = one_layer({{0, 60}, {60, 60}, {90, 45}, {95, 10}, {100, 40}, {140, 20}, {180, 20}}, mc(120, 600, 20));
    const auto r = run(notch, fk_circle(), LeMethod::Bishop);
    ASSERT_TRUE(r.factor_of_safety.has_value());
    ASSERT_EQ(r.warnings.size(), 1u);
    EXPECT_NE(r.warnings[0].find("more than twice"), std::string::npos);
    EXPECT_TRUE(run(fk(), fk_circle(), LeMethod::Bishop).warnings.empty());
    // superficie horizontal en los dos extremos de la masa
    EXPECT_NE(error_of([] { run(one_layer({{0, 10}, {100, 10}}, mc(20, 10, 30)), circle(50, 30, 25), LeMethod::Bishop); })
                  .find("face direction"),
              std::string::npos);
}

TEST(LimitEquilibrium, BackwardMassAndConvergence) {
    // la cara mira a la derecha (la masa termina más abajo a la derecha), pero el peso cae del lado que sube:
    // la masa giraría hacia atrás
    const auto s = one_layer({{-20, 50}, {12, 50}, {13, 70}, {22, 70}, {22.5, 45}, {60, 45}}, mc(20, 10, 30));
    for (LeMethod m : kMethods) {
        const auto r = run(s, circle(12, 65, 20), m);
        EXPECT_FALSE(r.factor_of_safety.has_value()) << le_detail::name(m);
        EXPECT_FALSE(r.converged);
        ASSERT_EQ(r.notes.size(), 1u);
        EXPECT_EQ(r.notes[0], "the sliding mass does not move towards the face");
        EXPECT_TRUE(r.warnings.empty());
    }
    auto o = opts(50);
    o.max_iterations = 1;
    const auto r = le_factor_of_safety(fk(), fk_circle(), LeMethod::Spencer, o);
    EXPECT_FALSE(r.factor_of_safety.has_value());
    EXPECT_FALSE(r.lambda.has_value());
    EXPECT_FALSE(r.converged);
    ASSERT_EQ(r.warnings.size(), 1u);
    EXPECT_EQ(r.warnings[0], "Spencer did not converge");
    const auto rb = le_factor_of_safety(fk(), fk_circle(), LeMethod::Bishop, o);
    EXPECT_FALSE(rb.factor_of_safety.has_value());
    EXPECT_EQ(rb.warnings[0], "Bishop did not converge");
}

// Con Spencer convergido, la masa entera queda en equilibrio de fuerzas y de momentos (W por el punto medio de la
// base y kh W en el centroide, como en Zhu et al. 2005): comprueba los signos de kh en R, T y λ.
TEST(LimitEquilibrium, SpencerGlobalEquilibriumWithKh) {
    using namespace le_detail;
    auto s = fk();
    s.kh = 0.1;
    LeOptions o = opts(200);
    o.tolerance = 1e-12;
    auto b = build(s, fk_circle(), o.n_slices);
    auto& sl = b.slices;
    const Solve r = gle(sl, s, o, true, false, 1.5);
    ASSERT_TRUE(r.converged);
    double H = 0, V = 0, M = 0, scale = 0;
    const double ox = 77.0, oy = 33.0;  // un punto cualquiera
    for (const auto& t : sl) {
        const double N = t.Np + t.u * t.l, S = (t.c * t.l + t.Np * t.tf) / *r.F;
        const double fx = N * t.sa - S * t.ca, fy = N * t.ca + S * t.sa;
        const double mx = 0.5 * (t.xa + t.xb), my = 0.5 * (t.ya + t.yb);
        H += fx + s.kh * t.W;
        V += fy - t.W;
        M += (mx - ox) * fy - (my - oy) * fx + (mx - ox) * (-t.W) - (t.yg - oy) * (s.kh * t.W);
        scale += t.W * std::fabs(mx - ox);
    }
    double W = 0;
    for (const auto& t : sl) W += t.W;
    EXPECT_NEAR(H / W, 0.0, 1e-8);
    EXPECT_NEAR(V / W, 0.0, 1e-8);
    EXPECT_NEAR(M / scale, 0.0, 1e-8);
}

TEST(LimitEquilibrium, SeismicCoefficient) {
    auto s = fk();
    s.kh = 0.1;
    for (LeMethod m : kMethods) {
        EXPECT_LT(fs(s, fk_circle(), m), fs(fk(), fk_circle(), m)) << le_detail::name(m);
        auto z = fk();
        z.kh = 0.0;
        EXPECT_EQ(fs(z, fk_circle(), m), fs(fk(), fk_circle(), m));
    }
}

TEST(LimitEquilibrium, InvalidInputsNameTheField) {
    auto has = [](const std::function<void()>& f, const std::string& what) {
        const std::string e = error_of(f);
        EXPECT_NE(e.find(what), std::string::npos) << "expected '" << what << "' in: " << e;
    };
    auto bad = [&](auto edit, const std::string& what) {
        auto s = fk();
        auto f = fk_circle();
        auto o = opts(50);
        edit(s, f, o);
        has([&] { le_factor_of_safety(s, f, LeMethod::Bishop, o); }, what);
    };
    bad([](LeSection& s, SlipSurface&, LeOptions&) { s.surface[1].y = kNan; }, "surface[1].y");
    bad([](LeSection& s, SlipSurface&, LeOptions&) { s.materials[0].cohesion = kNan; }, "materials[0].cohesion");
    bad([](LeSection& s, SlipSurface&, LeOptions&) { s.materials[0].friction_deg = kNan; }, "materials[0].friction_deg");
    bad([](LeSection& s, SlipSurface&, LeOptions&) { s.materials[0].unit_weight = kNan; }, "materials[0].unit_weight");
    bad([](LeSection& s, SlipSurface&, LeOptions&) { s.materials[0].ru = kNan; }, "materials[0].ru");
    bad([](LeSection& s, SlipSurface&, LeOptions&) { s.materials[0].ru = 1.0; }, "materials[0].ru");
    bad([](LeSection& s, SlipSurface&, LeOptions&) { s.kh = kNan; }, "kh");
    bad([](LeSection& s, SlipSurface&, LeOptions&) { s.kh = -0.1; }, "kh");
    bad([](LeSection& s, SlipSurface&, LeOptions&) { s.water_unit_weight = kNan; }, "water_unit_weight");
    bad([](LeSection& s, SlipSurface&, LeOptions&) { s.model_base_y = kNan; }, "model_base_y");
    bad([](LeSection& s, SlipSurface&, LeOptions&) { s.crack = LeTensionCrack{2.0, 1.5}; }, "crack.water_fill");
    bad([](LeSection& s, SlipSurface&, LeOptions&) { s.crack = LeTensionCrack{kNan, 0.0}; }, "crack.depth_m");
    bad([](LeSection& s, SlipSurface&, LeOptions&) { s.layers[0].material = 3; }, "layers[0].material");
    bad([](LeSection& s, SlipSurface&, LeOptions&) { s.layers = {LeLayer{{}, 0}, LeLayer{{}, 0}}; }, "layers[0].bottom");
    bad([](LeSection&, SlipSurface& f, LeOptions&) { f.circle->radius = kNan; }, "circle.radius");
    bad([](LeSection&, SlipSurface& f, LeOptions&) { f.circle->xc = kNan; }, "circle.xc");
    bad([](LeSection&, SlipSurface& f, LeOptions&) { f.polyline = std::vector<Point2>{{0, 1}, {2, 3}}; }, "exactly one");
    bad([](LeSection&, SlipSurface&, LeOptions& o) { o.n_slices = 4; }, "n_slices");
    bad([](LeSection&, SlipSurface&, LeOptions& o) { o.tolerance = kNan; }, "tolerance");
    bad([](LeSection&, SlipSurface&, LeOptions& o) { o.function = InterSliceFunction::Points; }, "function_points");
    bad([](LeSection&, SlipSurface&, LeOptions& o) {
        o.function = InterSliceFunction::Points;
        o.function_points = {{0, 1}, {1, -0.5}};
    }, "function_points[1].y");
    bad([](LeSection& s, SlipSurface&, LeOptions&) { s.materials[0].model = StrengthModel::HoekBrown; }, "materials[0].hb");
    bad([](LeSection& s, SlipSurface&, LeOptions&) {
        s.materials[0].model = StrengthModel::HoekBrown;
        s.materials[0].hb = hb_params(50, 10, 0);
    }, "materials[0].sigma_ci");
    bad([](LeSection& s, SlipSurface&, LeOptions&) { s.piezometric = std::vector<Point2>{{0, 50}, {180, kNan}}; },
        "piezometric[1].y");
    bad([](LeSection& s, SlipSurface&, LeOptions&) { s.piezometric = std::vector<Point2>{{50, 50}, {180, 10}}; },
        "piezometric");
    bad([](LeSection& s, SlipSurface&, LeOptions&) {
        s.materials[0].model = StrengthModel::HoekBrown;
        s.materials[0].hb = hb_params(50, 10, 0);
        s.materials[0].sigma_ci = 50.0;
        s.materials[0].hb->mb = -1.0;
    }, "materials[0].hb.mb");
    bad([](LeSection& s, SlipSurface&, LeOptions&) {
        s.materials[0].model = StrengthModel::HoekBrown;
        s.materials[0].hb = hb_params(50, 10, 0);
        s.materials[0].sigma_ci = 50.0;
        s.materials[0].hb->a = kNan;
    }, "materials[0].hb.a");
    bad([](LeSection& s, SlipSurface&, LeOptions&) {
        s.materials[0].model = StrengthModel::HoekBrown;
        s.materials[0].hb = hb_params(50, 10, 0);
        s.materials[0].sigma_ci = kNan;
    }, "materials[0].sigma_ci");
}

TEST(LimitEquilibrium, InterSliceFunctions) {
    // función por puntos constante = Spencer; medio seno por puntos ≈ medio seno
    LeOptions o = opts(50);
    o.function = InterSliceFunction::Points;
    o.function_points = {{0, 1}, {1, 1}};
    const double sp = fs(fk(), fk_circle(), LeMethod::Spencer);
    EXPECT_NEAR(*le_factor_of_safety(fk(), fk_circle(), LeMethod::MorgensternPrice, o).factor_of_safety, sp, 1e-9);
    o.function = InterSliceFunction::Constant;
    EXPECT_NEAR(*le_factor_of_safety(fk(), fk_circle(), LeMethod::MorgensternPrice, o).factor_of_safety, sp, 1e-9);
    o.function = InterSliceFunction::Points;
    o.function_points.clear();
    for (int i = 0; i <= 100; ++i) o.function_points.push_back({i / 100.0, std::sin(le_detail::kPi * i / 100.0)});
    EXPECT_NEAR(*le_factor_of_safety(fk(), fk_circle(), LeMethod::MorgensternPrice, o).factor_of_safety,
                fs(fk(), fk_circle(), LeMethod::MorgensternPrice), 1e-4);
}

TEST(LimitEquilibrium, MethodInfoIsSecondary) {
    for (LeMethod m : kMethods) {
        const auto r = run(fk(), fk_circle(), m);
        EXPECT_EQ(r.info.verification, Verification::Secondary);
        EXPECT_EQ(r.method, m);
        EXPECT_NE(r.info.source.find("Fredlund"), std::string::npos);
    }
    EXPECT_EQ(run(fk(), fk_circle(), LeMethod::Bishop).info.method_id, "Bishop-Simplified");
    EXPECT_EQ(run(fk(), fk_circle(), LeMethod::MorgensternPrice).info.method_id, "Morgenstern-Price-GLE");
    EXPECT_NE(run(fk(), fk_circle(), LeMethod::Spencer).info.source.find("Zhu"), std::string::npos);
}

// --- Correcciones de la revisión de la tarea 1 ---

namespace {
LeSection reviewer_slope(double kh) {
    auto s = one_layer({{0, 30}, {40, 30}, {80, 0}, {120, 0}}, mc(20, 20, 35));
    s.kh = kh;
    return s;
}
}  // namespace

// C1: sin resistencia y con fuerza motora, FS = 0 (falla), no la nota de la masa hacia atrás
TEST(LimitEquilibrium, ZeroStrengthGivesZero) {
    auto s = one_layer({{0, 60}, {60, 60}, {140, 20}, {180, 20}}, mc(120, 0, 0));
    for (LeMethod m : kMethods) {
        const auto r = run(s, fk_circle(), m);
        ASSERT_TRUE(r.factor_of_safety.has_value()) << le_detail::name(m);
        EXPECT_EQ(*r.factor_of_safety, 0.0) << le_detail::name(m);
        EXPECT_TRUE(r.converged);
        EXPECT_TRUE(r.warnings.empty());
    }
}

// C1: un iterado no positivo o con mα <= 0 da el aviso, nunca solo la nota
TEST(LimitEquilibrium, BadIteratesWarnInsteadOfNote) {
    const LeSection cases[] = {one_layer({{0, 60}, {60, 60}, {140, 20}, {180, 20}}, mc(120, 0, 20, 0.99)),
                               one_layer({{0, 60}, {60, 60}, {140, 20}, {180, 20}}, mc(120, 600, 89.9))};
    for (const auto& s : cases)
        for (LeMethod m : kMethods) {
            const auto r = run(s, fk_circle(), m);
            EXPECT_TRUE(r.factor_of_safety.has_value() || !r.warnings.empty()) << le_detail::name(m);
            for (const auto& n : r.notes) EXPECT_EQ(n.find("does not move towards the face"), std::string::npos);
            if (!r.factor_of_safety) EXPECT_NE(r.warnings[0].find("did not converge"), std::string::npos);
        }
}

// I1: λ como raíz de la ecuación de momentos; la sustitución directa divergía aquí (valores del revisor, solver propio)
TEST(LimitEquilibrium, LambdaRootWithStrongKh) {
    const auto f = circle(70, 45, 50);
    const auto sp = run(reviewer_slope(0.2), f, LeMethod::Spencer);
    ASSERT_TRUE(sp.factor_of_safety.has_value());
    EXPECT_NEAR(*sp.factor_of_safety, 1.4389, 2e-3);
    EXPECT_NEAR(*sp.lambda, 0.5748, 2e-3);
    EXPECT_NEAR(fs(reviewer_slope(0.2), f, LeMethod::Bishop), 1.4118, 2e-3);
    EXPECT_NEAR(fs(reviewer_slope(0.2), f, LeMethod::MorgensternPrice), 1.4346, 2e-3);
    const auto sp25 = run(reviewer_slope(0.25), f, LeMethod::Spencer);
    ASSERT_TRUE(sp25.factor_of_safety.has_value());
    EXPECT_NEAR(*sp25.factor_of_safety, 1.346, 2e-3);
    EXPECT_NEAR(*sp25.lambda, 0.597, 2e-3);
}

// I1: barrido con semilla fija; Spencer y M-P convergen cuando Bishop da un FS razonable, y si no, avisan
TEST(LimitEquilibrium, RandomSectionsConvergeOrWarn) {
    std::mt19937 rng(20261104);
    auto U = [&](double a, double b) { return std::uniform_real_distribution<double>(a, b)(rng); };
    int checked = 0, good_cases = 0;
    for (int k = 0; k < 50; ++k) {
        const double H = U(10, 60), cotb = 1.0 / std::tan(U(25, 60) * le_detail::kPi / 180.0), toe = H * cotb;
        const double x0 = -3 * H, x1 = toe + 3 * H;
        LeSection s;
        s.surface = {{x0, H}, {0, H}, {toe, 0}, {x1, 0}};
        const int nl = U(0, 1) < 0.5 ? 2 : 3;
        double y = H;
        for (int i = 0; i < nl; ++i) {
            s.materials.push_back(mc(U(18, 26), U(0, 60), U(15, 40)));
            if (i + 1 == nl) {
                s.layers.push_back(LeLayer{{}, i});
            } else {
                y = U(y - 0.6 * H, y - 0.1 * H);
                s.layers.push_back(LeLayer{{{x0, y}, {x1, y}}, i});
            }
        }
        s.kh = U(0, 0.3);
        const Point2 A{U(-2 * H, -0.1 * H), H};
        const double xb = U(0.3 * toe, toe + H);
        const Point2 B{xb, xb < toe ? H * (1 - xb / toe) : 0.0};
        const double vx = B.x - A.x, vy = B.y - A.y, L = std::hypot(vx, vy), t = U(0.2, 1.5) * L;
        const double xc = 0.5 * (A.x + B.x) - vy / L * t, yc = 0.5 * (A.y + B.y) + vx / L * t;
        const double rad = std::hypot(A.x - xc, A.y - yc);
        const bool flip = U(0, 1) < 0.5;
        const LeSection sec = flip ? mirrored(s) : s;
        const auto sf = circle(flip ? -xc : xc, yc, rad);
        LeResult bi;
        try {
            bi = run(sec, sf, LeMethod::Bishop);
        } catch (const std::invalid_argument&) {
            continue;
        }
        ++checked;
        const bool good = bi.factor_of_safety && *bi.factor_of_safety >= 0.3 && *bi.factor_of_safety <= 5.0;
        good_cases += good;
        for (LeMethod m : {LeMethod::Spencer, LeMethod::MorgensternPrice}) {
            const auto r = run(sec, sf, m);
            if (good) EXPECT_TRUE(r.factor_of_safety.has_value()) << "case " << k << " " << le_detail::name(m);
            EXPECT_TRUE(r.factor_of_safety.has_value() || !r.warnings.empty()) << "case " << k;
        }
    }
    EXPECT_GE(checked, 40);
    EXPECT_GE(good_cases, 30);
}

// I2: la nota de Bishop con polilínea no tapa el aviso de no convergencia
TEST(LimitEquilibrium, PolylineBishopWarnsWhenNotConverged) {
    auto o = opts(50);
    o.max_iterations = 1;
    const auto r = le_factor_of_safety(fk(), polyline({{30, 60}, {70, 35}, {110, 25}, {150, 20}}), LeMethod::Bishop, o);
    EXPECT_FALSE(r.factor_of_safety.has_value());
    ASSERT_EQ(r.warnings.size(), 1u);
    EXPECT_EQ(r.warnings[0].rfind("Bishop did not converge", 0), 0u);
    EXPECT_EQ(r.notes.size(), 1u);
}

// M1: masa minúscula, FS informado con nota
TEST(LimitEquilibrium, NegligibleMassNote) {
    const auto r = run(fk(), polyline({{80, 50}, {90, 45 - 1e-7}, {100, 40}}), LeMethod::Ordinary);
    ASSERT_TRUE(r.factor_of_safety.has_value());
    EXPECT_NE(std::find(r.notes.begin(), r.notes.end(), "negligible sliding mass"), r.notes.end());
    for (const auto& n : run(fk(), fk_circle(), LeMethod::Ordinary).notes) EXPECT_NE(n, "negligible sliding mass");
}

// M2 y M3: coordenadas UTM dan el mismo FS y no aceptan cortes falsos
TEST(LimitEquilibrium, TranslatedCoordinates) {
    const double dx = 5e5, dy = 8.5e6;
    auto shift = [&](std::vector<Point2> p) {
        for (auto& v : p) v = {v.x + dx, v.y + dy};
        return p;
    };
    auto shifted = [&](LeSection s) {
        s.surface = shift(s.surface);
        for (auto& l : s.layers)
            if (!l.bottom.empty()) l.bottom = shift(l.bottom);
        if (s.model_base_y) *s.model_base_y += dy;
        return s;
    };
    for (LeMethod m : kMethods) {
        const double a = fs(fk(), fk_circle(), m), b = fs(shifted(fk()), circle(120 + dx, 90 + dy, 80), m);
        EXPECT_NEAR(b, a, 1e-9 * a) << le_detail::name(m);
        const double c = fs(acads3b(), polyline(acads3b_slip()), m),
                     d = fs(shifted(acads3b()), polyline(shift(acads3b_slip())), m);
        EXPECT_NEAR(d, c, 1e-9 * c) << le_detail::name(m);
    }
    const std::vector<Point2> ground{{0, 24.386}, {40, 24.386}, {59.550, 0}, {99.550, 0}};
    for (double ox : {0.0, 8.5e6}) {
        auto g = ground;
        for (auto& v : g) v.x += ox;
        const auto sec = one_layer(g, mc(20, 10, 30));
        EXPECT_NE(error_of([&] { run(sec, circle(58.480 + ox, 23.905, 24.011), LeMethod::Bishop); }).find("does not cut"),
                  std::string::npos)
            << ox;
    }
}

TEST(LimitEquilibrium, ReviewOptionChecks) {
    auto o = opts(50);
    o.tolerance = 1e-2;
    EXPECT_NE(error_of([&] { le_factor_of_safety(fk(), fk_circle(), LeMethod::Bishop, o); }).find("tolerance"),
              std::string::npos);
    // M5: N' < 0 en Bishop se anota, sin recortar
    const auto bi = run(fk(0.25), fk_circle(), LeMethod::Bishop);
    EXPECT_NE(std::find(bi.notes.begin(), bi.notes.end(), "effective normal force below zero in 3 slices"),
              bi.notes.end());
    // M6: sin convergencia, la tabla no trae fuerzas
    o = opts(50);
    o.max_iterations = 1;
    for (const auto& t : le_factor_of_safety(fk(), fk_circle(), LeMethod::Spencer, o).slices) {
        EXPECT_EQ(t.normal_force, 0.0);
        EXPECT_EQ(t.shear_strength, 0.0);
        EXPECT_EQ(t.interslice_normal_right, 0.0);
        EXPECT_EQ(t.interslice_shear_right, 0.0);
    }
    // M7: función por puntos de 0 a 1, al menos dos puntos y algún f > 0
    const std::vector<std::vector<Point2>> bad{{{0, 1}}, {{0.1, 1}, {1, 1}}, {{0, 1}, {0.9, 1}}, {{0, 0}, {1, 0}}};
    for (const auto& p : bad) {
        o = opts(50);
        o.function = InterSliceFunction::Points;
        o.function_points = p;
        EXPECT_NE(error_of([&] { le_factor_of_safety(fk(), fk_circle(), LeMethod::MorgensternPrice, o); })
                      .find("function_points"),
                  std::string::npos);
    }
}

// --- Tarea 2: agua, grieta de tracción y Janbu corregido ---

namespace {
const LeMethod kAllMethods[] = {LeMethod::Ordinary, LeMethod::Bishop, LeMethod::JanbuSimplified,
                                LeMethod::JanbuCorrected, LeMethod::Spencer, LeMethod::MorgensternPrice};

// ACADS 1(b), Slide problema 2: geometría de 1(a), c 32, φ 10, γ 20, grieta de 2c/(γ√Ka) = 3.814 m llena de agua
LeSection acads1b(double fill = 1.0) {
    auto s = one_layer({{20, 25}, {30, 25}, {50, 35}, {70, 35}}, mc(20, 32, 10));
    s.model_base_y = 20;
    s.crack = LeTensionCrack{3.814, fill};
    return s;
}
// Círculo crítico de Bishop hallado con una búsqueda propia (malla de centros (31-47) x (34-49) como la de Slide,
// 21 radios por centro y afinado por patrón hasta 0.001 m), llamando a le_factor_of_safety.
SlipSurface acads1b_circle() { return circle(37.45, 44.5, 20.875); }
}  // namespace

// Slide: Bishop 1.596, Spencer y GLE 1.592 (referencia 1.65); recalculado en el círculo de la búsqueda propia:
// Bishop 1.5915, Spencer 1.5879, M-P 1.5885. La grieta corta la masa en x = 53.53, a 3.814 m bajo la cresta.
TEST(LimitEquilibrium, Acads1bTensionCrackWithWater) {
    const auto f = acads1b_circle();
    const double b = fs(acads1b(), f, LeMethod::Bishop), sp = fs(acads1b(), f, LeMethod::Spencer),
                 mp = fs(acads1b(), f, LeMethod::MorgensternPrice);
    EXPECT_NEAR(b, 1.596, 0.02 * 1.596);
    EXPECT_NEAR(sp, 1.592, 0.02 * 1.592);
    EXPECT_NEAR(mp, 1.592, 0.02 * 1.592);
    EXPECT_NEAR(b, 1.5915, 2e-3);
    EXPECT_NEAR(sp, 1.5879, 2e-3);
    const auto r = run(acads1b(), f, LeMethod::Bishop);
    EXPECT_NEAR(r.slices.back().x_right, 53.528, 1e-3);
    EXPECT_NEAR(r.slices.back().base_y_right, 35.0 - 3.814, 1e-9);
    // el agua de la grieta baja el FS; sin grieta es mayor
    EXPECT_LT(b, fs(acads1b(0.0), f, LeMethod::Bishop));
    auto none = acads1b();
    none.crack.reset();
    EXPECT_LT(fs(acads1b(0.0), f, LeMethod::Bishop), fs(none, f, LeMethod::Bishop));
    // el Ordinario dice cómo trata la fuerza del agua
    const auto o = run(acads1b(), f, LeMethod::Ordinary);
    EXPECT_NE(std::find_if(o.notes.begin(), o.notes.end(),
                           [](const std::string& n) { return n.find("crack water force") != std::string::npos; }),
              o.notes.end());
}

TEST(LimitEquilibrium, CrackDepthToZeroAndCrackIgnored) {
    for (LeMethod m : kAllMethods) {
        const double base = fs(fk(), fk_circle(), m);
        for (double fill : {0.0, 1.0}) {
            auto s = fk();
            s.crack = LeTensionCrack{1e-7, fill};
            EXPECT_NEAR(fs(s, fk_circle(), m), base, 1e-6) << le_detail::name(m);
        }
        // una grieta más honda que la masa no actúa: mismo FS y nota
        auto deep = fk();
        deep.crack = LeTensionCrack{100.0, 1.0};
        const auto r = run(deep, fk_circle(), m);
        EXPECT_EQ(*r.factor_of_safety, base) << le_detail::name(m);
        EXPECT_NE(std::find(r.notes.begin(), r.notes.end(), "tension crack does not reach the slip surface: crack ignored"),
                  r.notes.end());
    }
    // la grieta seca acorta la base y quita su resistencia: la masa y el FS cambian
    auto dry = fk();
    dry.crack = LeTensionCrack{10.0, 0.0};
    const auto a = run(dry, fk_circle(), LeMethod::Bishop), b = run(fk(), fk_circle(), LeMethod::Bishop);
    EXPECT_LT(a.sliding_mass_area, b.sliding_mass_area);
    EXPECT_GT(a.slices.front().x_left, b.slices.front().x_left);
    EXPECT_NEAR(a.slices.front().base_y_left, 60.0 - 10.0, 1e-9);
}

TEST(LimitEquilibrium, PiezometricLine) {
    // bajo toda la masa (el fondo del círculo está en y = 10): igual que seco
    for (LeMethod m : kAllMethods) {
        auto s = fk();
        s.piezometric = std::vector<Point2>{{0, 0}, {180, 0}};
        s.water_unit_weight = 62.4;
        EXPECT_NEAR(fs(s, fk_circle(), m), fs(fk(), fk_circle(), m), 1e-12) << le_detail::name(m);
    }
    // sobre la base: u = γw (y_piezo - y_base) en el punto medio, el FS baja, los vértices son bordes, ru ignorado
    auto s = fk(0.25);
    s.water_unit_weight = 62.4;
    s.piezometric = std::vector<Point2>{{0, 40}, {100, 30}, {180, 15}};
    const auto r = run(s, fk_circle(), LeMethod::Spencer);
    ASSERT_TRUE(r.factor_of_safety.has_value());
    EXPECT_LT(*r.factor_of_safety, fs(fk(), fk_circle(), LeMethod::Spencer));
    int wet = 0, at100 = 0;
    for (const auto& t : r.slices) {
        const double xm = 0.5 * (t.x_left + t.x_right), ym = 0.5 * (t.base_y_left + t.base_y_right);
        const double yp = xm <= 100 ? 40 - 10 * xm / 100 : 30 - 15 * (xm - 100) / 80;
        EXPECT_NEAR(t.pore_pressure, 62.4 * std::max(yp - ym, 0.0), 1e-9);
        wet += t.pore_pressure > 0.0;
        at100 += t.x_left == 100.0;
    }
    EXPECT_GT(wet, 10);
    EXPECT_EQ(at100, 1);
    EXPECT_NE(std::find(r.notes.begin(), r.notes.end(), "piezometric line given: the ru of the materials is ignored"),
              r.notes.end());
    s.materials[0].ru = 0.0;
    EXPECT_NEAR(fs(s, fk_circle(), LeMethod::Spencer), *r.factor_of_safety, 1e-12);
    // la piezométrica debe cubrir la masa
    s.piezometric = std::vector<Point2>{{50, 40}, {180, 15}};
    EXPECT_NE(error_of([&] { run(s, fk_circle(), LeMethod::Bishop); }).find("piezometric"), std::string::npos);
}

TEST(LimitEquilibrium, RuPerMaterial) {
    // dos estratos con el mismo material salvo el índice y el mismo ru: igual que un solo material con ese ru
    auto two = [](double ru_top, double ru_bottom) {
        auto s = fk();
        s.materials = {mc(120, 600, 20, ru_top), mc(120, 600, 20, ru_bottom)};
        s.layers = {LeLayer{{{0, 35}, {180, 35}}, 0}, LeLayer{{}, 1}};
        return s;
    };
    auto global = two(0.25, 0.25);
    global.layers[1].material = 0;
    for (LeMethod m : kAllMethods) {
        EXPECT_NEAR(fs(two(0.25, 0.25), fk_circle(), m), fs(global, fk_circle(), m), 1e-12) << le_detail::name(m);
        EXPECT_NE(fs(two(0.0, 0.25), fk_circle(), m), fs(global, fk_circle(), m)) << le_detail::name(m);
    }
    // u = ru W/b con el ru del material de la base
    for (const auto& t : run(two(0.0, 0.25), fk_circle(), LeMethod::Bishop).slices) {
        const double ru = t.material == 1 ? 0.25 : 0.0;
        EXPECT_NEAR(t.pore_pressure, ru * t.weight / (t.x_right - t.x_left), 1e-9);
    }
}

namespace {
// d/L independiente: la cuerda entre los extremos de la tabla y el punto más hondo del círculo
double circle_d_over_l(const LeResult& r, double xc, double yc, double R) {
    const double ax = r.slices.front().x_left, ay = r.slices.front().base_y_left;
    const double cx = r.slices.back().x_right, cy = r.slices.back().base_y_right;
    const double L = std::hypot(cx - ax, cy - ay);
    const double dc = std::fabs((cy - ay) * (xc - ax) - (cx - ax) * (yc - ay)) / L;  // centro a la cuerda
    return (R - dc) / L;
}
}  // namespace

TEST(LimitEquilibrium, JanbuCorrectedF0) {
    struct Case { LeMaterial m; double b1; };
    const Case cases[] = {{mc(120, 600, 20), 0.69}, {mc(120, 0, 30), 0.50}, {mc(120, 1500, 0), 0.31}};
    for (const auto& c : cases) {
        const auto s = one_layer({{0, 60}, {60, 60}, {140, 20}, {180, 20}}, c.m);
        const auto co = run(s, fk_circle(), LeMethod::JanbuCorrected), si = run(s, fk_circle(), LeMethod::JanbuSimplified);
        ASSERT_TRUE(co.factor_of_safety && si.factor_of_safety) << c.b1;
        const double r = circle_d_over_l(co, 120, 90, 80);
        EXPECT_GT(r, 0.05);
        EXPECT_NEAR(*co.factor_of_safety / *si.factor_of_safety, 1.0 + c.b1 * (r - 1.4 * r * r), 1e-12) << c.b1;
        for (const auto& n : co.notes) EXPECT_EQ(n.find("b1"), std::string::npos) << n;
        EXPECT_EQ(co.info.method_id, "Janbu-Corrected");
        EXPECT_EQ(co.info.verification, Verification::Secondary);
        // reflejada: mismo FS
        const auto mi = run(mirrored(s), circle(-120, 90, 80), LeMethod::JanbuCorrected);
        EXPECT_NEAR(*mi.factor_of_safety, *co.factor_of_safety, 1e-9 * *co.factor_of_safety);
    }
    // mezcla de bases cohesivas y friccionantes: b1 = 0.69 con nota
    auto mix = fk();
    mix.materials = {mc(120, 600, 0), mc(120, 0, 30)};
    mix.layers = {LeLayer{{{0, 35}, {180, 35}}, 0}, LeLayer{{}, 1}};
    const auto co = run(mix, fk_circle(), LeMethod::JanbuCorrected), si = run(mix, fk_circle(), LeMethod::JanbuSimplified);
    const double r = circle_d_over_l(co, 120, 90, 80);
    EXPECT_NEAR(*co.factor_of_safety / *si.factor_of_safety, 1.0 + 0.69 * (r - 1.4 * r * r), 1e-12);
    EXPECT_NE(std::find(co.notes.begin(), co.notes.end(),
                        "Janbu corrected: the bases mix cohesive and frictional materials, b1 = 0.69"),
              co.notes.end());
}

// Slide: Janbu corregido 0.990 en su búsqueda. Círculo de la búsqueda propia de Janbu corregido (malla de 1(a),
// 21 radios y afinado): (30.121, 52.4, 27.4), FS 1.0039 (+1.4 % de Slide).
TEST(LimitEquilibrium, Acads1aJanbuCorrected) {
    const double v = fs(acads1a(), circle(30.121, 52.4, 27.4), LeMethod::JanbuCorrected);
    EXPECT_NEAR(v, 0.990, 0.02 * 0.990);
    EXPECT_NEAR(v, 1.0039, 2e-3);
}

TEST(LimitEquilibrium, ReflectedSectionWithWaterAndCrack) {
    auto a = acads1b();
    a.piezometric = std::vector<Point2>{{20, 24}, {45, 27}, {70, 29}};
    auto b = mirrored(a);
    b.piezometric = mirror(*a.piezometric);
    const auto fa = acads1b_circle(), fb = circle(-37.45, 44.5, 20.875);
    for (LeMethod m : kAllMethods) {
        const auto ra = run(a, fa, m), rb = run(b, fb, m);
        ASSERT_TRUE(ra.factor_of_safety && rb.factor_of_safety) << le_detail::name(m);
        EXPECT_NEAR(*rb.factor_of_safety, *ra.factor_of_safety, 1e-9 * *ra.factor_of_safety) << le_detail::name(m);
        if (ra.lambda) EXPECT_NEAR(*rb.lambda, *ra.lambda, 1e-9 * std::fabs(*ra.lambda));
        EXPECT_NEAR(rb.slices.front().x_left, -ra.slices.back().x_right, 1e-9);
    }
}

// Spencer con la grieta llena: la masa queda en equilibrio de fuerzas y de momentos, verificado desde la tabla de
// tajadas (N = N' + u l, S = resistencia / FS, W por el punto medio de la base como en Zhu et al. 2005) más el agua
// P = ½ γw (f zc)² a f zc / 3 sobre el fondo de la grieta.
TEST(LimitEquilibrium, SpencerGlobalEquilibriumWithWaterFilledCrack) {
    auto s = fk(0.1);
    s.water_unit_weight = 62.4;
    s.crack = LeTensionCrack{12.0, 1.0};
    LeOptions o = opts(200);
    o.tolerance = 1e-12;
    const auto r = le_factor_of_safety(s, fk_circle(), LeMethod::Spencer, o);
    ASSERT_TRUE(r.factor_of_safety.has_value());
    const double F = *r.factor_of_safety, P = 0.5 * 62.4 * 12.0 * 12.0;
    const double py = r.slices.front().base_y_left + 12.0 / 3.0;
    EXPECT_NEAR(r.slices.front().base_y_left, 60.0 - 12.0, 1e-9);
    const double ox = 77.0, oy = 33.0;
    double H = P, V = 0, M = -(py - oy) * P, W = 0, scale = 0;
    for (const auto& t : r.slices) {
        const double a = t.alpha_deg * le_detail::kPi / 180.0;
        const double N = t.normal_force + t.pore_pressure * t.base_length, S = t.shear_strength / F;
        const double fx = N * std::sin(a) - S * std::cos(a), fy = N * std::cos(a) + S * std::sin(a);
        const double mx = 0.5 * (t.x_left + t.x_right), my = 0.5 * (t.base_y_left + t.base_y_right);
        H += fx;
        V += fy - t.weight;
        M += (mx - ox) * fy - (my - oy) * fx - (mx - ox) * t.weight;
        W += t.weight;
        scale += t.weight * std::fabs(mx - ox);
    }
    EXPECT_NEAR(H / W, 0.0, 1e-8);
    EXPECT_NEAR(V / W, 0.0, 1e-8);
    EXPECT_NEAR(M / scale, 0.0, 1e-8);
    // el agua pesa en el balance: sin ella no cerraría
    EXPECT_GT(P / W, 1e-3);
}

// --- Revisión 3C: agua encharcada (R16) y grieta casi nula ---

namespace {
// F&K con un lago horizontal a la cota y: la piezométrica queda sobre el terreno en la cara baja y en el pie
LeSection fk_lake(double y) {
    auto s = fk();
    s.water_unit_weight = 62.4;
    s.piezometric = std::vector<Point2>{{0, y}, {180, y}};
    return s;
}
double fk_ground(double x) { return x <= 60 ? 60 : x >= 140 ? 20 : 60 - 0.5 * (x - 60); }
bool has_note(const LeResult& r, const std::string& n) {
    return std::find(r.notes.begin(), r.notes.end(), n) != r.notes.end();
}
const char* kPondNote = "ponded water above the ground surface modelled as a surface load";
}  // namespace

// Bishop con el agua encharcada como carga contra la implementación independiente del revisor (sondeo p3b: 200
// tajadas, peso y empuje en el medio del tramo de terreno): 2.177 con el lago en y = 40 y 1.954 en y = 30. Antes de la
// R16 el núcleo daba 1.356 y 1.661 sin aviso (u en la base sin la carga que la equilibra).
TEST(LimitEquilibrium, PondedWaterBishopIndependent) {
    for (const auto& [y, ref] : {std::pair{40.0, 2.177}, std::pair{30.0, 1.954}}) {
        const auto r = run(fk_lake(y), fk_circle(), LeMethod::Bishop);
        ASSERT_TRUE(r.factor_of_safety.has_value()) << y;
        EXPECT_NEAR(*r.factor_of_safety, ref, 0.005 * ref) << y;
        EXPECT_TRUE(has_note(r, kPondNote));
        for (LeMethod m : kAllMethods) EXPECT_TRUE(run(fk_lake(y), fk_circle(), m).factor_of_safety) << le_detail::name(m);
    }
}

// Spencer con el lago: la masa queda en equilibrio de fuerzas y de momentos desde la tabla de tajadas (W por el punto
// medio de la base, como en Zhu et al. 2005) más el agua encharcada calculada aquí aparte: p lineal en la tajada,
// resultante p_med·b normal al terreno en el centroide del trapecio de presiones.
TEST(LimitEquilibrium, SpencerGlobalEquilibriumWithPondedWater) {
    const auto s = fk_lake(40.0);
    LeOptions o = opts(200);
    o.tolerance = 1e-12;
    const auto r = le_factor_of_safety(s, fk_circle(), LeMethod::Spencer, o);
    ASSERT_TRUE(r.factor_of_safety.has_value());
    const double F = *r.factor_of_safety, ox = 77.0, oy = 33.0;
    double H = 0, V = 0, M = 0, W = 0, scale = 0, Vw = 0;
    int at100 = 0;
    for (const auto& t : r.slices) {
        const double a = t.alpha_deg * le_detail::kPi / 180.0;
        const double N = t.normal_force + t.pore_pressure * t.base_length, S = t.shear_strength / F;
        const double fx = N * std::sin(a) - S * std::cos(a), fy = N * std::cos(a) + S * std::sin(a);
        const double mx = 0.5 * (t.x_left + t.x_right), my = 0.5 * (t.base_y_left + t.base_y_right);
        H += fx;
        V += fy - t.weight;
        M += (mx - ox) * fy - (my - oy) * fx - (mx - ox) * t.weight;
        W += t.weight;
        scale += t.weight * std::fabs(mx - ox);
        const double b = t.x_right - t.x_left;
        const double pa = 62.4 * std::max(40.0 - fk_ground(t.x_left), 0.0), pb = 62.4 * std::max(40.0 - fk_ground(t.x_right), 0.0);
        if (pa + pb > 0.0) {
            const double Qv = 0.5 * (pa + pb) * b, Qh = Qv * (fk_ground(t.x_right) - fk_ground(t.x_left)) / b;
            const double qx = t.x_left + b * (pa + 2.0 * pb) / (3.0 * (pa + pb)), qy = fk_ground(qx);
            H += Qh;
            V -= Qv;
            M += (qx - ox) * (-Qv) - (qy - oy) * Qh;
            Vw += Qv;
        }
        at100 += std::fabs(t.x_left - 100.0) < 1e-9;  // el lago empieza en x = 100: borde de tajada
    }
    EXPECT_EQ(at100, 1);
    EXPECT_GT(Vw / W, 0.05);  // el agua pesa en el balance: sin ella no cerraría
    EXPECT_NEAR(H / W, 0.0, 1e-8);
    EXPECT_NEAR(V / W, 0.0, 1e-8);
    EXPECT_NEAR(M / scale, 0.0, 1e-8);
}

// Con la piezométrica bajo el terreno (o tocándolo en el pie) no hay carga: el FS es el de antes de la R16 (fase-3c,
// 53c1365, 50 tajadas).
TEST(LimitEquilibrium, PiezometricBelowGroundUnchanged) {
    const std::vector<Point2> piezos[] = {{{0, 50}, {60, 45}, {140, 15}, {180, 15}}, {{0, 50}, {60, 45}, {140, 20}, {180, 20}}};
    const double before[2][6] = {
        {1.595155584331892, 1.7420709735369986, 1.5903337598442362, 1.7594808038777057, 1.741632329980768, 1.7407040941073466},
        {1.520277002696464, 1.6603001211376471, 1.5238699097781523, 1.685947894437027, 1.660518711582712, 1.6594973307375793}};
    for (int i = 0; i < 2; ++i)
        for (int k = 0; k < 6; ++k) {
            auto s = fk();
            s.water_unit_weight = 62.4;
            s.piezometric = piezos[i];
            const auto r = run(s, fk_circle(), kAllMethods[k]);
            ASSERT_TRUE(r.factor_of_safety.has_value()) << le_detail::name(kAllMethods[k]);
            EXPECT_NEAR(*r.factor_of_safety, before[i][k], 1e-12 * before[i][k]) << i << " " << le_detail::name(kAllMethods[k]);
            EXPECT_FALSE(has_note(r, kPondNote));
        }
}

// Talud sumergido por completo (lago sobre la cresta): Bishop y Janbu, sin cortante entre tajadas, dan lo mismo que el
// talud seco con el peso sumergido γ - γw (el agua sobre la masa y en su base cierra la flotación); Spencer y M-P
// quedan cerca (su X = λ f E toma la E total, con el agua) y el Ordinario, que ignora el agua entre tajadas, no da FS.
TEST(LimitEquilibrium, SubmergedSlopeMatchesBuoyantWeight) {
    const auto wet = fk_lake(100.0);
    const auto dry = one_layer({{0, 60}, {60, 60}, {140, 20}, {180, 20}}, mc(120 - 62.4, 600, 20));
    EXPECT_NEAR(fs(wet, fk_circle(), LeMethod::Bishop, 200) / fs(dry, fk_circle(), LeMethod::Bishop, 200), 1.0, 1e-4);
    EXPECT_NEAR(fs(wet, fk_circle(), LeMethod::JanbuSimplified, 200) /
                    fs(dry, fk_circle(), LeMethod::JanbuSimplified, 200), 1.0, 1e-6);
    for (LeMethod m : {LeMethod::Spencer, LeMethod::MorgensternPrice})
        EXPECT_NEAR(fs(wet, fk_circle(), m, 200) / fs(dry, fk_circle(), m, 200), 1.0, 5e-3) << le_detail::name(m);
    const auto o = run(wet, fk_circle(), LeMethod::Ordinary);
    EXPECT_FALSE(o.factor_of_safety.has_value());
    EXPECT_TRUE(o.warnings.empty());
    EXPECT_TRUE(has_note(o, "Ordinary: no driving force along the bases with the ponded water load (the method "
                            "neglects the water between slices)"));
}

TEST(LimitEquilibrium, PondedWaterReflected) {
    const auto a = fk_lake(40.0);
    auto b = mirrored(a);
    b.piezometric = mirror(*a.piezometric);
    for (LeMethod m : kAllMethods) {
        const auto ra = run(a, fk_circle(), m), rb = run(b, circle(-120, 90, 80), m);
        ASSERT_TRUE(ra.factor_of_safety && rb.factor_of_safety) << le_detail::name(m);
        EXPECT_NEAR(*rb.factor_of_safety, *ra.factor_of_safety, 1e-9 * *ra.factor_of_safety) << le_detail::name(m);
        if (ra.lambda) EXPECT_NEAR(*rb.lambda, *ra.lambda, 1e-9 * std::fabs(*ra.lambda));
    }
}

// Grieta de 1e-9: el corte del lado de la cresta cae sobre el borde de la masa; antes se tomaba el del pie y la masa
// quedaba en una tajada (FS vacío, «does not move towards the face»). Ahora la grieta se ignora con nota.
TEST(LimitEquilibrium, NearZeroCrackIgnored) {
    for (LeMethod m : kAllMethods) {
        auto s = fk();
        s.crack = LeTensionCrack{1e-9, 0.0};
        const auto r = run(s, fk_circle(), m);
        ASSERT_TRUE(r.factor_of_safety.has_value()) << le_detail::name(m);
        EXPECT_EQ(*r.factor_of_safety, fs(fk(), fk_circle(), m)) << le_detail::name(m);
        EXPECT_TRUE(has_note(r, "tension crack too shallow to cut the slip surface inside the mass: crack ignored"));
    }
}

// --- Tarea 3: Hoek-Brown no lineal ---

namespace {
// Carranza-Torres y Hormazábal (2020), Tabla 1: H, γ (kN/m³), σci (MPa), mb, s; a = 0.5, talud de 50°
struct CctCase { double H, gamma, sci_mpa, mb, s, fs; };
// FS recalculados (plan 3C) con Bishop en el círculo escalado; el artículo publica 2.01 para el caso 3 y no se
// reproduce (plan, «Valores a confirmar»): con Balmer y con el Mohr-Coulomb equivalente salen 3.5 a 3.6.
const CctCase kCct[] = {{241, 27, 20.4, 3.2374, 1.0509e-2, 3.6031},
                        {520, 25, 15.0, 8.7961, 7.7649e-2, 3.6031},
                        {360, 27, 77.7, 1.2601, 1.5893e-3, 3.5940},
                        {676, 24, 11.3, 14.5567, 2.1107e-1, 3.6015},
                        {399, 26, 225, 0.4638, 2.1509e-4, 3.5924}};

LeMaterial hb_material(double gamma, double sci_kpa, double mb, double s, double ru = 0.0) {
    LeMaterial m;
    m.unit_weight = gamma;
    m.model = StrengthModel::HoekBrown;
    m.hb = hb_params_from_constants(mb, s, 0.5);
    m.sigma_ci = sci_kpa;
    m.ru = ru;
    return m;
}
// Pie en el origen y el centro (xc, yc) = (-0.5758H, 1.6293H) sobre la cara: la cresta queda en x = -H cot 50° y la
// cara mira a +x (con la cresta en +H cot 50° el centro cae fuera de la cara y sale FS 3.398, no el 3.594 del plan).
// σci en kPa porque γ va en kN/m³.
LeSection cct_section(const CctCase& c, std::optional<LeMaterial> mat = std::nullopt) {
    const double H = c.H, xk = -H / std::tan(50.0 * le_detail::kPi / 180.0);
    return one_layer({{xk - 3 * H, H}, {xk, H}, {0, 0}, {3 * H, 0}},
                     mat.value_or(hb_material(c.gamma, c.sci_mpa * 1000.0, c.mb, c.s)));
}
SlipSurface cct_circle(double H) { return circle(-0.5758 * H, 1.6293 * H, 1.728 * H); }

// τ de la envolvente de Balmer en σn, por bisección propia sobre hb_normal_shear (independiente del núcleo)
double balmer_tau(double sn, double sci, const HbParams& p) {
    const double st = hb_tensile(sci, p);
    if (sn <= st) return 0.0;
    double lo = st, hi = std::max(sn, 0.0) + 1.0;
    for (int k = 0; k < 300; ++k) {
        const double mid = 0.5 * (lo + hi);
        (hb_normal_shear(mid, sci, p).sigma_n_mpa < sn ? lo : hi) = mid;
    }
    return hb_normal_shear(0.5 * (lo + hi), sci, p).tau_mpa;
}
}  // namespace

TEST(LimitEquilibrium, HoekBrownSimilarityCarranzaTorres) {
    const double f3 = fs(cct_section(kCct[2]), cct_circle(kCct[2].H), LeMethod::Bishop);
    EXPECT_NEAR(f3, 3.594, 0.01);
    for (const auto& c : kCct) {
        const auto r = run(cct_section(c), cct_circle(c.H), LeMethod::Bishop);
        ASSERT_TRUE(r.factor_of_safety.has_value()) << c.H;
        EXPECT_NEAR(*r.factor_of_safety, f3, 0.005 * f3) << c.H;  // similitud: el mismo FS a ±0.5 %
        EXPECT_NEAR(*r.factor_of_safety, c.fs, 0.01) << c.H;
        EXPECT_TRUE(r.warnings.empty()) << c.H;
        // la masa va de 2.185H detrás del pie (sobre la cresta) hasta el pie
        EXPECT_NEAR(r.slices.front().x_left / c.H, -2.1851, 1e-3);
        EXPECT_NEAR(r.slices.back().x_right / c.H, 0.0, 1e-3);
        EXPECT_NE(r.info.source.find("Balmer"), std::string::npos);
    }
    // con s = 0 baja (plan: 3.545)
    auto zero = kCct[2];
    zero.s = 0.0;
    EXPECT_NEAR(fs(cct_section(zero), cct_circle(zero.H), LeMethod::Bishop), 3.545, 0.01);
}

// Mohr-Coulomb equivalente de Hoek et al. (2002) con σ3max de talud (hb_sigma3max en MPa y MN/m³)
TEST(LimitEquilibrium, HoekBrownAgainstEquivalentMohrCoulomb) {
    const auto& c = kCct[2];
    const HbParams p = hb_params_from_constants(c.mb, c.s, 0.5);
    const double s3 = hb_sigma3max(hb_global_strength(c.sci_mpa, p), c.gamma / 1000.0, c.H, HbApplication::Slope);
    const auto fit = hb_mohr_coulomb(c.sci_mpa, p, s3);
    const double hb = fs(cct_section(c), cct_circle(c.H), LeMethod::Bishop);
    const double eq = fs(cct_section(c, mc(c.gamma, fit.cohesion_mpa * 1000.0, fit.phi_deg)), cct_circle(c.H),
                         LeMethod::Bishop);
    EXPECT_GE(hb / eq, 0.9);
    EXPECT_LE(hb / eq, 1.1);
    EXPECT_NEAR(eq, 3.580, 0.01);  // φ' 36.56°, c' 1.858 MPa con σ3max 7.12 MPa
    // el par del plan (φ' 36.38°, c' 1.770 MPa) da su 3.51
    EXPECT_NEAR(fs(cct_section(c, mc(c.gamma, 1770.0, 36.38)), cct_circle(c.H), LeMethod::Bishop), 3.51, 0.01);
}

TEST(LimitEquilibrium, HoekBrownSpencerAndMorgensternPrice) {
    const auto& c = kCct[2];
    const double b = fs(cct_section(c), cct_circle(c.H), LeMethod::Bishop);
    for (LeMethod m : {LeMethod::Spencer, LeMethod::MorgensternPrice}) {
        const auto r = run(cct_section(c), cct_circle(c.H), m);
        ASSERT_TRUE(r.factor_of_safety.has_value()) << le_detail::name(m);
        EXPECT_TRUE(r.converged);
        EXPECT_NEAR(*r.factor_of_safety, b, 0.02 * b) << le_detail::name(m);
        EXPECT_TRUE(r.lambda.has_value());
    }
    // reflejada: mismo FS y λ en todos los métodos
    const auto a = cct_section(c), m = mirrored(a);
    for (LeMethod k : kAllMethods) {
        const auto ra = run(a, cct_circle(c.H), k), rb = run(m, circle(0.5758 * c.H, 1.6293 * c.H, 1.728 * c.H), k);
        ASSERT_TRUE(ra.factor_of_safety && rb.factor_of_safety) << le_detail::name(k);
        EXPECT_NEAR(*rb.factor_of_safety, *ra.factor_of_safety, 1e-9 * *ra.factor_of_safety) << le_detail::name(k);
        if (ra.lambda) EXPECT_NEAR(*rb.lambda, *ra.lambda, 1e-9 * std::fabs(*ra.lambda));
    }
}

// En el FS convergido la resistencia de cada base es la τ de Balmer en su σn' (la recta tangente pasa por el punto):
// el Ordinario en forma cerrada, Bishop y Spencer en la tabla.
TEST(LimitEquilibrium, HoekBrownStrengthIsOnTheEnvelope) {
    auto c = kCct[2];
    auto s = cct_section(c);
    s.kh = 0.1;
    s.materials[0].ru = 0.1;
    const double sci = c.sci_mpa * 1000.0;
    const HbParams& p = *s.materials[0].hb;
    const auto o = run(s, cct_circle(c.H), LeMethod::Ordinary);
    double num = 0.0, den = 0.0;
    for (const auto& t : o.slices) {
        const double a = t.alpha_deg * le_detail::kPi / 180.0;
        const double np = std::max(0.0, t.weight * std::cos(a) - 0.1 * t.weight * std::sin(a) -
                                            t.pore_pressure * t.base_length);
        num += balmer_tau(np / t.base_length, sci, p) * t.base_length;
        den += t.weight * std::sin(a) + 0.1 * t.weight * std::cos(a);
    }
    EXPECT_NEAR(*o.factor_of_safety, num / den, 1e-9 * num / den);
    for (LeMethod m : {LeMethod::Bishop, LeMethod::Spencer}) {
        const auto r = run(s, cct_circle(c.H), m);
        ASSERT_TRUE(r.factor_of_safety.has_value()) << le_detail::name(m);
        for (const auto& t : r.slices) {
            const double tau = balmer_tau(t.normal_force / t.base_length, sci, p);
            EXPECT_NEAR(t.shear_strength / t.base_length, tau, 1e-6 * sci) << le_detail::name(m);
            EXPECT_GT(t.friction_deg, 0.0);
            EXPECT_LT(t.friction_deg, 90.0);
        }
    }
}

TEST(LimitEquilibrium, HoekBrownTensionGivesZeroShear) {
    // s = 0: σt = 0, y con ru alto el Ordinario deja N' = 0 cerca de la cresta
    const auto s = one_layer({{0, 30}, {40, 30}, {80, 0}, {120, 0}}, hb_material(20, 10000, 0.5, 0.0, 0.45));
    const auto f = circle(70, 45, 50);
    const auto o = run(s, f, LeMethod::Ordinary);
    ASSERT_TRUE(o.factor_of_safety.has_value());
    ASSERT_EQ(o.warnings.size(), 1u);
    EXPECT_EQ(o.warnings[0], "Hoek-Brown base in tension in 12 slices: shear strength taken as zero");
    int zero = 0;
    for (const auto& t : o.slices) {
        if (t.normal_force <= 0.0) {
            EXPECT_EQ(t.shear_strength, 0.0);
            ++zero;
        }
    }
    EXPECT_EQ(zero, 12);
    // en ningún método sale NaN: o un FS, o FS vacío con aviso
    for (LeMethod m : kAllMethods) {
        const auto r = run(s, f, m);
        EXPECT_TRUE(r.factor_of_safety.has_value() || !r.warnings.empty()) << le_detail::name(m);
        if (r.factor_of_safety) EXPECT_TRUE(std::isfinite(*r.factor_of_safety));
        for (const auto& t : r.slices)
            for (double v : {t.normal_force, t.shear_strength, t.cohesion, t.friction_deg, t.interslice_normal_right})
                EXPECT_TRUE(std::isfinite(v)) << le_detail::name(m);
    }
    // Bishop: la base del pie queda bajo σt con la recta tangente (mα chico): FS vacío con aviso, no un número a medias
    const auto b = run(s, f, LeMethod::Bishop);
    EXPECT_FALSE(b.factor_of_safety.has_value());
    ASSERT_FALSE(b.warnings.empty());
    EXPECT_NE(b.warnings.back().find("tensile limit"), std::string::npos);
}

TEST(LimitEquilibrium, HoekBrownConstants) {
    const auto p = hb_params_from_constants(1.2601, 1.5893e-3, 0.5);
    EXPECT_EQ(p.mb, 1.2601);
    EXPECT_EQ(p.info.method_id, "HB-constants");
    EXPECT_NE(error_of([] { hb_params_from_constants(-1, 0.1, 0.5); }).find("mb"), std::string::npos);
    EXPECT_NE(error_of([] { hb_params_from_constants(1, 1.5, 0.5); }).find("'s'"), std::string::npos);
    EXPECT_NE(error_of([] { hb_params_from_constants(1, 0.1, 1.5); }).find("'a'"), std::string::npos);
    EXPECT_NE(error_of([] { hb_params_from_constants(1, kNan, 0.5); }).find("'s'"), std::string::npos);
}

// Barridos de robustez de Spencer y M-P: para cada λ, F sale como raíz de la ecuación de fuerzas con intervalo y
// cambio de signo. Secciones al azar con semilla fija; el generador uniforme es propio porque
// uniform_real_distribution cambia entre bibliotecas estándar y los umbrales no deben moverse por plataforma.
namespace {
struct Uniform {
    std::mt19937 g;
    explicit Uniform(unsigned seed) : g(seed) {}
    double operator()(double a, double b) { return a + (b - a) * ((static_cast<double>(g()) + 0.5) / 4294967296.0); }
};
enum class Sweep { MohrCoulomb, HoekBrown, HoekBrownTinyS };
struct SweepCase {
    LeSection section;
    SlipSurface surface;
};
SweepCase sweep_case(Uniform& U, Sweep kind) {
    const double H = U(10, 60), toe = H / std::tan(U(25, 60) * le_detail::kPi / 180.0);
    const double x0 = -3 * H, x1 = toe + 3 * H;
    LeSection s;
    s.surface = {{x0, H}, {0, H}, {toe, 0}, {x1, 0}};
    const int nl = 1 + std::min(2, static_cast<int>(U(0, 3)));
    const bool no_c = U(0, 1) < 0.5;
    double y = H;
    for (int i = 0; i < nl; ++i) {
        if (kind == Sweep::MohrCoulomb) {
            s.materials.push_back(mc(U(17, 26), no_c ? 0.0 : U(2, 60), U(20, 42), U(0, 0.4)));
        } else {
            const double g = U(22, 27), mb = U(0.3, 5), X = std::pow(10.0, U(std::log10(0.02), std::log10(0.5)));
            double sv = std::pow(10.0, U(-4, -2));
            if (kind == Sweep::HoekBrownTinyS) sv = U(0, 1) < 0.3 ? 0.0 : std::pow(10.0, U(-7, -4));
            s.materials.push_back(hb_material(g, g * H / (mb * X), mb, sv, U(0, 0.4)));
        }
        if (i + 1 == nl) {
            s.layers.push_back(LeLayer{{}, i});
        } else {
            y = U(y - 0.6 * H, y - 0.1 * H);
            s.layers.push_back(LeLayer{{{x0, y}, {x1, y}}, i});
        }
    }
    s.kh = U(0, 0.3);
    const Point2 A{U(-2 * H, -0.1 * H), H};
    const double xb = U(0.3 * toe, toe + H);
    const Point2 B{xb, xb < toe ? H * (1 - xb / toe) : 0.0};
    const double vx = B.x - A.x, vy = B.y - A.y, L = std::hypot(vx, vy), t = U(0.2, 1.5) * L;
    const double xc = 0.5 * (A.x + B.x) - vy / L * t, yc = 0.5 * (A.y + B.y) + vx / L * t;
    const double rad = std::hypot(A.x - xc, A.y - yc);
    if (U(0, 1) < 0.5) return {mirrored(s), circle(-xc, yc, rad)};
    return {s, circle(xc, yc, rad)};
}
// Equilibrio de fuerzas de toda la masa desde la tabla: N = N' + u l normal a la base y S = resistencia / F a lo largo
// de ella, contra el peso y kh W (α es el del marco interno, positivo hacia el pie; las fuerzas entre tajadas se anulan)
void expect_force_balance(const LeSection& s, const LeResult& r, const std::string& what) {
    double H = 0, V = 0, W = 0;
    for (const auto& t : r.slices) {
        const double a = t.alpha_deg * le_detail::kPi / 180.0;
        const double N = t.normal_force + t.pore_pressure * t.base_length, S = t.shear_strength / *r.factor_of_safety;
        H += N * std::sin(a) - S * std::cos(a) + s.kh * t.weight;
        V += N * std::cos(a) + S * std::sin(a) - t.weight;
        W += t.weight;
    }
    EXPECT_LT(std::fabs(H), 1e-6 * W) << what;
    EXPECT_LT(std::fabs(V), 1e-6 * W) << what;
}
// FS finito o vacío con aviso, y la tabla sin NaN
void expect_number_or_warning(const LeResult& r, const std::string& what) {
    EXPECT_TRUE(r.factor_of_safety.has_value() || !r.warnings.empty()) << what;
    if (r.factor_of_safety) EXPECT_TRUE(std::isfinite(*r.factor_of_safety)) << what;
    for (const auto& t : r.slices)
        for (double v : {t.normal_force, t.shear_strength, t.cohesion, t.friction_deg, t.interslice_normal_right,
                         t.interslice_shear_right})
            EXPECT_TRUE(std::isfinite(v)) << what;
}
struct SweepStats {
    int cases = 0, good = 0, balanced = 0;
    int converged[2] = {0, 0};
    double worst_gap = 0.0;
};
SweepStats run_sweep(Sweep kind, unsigned seed, bool check_gap, int balance_cases) {
    Uniform U(seed);
    SweepStats st;
    const LeMethod gle_methods[] = {LeMethod::Spencer, LeMethod::MorgensternPrice};
    for (int k = 0; k < 100; ++k) {
        const auto c = sweep_case(U, kind);
        LeResult bi;
        try {
            bi = run(c.section, c.surface, LeMethod::Bishop);
        } catch (const std::invalid_argument&) {
            continue;  // el círculo no forma masa: no es un caso
        }
        ++st.cases;
        expect_number_or_warning(bi, "Bishop case " + std::to_string(k));
        const bool good = bi.factor_of_safety && *bi.factor_of_safety >= 0.3 && *bi.factor_of_safety <= 5.0;
        st.good += good;
        bool balanced = false;
        LeResult res[2];
        for (int j = 0; j < 2; ++j) {
            const std::string what = std::string(le_detail::name(gle_methods[j])) + " case " + std::to_string(k);
            const auto& r = res[j] = run(c.section, c.surface, gle_methods[j]);
            expect_number_or_warning(r, what);
            if (!good || !r.factor_of_safety) continue;
            ++st.converged[j];
            const double gap = std::fabs(*r.factor_of_safety - *bi.factor_of_safety) / *bi.factor_of_safety;
            st.worst_gap = std::max(st.worst_gap, gap);
            // con kh > 0.2 Bishop simplificado (sin equilibrio horizontal) no es referencia: se compara Spencer con M-P
            if (check_gap && c.section.kh <= 0.2) EXPECT_LT(gap, 0.15) << what;
            if (st.balanced < balance_cases) {
                expect_force_balance(c.section, r, what);
                balanced = true;
            }
        }
        if (check_gap && good && c.section.kh > 0.2 && res[0].factor_of_safety && res[1].factor_of_safety) {
            const double sm = *res[1].factor_of_safety;
            EXPECT_LT(std::fabs(*res[0].factor_of_safety - sm) / sm, 0.10) << "Spencer vs M-P case " << k;
        }
        st.balanced += balanced;
    }
    std::printf("[sweep] cases %d, Bishop in [0.3, 5] %d, Spencer %d, M-P %d, worst |GLE - Bishop|/Bishop %.4f\n",
                st.cases, st.good, st.converged[0], st.converged[1], st.worst_gap);
    return st;
}
}  // namespace

// Mohr-Coulomb: c = 0 en la mitad de los casos, kh 0 a 0.3, ru 0 a 0.4. Spencer y M-P convergen en al menos el 95 %
// de los casos en que Bishop da FS en [0.3, 5]; con kh <= 0.2 quedan a menos de 15 % de Bishop y con kh > 0.2 Spencer
// queda a menos de 10 % de M-P, porque Bishop simplificado no cumple el equilibrio horizontal. 30 casos cierran el
// equilibrio de fuerzas. Medido el 4-nov-2026: convergen 95 de 95; los casos 39 y 43 (kh 0.30 y 0.28, c = 0) dan
// Bishop 0.631 y 0.457 frente a Spencer 0.824 y 0.606 y M-P 0.783 y 0.618 (24-35 % de Bishop, < 6 % entre Spencer y
// M-P), igual que con la iteración de punto fijo.
TEST(LimitEquilibrium, SweepMohrCoulombSpencerAndMorgensternPrice) {
    const auto st = run_sweep(Sweep::MohrCoulomb, 20261104u, true, 30);
    ASSERT_GE(st.good, 50);
    EXPECT_GE(st.converged[0], 0.95 * st.good);
    EXPECT_GE(st.converged[1], 0.95 * st.good);
    EXPECT_EQ(st.balanced, 30);
}

// Hoek-Brown con s de 1e-4 a 1e-2: Spencer converge en al menos el 95 % y M-P en al menos el 90 % (meta de robustez,
// no tolerancia de validación). Medido el 4-nov-2026: Spencer 88 de 92 (95.7 %), M-P 87 de 92 (94.6 %). Límite conocido
// del esquema de tangentes: en los casos 6, 18 y 41 la iteración de tangentes no se asienta y en el 42 y el 82 no hay
// raíz de λ (el residuo de momentos tiene un mínimo de 40 y 71 sin cruzar cero). Cuando no converge, el resultado es
// siempre FS vacío con aviso (expect_number_or_warning).
TEST(LimitEquilibrium, SweepHoekBrownSpencerAndMorgensternPrice) {
    const auto st = run_sweep(Sweep::HoekBrown, 20261105u, false, 0);
    ASSERT_GE(st.good, 50);
    EXPECT_GE(st.converged[0], 0.95 * st.good);
    EXPECT_GE(st.converged[1], 0.90 * st.good);
}

// Hoek-Brown con s < 1e-4 (y s = 0): sin umbral, pero nunca NaN ni FS vacío sin aviso
TEST(LimitEquilibrium, SweepHoekBrownTinySNeverSilent) {
    const auto st = run_sweep(Sweep::HoekBrownTinyS, 20261106u, false, 0);
    EXPECT_GE(st.cases, 50);
}

