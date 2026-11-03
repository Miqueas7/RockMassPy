#include <gtest/gtest.h>

#include <cmath>
#include <limits>

#include "error_of.hpp"
#include "rockmasspy/bench.hpp"

using namespace rockmasspy;

namespace {
const double kNan = std::numeric_limits<double>::quiet_NaN();
const double kInf = std::numeric_limits<double>::infinity();
const double kPi = 3.14159265358979323846;
// cara que deja un ancho W con banco H e interrampa dada (inversa de bench_width)
double face_for(double h, double ir, double w) { return std::atan(1.0 / (1.0 / std::tan(ir * kPi / 180) - w / h)) * 180 / kPi; }
}  // namespace

TEST(Bench, RitchieModified) {
    // Fig. 3.3 imprime 4.6 m para la constante (errata); la ec. 3.1 da 4.5
    EXPECT_NEAR(ritchie_berm_width(12).width_m, 6.9, 1e-12);
    EXPECT_NEAR(ritchie_berm_width(15).width_m, 7.5, 1e-12);
    EXPECT_EQ(ritchie_berm_width(12).info.method_id, "Berm-ModifiedRitchie");
    EXPECT_FALSE(error_of([] { ritchie_berm_width(0); }).empty());
    EXPECT_NE(error_of([] { ritchie_berm_width(kNan); }).find("bench_height_m"), std::string::npos);
}

TEST(Bench, Figure38Widths) {
    EXPECT_NEAR(bench_width(12, 27, 65), 17.956, 1e-3);
    EXPECT_NEAR(bench_width(12, 27, 81), 21.651, 1e-3);
    EXPECT_NEAR(bench_width(12, 27, 39), 8.733, 1e-3);
    EXPECT_NEAR(bench_width(24, 27, 71), 38.839, 1e-3);
    EXPECT_NEAR(bench_width(24, 27, 81), 43.301, 1e-3);
    EXPECT_NEAR(bench_width(24, 27, 49), 26.240, 1e-3);
    // publicados 41.4 y 34.7; el cálculo da 41.53 (la diferencia de 0.1 queda anotada)
    EXPECT_NEAR(face_for(12, 27, 10.0), 41.53, 0.01);
    EXPECT_NEAR(face_for(24, 27, 12.4), 34.67, 0.01);
    EXPECT_LT(bench_width(12, 60, 30), 0.0);  // puede ser negativo
    EXPECT_NEAR(bench_width(10, 45, 90), 10.0, 1e-12);
}

TEST(Bench, InterrampAngle) {
    EXPECT_NEAR(interramp_angle(12, 17.956, 65), 27.0, 1e-3);
    EXPECT_NEAR(interramp_angle(15, 8, 70), 48.098, 1e-3);
    EXPECT_NEAR(interramp_angle(10, 0, 90), 90.0, 1e-9);
}

TEST(Bench, Reliability) {
    const auto r = berm_reliability({5, 6.9, 7, 8}, 6.9);
    EXPECT_EQ(r.n, 4);
    EXPECT_EQ(r.n_meeting, 2);
    EXPECT_DOUBLE_EQ(r.reliability, 0.5);
    EXPECT_NEAR(r.width_mean, 6.725, 1e-12);
    EXPECT_DOUBLE_EQ(r.width_min, 5);
    EXPECT_DOUBLE_EQ(r.width_max, 8);
    EXPECT_EQ(r.info.method_id, "Berm-Reliability-RyanPryor2000");
}

TEST(Bench, ReliabilityBoundary) {
    EXPECT_EQ(berm_reliability({6.9 + 1e-12}, 6.9).n_meeting, 0);   // dentro de la holgura: no cumple
    EXPECT_EQ(berm_reliability({6.9 + 1e-8}, 6.9).n_meeting, 1);
    EXPECT_EQ(berm_reliability({6.9}, 6.9).n_meeting, 0);
}

TEST(Bench, Throws) {
    EXPECT_FALSE(error_of([] { bench_width(0, 27, 65); }).empty());
    EXPECT_NE(error_of([] { bench_width(12, 27, 0); }).find("face_angle_deg"), std::string::npos);
    EXPECT_FALSE(error_of([] { bench_width(12, 27, 95); }).empty());
    EXPECT_NE(error_of([] { bench_width(12, 90, 65); }).find("interramp_deg"), std::string::npos);
    EXPECT_NE(error_of([] { bench_width(12, kNan, 65); }).find("interramp_deg"), std::string::npos);
    EXPECT_NE(error_of([] { bench_width(12, 27, kInf); }).find("face_angle_deg"), std::string::npos);
    EXPECT_FALSE(error_of([] { interramp_angle(12, -1, 65); }).empty());
    EXPECT_FALSE(error_of([] { interramp_angle(12, 8, 0); }).empty());
    EXPECT_NE(error_of([] { interramp_angle(12, kNan, 65); }).find("berm_width_m"), std::string::npos);
    EXPECT_NE(error_of([] { berm_reliability({}, 6.9); }).find("widths_m"), std::string::npos);
    EXPECT_NE(error_of([] { berm_reliability({5, kNan}, 6.9); }).find("widths_m[1]"), std::string::npos);
    EXPECT_NE(error_of([] { berm_reliability({5}, kNan); }).find("required_width_m"), std::string::npos);
}
