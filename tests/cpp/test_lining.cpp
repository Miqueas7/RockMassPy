#include <gtest/gtest.h>

#include "error_of.hpp"
#include "rockmasspy/excavation.hpp"
#include "rockmasspy/lining.hpp"

using namespace rockmasspy;

namespace {
LiningSection steel() { return {4.75e-3, 2.23e-5, 0.162, 500, -500}; }
LiningSection shotcrete() { return {0.12, 0.0004, 0.2, 40, -5}; }  // σt = -5: errata de KL08 p. 51 (FORMULAS §14)
}  // namespace

TEST(Lining, CerchaKL08) {
    const auto e = capacity_mn(steel(), 1);
    EXPECT_NEAR(e.n_max, 2.375, 1e-3);
    EXPECT_NEAR(e.n_min, -2.375, 1e-3);
    EXPECT_NEAR(e.m_max, 0.1377, 1e-4);
    EXPECT_NEAR(q_crit(steel(), 1), 1.583, 1e-3);
    EXPECT_NEAR(shear_capacity_n(steel(), 1.19, 1, true), 1.033, 1e-3);
    EXPECT_EQ(e.info.method_id, "Lining-capacity-Carranza-Torres-Diederichs-2009");
}

TEST(Lining, ShotcreteKL08) {
    const auto e = capacity_mn(shotcrete(), 1);
    EXPECT_NEAR(e.n_max, 4.80, 1e-9);
    EXPECT_NEAR(e.n_min, -0.60, 1e-9);
    EXPECT_NEAR(e.n_cr, 2.10, 1e-9);
    EXPECT_NEAR(e.m_max, 0.090, 1e-9);
    EXPECT_NEAR(q_crit(shotcrete(), 1), 1.131, 1e-3);
    EXPECT_NEAR(shear_capacity_n(shotcrete(), 0.85, 1, true), 4.461, 1e-3);
    EXPECT_NEAR(shear_capacity_n(shotcrete(), 0.85, 1, false), 2.109, 1e-3);
}

TEST(Lining, FsDosDivideEnDos) {
    const auto a = capacity_mn(shotcrete(), 1), b = capacity_mn(shotcrete(), 2);
    EXPECT_NEAR(b.n_max, a.n_max / 2, 1e-12);
    EXPECT_NEAR(b.m_max, a.m_max / 2, 1e-12);
    EXPECT_NEAR(b.n_cr, a.n_cr / 2, 1e-12);
    EXPECT_NEAR(q_crit(shotcrete(), 2), q_crit(shotcrete(), 1) / 2, 1e-12);
    // convexo: (Ncr, 0) y el punto medio de una arista están dentro
    EXPECT_TRUE(check_capacity(shotcrete(), {{b.n_cr, 0, 0}}, 2).all_inside);
    const auto& v = a.vertices;
    const LiningForce mid{(v[0].first + v[1].first) / 2, (v[0].second + v[1].second) / 2, 0};
    EXPECT_TRUE(check_capacity(shotcrete(), {mid}, 1).all_inside);
}

TEST(Lining, EinsteinSchwartzContraRombo) {
    const LiningSection s{0.5, 0.5 * 0.5 * 0.5 / 12, 0.5, 60, -6};
    std::vector<LiningForce> f;
    for (double th : {0.0, 45.0, 90.0}) {
        EinsteinSchwartzInput in;
        in.sigma_v_mpa = 15; in.k_ratio = 2; in.e_rock_mpa = 6000; in.nu_rock = 0.2;
        in.e_lining_mpa = 20000; in.nu_lining = 0.2; in.thickness_m = 0.5; in.radius_m = 2.5; in.theta_deg = th;
        const auto r = einstein_schwartz(in);
        f.push_back({r.n_mn, r.m_mnm, 0});
    }
    // cuenta propia: con FS = 1, Nmax 30, Ncr 13.5, Mmax 1.375: solo θ = 90° (N 36.6) sale
    EXPECT_EQ(check_capacity(s, f, 1).outside, std::vector<int>({2}));
    // FS = 2: Nmax 15, Mmax 0.6875; θ = 0 (N 14.61, |M| 0.703) también sale, θ = 45° (N 25.6) también
    EXPECT_EQ(check_capacity(s, f, 2).outside, std::vector<int>({0, 1, 2}));
}

TEST(Lining, Compuesta) {
    const ElasticSection st{200000, 0.3, 4.75e-3, 2.23e-5}, sh{20000, 0.2, 0.12, 0.0004};
    const auto c = composite(st, sh, 1 / 0.6, 3);
    EXPECT_NEAR(c.t_eq, std::sqrt(12 * c.k_eq / c.d_eq), 1e-12);
    EXPECT_NEAR(c.e_eq * c.t_eq, c.d_eq, 1e-6);
    const auto f = split_forces(c, 2.0, 0.1, 0.5);
    EXPECT_NEAR(f.n_steel + f.n_shotcrete, 2.0 / c.n_sets_per_m, 1e-9);  // el reparto conserva N, M y Q
    EXPECT_NEAR(f.m_steel + f.m_shotcrete, 0.1 / c.n_sets_per_m, 1e-9);
    EXPECT_NEAR(f.q_steel + f.q_shotcrete, 0.5 / c.n_sets_per_m, 1e-9);
}

TEST(Lining, Errores) {
    auto s = shotcrete();
    s.sigma_t_mpa = 5;
    const auto msg = error_of([&] { capacity_mn(s, 1); });
    EXPECT_NE(msg.find("'sigma_t_mpa'"), std::string::npos);
    EXPECT_NE(error_of([&] { capacity_mn(shotcrete(), 0); }).find("'fs'"), std::string::npos);
    EXPECT_NE(error_of([&] { shear_capacity_n(shotcrete(), 2, 1, true); }).find("'q_mn'"), std::string::npos);
    EXPECT_NE(error_of([] { capacity_mn({}, 1); }).find("'area_m2'"), std::string::npos);
}
