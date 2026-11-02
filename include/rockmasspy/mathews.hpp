/**
 * @file mathews.hpp
 * @brief Factores A y C del gráfico de estabilidad de Mathews (según Potvin 1988) y radio hidráulico [V1].
 *
 * Fuente: Potvin (1988), Empirical open stope design in Canada, tesis PhD, UBC (páginas impresa / física del PDF).
 * Ajuste medido de cada curva contra la lámina (render a 250 dpi, tinta de la curva menos la fórmula):
 *  - Factor A, Fig. 7.4 (p. 175 / 197): recta (2, 0.1)-(10, 1.0); desvío máximo 0.019 entre 2 y 10
 *    (0.003 en el tramo plano). Es un gráfico, sin ecuación escrita.
 *  - Factor C deslizamiento, Fig. 7.21 (p. 204 / 226): desvío máximo 0.044. Gráfico sin ecuación.
 *  - Factor C gravedad, Fig. 7.20 (p. 204 / 226): la curva dibujada se aparta hasta 0.13 (≈1.3° en horizontal)
 *    de la ecuación de la p. 232 / 254, atribuido a distorsión del dibujo o del escaneo (marcas del eje x
 *    desiguales; la curva termina pasada la marca de 90°); manda la ecuación 8 - 6 cos.
 * Los errores incluyen los empalmes. El 8 - 7 cos de Mathews et al. (1980) no se usa (resolución R1).
 */

#pragma once

#include <cmath>
#include <string>

#include "rockmasspy/method_info.hpp"
#include "rockmasspy/validation.hpp"

namespace rockmasspy {

struct FactorResult {
    double value;
    MethodInfo info;
};

namespace detail_mw {
inline MethodInfo potvin(const std::string& what) {
    return {"Mathews-Potvin1988", Verification::Primary,
            "Potvin (1988) Empirical open stope design in Canada, PhD thesis UBC: " + what};
}
}  // namespace detail_mw

/// Factor de esfuerzo A: recta por (2, 0.1) y (10, 1.0); en relajación (σ1 <= 0) vale 1.0 (R4).
inline FactorResult mathews_factor_a(double ucs_mpa, double induced_stress_mpa) {
    validation::require_positive(ucs_mpa, "ucs_mpa");
    validation::require_finite(induced_stress_mpa, "induced_stress_mpa");
    double a = 1.0;
    if (induced_stress_mpa > 0.0) {
        const double r = ucs_mpa / induced_stress_mpa;
        a = r <= 2.0 ? 0.1 : (r >= 10.0 ? 1.0 : 0.1125 * r - 0.125);
    }
    return {a, detail_mw::potvin("Fig. 7.4 (p. 175), text pp. 174, 207 and 227; straight line through (2, 0.1) and "
                                 "(10, 1.0); digitization check max deviation 0.019")};
}

/// Factor C por gravedad y lajamiento: 8 - 6·cos(α), α en [0, 90].
inline FactorResult mathews_factor_c_gravity(double surface_inclination_deg) {
    validation::require_in_range(surface_inclination_deg, 0.0, 90.0, "surface_inclination_deg");
    const double rad = surface_inclination_deg * std::acos(-1.0) / 180.0;
    return {8.0 - 6.0 * std::cos(rad),
            detail_mw::potvin("equation on p. 232 (8 - 6 cos of the surface inclination), Fig. 7.20 (p. 204); "
                              "gravity fall and slabbing; Fig. 7.20 drawn curve deviates up to 0.13 (~1.3 deg "
                              "horizontally) from the equation, attributed to drawing/scan distortion; the equation "
                              "governs")};
}

/// Factor C por deslizamiento: 8 hasta 30°, luego 8 - (β - 30)/10 hasta 2 en 90°.
inline FactorResult mathews_factor_c_sliding(double joint_dip_deg) {
    validation::require_in_range(joint_dip_deg, 0.0, 90.0, "joint_dip_deg");
    const double c = joint_dip_deg <= 30.0 ? 8.0 : 8.0 - (joint_dip_deg - 30.0) / 10.0;
    return {c, detail_mw::potvin("Fig. 7.21 (p. 204), text pp. 203 and 231; sliding on the critical joint; "
                                 "digitization check max deviation 0.044")};
}

/// Radio hidráulico = área / perímetro (m). Un área mayor que la de un círculo de ese perímetro es imposible.
inline double hydraulic_radius(double area_m2, double perimeter_m) {
    validation::require_positive(area_m2, "area_m2");
    validation::require_positive(perimeter_m, "perimeter_m");
    const double max_area = perimeter_m * perimeter_m / (4.0 * std::acos(-1.0));
    validation::require(area_m2 <= max_area, "area_m2",
                        "area too large for its perimeter (a circle of that perimeter has " +
                            validation::detail::num(max_area) + " m2)",
                        area_m2);
    return area_m2 / perimeter_m;
}

/// Radio hidráulico de una cara rectangular: w·l / (2·(w + l)).
inline double hydraulic_radius_rect(double width_m, double length_m) {
    validation::require_positive(width_m, "width_m");
    validation::require_positive(length_m, "length_m");
    return width_m * length_m / (2.0 * (width_m + length_m));
}

}  // namespace rockmasspy
