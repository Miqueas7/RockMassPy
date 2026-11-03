/**
 * @file toppling.hpp
 * @brief Volteo de bloques de Goodman y Bray: fuerzas por bloque, soporte en el pie y factor de seguridad.
 *
 * Fuente: Goodman & Bray (1976) «Toppling of rock slopes», ASCE, ec. 2-15 (pp. 211-222), por metro de talud. Bloques
 * numerados desde el pie (índice 0 = bloque 1) y calculados de arriba abajo. a2 es un dato: la ec. 2 del artículo no
 * calza con su propio ejemplo (R10). Un valor justo en un límite toma el lado menos favorable con holgura 1e-9: un
 * bloque es estable solo si max(Pt, Ps) < -1e-9 Wn, y las condiciones (8)-(9) fallan con Rn <= 1e-9 Wn o
 * |Sn|/Rn >= mu - 1e-9 solo con Sn < 0 (deslizamiento cuesta arriba; con Sn >= 0 la (9) equivale a Pt >= Ps, la regla
 * de etiquetado, y daría un aviso que cambia con el signo del ruido). Con soporte > 0 el ángulo cumple
 * -45 < alpha + delta < 90: Tt exige cos(alpha + delta) > 0 y Ts exige mu sin + cos > 0 en todo mu de (0, 1], lineal en
 * mu, o sea cos > 0 y sin + cos > 0. Con soporte 0 la dirección no importa. FS = mu disponible / mu requerido
 * (ec. 15), con tope 100. Los avisos no repiten valores.
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

enum class TopplingState { Stable, Toppling, Sliding };

struct TopplingInput {
    std::vector<double> heights_m;  // bloque 1 (pie) primero
    double block_width_m = validation::unset, base_dip_deg = validation::unset;  // Δx y α
    double a1_m = validation::unset, a2_m = validation::unset;
    int crest_block = 0;  // 1..n
    double unit_weight = validation::unset, friction_deg = validation::unset;
    double support_force = 0.0, support_angle_deg = 0.0;  // T y δ bajo la horizontal
    std::optional<double> support_height_m;               // vacío = altura del bloque 1
};

struct TopplingBlock {
    int n;
    double height_m, m_m, l_m, p_toppling, p_sliding, p_lower, normal, shear;
    TopplingState state;
};

struct TopplingForces {
    std::vector<TopplingBlock> blocks;
    double support_toppling, support_sliding, support_required;
};

struct TopplingResult {
    double factor_of_safety, friction_required;
    TopplingForces forces;
    bool fs_bounded;
    bool capped;  // FS en el tope de 100: cota inferior
    MethodInfo info;
    std::vector<std::string> warnings, notes;
};

namespace toppling_detail {
constexpr double kPi = 3.14159265358979323846;
constexpr double kTol = 1e-9;
inline double rad(double d) { return d * kPi / 180.0; }

inline void check(const TopplingInput& in) {
    validation::require_positive(in.block_width_m, "block_width_m");
    validation::require_finite(in.base_dip_deg, "base_dip_deg");
    validation::require(in.base_dip_deg > 0.0 && in.base_dip_deg < 90.0, "base_dip_deg", "must be within (0, 90)",
                        in.base_dip_deg);
    validation::require_non_negative(in.a1_m, "a1_m");
    validation::require_non_negative(in.a2_m, "a2_m");
    validation::require_positive(in.unit_weight, "unit_weight");
    validation::require_finite(in.friction_deg, "friction_deg");
    validation::require(in.friction_deg > 0.0 && in.friction_deg < 90.0, "friction_deg", "must be within (0, 90)",
                        in.friction_deg);
    const int n = static_cast<int>(in.heights_m.size());
    if (n == 0) throw std::invalid_argument("Domain error [RockMassPy]: parameter 'heights_m' must not be empty");
    for (int i = 0; i < n; ++i) validation::require_positive(in.heights_m[i], "heights_m[" + std::to_string(i) + "]");
    validation::require(in.crest_block >= 1 && in.crest_block <= n, "crest_block", "must be within [1, n_blocks]",
                        in.crest_block);
    validation::require_non_negative(in.support_force, "support_force");
    validation::require_finite(in.support_angle_deg, "support_angle_deg");
    validation::require(in.support_angle_deg > -90.0 && in.support_angle_deg < 90.0, "support_angle_deg",
                        "must be within (-90, 90)", in.support_angle_deg);
    // mu-independiente: garantiza los denominadores de las ec. 11-12 en todo mu de (0, 1]
    if (in.support_force > 0.0 && !(in.base_dip_deg + in.support_angle_deg > -45.0 && in.base_dip_deg + in.support_angle_deg < 90.0))
        throw std::invalid_argument(
            "Domain error [RockMassPy]: parameter 'support_angle_deg': base_dip_deg + support_angle_deg must be within "
            "(-45, 90) for the support to act");
    if (in.support_height_m) {
        validation::require_finite(*in.support_height_m, "support_height_m");
        validation::require(*in.support_height_m > 0.0 && *in.support_height_m <= in.heights_m[0], "support_height_m",
                            "must be within (0, height of block 1]", *in.support_height_m);
    }
    for (int k = 2; k <= n; ++k) {
        const double l = k <= in.crest_block ? in.heights_m[k - 1] - in.a1_m : in.heights_m[k - 1];
        if (l <= 0.0)
            throw std::invalid_argument("Domain error [RockMassPy]: block " + std::to_string(k) +
                                        ": L_n must be positive");
    }
}

inline MethodInfo info() {
    return {"Toppling-GoodmanBray1976", Verification::Primary,
            "Goodman & Bray (1976) Toppling of rock slopes, ASCE: eqs. 2-15 (pp. 211-222); FS = mu available / mu "
            "required (eq. 15); support on block 1, eqs. 11-14"};
}
}  // namespace toppling_detail

/// Alturas regulares de los bloques: ec. 3a bajo la cresta y 3b sobre ella (p. 211). Lanza si alguna queda <= 0.
inline std::vector<double> goodman_bray_heights(int n_blocks, int crest_block, double a1_m, double a2_m, double b_m) {
    validation::require(n_blocks >= 1, "n_blocks", "must be at least 1", n_blocks);
    validation::require(crest_block >= 1 && crest_block <= n_blocks, "crest_block", "must be within [1, n_blocks]",
                        crest_block);
    validation::require_finite(a1_m, "a1_m");
    validation::require_finite(a2_m, "a2_m");
    validation::require_finite(b_m, "b_m");
    std::vector<double> y(n_blocks);
    for (int n = 1; n <= n_blocks; ++n) {
        y[n - 1] = n <= crest_block ? n * (a1_m - b_m) : y[n - 2] - a2_m - b_m;
        validation::require(y[n - 1] > 0.0, "heights_m[" + std::to_string(n - 1) + "]", "block height must be positive",
                            y[n - 1]);
    }
    return y;
}

/// Fuerzas por bloque para un coeficiente de fricción mu en (0, 1): ec. 4-14, de arriba abajo.
inline TopplingForces toppling_forces(const TopplingInput& in, double mu) {
    using namespace toppling_detail;
    check(in);
    validation::require_finite(mu, "mu");
    validation::require(mu > 0.0 && mu < 1.0, "mu", "must be within (0, 1)", mu);
    const int N = static_cast<int>(in.heights_m.size());
    const double dx = in.block_width_m, al = rad(in.base_dip_deg), sa = std::sin(al), ca = std::cos(al);
    // sin soporte la dirección es irrelevante: Tt y Ts se miden en horizontal
    const double ang = rad(in.base_dip_deg + (in.support_force > 0.0 ? in.support_angle_deg : 0.0));
    const double den_t = std::cos(ang), den_s = mu * std::sin(ang) + std::cos(ang);
    TopplingForces out;
    out.blocks.resize(N);
    double P = 0.0;  // Pn: fuerza que llega del bloque de arriba
    for (int n = N; n >= 1; --n) {
        const double y = in.heights_m[n - 1], W = in.unit_weight * dx * y;
        TopplingBlock& b = out.blocks[n - 1];
        b.n = n;
        b.height_m = y;
        b.m_m = n < in.crest_block ? y : y - in.a2_m;
        b.l_m = n <= in.crest_block ? y - in.a1_m : y;
        const double pre_t = 0.5 * W * (y * sa - dx * ca), pre_s = -W * (mu * ca - sa) / (1.0 - mu * mu);
        if (n == 1) {
            b.l_m = in.support_height_m ? *in.support_height_m : y;
            b.p_toppling = (pre_t + P * (b.m_m - mu * dx)) / (b.l_m * den_t);
            b.p_sliding = (P * (1.0 - mu * mu) - W * (mu * ca - sa)) / den_s;
            b.p_lower = 0.0;
            b.normal = mu * P + in.support_force * std::sin(ang) + W * ca;
            b.shear = P - in.support_force * std::cos(ang) + W * sa;
            b.state = std::max(b.p_toppling, b.p_sliding) < -kTol * W
                          ? TopplingState::Stable
                          : (b.p_toppling >= b.p_sliding ? TopplingState::Toppling : TopplingState::Sliding);
            break;
        }
        b.p_toppling = (P * (b.m_m - mu * dx) + pre_t) / b.l_m;
        b.p_sliding = P + pre_s;
        if (std::max(b.p_toppling, b.p_sliding) < -kTol * W) {
            b.state = TopplingState::Stable;
            b.p_lower = 0.0;
        } else {
            b.state = b.p_toppling >= b.p_sliding ? TopplingState::Toppling : TopplingState::Sliding;
            b.p_lower = std::max({b.p_toppling, b.p_sliding, 0.0});
        }
        b.normal = W * ca - mu * (b.p_lower - P);
        b.shear = b.state == TopplingState::Sliding ? mu * b.normal : W * sa - (b.p_lower - P);
        P = b.p_lower;
    }
    const TopplingBlock& b1 = out.blocks[0];
    out.support_toppling = b1.p_toppling;
    out.support_sliding = b1.p_sliding;
    out.support_required = std::max({b1.p_toppling, b1.p_sliding, 0.0});
    return out;
}

/// Factor de seguridad con el soporte dado: mu requerido por bisección y FS = tan(phi)/mu (ec. 15, p. 222).
inline TopplingResult toppling_fs(const TopplingInput& in) {
    using namespace toppling_detail;
    check(in);
    const double tphi = std::tan(rad(in.friction_deg)), lo0 = tphi / 100.0, hi0 = 1.0 - 1e-9;
    TopplingResult r{0.0, 0.0, {}, false, false, info(), {}, {}};
    const auto req = [&](double mu) { return toppling_forces(in, mu); };
    double mu;
    const TopplingForces at_lo = req(lo0);
    if (at_lo.support_required <= in.support_force) {
        mu = lo0;
        r.forces = at_lo;
        r.factor_of_safety = 100.0;
        r.notes.push_back("toppling FS above 100");
        r.capped = true;  // mu artificial: no se evalúan (8)-(9)
    } else {
        const TopplingForces at_hi = req(hi0);
        if (at_hi.support_required > in.support_force) {
            mu = hi0;
            r.forces = at_hi;
            r.fs_bounded = true;
            r.warnings.push_back(
                "toppling: support is insufficient for any friction coefficient below 1; FS is an upper bound");
        } else {
            double lo = lo0, hi = hi0;  // lo no alcanza, hi sí
            for (int i = 0; i < 200 && hi - lo > 1e-15 * hi; ++i) {
                const double mid = 0.5 * (lo + hi);
                (req(mid).support_required <= in.support_force ? hi : lo) = mid;
            }
            mu = hi;  // el lado menos favorable (mu mayor, FS menor)
            r.forces = req(mu);
        }
        r.factor_of_safety = tphi / mu;
    }
    r.friction_required = mu;
    int fails = 0;
    for (const auto& b : r.forces.blocks) {
        if (r.capped) break;
        const double w = in.unit_weight * in.block_width_m * b.height_m;
        fails += b.normal <= kTol * w ||
                 (b.state != TopplingState::Sliding && b.shear < 0.0 && -b.shear >= (mu - kTol) * b.normal);
    }
    if (fails > 0) r.warnings.push_back("Goodman-Bray conditions (8)-(9) fail in " + std::to_string(fails) + " blocks");
    return r;
}

}  // namespace rockmasspy
