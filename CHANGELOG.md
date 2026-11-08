# Changelog

All released versions of RockMassPy. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
the project uses [semantic versioning](https://semver.org/). Before 1.0 the API may still change between minor
versions.

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

[0.1.1]: https://github.com/Miqueas7/RockMassPy/releases/tag/v0.1.1
[0.1.0]: https://github.com/Miqueas7/RockMassPy/releases/tag/v0.1.0
