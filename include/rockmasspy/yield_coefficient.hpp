/**
 * @file yield_coefficient.hpp
 * @brief Coeficiente de fluencia ky: el kh que da FS = 1 sobre una superficie dada, por bisección en [0, 1].
 *
 * Solo llama a le_factor_of_safety con la sección y kh reemplazado (el kh de la sección se ignora). Reglas (plan 3C,
 * tarea 5 y «Restricciones globales»):
 * - FS estático (kh = 0) <= 1 + 1e-9: ky = 0 con aviso (la superficie ya falla sin sismo).
 * - Bisección hasta |FS - 1| < 1e-6. kh = 1 se evalúa solo si FS(0.5) > 1; si FS(1) > 1 + 1e-9, ky vacío con nota.
 * - Si el método no converge (o da FS vacío) en algún kh, ky vacío y el aviso «ky not found: <method> did not
 *   converge at some kh» más los avisos del núcleo en ese kh. Nunca se devuelve un kh a medias.
 * - Si tras 200 bisecciones no se llega a la tolerancia (FS discontinuo en kh), ky vacío con aviso.
 * Fuente (Secondary): definición usual del coeficiente de fluencia (Newmark 1965, no leído); la bisección es nuestra.
 */

#pragma once

#include <cmath>
#include <optional>
#include <string>
#include <vector>

#include "rockmasspy/limit_equilibrium.hpp"

namespace rockmasspy {

struct YieldResult {
    std::optional<double> ky;
    double fs_static;  // FS con kh = 0 (0 si no se encontró)
    MethodInfo info;
    std::vector<std::string> warnings, notes;
};

inline YieldResult le_yield_coefficient(const LeSection& section, const SlipSurface& surface, LeMethod method,
                                        const LeOptions& options = {}) {
    YieldResult out{std::nullopt, 0.0,
                    {"LE-YieldCoefficient", Verification::Secondary,
                     std::string("kh giving FS = 1 by bisection in [0, 1] on the given surface (") +
                         le_detail::info(method).method_id + "); yield coefficient as in Newmark (1965), not read"},
                    {}, {}};
    LeSection s = section;
    std::vector<std::string> last_warnings;
    auto fs_at = [&](double kh) -> std::optional<double> {
        s.kh = kh;
        LeResult r = le_factor_of_safety(s, surface, method, options);
        last_warnings = r.warnings;
        if (!r.factor_of_safety) {
            out.warnings.push_back(std::string("ky not found: ") + le_detail::name(method) +
                                   " gave no factor of safety at some kh");
            out.warnings.insert(out.warnings.end(), r.warnings.begin(), r.warnings.end());
        }
        return r.factor_of_safety;
    };

    const auto f0 = fs_at(0.0);
    if (!f0) return out;
    out.fs_static = *f0;
    if (*f0 <= 1.0 + 1e-9) {
        out.ky = 0.0;
        out.warnings.push_back("static factor of safety at or below 1: ky taken as 0");
        return out;
    }
    double lo = 0.0, hi = 1.0;
    bool top_checked = false;
    for (int it = 0; it < 200; ++it) {
        const double mid = 0.5 * (lo + hi);
        const auto f = fs_at(mid);
        if (!f) return out;
        if (std::abs(*f - 1.0) < 1e-6) {
            out.ky = mid;
            out.warnings = last_warnings;
            return out;
        }
        if (*f > 1.0) {
            lo = mid;
            if (!top_checked) {  // solo aquí hace falta saber si kh = 1 llega a la falla
                top_checked = true;
                const auto f1 = fs_at(1.0);
                if (!f1) return out;
                if (std::abs(*f1 - 1.0) < 1e-6) {
                    out.ky = 1.0;
                    out.warnings = last_warnings;
                    return out;
                }
                if (*f1 > 1.0 + 1e-9) {
                    out.notes.push_back("factor of safety above 1 with kh = 1: ky not found in [0, 1]");
                    return out;
                }
            }
        } else {
            hi = mid;
            top_checked = true;
        }
    }
    out.warnings.push_back("ky bisection did not reach |FS - 1| < 1e-6 (factor of safety not continuous in kh)");
    return out;
}

}  // namespace rockmasspy
