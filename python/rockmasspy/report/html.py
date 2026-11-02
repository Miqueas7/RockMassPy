"""Salida HTML de un Report: un solo archivo UTF-8, CSS mínimo incluido, figuras en base64. Solo biblioteca estándar."""

from __future__ import annotations

import base64
from html import escape
from pathlib import Path

from .texts import t

_CSS = """body{font-family:Arial,Helvetica,sans-serif;max-width:960px;margin:2em auto;padding:0 1em;color:#222}
table{border-collapse:collapse;width:100%;margin:.5em 0;font-size:.85em}
th,td{border:1px solid #999;padding:3px 6px;text-align:left;vertical-align:top}th{background:#eee}
caption{text-align:left;font-weight:bold;padding:4px 0}
figure{margin:1em 0}img{max-width:100%}figcaption,.note{font-size:.85em;color:#555}
.disclaimer{border:2px solid #444;padding:.6em 1em;margin:1em 0;font-weight:bold}
.todo{background:#fff3cd;padding:2px 6px}footer{margin-top:2em;border-top:1px solid #999;padding-top:.5em;font-size:.85em}
@media print{body{margin:0;max-width:none}section{page-break-inside:avoid}footer{position:fixed;bottom:0}}"""


def _block(b, lang, level) -> str:
    kind = type(b).__name__
    if kind == "Paragraph":
        return f"<p>{escape(b.text)}</p>"
    if kind == "Table":
        head = "".join(f"<th>{escape(h)}</th>" for h in b.header)
        body = "".join("<tr>" + "".join(f"<td>{escape(c)}</td>" for c in row) + "</tr>" for row in b.rows)
        return f"<table><caption>{escape(b.caption)}</caption><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
    if kind == "Figure":
        img = (f'<img src="data:image/png;base64,{base64.b64encode(b.png).decode()}" alt="{escape(b.caption)}">'
               if b.png else "")
        note = f'<p class="note">{escape(b.note)}</p>' if b.note else ""
        return f"<figure>{img}{note}<figcaption>{escape(b.caption)}</figcaption></figure>"
    return _section(b, lang, level)


def _section(s, lang, level=2) -> str:
    h = min(level, 6)
    mark = f' <span class="todo">{escape(t("to_complete", lang))}</span>' if s.to_complete else ""
    num = escape(s.number) + ". " if s.number else ""  # la memoria resumen va sin número
    inner = "".join(_block(b, lang, level + 1) for b in s.blocks)
    return f"<section><h{h}>{num}{escape(s.title)}{mark}</h{h}>{inner}</section>"


def write_html(report, path) -> Path:
    lang = report.lang
    disc = f'<p class="disclaimer">{escape(report.disclaimer)}</p>'
    sub = f"<p>{escape(report.subtitle)}</p>" if report.subtitle else ""
    foot = (f"<footer><p>{escape(report.disclaimer)}</p><p>{escape(t('version', lang))} {escape(report.version)}"
            f" · {escape(t('date', lang))} {escape(report.date)}</p></footer>")
    doc = (f'<!DOCTYPE html><html lang="{escape(lang)}"><head><meta charset="utf-8">'
           f"<title>{escape(report.title)}</title><style>{_CSS}</style></head><body>"
           f"<h1>{escape(report.title)}</h1>{sub}{disc}"
           + "".join(_section(s, lang) for s in report.sections) + foot + "</body></html>")
    p = Path(path)
    p.write_text(doc, encoding="utf-8")
    return p
