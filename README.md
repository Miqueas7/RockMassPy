# RockMassPy

Open-source rock mass engineering library for mining: rock mass classifications (RQD, RMR, Q, GSI, MRMR, Q-slope, SMR),
Hoek-Brown strength, site-customizable classification tables, charts, ground support recommendation, per-country
regulatory profiles, open-pit slope analysis and data-driven support prediction. C++20 core with a Python API.

**Status:** phase 1A (calculation core) and 1B (per-labor tables) done on branches `fase-1a` and `fase-1b`; no release yet. The library recommends, the engineer decides.

## Install (from source)

Needs Python >= 3.10 and a C++20 compiler.

```bash
pip install .
```

## Minimal example

```python
import rockmasspy as rm

q = rm.q_value(rm.QInput(65, 9, 1.5, 2, 1, 1))          # rqd, Jn, Jr, Ja, Jw, SRF
print(q.q, q.info.method_id)                             # 5.4167 Q-NGI-2025

gsi = rm.gsi_from_jcond89_rqd(18, 65).gsi                # 59.5
p = rm.hb_params(gsi, 25, 0)                             # mi = 25, D = 0, HB-2018
scm = rm.hb_global_strength(90.0, p)
s3 = rm.hb_sigma3max(scm, 0.027, 400, rm.HbApplication.Tunnel)   # MN/m3, depth in m
mc = rm.hb_mohr_coulomb(90.0, p, s3)
print(mc.phi_deg, mc.cohesion_mpa)                       # 52.75 2.633
```

A full synthetic walk-through is in `examples/01-tramo-sintetico/`.

## Per-labor support tables

Each labor type (gallery, stope...) gets its own table: a catalog of support types plus RMR/Q/GSI classes or GSI chart cells.
Tables validate (warn, never block), classify, and round-trip through JSON, YAML and Excel. YAML and Excel need the optional extra: `pip install "rockmasspy[io]"`.

```python
import rockmasspy as rm

cat = rm.SupportCatalog([rm.SupportType("I", 1), rm.SupportType("II", 2, bolt=rm.Bolt("split-set", 1.8, 1.5))])
classes = [(80, "I", "I"), (60, "II", "I"), (40, "III", "II"), (20, "IV", "II"), (0, "V", "II")]
table = rm.RangeTable("RMR", "RMR89", [rm.RangeClass(lo, lo + 20, label, sup) for lo, label, sup in classes])
labor = rm.LaborTable("gallery", cat, table, span_m=(3, 4))
print(labor.validate())             # []
c = labor.classify(53)
print(c.label, c.support.code)      # III II
print(labor.classify(40).label)     # IV
```

A value exactly on a class boundary (RMR 40) takes the worse class. The library recommends, the engineer decides.
See `examples/02-tabla-por-labor/`.

`RatingTable` (your own ratings per parameter, RMR89 by default) is available in Python. Saving it in the labor-table
files (JSON, YAML, Excel) and importing it from CSV are deferred to phase 1C.

## Methods

Every result carries `info.method_id` and a verification mark: **Primary** (verified in the original source, or a
faithful reproduction of its equations by a cited author), **PrimaryLaterAuthors** (verified in a later publication by
the same authors) or **Secondary** (checked against a secondary source only). **UserDefined** means calibrated by the user on site data.

| method_id | Method | Verification |
|---|---|---|
| RQD-Deere | RQD from core | Secondary |
| RQD-PH1976 | RQD from discontinuity frequency (Priest & Hudson) | Primary |
| RQD-P1982 | RQD from Jv (Palmstrom 1982) | Primary |
| RQD-P2005 | RQD from Jv (Palmstrom 2005) | Secondary |
| RMR76 | Bieniawski 1976 | Secondary |
| RMR89 | Bieniawski 1989 | Secondary |
| RMR14 | Celada et al. 2014 | Secondary |
| Q-NGI-2015 / Q-NGI-2025 | Q system, NGI editions (2025 is the default) | Primary |
| GSI-2013 | Quantified GSI (Hoek, Carter & Diederichs) | Primary |
| HB-2002 / HB-2018 | Hoek-Brown criterion parameters (`hb_params`) and equivalent Mohr-Coulomb (`hb_mohr_coulomb`); 2018 is the default | Primary |
| HB-2002 | Rock mass modulus Em (`em_hoek2002`) | Secondary |
| HD-2006 | Rock mass modulus (Hoek & Diederichs) | Primary |
| Correlations (enum name, e.g. `RmrFromQ_Bieniawski1976`) | Global correlations, never chained | Primary or Secondary, see `rm.correlate(...).info` |

Out of phase 1A: TBM Fe, Q 1974, GSI equation 3, mi/MR tables, support pressure and maximum span.

## Python notes

Some C++ names are reserved words in Python, so they get a trailing underscore:

- `Infilling.None_` (no infilling), as in `JointCondition89(..., rm.Infilling.None_, ...)`.
- `CorrelationResult.from_` and `CustomCorrelation.from_` (the `from_` argument of its constructor).

Results print readably (`QResult(q=4.5, ...)`) and the package ships type stubs (`py.typed`).

License: MIT.
