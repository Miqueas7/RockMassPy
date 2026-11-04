/**
 * @file newmark.hpp
 * @brief Desplazamiento de Newmark de bloque rígido para un registro de aceleraciones y un coeficiente de fluencia ky.
 *
 * Fuente: Newmark (1965) «Effects of earthquakes on dams and embankments» (no leído, de pago); la integración sigue
 * la descrita por Jibson (2007) (no leído). Es mecánica de cuerpo rígido: el bloque arranca cuando a > ky y se mueve
 * con aceleración relativa (a - ky)·g hasta que la velocidad relativa vuelve a cero; solo hacia abajo, nunca v < 0
 * (R13). Comprobado contra la solución cerrada de un pulso rectangular: d = g t0² A (A - ky) / (2 ky).
 *
 * Integración: la aceleración se interpola lineal entre muestras (t_i = i·dt), así que en cada paso la aceleración
 * relativa es lineal y la velocidad al final del paso es exactamente la regla trapezoidal; el desplazamiento es la
 * integral exacta (cúbica) de esa velocidad. Dentro del paso se ubican en forma cerrada el cruce a = ky (arranque) y
 * el instante en que v = 0 (parada), sin sesgo de paso. Con a = ky justo el bloque no arranca. Si termina el registro
 * con el bloque en movimiento, el desplazamiento queda corto y se avisa. Con both_directions se corre también el
 * registro invertido y se devuelve el sentido de mayor desplazamiento (empate: el original), con una nota.
 * Los mensajes no repiten valores salvo los de validation.
 */

#pragma once

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>
#include <vector>

#include "rockmasspy/method_info.hpp"
#include "rockmasspy/validation.hpp"

namespace rockmasspy {

struct NewmarkInput {
    double dt_s = validation::unset;     // paso constante del registro
    std::vector<double> acceleration_g;  // en g; positivo = hacia abajo del talud
    double ky = validation::unset;       // coeficiente de fluencia, en g
    double scale = 1.0;                  // factor sobre el registro
    bool both_directions = false;        // probar también el registro invertido
};

struct NewmarkResult {
    double displacement_m;
    double max_velocity_m_s;
    double time_of_max_s;  // instante de la velocidad relativa máxima
    std::vector<double> displacement_history_m;  // una por muestra; empieza en 0 y termina en displacement_m
    MethodInfo info;
    std::vector<std::string> warnings, notes;
};

namespace newmark_detail {
constexpr double kG = 9.80665;

/// Menor raíz u en (0, L] de v + b u + c u² = 0 con v >= 0; -1 si no hay.
inline double first_stop(double v, double b, double c, double L) {
    double r1 = -1.0, r2 = -1.0;
    if (v <= 0.0) {
        if (c != 0.0) r1 = -b / c;  // raíces 0 y -b/c
    } else if (c == 0.0) {
        if (b < 0.0) r1 = -v / b;
    } else {
        const double disc = b * b - 4.0 * c * v;
        if (disc < 0.0) return -1.0;
        const double q = -0.5 * (b + std::copysign(std::sqrt(disc), b));
        r1 = q / c;
        r2 = (q != 0.0) ? v / q : -1.0;
    }
    // una parada justo al final del paso puede salir L(1 + ε) por redondeo: se toma como parada en L
    double best = -1.0;
    for (double r : {r1, r2})
        if (r > 0.0 && r <= L * (1.0 + 1e-12) && (best < 0.0 || r < best)) best = r;
    return best < 0.0 ? best : std::min(best, L);
}

struct Run {
    double d = 0.0, vmax = 0.0, tmax = 0.0, v_end = 0.0;
    std::vector<double> hist;
};

/// Integra el registro (ya escalado y con signo) con aceleración relativa lineal en cada paso.
inline Run integrate(const std::vector<double>& acc, double dt, double ky, double sign) {
    Run out;
    out.hist.assign(acc.size(), 0.0);
    double v = 0.0;
    for (std::size_t i = 0; i + 1 < acc.size(); ++i) {
        const double r0 = (sign * acc[i] - ky) * kG, r1 = (sign * acc[i + 1] - ky) * kG;
        const double s = (r1 - r0) / dt;  // pendiente de la aceleración relativa
        const double t0 = static_cast<double>(i) * dt;
        double tau = 0.0;
        // r es lineal: a lo más una parada y un arranque por paso
        for (int k = 0; k < 4 && tau < dt; ++k) {
            double b = r0 + s * tau;
            if (v <= 0.0) {
                v = 0.0;
                if (b <= 0.0) {
                    if (s <= 0.0 || r1 <= 0.0) break;  // sigue quieto todo el paso
                    tau = -r0 / s;                     // cruce a = ky, arranca aquí
                    b = 0.0;
                }
            }
            const double L = dt - tau, c = 0.5 * s;
            const double u_stop = first_stop(v, b, c, L);
            const double u = u_stop > 0.0 ? u_stop : L;
            if (b > 0.0 && s < 0.0 && -b / s < u) {  // máximo de v donde r cruza a cero
                const double ur = -b / s, vr = v + b * ur + c * ur * ur;
                if (vr > out.vmax) { out.vmax = vr; out.tmax = t0 + tau + ur; }
            }
            out.d += std::max(0.0, v * u + 0.5 * b * u * u + s * u * u * u / 6.0);
            v = u_stop > 0.0 ? 0.0 : std::max(0.0, v + b * u + c * u * u);
            if (v > out.vmax) { out.vmax = v; out.tmax = t0 + tau + u; }
            tau += u;
        }
        out.hist[i + 1] = out.d;
    }
    out.v_end = v;
    return out;
}
}  // namespace newmark_detail

/// Desplazamiento de Newmark de bloque rígido, solo hacia abajo (R13).
inline NewmarkResult newmark_rigid_block(const NewmarkInput& in) {
    using namespace newmark_detail;
    validation::require_positive(in.dt_s, "dt_s");
    validation::require_positive(in.ky, "ky");
    validation::require_positive(in.scale, "scale");
    if (in.acceleration_g.size() < 2)
        throw std::invalid_argument("Domain error [RockMassPy]: parameter 'acceleration_g' must have at least two samples");
    std::vector<double> acc(in.acceleration_g.size());
    double peak = 0.0, trough = 0.0;
    for (std::size_t i = 0; i < acc.size(); ++i) {
        validation::require_finite(in.acceleration_g[i], "acceleration_g[" + std::to_string(i) + "]");
        acc[i] = in.scale * in.acceleration_g[i];
        validation::require_finite(acc[i], "scale * acceleration_g[" + std::to_string(i) + "]");
        peak = std::max(peak, acc[i]);
        trough = std::min(trough, acc[i]);
    }

    Run run = integrate(acc, in.dt_s, in.ky, 1.0);
    NewmarkResult res{};
    if (in.both_directions) {
        Run inv = integrate(acc, in.dt_s, in.ky, -1.0);
        if (inv.d > run.d) {
            run = std::move(inv);
            peak = -trough;
            res.notes.push_back("both directions: the inverted record governs");
        } else {
            res.notes.push_back("both directions: the original record governs");
        }
    }
    if (in.ky >= peak) res.notes.push_back("ky at or above the peak acceleration: the block does not slide");
    if (run.v_end > 0.0)
        res.warnings.push_back("block still sliding at the end of the record: displacement is a lower bound");

    res.displacement_m = run.d;
    res.max_velocity_m_s = run.vmax;
    res.time_of_max_s = run.tmax;
    res.displacement_history_m = std::move(run.hist);
    res.info = {"Newmark-RigidBlock", Verification::Secondary,
                "Newmark (1965) rigid sliding block; integration as in Jibson (2007), not read; checked against the "
                "closed form of a rectangular pulse"};
    return res;
}

}  // namespace rockmasspy
