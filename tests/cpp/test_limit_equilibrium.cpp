#include <gtest/gtest.h>

#include <cmath>
#include <limits>

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
    const Solve r = zhu(sl, s, o, true, false, 1.5);
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
    // lo que llega en las tareas 2 y 3 no da un número
    bad([](LeSection& s, SlipSurface&, LeOptions&) { s.crack = LeTensionCrack{2.0, 0.5}; }, "not implemented yet (task 2)");
    bad([](LeSection& s, SlipSurface&, LeOptions&) { s.piezometric = std::vector<Point2>{{0, 50}, {180, 10}}; },
        "not implemented yet (task 2)");
    bad([](LeSection& s, SlipSurface&, LeOptions&) {
        s.materials[0].model = StrengthModel::HoekBrown;
        s.materials[0].hb = hb_params(50, 10, 0);
        s.materials[0].sigma_ci = 50.0;
    }, "not implemented yet (task 3)");
    has([] { le_factor_of_safety(fk(), fk_circle(), LeMethod::JanbuCorrected); }, "not implemented yet (task 2)");
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
