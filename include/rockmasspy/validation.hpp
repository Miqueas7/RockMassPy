/**
 * @file validation.hpp
 * @brief Validación de dominio en la frontera: toda entrada numérica pasa por aquí.
 *
 * NaN e infinito siempre se rechazan (una celda vacía de Excel llega como NaN).
 * Todas las funciones lanzan std::invalid_argument (ValueError en Python) con un
 * mensaje que empieza "Domain error [RockMassPy]: parameter '<name>'".
 * Las entradas usan NaN (medidas) y std::optional vacío (enums obligatorios) como «sin dato»:
 * un campo olvidado lanza con su nombre en vez de tomar un valor por defecto.
 */

#pragma once

#include <cmath>
#include <iomanip>
#include <limits>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>

namespace rockmasspy::validation {

/// Valor «sin dato» de las medidas en las estructuras de entrada.
inline constexpr double unset = std::numeric_limits<double>::quiet_NaN();

namespace detail {
/// 15 cifras significativas, formato general: 1e-9 sale "1e-09" y 100 sale "100".
inline std::string num(double value) {
    std::ostringstream out;
    out << std::setprecision(15) << value;
    return out.str();
}

[[noreturn]] inline void fail(const std::string& name, const std::string& what, double value) {
    throw std::invalid_argument("Domain error [RockMassPy]: parameter '" + name + "' " + what +
                                ". Received: " + num(value));
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
        detail::fail(name, "must be within [" + detail::num(lo) + ", " + detail::num(hi) + "]", value);
}

/// Condición propia: si `ok` es falso lanza con el nombre, el motivo y el valor recibido.
inline void require(bool ok, const std::string& name, const std::string& what, double value) {
    if (!ok) detail::fail(name, what, value);
}

/// value <= hi, con un mensaje propio (por ejemplo, para sugerir la unidad correcta).
inline void require_max(double value, double hi, const std::string& name, const std::string& hint) {
    require_finite(value, name);
    if (value > hi) throw std::invalid_argument("Domain error [RockMassPy]: parameter '" + name + "': " + hint);
}

/// Un enum obligatorio que llegó vacío lanza con su nombre.
template <class T>
const T& require_set(const std::optional<T>& value, const std::string& name) {
    if (!value) throw std::invalid_argument("Domain error [RockMassPy]: parameter '" + name + "' is required");
    return *value;
}

}  // namespace rockmasspy::validation
