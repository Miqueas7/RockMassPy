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

from .batch import add_q_chart_reference, classify_tramos, q_chart_crosstab, save_results, summarize
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
        cat, colon, num = spec.partition(":")
        if (eq and not labor) or not cat or (colon and not num):
            raise ValueError(f"invalid --esr {v!r}: {syntax}")
        try:
            out[labor if eq else "*"] = (cat, float(num)) if colon else cat
        except ValueError:
            raise ValueError(f"invalid --esr {v!r}: {syntax}") from None
    return out


def _classify_all(a):
    tables = [load_table(p) for p in a.tables]
    tramos = load_tramos(a.tramos, sheet=a.sheet, column_map=_column_map(a.column_map))
    esr = _esr_specs(a.esr) if a.esr else None  # antes de clasificar: un --esr malo falla temprano
    results = classify_tramos(tramos, tables)
    if esr:
        try:
            results = add_q_chart_reference(results, esr, edition=a.q_edition)
        except ValueError as e:  # la biblioteca habla de tuplas de Python; la CLI, de A:<esr>
            raise ValueError(re.sub(r"ESR category (\w) covers ([\d.]+)-([\d.]+); pass \(category, esr\)",
                                    lambda m: f"ESR category {m[1]} covers {m[2]}-{m[3]}; use {m[1]}:<esr>, "
                                              f"e.g. {m[1]}:{(float(m[2]) + float(m[3])) / 2:g}", str(e))) from None
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
