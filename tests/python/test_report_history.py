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


def test_methods_table_separates_marks(caso):
    """La marca [V2] de los métodos estadísticos y la verificación del núcleo del prior van en columnas aparte; el
    bootstrap dice las réplicas que de verdad corrieron (n_boot=200 en este caso, no 2000)."""
    _, audit, fits = caso
    for lang in ("es", "en"):
        rep = rp.build_history_report(audit, fits, figures=False, lang=lang)
        tab = tablas(rp.Section("", "", rep.sections[3].blocks[:2]))[0]
        assert tab.header[2:4] == (rp.t("h_research_mark", lang), rp.t("h_core_verification", lang))
        stats = [r for r in tab.rows if r[1] == rp.t("hm_role_stat", lang)]
        priors = [r for r in tab.rows if r[1] == rp.t("hm_role_prior", lang)]
        assert len(stats) == 4 and all(r[2] == "[V2]" and r[3] == "-" for r in stats)
        assert {r[0] for r in priors} == {"RmrFromQ_Huang2026", "GsiFromRmr89Prime_HoekDiederichs2006"}
        assert all(r[2] == "-" and r[3] in ("Primary", "Secondary") for r in priors)
        boot = stats[1][0]
        assert "200" in boot and "2000" not in boot


# ---------- niveles 2 y 3 y TRIPOD+AI ----------

@pytest.fixture(scope="module")
def niveles():
    """Histórico grande con efecto del sitio (nivel 3 «site») y ZZSENT en labor, zona y litología."""
    h, _ = pred.synthetic_history(seed=0, n_zones=8, labors_per_zone=12, tramos_per_labor=15)
    ts = [dataclasses.replace(t, labor_codigo=f"{SENT}{t.labor_codigo}", zona_nivel=f"{SENT}{t.zona_nivel}",
                              litologia=f"{SENT}{t.litologia}") for t in h.tramos]
    h = rm.History(tuple(ts), h.support_types, h.inspections)
    return h, rm.audit_history(h), pred.audit_practice(h, n_boot=100), pred.fit_performance(h, n_boot=100)


def _rep(niveles, **kw):
    h, audit, practice, perf = niveles
    return rp.build_history_report(audit, history=h, practice=practice, performance=perf, figures=False, **kw)


def test_level_sections_order(niveles):
    rep = _rep(niveles, threshold=0.3)
    assert [s.number for s in rep.sections] == [str(i) for i in range(1, 9)]
    assert [s.title for s in rep.sections[4:]] == [rp.t(k, "es") for k in ("hs_l2", "hs_l3", "hs_tripod", "hs_5")]
    h, audit, practice, _ = niveles
    solo2 = rp.build_history_report(audit, practice=practice, figures=False)
    assert [s.title for s in solo2.sections[4:]] == [rp.t(k, "es") for k in ("hs_l2", "hs_tripod", "hs_5")]
    assert rp.build_history_report(audit).sections[-1].blocks[1].text == rp.t("hist_limits_none", "es")


def test_level2_describes_and_lists_outside(niveles):
    _, _, practice, _ = niveles
    s = _rep(niveles).sections[4]
    texto = " ".join(b.text for b in s.blocks if isinstance(b, rp.Paragraph))
    assert "describe la práctica de la mina, no recomienda" in texto
    data, coef, val, conc, outside, dd = tablas(s)[:6]
    assert dict(data.rows)[rp.t("l2_n", "es")] == str(practice.n)
    assert {r[0]: r[4] for r in coef.rows}["ln_q"] == "coherente"
    assert [r[0] for r in val.rows] == [rp.t(f"part_{p}", "es") for p in ("labor", "zone", "temporal")]
    assert val.header[3:6] == ("practice", "dummy", "ngi")
    assert len(conc.rows) == len(practice.concordance.types)
    assert outside.header[0] == "id_tramo" and {r[0] for r in outside.rows} == set(practice.outside_set)
    assert "decisión de diseño" in dd.caption and len(dd.rows) == 4


def test_level3_state_validation_figures_and_rule(niveles):
    _, _, _, perf = niveles
    s = _rep(niveles, threshold=0.3).sections[5]
    state, coef, val = tablas(s)[:3]
    assert dict(state.rows)[rp.t("l3_calibration", "es")] == "propio del sitio"
    assert [r[0] for r in coef.rows] == list(perf.features)
    temporal = dict((r[0], r[-1]) for r in val.rows)[rp.t("part_temporal", "es")]
    assert temporal.startswith("no inferioridad")
    figs = [b for b in s.blocks if isinstance(b, rp.Figure)]
    assert len(figs) == 1 + len(perf.support_types) and all(f.png is None for f in figs)  # figures=False
    texto = " ".join(b.text for b in s.blocks if isinstance(b, rp.Paragraph))
    assert "obligatorio y no tiene valor por defecto" in texto and "P(falla) ≤ 0.3" in texto
    assert "no inferioridad" in texto and "zona fuera" in texto
    dd = [x for x in tablas(s) if "decisión de diseño" in x.caption]
    assert dd and len(dd[0].rows) == 9
    sin_umbral = _rep(niveles).sections[5]
    assert any(isinstance(b, rp.Paragraph) and b.text == rp.t("l3_threshold_none", "es") for b in sin_umbral.blocks)
    with pytest.raises(ValueError, match="threshold"):
        _rep(niveles, threshold=1.0)


def test_tripod_and_limitations(niveles):
    from rockmasspy.report.texts import TRIPOD_ITEMS

    rep = _rep(niveles)
    (tab,) = tablas(rep.sections[6])
    assert len(tab.rows) == len(TRIPOD_ITEMS) and {r[1] for r in tab.rows} <= {"sí", "parcial", "no", "no aplica"}
    assert "Collins et al. 2024" in rep.sections[6].blocks[0].text
    lim = " ".join(b.text for b in rep.sections[7].blocks)
    for frase in ("práctica pasada como etiqueta", "Sesgo de selección", "Extrapolación"):
        assert frase in lim
    assert {"TRIPOD+AI", "Gelman et al. (2008)"} <= {m.method_id for m in rep.methods} | {m.source for m in rep.methods}


def test_levels_no_sentinel_english_and_writers(niveles, tmp_path):
    for lang in ("es", "en"):
        rep = _rep(niveles, lang=lang)
        assert not any(SENT in x for x in textos(rep))
    en = _rep(niveles, lang="en")
    assert en.sections[4].title.startswith("Level 2") and en.sections[6].title == "TRIPOD+AI checklist"
    pytest.importorskip("matplotlib")
    h, audit, practice, perf = niveles
    rep = rp.build_history_report(audit, history=h, practice=practice, performance=perf, threshold=0.3)
    figs = [b for b in rep.sections[5].blocks if isinstance(b, rp.Figure)]
    assert figs and all(f.png[:4] == b"\x89PNG" for f in figs)
    html = rp.write_html(rep, tmp_path / "n.html").read_text(encoding="utf-8")
    assert SENT not in html and practice.outside_set[0] in html  # el id_tramo, solo en su tabla
    docx = pytest.importorskip("docx")
    d = docx.Document(str(rp.write_docx(rep, tmp_path / "n.docx")))
    heads = [p.text for p in d.paragraphs if p.style.name == "Heading 1"]
    assert heads[4:] == ["5. Nivel 2: auditoría de la práctica", "6. Nivel 3: desempeño y recomendación",
                         "7. Lista TRIPOD+AI", "8. Limitaciones"]
    assert SENT not in "\n".join(c.text for t in d.tables for row in t.rows for c in row.cells)
