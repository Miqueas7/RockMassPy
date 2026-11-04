import re
from types import SimpleNamespace

import pytest

import rockmasspy as rm
import rockmasspy.report as rp
from rockmasspy import limit_equilibrium as le
from rockmasspy.report.texts import REPORT_TEXTS, t

import test_limit_equilibrium as tl
import test_report_blocks as trb


@pytest.fixture(scope="module")
def les(tmp_path_factory):
    data = tl.merge(tl.fk_data(), tl.acads3b_data(registro="R-ZZSENT", kh=0.05), {"Sismos": tl.seno()})
    return rm.assess_le(tl.hojas(tmp_path_factory.mktemp("rle"), data))


@pytest.fixture
def slopes(tmp_path):
    return trb.todas(tmp_path, iterations=100)


def sec3(rep):
    return rep.sections[2].blocks


def tabla(rep, key, lang="es"):
    return next(b for b in sec3(rep) if isinstance(b, rp.Table) and b.caption == t(key, lang))


def test_tablas_y_figuras_en_su_orden(les):
    rep = rp.build_slope_report([], title="T", figures=False, le=les)
    caps = [b.caption for b in sec3(rep) if isinstance(b, (rp.Table, rp.Figure))]
    assert caps == [t("cap_le", "es"), t("cap_le_surface", "es"), t("fig_le_section", "es").format(n=1),
                    t("fig_le_section", "es").format(n=2), t("fig_newmark", "es").format(n=2)]
    eq = tabla(rep, "cap_le")
    assert [r[:4] for r in eq.rows] == [("AFK-ZZSENT", "SFK-ZZSENT", "circular", "Bishop"),
                                        ("AFK-ZZSENT", "SFK-ZZSENT", "circular", "Spencer"),
                                        ("A3B-ZZSENT", "S3B-ZZSENT", "dada", "Spencer"),
                                        ("A3B-ZZSENT", "S3B-ZZSENT", "dada", "M-P (GLE)")]
    fk, b = les
    assert eq.header[4:7] == ("kh", t("h_fs", "es"), t("h_fs_static", "es"))
    assert eq.rows[0][4] == "0.000" and eq.rows[2][4] == "0.050"
    assert eq.rows[0][5] == eq.rows[0][6] == f"{fk.results[0].factor_of_safety:.3f}" and eq.rows[0][7] == "no"
    assert eq.rows[2][5] == f"{b.results[0].factor_of_safety:.3f}"
    assert eq.rows[2][6] == f"{b.static_results[0].factor_of_safety:.3f}" != eq.rows[2][5]  # sin kh, más alto
    assert eq.rows[0][8] == "-" and eq.rows[1][8] != "-"  # λ solo en Spencer
    assert eq.rows[2][9] == f"{b.yield_.ky:.3f}" and eq.rows[2][10] == f"{b.newmark.displacement_m:.3f}"
    assert eq.rows[0][9] == eq.rows[0][10] == "-"
    assert eq.rows[3][9] == eq.rows[3][10] == "-"  # ky y Newmark solo en la fila del primer método
    sup = tabla(rep, "cap_le_surface").rows
    c = fk.surface.circle
    assert sup[0][:5] == ("AFK-ZZSENT", "circular", f"{c.xc:.2f}", f"{c.yc:.2f}", f"{c.radius:.2f}")
    assert sup[0][5] == "-" and sup[0][6] == str(fk.search.evaluated)
    assert sup[1][2:5] == ("-", "-", "-") and sup[1][5].count(";") == 3 and sup[1][6:] == ("-", "-")
    ids = {m.method_id for m in rep.methods}
    assert {"Circular-Grid-Search", "Bishop-Simplified", "Spencer", "Morgenstern-Price-GLE",
            "LE-YieldCoefficient", "Newmark-RigidBlock"} <= ids
    assert {r[0] for r in rep.sections[1].blocks[0].rows} == ids


def test_sin_taludes_la_seccion_3a_lo_dice(les):
    rep = rp.build_slope_report([], title="T", figures=False, le=les)
    assert sec3(rep)[0] == rp.Paragraph(t("sl_no_slopes", "es"))
    assert t("cap_slopes", "es") not in [b.caption for b in sec3(rep) if isinstance(b, rp.Table)]
    with pytest.raises(ValueError, match="empty"):
        rp.build_slope_report([], title="T")


@pytest.mark.parametrize("lang", ["es", "en"])
def test_solo_le_alcance_y_titulo_propios(les, lang):
    rep = rp.build_slope_report([], title="T", lang=lang, figures=False, le=les)
    assert rep.sections[0].blocks == (rp.Paragraph(t("le_scope_only", lang)),)  # sin cinemática ni «Además»
    assert rep.subtitle == t("slope_title_le", lang) == {"es": "Estabilidad de taludes", "en": "Slope stability"}[lang]
    assert "roca" not in rep.subtitle and "Rock" not in rep.subtitle
    assert not t("le_scope_only", lang).startswith(("Además", "It also"))


def test_con_taludes_alcance_y_titulo_como_antes(slopes, les):
    _, sl = slopes
    rep = rp.build_slope_report(sl, title="T", figures=False, le=les)
    assert rep.sections[0].blocks == (rp.Paragraph(t("sl_scope", "es")), rp.Paragraph(t("le_scope", "es")))
    assert rep.subtitle == t("slope_title", "es") == "Estabilidad de taludes en roca"
    assert rp.build_slope_report(sl, title="T", figures=False).subtitle == t("slope_title", "es")


def test_metodos_sin_repetir(les):
    rep = rp.build_slope_report([], title="T", figures=False, le=les)
    ids = [r[0] for r in rep.sections[1].blocks[0].rows]
    assert len(ids) == len(set(ids)) and ids.count("Morgenstern-Price-GLE") == 1
    a = SimpleNamespace(method_id="X", verification=SimpleNamespace(name="Secondary"), source="F1")
    b = SimpleNamespace(method_id="X", verification=SimpleNamespace(name="Secondary"), source="F2")
    assert rp._dedup_methods([a, b, a]) == (rp.MethodRef("X", "Secondary", "F1 · F2"),)


def test_sin_le_el_informe_no_cambia(slopes, tmp_path):
    _, sl = slopes
    a = rp.build_slope_report(sl, title="T", figures=False, date="d")
    b = rp.build_slope_report(sl, title="T", figures=False, date="d", le=())
    assert a == b and sec3(a) == rp._slope_blocks(sl, "es", False)
    assert rp.write_html(a, tmp_path / "a.html").read_text(encoding="utf-8") == \
        rp.write_html(b, tmp_path / "b.html").read_text(encoding="utf-8")
    txt = (tmp_path / "a.html").read_text(encoding="utf-8")
    for k in ("cap_le", "le_scope", "cap_le_warnings", "le_attention", "sl_no_slopes"):
        assert t(k, "es").split("{")[0] not in txt


def test_taludes_bloques_y_le_juntos(slopes, les):
    rs, sl = slopes
    rep = rp.build_slope_report(sl, title="T", figures=False, blocks=rs, le=les)
    base = rp._slope_blocks(sl, "es", False) + rp._block_blocks(rs, "es", False)
    assert sec3(rep)[:len(base)] == base and sec3(rep)[len(base)].caption == t("cap_le", "es")


def test_figuras_con_png_y_titulo_por_orden(les):
    rep = rp.build_slope_report([], title="T", figures=True, le=les)
    figs = [b for b in sec3(rep) if isinstance(b, rp.Figure)]
    assert len(figs) == 3 and all(f.png for f in figs) and not any("ZZSENT" in f.caption for f in figs)
    assert rp.le_figure(les[1], "en").axes[0].get_title() == t("fig_le_section", "en").format(n=2)
    assert rp.newmark_figure(les[1], "en").axes[0].get_title() == t("fig_newmark", "en").format(n=2)


def test_en_ingles(les):
    rep = rp.build_slope_report([], title="T", lang="en", figures=False, le=les)
    eq = tabla(rep, "cap_le", "en")
    assert eq.header[2:4] == ("Surface", "Method") and eq.rows[2][2] == "given"
    es_vals = {v["es"] for v in REPORT_TEXTS.values() if v["es"] != v["en"]}
    txt = " ".join(c for b in sec3(rep) if isinstance(b, rp.Table) for row in (b.header, *b.rows) for c in row)
    txt += " ".join(b.caption for b in sec3(rep) if isinstance(b, (rp.Table, rp.Figure)))
    txt += " ".join(b.text for s in rep.sections[:3] for b in s.blocks if isinstance(b, rp.Paragraph))  # sin notas del núcleo
    assert not [v for v in es_vals if len(v) > 3 and v in txt]


def test_claves_en_los_dos_idiomas():
    for k in ("sl_no_slopes", "le_scope", "le_scope_only", "slope_title_le", "h_fs_static", "cap_le", "cap_le_surface", "cap_le_warnings", "h_analyses",
              "h_le_surface", "h_le_method", "h_lambda", "h_ky", "h_newmark", "h_points", "h_evaluated",
              "h_discarded", "le_surf_circular", "le_surf_block", "le_surf_given", "fig_le_section", "fig_newmark",
              "att_le_fs_below_1", "att_le_warnings", "le_attention"):
        assert set(REPORT_TEXTS[k]) == {"es", "en"} and all(REPORT_TEXTS[k].values()), k


def _fake(fs, warnings=(), notes=(), order=1):
    res = SimpleNamespace(factor_of_safety=fs, method=rm.LeMethod.Bishop, lambda_=None, converged=fs is not None,
                          info=SimpleNamespace(method_id="Bishop-Simplified"))
    return le.LeAnalysisResult("A", "S", order, "given", (res,), None, None, None, tuple(warnings), tuple(notes), ())


def test_paridad_de_conteos_informe_y_archivo(tmp_path):
    rs = [_fake(x, order=i) for i, x in enumerate((0.5, 1.0, 1 + 1e-12, 1.2, None), 1)]
    rep = rp.build_slope_report([], title="T", figures=False, le=rs)
    si = sum(r[7] == "sí" for r in tabla(rep, "cap_le").rows)
    _, filas = tl.leer(le.save_le_results(rs, tmp_path / "p.csv"))
    assert si == le.le_counts(rs)["fs_below_1"] == sum(f["fs_menor_o_igual_1"] == "si" for f in filas) == 3
    assert [r[7] for r in tabla(rep, "cap_le").rows][-1] == "-"


@pytest.mark.parametrize("case", ["fs", "warning", "note", "quiet"])
def test_atencion_igual_a_le_attention(case):
    r = {"fs": _fake(0.9), "warning": _fake(1.5, warnings=("w",)), "note": _fake(1.5, notes=("n",)),
         "quiet": _fake(1.5)}[case]
    s4 = rp.build_slope_report([], title="T", figures=False, le=[r]).sections[3].blocks
    att = [b.text for b in s4 if isinstance(b, rp.Paragraph) and b.text.startswith("Análisis de equilibrio")]
    assert bool(att) == r.needs_attention == (case in ("fs", "warning"))
    if case == "fs":
        assert att == [t("le_attention", "es").format(n=1, m=1, why=f"{t('att_le_fs_below_1', 'es')} (1)")]
    if case == "note":
        assert rp.Paragraph("n") in s4


def test_avisos_agrupados_entre_analisis():
    rs = [_fake(1.5, warnings=("bishop: m-alpha below 0.2 in 3 slices: results may be unreliable",)),
          _fake(1.5, warnings=("bishop: m-alpha below 0.2 in 5 slices: results may be unreliable",))]
    s4 = rp.build_slope_report([], title="T", figures=False, le=rs).sections[3].blocks
    w = next(b for b in s4 if isinstance(b, rp.Table) and b.caption == t("cap_le_warnings", "es"))
    assert w.header == (t("h_warning", "es"), t("h_analyses", "es"))
    assert w.rows == (("bishop: m-alpha below 0.2 in N slices: results may be unreliable", "2"),)


def test_privacidad_html_y_word(les, tmp_path):
    rep = rp.build_slope_report([], title="T", figures=True, le=les)
    html = rp.write_html(rep, tmp_path / "x.html").read_text(encoding="utf-8")
    celdas = re.findall(r"<td>([^<]*ZZSENT[^<]*)</td>", html)
    assert len(re.findall("ZZSENT", html)) == len(celdas) > 0  # solo en celdas de tabla
    assert set(celdas) == {"AFK-ZZSENT", "SFK-ZZSENT", "A3B-ZZSENT", "S3B-ZZSENT"}  # ni material ni línea ni registro
    docx = pytest.importorskip("docx")
    d = docx.Document(str(rp.write_docx(rep, tmp_path / "x.docx")))
    assert not any("ZZSENT" in p.text for p in d.paragraphs)
    assert any(c.text == "A3B-ZZSENT" for x in d.tables for row in x.rows for c in row.cells)
