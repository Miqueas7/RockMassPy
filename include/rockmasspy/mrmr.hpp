/**
 * @file mrmr.hpp
 * @brief MRMR de Laubscher (1990): puntajes, espaciamiento, FF/m, condición de juntas, ajustes y clase [V1].
 *
 * Fuente: Laubscher (1990), J. SAIMM 90(10) 257-273 (páginas impresa / física del PDF):
 *  - Tabla I parte 1 (p. 260 / 4): clases 1 a 5 de 20 puntos, subclases A (mitad superior) y B.
 *  - Tabla I parte 2 (p. 260 / 4): puntajes de IRS (0-20), RQD (0-15) y FF/m (0-40, 1 a 3 familias).
 *  - Fig. 2 (p. 259 / 3): espaciamiento (0-25) con ecuaciones escritas, x en cm; 4 o más familias usan las tres más juntas.
 *  - Tabla I parte 3 (p. 261 / 5): condición de juntas = 40 x A x B x (C) x (D), por condición de agua.
 *  - Tabla VI (p. 264 / 8): meteorización. Voladura y resumen de ajustes (p. 266 / 10).
 * Erratas de los ejemplos impresos (las pruebas usan las ecuaciones y la tabla, resoluciones R14-R21):
 *  - p. 259: el ejemplo de una familia imprime 0.88 y su ecuación da 0.8985; con dos familias imprime 0.81 x 0.86
 *    y la ecuación da 0.82 x 0.88.
 *  - p. 261: el ejemplo rotula A = 70 y B = 65 y la tabla da 75 y 60; el producto, 27 %, sí calza.
 * Un valor toma el rango cuyo límite inferior impreso alcanza; en el hueco entre dos rangos, el menor (R14).
 */

#pragma once

#include <algorithm>
#include <cmath>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

#include "rockmasspy/method_info.hpp"
#include "rockmasspy/validation.hpp"

namespace rockmasspy {

enum class JointExpressionLarge { MultiWavyDirectional, UniDirectional, Curved, SlightUndulation, Straight };
enum class JointExpressionSmall {
    RoughStepped, SmoothStepped, SlickensidedStepped, RoughUndulating, SmoothUndulating,
    SlickensidedUndulating, RoughPlanar, SmoothPlanar, Polished
};
enum class JointFilling90 {
    None, NonSofteningCoarse, NonSofteningMedium, NonSofteningFine, SoftCoarse, SoftMedium, SoftFine,
    GougeThinnerThanIrregularities, GougeThickerThanIrregularities
};
enum class JointWater90 { Dry, Moist, ModeratePressure, HighPressure };
enum class Weathering90 { Fresh, Slight, Moderate, High, Complete, ResidualSoil };
enum class Blasting90 { Boring, SmoothWall, GoodConventional, Poor };

inline int rating_irs90(double irs_mpa) {
    validation::require_non_negative(irs_mpa, "irs_mpa");
    if (irs_mpa > 185) return 20;
    static const double lo[] = {165, 145, 125, 105, 85, 65, 45, 35, 25, 12, 5, 1};
    static const int pts[] = {18, 16, 14, 12, 10, 8, 6, 5, 4, 3, 2, 1};
    for (int i = 0; i < 12; ++i)
        if (irs_mpa >= lo[i]) return pts[i];
    return 0;
}

inline int rating_rqd90(double rqd_pct) {
    validation::require_in_range(rqd_pct, 0.0, 100.0, "rqd_pct");
    static const double lo[] = {97, 84, 71, 56, 44, 31, 17, 4};
    static const int pts[] = {15, 14, 12, 10, 8, 6, 4, 2};
    for (int i = 0; i < 8; ++i)
        if (rqd_pct >= lo[i]) return pts[i];
    return 0;
}

/// Espaciamiento en m (1 a n familias); ecuaciones de la Fig. 2 con x en cm, cada factor acotado a [0, 1] (R15).
inline double rating_joint_spacing90(const std::vector<double>& spacings_m) {
    validation::require(!spacings_m.empty(), "spacings_m", "at least one joint set spacing is required", 0.0);
    for (double s : spacings_m) validation::require_positive(s, "spacings_m");
    std::vector<double> s = spacings_m;
    std::sort(s.begin(), s.end());
    if (s.size() > 3) s.resize(3);  // regla del método (p. 259): las tres familias más juntas
    auto f = [](double a, double b, double m) {
        return std::clamp((a * std::log10(m * 100.0) + b) / 100.0, 0.0, 1.0);
    };
    switch (s.size()) {
        case 1: return 25.0 * f(26.4, 45, s[0]);
        case 2: return 25.0 * f(25.9, 38, s[0]) * f(30.0, 28, s[1]);
        default: return 25.0 * f(25.9, 30, s[0]) * f(29.6, 20, s[1]) * f(33.3, 10, s[2]);
    }
}

/// FF/m (Tabla I): sin interpolar, entre dos filas la de FF/m mayor; bajo 0.1 la fila 0.1; sobre 40 da 0 (R16).
inline int rating_ff90(double ff_per_m, int joint_sets, double core_recovery_pct = 100.0) {
    validation::require_positive(ff_per_m, "ff_per_m");
    validation::require(joint_sets >= 1, "joint_sets", "must be at least 1", joint_sets);
    validation::require_positive(core_recovery_pct, "core_recovery_pct");
    validation::require(core_recovery_pct <= 100.0, "core_recovery_pct", "must be within (0, 100]", core_recovery_pct);
    static const double ff[] = {0.10, 0.15, 0.20, 0.25, 0.30, 0.50, 0.80, 1.00, 1.50,
                                2.00, 3.00, 5.00, 7.00, 10.0, 15.0, 20.0, 30.0, 40.0};
    static const int tab[18][3] = {{40, 40, 40}, {40, 40, 40}, {40, 40, 38}, {40, 38, 36}, {38, 36, 34}, {36, 34, 31},
                                   {34, 31, 28}, {31, 28, 26}, {29, 26, 24}, {26, 24, 21}, {24, 21, 18}, {21, 18, 15},
                                   {18, 15, 12}, {15, 12, 10}, {12, 10, 7},  {10, 7, 5},   {7, 5, 2},    {5, 2, 0}};
    const double corrected = ff_per_m / (core_recovery_pct / 100.0);
    const int col = std::min(joint_sets, 3) - 1;
    for (int i = 0; i < 18; ++i)
        if (corrected <= ff[i]) return tab[i][col];
    return 0;
}

struct JointCondition90 {
    std::optional<JointExpressionLarge> large;
    std::optional<JointExpressionSmall> small;
    JointFilling90 filling = JointFilling90::None;
    bool altered_wall = false;
    std::optional<JointWater90> water;
};

/// Condición de juntas de una familia (0-40): 40 x A x B x (C) x (D) con los % de la columna de agua (Tabla I parte 3).
inline double joint_condition90(const JointCondition90& j) {
    static const int A[5][4] = {{100, 100, 95, 90}, {95, 90, 85, 80}, {85, 80, 75, 70}, {80, 75, 70, 65}, {75, 70, 65, 60}};
    static const int B[9][4] = {{95, 90, 85, 80}, {90, 85, 80, 75}, {85, 80, 75, 70}, {80, 75, 70, 65}, {75, 70, 65, 60},
                                {70, 65, 60, 55}, {65, 60, 55, 50}, {60, 55, 50, 45}, {55, 50, 45, 40}};
    static const int C[4] = {75, 70, 65, 60};
    static const int D[8][4] = {{90, 85, 80, 75}, {85, 80, 75, 70}, {80, 75, 70, 65}, {70, 65, 60, 55},
                                {60, 55, 50, 45}, {50, 45, 40, 35}, {45, 40, 35, 30}, {30, 20, 15, 10}};
    const auto large = validation::require_set(j.large, "large");
    const auto small = validation::require_set(j.small, "small");
    const auto water = validation::require_set(j.water, "water");
    const int w = static_cast<int>(water);
    double r = 40.0 * A[static_cast<int>(large)][w] / 100.0 * B[static_cast<int>(small)][w] / 100.0;
    if (j.altered_wall) r *= C[w] / 100.0;
    if (j.filling != JointFilling90::None) r *= D[static_cast<int>(j.filling) - 1][w] / 100.0;
    return r;
}

/// Tabla VI: columnas 1/2, 1, 2, 3 y 4+ años; se usa la mayor que no pasa de `years`, bajo 1/2 la de 1/2 (R19).
inline double weathering_adjustment90(Weathering90 degree, double years) {
    validation::require_positive(years, "years");
    static const int T[6][5] = {{100, 100, 100, 100, 100}, {88, 90, 92, 94, 96}, {82, 84, 86, 88, 90},
                                {70, 72, 74, 76, 78},      {54, 56, 58, 60, 62}, {30, 32, 34, 36, 38}};
    const int col = years >= 4 ? 4 : years >= 3 ? 3 : years >= 2 ? 2 : years >= 1 ? 1 : 0;
    return T[static_cast<int>(degree)][col];
}

inline double blasting_adjustment90(Blasting90 t) {
    static const double v[] = {100, 97, 94, 80};
    return v[static_cast<int>(t)];
}

/// Clase 1 a 5 de 20 puntos; subclase A en la mitad superior (Tabla I parte 1, R20).
inline std::string laubscher_class(double rating) {
    validation::require_non_negative(rating, "rating");
    static const double lower[] = {81, 61, 41, 21, 1};
    int i = 0;
    while (i < 4 && rating < lower[i]) ++i;
    return std::to_string(i + 1) + (rating >= lower[i] + 10.0 ? "A" : "B");
}

struct Mrmr90Input {
    double irs_mpa = validation::unset;
    double rqd_pct = validation::unset;
    std::vector<double> spacings_m;
    double ff_per_m = validation::unset;
    int joint_sets = 0;
    double core_recovery_pct = 100.0;
    double joint_condition = validation::unset;
    double weathering_pct = 100.0, orientation_pct = 100.0, stress_pct = 100.0, blasting_pct = 100.0;
};

struct Mrmr90Result {
    double irs_rating, rqd_rating, spacing_rating, ff_rating, joint_condition, rmr, adjustment, mrmr;
    std::string rmr_class, mrmr_class;
    MethodInfo info;
    std::vector<std::string> warnings;
};

inline Mrmr90Result mrmr90(const Mrmr90Input& in) {
    const double nan = std::numeric_limits<double>::quiet_NaN();
    const bool path_rqd = !std::isnan(in.rqd_pct) || !in.spacings_m.empty();
    const bool path_ff = !std::isnan(in.ff_per_m);
    if (path_rqd == path_ff) throw std::invalid_argument("pass rqd_pct and spacings_m, or ff_per_m and joint_sets");

    Mrmr90Result r{};
    r.irs_rating = rating_irs90(in.irs_mpa);
    r.rqd_rating = r.spacing_rating = r.ff_rating = nan;
    double rock = r.irs_rating;
    if (path_rqd) {
        r.rqd_rating = rating_rqd90(in.rqd_pct);
        r.spacing_rating = rating_joint_spacing90(in.spacings_m);
        rock += r.rqd_rating + r.spacing_rating;
    } else {
        r.ff_rating = rating_ff90(in.ff_per_m, in.joint_sets, in.core_recovery_pct);
        rock += r.ff_rating;
        if (in.ff_per_m / (in.core_recovery_pct / 100.0) > 40.0)
            r.warnings.push_back("FF/m above Table I (40 per m): rating 0");
    }
    validation::require_in_range(in.joint_condition, 0.0, 40.0, "joint_condition");
    r.joint_condition = in.joint_condition;
    r.rmr = rock + in.joint_condition;

    struct Adj { double v; const char* name; double lo, hi; const char* label; };
    const Adj adj[] = {{in.weathering_pct, "weathering_pct", 30, 100, "weathering"},
                       {in.orientation_pct, "orientation_pct", 63, 100, "orientation"},
                       {in.stress_pct, "stress_pct", 60, 120, "induced stress"},
                       {in.blasting_pct, "blasting_pct", 80, 100, "blasting"}};
    r.adjustment = 1.0;
    for (const auto& a : adj) validation::require_positive(a.v, a.name);
    for (const auto& a : adj) {
        r.adjustment *= a.v / 100.0;
        if (a.v < a.lo || a.v > a.hi)
            r.warnings.push_back(std::string(a.label) + " adjustment outside " + validation::detail::num(a.lo) + "-" +
                                 validation::detail::num(a.hi) + " % (Laubscher 1990, p. 266)");
    }
    r.mrmr = r.rmr * r.adjustment;
    r.rmr_class = laubscher_class(r.rmr);
    r.mrmr_class = laubscher_class(r.mrmr);
    r.info = {"MRMR-Laubscher1990", Verification::Primary,
              "Laubscher (1990) A geomechanics classification system for the rating of rock mass in mine design, "
              "J. SAIMM 90(10) 257-273: Table I, Fig. 2 equations and adjustments, pp. 259-266"};
    return r;
}

}  // namespace rockmasspy
