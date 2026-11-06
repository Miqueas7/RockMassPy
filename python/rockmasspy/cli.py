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
    le = ()
    if a.workbook or a.records or any(getattr(a, attr) for attr, _, _ in _LE_CSV):  # para el art. 264
        from .limit_equilibrium import assess_le

        le = assess_le(_le_source(a, "--le"))
    v = verify(profile, as_of=as_of, tables=tables, results=results, stopes=stopes, design=design, le=le)
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


def _blocks(n: int) -> str:
    return f"{n} block" + ("" if n == 1 else "s")


_BLOCK_ONLY = (("distributions", "--distributions"), ("blocks_output", "--blocks-output"),
               ("iterations", "--iterations"), ("sampling", "--sampling"), ("seed", "--seed"))


def _block_args(a) -> None:
    """Valida las opciones de bloques antes de leer archivos; deja los valores por defecto en `a`."""
    if not a.blocks:
        for attr, flag in _BLOCK_ONLY:
            if getattr(a, attr) is not None:
                raise ValueError(f"{flag} needs --blocks")
        return
    a.iterations = 5000 if a.iterations is None else a.iterations
    a.seed = 1 if a.seed is None else a.seed
    a.sampling = a.sampling or "lhs"
    if a.iterations < 1:
        raise ValueError("--iterations must be at least 1")
    if a.seed < 0:
        raise ValueError("--seed must be 0 or more")
    if a.blocks_output and Path(a.blocks_output).suffix.lower() not in (".csv", ".xlsx"):
        raise ValueError("--blocks-output must end in .csv or .xlsx")


_CRITERIA_ONLY = (("criteria_output", "--criteria-output"), ("range_policy", "--range-policy"))


def _criteria_args(a):
    """Valida las opciones de criterios antes de leer archivos; devuelve (perfil de criterios, perfil normativo)."""
    from .criteria import load_criteria_table
    from .normative import available_profiles, get_profile

    if not a.criteria:
        for attr, flag in _CRITERIA_ONLY:
            if getattr(a, attr) is not None:
                raise ValueError(f"{flag} needs --criteria")
    if a.criteria_output and Path(a.criteria_output).suffix.lower() not in (".csv", ".xlsx"):
        raise ValueError("--criteria-output must end in .csv or .xlsx")
    norm = None
    if getattr(a, "profile", None):
        if a.profile not in available_profiles():  # sin repetir el valor, como --criteria
            raise ValueError("--profile: unknown profile id (see available_profiles())")
        norm = get_profile(a.profile)
        if not any(i.check == "pseudostatic_analysis_present" for i in norm.items):
            raise ValueError("--profile: the profile has no pseudo-static analysis requirement (art. 264)")
    if not a.criteria:
        return None, norm
    if a.criteria in available_profiles():
        return get_profile(a.criteria), norm
    if Path(a.criteria).suffix.lower() in (".csv", ".xlsx"):
        return load_criteria_table(a.criteria), norm
    # sin repetir el valor: puede ser una ruta
    raise ValueError(f"--criteria: not a profile id ({', '.join(sorted(available_profiles()))}) "
                     f"nor a .csv or .xlsx table")


def _assess_criteria(a, prof, norm, blocks=(), le=()):
    """(chequeos de criterios, chequeos del perfil normativo); cada uno None si no se pidió."""
    from .criteria import assess_criteria, criteria_assignments, return_periods

    asg, tr = criteria_assignments(blocks, le), return_periods(le)
    checks = None if prof is None else assess_criteria(prof, blocks=blocks, le=le, assignments=asg,
                                                        range_policy=a.range_policy, return_periods=tr)
    pchecks = None if norm is None else [c for c in assess_criteria(norm, le=le, assignments=asg, return_periods=tr)
                                         if c.rule == "pseudostatic_analysis_present"]
    return checks, pchecks


_STATUS_EN = {"meets": "meets", "fails": "fails", "not_verifiable": "not verifiable"}


def _print_criteria(prof, norm, checks, pchecks) -> bool:
    """Líneas del resumen, sin ids; True si algo «no cumple» (R10)."""
    from .criteria import criteria_attention, criteria_counts, profile_marks

    if checks is not None:
        c = criteria_counts(checks)
        print(f"criteria: {prof.profile_id} ({', '.join(profile_marks(prof))})")
        print(f"meets: {c['meets']}, fails: {c['fails']}, not verifiable: {c['not_verifiable']}")
        for rule, n in sorted(criteria_attention(checks).items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"fails by rule: {rule} ({n})")
    for x in pchecks or ():
        print(f"profile: {norm.profile_id}, {x.item_id}: {_STATUS_EN[x.status]} [{x.force}]"
              + (f" ({x.reason})" if x.reason else ""))
    return bool(checks and criteria_attention(checks)) or any(x.needs_attention for x in pchecks or ())


def _slope(a) -> int:
    from collections import Counter

    from . import blocks as bk
    from . import report as rp
    from .slopes import assess_slopes, load_families, load_slope_faces, save_slope_results, slope_counts

    ext = Path(a.report).suffix.lower() if a.report else ""
    if a.report and ext not in (".docx", ".html"):
        raise ValueError("report must end in .docx or .html")
    if not 0 < a.lateral_limit < 90:
        raise ValueError("--lateral-limit must be between 0 and 90 degrees")
    _block_args(a)
    if a.criteria and not a.blocks:
        raise ValueError("--criteria needs --blocks")
    prof, _ = _criteria_args(a)
    faces = load_slope_faces(a.faces, sheet=a.sheet_faces)
    if not faces:
        raise ValueError(f"no slope faces in {Path(a.faces).name}")
    rs = assess_slopes(faces, load_families(a.families, sheet=a.sheet_families),
                       lateral_limit_deg=a.lateral_limit)
    bs = []
    if a.blocks:  # antes del primer print: un error de bloques deja stdout vacío
        dists = bk.load_distributions(a.distributions, sheet=a.sheet_distributions) if a.distributions else ()
        bs = bk.assess_blocks(bk.load_blocks(a.blocks, sheet=a.sheet_blocks), rs, dists, iterations=a.iterations,
                              sampling=a.sampling.replace("-", "_"), seed=a.seed, lateral_limit_deg=a.lateral_limit)
    checks, _ = _assess_criteria(a, prof, None, blocks=bs)
    c = slope_counts(rs)
    proj = a.projection.replace("-", "_")
    print(f"slopes: {c['slopes']}")
    n_kin = sum(r.kinematics is not None for r in rs)
    print(f"kinematics run on {n_kin} of {_slopes(c['slopes'])}; planes: {c['n_planes']}")
    print(f"intersections: {c['n_intersections']}")
    print(f"planar sliding: {c['planar']} of {c['n_planes']} poles")
    print(f"planar sliding (no lateral limits): {c['planar_no_limits']}")
    print(f"wedge sliding: {c['wedge_primary']} primary, {c['wedge_secondary']} secondary of {c['n_intersections']} intersections")
    print(f"flexural toppling: {c['flexural_toppling']} of {c['n_planes']} poles")
    print(f"direct toppling: {c['direct_toppling']}, oblique {c['direct_toppling_oblique']} of {c['n_intersections']} intersections")
    for m, name in (("d", "discrete"), ("c", "continuous")):
        print(f"SMR {name}: " + " | ".join(f"{r} {c[f'smr_{m}_{k}']}" for k, r in enumerate(("I", "II", "III", "IV", "V"), 1)))
    print(f"Q-slope: {c['q_slope_evaluated']} faces, {c['face_steeper_than_beta']} steeper than beta")
    if a.blocks:  # solo agregados de block_counts: nunca un id (R18)
        b = bk.block_counts(bs)
        print(f"blocks: {b['blocks']} (planar {b['planar']}, wedge {b['wedge']}, toppling {b['toppling']}, "
              f"berm {b['berm']})")
        print(f"blocks formed: {b['formed']} of {b['planar'] + b['wedge'] + b['toppling']}")
        print(f"FS at or below 1: {b['fs_below_1']} of {b['with_fs']} blocks with FS")
        print(f"probabilistic: {_blocks(b['probabilistic'])}, {a.iterations} iterations, {a.sampling}, seed {a.seed}")
        print(f"PoF above 0: {b['pof_above_0']} of {_blocks(b['probabilistic'])}")
        print(f"berms narrower than required: {b['berm_narrower']} of {b['berm']}")
        print(f"berm reliability evaluated: {b['berm_reliability_evaluated']}")
        print(f"warnings: {c['warnings'] + b['warnings']} in {_slopes(sum(1 for r in rs if r.warnings))} and "
              f"{_blocks(sum(1 for r in bs if r.warnings))}")
    else:
        print(f"warnings: {c['warnings']} in {_slopes(sum(1 for r in rs if r.warnings))}")
    for w, n in sorted(Counter(w for r in rs for w in set(r.warnings)).items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"warning: {w} ({_slopes(n)})")
    for w, n in sorted(bk.warning_counts(bs).items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"warning: {w} ({_blocks(n)})")
    print(f"notes: {c['notes'] + sum(len(r.notes) for r in bs)}")
    crit_fails = _print_criteria(prof, None, checks, None)
    if a.output:
        print(f"results: {save_slope_results(rs, a.output)}")
    if a.blocks_output:
        print(f"blocks results: {bk.save_block_results(bs, a.blocks_output)}")
    if a.criteria_output:
        from .criteria import save_criteria_results

        print(f"criteria results: {save_criteria_results(checks, a.criteria_output)}")
    if a.charts:
        from .viz import save_figure

        for n, r in enumerate(rs, 1):
            for mode in (None, *rp.slope_modes(r)):
                path = Path(a.charts) / f"estereograma_{n}_{mode or 'density'}.png"
                print(f"chart: {save_figure(rp.slope_figure(r, mode, a.lang, proj), path)}")
        for r in bs:
            if r.probabilistic is not None:
                for kind in ("hist", "cdf"):
                    path = Path(a.charts) / f"fs_{kind}_{r.order}.png"
                    print(f"chart: {save_figure(rp.block_figure(r, kind, a.lang), path)}")
    if a.report:
        rep = rp.build_slope_report(rs, title=a.title or t("slope_title", a.lang), lang=a.lang, author=a.author or "",
                                    figures=not a.no_figures, projection=proj, blocks=bs, criteria=checks,
                                    criteria_profile=prof, range_policy=a.range_policy)
        out = rp.write_docx(rep, a.report, author=a.author or "") if ext == ".docx" else rp.write_html(rep, a.report)
        print(f"report: {out}")
    print("the library recommends, the engineer decides")
    # una sola regla: needs_attention del talud (3A), block_attention del bloque (R14) y un «no cumple» (R10)
    return 2 if any(r.needs_attention for r in rs) or any(bk.block_attention(r) for r in bs) or crit_fails else 0


def _analyses(n: int) -> str:
    return f"{n} analys" + ("is" if n == 1 else "es")


_LE_CSV = (("geometry", "--geometry", "Geometria"), ("layers", "--layers", "Estratos"),
           ("materials", "--materials", "Materiales_LE"), ("analyses", "--analyses", "Analisis_LE"))


def _le_source(a, workbook_flag="--workbook"):
    """--workbook (en `verify`, --le) o los CSV por hoja; todo se valida antes de leer archivos."""
    given = [flag for attr, flag, _ in _LE_CSV if getattr(a, attr)]
    if a.workbook:
        if given or a.records:
            raise ValueError(f"{workbook_flag} goes alone; drop {(given or ['--records'])[0]}")
        return a.workbook
    if len(given) != len(_LE_CSV):
        missing = [flag for attr, flag, _ in _LE_CSV if not getattr(a, attr)]
        raise ValueError(f"give {workbook_flag}, or --geometry, --layers, --materials and --analyses "
                         f"(missing {missing[0]})")
    src = {sheet: getattr(a, attr) for attr, _, sheet in _LE_CSV}
    if a.records:
        src["Sismos"] = a.records
    return src


def _le(a) -> int:
    from . import limit_equilibrium as le
    from . import report as rp

    ext = Path(a.report).suffix.lower() if a.report else ""
    if a.report and ext not in (".docx", ".html"):
        raise ValueError("report must end in .docx or .html")
    if a.output and Path(a.output).suffix.lower() not in (".csv", ".xlsx"):
        raise ValueError("--output must end in .csv or .xlsx")
    prof, norm = _criteria_args(a)

    def progress(k, n):  # avance en stderr, sin ids; stdout queda para el resumen
        if n > 1:
            print(f"analysis {k} of {n}...", file=sys.stderr, flush=True)

    rs = le.assess_le(_le_source(a), progress=progress)  # antes del primer print: un error deja stdout vacío
    if not rs:
        raise ValueError("no analyses in Analisis_LE")
    checks, pchecks = _assess_criteria(a, prof, norm, le=rs)
    c = le.le_counts(rs)
    sarma = f", sarma {c['sarma']}" if "sarma" in c else ""  # como le_counts: solo si hay alguno
    print(f"analyses: {c['analyses']} (circular {c['circular']}, block {c['block']}, given {c['given']}{sarma})")
    print(f"FS at or below 1: {c['fs_below_1']} of {c['with_fs']}")
    fs = [(x.factor_of_safety, x.info.method_id) for r in rs for x in r.results]
    fs += [(r.sarma.factor_of_safety, r.sarma.info.method_id) for r in rs if r.sarma is not None]
    low = min(((v, m) for v, m in fs if v is not None), default=None)
    print("lowest FS: none" if low is None else f"lowest FS: {low[0]:.3f} ({low[1]})")
    print(f"Newmark: {_analyses(c['with_newmark'])}")
    print(f"warnings: {c['warnings']} in {_analyses(sum(1 for r in rs if r.warnings))}")
    for w, n in sorted(le.le_warning_counts(rs).items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"warning: {w} ({_analyses(n)})")
    print(f"notes: {c['notes']}")
    crit_fails = _print_criteria(prof, norm, checks, pchecks)
    if a.output:
        print(f"results: {le.save_le_results(rs, a.output)}")
    if a.criteria_output:
        from .criteria import save_criteria_results

        print(f"criteria results: {save_criteria_results(checks, a.criteria_output)}")
    if a.charts:
        from .viz import save_figure

        for r in rs:  # nombres por número de orden: nunca un id
            print(f"chart: {save_figure(rp.le_figure(r, a.lang), Path(a.charts) / f'seccion_le_{r.order}.png')}")
            if r.newmark is not None and r.record is not None:
                print(f"chart: {save_figure(rp.newmark_figure(r, a.lang), Path(a.charts) / f'newmark_{r.order}.png')}")
    if a.report:
        rep = rp.build_slope_report([], title=a.title or t(rp.slope_title_key(False), a.lang), lang=a.lang,
                                    author=a.author or "", figures=not a.no_figures, le=rs, criteria=checks,
                                    criteria_profile=prof, range_policy=a.range_policy, profile_checks=pchecks)
        out = rp.write_docx(rep, a.report, author=a.author or "") if ext == ".docx" else rp.write_html(rep, a.report)
        print(f"report: {out}")
    print("the library recommends, the engineer decides")
    return 2 if any(le.le_attention(r) for r in rs) or crit_fails else 0  # una sola regla (R14) y R10


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


def _fit_correlations(history, group_by, deming_ratio) -> list:
    """Los tres pares; uno que no se puede ajustar queda como (tipo, razón) y no detiene a los otros."""
    from .predictive import KINDS, fit_site_correlation  # sin numpy/scipy: ImportError con el texto del extra [ml]

    out = []
    for kind in KINDS:
        try:
            out.append(fit_site_correlation(history, kind, group_by=group_by, deming_ratio=deming_ratio))
        except ValueError as e:  # sin pares, ediciones mezcladas…: el mensaje trae conteos y filas, nunca ids
            out.append((kind, str(e)))
    return out


def _decision_note(partition: str, c) -> str:
    """Cómo pesa la partición en la decisión (ValidationReport.recommend): labor y zona por superioridad (con sus
    motivos genéricos: nombres de modelo y conteos), la temporal por no inferioridad, la aleatoria no cuenta."""

    if partition == "temporal":
        return "non-inferiority " + ("met" if c.noninferior else "not met")
    if partition == "random":
        return "optimistic, does not count"
    return f"blockers {len(c.blockers)}" + (f" ({'; '.join(c.blockers)})" if c.blockers else "")


def _print_validation(level: str, metric: str, report, fmt: str) -> None:
    """Una línea por partición: métricas, mejora con IC y los motivos para no recomendar (sin etiquetas)."""
    from .report import gain_text

    for p, c in report.results.items():
        refs = list(c.improvements)
        ms = ", ".join(f"{m} {c.metrics[m]:{fmt}}" for m in (c.main, *refs))
        gains = ", ".join(f"over {r} {gain_text(c.improvements[r], fmt)}" for r in refs)
        print(f"{level} {metric} {p}: {ms}; gain {gains}; {_decision_note(p, c)}")
    for p, why in report.skipped.items():
        print(f"{level} {metric} {p}: skipped ({why})")
    for w in report.warnings:
        print(f"{level} validation warning: {w}")


def _print_practice(a) -> bool:
    """Líneas del nivel 2; True si hay que revisar (práctica incoherente, no significativa, poco consistente o datos
    insuficientes)."""
    from .predictive.practice import MAX_PRACTICE_INCONSISTENCY

    ref = a.design.labor_levels[0] if a.design.labor_levels else None  # los tipo_labor=… son contrastes contra él
    print(f"practice: n {a.n}, labors {a.labors}, types {', '.join(a.types)}, {a.status}"
          + ("" if ref is None else f", reference tipo_labor {ref}"))
    for name, v in a.verdicts.items():
        c = a.coefficients.get(name)
        coef = "" if c is None else f" (beta {c.value:.3f}, 95% CI {c.ci_low:.3f}; {c.ci_high:.3f})"
        print(f"practice {name}: {v}{coef}")
    print(f"practice consistency: {a.consistency_verdict} (share of tramos given another type at the centre of a "
          f"type's range {a.consistency:.3f}, design threshold {MAX_PRACTICE_INCONSISTENCY:g})")
    _print_validation("practice", "kappa", a.validation, ".3f")
    print(f"practice beyond the Q chart: {'yes' if a.beyond_chart else 'no'} (describes the practice, "
          "it does not recommend)")
    n_sets = sum(x.conformal_set is not None for x in a.tramos)
    print(f"practice outside the conformal set: {len(a.outside_set)} of {n_sets} tramos "
          f"(level {a.conformal_level:g}; about 1 - level fall outside by construction, it is not a deviation)")
    cc = a.concordance
    print("practice concordance: none" if cc is None else
          f"practice concordance: n {cc.n}, kappa {'-' if cc.kappa is None else f'{cc.kappa:.3f}'}")
    for w in a.warnings:
        if w not in a.validation.warnings:  # ya salieron como «validation warning»
            print(f"practice warning: {w}")
    return (a.status != "ready" or any(v != "coherent" for v in a.verdicts.values())
            or a.consistency_verdict != "consistent")


def _print_performance_gates(m) -> None:
    """Forma, σ_z y las compuertas (a) y (d) del nivel 3: solo conteos y valores agregados."""
    from .history import MIN_EVENTS_PER_PARAMETER_LEVEL3
    from .predictive.performance import POOR_ROCK_MAX_OE, POOR_ROCK_MIN_EVENTS

    dev = {f: m.metrics[f"oof_deviance_{f}"] for f in ("additive", "interaction") if f"oof_deviance_{f}" in m.metrics}
    extra = (f" (out-of-fold deviance {', '.join(f'{f} {v:.4f}' for f, v in dev.items())})" if len(dev) > 1 else "")
    if m.metrics.get("interaction_at_bound"):
        extra += "; the interaction was at its bound in the final fit, so the additive form is kept"
    print(f"performance form: {m.form}{extra}")
    if m.form == "interaction":
        q_ref, k_ref = m.interaction_ref
        print(f"performance interaction column: ({m.features[0]} - {q_ref:.4g}) * (support_rank - {k_ref:g}), "
              "the training maxima, so it is >= 0 in the training domain")
    if m.fit is not None:
        print(f"performance new zone: sigma_z estimate {m.zone_sd:.3f}, one-sided upper bound used "
              f"{m.zone_sd_upper(0.9):.3f} at level 0.9 ({m.fit.n_clusters} zones)")
    if m.poor_rock is None:
        print("performance worst third of rock quality: not checked (no out-of-fold predictions)")
    else:
        cut, obs, exp = m.poor_rock
        oe = f"{obs / exp:.2f}" if exp > 0 else "-"
        print(f"performance worst third of rock quality ({m.features[0]} <= {cut:.4g}): out-of-fold observed/expected "
              f"{obs}/{exp:.1f} = {oe} (gate: at most {POOR_ROCK_MAX_OE:g} with at least {POOR_ROCK_MIN_EVENTS} "
              f"failures): {'passes' if m.poor_rock_problem is None else 'no choice there'}")
    if m.labor_types:
        print("performance failures by tipo_labor: " + ", ".join(
            f"{lt} {n}" for lt, n in zip(m.labor_types, m.labor_type_failures))
            + f" (no choice with fewer than {MIN_EVENTS_PER_PARAMETER_LEVEL3})")


def _print_performance(m) -> bool:
    """Líneas del nivel 3; True si el modelo no quedó «site» o si recommend nunca elegiría con él."""
    from .report import recommendation_blockers

    c = m.counts
    rb = recommendation_blockers(m)
    if m.calibration == "site" and rb:
        print(f"performance: calibration site, but recommend will not choose: {'; '.join(rb)}")
    else:
        print(f"performance: calibration {m.calibration} ({m.calibration_reason})")
    print(f"performance: n {c['tramos']}, failures {c['failures']}, labors {c['labors']}, zones {c['zones']}, "
          f"parameters {c['parameters']}, quality {m.quality}")
    print("performance model: constant failure rate with a gamma frailty per excavation; P(failure in H days) "
          "for a new excavation = 1 - (1 + theta*lambda*H)^(-1/theta); the decision bound is "
          "1 - exp(-lambda_up*H*Z_q), with lambda_up = exp(eta + q*sqrt(se^2 + sigma_z_up^2)) for a new zone and "
          "Z_q the frailty quantile at the upper theta")
    _print_performance_gates(m)
    if m.validation is not None:
        _print_validation("performance", "poisson_deviance", m.validation, ".4f")
    coefs = m.coefficients  # {} sin ajuste
    for name, (lo, hi) in zip(coefs, m.coef_ci):
        bound = " (sign bound active)" if name in m.active_bounds else ""
        print(f"performance coefficient {name}: {coefs[name]:.4g} (95% CI {lo:.4g}; {hi:.4g}){bound}")
    shown = m.validation.warnings if m.validation is not None else ()
    for w in m.warnings:
        if w not in shown:
            print(f"performance warning: {w}")
    return m.calibration != "site" or bool(rb)


def _history(a) -> int:
    from collections import Counter

    from . import report as rp
    from .history import (FINDING_KINDS, audit_history, check_group_by, history_audit_counts, load_history,
                          save_history_findings)

    ext = Path(a.report).suffix.lower() if a.report else ""
    if a.report and ext not in (".docx", ".html"):
        raise ValueError("report must end in .docx or .html")
    # las salidas se validan antes de leer y ajustar; los mensajes no llevan la ruta (puede nombrar la mina)
    if a.report and not Path(a.report).resolve().parent.is_dir():
        raise ValueError("--report: its folder does not exist")
    if a.output and Path(a.output).is_file():
        raise ValueError("--output must be a folder, not a file")
    level3_only = [f for f, v in (("--quality", a.quality), ("--model-output", a.model_output),
                                  ("--threshold", a.threshold), ("--exposure-days", a.exposure_days)) if v is not None]
    if not a.performance and level3_only:
        raise ValueError(f"{level3_only[0]} needs --performance")
    if a.performance:
        from .predictive.performance import QUALITIES  # sin el extra [ml]: ImportError con su texto, antes de leer

        if a.quality is not None and a.quality not in QUALITIES:
            raise ValueError(f"--quality must be one of {', '.join(QUALITIES)}")
    if a.threshold is not None and not 0 < a.threshold < 1:
        raise ValueError("--threshold must be a probability strictly between 0 and 1")
    if a.exposure_days is not None and not a.exposure_days > 0:
        raise ValueError("--exposure-days must be greater than 0")
    if a.model_output and Path(a.model_output).suffix.lower() != ".json":
        raise ValueError("--model-output must end in .json")
    if a.model_output and not Path(a.model_output).resolve().parent.is_dir():
        raise ValueError("--model-output: its folder does not exist")
    group_by = None if a.group_by.lower() == "none" else a.group_by
    try:
        check_group_by(group_by)
    except ValueError:
        raise ValueError("--group-by must be none or a column of sheet Tramos") from None
    if not a.correlations and a.deming_ratio is not None:
        raise ValueError("--deming-ratio needs --correlations")
    if a.deming_ratio is not None and not a.deming_ratio > 0:
        raise ValueError("--deming-ratio must be greater than 0")
    history = load_history(a.history)
    audit = audit_history(history)
    fits = _fit_correlations(history, group_by, a.deming_ratio) if a.correlations else None  # antes del 1.er print
    practice = performance = None
    if a.practice:
        from . import predictive  # el atributo del paquete: las pruebas cambian n_boot ahí

        practice = predictive.audit_practice(history)
    if a.performance:
        from . import predictive

        performance = predictive.fit_performance(history, quality=a.quality or "q")
    c = history_audit_counts(audit)
    print(f"tramos: {c['tramos']}\nsupport types: {c['support_types']}\ninspections: {c['inspections']}")
    print(f"findings: {c['findings']}")
    for k in sorted((k for k in FINDING_KINDS if c[k]), key=lambda k: (-c[k], k)):
        print(f"finding: {k} ({c[k]})")
    for r in audit.readiness:
        have = ", ".join(f"{k} {r.counts.get(k, 0)} of {m}" for k, m in r.minimums.items())
        print(f"level {r.level} {r.item}: {'ready' if r.ready else 'not ready'} ({have})")
    not_site = False
    warns = Counter()
    for r in fits or ():
        if isinstance(r, tuple):
            print(f"correlation {r[0]}: not fitted ({r[1]})")
            not_site = True
            continue
        print(f"prior {r.kind}: {r.prior_correlation} [{r.prior_verification}]")
        for f in rp.site_fits(r):  # la etiqueta (D1, D2…), nunca el dominio: puede ser la litología
            print(f"correlation {r.kind} {f.label}: n {f.n}, labors {f.n_labors}, {f.status}, a {f.a:.4g}, "
                  f"b {f.b:.4g}")
            not_site |= f.status != "site"
            warns.update({*r.warnings, *f.warnings})
    for w, n in sorted(warns.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"warning: {w} ({n} fit{'' if n == 1 else 's'})")
    review = (practice is not None and _print_practice(practice)) | \
        (performance is not None and _print_performance(performance))
    try:  # en Excel o sin permiso: el OSError de Python trae la ruta completa
        if a.output:  # solo el nombre: la carpeta protegida puede llevar el nombre de la mina
            out = Path(a.output)
            out.mkdir(parents=True, exist_ok=True)
            paths = [save_history_findings(audit, out / "history_findings.csv")]
            if fits is not None:
                from .predictive import save_site_correlations

                paths += save_site_correlations(fits, out)
            if practice is not None:
                from .predictive import save_practice_results

                paths.append(save_practice_results(practice, out / "practice_results.csv"))
            reports = {lv: x.validation for lv, x in (("2", practice), ("3", performance))
                       if x is not None and x.validation is not None}
            if reports:
                from .predictive.validation import save_validation_summary

                paths.append(save_validation_summary(reports, out / "validation_summary.csv"))
            for p in paths:
                print(f"results: {p.name}")
        if a.model_output:
            from .predictive import save_model

            print(f"model: {save_model(performance, a.model_output).name}")
        if a.report:
            rep = rp.build_history_report(audit, fits or (), history=history, practice=practice,
                                          performance=performance, threshold=a.threshold,
                                          exposure_days=a.exposure_days, lang=a.lang)
            out = rp.write_docx(rep, a.report) if ext == ".docx" else rp.write_html(rep, a.report)
            print(f"report: {Path(out).name}")
    except OSError:
        raise OSError("results or report could not be written (in use or no permission)") from None
    print("the library recommends, the engineer decides")
    return 2 if audit.findings or not_site or review else 0


class _PositionedPractice:
    """El nivel 2 para `recommend`: un tramo que el modelo de práctica no puede evaluar falla con SU posición
    (practice.conformal_set recibe un solo tramo y diría siempre «position 0»)."""

    def __init__(self, audit):
        self.audit, self.i = audit, 0

    def conformal_set(self, tramo):
        i, self.i = self.i, self.i + 1
        try:
            return self.audit.conformal_set(tramo)
        except ValueError as e:
            raise ValueError(f"tramo at position {i + 1}: practice model: "
                             f"{re.sub(r'^tramo( at position \d+)?: ', '', str(e))}") from None


def _new_tramos(path):
    """Tramos nuevos: un .xlsx o una carpeta con la plantilla del histórico (solo la hoja Tramos es obligatoria), o
    un .csv que es la hoja Tramos. Los errores no llevan la ruta."""
    from .history import load_history

    p = Path(path)
    if p.suffix.lower() != ".csv":
        return load_history(p).tramos
    from .csv_io import _CsvSource
    from .history import _read_tramos

    if not p.is_file():
        raise FileNotFoundError("tramos file not found")
    try:
        return _read_tramos(_CsvSource({"Tramos": p}), None)
    except OSError:
        raise OSError("tramos file could not be read (in use or no permission)") from None


def _recommend(a) -> int:
    if not 0 < a.threshold < 1:  # antes de leer: el umbral lo fija el ingeniero y no tiene valor por defecto
        raise ValueError("--threshold must be a probability strictly between 0 and 1")
    if not a.exposure_days > 0:
        raise ValueError("--exposure-days must be greater than 0")
    if a.output and Path(a.output).suffix.lower() not in (".csv", ".xlsx"):
        raise ValueError("--output must end in .csv or .xlsx")
    if a.output and not Path(a.output).resolve().parent.is_dir():
        raise ValueError("--output: its folder does not exist")
    from . import predictive

    try:
        model = predictive.load_model(a.model)
    except OSError:  # el OSError de Python trae la ruta completa
        raise OSError("model file could not be read (missing, in use or no permission)") from None
    except (KeyError, TypeError, AttributeError):
        raise ValueError("model file is not a valid performance model") from None
    tramos = _new_tramos(a.tramos)
    if not tramos:
        raise ValueError("no tramos in the input")
    practice = None
    if a.practice_from:
        from .history import load_history

        h = load_history(a.practice_from)
        # otros códigos de tipo: el conjunto conforme hablaría de tipos que el modelo no conoce (decisión: error)
        if {s.codigo_tipo for s in h.support_types} != {code for code, _ in model.support_types}:
            raise ValueError("--practice-from: its support type codes do not match the model's")
        practice = _PositionedPractice(predictive.audit_practice(h))
    recs = predictive.recommend(model, tramos, threshold=a.threshold, exposure_days=a.exposure_days,
                                practice=practice)
    print(f"model: calibration {model.calibration}, threshold {a.threshold:g}, exposure {a.exposure_days:g} days, "
          f"interval {recs[0].level:g}")
    print(f"tramos: {len(recs)}")
    for i, r in enumerate(recs, 1):  # la posición, nunca el id_tramo (va solo en el archivo)
        what = r.chosen if r.chosen else f"no recommendation: {r.reason}"
        alerts = "; ".join(r.extrapolation_notes) or "none"
        cset = "" if r.conformal_set is None else f"; practice set {', '.join(r.conformal_set) or 'none'}"
        print(f"tramo {i}: {what}; alerts: {alerts}; calibration {r.calibration}{cset}")
    n_chosen = sum(r.chosen is not None for r in recs)
    n_alert = sum(r.extrapolation for r in recs)
    print(f"recommended: {n_chosen} of {len(recs)}; with alerts: {n_alert}")
    if a.output:
        try:
            print(f"results: {predictive.save_recommendations(recs, a.output).name}")
        except OSError:
            raise OSError("results could not be written (in use or no permission)") from None
    print("the library recommends, the engineer decides")
    return 2 if n_chosen < len(recs) or n_alert else 0


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
    _le_inputs(c, "--le")
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
    c.add_argument("--blocks", metavar="BLOQUES", help="planar, wedge, toppling and berm blocks (sheet Bloques)")
    c.add_argument("--sheet-blocks", default="Bloques")
    c.add_argument("--distributions", metavar="DIST", help="random variables per block (needs --blocks)")
    c.add_argument("--sheet-distributions", default="Distribuciones")
    c.add_argument("--iterations", type=int, metavar="N", help="samples per probabilistic block (default 5000)")
    c.add_argument("--sampling", choices=("lhs", "monte-carlo"), help="default lhs")
    c.add_argument("--seed", type=int, help="default 1")
    c.add_argument("--blocks-output", metavar="RES.csv|.xlsx")
    _criteria_inputs(c)
    c.set_defaults(fn=_slope)
    c = sub.add_parser("le", help="2D limit equilibrium, critical slip surface, ky and Newmark")
    _le_inputs(c, "--workbook")
    c.add_argument("-o", "--output", metavar="RES.csv|.xlsx")
    c.add_argument("--report", metavar="OUT.docx|.html")
    c.add_argument("--charts", metavar="DIR")
    c.add_argument("--title")
    c.add_argument("--author")
    c.add_argument("--lang", choices=("es", "en"), default="es")
    c.add_argument("--no-figures", action="store_true")
    _criteria_inputs(c)
    c.add_argument("--profile", metavar="PE-DS024-2016", help="regulatory profile for art. 264 (pseudo-static "
                   "analysis of the overall slope)")
    c.set_defaults(fn=_le)
    c = sub.add_parser("history", help="audit the mine's geomechanical history and fit site correlations (level 1)")
    c.add_argument("history", metavar="HISTORICO.xlsx|CARPETA", help="the history template (.xlsx) or a folder of "
                   "Tramos.csv, Tipos_sostenimiento.csv and Desempeno.csv")
    c.add_argument("--correlations", action="store_true", help="fit RMR-Q, GSI-RMR and GSI-Q' (needs the ml extra)")
    c.add_argument("--group-by", default="litologia", metavar="COL", help="domain column (default litologia; "
                   "none = whole mine only)")
    c.add_argument("--deming-ratio", type=float, metavar="R", help="error-variance ratio for the Deming line")
    c.add_argument("--practice", action="store_true", help="level 2: audit the support practice (describes, "
                   "never recommends; needs the ml extra)")
    c.add_argument("--performance", action="store_true", help="level 3: fit and validate the P(failure) model "
                   "(needs the ml extra)")
    # las opciones salen de performance.QUALITIES al correr: el parser no importa numpy
    c.add_argument("--quality", metavar="q|rmr", help="rock quality of the level 3 model (default q; needs "
                   "--performance)")
    c.add_argument("--model-output", metavar="MODELO.json", help="save the level 3 model (no rows, no ids)")
    c.add_argument("--threshold", type=float, metavar="P", help="P(failure) threshold set by the engineer, quoted in "
                   "the report (needs --performance; no default)")
    c.add_argument("--exposure-days", type=float, metavar="D", help="horizon of the report's isoprobability "
                   "charts (needs --performance; default: the history's median exposure)")
    c.add_argument("-o", "--output", metavar="DIR", help="folder for history_findings.csv, site_correlations.csv, "
                   "site_correlations.json, practice_results.csv and validation_summary.csv")
    c.add_argument("--report", metavar="OUT.docx|.html")
    c.add_argument("--lang", choices=("es", "en"), default="es")
    c.set_defaults(fn=_history)
    c = sub.add_parser("recommend", help="level 3: P(failure) of every support type and the lightest one under the "
                       "engineer's threshold")
    c.add_argument("tramos", metavar="TRAMOS.xlsx|.csv|CARPETA", help="new tramos with the columns of sheet Tramos")
    c.add_argument("--model", required=True, metavar="MODELO.json", help="model saved by history --model-output")
    c.add_argument("--threshold", type=float, required=True, metavar="P", help="acceptable P(failure), set by the "
                   "engineer (no default)")
    c.add_argument("--exposure-days", type=float, required=True, metavar="D", help="exposure horizon in days, "
                   "set by the engineer (no default)")
    c.add_argument("--practice-from", metavar="HISTORICO.xlsx", help="history for the level 2 conformal set")
    c.add_argument("-o", "--output", metavar="RECOMENDACIONES.csv|.xlsx", help="one row per tramo and type, with "
                   "the id_tramo and the empty columns decision_ingeniero and motivo")
    c.set_defaults(fn=_recommend)
    return p


def _criteria_inputs(c) -> None:
    """Criterios de aceptación (3D): los mismos en `slope` (sobre los bloques) y en `le`."""
    c.add_argument("--criteria", metavar="ID|CRITERIOS.csv|.xlsx", help="acceptance criteria: a profile id "
                   "(READ-STACEY-2009, NDEP-2021, DMIRS-WA-2019, RYAN-PRYOR-2000) or your own table (sheet Criterios)")
    c.add_argument("--criteria-output", metavar="RES.csv|.xlsx", help="one row per criterion check (needs --criteria)")
    c.add_argument("--range-policy", choices=("conservative", "upper", "lower"),
                   help="value used inside a criterion range (default: the profile's; needs --criteria)")


def _le_inputs(c, workbook_flag: str) -> None:
    """Entradas de equilibrio límite: las mismas en `le` (--workbook) y en `verify` (--le, para el art. 264)."""
    c.add_argument(workbook_flag, dest="workbook", metavar="LIBRO.xlsx", help="workbook with the sheets Geometria, "
                   "Estratos, Materiales_LE, Analisis_LE and Sismos")
    c.add_argument("--geometry", metavar="GEOMETRIA.csv")
    c.add_argument("--layers", metavar="ESTRATOS.csv")
    c.add_argument("--materials", metavar="MATERIALES.csv")
    c.add_argument("--analyses", metavar="ANALISIS.csv")
    c.add_argument("--records", metavar="SISMOS.csv", help="acceleration records for Newmark (with the CSV files)")


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
