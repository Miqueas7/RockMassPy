# Changelog

All released versions of RockMassPy. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
the project uses [semantic versioning](https://semver.org/). Before 1.0 the API may still change between minor
versions.

## [0.2.1] - 2026-11-10

Fixes found while writing the complete notebook.

### Fixed

- With `--distributions`, each tramo now draws its own samples: its seed comes from `--seed` and its `id_tramo`, so
  results are reproducible and no longer correlated across tramos. Probabilities change slightly for the same seed.
- The probability text no longer shows `0 %` for classes between 0.5 and 1 %: anything under 1 % shows `<1 %`.
- `load_support_catalog_csv` given a folder now says it expects the CSV file (on Windows it raised `PermissionError`).
- `rockmass history --report` and the Word and HTML report writers create the destination folder if it is missing.

### Documented

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

[0.2.1]: https://github.com/Miqueas7/RockMassPy/releases/tag/v0.2.1
[0.2.0]: https://github.com/Miqueas7/RockMassPy/releases/tag/v0.2.0
[0.1.1]: https://github.com/Miqueas7/RockMassPy/releases/tag/v0.1.1
[0.1.0]: https://github.com/Miqueas7/RockMassPy/releases/tag/v0.1.0
