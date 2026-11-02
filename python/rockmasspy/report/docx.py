"""Salida Word (.docx) de un Report. Necesita python-docx (extra [report]); se importa al llamar."""

from __future__ import annotations

import io
from pathlib import Path

from ..table_io import _optional
from .texts import t

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_LANG = {"es": "es-PE", "en": "en-US"}


def _set_lang(rpr, tag) -> None:
    for old in rpr.findall(_W + "lang"):
        rpr.remove(old)
    el = rpr.makeelement(_W + "lang", {_W + "val": tag})
    rpr.append(el)


def _set_languages(doc, lang) -> None:
    tag = _LANG.get(lang, lang)
    defaults = doc.styles.element.find(_W + "docDefaults")
    if defaults is not None:
        rpr_default = defaults.find(_W + "rPrDefault")
        if rpr_default is not None:
            rpr = rpr_default.find(_W + "rPr")
            if rpr is None:
                rpr = rpr_default.makeelement(_W + "rPr", {})
                rpr_default.append(rpr)
            _set_lang(rpr, tag)
    _set_lang(doc.styles["Normal"].element.get_or_add_rPr(), tag)


def _box(paragraph) -> None:
    """Recuadro alrededor del descargo en la portada."""
    ppr = paragraph._p.get_or_add_pPr()
    bdr = ppr.makeelement(_W + "pBdr", {})
    for side in ("top", "left", "bottom", "right"):
        bdr.append(bdr.makeelement(_W + side, {_W + "val": "single", _W + "sz": "12", _W + "space": "4",
                                               _W + "color": "444444"}))
    ppr.append(bdr)


def _table(doc, b) -> None:
    doc.add_paragraph(b.caption, style="Caption")
    tab = doc.add_table(rows=1, cols=len(b.header), style="Table Grid")
    for cell, h in zip(tab.rows[0].cells, b.header):
        cell.paragraphs[0].add_run(h).bold = True
    for row in b.rows:
        for cell, v in zip(tab.add_row().cells, row):
            cell.text = v


def _figure(doc, b, width) -> None:
    if b.png:
        doc.add_picture(io.BytesIO(b.png), width=width)
    if b.note:
        doc.add_paragraph(b.note)
    doc.add_paragraph(b.caption, style="Caption")


def _section(doc, s, lang, depth, ctx) -> None:
    doc.add_heading(f"{s.number}. {s.title}", level=min(depth, 9))
    if s.to_complete:
        run = doc.add_paragraph().add_run(t("to_complete", lang))
        run.font.highlight_color = ctx["yellow"]
    for b in s.blocks:
        kind = type(b).__name__
        if kind == "Paragraph":
            doc.add_paragraph(b.text)
        elif kind == "Table":
            _table(doc, b)
        elif kind == "Figure":
            _figure(doc, b, ctx["width"])
        else:
            _section(doc, b, lang, depth + 1, ctx)


def write_docx(report, path, *, author: str = "") -> Path:
    """Escribe el informe en Word. `author` queda vacío por defecto: nunca se usa el usuario del sistema."""
    docx = _optional("docx", "report")
    ctx = {"yellow": _optional("docx.enum.text", "report").WD_COLOR_INDEX.YELLOW,
           "width": _optional("docx.shared", "report").Cm(15)}
    lang = report.lang
    doc = docx.Document()
    _set_languages(doc, lang)
    cp = doc.core_properties
    cp.title, cp.author, cp.last_modified_by = report.title, author, author
    doc.add_paragraph(report.title, style="Title")
    if report.subtitle:
        doc.add_paragraph(report.subtitle, style="Subtitle")
    box = doc.add_paragraph()
    box.add_run(report.disclaimer).bold = True
    _box(box)
    for s in report.sections:
        _section(doc, s, lang, 1, ctx)
    footer = doc.sections[0].footer
    footer.paragraphs[0].text = report.disclaimer
    footer.add_paragraph(f"{t('version', lang)} {report.version} · {t('date', lang)} {report.date}")
    p = Path(path)
    doc.save(str(p))
    return p
