# RockMassPy

Open-source rock mass engineering library for mining: rock mass classifications (RQD, RMR, Q, GSI, MRMR, Q-slope, SMR),
Hoek-Brown strength, site-customizable classification tables, charts, ground support recommendation, per-country
regulatory profiles, rock slope analysis (kinematics, stereonets, block and limit equilibrium), uncertainty in classifications and data-driven support prediction. C++20 core with a Python API.

**Documentation: <https://miqueas.dev/rockmasspy>** (guide, methods, worked examples and API reference, in English
and Spanish). Changes per version are in [CHANGELOG.md](https://github.com/Miqueas7/RockMassPy/blob/main/CHANGELOG.md).

**Status:** version 0.2.0 (phases 1 to 5: calculation core and per-labor tables, support and the Peru profile, open pit, predictive module, synthetic mine and test bench; phase 7: uncertainty in classifications). The library recommends, the engineer decides.

## Installation

```bash
pip install rockmasspy
```

Prebuilt wheels are published for Python 3.10 to 3.14 on Linux (x86_64), Windows and macOS (Apple Silicon), so no
compiler or CMake is required. The base install has no Python dependencies: the calculations live in the compiled core.

Optional extras add what is not pure calculation:

| Extra | Adds | For |
|---|---|---|
| `io` | `pyyaml`, `openpyxl` | Tables in YAML and Excel; sections, stope faces, slopes and the history template in Excel |
| `viz` | `matplotlib` | Q chart, stability graphs, stereonets, field charts, profiles and maps |
| `report` | `python-docx` | Word report (the HTML report needs nothing extra) |
| `ml` | `numpy`, `scipy` | Predictive module |

```bash
pip install "rockmasspy[io,viz,report,ml]"
```

On other platforms (Linux ARM, Intel Macs) `pip` builds the C++ core from the source distribution, which needs a C++20
compiler.

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

## Uncertainty and class boundaries

`classification_uncertainty` samples the inputs of RMR89, Q, GSI or Hoek-Brown (Monte Carlo or LHS, fixed seed) and
reports mean, sd, p05, p50, p95, minimum and maximum of each output, plus the probability of each class and of each
support of the labor table. It reports; it never changes an attention rule or an exit code. The distributions are
yours: the library only propagates what you give it. A sample the core rejects is an error that names the variable.

```python
import rockmasspy as rm
from rockmasspy import probabilistic as pb

base = rm.Rmr89Input()
base.functions = rm.RmrFunctions.Continuous            # Kundu et al. (2020) curves instead of the table ratings
base.ucs_mpa, base.rqd_pct, base.spacing_m = 90.0, 70.0, 0.3
base.joint_condition_rating, base.water = 20.0, rm.Water.Dry

table = rm.LaborTable("gallery", rm.SupportCatalog([rm.SupportType("I", 1), rm.SupportType("II", 2)]),
                      rm.RangeTable("RMR", "RMR89", [rm.RangeClass(0, 68, "fair", "II"), rm.RangeClass(68, 100, "good", "I")]))
u = rm.classification_uncertainty("RMR89", base, {"ucs_mpa": pb.normal(90, 15, 50, 130), "rqd_pct": pb.uniform(55, 85)},
                                  table=table, n=2000, seed=1)
print(round(u.outputs["rmr"].mean, 1), u.class_probabilities)   # 67.5 {'fair': 0.583, 'good': 0.417}
```

`RmrFunctions.Continuous` uses continuous functions fitted to the Bieniawski (1989) charts (Kundu et al., 2020; method
`RMR89-continuous`), so a small change in UCS, RQD or spacing moves the rating smoothly. Classification against a
range table warns `near the boundary between classes {a} and {b}` when the value is within 3 points of the edge
(RMR, GSI) or within a factor of 1.25 (Q); these two margins are provisional. In batch, a `Distribuciones` sheet per
`id_tramo` adds `clase_probable`, `prob_clase_probable`, `prob_clase`, `probabilidades` and `n_validas` to the results
(`rockmass classify ... --distributions FILE`, also in `report`). See `examples/14-incertidumbre-clasificacion/`.

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
The chart bolt length (`q_carta_longitud_*` columns) is given for ESR = 1; with another ESR, compare it with the Barton et al. (1980) formula and your own judgement.
Points in the dashed zones of the chart (no empirical data) follow their lines and carry `no_empirical_data` and a warning.
In batch, `rm.add_q_chart_reference(results, {"*": "C"})` adds the roof reading using only the tramo's own Q, and the
report gets section 5.1; `viz.plot_q_chart` draws the chart with the tramos (never labelled). From the command line:

```bash
rockmass qsupport --q 4.5 --span 15 --esr-category C --chart point.png      # exit 2 on a warning or category 7 or higher
rockmass classify tramos.xlsx --tables galeria.json --esr "*=C" -o results.csv
```

See `examples/05-sostenimiento-q/`.

## Stope stability (Mathews) and MRMR

Modified Mathews stability number of Potvin (1988): N' = Q' x A x B x C, with the hydraulic radius of each stope face
(`hydraulic_radius`, `hydraulic_radius_rect`) and the stable / transition / caved zones of Potvin's graph, digitized
by RockMassPy. There is no logit curve: Mawdesley publishes no coefficients. Factor C follows Potvin's own equation
(8 - 6 cos a); the 8 - 7 cos of Mathews et al. (1980) belongs to the original method. The MRMR is Laubscher (1990) and
its zones are read on the 1994 diagram. Everything is **Primary**; read points outside the frame are taken on the
unfavourable side, with a warning.

```python
import rockmasspy as rm

# N' = Q' * A * B * C of a synthetic roof face (Q' 12, HR 2.5 m), read on Potvin's stability graph
r = rm.mathews_stability(12.0, 2.5, ucs_mpa=120, sigma1_mpa=30, dip_difference_deg=60,
                         failure_mode="gravity", surface_inclination_deg=0)
print(f"{r.factor_a:.3f} {r.factor_b:.1f} {r.factor_c:.1f}")      # 0.325 0.8 2.0
print(f"{r.n_prime:.2f}")                                         # 6.24
print(r.reading.zone_label)                                       # stable

# MRMR (Laubscher 1990) of a synthetic case, placed on the 1994 caving diagram at HR = 30 m
i = rm.Mrmr90Input()
i.irs_mpa, i.rqd_pct, i.spacings_m, i.joint_condition = 100, 75, [0.5, 1.0, 3.0], 10.8
m = rm.mrmr90(i)
print(m.mrmr_class)                                               # 3B
print(rm.read_stability_graph("Laubscher1994-stability", 30.0, m.mrmr).zone_label)    # caving
```

Faces come from a `Superficies` sheet (xlsx) or a CSV (`rm.SURFACE_COLUMNS`): `rm.load_stope_surfaces`,
`rm.assess_stope_surfaces`, `rm.save_stope_results`, `viz.plot_stability_graph` and `report.build_stope_report`. A
face with impossible geometry stops the run with its row. From the command line:

```bash
rockmass mathews Superficies.csv --chart mathews.png -o results.csv     # exit 2 if a face is in transition, caved or warns
rockmass mrmr --irs 100 --rqd 75 --spacing 0.5 1.0 3.0 --jc 10.8 --hr 30 --chart laubscher.png
```

See `examples/06-tajeos-mathews-mrmr/`.

## Normative verification (Peru, DS 024-2016-EM)

`rockmass verify` and `verify(...)` compare your inputs (per-labor tables, tramos, stope faces and a design sheet set)
with the requirements of a **normative profile**: a JSON file in `python/rockmasspy/profiles/`. The first one is
`PE-DS024-2016`: the Peruvian mining safety regulation (DS 024-2016-EM, with DS 023-2017-EM and DS 034-2023-EM) and the
Osinergmin (2017) geomechanical criteria guide. Every requirement carries its instrument, article, page, URL and
force: **law** (the regulation) or **guide** (a recommendation, which never reads "does not comply"). Text that was
not in force on `--as-of` is reported as not verifiable and says since when the loaded text applies.

Six statuses: complies, does not comply, attention, note, **not checked** (you gave no input for it) and **not
verifiable by the library** (procedural, or no rule for it). Read this part twice:

- **"Not verifiable by the library" is not a non-compliance.** It means the library cannot judge it (a signed study,
  posting in the labor, the quarterly inspection); the engineer checks it.
- **The library never says "approved".** A "complies" only means that the declared numbers meet the numeric limit it
  could check; the signed study and the engineer's judgment remain.
- Exit code 0 if nothing fails, 1 for an input error, 2 if something does not comply or needs attention. Notes, items
  not checked and items not verifiable do not change the code.

```python
import rockmasspy as rm
from rockmasspy.design_inputs import DesignInputs, RefugeStation
from rockmasspy.verify import verify

# one synthetic refuge station: RMR 55 with no declared support, 400 m from the face, 30 m2 for 20 people
st = RefugeStation("E1", "roca", rmr=55, distancia_frente_m=400, area_m2=30, aforo=20)
v = verify(rm.get_profile("PE-DS024-2016"), as_of="2026-11-02", design=DesignInputs(refuge_stations=(st,)))
print("PE-DS024-2016" in rm.available_profiles())        # True
print(v.counts())                                       # {'complies': 2, 'does_not_comply': 1, 'attention': 0, 'note': 0, 'not_checked': 12, 'not_verifiable': 9}
print(v.exit_code)                                      # 2
```

The design sheets are `Estaciones_refugio`, `Refugios_peatonales`, `Resumen_QC`, `Factores_seguridad` and `Autosoporte`
(an xlsx workbook, or one CSV per sheet named after it; all optional). Row identifiers never reach the console or the
report. From the command line:

```bash
rockmass verify --profile PE-DS024-2016 --as-of 2026-11-02 --tables galeria.json --tramos Tramos.csv \
  --surfaces Superficies.csv --design Estaciones_refugio.csv Resumen_QC.csv --report verificacion.html
```

See `examples/07-verificacion-normativa-peru/`.

## Slope kinematics, SMR and Q-slope

For one open-pit slope face and its discontinuity sets, `rockmass slope` and `assess_slopes(...)` return:
- the **Fisher** statistics of each family (mean orientation, kappa, alpha95) and the pole density;
- the **Markland kinematic tests**: planar sliding, wedge sliding (primary and secondary zones), flexural toppling and
  direct toppling (oblique toppling is counted apart), each with its count and percentage;
- the **SMR** (Romana, discrete; Tomas, continuous) per family, per wedge and per plane without a family, with the case
  that governs and its class;
- the **Q-slope** of Bar and Barton and the angle beta, compared with the face dip.

Read this part twice:

- **The percentages are feasibility, not probability.** They are the share of poles (planar, flexural) or of
  intersections (wedge, direct toppling) that fall in the critical zone. They are not a probability of failure.
- **The lateral limit** (30 degrees by default, `--lateral-limit`) keeps planar sliding and both topplings to the
  discontinuities that strike close to the face. Wedge sliding has no lateral limit. The planar count without limits
  is reported too; the exit code uses the one with limits.
- **A face steeper than beta** (`face_steeper_than_beta`) means the face is steeper than the angle Q-slope allows
  without reinforcement or support: it asks for attention. A face equal to beta is also flagged.
- The wedge figure counts primary plus secondary intersections. The continuous SMR (`smr_caso_continuo`) has its own
  governing case, apart from the discrete one.
- `familia` names reach the console in warnings: do not put labor or mine codes in them. `id_talud` and `id_tramo`
  go only to the results file and the report tables, never to the console or the figures.

```python
import rockmasspy as rm

# a synthetic planar case (Tomas et al. 2006, p. 93): face 22/180, joint 21/209, basic RMR 60, normal blasting
a = rm.smr_angles(rm.SmrMode.Planar, 209, 21, rm.PlaneOrientation(180, 22))
print(f"{a.a_deg:.0f} {a.b_deg:.0f} {a.c_deg:.0f}")           # 29 21 -1
d = rm.smr(60, rm.SmrMode.Planar, rm.SmrFunctions.Discrete, rm.SlopeExcavation.NormalBlastingOrMechanical, a)
c = rm.smr(60, rm.SmrMode.Planar, rm.SmrFunctions.Continuous, rm.SlopeExcavation.NormalBlastingOrMechanical, a)
print(f"{d.smr:.0f} {d.smr_class} {c.smr:.1f} {c.smr_class}")  # 52 3 55.7 3
# Q-slope 0.6 (Bar and Barton 2018, Table 12): the steepest angle without reinforcement
print(f"{rm.q_slope_beta(0.6):.2f}")                          # 60.56
```

The faces come from a `Taludes` sheet and the planes from a `Familias` sheet (xlsx, or CSV): `rm.load_slope_faces`,
`rm.load_families`, `rm.assess_slopes`, `rm.slope_counts`, `rm.save_slope_results` (26 columns) and
`report.build_slope_report`. `report.slope_modes` and `report.slope_figure` are the helpers the command line uses for
the stereonets. From the command line (exit 2 if anything asks for attention):

```bash
rockmass slope --faces Taludes.csv --families Familias.csv --report taludes.html --charts fig -o resultados.csv
```

See `examples/08-taludes-cinematica-smr-qslope/`.

## Rock blocks, probability of failure and bench–berm design

On top of the kinematics, `assess_blocks(...)` and `rockmass slope --blocks` run **limit-equilibrium blocks** per row of a
`Bloques` sheet, each tied to a slope face by `id_talud`:
- **planar** sliding (Hoek and Bray), with a tension crack, water, horizontal seismic load, a bolt or an external
  force, and an optional back-analysis (the c–phi pairs that give FS = 1);
- **wedge** sliding by vector resolution (two planes, one plane or lift-off), with water pressure per joint, seismic
  load and an external force;
- **toppling** of regular blocks (Goodman and Bray 1976), with an optional support force at the toe;
- a **berm** (Ritchie modified, 0.2 H + 4.5 m): inter-ramp angle, width against the required one and, with a
  distribution, the berm reliability.

A block row with a `Distribuciones` row for its variables also gets a **probability of failure** (Monte Carlo or Latin
hypercube, truncated normal, exponential or uniform variables, a fixed seed), with the FS mean, deviation and
reliability index. A sampled variable that has a column in `Bloques` must also be filled in the row: the
deterministic FS, the only one that decides attention, runs on that value.

Read this part twice:

- **The PoF depends on the distributions you choose.** The library propagates what you give it; it does not know how
  much your rock mass varies. The same seed, sample size and sheets give the same PoF on any machine.
- **FS equal to 1 counts as failure** (with a 1e-9 margin), a lifted-off sample counts as failure, and the PoF is
  conditional on the block forming (`n` and `n_valid` are reported).
- **The library never says "acceptable".** Only an FS below 1 and the warnings change the exit code. The PoF, the
  berm reliability and the comparison with Ritchie are reported, not judged (only an acceptance criterion you choose judges
  them, see below), and the analysis is 2D, per meter of slope.
- **Privacy:** `id_bloque` and `id_talud` appear only in the report tables and in the results file, never in the
  console, the figures or an error message. Do not put labor or mine codes in `familia` names; they reach warnings.

```python
import rockmasspy as rm
from rockmasspy.probabilistic import Distribution, run_probabilistic

# Sau Mau Ping (RocPlane verification problem 1, in kN): H 60 m, face 50, plane 35, c 100 kPa, phi 35, kh 0.08
i = rm.PlanarInput()
i.height_m, i.face_dip_deg, i.plane_dip_deg = 60, 50, 35
i.unit_weight, i.water_unit_weight, i.cohesion, i.friction_deg, i.kh = 27, 10, 100, 35, 0.08
i.water_fill = 1.0                                    # saturated, no tension crack
print(f"{rm.planar_fs(i).factor_of_safety:.3f}")      # 0.818
crack = rm.critical_tension_crack(60, 50, 35)         # dry-slope critical crack, filled to 90 %
print(f"{crack.depth_m:.4f} {crack.distance_m:.4f}")  # 14.0092 15.3358
i.tension_crack_distance_m, i.water_fill = crack.distance_m, 0.9
print(f"{rm.planar_fs(i).factor_of_safety:.3f}")      # 1.065
variables = {"friction_deg": Distribution("normal", 15, 70, 35, 5),
             "cohesion": Distribution("normal", 0, 250, 100, 20),
             "tension_crack_distance_m": Distribution("normal", 0, 35.34, 15.3, 4),
             "water_fill": Distribution("exponential", 0, 1, 0.5),
             "kh": Distribution("exponential", 0, 0.16, 0.08)}
r = run_probabilistic("planar", i, variables, n=5000, sampling="lhs", seed=9)
print(f"{r.pof * 100:.1f} {r.n_valid}/{r.n}")         # 7.4 5000/5000
print(f"{rm.ritchie_berm_width(12).width_m:.1f}")     # 6.9
```

The blocks come from a `Bloques` sheet (`rm.load_blocks`, one row per analysis, column `modelo` = `planar`, `cuña`,
`volteo` or `berma`) and the random variables from a `Distribuciones` sheet (`rm.load_distributions`: `id_bloque`,
`variable`, `distribucion` = `normal`, `exponencial` or `uniforme`, `media`, `desviacion`, `minimo`, `maximo`), both xlsx
or CSV. Each block takes the face and the mean (Fisher) orientation of the families of its slope, so `Taludes` keeps its
columns. `rm.block_counts` gives the counts and `rm.save_block_results` writes the 25-column results file;
`report.build_slope_report(..., blocks=...)` adds the block tables, and `report.block_figure` draws the FS histogram and
the PoF curve. From the command line (exit 0 if all is well, 1 on an input error, 2 if something asks for attention):

```bash
rockmass slope --faces Taludes.csv --families Familias.csv --blocks Bloques.csv --distributions Distribuciones.csv \
    --iterations 5000 --sampling lhs --seed 9 --blocks-output bloques_resultados.csv --report taludes.html --charts fig
```

Options: `--blocks` (needs `--faces` and `--families`), `--sheet-blocks`, `--distributions`, `--sheet-distributions`,
`--iterations` (default 5000), `--sampling lhs|monte-carlo` (default `lhs`), `--seed` (default 1) and
`--blocks-output RES.csv|.xlsx`. Every option except `--blocks` itself needs `--blocks`.

See `examples/09-bloques-probabilistico-berma/`.

## Limit equilibrium and Newmark

`assess_le(...)` and `rockmass le` compute the **factor of safety of a 2D section by vertical slices**: a pit slope, a
pad or a waste dump, with layers, a piezometric line and a pseudo-static seismic coefficient. Per row of an
`Analisis_LE` sheet:
- the methods: Ordinary (Fellenius), Bishop simplified, Janbu simplified and corrected, Spencer and
  Morgenstern-Price/GLE (half-sine or constant interslice function);
- the slip surface: a **circular search** (grid of centres with radii and local refinement), a **block search** along a
  weak layer, or a given polyline;
- the strength at each slice base: Mohr-Coulomb or **non-linear Hoek-Brown** (Balmer envelope, from GSI and mi or from
  mb, s and a);
- water by `ru` or by a piezometric line (ponded water on the ground included), a tension crack with water and `kh`;
- the **yield coefficient ky** (the kh that brings FS to 1) and the **rigid-block Newmark displacement** for an
  acceleration record.

Read this part twice:

- **With seismic load, use Spencer or GLE.** Bishop does not balance horizontal forces, so a high kh separates it from
  the rigorous methods (Slide2 ACADS 1(d), kh 0.15: Bishop 1.016, Spencer 0.991).
- **The library never says "acceptable".** Only an FS at or below 1 (1e-9 margin) and the warnings change the exit
  code; FS, ky and the Newmark displacement are reported, not judged; see Acceptance criteria and Sarma.
- **Privacy:** `id_seccion`, `id_analisis`, `material`, `registro` and the line names appear only in the report tables
  (the two ids also in the results file), never in the console, the figures or a message.

```python
import rockmasspy as rm

# Fredlund and Krahn (1977), Slide2 verification problem 21, in psf, pcf and ft: c 600, phi 20, gamma 120, dry
s = rm.LeSection()
s.surface = [rm.Point2(x, y) for x, y in [(0, 60), (60, 60), (140, 20), (180, 20)]]
m = rm.LeMaterial()
m.unit_weight, m.cohesion, m.friction_deg = 120, 600, 20
layer = rm.LeLayer()
layer.bottom, layer.material = [], 0                  # a single layer: no bottom line
s.layers, s.materials = [layer], [m]
f = rm.SlipSurface()
f.circle = rm.Circle(120, 90, 80)                     # xc, yc, R
bishop = rm.le_factor_of_safety(s, f, rm.LeMethod.Bishop)
spencer = rm.le_factor_of_safety(s, f, rm.LeMethod.Spencer)
print(f"{bishop.factor_of_safety:.3f}")               # 2.076
print(f"{spencer.factor_of_safety:.3f}")              # 2.072
print(spencer.info.method_id)                         # Spencer
```

The sheets are `Geometria` (one row per vertex: `id_seccion`, `linea`, `x_m`, `y_m`; the line `superficie` is
required and `piezometrica` optional), `Estratos` (`orden` 1 on top, `material`, `linea_base`), `Materiales_LE`
(`mohr_coulomb` or `hoek_brown`), `Analisis_LE` (`metodos` separated by `;`, the first one searches; `superficie` =
`circular`, `bloque` or `dada`; `kh`, `registro`) and `Sismos` (`registro`, `t_s`, `a_g` in g, constant step), as one
xlsx or one CSV per sheet. `rm.le_counts` gives the counts, `rm.save_le_results` writes one row per method (with
`kh` and `fs_estatico`, the static FS of each method on the static critical surface),
`report.build_slope_report(..., le=...)` adds the limit-equilibrium tables and `report.le_figure` /
`report.newmark_figure` draw the section and the Newmark record. From the command line (exit 0 if all is well, 1 on an
input error, 2 if something asks for attention):

```bash
rockmass le --geometry Geometria.csv --layers Estratos.csv --materials Materiales_LE.csv --analyses Analisis_LE.csv \
    --records Sismos.csv --output equilibrio_resultados.csv --report taludes.html --charts fig
```

Options: `--workbook LIBRO.xlsx` (instead of the CSV files), `--records`, `-o/--output RES.csv|.xlsx`,
`--report OUT.docx|.html`, `--charts DIR`, `--title`, `--author`, `--lang es|en` and `--no-figures`. With more than
one analysis, `rockmass le` prints `analysis <k> of <n>...` on stderr.

Run times: with Hoek-Brown, a 20×20×11 circular search takes about 10 to 15 s; with kh, ky by rounds can repeat it up
to 5 times.

See `examples/10-equilibrio-limite-newmark/`.

## Acceptance criteria and Sarma

`assess_criteria(...)` and `rockmass slope|le --criteria` compare each block (3B) and each limit-equilibrium analysis
(3C) with an **acceptance criterion** chosen by you, and say per check **"meets", "fails" or "not verifiable"**, always
with the criterion, its source, its force (law or guide) and its mark. The criteria are versioned data profiles:
- `READ-STACEY-2009`: Read and Stacey (2009), table 9.9, minimum static FS and maximum PoF by scale (bench, inter-ramp,
  overall) and consequence; mark V2 (read in Moffitt 2023, which reproduces it), without the dynamic column;
- `NDEP-2021`: Nevada heap leach pads, static FS 1.30, pseudo-static 1.05 and, below 1.05, a deformation analysis;
- `DMIRS-WA-2019`: Western Australia, FS by consequence;
- `RYAN-PRYOR-2000`: catch bench reliability of 50 to 90 %;
- your own table (sheet `Criterios`: `escala`, `consecuencia`, `fs_estatico_min`, `fs_seudoestatico_min`,
  `pof_max_pct`, `confiabilidad_berma_min_pct`, `fuente`), read by `rm.load_criteria_table` as a guide with mark
  `user`.

Each row of `Bloques` and `Analisis_LE` takes `escala` (`banco`, `interrampa`, `global`, `pad`, `botadero`) and
`consecuencia`; `Analisis_LE` also takes `periodo_retorno_anios`. The profile `PE-DS024-2016` checks **art. 264** of
the DS 024 (a pseudo-static analysis of the overall pit slope with a 100-year return period; it sets no FS).

**Sarma with non-vertical slices** (`superficie = sarma`, the base in `linea_superficie` and one interface angle per
interior vertex in `sarma_angulos`, or `opt` to search them) splits the mass into rigid wedges with inclined
interfaces and gives the FS and the critical acceleration Kc. It is the method for waste dumps sliding on an inclined
weak base. It reproduces Slide's Sarma verification problem 4 (1.1970 against 1.198) and, with one wedge, Hoek's planar
block. Hoek-Brown, ponded water and tension cracks are not supported.

Read this part twice:

- **The library never says "approved".** A "fails" asks for attention (exit code 2); a "not verifiable" is a note
  with its reason (no scale, no criterion for that scale, no probabilistic analysis). It never counts as "meets".
- **Ranges:** where a criterion is a range (PoF 25–50 % for a bench), the default policy is the conservative end (the
  upper end for a minimum FS, the lower end for a maximum PoF); `range_policy=` or `--range-policy upper|lower` change
  it, and the value used is reported. A value equal to the limit meets it.
- **Privacy:** the ids appear only in the report tables and the results files, never in the console or a message.

```python
import csv
import tempfile
from pathlib import Path

import rockmasspy as rm
from rockmasspy.criteria import criteria_assignments

# Slide Sarma verification, problem 4 (Hoek 1987): a dry waste pile on a sheared floor, in kN and m
ground = [(-50, -2.97), (0, 0), (111.4, 76.5), (229.545, 13.6815), (250, 14.9)]
floor = [(-50, -2.97), (0, 0), (250, 14.9)]
base = [(0, 0), (108, 6.4), (130, 73.06)]             # two wedges, one interior vertex
s = rm.LeSection()
s.surface = [rm.Point2(x, y) for x, y in ground]
top, bottom = rm.LeLayer(), rm.LeLayer()
top.bottom, top.material = [rm.Point2(x, y) for x, y in floor], 0
bottom.bottom, bottom.material = [], 1
pile, sheared = rm.LeMaterial(), rm.LeMaterial()
pile.unit_weight, pile.cohesion, pile.friction_deg = 15.7, 100, 42
sheared.unit_weight, sheared.cohesion, sheared.friction_deg = 15.7, 10, 6
s.layers, s.materials = [top, bottom], [pile, sheared]
i = rm.SarmaInput()
i.base, i.interface_angles_deg = [rm.Point2(x, y) for x, y in base], [116.5]  # from +x, counter-clockwise
r = rm.sarma_fs(s, i)
print(f"{r.factor_of_safety:.3f} {r.critical_acceleration:.4f}")  # 1.197 0.0540

# The same section from sheets, judged (for illustration) as a heap leach pad against NDEP (2021)
d = Path(tempfile.mkdtemp())
def sheet(name, cols, rows):
    with open(d / f"{name}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, cols, restval="")
        w.writeheader()
        w.writerows(rows)
    return d / f"{name}.csv"
src = {"Geometria": sheet("Geometria", rm.GEOMETRY_COLUMNS, [
           dict(id_seccion="S", linea=n, x_m=x, y_m=y)
           for n, pts in (("superficie", ground), ("piso", floor), ("falla", base)) for x, y in pts]),
       "Estratos": sheet("Estratos", rm.LAYER_COLUMNS, [dict(id_seccion="S", orden=1, material="pila", linea_base="piso"),
                                                       dict(id_seccion="S", orden=2, material="piso")]),
       "Materiales_LE": sheet("Materiales_LE", rm.MATERIAL_COLUMNS, [
           dict(material="pila", modelo="mohr_coulomb", peso_unitario_kn_m3=15.7, cohesion_kpa=100, friccion_grados=42),
           dict(material="piso", modelo="mohr_coulomb", peso_unitario_kn_m3=15.7, cohesion_kpa=10, friccion_grados=6)]),
       "Analisis_LE": sheet("Analisis_LE", rm.ANALYSIS_COLUMNS, [
           dict(id_analisis="A", id_seccion="S", superficie="sarma", linea_superficie="falla", sarma_angulos="116.5",
                base_modelo_m=-10, escala="pad", consecuencia="media")])}
le = rm.assess_le(src)
checks = rm.assess_criteria(rm.get_profile("NDEP-2021"), le=le, assignments=criteria_assignments(le=le))
print(f"{le[0].sarma.factor_of_safety:.3f}")          # 1.197
print(rm.criteria_counts(checks))                     # {'checks': 3, 'meets': 0, 'fails': 1, 'not_verifiable': 2}
print([(c.item_id, c.status) for c in checks][0])     # ('NDEP-6-estatico', 'fails')
print(checks[1].reason)                               # no pseudo-static analysis
```

`rm.save_criteria_results` writes one row per check (sheet `Criterios_resultados`), and
`report.build_slope_report(..., criteria=..., criteria_profile=..., profile_checks=...)` builds the full slope report:
executive summary, scope and criteria, kinematics, blocks, limit equilibrium and Sarma, criteria checks, regulation
(art. 264), warnings and methods. From the command line:

```bash
rockmass le --geometry Geometria.csv --layers Estratos.csv --materials Materiales_LE.csv --analyses Analisis_LE.csv \
    --records Sismos.csv --criteria READ-STACEY-2009 --profile PE-DS024-2016 --criteria-output criterios.csv
rockmass slope --faces Taludes.csv --families Familias.csv --blocks Bloques.csv --criteria Criterios.csv
```

Options: `--criteria ID|CRITERIOS.csv|.xlsx`, `--criteria-output RES.csv|.xlsx`, `--range-policy
conservative|upper|lower` (both need `--criteria`) and, in `rockmass le`, `--profile PE-DS024-2016`. The summary prints
`meets: a, fails: b, not verifiable: c` and the fails grouped by rule, without ids.

See `examples/11-criterios-sarma/`.

## Mine history: ingest audit and site correlations

Needs the extra `pip install "rockmasspy[ml]"` (numpy and scipy) for the correlations; reading and auditing the
history need only the base package (Excel needs `[io]`). `rm.load_history` reads the history template
(`plantillas/Plantilla_historico_geomecanico.xlsx`: sheets `Tramos`, `Tipos_sostenimiento` and `Desempeno`), and
`rm.audit_history` recomputes Q and the basic RMR89, flags non-independent records and cross-sheet inconsistencies,
and counts how far each predictive level is from its minimum (a design decision, not a published value).

```python
import rockmasspy as rm
from rockmasspy.predictive import fit_site_correlation, save_site_correlations

h = rm.load_history("historico.xlsx")
audit = rm.audit_history(h)
fit = fit_site_correlation(h, "rmr_from_q", group_by="litologia")
print(fit.mine.status, fit.mine.a, fit.mine.b)       # "site", "unstable" or "not_calibrated"
save_site_correlations(fit, "results/")              # CSV with every fit, JSON with the "site" ones only
```

Level 1 fits `rmr_from_q`, `gsi_from_rmr` and `gsi_from_q_prime` per domain and for the whole mine: OLS with a
prediction interval, Deming only when you give the error-variance ratio, a bootstrap that resamples whole
excavations, and a conjugate Bayesian fit centred on the published global correlation, so few data stay close to it.
`to_custom_correlation()` turns a fit into a `CustomCorrelation` for your per-labor tables. From the command line:

```bash
rockmass history historico.xlsx --correlations --output results/ --report historico.docx
```

The CLI and the report print counts and codes (domains as D1, D2…), never the excavation, zone, coordinates or
lithology, and never the input file name. Result files do carry `id_tramo` and the domain: keep them in the mine's
protected folder, like the history. See `examples/12-historico-prediccion/`.

### Practice audit (level 2) and failure model with recommendation (level 3)

```python
from rockmasspy.predictive import audit_practice, fit_performance, recommend, save_model

practice = audit_practice(h)                  # ordinal logit of the installed type: describes, never recommends
model = fit_performance(h)                    # "site", "partial" or "not_calibrated"
recs = recommend(model, new_tramos, threshold=0.10, exposure_days=365, practice=practice)
save_model(model, "model.json")               # coefficients, ranges and counts; never rows or ids
```

- **Level 2** fits a cumulative logit of the installed support type on ln Q, ln De (span/ESR), service life and
  excavation type. It says whether the practice is coherent with rock quality and span, whether it is more
  predictable than the NGI Q chart, and which tramos have an installed type outside their 90 % conformal set
  (≈ 10 % by construction: it is not a detector of deviations). A consistency indicator, 1 − tanh(w/4) with w the
  mean width of the inner logit bands, flags a `practice poorly consistent` practice above 0.66.
- **Level 3** models the failure rate with a constant hazard and a gamma frailty per excavation (exposure as offset),
  with sign constraints (worse rock or a larger span never lowers the risk; more support never raises it) and a
  zone-clustered robust covariance. P(failure within H days) for a new excavation is 1 − (1 + θλH)^(−1/θ).
- **Validation** is grouped by excavation, leave-one-zone-out and temporal, against a constant-rate dummy and the
  NGI-category baseline, with a bootstrap over excavations. The model is `site` only if the excavation and zone
  partitions beat both references (95 % CI of the Poisson-deviance gain above zero, no failed folds) and the
  temporal one is not worse.
- **Form:** additive in quality and support rank, or with the interaction (quality − max)·(rank − max) bounded
  ≥ 0 (risk stays monotone in both). The interaction enters only with 10 events per parameter counting it and a
  lower out-of-fold Poisson deviance (folds by excavation, another seed than the validation); if it ends at its
  bound, the additive form comes back.
- **Recommendation:** the lightest eligible type whose upper bound, 1 − exp(−λ_up·H·Z_q), stays under the
  threshold. λ_up adds the frailty quantile with upper θ and a **new zone**: σ_z² = C·Var(η at the mean) with the
  zone-clustered covariance, taken at its one-sided χ² upper bound σ̂_z·sqrt((C − 1)/χ²₁₋ᵤ(C − 1)), u = 0.5 + level/2
  (`PerformanceModel.zone_sd_upper`; ×1.80 with 8 zones and ×2.37 with 5 at level 0.9). With fewer than 10 zones
  `fit_performance` warns. The threshold and the horizon are set by the engineer: there are no defaults.
- **Nothing is chosen** when the model is not `site`, the tramo extrapolates, the support effect is not
  identified, or a sign constraint on rock quality or span is active, and also when (gates, design decisions):
  (a) the tramo is in the worst third of quality and the out-of-fold observed/expected there exceeds 1.2 or has
  fewer than 10 failures; (b) a type has fewer than 10 training tramos in the tramo's Q class (Barton et al. 1974;
  RMR classes of Bieniawski 1989 with `quality="rmr"`) — such a type is not eligible; (d) the tramo's excavation
  type had fewer than 10 failures in training. (c) When no type meets the threshold it says so (`no support type
  meets the threshold`), and so it does when the types that meet it are not eligible. The options are always
  shown, with the reason.

```bash
rockmass history historico.xlsx --practice --performance --model-output model.json --output results/ \
    --threshold 0.10 --exposure-days 365 --report historico.docx
rockmass recommend new_tramos.xlsx --model model.json --threshold 0.10 --exposure-days 365 \
    --practice-from historico.xlsx --output recommendations.csv
```

`recommend` prints each tramo by position; `recommendations.csv` carries `id_tramo` and two empty columns,
`decision_ingeniero` and `motivo`, where the engineer records what was decided. The minimum data per level were
checked by simulation (`docs/investigacion/SIMULACION_MINIMOS.md` in the repository). The library recommends, the
engineer decides.

## Synthetic mine and test bench

`synthetic_mine` builds a **synthetic mine calibrated with the literature** to test the predictive module end to end
against a known truth. It is a test bench: it never trains a model that is shipped, gives no priors or default
coefficients and never replaces a mine's own history.

```python
from rockmasspy.predictive import SCENARIOS, synthetic_mine

h, truth = synthetic_mine("base", seed=0)         # History (Tramos, Tipos_sostenimiento, Desempeno) and MineTruth
h_bad, truth_bad = synthetic_mine("base", seed=0, defects=True)   # same mine plus injected data defects
truth.rmr_lnq_slope                               # the RMR–ln Q line of the mine (it emerges; it is not fixed)
truth.p_fail("T0001", "III", 365)                 # true P(failure within 365 days) with type III, new excavation
```

- **Mechanism:** the true rock mass comes from geology (quality per lithology and zone, an AR(1) process along each
  excavation plus nugget, Poisson fault zones); joint parameters come from that quality and Q, RMR89 and GSI are
  computed with the library, so the RMR–ln Q relation and its scatter emerge. Each excavation is mapped by a
  geologist with bias and noise; the mine installs support from its own GSI table with deviations, a table change
  and unsupported hours; failure is a constant hazard with gamma frailty driven by the deficit against the Q chart
  read with Q·exp(−δ) (δ = 0.5 in `base`, a site somewhat worse than NGI). `failure_mechanism="saturating"` is an
  alternative without chart or deficit, so the module is not tuned to one recipe.
- **Truth:** `MineTruth.tramos` keeps the true values, geologist, installed and table types, frailty and, for
  each tramo, the true rate of every support type (with the unsupported hours that type would have had);
  `p_fail(id, type, H)` is closed form, marginal over the frailty of a new excavation in the same zone
  (`conditional=True` for the tramo's own excavation). `truth.defects` lists the injected defects.
- **Scenarios** (`SCENARIOS`): `base` (≈ 800 tramos, 5 zones), `ngi_site` (the site equals the NGI chart),
  `worse_site`, `better_site`, `shifted_correlation`, `conservative_practice`, `incoherent_practice`,
  `mine_practice`, `noisy_mapping`, `small_mine` (≈ 80 tramos), `large_mine` (≈ 4800 tramos, 8 zones),
  `saturating_large` and `saturating_worse` (the alternative mechanism). A `MineScenario` can be built or changed
  with `dataclasses.replace`.

**Bench results** (`docs/investigacion/BANCO_MINA_SINTETICA.md` in the repository; 50 seeds per scenario, 20 in the
large ones; recommendation applied to a second mine of the same scenario, with zones and excavations the fit did
not see; threshold 0.10, H = 365 days):

| Scenario | Chooses | Too light, pooled | Too light per mine, p90 / max | Overcost vs true optimum (median) |
|---|---:|---:|---:|---:|
| `large_mine` | 30.8 % | 0.7 % | 0.5 % / 4.6 % | +261 % |
| `saturating_large` | 41.8 % | 0.5 % | 1.3 % / 2.6 % | +146 % |
| `shifted_correlation` | 1.8 % | 1.1 % | 1.9 % / 3.2 % | +220 % |
| `incoherent_practice` | 1.9 % | 0.2 % | 0.1 % / 0.3 % | +431 % |
| `base` | 0.3 % | 0.0 % | 0.0 % / 0.0 % | +201 % |
| `worse_site`, `ngi_site`, `better_site`, `conservative_practice`, `small_mine` | 0 | — | — | — |

Before the 5B corrections, `large_mine` chose in 60.7 % with 5.0 % too light and `worse_site` reached 23.4 %. Now
the per-mine p90 stays at or under 3.7 % in every cell with ln Q. Safety was bought with support and fewer
choices: with few zones σ_z is poorly known and its upper bound covers it with more support, not with more
information. Where the model chooses it is much safer than the Q chart alone in the same tramos.

**Module changes from the bench (Phase 5B):**

- Level 2: the consistency indicator above (cut 0.66); the ordinal logit converges with large n (mean gradient
  criterion).
- Audit: `missing_values`, one finding per column with empty cells (counts only, no `id_tramo`); the Q rule is
  |Q recorded − Q recomputed| > max(0.005, 1 % of Q) or a ratio over 2 (`Q_MAX_RATIO`), and Q recorded ≤ 0 is
  always a finding.
- Level 1: `gsi_from_rmr` warns that GSI and RMR share joint condition and RQD (correlated mapping errors).
- Level 3: the interaction form, the χ² upper bound of σ_z, the gates (a)–(d) and the warning with fewer than 10
  zones (above). The model JSON goes to **schema 4** (`zone_sd`, `poor_rock`, `class_counts`,
  `labor_type_failures`); an older schema is rejected with a hint to refit with
  `rockmass history --performance --model-output`.

See `examples/13-mina-sintetica/`: one mine through the audit and levels 1–3, measured against its truth.

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
| Q-NGI-2025-chart / Q-NGI-2015-chart | Q support chart regions, digitized by RockMassPy (max. measured error 0.017 / 0.008 decade, including junctions) | Primary |
| Q-Barton1980 | Maximum unsupported span and bolt length formulas (Hoek, after Barton et al. 1980) | Secondary |
| Q-GrimstadBarton1993 | Roof support pressure (Hoek, after Grimstad & Barton 1993); the unit is still to be confirmed | Secondary |
| Mathews-Potvin1988 | Modified stability number N' (factors A, B, C), hydraulic radius and the stability graph, digitized by RockMassPy (max. measured error 0.014 grid cell; factor A fit 0.019, sliding C 0.044, B curves 0.007) | Primary |
| MRMR-Laubscher1990 / Laubscher1994-stability | MRMR (Laubscher 1990) and its caving diagram (1994, max. measured error 0.009 grid cell) | Primary |
| SMR-Romana1985 / SMR-Tomas2007 | SMR of Romana (discrete) and Tomas (continuous, revision 2017) for planar and toppling failure | PrimaryLaterAuthors |
| SMR-Romana1985-wedge | Discrete SMR for wedges (Anbalagan 1992 adaptation, as described by Tomas) | Secondary |
| Q-slope-BarBarton2017 | Q-slope and the angle beta (Bar and Barton 2017, 2018) | PrimaryLaterAuthors |
| Kinematic-PlanarSliding / -WedgeSliding / -FlexuralToppling-Goodman1980 / -DirectToppling-HudsonHarrison1997 | Markland kinematic tests (criteria of the Dips documentation) | Secondary |
| Fisher1953-set-statistics | Fisher statistics of a discontinuity set (after Tauxe et al.) | Secondary |
| GSI-2013 | Quantified GSI (Hoek, Carter & Diederichs) | Primary |
| HB-2002 / HB-2018 | Hoek-Brown criterion parameters (`hb_params`) and equivalent Mohr-Coulomb (`hb_mohr_coulomb`); 2018 is the default | Primary |
| HB-2002 | Rock mass modulus Em (`em_hoek2002`) | Secondary |
| HD-2006 | Rock mass modulus (Hoek & Diederichs) | Primary |
| Correlations (enum name, e.g. `RmrFromQ_Bieniawski1976`) | Global correlations, never chained | Primary or Secondary, see `rm.correlate(...).info` |

Out of phase 1A: TBM Fe, Q 1974, GSI equation 3, mi/MR tables.

## Python notes

Some C++ names are reserved words in Python, so they get a trailing underscore:

- `Infilling.None_` (no infilling), as in `JointCondition89(..., rm.Infilling.None_, ...)`.
- `CorrelationResult.from_` and `CustomCorrelation.from_` (the `from_` argument of its constructor).

Results print readably (`QResult(q=4.5, ...)`) and the package ships type stubs (`py.typed`).

## How to cite

If RockMassPy helps your work, please cite it. GitHub shows a "Cite this repository" button built from
[CITATION.cff](https://github.com/Miqueas7/RockMassPy/blob/main/CITATION.cff):

> Quintanilla Ventura, M. (2026). *RockMassPy: rock mass classifications, Hoek-Brown strength and mining
> geomechanics* (version 0.2.0) [Computer software]. https://github.com/Miqueas7/RockMassPy

Each result also records the method and edition it follows (`result.info`); cite that original source as well.

License: MIT.
