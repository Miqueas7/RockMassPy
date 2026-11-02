"""Línea de comandos `rockmass`: solo presenta lo que la librería calcula.

Nunca imprime filas de tramos: solo conteos, nombres de archivo y avisos de las tablas de diseño.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .batch import classify_tramos, save_results, summarize
from .table_files import load_table
from .tramos import load_tramos

_INPUT_ERRORS = (ValueError, ImportError, FileNotFoundError)


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


def _classify_all(a):
    tables = [load_table(p) for p in a.tables]
    tramos = load_tramos(a.tramos, sheet=a.sheet, column_map=_column_map(a.column_map))
    return classify_tramos(tramos, tables), tables


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
    title = a.title or "RockMassPy report"
    kw = dict(title=title, lang=a.lang, author=a.author or "", figures=not a.no_figures)
    if a.template == "anexo39b":
        rep = rp.build_anexo39b(results, tables, labor_type=a.labor, **kw)
    else:
        rep = rp.build_memoria(results, tables, **kw)
    out = rp.write_docx(rep, a.output, author=a.author or "") if ext == ".docx" else rp.write_html(rep, a.output)
    code = _print_summary(summarize(results))
    print(f"report: {out}")
    return code


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="rockmass", description="RockMassPy command line.")
    p.add_argument("--debug", action="store_true", help="show the traceback on errors")
    sub = p.add_subparsers(dest="cmd")

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
    return p


def main(argv: Sequence[str] | None = None) -> int:
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
