import subprocess
import sys

import pytest

import rockmasspy.report as rp

from test_report_html import build


def test_without_docx_in_fresh_interpreter():
    code = ("import sys; sys.modules['docx'] = None; import rockmasspy.report as rp\n"
            "print('html' if rp.write_html else '')\n"
            "try:\n    rp.write_docx(None, 'x.docx')\nexcept ImportError as e:\n    print(e)")
    r = subprocess.run([sys.executable, "-I", "-c", code], check=True, capture_output=True, text=True)
    assert "html" in r.stdout and "rockmasspy[report]" in r.stdout


docx = pytest.importorskip("docx")


def _open(tmp_path, report=None, **kw):
    p = rp.write_docx(report or build(), tmp_path / "m.docx", **kw)
    return docx.Document(str(p))


def test_headings_tables_images_footer(tmp_path):
    r = build()
    d = _open(tmp_path, r)
    h1 = [p.text for p in d.paragraphs if p.style.name == "Heading 1"]
    assert h1 == [f"{s.number}. {s.title}" for s in r.sections]
    assert any(p.style.name == "Heading 2" for p in d.paragraphs)  # subsecciones de la sección 3
    assert d.tables and all(t.style.name == "Table Grid" for t in d.tables)
    res = next(t for t in d.tables if t.rows[0].cells[0].text == "id_tramo")
    assert len(res.rows) == 6 and all(c.paragraphs[0].runs[0].bold for c in res.rows[0].cells)
    assert len(d.inline_shapes) >= 3
    assert all(abs(s.width.cm - 15) < 0.01 for s in d.inline_shapes)
    assert d.sections[0].footer.paragraphs[0].text == r.disclaimer
    assert sum(p.text == r.disclaimer for p in d.paragraphs) == 1  # portada
    assert r.title == d.core_properties.title


def test_author_empty_by_default_and_explicit(tmp_path):
    cp = _open(tmp_path).core_properties
    assert cp.author == "" and cp.last_modified_by == ""
    cp = _open(tmp_path, author="Ing. Prueba").core_properties
    assert cp.author == "Ing. Prueba" and cp.last_modified_by == "Ing. Prueba"


@pytest.mark.parametrize("lang,tag", [("es", "es-PE"), ("en", "en-US")])
def test_language_in_styles(tmp_path, lang, tag):
    d = _open(tmp_path, build(lang=lang))
    xml = d.styles.element.xml
    assert xml.count(f'w:lang w:val="{tag}"') >= 2  # docDefaults y Normal
    assert d.styles["Normal"].element.rPr.find(
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}lang").get(
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val") == tag


def test_to_complete_highlight_and_no_figures(tmp_path):
    from dataclasses import replace
    r = build(figures=False)
    r = replace(r, sections=r.sections[:-1] + (replace(r.sections[-1], to_complete=True),))
    d = _open(tmp_path, r)
    runs = [x for p in d.paragraphs for x in p.runs if x.text == "A completar por el ingeniero"]
    assert runs and runs[0].font.highlight_color == docx.enum.text.WD_COLOR_INDEX.YELLOW
    assert len(d.inline_shapes) == 0
