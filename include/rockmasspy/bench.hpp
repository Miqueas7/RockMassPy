/**
 * @file bench.hpp
 * @brief Banco-berma: berma mínima de Ritchie modificada, ancho de berma, ángulo interrampa y confiabilidad.
 *
 * Fuente: Ryan & Pryor (2000) «Slope Stability in Surface Mining» (SME) cap. 3: ec. 3.1 (p. 28) W = 0.2 H + 4.5,
 * relación derivada por Call & Nicholas Inc. (Call 1992 no leído); la Fig. 3.3 imprime 4.6 m (errata). El ancho de
 * berma sale de la geometría H cot(interrampa) - H cot(cara) (Fig. 3.8, p. 32) y puede ser negativo. La confiabilidad
 * es la fracción de bancos con ancho final por encima del criterio (p. 29); un ancho igual al criterio con holgura
 * 1e-9 m cuenta como no cumple (lado menos favorable). Geometría pura sin MethodInfo. Los mensajes no repiten valores
 * salvo los de validation.
 */

#pragma once

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <vector>

#include "rockmasspy/method_info.hpp"
#include "rockmasspy/validation.hpp"

namespace rockmasspy {

struct RitchieWidth {
    double width_m;
    MethodInfo info;
};

struct BermReliability {
    double reliability;
    int n, n_meeting;
    double width_mean, width_min, width_max;
    MethodInfo info;
};

namespace bench_detail {
constexpr double kPi = 3.14159265358979323846;
inline double cot_deg(double d) { return 1.0 / std::tan(d * kPi / 180.0); }
inline void face(double f) {
    validation::require_finite(f, "face_angle_deg");
    validation::require(f > 0.0 && f <= 90.0, "face_angle_deg", "must be within (0, 90]", f);
}
}  // namespace bench_detail

/// Berma mínima de Ritchie modificada: 0.2 H + 4.5 (ec. 3.1).
inline RitchieWidth ritchie_berm_width(double bench_height_m) {
    validation::require_positive(bench_height_m, "bench_height_m");
    return {0.2 * bench_height_m + 4.5,
            {"Berm-ModifiedRitchie", Verification::PrimaryLaterAuthors,
             "Ryan & Pryor (2000) Slope Stability in Surface Mining (SME) ch. 3, eq. 3.1 (p. 28), relation derived by "
             "Call & Nicholas Inc. (Call 1992 not read); Fig. 3.3 prints 4.6 m (erratum)"}};
}

/// Ancho de berma H cot(interrampa) - H cot(cara); puede ser negativo.
inline double bench_width(double bench_height_m, double interramp_deg, double face_angle_deg) {
    using namespace bench_detail;
    validation::require_positive(bench_height_m, "bench_height_m");
    validation::require_finite(interramp_deg, "interramp_deg");
    validation::require(interramp_deg > 0.0 && interramp_deg < 90.0, "interramp_deg", "must be within (0, 90)",
                        interramp_deg);
    face(face_angle_deg);
    return bench_height_m * (cot_deg(interramp_deg) - cot_deg(face_angle_deg));
}

/// Ángulo interrampa en grados: atan(H / (W + H cot(cara))).
inline double interramp_angle(double bench_height_m, double berm_width_m, double face_angle_deg) {
    using namespace bench_detail;
    validation::require_positive(bench_height_m, "bench_height_m");
    validation::require_non_negative(berm_width_m, "berm_width_m");
    face(face_angle_deg);
    return std::atan(bench_height_m / (berm_width_m + bench_height_m * cot_deg(face_angle_deg))) * 180.0 / kPi;
}

/// Confiabilidad de berma: cumple si ancho > requerido + 1e-9.
inline BermReliability berm_reliability(const std::vector<double>& widths_m, double required_width_m) {
    validation::require_finite(required_width_m, "required_width_m");
    if (widths_m.empty()) throw std::invalid_argument("Domain error [RockMassPy]: parameter 'widths_m' must not be empty");
    int meet = 0;
    double sum = 0.0;
    for (std::size_t i = 0; i < widths_m.size(); ++i) {
        validation::require_finite(widths_m[i], "widths_m[" + std::to_string(i) + "]");
        sum += widths_m[i];
        if (widths_m[i] > required_width_m + 1e-9) ++meet;
    }
    const int n = static_cast<int>(widths_m.size());
    const auto mm = std::minmax_element(widths_m.begin(), widths_m.end());
    return {static_cast<double>(meet) / n, n, meet, sum / n, *mm.first, *mm.second,
            {"Berm-Reliability-RyanPryor2000", Verification::PrimaryLaterAuthors,
             "Ryan & Pryor (2000) ch. 3: share of benches with final width at or above the criterion (p. 29), widths "
             "from H cot(interramp) - H cot(face) as in Fig. 3.8 (p. 32); a width equal to the criterion within 1e-9 m "
             "counts as not meeting"}};
}

}  // namespace rockmasspy
