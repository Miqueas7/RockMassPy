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

`RatingTable` (your own ratings per parameter, RMR89 by default) is available in Python and is saved with the labor table
(`LaborTable.rating`) in JSON, YAML, Excel and CSV (`save_csv_dir` / `load_csv_dir`).

CSV is a folder with one file per sheet (UTF-8 with BOM). `save_csv_dir(t, path)` writes the number format of the
computer (on Windows the one Excel uses, elsewhere the locale), so colleagues in Spain or the US open it in their own
Excel; pass `separator=` (`","` or `";"`) and/or `decimal=` (`"."` or `","`) to force one. `load_csv_dir` reads both, matches file names case-insensitively (`TABLA.CSV` is `Tabla`) and also takes the
date as `d/m/yyyy` (day first).

## Charts

Needs the optional extra `pip install "rockmasspy[viz]"` (matplotlib 3.8 or newer). Without it, `import rockmasspy` still
works and any `rockmasspy.viz` call raises an `ImportError` that names the extra. Figures are plain matplotlib `Figure`
objects (no global state, no windows).

```python
import rockmasspy.viz as viz

style = viz.Style(lang="en", size="cartilla", brand="My company")   # lang "es" (default) or "en"; size "cartilla", "A4" or "A3"
fig = viz.plot_cartilla(labor, style=style)                         # `labor` comes from the block above
path = viz.save_figure(fig, "figs/cartilla.png")                    # creates the folder; png, svg or pdf
print(path.name)                                                    # cartilla.png
p = rm.hb_params(45, 10, 0)                                         # HbParams keeps no GSI, mi or D...
env = viz.plot_hb_envelopes(50.0, p, sigma3max_mpa=1.35, gsi=45, mi=10, d=0)  # ...so pass them for the footer
```

The same module draws the quantified GSI chart, Hoek-Brown envelopes, Q-RMR scatter and class histograms; every figure
states its source in the footer. The library recommends, the engineer decides. See `examples/03-cartillas/`.

## Tramos, batch, report and CLI

Needs the extras `pip install "rockmasspy[io,viz,report]"` (the HTML report only needs the base package; Word needs
`[report]`, figures need `[viz]`). `load_tramos` reads a `Tramos` sheet (Excel or CSV) and takes a `column_map` from
your column names to the template's. Classification never stops on a bad row: a tramo with no table for its labor or
span, or without the method value, stays unclassified (`label=None`) with a warning, and the summary counts it apart.
Neither the library nor the CLI prints tramo rows.

```python
from pathlib import Path

import rockmasspy as rm
import rockmasspy.report as rp

Path("tramos.csv").write_text("id_tramo,Labor,luz_m,RMR\nT01,gallery,3.5,53\n", encoding="utf-8")   # a one-row sheet
tramos = rm.load_tramos("tramos.csv", column_map={"RMR": "rmr_valor", "Labor": "tipo_labor"})   # CSV: the sheet is the file name
results = rm.classify_tramos(tramos, [labor])                      # `labor` comes from the tables section
summary = rm.summarize(results)
rm.save_results(results, "results.csv")                            # or .xlsx (needs [io])
report = rp.build_memoria(results, [labor], title="Calculation report", lang="en")
rp.write_html(report, "report.html")                               # rp.write_docx(report, "report.docx") needs [report]
print(summary.total, summary.classified)                           # 1 1
```

Every report states what it is: "The library recommends, the engineer decides. This document does not replace the
signed geomechanical study." on the cover and in each page footer, plus the edition and verification mark of each
method and the RockMassPy version. `rp.build_anexo39b` gives the Annex 39 B layout of DS 024.

The same pipeline from the command line (exit code 0 ok, 1 input or usage error, 2 done but needs attention):

```bash
rockmass check galeria.json
rockmass cartilla galeria.json -o cartilla.png --lang en
rockmass classify tramos.xlsx --tables galeria.json -o results.csv
rockmass report tramos.xlsx --tables galeria.json -o report.docx --template anexo39b --labor gallery
```

See `examples/04-informe/`.

## Q support chart (reference)

Digitized from the NGI Q-system support chart (2025, Fig. 4-1; 2015 edition, Fig. 7), with the ESR table, the
equivalent dimension De = span / ESR and three classical formulas marked **Secondary**. It is a reference next to your own
tables, never a replacement. ESR is a safety decision: `esr_category` is required, and categories with a range (A, B) also need `esr`.

```python
from rockmasspy.q_support import recommend_q_support

r = recommend_q_support(4.5, 15.0, esr_category="C")      # public Hoek chamber: Q 4.5, span 15 m
print(r.roof.category)                                    # 3
print(f"{r.roof.de_m:.3f}")                               # 9.375
print(r.roof.no_empirical_data)                           # False
w = recommend_q_support(0.4, 4.5, esr_category="C", edition="Q-NGI-2015", wall_height_m=4.5)
print(w.wall_q)                                           # 1.0
```

Hoek publishes category 4 for this chamber, read on an older (1993) chart; the digitized 2025 and 2015 charts give 3.
Points in the dashed zones of the chart (no empirical data) follow their lines and carry `no_empirical_data` and a warning.
In batch, `rm.add_q_chart_reference(results, {"*": "C"})` adds the roof reading using only the tramo's own Q, and the
report gets section 5.1; `viz.plot_q_chart` draws the chart with the tramos (never labelled). From the command line:

```bash
rockmass qsupport --q 4.5 --span 15 --esr-category C --chart point.png      # exit 2 on a warning or category 7 or higher
rockmass classify tramos.xlsx --tables galeria.json --esr "*=C" -o results.csv
```

See `examples/05-sostenimiento-q/`.

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
