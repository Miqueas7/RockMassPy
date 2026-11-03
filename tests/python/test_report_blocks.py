import re
from types import SimpleNamespace

import pytest

import rockmasspy.report as rp
from rockmasspy import blocks as bk
from rockmasspy.report.texts import REPORT_TEXTS, t

import test_blocks as tb


def todas(tmp_path, iterations=300):
    jf, tf, bf, df = tb._todas(tmp_path)
    return tb.correr(tmp_path, jf, tf, bf, df, iterations=iterations)


@pytest.fixture
def casos(tmp_path):
    return todas(tmp_path)


def sec3(rep):
    return rep.sections[2].blocks


def caps(blocks):
    return [b.caption for b in blocks if isinstance(b, (rp.Table, rp.Figure))]


def tabla(rep, key, lang="es"):
    return next(b for b in sec3(rep) if isinstance(b, rp.Table) and b.caption == t(key, lang))


def test_tablas_en_su_orden(casos):
    rs, slopes = casos
    rep = rp.build_slope_report(slopes, title="T", figures=False, blocks=rs)
    base = len(rp._slope_blocks(slopes, "es", False))
    nuevos = sec3(rep)[base:]
    assert caps(nuevos) == [t("cap_blocks", "es"), t("cap_prob", "es"), t("cap_back", "es"),
                            t("cap_topple", "es").format(n=3), t("cap_berms", "es"),
                            t("fig_fs_hist", "es").format(n=5), t("fig_fs_cdf", "es").format(n=5)]
    blq = tabla(rep, "cap_blocks")
    assert [r[0] for r in blq.rows] == ["B1", "C1", "V1", "M1", "S1"]
    assert [r[-1] for r in blq.rows] == ["sí", "no", "no", "-", "no"]  # solo el FS ≤ 1 dice sí
    assert blq.rows[0][4] == "0.818"
    assert blq.rows[1][3] == t("bmode_dos_planos", "es")
    (prob,) = tabla(rep, "cap_prob").rows
    p = rs[4].probabilistic
    assert prob[0] == "S1" and prob[2] == f"{p.n_valid}/{p.n}" and prob[3] == "1"
    assert prob[8] == f"{p.pof * 100:.1f}"  # la PoF sale de ProbabilisticResult
    back = tabla(rep, "cap_back").rows
    assert len(back) == 9 and all(r[0] == "B1" for r in back) and back[0][3] == "70.59"
    top = next(b for b in sec3(rep) if isinstance(b, rp.Table) and b.caption == t("cap_topple", "es").format(n=3))
    assert len(top.rows) == 16 and top.rows[0][2] == t("topple_sliding", "es")
    (berm,) = tabla(rep, "cap_berms").rows
    assert berm[:2] == ("M1", "T3") and berm[7] == "sí" and berm[8] != "-"
    pairs = [(m.method_id, m.source) for m in rep.methods]
    ids = [m.method_id for m in rep.methods]
    assert len(pairs) == len(set(pairs))
    for i in ("Planar-HoekBray", "Wedge-Tetrahedral-Vector", "Toppling-GoodmanBray1976", "Berm-ModifiedRitchie",
              "Probabilistic-MC-LHS"):
        assert i in ids
    met = rep.sections[1].blocks[0]
    assert {r[0] for r in met.rows} == set(ids)


def test_figuras_con_orden_y_sin_ids(casos):
    rs, slopes = casos
    rep = rp.build_slope_report(slopes, title="T", figures=True, blocks=rs)
    figs = [b for b in sec3(rep) if isinstance(b, rp.Figure) and "5" in b.caption]
    assert len(figs) == 2 and all(f.png for f in figs)
    sin = rp.build_slope_report(slopes, title="T", figures=False, blocks=rs)
    assert all(f.png is None for f in sec3(sin) if isinstance(f, rp.Figure))
    fig = rp.block_figure(rs[4], "hist", "en")
    assert fig.axes[0].get_title() == t("fig_fs_hist", "en").format(n=5)


def test_en_ingles(casos):
    rs, slopes = casos
    rep = rp.build_slope_report(slopes, title="T", lang="en", figures=False, blocks=rs)
    blq = tabla(rep, "cap_blocks", "en")
    assert blq.header[2] == "Model" and [r[-1] for r in blq.rows] == ["yes", "no", "no", "-", "no"]
    assert blq.rows[0][2] == "planar" and blq.rows[2][2] == "toppling"
    es_vals = {v["es"] for k, v in REPORT_TEXTS.items() if v["es"] != v["en"]}
    txt = " ".join(c for b in sec3(rep) if isinstance(b, rp.Table) for row in (b.header, *b.rows) for c in row)
    txt += " ".join(caps(sec3(rep))) + " ".join(b.text for b in rep.sections[3].blocks if isinstance(b, rp.Paragraph))
    assert not [v for v in es_vals if len(v) > 3 and v in txt]


def test_todas_las_claves_en_los_dos_idiomas():
    for k in ("cap_blocks", "cap_prob", "cap_back", "cap_topple", "cap_berms", "h_block", "h_model", "h_block_mode",
              "h_fs", "h_fs_le1", "h_sampling", "h_valid", "h_seed", "h_mean", "h_sd", "h_min", "h_max", "h_pof",
              "h_beta_n", "h_beta_ln", "h_phi0", "h_bench_h", "h_berm_w", "h_ritchie", "h_required", "h_ira",
              "h_narrower", "h_berm_rel", "h_state", "fig_fs_hist", "fig_fs_cdf", "model_planar", "model_wedge",
              "model_toppling", "model_berm", "bmode_planar", "bmode_dos_planos", "bmode_plano_1", "bmode_plano_2",
              "bmode_despegue", "bmode_no_formado", "bmode_volteo", "topple_stable", "topple_toppling",
              "topple_sliding", "att_fs_below_1", "att_block_warnings", "sl_scope", "bl_attention",
              "cap_bl_warnings", "h_blocks"):
        assert set(REPORT_TEXTS[k]) == {"es", "en"} and all(REPORT_TEXTS[k].values()), k
    assert "3D" in t("sl_scope", "es") and "PoF" in t("sl_scope", "en")


def test_word_trae_la_tabla_de_bloques(casos, tmp_path):
    docx = pytest.importorskip("docx")
    rs, slopes = casos
    out = rp.write_docx(rp.build_slope_report(slopes, title="T", figures=False, blocks=rs), tmp_path / "x.docx")
    d = docx.Document(str(out))
    assert any(c.text == "S1" for tb_ in d.tables for row in tb_.rows for c in row.cells)
    assert any(c.text == t("h_fs_le1", "es") for tb_ in d.tables for row in tb_.rows for c in row.cells)


def test_sin_bloques_es_el_informe_de_la_3a(casos, tmp_path):
    _, slopes = casos
    a = rp.write_html(rp.build_slope_report(slopes, title="T", figures=False, date="d"), tmp_path / "a.html")
    b = rp.write_html(rp.build_slope_report(slopes, title="T", figures=False, date="d", blocks=()), tmp_path / "b.html")
    assert a.read_text(encoding="utf-8") == b.read_text(encoding="utf-8")
    rep = rp.build_slope_report(slopes, title="T", figures=False, blocks=())
    assert sec3(rep) == rp._slope_blocks(slopes, "es", False)
    txt = a.read_text(encoding="utf-8")
    for k in ("cap_blocks", "bl_attention", "cap_bl_warnings"):
        assert t(k, "es").split("{")[0] not in txt


def test_avisos_y_atencion_de_los_bloques(tmp_path):
    rs, slopes = tb.correr(tmp_path, ["R1,J1,35,140"], [tb.talud()], [tb.B(**tb.PL1)])  # aviso lateral y FS < 1
    rep = rp.build_slope_report(slopes, title="T", figures=False, blocks=rs)
    s4 = rep.sections[3].blocks
    w = next(b for b in s4 if isinstance(b, rp.Table) and b.caption == t("cap_bl_warnings", "es"))
    assert w.header == (t("h_warning", "es"), t("h_blocks", "es")) and w.rows == ((rs[0].warnings[0], "1"),)
    att = [b.text for b in s4 if isinstance(b, rp.Paragraph) and b.text.startswith("Bloques que piden")]
    assert att == [t("bl_attention", "es").format(n=1, m=1, why=f"{t('att_fs_below_1', 'es')} (1), "
                                                                   f"{t('att_block_warnings', 'es')} (1)")]


def test_nota_de_bloque_como_parrafo(tmp_path):
    rs, slopes = tb.correr(tmp_path, ["R1,J1,50,180"], [tb.talud(fr="60")], [tb.B(**tb.PL1)])  # no formado
    rep = rp.build_slope_report(slopes, title="T", figures=False, blocks=rs)
    paras = [b.text for b in rep.sections[3].blocks if isinstance(b, rp.Paragraph)]
    assert rs[0].notes[0] in paras and not any(p.startswith("Bloques que piden") for p in paras)
    (fila,) = tabla(rep, "cap_blocks").rows
    assert fila[3] == t("bmode_no_formado", "es") and fila[4] == "-" and fila[5] == "-"


def test_fs_infinito(tmp_path):
    fila = {**tb.PL1, "perno_kn_m": 1e6, "perno_inclinacion_grados": 0, "perno_tipo": "activo"}
    rs, slopes = tb.correr(tmp_path, tb.J35, [tb.talud()], [tb.B(**fila)])
    (r,) = tabla(rp.build_slope_report(slopes, title="T", figures=False, blocks=rs), "cap_blocks").rows
    assert r[4] == "∞" and r[5] == "no"


def _fake(fs, warnings=(), notes=()):
    det = None if fs is None else SimpleNamespace(factor_of_safety=fs, formed=True)
    return bk.BlockResult("B", "T1", 1, "planar", det, None, None, None, tuple(warnings), tuple(notes), ())


def test_paridad_de_conteos(tmp_path):
    _, slopes = tb.correr(tmp_path, tb.J35, [tb.talud()], [tb.B(**tb.PL1)])
    rs = [_fake(x) for x in (0.5, 1.0, 1 + 1e-12, 1.2)]
    rep = rp.build_slope_report(slopes, title="T", figures=False, blocks=rs)
    si = sum(r[5] == "sí" for r in tabla(rep, "cap_blocks").rows)
    _, filas = tb.leer(bk.save_block_results(rs, tmp_path / "p.csv"))
    assert si == bk.block_counts(rs)["fs_below_1"] == sum(f["fs_menor_o_igual_1"] == "si" for f in filas) == 3


@pytest.mark.parametrize("case", ["fs", "warning", "note", "quiet"])
def test_atencion_igual_a_needs_attention(tmp_path, case):
    _, slopes = tb.correr(tmp_path, tb.J35, [tb.talud(fr="40")], [tb.B(**tb.PL1)])
    assert not any(s.needs_attention for s in slopes)
    r = {"fs": _fake(0.9), "warning": _fake(1.5, warnings=("w",)), "note": _fake(1.5, notes=("n",)),
         "quiet": _fake(1.5)}[case]
    rep = rp.build_slope_report(slopes, title="T", figures=False, blocks=[r])
    paras = [b.text for b in rep.sections[3].blocks if isinstance(b, rp.Paragraph)]
    hay = any(p.startswith("Bloques que piden") for p in paras)
    assert hay == r.needs_attention == (case in ("fs", "warning"))


def test_privacidad_en_el_informe(tmp_path):
    jf = ["R-ZZSENT,J1,35,180"] * 3
    tf = [tb.talud("T-ZZSENT", "R-ZZSENT")]
    bf = [tb.B(**{**tb.SMP, "id_bloque": "B-ZZSENT", "id_talud": "T-ZZSENT"})]
    df = [tb.D("B-ZZSENT", "friccion_1_grados", "normal", 35, 5, 15, 70)]
    rs, slopes = tb.correr(tmp_path, jf, tf, bf, df, iterations=200)
    rep = rp.build_slope_report(slopes, title="T", figures=False, blocks=rs)
    assert not any("ZZSENT" in c for c in caps(sec3(rep)) if c)
    html = rp.write_html(rep, tmp_path / "x.html").read_text(encoding="utf-8")
    assert "B-ZZSENT" in html and "T-ZZSENT" in html
    assert len(re.findall("ZZSENT", html)) == len(re.findall("[BTR]-ZZSENT", html))
