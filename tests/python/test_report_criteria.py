"""Informe de taludes completo y criterios en la CLI (fase 3D, tarea 4). Solo datos sintéticos."""
import ast
import hashlib
import re
from pathlib import Path

import pytest

import rockmasspy as rm
import rockmasspy.report as rp
from rockmasspy import limit_equilibrium as le
from rockmasspy.cli import main
from rockmasspy.criteria import (assess_criteria, criteria_assignments, criteria_attention, criteria_counts,
                                 return_periods)
from rockmasspy.normative import get_profile
from rockmasspy.report.texts import REPORT_TEXTS, t

import test_limit_equilibrium as tl
import test_report_blocks as trb
from test_le_sarma_criteria import p4_data

RS = get_profile("READ-STACEY-2009")
PE = get_profile("PE-DS024-2016")
S = "ZZSENT"
_BASE = dict(id_seccion="SP4-ZZSENT", superficie="sarma", linea_superficie="F-ZZSENT", sarma_angulos="116.5")
# problema 4 de Sarma (FS estático 1.197): global baja con kh y Tr 100 no cumple 1.30 (rango 1.20-1.30, extremo
# alto), banco cumple 1.1, sin escala y con la escala mal escrita son no verificables
_ROWS = {"AG": dict(escala="global", consecuencia="baja", kh=0.05, periodo_retorno_anios=100),
         "AB": dict(escala="banco", consecuencia="alta"), "AN": {}, "AX": dict(escala="glob-ZZSENT",
                                                                              consecuencia="alta")}


def mezcla(ids=tuple(_ROWS)):
    d = p4_data()
    d["Analisis_LE"] = [tl.ana(**{**_BASE, "id_analisis": f"{k}-{S}", **_ROWS[k]}) for k in ids]
    return d


@pytest.fixture(scope="module")
def files(tmp_path_factory):
    return tl.hojas(tmp_path_factory.mktemp("crit"), mezcla())


@pytest.fixture(scope="module")
def les(files):
    return rm.assess_le(files)


def checks_of(les, profile=RS, **kw):
    return assess_criteria(profile, le=les, assignments=criteria_assignments(le=les),
                           return_periods=return_periods(les), **kw)


def full(les, lang="es", figures=False, **kw):
    pchecks = [c for c in checks_of(les, PE) if c.rule == "pseudostatic_analysis_present"]
    return rp.build_slope_report([], title="T", lang=lang, figures=figures, date="2026-11-04", le=les,
                                 criteria=checks_of(les), criteria_profile=RS, profile_checks=pchecks, **kw)


def run_le(capsys, files, *extra):
    args = ["le"]
    for flag, sheet in (("--geometry", "Geometria"), ("--layers", "Estratos"), ("--materials", "Materiales_LE"),
                        ("--analyses", "Analisis_LE")):
        args += [flag, str(files[sheet])]
    code = main([*args, *map(str, extra)])
    cap = capsys.readouterr()
    return code, cap.out, cap.err


def table(rep, key, lang="es"):
    return next(b for s in rep.sections for b in s.blocks if isinstance(b, rp.Table) and b.caption == t(key, lang))


# ---------------------------------------------------------------- regresión: sin criterios, el informe de la 3C

# sha256 del HTML del commit 369ad13 (antes de la tarea 4), con la versión reemplazada por «VER»
_GOLDEN = {("all", "es"): "38b86073d2ff4233cb2f9b30f2ab41e4aee80b0547458f13b7ab7cb610cdaed9",
           ("le", "es"): "5c8296ee1f78f49aaba0f83a1e2d50bb2d555b5eb64ae09af1dd0b3aa78945f4",
           ("all", "en"): "11dcb41719790e43a15013a435c3c6e67895a7cdb46ad54989f70dc9b24e99c0",
           ("le", "en"): "2960a91240f58023c86d8916c61a1bf5e266e5e8e6684e29fae0c017fb86f0ca"}


def test_sin_criterios_el_html_es_byte_a_byte_el_de_la_3c(tmp_path):
    (tmp_path / "b").mkdir()
    rs, sl = trb.todas(tmp_path / "b", iterations=100)
    les3c = rm.assess_le(tl.hojas(tmp_path, tl.merge(tl.fk_data(), tl.acads3b_data(registro="R-ZZSENT", kh=0.05),
                                                     {"Sismos": tl.seno()})))
    for lang in ("es", "en"):
        for name, res, kw in (("all", sl, dict(blocks=rs, le=les3c)), ("le", [], dict(le=les3c))):
            rep = rp.build_slope_report(res, title="T", lang=lang, figures=False, date="2026-11-04", criteria=None,
                                        profile_checks=None, **kw)
            h = rp.write_html(rep, tmp_path / f"{name}{lang}.html").read_text(encoding="utf-8")
            h = h.replace(rm.__version__, "VER")
            assert hashlib.sha256(h.encode()).hexdigest() == _GOLDEN[name, lang], (name, lang)


def test_claves_sin_repetir_y_en_los_dos_idiomas():
    import rockmasspy.report.texts as mod

    tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
    (d,) = [n for n in ast.walk(tree) if isinstance(n, ast.Dict) and len(n.keys) > 50]
    keys = [k.value for k in d.keys]
    assert len(keys) == len(set(keys))  # una clave repetida pisa a la primera en silencio
    for k in keys:
        assert set(REPORT_TEXTS[k]) == {"es", "en"} and all(REPORT_TEXTS[k].values()), k


# ---------------------------------------------------------------- el informe completo

@pytest.mark.parametrize("lang", ["es", "en"])
def test_nueve_secciones_en_su_orden(les, lang):
    rep = full(les, lang)
    assert [s.title for s in rep.sections] == [t(f"sx_{k}", lang) for k in range(1, 10)]
    assert rep.sections[2].blocks == (rp.Paragraph(t("sl_no_slopes", lang)),)
    assert rep.sections[3].blocks == (rp.Paragraph(t("crit_no_blocks", lang)),)
    assert rep.sections[4].blocks == rp._le_blocks(les, lang, False)
    assert rep.sections[8].blocks[-1] == rp.Paragraph(rp.DISCLAIMER[lang])
    assert {r[0] for r in rep.sections[8].blocks[0].rows} == {"Sarma-NonVertical"}


def test_sarma_en_la_tabla_de_equilibrio_limite(les):
    eq = table(full(les), "cap_le")
    assert len(eq.rows) == 4 and {r[3] for r in eq.rows} == {"Sarma (no vertical)"}
    ag = les[0]
    row = eq.rows[0]
    assert row[:3] == ("AG-ZZSENT", "SP4-ZZSENT", t("le_surf_sarma", "es"))
    assert row[4:] == ("0.050", f"{ag.sarma.factor_of_safety:.3f}", f"{ag.sarma_static.factor_of_safety:.3f}", "no",
                       "-", f"{ag.sarma.critical_acceleration:.3f}", "-")
    assert row[9] == f"{ag.ky:.3f}"  # ky es Kc


def test_resumen_ejecutivo_por_objeto(les):
    rep = full(les)
    s1 = rep.sections[0].blocks
    c = criteria_counts(checks_of(les))
    assert s1[0] == rp.Paragraph(t("crit_counts", "es").format(n=4, meets=1, fails=1, not_verifiable=2)) and \
        (c["meets"], c["fails"], c["not_verifiable"]) == (1, 1, 2)
    assert s1[1] == rp.Paragraph(t("crit_attention", "es").format(why=f"{t('rule_slope_fs_static', 'es')} (1)"))
    tab = table(rep, "cap_crit_summary")
    assert tab.header[-1] == t("rule_slope_fs_static", "es")
    ag, ab, an, ax = les
    assert tab.rows[0] == ("Equilibrio límite", "AG-ZZSENT", "global", "baja", f"{ag.sarma_static.factor_of_safety:.3f}",
                           f"{ag.sarma.factor_of_safety:.3f}", "-", "-", "no cumple")
    assert tab.rows[1][2:5] == ("banco", "alta", f"{ab.fs_min:.3f}") and tab.rows[1][-1] == "cumple"
    assert tab.rows[2][2:4] == ("-", "-") and tab.rows[2][-1] == "no verificable"
    assert tab.rows[3][-1] == "no verificable"


def test_alcance_criterios_y_marca_v2(les):
    s2 = full(les).sections[1].blocks
    prof = dict(table(full(les), "cap_crit_profile").rows)
    assert prof[t("h_id", "es")] == "READ-STACEY-2009" and prof[t("h_mark", "es")] == "V2"
    assert prof[t("h_force", "es")] == "guía" and prof[t("h_range_policy", "es")] == t("policy_conservative", "es")
    assert rp.Paragraph(t("crit_mark_V2", "es")) in s2 and rp.Paragraph(t("crit_mark_user", "es")) not in s2
    upper = dict(table(full(les, range_policy="lower"), "cap_crit_profile").rows)
    assert upper[t("h_range_policy", "es")] == t("policy_lower", "es")


def test_verificacion_una_fila_por_chequeo_y_normativa(les):
    rep = full(les)
    rows = table(rep, "cap_crit_checks").rows
    cs = checks_of(les)
    assert len(rows) == len(cs) == 4
    assert [r[4] for r in rows] == ["no cumple", "cumple", "no verificable", "no verificable"]
    assert rows[0][1:8] == ("AG-ZZSENT", "RS-FS-global-baja", t("rule_slope_fs_static", "es"), "no cumple", "≥ 1.3",
                            f"{les[0].sarma_static.factor_of_safety:.3f}", "upper of 1.2-1.3")
    assert rows[0][9:] == (cs[0].source, "guía", "V2")
    assert [r[8] for r in rows[2:]] == ["no scale assigned", "unknown scale"]
    (norm,) = table(rep, "cap_crit_normative").rows
    assert norm[:6] == ("Conjunto de análisis", "-", "PE-264", t("rule_pseudostatic_analysis_present", "es"), "cumple",
                        "≥ 100 años")
    assert norm[10:] == ("ley", "V1")
    s8 = rep.sections[7].blocks
    assert rp.Paragraph(t("crit_not_verifiable", "es").format(n=2)) in s8


def test_solo_perfil_normativo(les):
    pchecks = [c for c in checks_of(les, PE) if c.rule == "pseudostatic_analysis_present"]
    rep = rp.build_slope_report([], title="T", figures=False, le=les, profile_checks=pchecks)
    assert len(rep.sections) == 9 and rep.sections[0].blocks == (rp.Paragraph(t("crit_profile_only", "es")),)
    assert rep.sections[5].blocks == (rp.Paragraph(t("crit_profile_only", "es")),)
    assert table(rep, "cap_crit_normative").rows[0][4] == "cumple"
    with pytest.raises(ValueError, match="criteria_profile"):
        rp.build_slope_report([], title="T", le=les, criteria=[])


@pytest.mark.parametrize("lang", ["es", "en"])
def test_nunca_aprobado(les, tmp_path, lang):
    html = rp.write_html(full(les, lang), tmp_path / "x.html").read_text(encoding="utf-8")
    assert not re.search(r"aprob|approv", html, re.I)
    from rockmasspy.viz.style import TEXTS

    for d in (REPORT_TEXTS, TEXTS):
        assert not [k for k, v in d.items() if re.search(r"aprob|approv", " ".join(v.values()), re.I)]


def test_privacidad_html_word_y_figuras(les, tmp_path):
    rep = full(les, figures=True)
    html = rp.write_html(rep, tmp_path / "x.html").read_text(encoding="utf-8")
    celdas = re.findall(r"<td>([^<]*zzsent[^<]*)</td>", html, re.I)
    assert len(re.findall("zzsent", html, re.I)) == len(celdas) > 0  # solo en celdas de tabla
    assert {c for c in celdas} == {f"{k}-ZZSENT" for k in _ROWS} | {"SP4-ZZSENT", "glob-zzsent"}
    assert all(f.png for s in rep.sections for f in s.blocks if isinstance(f, rp.Figure))
    docx = pytest.importorskip("docx")
    d = docx.Document(str(rp.write_docx(rep, tmp_path / "x.docx")))
    assert not any(re.search("zzsent", p.text, re.I) for p in d.paragraphs)


# ---------------------------------------------------------------- CLI

def test_cli_le_paridad_con_el_informe_y_el_archivo(files, les, tmp_path, capsys):
    res, html = tmp_path / "c.csv", tmp_path / "x.html"
    code, out, err = run_le(capsys, files, "--criteria", "READ-STACEY-2009", "--criteria-output", res,
                            "--profile", "PE-DS024-2016", "--report", html, "--no-figures")
    lines = out.splitlines()
    assert code == 2 and "error:" not in err and S.casefold() not in (out + err).casefold()
    for ln in ("analyses: 4 (circular 0, block 0, given 0, sarma 4)", "FS at or below 1: 0 of 4",
               f"lowest FS: {min(r.fs_min for r in les):.3f} (Sarma-NonVertical)",
               "criteria: READ-STACEY-2009 (V2, guide)", "meets: 1, fails: 1, not verifiable: 2",
               "fails by rule: slope_fs_static (1)", "profile: PE-DS024-2016, PE-264: meets [law]",
               f"criteria results: {res}", f"report: {html}"):
        assert ln in lines, ln
    notes = next(i for i, ln in enumerate(lines) if ln.startswith("notes: "))
    assert notes + 1 == lines.index("criteria: READ-STACEY-2009 (V2, guide)")
    cs = checks_of(les)
    _, filas = tl.leer(res)
    assert [f["estado"] for f in filas] == ["no_cumple", "cumple", "no_verificable", "no_verificable"]
    assert [f["razon"] for f in filas[2:]] == ["no scale assigned", "unknown scale"]
    txt = html.read_text(encoding="utf-8")
    tab = txt.split(t("cap_crit_checks", "es"))[1].split("</table>")[0]
    n = criteria_counts(cs)
    for st, k in (("cumple", "meets"), ("no cumple", "fails"), ("no verificable", "not_verifiable")):
        assert tab.count(f"<td>{st}</td>") == n[k]
    assert sum(criteria_attention(cs).values()) == 1


def test_cli_no_verificable_no_cambia_el_codigo(tmp_path, capsys):
    f = tl.hojas(tmp_path, mezcla(("AB", "AN", "AX")))
    code, out, _ = run_le(capsys, f, "--criteria", "READ-STACEY-2009")
    assert code == 0 and "meets: 1, fails: 0, not verifiable: 2" in out.splitlines()
    assert "fails by rule" not in out
    code, out, _ = run_le(capsys, f, "--profile", "PE-DS024-2016")
    assert code == 0 and "profile: PE-DS024-2016, PE-264: not verifiable [law] (no scale assigned)" in out
    assert "criteria:" not in out


def test_cli_le_sin_sarma_no_cambia_el_resumen(tmp_path, capsys):
    f = tl.hojas(tmp_path, tl.fk_data())
    code, out, _ = run_le(capsys, f)
    assert "analyses: 1 (circular 1, block 0, given 0)" in out.splitlines() and "criteria" not in out


def test_cli_range_policy_y_tabla_propia(files, tmp_path, capsys):
    res = tmp_path / "c.csv"
    run_le(capsys, files, "--criteria", "READ-STACEY-2009", "--criteria-output", res, "--range-policy", "lower")
    _, (ag, *_) = tl.leer(res)
    assert (ag["requerido"], ag["rango_usado"], ag["estado"]) == ("1.2", "lower of 1.2-1.3", "no_cumple")
    from rockmasspy.criteria import CRITERIA_COLUMNS

    tabla = tmp_path / "mis_criterios.csv"
    tabla.write_text(",".join(CRITERIA_COLUMNS) + "\nglobal,baja,1.15,,,,Tabla ZZSENT\nbanco,*,1.5,,,,Tabla ZZSENT\n",
                     encoding="utf-8")
    html = tmp_path / "u.html"
    code, out, err = run_le(capsys, files, "--criteria", tabla, "--report", html, "--no-figures")
    assert code == 2 and "criteria: USER-TABLE (user, guide)" in out and "meets: 1, fails: 1, not verifiable: 2" in out
    assert S.casefold() not in (out + err).casefold()
    txt = html.read_text(encoding="utf-8")
    assert t("crit_mark_user", "es") in txt and t("crit_mark_V2", "es") not in txt
    assert txt.count("ZZSENT") == sum(c.count("ZZSENT") for c in re.findall(r"<td>([^<]*)</td>", txt))
    assert "<td>Tabla ZZSENT</td>" in txt  # la fuente de la tabla propia, una vez aunque la den dos filas


@pytest.mark.parametrize("extra,msg", [
    (["--criteria-output", "c.csv"], "--criteria-output needs --criteria"),
    (["--range-policy", "upper"], "--range-policy needs --criteria"),
    (["--criteria", "ZZSENT-perfil"], "--criteria: not a profile id"),
    (["--criteria", "READ-STACEY-2009", "--criteria-output", "c.txt"], "--criteria-output must end in .csv or .xlsx"),
    (["--profile", "READ-STACEY-2009"], "--profile: the profile has no pseudo-static analysis requirement"),
])
def test_cli_errores_una_sola_linea(files, capsys, extra, msg):
    code, out, err = run_le(capsys, files, *extra)
    assert code == 1 and out == "" and err.count("error:") == 1 and err.startswith(f"error: {msg}"), err
    assert S not in err


def test_cli_slope_bloques_con_criterios(tmp_path, capsys):
    import test_blocks as tb
    from test_cli import block_files, run_blocks

    jf, tf, bf, df = tb._todas(tmp_path)
    bf[0] = tb.B(**{**tb.PL1, "retroanalisis": "si", "escala": "banco", "consecuencia": "alta"})  # FS 0.818 < 1.1
    bf[-1] = tb.B(**{**tb.SMP, "escala": "Global", "consecuencia": "baja"})
    fs = block_files(tmp_path, jf, tf, bf, df)
    res, html = tmp_path / "c.xlsx", tmp_path / "b.html"
    code, out, err = run_blocks(capsys, fs, "--iterations", 200, "--criteria", "READ-STACEY-2009",
                                "--criteria-output", res, "--report", html, "--no-figures")
    assert code == 2 and "error:" not in err and "ZZSENT" not in out
    rs, _ = tb.correr(tmp_path, jf, tf, bf, df, iterations=200)
    cs = assess_criteria(RS, blocks=rs, assignments=criteria_assignments(blocks=rs))
    n = criteria_counts(cs)
    assert f"meets: {n['meets']}, fails: {n['fails']}, not verifiable: {n['not_verifiable']}" in out.splitlines()
    assert n["fails"] >= 1 and [f"fails by rule: {k} ({v})" for k, v in criteria_attention(cs).items()] ==         [ln for ln in out.splitlines() if ln.startswith("fails by rule: ")]
    openpyxl = pytest.importorskip("openpyxl")
    ws = openpyxl.load_workbook(res)["Criterios_resultados"]
    estados = [r[8] for r in ws.iter_rows(min_row=2, values_only=True)]
    assert estados.count("no_cumple") == n["fails"] and len(estados) == n["checks"]
    txt = html.read_text(encoding="utf-8")
    assert t("sx_4", "es") in txt and t("cap_crit_summary", "es") in txt
    code = main(["slope", "--faces", str(fs[0]), "--families", str(fs[1]), "--criteria", "READ-STACEY-2009"])
    assert code == 1 and capsys.readouterr().err.startswith("error: --criteria needs --blocks")


def test_help_lista_las_opciones_nuevas(capsys):
    for cmd, opts in (("slope", ("--criteria", "--criteria-output", "--range-policy")),
                      ("le", ("--criteria", "--criteria-output", "--range-policy", "--profile"))):
        with pytest.raises(SystemExit):
            main([cmd, "--help"])
        out = capsys.readouterr().out
        for o in opts:
            assert o in out, (cmd, o)


# ---------------------------------------------------------------- figura de Sarma

def test_figura_sarma_cunas_interfaces_fs_y_kc(tmp_path):
    pytest.importorskip("matplotlib")
    from matplotlib.text import Text

    from rockmasspy.viz import Style, plot_le_section
    from rockmasspy.viz.style import TEXTS

    (r,) = rm.assess_le(tl.hojas(tmp_path, p4_data(kh=0.05)))
    for lang in ("es", "en"):
        fig = plot_le_section(r, style=Style(lang=lang))
        fig.canvas.draw()
        txt = [x.get_text() for x in fig.findobj(Text) if x.get_text()]
        joined = " ".join(txt)
        for k in ("le_sarma_base", "le_sarma_interfaces"):
            assert TEXTS[k][lang] in joined
        assert f"{TEXTS['le_method_sarma'][lang]}: FS = {r.sarma.factor_of_safety:.3f}" in joined
        assert TEXTS["le_fs_static"][lang].format(fs=r.sarma_static.factor_of_safety) in joined
        assert f"Kc = {r.sarma.critical_acceleration:.3f}" in joined and "kh = 0.05" in joined
        assert "1" in txt and "2" in txt and S not in joined  # número de cada cuña, nunca un id
    ax = fig.axes[0]
    (inter,) = [ln for ln in ax.get_lines() if ln.get_linewidth() == 1.4]
    (x0, x1), (y0, y1) = inter.get_xdata(), inter.get_ydata()
    v = r.surface.polyline[1]
    assert (x0, y0) == pytest.approx((v.x, v.y))
    surf = list(r.section.surface)
    import numpy as np

    assert y1 == pytest.approx(np.interp(x1, [p.x for p in surf], [p.y for p in surf]), abs=1e-9)  # llega al terreno
    ang = np.degrees(np.arctan2(y1 - y0, x1 - x0))
    assert ang == pytest.approx(r.sarma.interface_angles_deg[0])
