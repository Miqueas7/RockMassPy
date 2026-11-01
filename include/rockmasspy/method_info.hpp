/**
 * @file method_info.hpp
 * @brief Trazabilidad de cada resultado: qué método y edición lo produjo y qué tan verificada está su fuente.
 */

#pragma once

#include <string>

namespace rockmasspy {

/// Primary = verificada en la fuente original (o en una reproducción fiel de sus ecuaciones por un autor citado);
/// PrimaryLaterAuthors = verificada en una publicación posterior de los mismos autores; Secondary = solo fuente
/// secundaria; UserDefined = calibrada por el usuario con datos del sitio.
enum class Verification { Primary, PrimaryLaterAuthors, Secondary, UserDefined };

struct MethodInfo {
    std::string method_id;  // p. ej. "RMR89", "Q-NGI-2025", "HB-2018"
    Verification verification;
    std::string source;
};

}  // namespace rockmasspy
