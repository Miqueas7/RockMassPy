"""Informe de resultados externos (Fase 8A, Tarea 4)."""
import re

import pytest

import rockmasspy.report as rp
from rockmasspy.criteria import assess_criteria, criteria_assignments
from rockmasspy.external import (ExternalRecord, ExternalSet, HbRow, MonitoringComparison, check_rocdata,
                                 compare_methods)
from rockmasspy.normative import get_profile
from rockmasspy.report.texts import REPORT_TEXTS

S = "ZZSENT"
A = f"A-{S}"


def _recs():
    r = lambda q, v, m=None, **k: ExternalRecord(A, q, v, program="Slide2", version="9.0", method=m, scale="global",  # noqa: E731
                                                 consequence="alta", **k)
    return ExternalSet((r("fs", 1.6, "bishop"), r("fs", 1.9, "spencer"), r("srf", 1.5)))


@pytest.fixture
def parts():
    ext = _recs()
    checks = assess_criteria(get_profile("READ-STACEY-2009"), external=ext,
                             assignments=criteria_assignments(external=ext), as_of="2026-11-14")
    mon = [MonitoringComparison(A, None, 3.0, 1.0, 3.0, "measured exceeds model by more than 50 %")]
    hb = [HbRow("M", 53, 21.22, mb=9.0, gamma=0.042)]
    return ext, checks, compare_methods(ext), mon, list(zip(hb, check_rocdata(hb)))


def test_sections_and_ids_only_in_tables(parts):
    ext, checks, cmp_, mon, roc = parts
    rep = rp.build_external_report(ext, checks=checks, comparisons=cmp_, monitoring=mon, rocdata=roc, title="T",
                                   date="2026-11-14")
    assert [s.number for s in rep.sections] == ["1", "2", "3", "4", "5", "6", "7", "8"]
    for s in rep.sections:
        for b in s.blocks:
            if isinstance(b, rp.Paragraph):
                assert S not in b.text
    cells = [c for s in rep.sections for b in s.blocks if isinstance(b, rp.Table) for r in b.rows for c in r]
    assert any(S in c for c in cells)
    assert "Slide2" in cells


def test_empty_optional_parts():
    rep = rp.build_external_report(_recs(), title="T")
    assert len(rep.sections) == 8


def test_bad_lang():
    with pytest.raises(ValueError):
        rp.build_external_report(_recs(), title="T", lang="fr")


def test_en_no_spanish_and_keys(parts, tmp_path):
    ext, checks, cmp_, mon, roc = parts
    rep = rp.build_external_report(ext, checks=checks, comparisons=cmp_, monitoring=mon, rocdata=roc, title="T",
                                   lang="en")
    es_vals = {v["es"] for v in REPORT_TEXTS.values() if v["es"] != v["en"]}
    txt = " ".join(b.text if isinstance(b, rp.Paragraph) else " ".join([b.caption, *b.header, *(c for r in b.rows for c in r)])
                   for s in rep.sections for b in s.blocks if not isinstance(b, rp.Figure))
    txt += " ".join(s.title for s in rep.sections)
    assert not [v for v in es_vals if len(v) > 3 and re.search(rf"\b{re.escape(v)}\b", txt)]
    for k, v in REPORT_TEXTS.items():
        if k.startswith("ex_"):
            assert set(v) == {"es", "en"} and all(v.values()), k


def test_writes_html_and_docx(parts, tmp_path):
    pytest.importorskip("docx")
    ext, checks, cmp_, mon, roc = parts
    for lang in ("es", "en"):
        rep = rp.build_external_report(ext, checks=checks, comparisons=cmp_, monitoring=mon, rocdata=roc, title="T",
                                       lang=lang)
        assert rp.write_html(rep, tmp_path / f"{lang}.html").exists()
        assert rp.write_docx(rep, tmp_path / f"{lang}.docx").exists()
