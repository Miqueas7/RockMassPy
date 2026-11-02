from dataclasses import replace
from types import SimpleNamespace

import pytest

import rockmasspy.report as rp
from test_slopes import Q, RIQ, T, correr


@pytest.fixture
def results(tmp_path):
    # T1: Riquelme con SMR; T2: Q-slope con cara de 80 (más empinada que beta)
    return correr(tmp_path, [T(id_="T-ZZSENT", tramo="R1"), T("T2", fr="", rmr="", exc="", q=Q, b="2,1,0.9", srf="2.5,,")])


def tables(sec):
    return [b for b in sec.blocks if isinstance(b, rp.Table)]


def test_sections_and_tables(results):
    rep = rp.build_slope_report(results, title="T", figures=False, date="2026-11-02")
    assert [s.number for s in rep.sections] == ["1", "2", "3", "4", "5"]
    tabs = tables(rep.sections[2])
    assert [x.header[0] for x in tabs] == ["id_talud", "id_tramo", "id_talud", "id_talud"]
    smr = tabs[2]
    assert any(r[1] == "J1×J2" for r in smr.rows)
    assert sum("D" in r[-1] for r in smr.rows) == 1 and sum("C" in r[-1] for r in smr.rows) == 1
    assert len(tabs[3].rows) == 1 and tabs[3].rows[0][0] == "T2"
    assert all(f.png is None for f in rep.sections[2].blocks if isinstance(f, rp.Figure))
    assert rep.sections[4].blocks[0].text == rp.DISCLAIMER["es"]
    pairs = [(m.method_id, m.source) for m in rep.methods]
    assert pairs and len(pairs) == len(set(pairs)) and all(m.verification for m in rep.methods)


def test_infinite_kappa(tmp_path):
    (r,) = correr(tmp_path, [T()], jf=["R1,J1,60,100", "R1,J1,60,100", "R1,J2,30,250"])
    fam = tables(rp.build_slope_report([r], title="T", figures=False).sections[2])[1]
    assert fam.rows[0][4] == "∞" and fam.rows[1][4] == "-"


def test_figures_and_privacy(results, tmp_path):
    rep = rp.build_slope_report(results, title="T", figures=True)
    figs = [b for b in rep.sections[2].blocks if isinstance(b, rp.Figure)]
    assert len(figs) >= 2 and all(f.png for f in figs)
    assert all("ZZSENT" not in f.caption for f in figs)
    assert any("1" in f.caption for f in figs)
    p = tmp_path / "x.html"
    rp.write_html(rep, p)
    html = p.read_text(encoding="utf-8")
    assert "T-ZZSENT" in html and html.count("ZZSENT") == html.count("T-ZZSENT")


def test_english_and_errors(results):
    es = rp.build_slope_report(results, title="T", figures=False)
    en = rp.build_slope_report(results, title="T", lang="en", figures=False)
    assert en.subtitle == "Rock slope stability" and es.subtitle != en.subtitle
    assert en.sections[0].title == "Scope"
    assert tables(en.sections[2])[0].header[2] == "Face (dip/dir.)"
    with pytest.raises(ValueError, match="empty"):
        rp.build_slope_report([], title="T")
    assert rp.build_slope_report(results, title="T", author="Ana", figures=False).subtitle.endswith("Ana")


def test_docx_opens(results, tmp_path):
    docx = pytest.importorskip("docx")
    out = rp.write_docx(rp.build_slope_report(results, title="T", figures=False), tmp_path / "x.docx")
    d = docx.Document(str(out))
    assert any("J1×J2" in c.text for tb in d.tables for row in tb.rows for c in row.cells)


def test_notes_separate_and_empty_caption(tmp_path):
    (r,) = correr(tmp_path, [T(rmr="", exc="")], jf=["R1,J1,20,90", "R1,J2,20,90"])
    rep = rp.build_slope_report([r], title="T", figures=False)
    paras = [b.text for b in rep.sections[3].blocks if isinstance(b, rp.Paragraph)]
    assert len(paras) == 2 + len(r.notes) and r.notes[0] in paras
    smr = next(b for b in rep.sections[2].blocks if isinstance(b, rp.Paragraph) and "SMR" in b.text)
    assert ".:" not in smr.text and smr.text.endswith("Ninguno.")


_KIN = dict(planar=0, wedge_primary=0, wedge_secondary=0, flexural_toppling=0, direct_toppling=0,
            direct_toppling_oblique=0)
_CLS = lambda n: SimpleNamespace(discrete=SimpleNamespace(smr_class=n), continuous=SimpleNamespace(smr_class=n))


@pytest.mark.parametrize("case", [*_KIN, "smr_d", "smr_c", "qslope", "warning", "note", "quiet"])
def test_attention_matches_needs_attention(tmp_path, case):
    (r,) = correr(tmp_path, [T(fr="", rmr="", exc="")])
    kw = {}
    if case in _KIN:
        kw["kinematics"] = SimpleNamespace(**{**_KIN, case: 1})
    elif case == "smr_d":
        kw["smr_discrete"] = _CLS(4)
    elif case == "smr_c":
        kw["smr_continuous"] = _CLS(5)
    elif case == "qslope":
        kw["face_steeper_than_beta"] = True
    elif case == "warning":
        kw["warnings"] = ("w",)
    elif case == "note":
        kw["notes"] = ("n",)
    r = replace(r, **{"warnings": (), "notes": (), **kw})
    assert bool(rp._attention(r)) == r.needs_attention == (case not in ("note", "quiet"))
