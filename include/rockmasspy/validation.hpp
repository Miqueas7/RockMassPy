/**
 * @file validation.hpp
 * @brief Validación de dominio en la frontera: toda entrada numérica pasa por aquí.
 *
 * NaN e infinito siempre se rechazan (una celda vacía de Excel llega como NaN).
 * Todas las funciones lanzan std::invalid_argument (ValueError en Python) con un
 * mensaje que empieza "Domain error [RockMassPy]: parameter '<name>'".
 */

#pragma once

#include <cmath>
#include <stdexcept>
#include <string>

namespace rockmasspy::validation {

namespace detail {
[[noreturn]] inline void fail(const std::string& name, const std::string& what, double value) {
    throw std::invalid_argument("Domain error [RockMassPy]: parameter '" + name + "' " + what +
                                ". Received: " + std::to_string(value));
}
}  // namespace detail

/// Rechaza NaN y ±infinito.
inline void require_finite(double value, const std::string& name) {
    if (!std::isfinite(value)) detail::fail(name, "must be a finite number (got NaN or infinity)", value);
}

/// value > 0
inline void require_positive(double value, const std::string& name) {
    require_finite(value, name);
    if (value <= 0.0) detail::fail(name, "must be strictly positive (> 0)", value);
}

/// value >= 0
inline void require_non_negative(double value, const std::string& name) {
    require_finite(value, name);
    if (value < 0.0) detail::fail(name, "must not be negative (>= 0)", value);
}

/// lo <= value <= hi (ambos límites inclusivos)
inline void require_in_range(double value, double lo, double hi, const std::string& name) {
    require_finite(value, name);
    require_finite(lo, name);
    require_finite(hi, name);
    if (value < lo || value > hi)
        detail::fail(name, "must be within [" + std::to_string(lo) + ", " + std::to_string(hi) + "]", value);
}

/// value <= hi, con un mensaje propio (por ejemplo, para sugerir la unidad correcta).
inline void require_max(double value, double hi, const std::string& name, const std::string& hint) {
    require_finite(value, name);
    if (value > hi) throw std::invalid_argument("Domain error [RockMassPy]: parameter '" + name + "': " + hint);
}

}  // namespace rockmasspy::validation
