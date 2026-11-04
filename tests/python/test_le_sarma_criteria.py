"""Sarma en la hoja `Analisis_LE`, escala y consecuencia por análisis y art. 264 (fase 3D, tarea 3). Solo sintéticos."""
import pytest

import rockmasspy as rm
from rockmasspy import blocks as bk
from rockmasspy import limit_equilibrium as le
from rockmasspy import verify as V
from rockmasspy.cli import main
from rockmasspy.criteria import assess_criteria, criteria_assignments, return_periods
from rockmasspy.normative import get_profile

from test_limit_equilibrium import G, L, acads3b_data, ana, hojas, leer, libro, mat, merge, seno
from test_sarma_core import P4_BASE, P4_FLOOR, P4_SURFACE

SEC = "SP4-ZZSENT"
PE = get_profile("PE-DS024-2016")
RS = get_profile("READ-STACEY-2009")


def p4_data(**an):
    """Problema 4 de Slide Sarma (Hoek 1987) por la hoja: desmonte sobre un piso cizallado, interfaz leída a 116.5°."""
    return {"Geometria": (G(SEC, "superficie", P4_SURFACE) + G(SEC, "piso-ZZSENT", P4_FLOOR)
                          + G(SEC, "F-ZZSENT", P4_BASE)),
            "Estratos": [L(SEC, 1, "MD-ZZSENT", "piso-ZZSENT"), L(SEC, 2, "MP-ZZSENT")],
            "Materiales_LE": [mat(material="MD-ZZSENT", modelo="mohr_coulomb", peso_unitario_kn_m3=15.7,
                                  cohesion_kpa=100, friccion_grados=42),
                              mat(material="MP-ZZSENT", modelo="mohr_coulomb", peso_unitario_kn_m3=15.7,
                                  cohesion_kpa=10, friccion_grados=6)],
            "Analisis_LE": [ana(**{"id_analisis": "AP4-ZZSENT", "id_seccion": SEC, "superficie": "sarma",
                                   "linea_superficie": "F-ZZSENT", "sarma_angulos": "116.5", **an})]}


def core_fs(angles=(116.5,), optimize=False, kh=0.0):
    from test_sarma_core import problem4, sarma_in

    s = problem4()
    s.kh = kh
    o = rm.SarmaOptions()
    o.optimize_angles = optimize
    return rm.sarma_fs(s, sarma_in(P4_BASE, angles), o)


def test_problema4_por_la_hoja(tmp_path):
    (r,) = rm.assess_le(hojas(tmp_path, p4_data()))
    want = core_fs()
    assert r.surface_type == "sarma" and r.results == () and r.sarma is not None
    assert r.fs_min == want.factor_of_safety == pytest.approx(1.1977, abs=2e-3)
    assert r.ky == want.critical_acceleration and r.yield_ is None and r.newmark is None
    assert le.le_static_fs(r) == le.le_fs(r) == [want.factor_of_safety]
    assert [m.method_id for m in r.methods] == ["Sarma-NonVertical"]
    assert le.le_counts([r])["sarma"] == 1 and le.le_counts([r])["with_fs"] == 1
    (b,) = rm.assess_le(libro(tmp_path, p4_data()))
    assert b.fs_min == r.fs_min and repr(b) == repr(r)


def test_vacio_es_90_y_opt_optimiza(tmp_path):
    (r90,) = rm.assess_le(hojas(tmp_path, p4_data(sarma_angulos="")))
    assert r90.fs_min == core_fs((90.0,)).factor_of_safety and list(r90.sarma.interface_angles_deg) == [90.0]
    (ro,) = rm.assess_le(hojas(tmp_path, p4_data(sarma_angulos="OPT")))
    assert ro.fs_min == core_fs((90.0,), optimize=True).factor_of_safety
    assert ro.fs_min <= r90.fs_min and ro.fs_min <= core_fs().factor_of_safety + 1e-9
    assert 100 < ro.sarma.interface_angles_deg[0] < 130


def test_metodos_se_ignora_con_nota(tmp_path):
    (r,) = rm.assess_le(hojas(tmp_path, p4_data(metodos="bishop;ZZSENT")))
    assert "metodos does not apply to Sarma; ignored" in r.notes and r.fs_min == core_fs().factor_of_safety
    (r,) = rm.assess_le(hojas(tmp_path, p4_data()))
    assert not any("metodos" in n for n in r.notes)


def test_kh_estatico_sobre_las_mismas_cunas_y_newmark_con_kc(tmp_path):
    data = merge(p4_data(kh=0.05, sarma_angulos="opt", registro="R-ZZSENT"), {"Sismos": seno(amp=0.4)})
    (r,) = rm.assess_le(hojas(tmp_path, data))
    ang = list(r.sarma.interface_angles_deg)
    static = core_fs(ang)
    assert le.le_static_fs(r) == [static.factor_of_safety] and r.fs_min < static.factor_of_safety
    assert r.fs_min == core_fs((90.0,), optimize=True, kh=0.05).factor_of_safety
    assert "static FS: Sarma with kh = 0 on the same wedges" in r.notes
    assert r.ky == r.sarma.critical_acceleration > 0
    ni = rm.NewmarkInput()
    acc = le.read_accelerogram(hojas(tmp_path, {"Sismos": seno(amp=0.4)})["Sismos"])["R-ZZSENT"]
    ni.dt_s, ni.acceleration_g, ni.ky, ni.both_directions = acc.dt_s, list(acc.acceleration_g), r.ky, True
    assert r.newmark.displacement_m == rm.newmark_rigid_block(ni).displacement_m > 0
    pytest.importorskip("matplotlib")
    from rockmasspy import report as rp
    assert rp.newmark_figure(r, "es") is not None  # en Sarma el ky es Kc (yield_ es None); antes se caía


def test_archivo_de_resultados_una_fila_sarma(tmp_path):
    data = p4_data(kh=0.05)
    (r,) = rm.assess_le(hojas(tmp_path, data))
    cab, (f,) = leer(le.save_le_results([r], tmp_path / "res.csv"))
    assert cab == list(le.RESULT_COLUMNS)  # R9: la forma no cambia
    assert (f["superficie"], f["metodo"], f["kh"]) == ("sarma", "sarma", "0.05")
    assert float(f["fs"]) == pytest.approx(r.fs_min) and float(f["fs_estatico"]) == pytest.approx(1.1977, abs=2e-3)
    assert float(f["ky"]) == pytest.approx(r.ky) and f["fs_menor_o_igual_1"] == "no"
    assert all(f[c] == "" for c in ("lambda", "convergio", "xc_m", "yc_m", "radio_m", "evaluadas", "descartadas",
                                     "desplazamiento_newmark_m"))
    assert f["puntos_superficie"].count(";") == len(P4_BASE) - 1
    assert "ZZSENT" not in f["avisos"] + f["notas"]


@pytest.mark.parametrize("angulos,motivo", [
    ("abc-ZZSENT", "must be a ';'-separated list of angles in degrees, or 'opt'"),
    ("116.5;", "must be a ';'-separated list of angles in degrees, or 'opt'"),
    ("nan", "must be a ';'-separated list of angles in degrees, or 'opt'"),
    ("100;110", "give one angle per interior vertex of linea_superficie"),
    ("180", "each angle must be within (0, 180)"),
    ("0", "each angle must be within (0, 180)"),
])
def test_sarma_angulos_mal_escritos(tmp_path, angulos, motivo):
    with pytest.raises(ValueError) as e:
        rm.assess_le(hojas(tmp_path, p4_data(sarma_angulos=angulos)))
    m = str(e.value)
    assert m == f"sheet 'Analisis_LE', row 2, column 'sarma_angulos': {motivo}", m
    assert not any(x in m for x in ("ZZSENT", "116", "110", "abc")), m


def test_sarma_angulos_solo_en_sarma_y_metodos_exigido_fuera(tmp_path):
    with pytest.raises(ValueError, match=r"^sheet 'Analisis_LE', row 2, column 'sarma_angulos': only for superficie"):
        rm.assess_le(hojas(tmp_path, acads3b_data(sarma_angulos="90")))
    with pytest.raises(ValueError, match=r"^sheet 'Analisis_LE', row 2, column 'metodos': required value is empty"):
        rm.assess_le(hojas(tmp_path, p4_data(superficie="dada", sarma_angulos="")))


def test_sarma_no_soportado_con_hoja_y_fila(tmp_path):
    with pytest.raises(ValueError, match=r"^sheet 'Analisis_LE', row 2: .*not supported in Sarma"):
        rm.assess_le(hojas(tmp_path, p4_data(grieta_m=5)))
    with pytest.raises(ValueError, match=r"^sheet 'Analisis_LE', row 2: .*inadmissible mechanism at interface 0"):
        rm.assess_le(hojas(tmp_path, p4_data(sarma_angulos="60")))


# ---------------------------------------------------------------- escala, consecuencia y período de retorno


def test_escala_y_consecuencia_por_analisis(tmp_path):
    (r,) = rm.assess_le(hojas(tmp_path, p4_data(escala=" Global ", consecuencia="ALTA", periodo_retorno_anios=475)))
    assert (r.escala, r.consecuencia, r.periodo_retorno_anios) == ("global", "alta", 475.0)
    assert "global" not in repr(r) and "475" not in repr(r)
    assert criteria_assignments(le=[r]) == {("le", "AP4-ZZSENT"): ("global", "alta")}
    assert return_periods([r]) == {"AP4-ZZSENT": 475.0}
    (c,) = [x for x in assess_criteria(RS, le=[r], assignments=criteria_assignments(le=[r]))
            if x.rule == "slope_fs_static"]
    assert c.status == "fails" and c.obtained == r.fs_min  # 1.198 < 1.5 (rango 1.30-1.50, extremo alto)
    (r,) = rm.assess_le(hojas(tmp_path, p4_data()))
    assert (r.escala, r.consecuencia, r.periodo_retorno_anios) == (None, None, None)
    assert {x.status for x in assess_criteria(RS, le=[r], assignments=criteria_assignments(le=[r]))} == \
        {"not_verifiable"}
    with pytest.raises(ValueError, match=r"column 'periodo_retorno_anios': out of range"):
        rm.assess_le(hojas(tmp_path, p4_data(periodo_retorno_anios=0)))


def test_escala_sin_lista_al_leer_la_valida_assess_criteria(tmp_path):
    (r,) = rm.assess_le(hojas(tmp_path, p4_data(escala="ZZSENT")))
    assert r.escala == "zzsent"
    cs = assess_criteria(RS, le=[r], assignments=criteria_assignments(le=[r]))
    assert [(c.status, c.reason) for c in cs] == [("not_verifiable", "unknown scale")]
    pe = assess_criteria(PE, le=[r], assignments=criteria_assignments(le=[r]), return_periods=return_periods([r]))
    assert [(c.item_id, c.status, c.reason) for c in pe] == [("PE-264", "not_verifiable", "unknown scale")]


def test_cli_verify_escala_mal_escrita_no_verificable(tmp_path, capsys):
    x = libro(tmp_path, p4_data(kh=0.05, escala="glob-ZZSENT", periodo_retorno_anios=100))
    assert main(["verify", "--profile", "PE-DS024-2016", "--as-of", "2026-11-04", "--le", str(x)]) == 0
    cap = capsys.readouterr()
    assert "error:" not in cap.err and "ZZSENT" not in cap.out + cap.err
    assert "not verifiable by the library: " in cap.out
    v = V.verify(PE, as_of="2026-11-04", le=rm.assess_le(x))
    assert _pe264(v) == ("not_verifiable", "unknown scale")


def test_bloques_ganan_escala_y_consecuencia():
    rows = [{c: None for c in bk.BLOCK_COLUMNS} | dict(id_bloque=f"B{k}-ZZSENT", id_talud="T-ZZSENT", modelo=m,
                                                         altura_banco_m=10, ancho_berma_m=8, **extra)
            for k, (m, extra) in enumerate([("berma", dict(escala="Banco", consecuencia=" media ")),
                                            ("berma", {})])]
    b1, b2 = (bk._block(dict(v), k + 2, "Bloques") for k, v in enumerate(rows))
    assert (b1.escala, b1.consecuencia, b2.escala, b2.consecuencia) == ("banco", "media", None, None)
    r1 = bk.BlockResult("B1", "T", 1, "berm", None, None, None, None, (), (), (), escala="banco", consecuencia="media")
    r2 = bk.BlockResult("B2", "T", 2, "planar", None, None, None, None, (), (), ())
    assert criteria_assignments(blocks=[r1, r2]) == {("berm", "B1"): ("banco", "media"), ("block", "B2"): (None, None)}
    assert "banco" not in repr(r1)


# ---------------------------------------------------------------- art. 264 en verify


def _pe264(v):
    (f,) = [x for x in v.findings if x.item.item_id == "PE-264"]
    return f.status, f.message


def test_pe264_sin_le_sigue_no_verificable():
    item = PE.version("PE-264", "2026-11-04")
    assert (item.check, item.value, item.comparison, item.unit) == ("pseudostatic_analysis_present", 100, ">=",
                                                                   "years")
    assert _pe264(V.verify(PE, as_of="2026-11-04")) == ("not_verifiable", "no limit equilibrium analyses given")


def test_pe264_con_le(tmp_path):
    def run(**an):
        rs = rm.assess_le(hojas(tmp_path, p4_data(**an)))
        return _pe264(V.verify(PE, as_of="2026-11-04", le=rs))

    st, msg = run(kh=0.05, escala="global", consecuencia="alta", periodo_retorno_anios=100)
    assert st == "complies" and ">= 100 years" in msg
    assert run(kh=0.05, escala="global", periodo_retorno_anios=50)[0] == "does_not_comply"  # ley
    assert run(escala="global", periodo_retorno_anios=100)[0] == "does_not_comply"  # sin kh
    assert run(kh=0.05, escala="global") == ("not_verifiable",
                                            "return period not given for a pseudo-static overall analysis")
    assert run(kh=0.05, periodo_retorno_anios=100) == ("not_verifiable", "no scale assigned")
    v = V.verify(PE, as_of="2026-11-04", le=rm.assess_le(hojas(tmp_path, p4_data(kh=0.05, escala="global",
                                                                                 periodo_retorno_anios=50))))
    assert v.exit_code == 2


def test_cli_verify_con_le(tmp_path, capsys):
    h = hojas(tmp_path, p4_data(kh=0.05, escala="global", periodo_retorno_anios=50))
    csvs = ["--geometry", h["Geometria"], "--layers", h["Estratos"], "--materials", h["Materiales_LE"],
            "--analyses", h["Analisis_LE"]]
    code = main(["verify", "--profile", "PE-DS024-2016", "--as-of", "2026-11-04", *map(str, csvs)])
    out = capsys.readouterr().out
    assert code == 2 and "does not comply: art. 264 [law]" in out and "ZZSENT" not in out
    x = libro(tmp_path, p4_data(kh=0.05, escala="global", periodo_retorno_anios=100))
    assert main(["verify", "--profile", "PE-DS024-2016", "--as-of", "2026-11-04", "--le", str(x)]) == 0
    assert "art. 264" not in capsys.readouterr().out
    assert main(["verify", "--profile", "PE-DS024-2016", "--le", str(x), "--analyses", str(h["Analisis_LE"])]) == 1
    assert "error: --le goes alone; drop --analyses" in capsys.readouterr().err
    assert main(["verify", "--profile", "PE-DS024-2016", "--analyses", str(h["Analisis_LE"])]) == 1
    assert "error: give --le, or --geometry" in capsys.readouterr().err
