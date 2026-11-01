/**
 * @file method_info.hpp
 * @brief Trazabilidad de cada resultado: qué método y edición lo produjo y qué tan verificada está su fuente.
 */

#pragma once

#include <string>

namespace rockmasspy {

/// Primary = fuente primaria leída; PrimaryLaterAuthors = primaria con ajustes de autores posteriores;
/// Secondary = solo fuente secundaria.
enum class Verification { Primary, PrimaryLaterAuthors, Secondary };

struct MethodInfo {
    std::string method_id;  // p. ej. "RMR89", "Q-NGI-2025", "HB-2018"
    Verification verification;
    std::string source;
};

}  // namespace rockmasspy
