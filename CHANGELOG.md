# Changelog

All released versions of RockMassPy. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
the project uses [semantic versioning](https://semver.org/). Before 1.0 the API may still change between minor
versions.

## [0.5.0] - 2026-11-15

Phase 8C: 2D boundary elements (stresses around excavations). Phase 8D: surrogate model.

### Added

- `bem2d` core (displacement discontinuity method, elastic infinite plane strain medium), strength factor
  (`strength_factor`, RS2 3D mode and Examine2D-style 2D mode), `analyze_bem` with the shapes `circle`, `ellipse`,
  `rectangle` and `horseshoe`, `load_excavations`, scope warnings and notes.
- `rockmass bem` command, `plot_bem` and `plot_bem_boundary`, `build_bem_report`.
- Example 17 (`examples/17-elementos-de-contorno/`).
- Surrogate model (8D): `load_runs`, `fit_surrogate` (`rbf` by default, `poly2` optional), `validate_surrogate`
  (grouped by scenario when groups are given), `surrogate_pof` with `pof_lower` and `pof_upper`, `load_points`,
  `load_variables`; predictions outside the domain are refused (`nan`) and counted.
- Test bench with known truth (`planar_runs`, `grc_runs`; 10 scenarios with their own geometry), the
  `rockmass surrogate` command and `build_surrogate_report`.
- Example 18 (`examples/18-modelo-sustituto/`).

### Values to confirm

- Default of 128 elements (smallest perimeter / 128) and the curvature-warning threshold of 0.05 times the radius of
  curvature (the plan said 0.04, but 128 elements on a circle give 0.049).
- Near-boundary remedy with c = 1.
- The exact Examine2D SF formula is [NV] (not verified); the 2D mode is an approximation.
- The generalized Hoek-Brown SF (a other than 0.5) is numeric and has no published oracle.
- Surrogate: box margin 5 %, chi-squared level 0.99 for the domain, useful when RMSE < 0.5 times the mean model's,
  out-of-domain warning above 5 % of samples, and `rbf` as default: on the planar bench `poly2` validated well
  (grouped) yet gave about 1.8 times the true PoF with cohesion and friction sampled (1.55 times in example 18, which
  also samples the water fill).
- Surrogate: the out-of-domain warning is triggered by the share of samples, not by their effect on the PoF (with
  4.9 % excluded the conditional PoF was 11 % below the truth; the bounds are always printed).
- In RS2 mode, tension is checked with the minimum of the three principal stresses (including sigma_z), which is
  conservative; RS2's text says "Sigma 3".

## [0.4.0] - 2026-11-14

Phase 8B: analytical tunnel excavations (convergence-confinement). Phase 8A: results from external programs
(Slide2, RS2, FLAC3D) read, checked and compared.

### Added

- `analyze_tunnel` and `TunnelInput`: ground reaction curve of a circular tunnel (Mohr-Coulomb with dilatancy, and
  Hoek-Brown), longitudinal deformation profile (Panet 1995, Unlu-Gercek 2003, Chern 1998, Vlachopoulos-Diederichs
  2009), crossing with the support curve and factor of safety, squeezing class (Hoek and Marinos), and scope warnings.
- `tunnel_uncertainty` (Monte Carlo over the tunnel inputs), `check_hoek_brown` and `check_k_ratio` (consistency of
  declared Hoek-Brown tables), `load_support_capacity` (capacity sheet, Spanish or Phase2 English headers, decimal
  comma) and Hoek's support pressure table (`HOEK_SUPPORT_TABLE`, `hoek_psm`).
- Core: Kirsch and elliptical-opening boundary stresses, Reed (stresses), Hoek and Brown (1982) brittle plastic
  radius and stresses (`hb1982_plastic_radius`, `hb1982_stress`, method `HB-1982-brittle`), M-N and Q-N capacity of
  linings (`capacity_mn`, `check_capacity`), the Einstein-Schwartz lining forces and `thick_ring_stiffness` (a
  number, without `info`).
- `plot_tunnel`, `build_tunnel_report` and the `rockmass tunnel` command.
- Example 15 (`examples/15-tuneles-convergencia-confinamiento/`).
- `TunnelResult.scc`: the full support curve (elastic part, plateau at psm, kinks when each element yields), drawn in
  the tunnel figure instead of a straight line to the crossing.
- External results (phase 8A): `load_external` (Slide2, RS2 and FLAC3D results reader), RocData table check,
  criteria for external results with `ssr_policy` and the SRF band, `compare_methods` (analytical vs numerical),
  `compare_monitoring` (against field measurements), `lining_forces`, `build_external_report` and the
  `rockmass ext` command.
- FLAC3D export script and example 16.

### Values to confirm

- Not implemented because no source was read: Reed displacement, rigorous generalized Hoek-Brown, steel-set support
  curves by formula, Hoek and Brown (1980) bolt stiffness, maximum pressure of a thick ring (Lame), and the elastic
  bolt reinforcement of RS2-S 21 (its transcription has errata). The maximum average strain of most Hoek support
  items is not published in the sources read, so only the 34 mm bolt (0.2 %) and the 50 mm shotcrete at 28 days
  (0.1 %) carry one; for the rest you give it.
- The squeezing correlation is used outside its fitted range (sigma_cm/p0 or pi/p0 above 0.5) with a note, not an
  error; that band is still to be confirmed.
- Hoek-Brown with `a` other than 0.5 uses the equivalent Mohr-Coulomb in the RocSupport style, which mixes the global
  sigma_cm with the friction angle of the tunnel fit; the output says so in a note. A rigorous solution is pending.
- The RocSupport combination modes (`rocsupport3`, `rocsupport`) are checked against RocSupport help text only
  (Secondary).
- In `tunnel_uncertainty`, `support_probabilities["no_crossing"]` counts the samples whose support was installed
  after full convergence (no crossing, no load); `fs_below_1` counts only crossings with FS below 1.
- External results: the SRF band (`SSR_BAND`, 5 %), the method-spread threshold (10 %) and the monitoring ratio
  (1.5) are provisional values, still to be confirmed.

### Fixed

- `ellipse_boundary_stress` takes the polar angle of the boundary point and converts it to the eccentric angle of
  Inglis' formula (it gave wrong values at intermediate angles).
- `fisher_stats`: a horizontal pole perpendicular to the principal axis no longer changes the mean depending on how
  it was written (0/0 or 180/0); a warning says when the mean direction is not unique.

## [0.3.0] - 2026-11-11

The rest of the continuous RMR curves of Kundu et al. (2020), the curves checked against the paper, and fixes found
while writing the complete notebook.

### Added

- Continuous RMR89 ratings for joint condition and groundwater: `rating_persistence89_continuous`,
  `rating_aperture89_continuous`, `rating_roughness89_continuous` (JRC), `rating_infilling89_continuous` (hard or soft),
  `rating_weathering89_continuous` (*I5 index), `rating_inflow89_continuous` (l/min per 10 m) and
  `rating_water_pressure89_continuous` (pressure / major principal stress), with `JointCondition89Continuous` and
  `jcond89_continuous` for the 0-30 sum.
- RMR14 helpers `rmr14_continuity_rating`, `rmr14_roughness_rating`, `rmr14_infilling_rating`,
  `rmr14_weathering_rating` and `rmr14_alterability_rating`, with `JointCondition14Continuous` and `jcond14_continuous`.
- `Rmr89Input.water_rating`, and `Rmr14Input.joint_condition_rating`, `water_rating` and `alterability_rating`: each
  takes a rating in place of its data (one or the other, not both). `water_rating` can be sampled in
  `classification_uncertainty`.

### Changed

- `Rmr89Result.r_water` is a float (it can come from `water_rating`).

### Fixed

- Continuous RMR89 strength from UCS subtracts 0.01, not 0.1, and the RMR14 joints-per-metre rating uses the exponent
  0.443, not 0.442, as in Table 3 of Kundu et al. (2020); the values came from QuickRMR 1.0.0. Continuous strength
  ratings rise by 0.09 points (up to the cap of 15).
- With `--distributions`, each tramo now draws its own samples: its seed comes from `--seed` and its `id_tramo`, so
  results are reproducible and no longer correlated across tramos. Probabilities change slightly for the same seed.
- The probability text no longer shows `0 %` for classes between 0.5 and 1 %: anything under 1 % shows `<1 %`.
- `load_support_catalog_csv` given a folder now says it expects the CSV file (on Windows it raised `PermissionError`).
- `rockmass history --report` and the Word and HTML report writers create the destination folder if it is missing.

### Documented

- The continuous ratings were compared with QuickRMR 1.0.0, the authors' program: they match to its rounding (0.1)
  except the two constants above and alterability, which QuickRMR cuts at 5 while Fig. 6f of the paper reaches 10.
  At the centre of each range of the discrete tables, every curve falls between the ratings of the neighbouring
  ranges, except spacing under 60 mm, where Bieniawski's own chart is below 5.
- `hb_params` gives the same mb, s and a for `HB2002` and `HB2018`: Hoek & Brown (2019) keep the 2002 equations; the
  2018 edition changes the method id and adds the warning on D.
- `available_profiles()` returns the path of each profile's JSON file; use `sorted(available_profiles())` for the ids.

## [0.2.0] - 2026-11-08

Uncertainty in classifications.

### Added

- Continuous RMR89 functions (`RmrFunctions.Continuous`, method `RMR89-continuous`) for UCS, Is50, RQD and spacing,
  and the helpers `rmr14_strength_rating` and `rmr14_joints_per_m_rating` for RMR14.
- `classification_uncertainty` (RMR89, Q, GSI and Hoek-Brown): Monte Carlo or LHS summaries and probability of each
  class and support.
- Warning `near the boundary between classes {a} and {b}` in range-table classification.
- `--distributions` (with `--sheet-distributions`, `--iterations`, `--sampling`, `--seed`) in `rockmass classify` and
  `report`, and `classify_tramos(..., distributions=...)`: class probabilities per tramo.
- Example 14, `examples/14-incertidumbre-clasificacion/`.

### Changed

- Range-table classification now adds the near-boundary warning also without `--distributions`: it appears in the
  `avisos` column, in the `warnings: N` count and in the report's warnings table. Exit codes do not change.
- `Rmr89Result.r_strength`, `r_rqd` and `r_spacing` are now `float` (they were `int`), so they print as `7.0`.
- With `--distributions`, all tramos use the same seed: each tramo's probabilities are correct, but aggregates across
  tramos are correlated.

### To confirm

- P1: the continuous functions were transcribed from the QuickRMR 1.0.0 program of Kundu et al. (2020); they are
  pending confirmation against the paper (RQD and UCS use max(x - c, 0) to stay monotone).
- P2: no rounding and no jump to 20 above 19.95, unlike QuickRMR (difference up to 0.1).
- P6: the boundary margins (3 points for RMR and GSI, factor 1.25 for Q) are provisional.

## [0.1.1] - 2026-11-07

Packaging and documentation only: the calculations are the same as in 0.1.0.

### Changed

- The PyPI page shows the README in English followed by the Spanish one.
- Installation in both READMEs starts with `pip install rockmasspy`, with the optional extras in a table; building
  from source is only needed on platforms without a wheel, and `pip` does it by itself.

## [0.1.0] - 2026-11-07

First public release. Every result records the method and edition it follows; the library recommends, the engineer
decides. Full documentation: <https://miqueas.dev/rockmasspy>.

### Rock mass classification and strength

- RQD, RMR (Bieniawski 1976 and 1989, Celada et al. 2014), Q (NGI 2015 and 2025 editions, 2025 by default), GSI
  (chart and the quantified GSI of 2013), global correlations (never chained) and Hoek-Brown (2002 and 2018) with its
  equivalent Mohr-Coulomb and rock mass modulus (Hoek 2002, Hoek and Diederichs 2006).
- Site-customizable support tables per labor type (RMR/Q/GSI classes or GSI chart cells) that validate, classify and
  round-trip through JSON, YAML and Excel.
- Charts and field cards (GSI chart, class tables) with matplotlib.
- Tramos (logged intervals), batch processing from CSV/Excel, Word and HTML reports, and the `rockmass` command line.

### Ground support and regulation

- Q support chart (NGI 2025 and 2015, digitized with the measured error stated), ESR and the Barton span, bolt length
  and roof pressure formulas.
- Modified stability graph of Potvin (Mathews), MRMR of Laubscher (1990) with the 1994 caving diagram, and stope
  faces.
- Normative profile for Peru (DS 024-2016-EM) and `rockmass verify`.

### Open pit

- Stereonet, Fisher statistics of sets and Markland kinematic tests; SMR (Romana 1985 and Tomas 2007) and Q-slope.
- Planar, wedge and toppling blocks, probability of failure by Monte Carlo, back analysis and bench–berm design.
- 2D limit equilibrium (Ordinary, Bishop, Janbu, Spencer and Morgenstern-Price/GLE) with circular and block searches,
  non-linear Hoek-Brown, water, tension crack, ponded water and seismic load; yield coefficient and Newmark
  displacement; non-vertical Sarma.
- Acceptance criteria as versioned profiles (Read and Stacey 2009, NDEP 2021, WA DMIRS, Ryan and Pryor, or your own
  table) and a complete slope report.

### Predictive module (mine history)

- `load_history` with an ingest audit, an Excel template for the history and the site correlations of level 1.
- Grouped validation (by labor, by zone and over time), practice audit with an ordinal logit and conformal sets
  (level 2), constant failure rate with gamma frailty and the bound for a new labor (level 3), and `recommend` with
  its blocking rules; `rockmass history` and `rockmass recommend`.
- A synthetic mine calibrated from the literature (`synthetic_mine`, `SCENARIOS`) and a test bench that checks the
  levels against a known truth. The synthetic mine is a test bench only: it trains no model that is delivered.

### Packaging

- Wheels for CPython 3.10 to 3.14 on Linux (x86_64), Windows (AMD64) and macOS, built and tested with cibuildwheel;
  optional extras `io`, `viz`, `report` and `ml`; type stubs (`py.typed`).
- Thirteen worked examples in `examples/` with synthetic data only.

[0.5.0]: https://github.com/Miqueas7/RockMassPy/releases/tag/v0.5.0
[0.4.0]: https://github.com/Miqueas7/RockMassPy/releases/tag/v0.4.0
[0.3.0]: https://github.com/Miqueas7/RockMassPy/releases/tag/v0.3.0
[0.2.0]: https://github.com/Miqueas7/RockMassPy/releases/tag/v0.2.0
[0.1.1]: https://github.com/Miqueas7/RockMassPy/releases/tag/v0.1.1
[0.1.0]: https://github.com/Miqueas7/RockMassPy/releases/tag/v0.1.0
