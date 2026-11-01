/**
 * @file rmr_common.hpp
 * @brief Piezas comunes de las ediciones del RMR: agua, orientación de discontinuidades, ajuste y clase.
 *
 * Valor justo en un límite de rango: se toma la clase menos favorable (desigualdad estricta hacia la mejor).
 */

#pragma once

#include <string>

#include "rockmasspy/validation.hpp"

namespace rockmasspy {

enum class Water { Dry, Damp, Wet, Dripping, Flowing };
enum class OrientationClass { VeryFavourable, Favourable, Fair, Unfavourable, VeryUnfavourable };
enum class Application { Tunnel, Foundation, Slope };
enum class StrikeRelation { PerpendicularDriveWithDip, PerpendicularDriveAgainstDip, Parallel };

struct RmrClass {
    int number;
    std::string roman;
    std::string label;
};

/// Clase de orientación de las discontinuidades respecto al eje del túnel; dip_deg en [0, 90].
inline OrientationClass tunnel_orientation_class(StrikeRelation rel, double dip_deg) {
    validation::require_in_range(dip_deg, 0.0, 90.0, "dip_deg");
    // En 20 y 45 grados cada relación toma la clase menos favorable de las dos vecinas.
    switch (rel) {
        case StrikeRelation::PerpendicularDriveWithDip:
            if (dip_deg <= 20.0) return OrientationClass::Fair;
            return dip_deg <= 45.0 ? OrientationClass::Favourable : OrientationClass::VeryFavourable;
        case StrikeRelation::PerpendicularDriveAgainstDip:
            if (dip_deg < 20.0) return OrientationClass::Fair;
            return dip_deg <= 45.0 ? OrientationClass::Unfavourable : OrientationClass::Fair;
        default:
            return dip_deg < 45.0 ? OrientationClass::Fair : OrientationClass::VeryUnfavourable;
    }
}

/// Ajuste (puntos, <= 0) por orientación según la aplicación.
inline int orientation_adjustment(OrientationClass c, Application app) {
    static const int table[3][5] = {{0, -2, -5, -10, -12}, {0, -2, -7, -15, -25}, {0, -5, -25, -50, -60}};
    return table[static_cast<int>(app)][static_cast<int>(c)];
}

inline RmrClass rmr_class(double rmr) {
    validation::require_finite(rmr, "rmr");
    if (rmr > 80.0) return {1, "I", "Very good"};
    if (rmr > 60.0) return {2, "II", "Good"};
    if (rmr > 40.0) return {3, "III", "Fair"};
    if (rmr > 20.0) return {4, "IV", "Poor"};
    return {5, "V", "Very poor"};
}

}  // namespace rockmasspy
