"""Informe del histórico (Fase 4A): datos, auditoría, preparación por nivel, nivel 1 y limitaciones (R12–R14)."""
import dataclasses

import pytest

import rockmasspy as rm
import rockmasspy.report as rp

pred = pytest.importorskip("rockmasspy.predictive")

SENT = "ZZSENT"


@pytest.fixture(scope="module")
def caso():
    h, _ = pred.synthetic_history(seed=12)
    ts = [dataclasses.replace(t, labor_codigo=f"{SENT}{t.labor_codigo}", zona_nivel=f"{SENT}{t.zona_nivel}",
                              litologia=f"{SENT}{t.litologia}") for t in h.tramos]
    ts[0] = dataclasses.replace(ts[0], q_valor=ts[0].q_valor * 3)  # un hallazgo q_mismatch
    h = rm.History(tuple(ts), h.support_types, h.inspections)
    fits = [pred.fit_site_correlation(h, k, n_boot=200) for k in ("rmr_from_q", "gsi_from_rmr")]
    fits.append(("gsi_from_q_prime", "gsi_from_q_prime: no usable pairs in the history"))
    return h, rm.audit_history(h), fits


def tablas(sec):
    out = []
    for b in sec.blocks:
        out += tablas(b) if isinstance(b, rp.Section) else [b] if isinstance(b, rp.Table) else []
    return out


def textos(rep):
    def walk(b):
        if isinstance(b, rp.Section):
            yield b.title
            for x in b.blocks:
                yield from walk(x)
        elif isinstance(b, rp.Paragraph):
            yield b.text
        elif isinstance(b, rp.Table):
            yield b.caption
            yield from b.header
            for r in b.rows:
                yield from r
        elif isinstance(b, rp.Figure):
            yield b.caption + b.note
    return [x for s in rep.sections for x in walk(s)]


def test_sections_and_counts(caso):
    h, audit, fits = caso
    rep = rp.build_history_report(audit, fits, history=h, figures=False, date="2026-11-05")
    assert [s.number for s in rep.sections] == ["1", "2", "3", "4", "5"]
    assert rep.title == rp.t("hist_title", "es")
    data = dict(tablas(rep.sections[0])[0].rows)
    c = rm.history_audit_counts(audit)
    assert data[rp.t("hd_tramos", "es")] == str(c["tramos"])
    assert data[rp.t("hd_inspections", "es")] == str(c["inspections"])
    assert data[rp.t("hd_with_insp", "es")] == str(len(rm.tramo_outcomes(h)))
    assert data[rp.t("hd_years_eval", "es")].startswith("2019–")
    kinds, findings = tablas(rep.sections[1])
    assert dict(kinds.rows)["q_mismatch"] == "1" and len(findings.rows) == len(audit.findings)
    assert findings.header[3] == "id_tramo" and findings.rows[0][:4] == ("q_mismatch", "Tramos", "2", "T0001")


def test_readiness_marked_design_decision(caso):
    _, audit, fits = caso
    rep = rp.build_history_report(audit, fits, figures=False)
    (tab,) = tablas(rep.sections[2])
    assert "decisión de diseño" in tab.header[3]
    assert len(tab.rows) == len(audit.readiness)
    assert tab.rows[0][:4] == ("1", "rmr_from_q", f"pairs {audit.readiness[0].counts['pairs']}; labors 20",
                               "pairs 30; labors 5")
    assert "decisión de diseño" in rep.sections[2].blocks[0].text


def test_level1(caso):
    h, audit, fits = caso
    rep = rp.build_history_report(audit, fits, history=h, figures=False)
    s4 = rep.sections[3]
    subs = [b for b in s4.blocks if isinstance(b, rp.Section)]
    assert [s.number for s in subs] == ["4.1", "4.2", "4.3"]
    methods = tablas(rp.Section("", "", s4.blocks[:2]))[0]
    assert {"RmrFromQ_Huang2026", "GsiFromRmr89Prime_HoekDiederichs2006"} <= {r[0] for r in methods.rows}
    fit_tab = tablas(subs[0])[0]
    assert [r[0] for r in fit_tab.rows] == ["mina", "D1", "D2", "D3", "D4"]
    mine = fits[0].mine
    assert fit_tab.rows[0][1:4] == (str(mine.n), str(mine.n_labors), "sitio")
    assert fit_tab.rows[0][5].startswith(f"{mine.a:.4g} (")
    assert "no calibrada al sitio" in {r[3] for r in fit_tab.rows}
    prior = subs[0].blocks[0].text
    assert "RmrFromQ_Huang2026 [Secondary]" in prior and "decisión de diseño" in prior
    assert "deming_ratio not given" in subs[0].blocks[2].text
    assert subs[2].blocks[0].text.startswith("No ajustado: gsi_from_q_prime: no usable pairs")
    assert isinstance(subs[0].blocks[-1], rp.Figure) and subs[0].blocks[-1].png is None  # figures=False


def test_no_correlations_and_english(caso):
    _, audit, _ = caso
    es = rp.build_history_report(audit)
    assert es.sections[3].blocks == (rp.Paragraph(rp.t("hist_l1_none", "es")),)
    en = rp.build_history_report(audit, lang="en")
    assert en.sections[0].title == "Data" and en.sections[3].title.startswith("Level 1")
    with pytest.raises(ValueError):
        rp.build_history_report(audit, lang="fr")


def test_no_sentinel_and_writers(caso, tmp_path):
    h, audit, fits = caso
    rep = rp.build_history_report(audit, fits, history=h)
    assert not any(SENT in x for x in textos(rep))
    for lit in pred.synthetic.LITHOLOGIES:
        assert not any(lit in x for x in textos(rep))
    html = rp.write_html(rep, tmp_path / "h.html").read_text(encoding="utf-8")
    assert SENT not in html and "T0001" in html
    pytest.importorskip("matplotlib")
    figs = [b for s in rep.sections[3].blocks if isinstance(s, rp.Section) for b in s.blocks
            if isinstance(b, rp.Figure)]
    assert len(figs) == 2 and all(f.png[:4] == b"\x89PNG" for f in figs)
    docx = pytest.importorskip("docx")
    d = docx.Document(str(rp.write_docx(rep, tmp_path / "h.docx")))
    heads = [p.text for p in d.paragraphs if p.style.name.startswith("Heading")]
    assert heads[:4] == ["1. Datos", "2. Auditoría de ingesta", "3. Preparación por nivel",
                         "4. Nivel 1: correlaciones propias del sitio"]
    assert "5. Limitaciones" in heads
    assert SENT not in "\n".join(c.text for t in d.tables for row in t.rows for c in row.cells)


def test_site_custom_tolerates_none():
    class Fit:
        def to_custom_correlation(self):
            return None

    class Raises:
        def to_custom_correlation(self):
            raise ValueError("single x")

    assert rp.site_custom(Fit()) is None and rp.site_custom(Raises()) is None
