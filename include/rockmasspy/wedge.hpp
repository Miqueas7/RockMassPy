/**
 * @file wedge.hpp
 * @brief Cuña tetraédrica por resolución vectorial de fuerzas: dos juntas, cara y talud superior, con agua,
 *        cohesión, carga externa y sismo pseudoestático; modos de deslizamiento.
 *
 * Convención de vectores de stereonet.hpp (x norte, y este, z abajo). Geometría (R7): el vértice inferior O está en el
 * origen sobre la cara; V1 = J1∩J2∩superior, V2 = J1∩cara∩superior, V3 = J2∩cara∩superior; la escala hace que el más
 * alto de V2 y V3 quede H por encima de O (es la única altura que reproduce los volúmenes de SWedge). Fuerzas: peso,
 * presión media por junta (empuja hacia el centroide, R9), fuerza externa y kh·W horizontal según la tendencia de la
 * intersección hacia la cara. Se resuelve R = -N1 n1 - N2 n2 + s i por Cramer. Las ecuaciones de Hoek y Bray 1981
 * (ap. 2) y Priest 1993 (cap. 8) no se leyeron: es mecánica de cuerpo rígido comprobada contra SWedge (marca Secondary).
 * Todo límite toma el lado menos favorable con holgura 1e-9; los avisos no repiten valores.
 */

#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

#include "rockmasspy/method_info.hpp"
#include "rockmasspy/stereonet.hpp"
#include "rockmasspy/validation.hpp"

namespace rockmasspy {

struct WedgeJoint {
    PlaneOrientation plane{validation::unset, validation::unset};
    double cohesion = 0.0;
    double friction_deg = validation::unset;
    double water_pressure = 0.0;  // presión media sobre la junta (R7)
};

struct WedgeInput {
    WedgeJoint joint1, joint2;
    PlaneOrientation face{validation::unset, validation::unset};
    PlaneOrientation upper{validation::unset, validation::unset};
    double height_m = validation::unset, unit_weight = validation::unset;
    double kh = 0.0;              // [0, 1], horizontal según la tendencia de la intersección hacia la cara
    double external_force = 0.0;  // >= 0
    LineOrientation external_direction{0.0, 90.0};  // tendencia e inmersión; por defecto vertical hacia abajo
};

enum class WedgeMode { TwoPlanes, PlaneOne, PlaneTwo, Lifting, NotFormed };

struct WedgeResult {
    std::optional<double> factor_of_safety;
    WedgeMode mode;
    std::optional<LineOrientation> intersection;
    double volume, weight, area1, area2, face_area, upper_area, normal1, normal2, driving_force, resisting_force;
    MethodInfo info;
    std::vector<std::string> warnings, notes;
};

namespace wedge_detail {
using stereonet_detail::Vec;
constexpr double kTol = 1e-9;

inline Vec sub(const Vec& a, const Vec& b) { return {a[0] - b[0], a[1] - b[1], a[2] - b[2]}; }
inline Vec scale(const Vec& a, double s) { return {a[0] * s, a[1] * s, a[2] * s}; }
inline Vec add(const Vec& a, const Vec& b) { return {a[0] + b[0], a[1] + b[1], a[2] + b[2]}; }
inline double dot(const Vec& a, const Vec& b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
inline Vec cross(const Vec& a, const Vec& b) {
    return {a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]};
}
inline double norm(const Vec& a) { return std::sqrt(dot(a, a)); }
inline double area(const Vec& a, const Vec& b, const Vec& c) { return 0.5 * norm(cross(sub(b, a), sub(c, a))); }

inline void check_plane(const PlaneOrientation& p, const std::string& prefix) {
    validation::require_in_range(p.dip_direction_deg, 0.0, 360.0, prefix + "dip_direction_deg");
    validation::require_in_range(p.dip_deg, 0.0, 90.0, prefix + "dip_deg");
}

inline void check(const WedgeInput& in) {
    check_plane(in.joint1.plane, "joint1.plane.");
    check_plane(in.joint2.plane, "joint2.plane.");
    check_plane(in.face, "face.");
    check_plane(in.upper, "upper.");
    validation::require_positive(in.height_m, "height_m");
    validation::require_positive(in.unit_weight, "unit_weight");
    int k = 0;
    for (const WedgeJoint* j : {&in.joint1, &in.joint2}) {
        const std::string p = ++k == 1 ? "joint1." : "joint2.";
        validation::require_non_negative(j->cohesion, p + "cohesion");
        validation::require_finite(j->friction_deg, p + "friction_deg");
        validation::require(j->friction_deg >= 0.0 && j->friction_deg < 90.0, p + "friction_deg",
                            "must be within [0, 90)", j->friction_deg);
        validation::require_non_negative(j->water_pressure, p + "water_pressure");
    }
    validation::require_in_range(in.kh, 0.0, 1.0, "kh");
    validation::require_non_negative(in.external_force, "external_force");
    validation::require_in_range(in.external_direction.trend_deg, 0.0, 360.0, "external_direction.trend_deg");
    validation::require_in_range(in.external_direction.plunge_deg, 0.0, 90.0, "external_direction.plunge_deg");
}

inline MethodInfo info() {
    return {"Wedge-Tetrahedral-Vector", Verification::Secondary,
            "limit equilibrium of a tetrahedral wedge by vector resolution of forces (Hoek & Bray 1981 App. 2 and "
            "Priest 1993 ch. 8 not read); height = vertical rise of the higher crest vertex above the toe vertex; "
            "checked against Rocscience SWedge Verification Manual (2022) problems 1-4, 6, 7 and Hoek (1974) Fig. 22"};
}

inline WedgeResult not_formed(const std::optional<LineOrientation>& axis, const std::string& why) {
    WedgeResult r{std::nullopt, WedgeMode::NotFormed, axis, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, info(), {}, {}};
    r.notes.push_back("wedge not formed: " + why);
    return r;
}

inline double tan_deg(double d) { return std::tan(stereonet_detail::rad(d)); }

/// Normal (polo) de un plano; un buzamiento 0 o 90 exacto no arrastra ruido de 1e-17 en los componentes.
inline Vec normal_of(const PlaneOrientation& p) {
    Vec v = stereonet_detail::vec(pole_of(p));
    if (p.dip_deg <= 0.0) v = {0.0, 0.0, 1.0};
    else if (p.dip_deg >= 90.0) v[2] = 0.0;
    return v;
}
}  // namespace wedge_detail

/// Factor de seguridad de la cuña y su modo. Cuña no formada: FS vacío y una nota; despegue: FS 0 y un aviso.
inline WedgeResult wedge_fs(const WedgeInput& in) {
    using namespace wedge_detail;
    using stereonet_detail::deg;
    using stereonet_detail::rad;
    check(in);

    const auto axis = plane_intersection(in.joint1.plane, in.joint2.plane);
    if (!axis) return not_formed(std::nullopt, "parallel joints");

    // sentido de la intersección hacia la cara (los dos si es horizontal: gana el que más mira a la cara)
    Vec iv = stereonet_detail::vec(*axis);
    const double af = rad(in.face.dip_direction_deg), as = rad(in.upper.dip_direction_deg);
    const double horiz_norm = std::hypot(iv[0], iv[1]);
    if (horiz_norm < kTol) return not_formed(axis, "the intersection does not daylight in the face");  // vertical
    if (iv[2] < kTol) {
        const Vec fh{std::cos(af), std::sin(af), 0.0};
        if (dot(iv, fh) < 0.0) iv = scale(iv, -1.0);
        iv[2] = 0.0;
    }
    const double t = std::atan2(iv[1], iv[0]);
    const double tan_psi_i = iv[2] / horiz_norm;
    const double cf = std::cos(t - af);
    if (cf <= kTol || tan_psi_i >= tan_deg(in.face.dip_deg) * cf - kTol)
        return not_formed(axis, "the intersection does not daylight in the face");
    if (tan_psi_i <= tan_deg(in.upper.dip_deg) * std::cos(t - as) + kTol)
        return not_formed(axis, "the intersection does not outcrop on the upper slope");

    // geometría: vértices con el plano superior en n_u·p = 1, luego escalados a la altura H
    const Vec n1 = normal_of(in.joint1.plane), n2 = normal_of(in.joint2.plane);
    const Vec nf = normal_of(in.face), nu = normal_of(in.upper);
    const auto vertex = [&](const Vec& d) -> std::optional<Vec> {
        const double c = dot(nu, d);
        if (std::fabs(c) < 1e-12 * norm(d)) return std::nullopt;
        return scale(d, 1.0 / c);
    };
    const auto v1 = vertex(cross(n1, n2)), v2 = vertex(cross(n1, nf)), v3 = vertex(cross(n2, nf));
    if (!v1 || !v2 || !v3) return not_formed(axis, "the intersection does not outcrop on the upper slope");
    double rise = std::max(-(*v2)[2], -(*v3)[2]);
    double sg = 1.0;
    if (rise < 0.0) { sg = -1.0; rise = std::max((*v2)[2], (*v3)[2]); }
    if (rise <= 1e-12) return not_formed(axis, "the intersection does not outcrop on the upper slope");
    const double k = sg * in.height_m / rise;
    const Vec V1 = scale(*v1, k), V2 = scale(*v2, k), V3 = scale(*v3, k);
    const double volume = std::fabs(dot(V1, cross(V2, V3))) / 6.0;
    if (volume <= kTol * in.height_m * in.height_m * in.height_m)
        return not_formed(axis, "the intersection does not outcrop on the upper slope");

    WedgeResult r{std::nullopt, WedgeMode::TwoPlanes, axis, volume, in.unit_weight * volume,
                  0.5 * norm(cross(V1, V2)), 0.5 * norm(cross(V1, V3)), 0.5 * norm(cross(V2, V3)),
                  area(V1, V2, V3), 0, 0, 0, 0, info(), {}, {}};

    // normales hacia el centroide
    const Vec centroid = scale(add(add(V1, V2), V3), 0.25);
    Vec nn1 = n1, nn2 = n2;
    if (dot(nn1, centroid) < 0.0) nn1 = scale(nn1, -1.0);
    if (dot(nn2, centroid) < 0.0) nn2 = scale(nn2, -1.0);

    // fuerza resultante R
    Vec R{0.0, 0.0, r.weight};
    R = add(R, scale(nn1, in.joint1.water_pressure * r.area1));
    R = add(R, scale(nn2, in.joint2.water_pressure * r.area2));
    R = add(R, scale(stereonet_detail::vec(in.external_direction), in.external_force));
    R = add(R, {r.weight * in.kh * std::cos(t), r.weight * in.kh * std::sin(t), 0.0});
    const double Rn = norm(R);

    // R = -N1 n1 - N2 n2 + s i por Cramer
    const Vec m1 = scale(nn1, -1.0), m2 = scale(nn2, -1.0);
    const double det = dot(m1, cross(m2, iv));
    const double N1 = dot(R, cross(m2, iv)) / det;
    const double N2 = dot(m1, cross(R, iv)) / det;
    const double s = dot(m1, cross(m2, R)) / det;

    const double t1 = tan_deg(in.joint1.friction_deg), t2 = tan_deg(in.joint2.friction_deg);
    const double c1A1 = in.joint1.cohesion * r.area1, c2A2 = in.joint2.cohesion * r.area2;
    const double inf = std::numeric_limits<double>::infinity();
    struct Cand { double fs, n1, n2, drive, resist; WedgeMode mode; bool infinite; };
    const auto two = [&]() -> Cand {
        const double resist = c1A1 + c2A2 + N1 * t1 + N2 * t2;
        if (s <= 1e-12 * Rn) return {inf, N1, N2, s, resist, WedgeMode::TwoPlanes, true};
        return {resist / s, N1, N2, s, resist, WedgeMode::TwoPlanes, false};
    };
    const auto one = [&](int kk) -> Cand {
        const Vec& nk = kk == 1 ? nn1 : nn2;
        const double N = -dot(R, nk);
        const WedgeMode md = kk == 1 ? WedgeMode::PlaneOne : WedgeMode::PlaneTwo;
        if (N <= kTol * Rn) return {0.0, 0.0, 0.0, Rn, 0.0, WedgeMode::Lifting, false};
        const double drive = norm(add(R, scale(nk, N)));
        const double resist = (kk == 1 ? c1A1 : c2A2) + N * (kk == 1 ? t1 : t2);
        const Cand c{drive <= 1e-12 * Rn ? inf : resist / drive, kk == 1 ? N : 0.0, kk == 2 ? N : 0.0, drive, resist, md,
                     drive <= 1e-12 * Rn};
        return c;
    };

    // estado de cada junta: en contacto, despegada o en el límite (se evalúan los dos lados)
    const auto states = [&](double N) { return N > kTol * Rn ? std::vector<int>{1} : (N < -kTol * Rn ? std::vector<int>{0} : std::vector<int>{1, 0}); };
    std::optional<Cand> best;
    for (int a : states(N1))
        for (int b : states(N2)) {
            const Cand c = a && b ? two() : (a ? one(1) : (b ? one(2) : Cand{0.0, 0.0, 0.0, Rn, 0.0, WedgeMode::Lifting, false}));
            if (!best || c.fs < best->fs) best = c;
        }
    r.factor_of_safety = best->fs;
    r.mode = best->mode;
    r.normal1 = best->n1;
    r.normal2 = best->n2;
    r.driving_force = best->drive;
    r.resisting_force = best->resist;
    if (best->mode == WedgeMode::Lifting) r.warnings.push_back("wedge lifts off both joints");
    if (best->infinite) r.notes.push_back("no force drives the wedge along the sliding direction: the factor of safety is infinite");
    return r;
}

}  // namespace rockmasspy
