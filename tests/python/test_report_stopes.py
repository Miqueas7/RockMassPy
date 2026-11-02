import pytest

import rockmasspy as rm
import rockmasspy.report as rp
from test_stope_surfaces import csv, evaluar


@pytest.fixture
def results(tmp_path):
    return evaluar(csv(tmp_path))


def test_sections_and_tables(results):
    rep = rp.build_stope_report(results, title="T", figures=False, date="2026-11-02")
    assert [s.number for s in rep.sections] == ["1", "2", "3", "4", "5"]
    tables = [b for b in rep.sections[2].blocks if isinstance(b, rp.Table)]
    assert len(tables) == 2 and len(tables[0].rows) == 6
    assert tables[0].header[0] == "id_superficie"
    assert sum(int(r[-1]) for r in tables[1].rows) == 6
    assert any(isinstance(b, rp.Figure) for b in rep.sections[2].blocks)
    assert rep.sections[4].blocks[0].text == rp.DISCLAIMER["es"]


def test_methods_deduplicated_with_digitized_source(results):
    rep = rp.build_stope_report(results, title="T", figures=False)
    pairs = [(m.method_id, m.source) for m in rep.methods]
    assert len(pairs) == len(set(pairs))
    m = next(m for m in rep.methods if m.method_id == "Mathews-Potvin1988" and "digitized" in m.source)
    assert m.verification == "Primary"


def test_warnings_counted_without_ids(results):
    rep = rp.build_stope_report(results, title="T", figures=False)
    tab = rep.sections[3].blocks[0]
    assert tab.rows == (("N' below the graph (0.1): taken as caved", "2"),)
    assert not any(r.id_superficie in str(tab) for r in results)


def test_english_and_errors(results):
    es = rp.build_stope_report(results, title="T", figures=False)
    en = rp.build_stope_report(results, title="T", lang="en", figures=False)
    assert es.sections[0].title != en.sections[0].title and en.sections[0].title == "Scope"
    with pytest.raises(ValueError):
        rp.build_stope_report([], title="T")
    with pytest.raises(ValueError):
        rp.build_stope_report(results, title="T", lang="fr")


def test_figure_and_docx_and_no_leak(results, tmp_path):
    pytest.importorskip("matplotlib")
    rep = rp.build_stope_report(results, title="T")
    fig = next(b for b in rep.sections[2].blocks if isinstance(b, rp.Figure))
    assert fig.png and fig.png[:4] == b"\x89PNG"
    h = rp.write_html(rep, tmp_path / "r.html").read_text(encoding="utf-8")
    assert "SECRETO-123" not in h and "S1" in h  # id_superficie va en la tabla del informe
    docx = pytest.importorskip("docx")
    d = docx.Document(str(rp.write_docx(rep, tmp_path / "r.docx")))
    assert any("id_superficie" in c.text for t in d.tables for c in t.rows[0].cells)
