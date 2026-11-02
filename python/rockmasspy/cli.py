"""Línea de comandos `rockmass`: solo presenta lo que la librería calcula.

Nunca imprime filas de tramos: solo conteos, nombres de archivo y avisos de las tablas de diseño.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Sequence

from .batch import add_q_chart_reference, classify_tramos, parse_esr_spec, q_chart_crosstab, save_results, summarize
from .q_chart_data import ESR_TABLES
from .report.texts import t
from .table_files import load_table
from .tramos import load_tramos

_INPUT_ERRORS = (ValueError, ImportError, OSError)


def _column_map(path):
    if path is None:
        return None
    m = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(m, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in m.items()):
        raise ValueError("column map must be a JSON object of text to text")
    return m


def _check(a) -> int:
    n = 0
    for path in a.tables:
        for i in load_table(path).validate():
            print(f"{Path(path).name}: {i.kind} [{i.edition}] {i.message}")
            n += 1
    print(f"{n} issue(s)")
    return 2 if n else 0


def _cartilla(a) -> int:
    from .viz import Style, plot_cartilla, save_figure

    fig = plot_cartilla(load_table(a.table), style=Style(lang=a.lang, size=a.size, brand=a.brand or ""),
                        title=a.title, show_lines=not a.no_lines)
    print(f"cartilla: {save_figure(fig, a.output)}")
    return 0


def _esr_specs(values: Sequence[str]) -> dict:
    """`C`, `A:4`, `labor=C` o `labor=A:4`; sin `labor=` va a la clave "*"."""
    syntax = "expected C, A:4, labor=C or labor=A:4"
    out = {}
    for v in values:
        labor, eq, spec = v.rpartition("=")
        if eq and not labor:
            raise ValueError(f"invalid --esr {v!r}: {syntax}")
        try:
            val = parse_esr_spec(spec)
        except ValueError:
            raise ValueError(f"invalid --esr {v!r}: {syntax}") from None
        if isinstance(val, str) and val in _ESR_EXAMPLE:  # A y B tienen rango: la CLI pide el valor
            lo, hi, _ = ESR_TABLES["Q-NGI-2025"][val]
            raise ValueError(f"ESR category {val} covers {lo:g}-{hi:g}; use {val}:<esr>, "
                             f"e.g. {val}:{_ESR_EXAMPLE[val]}")
        out[labor if eq else "*"] = val
    return out


_ESR_EXAMPLE = {"A": "4", "B": "2.5"}


def _classify_all(a):
    tables = [load_table(p) for p in a.tables]
    tramos = load_tramos(a.tramos, sheet=a.sheet, column_map=_column_map(a.column_map))
    esr = _esr_specs(a.esr) if a.esr else None  # antes de clasificar: un --esr malo falla temprano
    results = classify_tramos(tramos, tables)
    if esr:
        results = add_q_chart_reference(results, esr, edition=a.q_edition)
    return results, tables


def _print_chart_summary(a, results) -> None:
    if not a.esr:
        return
    n = sum(1 for r in results if r.q_chart)
    print(f"q chart ({a.q_edition}): {n} with reference, {len(results) - n} without")
    for (code, cat), k in sorted(q_chart_crosstab(results).items()):
        print(f"{code} / Q cat {cat}: {k}")


def _print_summary(s) -> int:
    print(f"total: {s.total}\nclassified: {s.classified}\nunclassified: {s.unclassified}")
    for (labor, label), n in sorted(s.by_labor_class.items()):
        print(f"{labor} / {label}: {n}")
    print(f"warnings: {s.warnings_count}")
    return 2 if s.unclassified else 0


def _classify(a) -> int:
    results, _ = _classify_all(a)
    out = save_results(results, a.output)
    code = _print_summary(summarize(results))
    _print_chart_summary(a, results)
    print(f"results: {out}")
    return code


def _report(a) -> int:
    from . import report as rp

    if a.template == "memoria" and a.labor is not None:
        raise ValueError("--labor applies only to --template anexo39b")
    ext = Path(a.output).suffix.lower()
    if ext not in (".docx", ".html"):
        raise ValueError("output must end in .docx or .html")
    results, tables = _classify_all(a)
    title = a.title or t("default_title", a.lang)
    kw = dict(title=title, lang=a.lang, author=a.author or "", figures=not a.no_figures)
    if a.template == "anexo39b":
        rep = rp.build_anexo39b(results, tables, labor_type=a.labor, **kw)
    else:
        rep = rp.build_memoria(results, tables, **kw)
    out = rp.write_docx(rep, a.output, author=a.author or "") if ext == ".docx" else rp.write_html(rep, a.output)
    code = _print_summary(summarize(results))
    _print_chart_summary(a, results)
    print(f"report: {out}")
    return code


def _qsupport(a) -> int:
    from .q_support import recommend_q_support

    if (a.jn is None) != (a.jr is None):
        raise ValueError("--jn and --jr go together")
    r = recommend_q_support(a.q, a.span, esr_category=a.esr_category, esr=a.esr, edition=a.edition,
                            wall_height_m=a.wall_height, high_stress=a.high_stress, jn=a.jn, jr=a.jr)
    ro = r.roof
    print(f"edition: {r.edition}")
    print(f"esr: {r.esr_used:g} (category {r.esr_category})")
    print(f"de_m: {ro.de_m:.3f}")
    for name, x in (("roof", ro), ("walls", r.walls)):
        if x is None:
            continue
        print(f"{name} category: {x.category}")
        for k in ("label", "shotcrete_mm", "sfr_energy_j", "bolt_spacing_with_sfr_m",
                  "bolt_spacing_without_sfr_m", "bolt_length_chart_m"):
            print(f"{name} {k}: {getattr(x, k)}")
        print(f"{name} chart: [{x.info.method_id}, {x.info.verification.name}]")
    if r.wall_q is not None:
        print(f"wall q: {r.wall_q:g}")
    fs = [("max unsupported span", r.max_unsupported_span), ("bolt length", r.bolt_length_formula)]
    if r.roof_pressure is not None:
        fs.append(("pressure", r.roof_pressure))
    for name, f in fs:
        print(f"{name}: {f.value:.3g} {f.unit}".rstrip() + f" [{f.info.method_id}, {f.info.verification.name}]")
    for w in r.warnings:
        print(f"warning: {w}")
    for n in r.notes:
        print(f"note: {n}")
    print("the library recommends, the engineer decides")
    if a.chart:
        from .viz import Style, plot_q_chart, save_figure

        fig = plot_q_chart(r.edition, points=[(ro.q, ro.de_m)], style=Style(lang=a.lang))
        print(f"chart: {save_figure(fig, a.chart)}")
    return 2 if r.warnings or max(ro.category, r.walls.category if r.walls else 0) >= 7 else 0


def _mathews(a) -> int:
    from collections import Counter

    from . import report as rp
    from .stope_surfaces import assess_stope_surfaces, load_stope_surfaces, save_stope_results, stope_zone_counts

    ext = Path(a.report).suffix.lower() if a.report else ""
    if a.report and ext not in (".docx", ".html"):
        raise ValueError("report must end in .docx or .html")
    rs = assess_stope_surfaces(load_stope_surfaces(a.surfaces, sheet=a.sheet, column_map=_column_map(a.column_map)))
    if not rs:
        raise ValueError(f"no surfaces in {Path(a.surfaces).name}")
    counts = stope_zone_counts(rs)
    ws = Counter(w for r in rs for w in set(r.mathews.warnings))
    info = rs[0].mathews.reading.info
    print(f"graph: {rs[0].mathews.graph} [{info.verification.name}]")
    print(f"surfaces: {len(rs)}")
    for z, name in ((1, "stable"), (2, "transition"), (3, "caved")):
        print(f"{name}: {counts[z]}")
    print(f"warnings: {sum(1 for r in rs if r.mathews.warnings)}")
    for w, n in sorted(ws.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"warning: {w} ({n})")
    if a.output:
        print(f"results: {save_stope_results(rs, a.output)}")
    if a.chart:
        from .viz import Style, plot_stability_graph, save_figure

        fig = plot_stability_graph(rs[0].mathews.graph, cases=[(r.mathews.reading.x, r.mathews.reading.y) for r in rs],
                                   style=Style(lang=a.lang))
        print(f"chart: {save_figure(fig, a.chart)}")
    if a.report:
        rep = rp.build_stope_report(rs, title=a.title or t("stope_title", a.lang), lang=a.lang, author=a.author or "",
                                    figures=not a.no_figures)
        out = rp.write_docx(rep, a.report, author=a.author or "") if ext == ".docx" else rp.write_html(rep, a.report)
        print(f"report: {out}")
    print("the library recommends, the engineer decides")
    return 2 if ws or counts[2] or counts[3] else 0


def _verify(a) -> int:
    import datetime

    from . import report as rp
    from .design_inputs import load_design_inputs
    from .normative import get_profile, profile_esr_specs
    from .stope_surfaces import assess_stope_surfaces, load_stope_surfaces
    from .verify import verify

    if a.tramos and not a.tables:
        raise ValueError("--tramos needs --tables")
    ext = Path(a.report).suffix.lower() if a.report else ""
    if a.report and ext not in (".docx", ".html"):
        raise ValueError("report must end in .docx or .html")
    profile = get_profile(a.profile)
    as_of = a.as_of or datetime.date.today().isoformat()
    esr = profile_esr_specs(profile, as_of)  # valida la fecha antes de leer archivos
    tables = [load_table(p) for p in a.tables or ()]
    results = ()
    if a.tramos:
        results = classify_tramos(load_tramos(a.tramos, sheet=a.sheet, column_map=_column_map(a.column_map)), tables)
        results = add_q_chart_reference(results, esr, edition=a.q_edition)
    stopes = assess_stope_surfaces(load_stope_surfaces(a.surfaces)) if a.surfaces else ()
    design = load_design_inputs(a.design) if a.design else None
    v = verify(profile, as_of=as_of, tables=tables, results=results, stopes=stopes, design=design)
    c = v.counts()
    print(f"profile: {profile.profile_id} (as of {v.as_of})\nrequirements: {len(v.findings)}")
    for s, label in (("complies", "complies"), ("does_not_comply", "does not comply"), ("attention", "attention"),
                     ("note", "notes"), ("not_checked", "not checked"), ("not_verifiable", "not verifiable by the library")):
        print(f"{label}: {c[s]}")
    for f in v.findings:
        if f.status in ("does_not_comply", "attention"):
            print(f"{f.status.replace('_', ' ')}: {f.item.article} [{f.item.force}] {f.message}")
    if a.report:
        title = a.title or t("verif_title", a.lang)
        rep = rp.build_verification_report(v, title=title, lang=a.lang, author=a.author or "")
        out = rp.write_docx(rep, a.report, author=a.author or "") if ext == ".docx" else rp.write_html(rep, a.report)
        print(f"report: {out}")
    print("the library verifies what it can check; it does not replace the signed study")
    return v.exit_code


def _slopes(n: int) -> str:
    return f"{n} slope" + ("" if n == 1 else "s")


def _slope(a) -> int:
    from collections import Counter

    from . import report as rp
    from .slopes import assess_slopes, load_families, load_slope_faces, save_slope_results, slope_counts

    ext = Path(a.report).suffix.lower() if a.report else ""
    if a.report and ext not in (".docx", ".html"):
        raise ValueError("report must end in .docx or .html")
    if not 0 < a.lateral_limit < 90:
        raise ValueError("--lateral-limit must be between 0 and 90 degrees")
    faces = load_slope_faces(a.faces, sheet=a.sheet_faces)
    if not faces:
        raise ValueError(f"no slope faces in {Path(a.faces).name}")
    rs = assess_slopes(faces, load_families(a.families, sheet=a.sheet_families),
                       lateral_limit_deg=a.lateral_limit)
    c = slope_counts(rs)
    proj = a.projection.replace("-", "_")
    print(f"slopes: {c['slopes']}")
    print(f"planes: {c['n_planes']}")
    print(f"intersections: {c['n_intersections']}")
    print(f"planar sliding: {c['planar']} of {c['n_planes']} poles")
    print(f"planar sliding (no lateral limits): {c['planar_no_limits']}")
    print(f"wedge sliding: {c['wedge_primary']} primary, {c['wedge_secondary']} secondary of {c['n_intersections']} intersections")
    print(f"flexural toppling: {c['flexural_toppling']} of {c['n_planes']} poles")
    print(f"direct toppling: {c['direct_toppling']}, oblique {c['direct_toppling_oblique']} of {c['n_intersections']} intersections")
    for m, name in (("d", "discrete"), ("c", "continuous")):
        print(f"SMR {name}: " + " | ".join(f"{r} {c[f'smr_{m}_{k}']}" for k, r in enumerate(("I", "II", "III", "IV", "V"), 1)))
    print(f"Q-slope: {c['q_slope_evaluated']} faces, {c['face_steeper_than_beta']} steeper than beta")
    print(f"warnings: {c['warnings']} in {_slopes(sum(1 for r in rs if r.warnings))}")
    for w, n in sorted(Counter(w for r in rs for w in set(r.warnings)).items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"warning: {w} ({_slopes(n)})")
    print(f"notes: {c['notes']}")
    if a.output:
        print(f"results: {save_slope_results(rs, a.output)}")
    if a.charts:
        from .viz import save_figure

        for n, r in enumerate(rs, 1):
            for mode in (None, *rp.slope_modes(r)):
                path = Path(a.charts) / f"estereograma_{n}_{mode or 'density'}.png"
                print(f"chart: {save_figure(rp.slope_figure(r, mode, a.lang, proj), path)}")
    if a.report:
        rep = rp.build_slope_report(rs, title=a.title or t("slope_title", a.lang), lang=a.lang, author=a.author or "",
                                    figures=not a.no_figures, projection=proj)
        out = rp.write_docx(rep, a.report, author=a.author or "") if ext == ".docx" else rp.write_html(rep, a.report)
        print(f"report: {out}")
    print("the library recommends, the engineer decides")
    return 2 if any(r.needs_attention for r in rs) else 0


def _snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name.rstrip("_")).lower()


def _enum(cls, value: str, flag: str):
    members = {_snake(m.name): m for m in cls}  # los nombres salen del enum enlazado, en CamelCase
    if value.lower() not in members:
        raise ValueError(f"invalid {flag} {value!r}; choose one of: {', '.join(members)}")
    return members[value.lower()]


def _mrmr(a) -> int:
    from . import _rockmasspy_core as rm
    from .stability_graphs import read_stability_graph

    if a.chart and a.hr is None:
        raise ValueError("--chart needs --hr")
    rqd_path, ff_path = a.rqd is not None or a.spacing is not None, a.ff is not None or a.sets is not None
    if rqd_path == ff_path or (rqd_path and (a.rqd is None or a.spacing is None)) or (ff_path and (a.ff is None or a.sets is None)):
        raise ValueError("give exactly one path: --rqd and --spacing, or --ff and --sets")
    if rqd_path and a.core_recovery is not None:
        raise ValueError("--core-recovery goes with --ff and --sets")
    has_desc = any((a.jc_large, a.jc_small, a.water, a.jc_filling, a.jc_altered))
    if (a.jc is not None) == has_desc or (has_desc and not (a.jc_large and a.jc_small and a.water)):
        raise ValueError("give --jc, or --jc-large, --jc-small and --water (optional --jc-filling, --jc-altered)")
    i = rm.Mrmr90Input()
    i.irs_mpa = a.irs
    if rqd_path:
        i.rqd_pct, i.spacings_m = a.rqd, a.spacing
    else:
        i.ff_per_m, i.joint_sets = a.ff, a.sets
        if a.core_recovery is not None:
            i.core_recovery_pct = a.core_recovery
    if a.jc is not None:
        i.joint_condition = a.jc
    else:
        j = rm.JointCondition90()
        j.large, j.small = _enum(rm.JointExpressionLarge, a.jc_large, "--jc-large"), _enum(rm.JointExpressionSmall, a.jc_small, "--jc-small")
        j.water = _enum(rm.JointWater90, a.water, "--water")
        if a.jc_filling:
            j.filling = _enum(rm.JointFilling90, a.jc_filling, "--jc-filling")
        j.altered_wall = a.jc_altered
        i.joint_condition = rm.joint_condition90(j)
    for field, v in (("weathering_pct", a.weathering), ("orientation_pct", a.orientation), ("stress_pct", a.stress),
                     ("blasting_pct", a.blasting)):
        if v is not None:
            setattr(i, field, v)
    r = rm.mrmr90(i)
    warnings = list(r.warnings)
    print(f"edition: {r.info.method_id} [{r.info.verification.name}]")
    print(f"irs rating: {r.irs_rating:g}")
    if rqd_path:
        print(f"rqd rating: {r.rqd_rating:g}")
        print(f"spacing rating: {r.spacing_rating:g}")
    else:
        print(f"ff rating: {r.ff_rating:g}")
    print(f"joint condition: {r.joint_condition:g}")
    print(f"rmr: {r.rmr:g} (class {r.rmr_class})")
    print(f"adjustment: {r.adjustment * 100:g}%")
    print(f"mrmr: {r.mrmr:g} (class {r.mrmr_class})")
    point = None
    if a.hr is not None:
        g = read_stability_graph("Laubscher1994-stability", a.hr, r.mrmr)
        print(f"zone: {g.zone} {g.zone_label} [{g.info.method_id}, {g.info.verification.name}]")
        warnings += g.warnings
        point = (g.x, g.y)
    for w in warnings:
        print(f"warning: {w}")
    print("the library recommends, the engineer decides")
    if a.chart:
        from .viz import Style, plot_stability_graph, save_figure

        print(f"chart: {save_figure(plot_stability_graph('Laubscher1994-stability', points=[point], style=Style(lang=a.lang)), a.chart)}")
    return 2 if warnings else 0


class _Parser(argparse.ArgumentParser):
    """Los errores de uso salen con 1 (2 queda para «terminó pero hay avisos»)."""

    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(1, f"error: {message}\n")


def _parser() -> argparse.ArgumentParser:
    p = _Parser(prog="rockmass", description="RockMassPy command line.")
    p.add_argument("--debug", action="store_true", help="show the traceback on errors")
    sub = p.add_subparsers(dest="cmd", parser_class=_Parser)

    c = sub.add_parser("check", help="validate tables and print their issues")
    c.add_argument("tables", nargs="+", metavar="TABLE")
    c.set_defaults(fn=_check)

    c = sub.add_parser("cartilla", help="save the support chart of a table")
    c.add_argument("table", metavar="TABLE")
    c.add_argument("-o", "--output", required=True)
    c.add_argument("--lang", choices=("es", "en"), default="es")
    c.add_argument("--size", choices=("cartilla", "A4", "A3"), default="cartilla")
    c.add_argument("--brand")
    c.add_argument("--title")
    c.add_argument("--no-lines", action="store_true")
    c.set_defaults(fn=_cartilla)

    def batch_args(c):
        c.add_argument("tramos", metavar="TRAMOS")
        c.add_argument("--tables", nargs="+", required=True, metavar="TABLE")
        c.add_argument("-o", "--output", required=True)
        c.add_argument("--sheet", default="Tramos")
        c.add_argument("--column-map", metavar="MAP.json")
        c.add_argument("--esr", nargs="+", metavar="SPEC", help="Q chart reference: C, A:4, labor=C or labor=A:4")
        c.add_argument("--q-edition", choices=("Q-NGI-2025", "Q-NGI-2015"), default="Q-NGI-2025")

    c = sub.add_parser("classify", help="classify tramos and save the results")
    batch_args(c)
    c.set_defaults(fn=_classify)

    c = sub.add_parser("report", help="build a .docx or .html report")
    batch_args(c)
    c.add_argument("--template", choices=("memoria", "anexo39b"), default="memoria")
    c.add_argument("--labor")
    c.add_argument("--lang", choices=("es", "en"), default="es")
    c.add_argument("--title")
    c.add_argument("--author")
    c.add_argument("--no-figures", action="store_true")
    c.set_defaults(fn=_report)

    c = sub.add_parser("qsupport", help="Q chart support recommendation for one opening")
    c.add_argument("--q", type=float, required=True)
    c.add_argument("--span", type=float, required=True, metavar="M")
    c.add_argument("--esr-category", required=True, metavar="A-G")
    c.add_argument("--esr", type=float)
    c.add_argument("--edition", choices=("Q-NGI-2025", "Q-NGI-2015"), default="Q-NGI-2025")
    c.add_argument("--wall-height", type=float, metavar="M")
    c.add_argument("--high-stress", action="store_true")
    c.add_argument("--jn", type=float)
    c.add_argument("--jr", type=float)
    c.add_argument("--chart", metavar="OUT.png")
    c.add_argument("--lang", choices=("es", "en"), default="es")
    c.set_defaults(fn=_qsupport)

    c = sub.add_parser("mathews", help="Mathews-Potvin stability of stope faces")
    c.add_argument("surfaces", metavar="SUPERFICIES")
    c.add_argument("--sheet", default="Superficies")
    c.add_argument("--column-map", metavar="MAP.json")
    c.add_argument("-o", "--output", metavar="RESULTADOS.csv|.xlsx")
    c.add_argument("--chart", metavar="OUT.png")
    c.add_argument("--report", metavar="OUT.docx|.html")
    c.add_argument("--title")
    c.add_argument("--author")
    c.add_argument("--lang", choices=("es", "en"), default="es")
    c.add_argument("--no-figures", action="store_true")
    c.set_defaults(fn=_mathews)

    c = sub.add_parser("mrmr", help="MRMR (Laubscher 1990) and caving diagram zone")
    c.add_argument("--irs", type=float, required=True, metavar="MPA")
    c.add_argument("--rqd", type=float, metavar="PCT")
    c.add_argument("--spacing", type=float, nargs="+", metavar="M")
    c.add_argument("--ff", type=float, metavar="F")
    c.add_argument("--sets", type=int, metavar="N")
    c.add_argument("--core-recovery", type=float, metavar="PCT")
    c.add_argument("--jc", type=float, metavar="RATING")
    c.add_argument("--jc-large", metavar="NAME")
    c.add_argument("--jc-small", metavar="NAME")
    c.add_argument("--jc-filling", metavar="NAME")
    c.add_argument("--jc-altered", action="store_true")
    c.add_argument("--water", metavar="NAME")
    for k in ("weathering", "orientation", "stress", "blasting"):
        c.add_argument(f"--{k}", type=float, metavar="PCT")
    c.add_argument("--hr", type=float, metavar="M")
    c.add_argument("--chart", metavar="OUT.png")
    c.add_argument("--lang", choices=("es", "en"), default="es")
    c.set_defaults(fn=_mrmr)
    c = sub.add_parser("verify", help="check inputs against a normative profile")
    c.add_argument("--profile", required=True, metavar="ID")
    c.add_argument("--as-of", metavar="YYYY-MM-DD")
    c.add_argument("--tables", nargs="+", metavar="TABLE")
    c.add_argument("--tramos", metavar="TRAMOS")
    c.add_argument("--sheet", default="Tramos")
    c.add_argument("--column-map", metavar="MAP.json")
    c.add_argument("--q-edition", choices=("Q-NGI-2025", "Q-NGI-2015"), default="Q-NGI-2025")
    c.add_argument("--surfaces", metavar="SUPERFICIES")
    c.add_argument("--design", nargs="+", metavar="FILE")
    c.add_argument("--report", metavar="OUT.docx|.html")
    c.add_argument("--title")
    c.add_argument("--author")
    c.add_argument("--lang", choices=("es", "en"), default="es")
    c.set_defaults(fn=_verify)
    c = sub.add_parser("slope", help="rock slope kinematics, SMR and Q-slope")
    c.add_argument("--faces", required=True, metavar="TALUDES")
    c.add_argument("--families", required=True, metavar="FAMILIAS")
    c.add_argument("--sheet-faces", default="Taludes")
    c.add_argument("--sheet-families", default="Familias")
    c.add_argument("--lateral-limit", type=float, default=30.0, metavar="DEG")
    c.add_argument("--projection", choices=("equal-area", "equal-angle"), default="equal-area")
    c.add_argument("-o", "--output", metavar="RESULTADOS.csv|.xlsx")
    c.add_argument("--charts", metavar="DIR")
    c.add_argument("--report", metavar="OUT.docx|.html")
    c.add_argument("--title")
    c.add_argument("--author")
    c.add_argument("--lang", choices=("es", "en"), default="es")
    c.add_argument("--no-figures", action="store_true")
    c.set_defaults(fn=_slope)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    for s in (sys.stdout, sys.stderr):  # una etiqueta no codificable no debe abortar el resumen
        if hasattr(s, "reconfigure"):
            s.reconfigure(errors="replace")
    parser = _parser()
    a = parser.parse_args(argv)
    if a.cmd is None:
        parser.print_help()
        return 1
    try:
        return a.fn(a)
    except _INPUT_ERRORS as e:
        if a.debug:
            raise
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
