#include <gtest/gtest.h>

#include <cmath>
#include <limits>

#include "error_of.hpp"
#include "rockmasspy/slip_search.hpp"

using namespace rockmasspy;

namespace {
const double kNan = std::numeric_limits<double>::quiet_NaN();

LeMaterial mc(double g, double c, double phi) {
    LeMaterial m;
    m.unit_weight = g; m.cohesion = c; m.friction_deg = phi;
    return m;
}
std::vector<Point2> mirror(const std::vector<Point2>& p) {
    std::vector<Point2> q(p.rbegin(), p.rend());
    for (auto& v : q) v.x = -v.x;
    return q;
}
LeSection mirrored(LeSection s) {
    s.surface = mirror(s.surface);
    for (auto& l : s.layers)
        if (!l.bottom.empty()) l.bottom = mirror(l.bottom);
    return s;
}
CircularGrid grid(double x0, double x1, double y0, double y1, int nx = 20, int ny = 20, int nr = 11) {
    CircularGrid g;
    g.x_min = x0; g.x_max = x1; g.y_min = y0; g.y_max = y1; g.nx = nx; g.ny = ny; g.n_radii = nr;
    return g;
}
SearchOptions opts(LeMethod m, bool refine = true) {
    SearchOptions o;
    o.method = m;
    o.refine = refine;
    return o;
}
double fs(const SearchResult& r) {
    EXPECT_TRUE(r.best.factor_of_safety.has_value());
    return r.best.factor_of_safety.value_or(kNan);
}
bool has(const std::vector<std::string>& v, const std::string& s) {
    for (const auto& w : v)
        if (w.find(s) != std::string::npos) return true;
    return false;
}

// ACADS 1(a), Slide problema 1: la cara mira a la izquierda; malla de centros del manual
LeSection acads1a() {
    LeSection s;
    s.surface = {{20, 25}, {30, 25}, {50, 35}, {70, 35}};
    s.layers = {LeLayer{{}, 0}};
    s.materials = {mc(20, 3, 19.6)};
    s.model_base_y = 20;
    return s;
}
CircularGrid acads1a_grid() { return grid(22.8, 43.7, 42.3, 62.6); }

// ACADS 1(c) y 1(d), Slide problemas 3 y 4: contactos leídos de la figura 3.1 (plan 3C, «Fuentes verificadas»)
LeSection acads1c(double kh = 0.0) {
    LeSection s;
    s.surface = {{20, 25}, {30, 25}, {50, 35}, {70, 35}};
    s.materials = {mc(19.5, 0, 38), mc(19.5, 5.3, 23), mc(19.5, 7.2, 20)};
    s.layers = {LeLayer{{{20, 25}, {30, 25}, {40, 27}, {50, 29}, {54, 31}, {70, 31}}, 0},
                LeLayer{{{20, 25}, {30, 25}, {40, 27}, {52, 24}, {70, 24}}, 1}, LeLayer{{}, 2}};
    s.model_base_y = 20;
    s.kh = kh;
    return s;
}

// ACADS 3(a) y 3(b), Slide problemas 7 y 8: capa débil entre y = 26.5 y 27.0 (sin agua sobre ella)
LeSection acads3() {
    LeSection s;
    s.surface = {{20, 27.75}, {43, 27.75}, {67.5, 40}, {84, 40}};
    s.materials = {mc(18.84, 28.5, 20), mc(18.84, 0, 10)};
    s.layers = {LeLayer{{{20, 27.0}, {63.5, 27.0}, {84, 27.0}}, 0}, LeLayer{{{20, 26.5}, {84, 26.5}}, 1}, LeLayer{{}, 0}};
    s.model_base_y = 20;
    return s;
}
// Casos sintéticos de la revisión independiente (repro_circ.py, repro_block_malpha.py): tres estratos, la cara mira a
// la izquierda
LeSection review(std::vector<Point2> surf, std::vector<std::vector<Point2>> bots, std::vector<LeMaterial> mats, double base,
                 double kh) {
    LeSection s;
    s.surface = std::move(surf);
    for (std::size_t k = 0; k < bots.size(); ++k) s.layers.push_back(LeLayer{bots[k], static_cast<int>(k)});
    s.layers.push_back(LeLayer{{}, static_cast<int>(bots.size())});
    s.materials = std::move(mats);
    s.model_base_y = base;
    s.kh = kh;
    return s;
}
LeSection review_block() {
    LeSection s;
    s.surface = {{-27, 0}, {0, 0}, {27.4, 17.7}, {54.4, 17.7}};
    s.layers = {LeLayer{{{-27, -1.8}, {54.4, -1.8}}, 0}, LeLayer{{{-27, -3.3}, {54.4, -3.3}}, 1}, LeLayer{{}, 0}};
    s.materials = {mc(18.2, 35.5, 33.8), mc(22.4, 4.5, 9.4)};
    s.model_base_y = -8.3;
    s.kh = 0.105;
    return s;
}
double deg(const Point2& a, const Point2& b) { return std::atan2(a.y - b.y, a.x - b.x) * 180.0 / le_detail::kPi; }

BlockSearch acads3a_block() {
    BlockSearch b;
    b.weak_line = {{20, 26.75}, {84, 26.75}};
    return b;
}
}  // namespace

// Slide: Bishop 0.987, Spencer 0.986, GLE 0.986 (±1 %, R9); recalculado con afinado: Bishop 0.9857 en (30.16, 51.9, 26.9)
TEST(SlipSearch, Acads1aBishop) {
    const auto r = search_circular(acads1a(), acads1a_grid(), opts(LeMethod::Bishop));
    const double f = fs(r);
    EXPECT_NEAR(f, 0.987, 0.01 * 0.987);
    EXPECT_NEAR(f, 0.9857, 2e-3);
    ASSERT_TRUE(r.surface.circle.has_value());
    // el valle es largo en la diagonal (centro, radio): el centro no se fija al metro, pero la búsqueda no queda por
    // encima del círculo del prototipo
    SlipSurface proto;
    proto.circle = Circle{30.16, 51.9, 26.9};
    EXPECT_LE(f, *le_factor_of_safety(acads1a(), proto, LeMethod::Bishop).factor_of_safety + 1e-9);
    EXPECT_FALSE(has(r.warnings, "edge"));
    EXPECT_EQ(r.best.method, LeMethod::Bishop);
    EXPECT_EQ(r.info.verification, Verification::Secondary);
    // sin afinado, la malla ya queda a ±1 % de Slide y no por debajo del afinado
    const double coarse = fs(search_circular(acads1a(), acads1a_grid(), opts(LeMethod::Bishop, false)));
    EXPECT_NEAR(coarse, 0.987, 0.01 * 0.987);
    EXPECT_GE(coarse, f);
    // top: a lo más 10, ordenadas, la primera es la crítica
    ASSERT_FALSE(r.top.empty());
    EXPECT_LE(r.top.size(), 10u);
    EXPECT_EQ(r.top.front().second, f);
    for (std::size_t i = 1; i < r.top.size(); ++i) EXPECT_LE(r.top[i - 1].second, r.top[i].second);
    EXPECT_GT(r.evaluated, 4000);
    EXPECT_GE(r.discarded, 0);
    EXPECT_LT(r.discarded, r.evaluated);
}

TEST(SlipSearch, Acads1aSpencerAndGle) {
    for (LeMethod m : {LeMethod::Spencer, LeMethod::MorgensternPrice})
        EXPECT_NEAR(fs(search_circular(acads1a(), acads1a_grid(), opts(m))), 0.986, 0.01 * 0.986) << le_detail::name(m);
}

TEST(SlipSearch, OrdinaryMethodWorks) {
    const auto r = search_circular(acads1a(), acads1a_grid(), opts(LeMethod::Ordinary));
    EXPECT_EQ(r.best.method, LeMethod::Ordinary);
    const double f = fs(r);
    EXPECT_GT(f, 0.0);
    EXPECT_LE(f, fs(search_circular(acads1a(), acads1a_grid(), opts(LeMethod::Bishop))));
}

// Slide 1(c): Bishop 1.405, Spencer 1.375, GLE 1.374; 1(d), kh 0.15: 1.016, 0.991, 0.989 (±2 %, contactos de figura)
TEST(SlipSearch, Acads1cAnd1d) {
    struct Case { double kh; LeMethod m; double slide; };
    const Case cases[] = {{0.0, LeMethod::Bishop, 1.405},  {0.0, LeMethod::Spencer, 1.375},
                          {0.0, LeMethod::MorgensternPrice, 1.374}, {0.15, LeMethod::Bishop, 1.016},
                          {0.15, LeMethod::Spencer, 0.991}, {0.15, LeMethod::MorgensternPrice, 0.989}};
    for (const auto& c : cases) {
        const auto r = search_circular(acads1c(c.kh), acads1a_grid(), opts(c.m));
        EXPECT_NEAR(fs(r), c.slide, 0.02 * c.slide) << le_detail::name(c.m) << " kh " << c.kh;
    }
}

// Slide 3(a): Spencer 1.246 con búsqueda de bloque sobre y = 26.75 y ángulos 135-155 (pie) y 45-65 (cresta)
TEST(SlipSearch, Acads3aBlockSpencer) {
    const auto r = search_block(acads3(), acads3a_block(), opts(LeMethod::Spencer));
    const double f = fs(r);
    EXPECT_LE(f, 1.246 * 1.01);
    EXPECT_GE(f, 1.246 * 0.97);
    ASSERT_TRUE(r.surface.polyline.has_value());
    EXPECT_EQ(r.info.method_id, "Block-Search");
}

// 3(b): la búsqueda de bloque alrededor de la superficie de la Tabla 8.2 no encuentra un FS mayor (Spencer 1.2759)
TEST(SlipSearch, Acads3bBlockAroundGivenSurface) {
    SlipSurface given;
    given.polyline = std::vector<Point2>{{41.85, 27.75}, {44.0, 26.5}, {63.5, 27.0}, {73.31, 40.0}};
    const double f0 = *le_factor_of_safety(acads3(), given, LeMethod::Spencer).factor_of_safety;
    EXPECT_NEAR(f0, 1.2758, 3e-3);
    BlockSearch b;
    b.weak_line = {{44.0, 26.5}, {63.5, 27.0}};
    b.n_points = 2;
    const double a = std::atan2(1.25, -2.15) * 180.0 / le_detail::kPi, c = std::atan2(13.0, 9.81) * 180.0 / le_detail::kPi;
    b.left_angle_min = a - 5; b.left_angle_max = a + 5;
    b.right_angle_min = c - 5; b.right_angle_max = c + 5;
    b.n_angles = 3;
    const auto r = search_block(acads3(), b, opts(LeMethod::Spencer));
    EXPECT_LE(fs(r), f0 + 1e-9);
}

// F&K (Slide problema 21): la búsqueda alrededor del círculo publicado (120, 90, 80) no encuentra un FS mayor
TEST(SlipSearch, FredlundKrahnAroundPublishedCircle) {
    LeSection s;
    s.surface = {{0, 60}, {60, 60}, {140, 20}, {180, 20}};
    s.layers = {LeLayer{{}, 0}};
    s.materials = {mc(120, 600, 20)};
    SlipSurface c;
    c.circle = Circle{120, 90, 80};
    for (LeMethod m : {LeMethod::Bishop, LeMethod::Spencer}) {
        const double f0 = *le_factor_of_safety(s, c, m).factor_of_safety;
        const auto r = search_circular(s, grid(110, 130, 80, 100, 4, 4, 5), opts(m));
        EXPECT_LE(fs(r), f0 + 1e-9) << le_detail::name(m);
    }
}

TEST(SlipSearch, ReflectedSectionGivesSameFs) {
    const auto g = acads1a_grid();
    const auto a = search_circular(acads1a(), g, opts(LeMethod::Bishop));
    const auto b = search_circular(mirrored(acads1a()), grid(-g.x_max, -g.x_min, g.y_min, g.y_max), opts(LeMethod::Bishop));
    EXPECT_NEAR(fs(a), fs(b), 1e-6);
    EXPECT_NEAR(a.surface.circle->xc, -b.surface.circle->xc, 1e-9);
    EXPECT_EQ(a.evaluated, b.evaluated);
    auto blk = acads3a_block();
    blk.n_points = 8;
    blk.n_angles = 3;
    const auto c = search_block(acads3(), blk, opts(LeMethod::Spencer));
    blk.weak_line = mirror(blk.weak_line);
    const auto d = search_block(mirrored(acads3()), blk, opts(LeMethod::Spencer));
    EXPECT_NEAR(fs(c), fs(d), 1e-6);
    EXPECT_NEAR(c.surface.polyline->front().x, -d.surface.polyline->back().x, 1e-9);
}

TEST(SlipSearch, EdgeOfGridWarns) {
    const auto r = search_circular(acads1a(), grid(50, 60, 70, 80, 4, 4, 5), opts(LeMethod::Bishop, false));
    EXPECT_TRUE(r.best.factor_of_safety.has_value());
    EXPECT_TRUE(has(r.warnings, "critical centre on the edge of the search grid"));
}

TEST(SlipSearch, DeterministicBitForBit) {
    const auto a = search_circular(acads1c(), acads1a_grid(), opts(LeMethod::Spencer));
    const auto b = search_circular(acads1c(), acads1a_grid(), opts(LeMethod::Spencer));
    EXPECT_EQ(*a.best.factor_of_safety, *b.best.factor_of_safety);
    EXPECT_EQ(a.surface.circle->xc, b.surface.circle->xc);
    EXPECT_EQ(a.surface.circle->yc, b.surface.circle->yc);
    EXPECT_EQ(a.surface.circle->radius, b.surface.circle->radius);
    EXPECT_EQ(a.evaluated, b.evaluated);
    EXPECT_EQ(a.discarded, b.discarded);
    ASSERT_EQ(a.top.size(), b.top.size());
    for (std::size_t i = 0; i < a.top.size(); ++i) EXPECT_EQ(a.top[i].second, b.top[i].second);
    auto blk = acads3a_block();
    blk.n_points = 8;
    const auto c = search_block(acads3(), blk, opts(LeMethod::Spencer)), d = search_block(acads3(), blk, opts(LeMethod::Spencer));
    EXPECT_EQ(*c.best.factor_of_safety, *d.best.factor_of_safety);
    ASSERT_EQ(c.surface.polyline->size(), d.surface.polyline->size());
    for (std::size_t i = 0; i < c.surface.polyline->size(); ++i) {
        EXPECT_EQ((*c.surface.polyline)[i].x, (*d.surface.polyline)[i].x);
        EXPECT_EQ((*c.surface.polyline)[i].y, (*d.surface.polyline)[i].y);
    }
}

// Superficies que no forman masa o con masa menor que min_mass_area: se descartan y se cuentan
TEST(SlipSearch, DiscardsAndCounts) {
    auto o = opts(LeMethod::Bishop, false);
    o.min_mass_area = 1e9;
    const auto r = search_circular(acads1a(), grid(22.8, 43.7, 42.3, 62.6, 4, 4, 5), o);
    EXPECT_FALSE(r.best.factor_of_safety.has_value());
    EXPECT_EQ(r.evaluated, r.discarded);
    EXPECT_GT(r.evaluated, 0);
    EXPECT_TRUE(r.top.empty());
    EXPECT_TRUE(has(r.warnings, "no valid slip surface found"));
    // una línea débil por encima de la superficie no da superficies
    BlockSearch b;
    b.weak_line = {{20, 50}, {84, 50}};
    const auto q = search_block(acads3(), b, opts(LeMethod::Spencer));
    EXPECT_FALSE(q.best.factor_of_safety.has_value());
    EXPECT_EQ(q.evaluated, 0);
}

// Una piezométrica que no cubre la superficie descartaba en silencio cada superficie que la cruza (revisión, sondeo
// p9: F&K con la piezométrica desde x = 100 daba FS 33.4 con 5306 de 5605 descartadas). Ahora lanza.
TEST(SlipSearch, PiezometricMustCoverTheSurface) {
    LeSection s;
    s.surface = {{0, 60}, {60, 60}, {140, 20}, {180, 20}};
    s.layers = {LeLayer{{}, 0}};
    s.materials = {mc(120, 600, 20)};
    s.model_base_y = 0;
    s.water_unit_weight = 62.4;
    s.piezometric = std::vector<Point2>{{100, 30}, {180, 20}};
    const std::string e = error_of([&] { search_circular(s, grid(110, 130, 80, 100)); });
    EXPECT_NE(e.find("piezometric"), std::string::npos) << e;
    BlockSearch b;
    b.weak_line = {{0, 30}, {180, 30}};
    EXPECT_NE(error_of([&] { search_block(s, b); }).find("piezometric"), std::string::npos);
    s.piezometric = std::vector<Point2>{{0, 30}, {100, 30}, {180, 20}};  // completa: busca
    EXPECT_TRUE(search_circular(s, grid(110, 130, 80, 100, 4, 4, 5)).best.factor_of_safety.has_value());
}

TEST(SlipSearch, InvalidInputsNameTheField) {
    const auto s = acads1a();
    const auto g = acads1a_grid();
    auto bad = g;
    bad.x_min = kNan;
    EXPECT_NE(error_of([&] { search_circular(s, bad); }).find("grid.x_min"), std::string::npos);
    bad = g;
    bad.nx = 0;
    EXPECT_NE(error_of([&] { search_circular(s, bad); }).find("grid.nx"), std::string::npos);
    bad = g;
    bad.n_radii = 1;
    EXPECT_NE(error_of([&] { search_circular(s, bad); }).find("grid.n_radii"), std::string::npos);
    bad = g;
    bad.x_max = bad.x_min;
    EXPECT_NE(error_of([&] { search_circular(s, bad); }).find("grid.x_max"), std::string::npos);
    auto o = opts(LeMethod::Bishop);
    o.min_mass_area = -1;
    EXPECT_NE(error_of([&] { search_circular(s, g, o); }).find("min_mass_area"), std::string::npos);
    auto ss = s;
    ss.materials[0].cohesion = kNan;
    EXPECT_NE(error_of([&] { search_circular(ss, g); }).find("materials[0].cohesion"), std::string::npos);
    auto b = acads3a_block();
    b.left_angle_min = 45;
    EXPECT_NE(error_of([&] { search_block(acads3(), b); }).find("left_angle_min"), std::string::npos);
    b = acads3a_block();
    b.right_angle_max = 90;
    EXPECT_NE(error_of([&] { search_block(acads3(), b); }).find("right_angle_max"), std::string::npos);
    b = acads3a_block();
    b.right_angle_min = 60;
    b.right_angle_max = 50;
    EXPECT_NE(error_of([&] { search_block(acads3(), b); }).find("right_angle_max"), std::string::npos);
    b = acads3a_block();
    b.weak_line = {{20, 26.75}};
    EXPECT_NE(error_of([&] { search_block(acads3(), b); }).find("weak_line"), std::string::npos);
    b = acads3a_block();
    b.n_points = 1;
    EXPECT_NE(error_of([&] { search_block(acads3(), b); }).find("n_points"), std::string::npos);
}

// Revisión I1: un valle diagonal en (yc, R) atascaba al afinado solo por ejes (1.4803); fuerza bruta 1.4650 (+0.5 %)
TEST(SlipSearch, ReviewDiagonalValley) {
    const auto A = review({{-60, 0}, {0, 0}, {57.41, 37.52}, {117.41, 37.52}},
                          {{{-60, 26.88}, {117.41, 28.10}}, {{-60, 10.24}, {117.41, 8.98}}},
                          {mc(21.69, 17.31, 34.15), mc(18.41, 25.06, 36.43), mc(21.77, 14.21, 31.39)}, -18.61, 0.007);
    EXPECT_LE(fs(search_circular(A, grid(-22.51, 64.92, 39.39, 93.79), opts(LeMethod::Bishop))), 1.4723);
}

// Revisión I2: mínimo somero que la malla con radios uniformes y un solo arranque no veía (0.7643); el círculo
// (0.276, 27.289, 21.342) da 0.7160 con Bishop (+0.5 %: 0.7196). El centro final es interior: sin aviso de borde.
TEST(SlipSearch, ReviewShallowMinimum) {
    const auto B = review({{-31.07, 0}, {0, 0}, {27.23, 25.86}, {73.4, 25.86}},
                          {{{-31.07, 18.95}, {73.4, 18.86}}, {{-31.07, 7.61}, {73.4, 6.79}}},
                          {mc(18.9, 29.67, 16.93), mc(20.47, 2.91, 31.51), mc(19.76, 19.77, 22.16)}, -21.83, 0.157);
    const auto r = search_circular(B, grid(-15.52, 32.4, 27.16, 64.66), opts(LeMethod::Bishop));
    EXPECT_LE(fs(r), 0.7196);
    const auto& c = *r.surface.circle;
    ASSERT_TRUE(c.xc > -15.52 && c.xc < 32.4 && c.yc > 27.16 && c.yc < 64.66);
    EXPECT_FALSE(has(r.warnings, "edge"));
}

// Revisión I3: el afinado del bloque salía de los ángulos y caía en una masa de pie empinado con mα < 0.2 (Bishop 0.673,
// área 53). Ahora respeta los ángulos y no trae el aviso. El afinado sí baja la base al piso de la capa débil (-3.3),
// como en ACADS 3(a): la cota de comparación es la malla sin afinar con la línea débil en y = -3.28 (Bishop 1.1179).
TEST(SlipSearch, ReviewBlockRefinementKeepsAnglesAndMalpha) {
    BlockSearch b;
    b.weak_line = {{-27, -2.55}, {54.4, -2.55}};
    for (LeMethod m : {LeMethod::Bishop, LeMethod::JanbuSimplified, LeMethod::Spencer}) {
        const auto r = search_block(review_block(), b, opts(m));
        const auto& p = *r.surface.polyline;
        EXPECT_GE(deg(p[0], p[1]), b.left_angle_min - 1e-6) << le_detail::name(m);
        EXPECT_LE(deg(p[0], p[1]), b.left_angle_max + 1e-6) << le_detail::name(m);
        EXPECT_GE(deg(p.back(), p[p.size() - 2]), b.right_angle_min - 1e-6) << le_detail::name(m);
        EXPECT_LE(deg(p.back(), p[p.size() - 2]), b.right_angle_max + 1e-6) << le_detail::name(m);
        EXPECT_FALSE(has(r.best.warnings, "m-alpha")) << le_detail::name(m);
        EXPECT_FALSE(has(r.warnings, "m-alpha")) << le_detail::name(m);
        const double grid_fs = fs(search_block(review_block(), b, opts(m, false)));
        EXPECT_GT(r.best.sliding_mass_area, 300.0) << le_detail::name(m);
        if (m == LeMethod::Bishop) {
            auto deep = b;
            deep.weak_line = {{-27, -3.28}, {54.4, -3.28}};
            const double deep_fs = fs(search_block(review_block(), deep, opts(m, false)));
            EXPECT_GE(fs(r), 0.98 * deep_fs);
            EXPECT_LE(fs(r), grid_fs);
        }
    }
}

// Revisión I3 (b) y (c): las superficies con el aviso de mα se descartan y se cuentan aparte, con nota; los avisos de
// la crítica pasan a la búsqueda
TEST(SlipSearch, MalphaDiscardedAndCounted) {
    BlockSearch b;
    b.weak_line = {{-27, -2.55}, {54.4, -2.55}};
    b.left_angle_min = 95;  // pies casi verticales: mα bajo con Bishop
    b.left_angle_max = 175;
    const auto r = search_block(review_block(), b, opts(LeMethod::Bishop, false));
    EXPECT_GT(r.discarded_malpha, 0);
    EXPECT_LE(r.discarded_malpha, r.discarded);
    EXPECT_TRUE(has(r.notes, "discarded for m-alpha below 0.2"));
    EXPECT_EQ(r.warnings, r.best.warnings);
}

// Revisión I4: un estrato que no cubre la sección se rechaza al validar, no se descarta superficie por superficie
TEST(SlipSearch, ShortLayerBottomThrows) {
    auto s = acads1a();
    s.layers = {LeLayer{{{20, 30}, {45, 30}}, 0}, LeLayer{{}, 0}};
    EXPECT_NE(error_of([&] { search_circular(s, acads1a_grid()); }).find("layers[0].bottom"), std::string::npos);
    EXPECT_NE(error_of([&] { search_block(s, acads3a_block()); }).find("layers[0].bottom"), std::string::npos);
}
