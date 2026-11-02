import re

import pytest

import rockmasspy as rm

FAM_CAB = "id_tramo,familia,buzamiento_grados,dir_buzamiento_grados,codigo_mina,labor_codigo,este_m,observaciones"
TAL_CAB = ("id_talud,id_tramo,buz_cara_grados,dir_buz_cara_grados,friccion_grados,limite_lateral_grados,rmr_basico,"
           "excavacion,rqd_pct,jn,jr_a,ja_a,o_a,jwice,jr_b,ja_b,o_b,srf_a,srf_b,srf_c,"
           "codigo_mina,labor_codigo,este_m,observaciones")
EXTRA_F = ",ZZSENT,ZZSENT,ZZSENT,ZZSENT"
EXTRA_T = ",ZZSENT,ZZSENT,ZZSENT,ZZSENT"
RIQ = ["R1,J1,87,325", "R1,J2,20,119", "R1,J3,83,234", "R1,J4,62,62"]


def fam(tmp_path, filas, cab=FAM_CAB):
    p = tmp_path / "Familias.csv"
    p.write_text("\n".join([cab, *[f + EXTRA_F for f in filas]]) + "\n", encoding="utf-8")
    return p


def tal(tmp_path, filas, cab=TAL_CAB):
    p = tmp_path / "Taludes.csv"
    p.write_text("\n".join([cab, *[f + EXTRA_T for f in filas]]) + "\n", encoding="utf-8")
    return p


def T(id_="T1", tramo="R1", buz="72", dir_="133", fr="35", lim="", rmr="42", exc="voladura_normal",
      q=",,,,,", b=",,", srf=",,"):
    return f"{id_},{tramo},{buz},{dir_},{fr},{lim},{rmr},{exc},{q},{b},{srf}"


Q = "80,9,1.5,1,0.75,0.7"  # rqd, jn, jr_a, ja_a, o_a, jwice


def correr(tmp_path, tf, jf=RIQ, **kw):
    return rm.assess_slopes(rm.load_slope_faces(tal(tmp_path, tf)), rm.load_families(fam(tmp_path, jf)), **kw)


def test_riquelme_por_la_hoja(tmp_path):
    (r,) = correr(tmp_path, [T()])
    labels = [c.label for c in r.smr_cases]
    assert labels == ["J1", "J2", "J3", "J4", "J1×J2", "J1×J4", "J2×J3", "J2×J4", "J3×J4"]
    face = rm.PlaneOrientation(133, 72)
    # J1 y J3 vuelcan; J2 y J4 son planares (dirección dentro de 90 de la cara); las cuñas, por su intersección
    assert [c.mode for c in r.smr_cases[:4]] == ["toppling", "planar", "toppling", "planar"]
    assert r.smr_discrete.label == "J1" and r.smr_discrete.mode == "toppling"
    assert r.smr_discrete.discrete.smr == pytest.approx(24.5)
    assert r.smr_continuous.continuous.smr == pytest.approx(21.5, abs=0.5)
    esperado = min(c.discrete.smr for c in r.smr_cases)
    assert r.smr_discrete.discrete.smr == esperado
    assert r.smr_discrete is next(c for c in r.smr_cases if c.discrete.smr == esperado)
    assert r.smr_continuous.continuous.smr == min(c.continuous.smr for c in r.smr_cases)
    j1 = r.smr_cases[0]
    a = rm.smr_angles(rm.SmrMode.Toppling, r.families[0].mean_plane.dip_direction_deg,
                      r.families[0].mean_plane.dip_deg, face)
    exc = rm.SlopeExcavation.NormalBlastingOrMechanical
    assert j1.discrete.smr == rm.smr(42, rm.SmrMode.Toppling, rm.SmrFunctions.Discrete, exc, a).smr


def test_ida_y_vuelta_csv_y_excel(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    tf = [T(), T("T2", fr="", rmr="", exc="", q=Q, b="2,1,0.9", srf="2.5,,")]
    a = correr(tmp_path, tf)
    wb = openpyxl.Workbook()
    for nombre, cab, filas in (("Familias", FAM_CAB, [f + EXTRA_F for f in RIQ]),
                               ("Taludes", TAL_CAB, [t + EXTRA_T for t in tf])):
        ws = wb.create_sheet(nombre)
        for linea in [cab, *filas]:
            ws.append([None if c == "" else (float(c) if c.replace(".", "").isdigit() else c)
                       for c in linea.split(",")])
    del wb["Sheet"]
    wb.save(tmp_path / "x.xlsx")
    b = rm.assess_slopes(rm.load_slope_faces(tmp_path / "x.xlsx"), rm.load_families(tmp_path / "x.xlsx"))
    assert repr(a) == repr(b)  # los objetos del núcleo no definen igualdad
    assert [r.id_talud for r in a] == [r.id_talud for r in b] == ["T1", "T2"]
    assert [r.id_tramo for r in b] == ["R1", "R1"]
    assert a[1].q_slope is not None and a[1].q_slope.jr_ja_0 == b[1].q_slope.jr_ja_0 == pytest.approx(2.025)


def test_cinematica_igual_a_mano_y_limite_lateral(tmp_path):
    planes = [rm.PlaneOrientation(d, b) for b, d in ((87, 325), (20, 119), (83, 234), (62, 62))]
    face = rm.PlaneOrientation(133, 72)
    for celda, llamada, usado in (("", 25.0, 25.0), ("20", 25.0, 20.0)):
        (r,) = correr(tmp_path, [T(lim=celda)], lateral_limit_deg=llamada)
        k = rm.kinematic_analysis(planes, [0, 1, 2, 3], rm.KinematicInput(face, 35, usado))
        for c in ("planar", "planar_no_limits", "wedge_primary", "wedge_secondary", "flexural_toppling",
                  "direct_toppling", "direct_toppling_oblique", "n_intersections", "n_parallel_pairs"):
            assert getattr(r.kinematics, c) == getattr(k, c)
        assert r.kinematics.input.lateral_limit_deg == usado


def test_tramo_sin_familias(tmp_path):
    (r,) = correr(tmp_path, [T(tramo="R9")])
    assert r.kinematics is None and r.smr_cases == () and r.smr_discrete is None
    assert any("no Familias rows" in w for w in r.warnings) and r.needs_attention


def test_sin_friccion_avisa(tmp_path):
    (r,) = correr(tmp_path, [T(fr="")])
    assert r.kinematics is None and "kinematics not run: friccion_grados is empty" in r.warnings
    assert r.smr_cases  # el SMR no necesita fricción


def test_una_familia_y_familia_de_una_fila(tmp_path):
    (r,) = correr(tmp_path, [T()], jf=["R1,J1,60,133"])
    assert r.kinematics.n_intersections == 0 and len(r.smr_cases) == 1
    f = r.families[0].fisher
    assert f.n == 1 and f.kappa is None and f.alpha95_deg is None


def test_familias_paralelas_son_una_nota(tmp_path):
    (r,) = correr(tmp_path, [T()], jf=["R1,J1,60,133", "R1,J2,60,133"])
    assert r.kinematics.n_parallel_pairs == 1 and r.kinematics.n_intersections == 0
    assert r.notes and not [c for c in r.smr_cases if "×" in c.label]


def test_filas_sin_familia(tmp_path):
    (r,) = correr(tmp_path, [T()], jf=["R1,,60,133", "R1,,45,250"])
    assert [c.label for c in r.smr_cases][:2] == ["row 2", "row 3"] and r.families == ()


def test_modo_en_90_gobierna_el_menor(tmp_path):
    (r,) = correr(tmp_path, [T(dir_="0")], jf=["R1,J1,50,90"])
    c = r.smr_cases[0]
    exc = rm.SlopeExcavation.NormalBlastingOrMechanical
    smrs = [rm.smr(42, m, rm.SmrFunctions.Discrete, exc,
                   rm.smr_angles(m, r.families[0].mean_plane.dip_direction_deg,
                                 r.families[0].mean_plane.dip_deg, rm.PlaneOrientation(0, 72))).smr
            for m in (rm.SmrMode.Planar, rm.SmrMode.Toppling)]
    assert c.discrete.smr == min(smrs)


def test_q_slope_y_cara_igual_a_beta(tmp_path):
    q = Q
    (r,) = correr(tmp_path, [T(q=q, srf=",,2.5")])
    assert r.q_slope is not None and r.q_slope.beta_deg == pytest.approx(73.943, abs=1e-3)
    assert r.face_steeper_than_beta is False
    beta = r.q_slope.beta_deg
    (r,) = correr(tmp_path, [T(buz=repr(beta), q=q, srf=",,2.5")])
    assert r.face_steeper_than_beta is True and r.needs_attention
    (r,) = correr(tmp_path, [T(q=Q, b="2,1,0.9", srf="2.5,,")])
    assert r.q_slope.jr_ja_0 == pytest.approx(2.025)


def test_conteos_y_resultados(tmp_path):
    rs = correr(tmp_path, [T(), T("T2", fr="")])
    c = rm.slope_counts(rs)
    assert c["slopes"] == 2 and c["warnings"] == 1 and sum(c[f"smr_d_{k}"] for k in range(1, 6)) == 2
    p = rm.save_slope_results(rs, tmp_path / "out.csv")
    txt = p.read_text(encoding="utf-8-sig")
    from rockmasspy.slopes import _RESULT_COLUMNS
    assert re.split("[;,]", txt.splitlines()[0]) == list(_RESULT_COLUMNS) and "ZZSENT" not in txt
    assert "smr_caso_continuo" in _RESULT_COLUMNS
    assert len(txt.splitlines()) == 3


def test_methods(tmp_path):
    (r,) = correr(tmp_path, [T(q=Q, srf=",,2.5")])
    ids = [m.method_id for m in r.methods]
    assert len(set((m.method_id, m.source) for m in r.methods)) == len(r.methods)
    for mid in ("Fisher1953-set-statistics", "Kinematic-PlanarSliding", "Kinematic-WedgeSliding",
                "Kinematic-FlexuralToppling-Goodman1980", "Kinematic-DirectToppling-HudsonHarrison1997",
                "SMR-Romana1985", "Q-slope-BarBarton2017"):
        assert mid in ids


@pytest.mark.parametrize("fila,col", [
    (T(buz="95"), "buz_cara_grados"), (T(buz="0"), "buz_cara_grados"), (T(dir_="-5"), "dir_buz_cara_grados"),
    (T(dir_="400"), "dir_buz_cara_grados"), (T(dir_="nan"), "dir_buz_cara_grados"),
    (T(fr="0"), "friccion_grados"), (T(fr="90"), "friccion_grados"), (T(lim="0"), "limite_lateral_grados"),
    (T(lim="90"), "limite_lateral_grados"), (T(exc=""), "excavacion"), (T(exc="explosivo"), "excavacion"),
    (T(q="150,9,1.5,1,0.75,0.7", srf=",,2.5"), "rqd_pct"), (T(q="-5,9,1.5,1,0.75,0.7", srf=",,2.5"), "rqd_pct"),
    (T(q="80,0,1.5,1,0.75,0.7", srf=",,2.5"), "jn"), (T(q="80,9,-1,1,0.75,0.7", srf=",,2.5"), "jr_a"),
    (T(q="80,9,1.5,0,0.75,0.7", srf=",,2.5"), "ja_a"), (T(q="80,9,1.5,1,0,0.7", srf=",,2.5"), "o_a"),
    (T(q="80,9,1.5,1,0.75,0", srf=",,2.5"), "jwice"), (T(q=Q, srf=",,0"), "srf_c"),
    (T(rmr="101"), "rmr_basico"), (T(rmr="-1"), "rmr_basico"),
    (T(q=Q, b="2,1,", srf=",,2.5"), "o_b"), (T(q=Q), "srf_a"), (T(q="80,9,1.5,1,0.75,", srf=",,2.5"), "jwice"),
])
def test_hoja_mal_escrita(tmp_path, fila, col):
    with pytest.raises(ValueError) as e:
        rm.load_slope_faces(tal(tmp_path, [fila]))
    m = str(e.value)
    assert col in m and "Taludes" in m and "row 2" in m
    for v in ("95", "-5", "400", "nan", "explosivo", "150", "101"):
        assert v not in m.replace("row 2", "")


def test_id_talud_repetido_y_joints_mal(tmp_path):
    with pytest.raises(ValueError, match="duplicate id_talud"):
        rm.load_slope_faces(tal(tmp_path, [T(), T()]))
    for fila, col in (("R1,J1,95,10", "buzamiento_grados"), ("R1,J1,50,-5", "dir_buzamiento_grados"),
                      ("R1,J1,50,400", "dir_buzamiento_grados"), ("R1,J1,nan,10", "buzamiento_grados")):
        with pytest.raises(ValueError) as e:
            rm.load_families(fam(tmp_path, [fila]))
        assert col in str(e.value) and "row 2" in str(e.value) and "Familias" in str(e.value)
        assert "95" not in str(e.value) and "nan" not in str(e.value)


def test_privacidad(tmp_path):
    tf = [T("T-ZZSENT", "R-ZZSENT", fr="")]
    jf = ["R-ZZSENT,J1,60,133", "R-ZZSENT,J2,60,133"]
    faces = rm.load_slope_faces(tal(tmp_path, tf))
    joints = rm.load_families(fam(tmp_path, jf))
    rs = rm.assess_slopes(faces, joints)
    for o in (*faces, *joints, *rs):
        assert "ZZSENT" not in repr(o)
    assert not any("ZZSENT" in s for r in rs for s in (*r.warnings, *r.notes))
    txt = rm.save_slope_results(rs, tmp_path / "o.csv").read_text(encoding="utf-8-sig")
    assert "T-ZZSENT" in txt and "R-ZZSENT" in txt and txt.count("ZZSENT") == 2
    with pytest.raises(ValueError) as e:
        rm.load_slope_faces(tal(tmp_path, [T("T-ZZSENT", "R-ZZSENT", buz="95")]))
    assert "ZZSENT" not in str(e.value)


def test_eje_vertical_sin_lado(tmp_path):
    # un plano vertical anotado de los dos lados da el mismo SMR (el menos favorable)
    r = [correr(tmp_path, [T(dir_="0", buz="72")], jf=[f"R1,,90,{d}"])[0] for d in (0, 180)]
    assert r[0].smr_discrete.discrete.smr == r[1].smr_discrete.discrete.smr
    assert r[0].smr_discrete.discrete.smr_class == r[1].smr_discrete.discrete.smr_class == 5
    assert r[0].smr_discrete.discrete.smr == pytest.approx(17)


@pytest.mark.parametrize("giro", [0, 45, 90, 180, 270])
@pytest.mark.parametrize("planos", [
    [(90, 0), (90, 90)],                 # intersección vertical
    [(40, 0), (40, 180)],                # intersección horizontal
    [(87, 325), (20, 119), (83, 234), (62, 62)],
    [(60, 20), (70, 100), (50, 200)],
])
def test_giro_no_cambia_el_smr(tmp_path, giro, planos):
    def corre(g):
        jf = [f"R1,,{b},{(d + g) % 360}" for b, d in planos]
        return correr(tmp_path, [T(dir_=str((133 + g) % 360))], jf=jf)[0]
    a, b = corre(0), corre(giro)
    assert b.smr_discrete.discrete.smr == pytest.approx(a.smr_discrete.discrete.smr)
    assert b.smr_continuous.continuous.smr == pytest.approx(a.smr_continuous.continuous.smr)
    assert len(a.smr_cases) == len(b.smr_cases)


@pytest.mark.parametrize("cara", [90, 270])
def test_cuna_horizontal_con_cara_a_90_y_270(tmp_path, cara):
    (r,) = correr(tmp_path, [T(dir_=str(cara))], jf=["R1,J1,40,0", "R1,J2,40,180"])
    assert [c.label for c in r.smr_cases] == ["J1", "J2", "J1×J2"]


def test_alpha95_indefinido_avisa(tmp_path):
    # polos muy dispersos: no hay alpha95
    jf = ["R1,J1,90,180", "R1,J1,90,270"]
    (r,) = correr(tmp_path, [T()], jf=jf)
    assert r.families[0].fisher.alpha95_deg is None
    assert any(w.startswith("J1: ") and "alpha95" in w for w in r.warnings) and r.needs_attention


def test_avisos_de_familia_no_se_juntan(tmp_path):
    jf = ["R1,J1,90,180", "R1,J1,90,270", "R1,J2,90,180", "R1,J2,90,270"]
    (r,) = correr(tmp_path, [T()], jf=jf)
    ws = [w for w in r.warnings if "alpha95" in w]
    assert any(w.startswith("J1: ") for w in ws) and any(w.startswith("J2: ") for w in ws)


def test_excavacion_a_mano_fuera_de_vocabulario():
    from rockmasspy.slopes import SlopeFace
    f = SlopeFace("T", "R", 72, 133, None, None, 42, "explosivo-ZZSENT", *[None] * 12, 2)
    j = rm.JointRecord("R", "J1", 60, 133, 2)
    with pytest.raises(ValueError, match="one of") as e:
        rm.assess_slopes([f], [j])
    assert "ZZSENT" not in str(e.value) and "row 2" in str(e.value)


def test_nota_planar_sin_limites(tmp_path):
    # J1 está fuera del límite lateral de 30 pero dentro sin límites
    (r,) = correr(tmp_path, [T(dir_="0", buz="70")], jf=["R1,J1,50,60"])
    k = r.kinematics
    assert k.planar_no_limits > k.planar
    assert f"planar count without lateral limits is higher ({k.planar_no_limits} vs {k.planar})" in r.notes
    (r,) = correr(tmp_path, [T(dir_="0", buz="70")], jf=["R1,J1,50,10"])
    assert not any("without lateral limits" in n for n in r.notes)


def test_eje_vertical_discreto_y_continuo_cada_uno_su_lado(tmp_path):
    # cara 0/90 y plano vertical 90/0: los dos sentidos empatan en el discreto (35) y difieren en el continuo
    face = rm.PlaneOrientation(0, 90)
    exc = rm.SlopeExcavation.NormalBlastingOrMechanical
    cont = []
    for d, m in ((0, rm.SmrMode.Planar), (180, rm.SmrMode.Toppling)):
        a = rm.smr_angles(m, d, 90, face)
        cont.append(rm.smr(42, m, rm.SmrFunctions.Continuous, exc, a).smr)
    assert abs(cont[0] - cont[1]) > 0.5
    (r,) = correr(tmp_path, [T(dir_="0", buz="90")], jf=["R1,,90,0"])
    assert r.smr_continuous.continuous.smr == pytest.approx(min(cont))


# --- revisión final de la 3A ---

def _cara(dd, dip, rmr=60.0):
    from rockmasspy.slopes import SlopeFace
    return SlopeFace("T1", "R1", dip, dd, 30.0, None, rmr, "voladura_normal", *[None] * 12, 2)


def _filas(spec):
    return [rm.JointRecord("R1", fam, dip, dd, i + 2) for i, (fam, dd, dip) in enumerate(spec)]


def _uno(cara, spec):
    return rm.assess_slopes([cara], _filas(spec))[0]


def test_media_de_fisher_en_el_limite_toma_la_clase_peor():
    # familia de tres filas paralela a la cara (C = 0) y familia de una fila con C = -10, RMRb 60
    r = _uno(_cara(7, 60), [("J1", 7, 60)] * 3)
    assert r.smr_discrete.discrete.smr == pytest.approx(35.0) and r.smr_discrete.discrete.smr_class == 4
    r = _uno(_cara(0, 40), [("J1", 0, 30)])
    assert r.smr_discrete.discrete.smr == pytest.approx(18.0) and r.smr_discrete.discrete.smr_class == 5


def test_barrido_de_limites_c_con_familia_de_una_fila():
    malos = 0
    for dd in range(360):
        for dip in (40.0, 50.0, 60.0, 70.0):
            for jdip, f3 in ((dip, -25), (dip - 10, -60), (dip + 10, -6)):
                malos += _uno(_cara(dd, dip), [("J1", dd, jdip)]).smr_cases[0].discrete.f3 != f3
    assert malos == 0  # de 4320 casos


def test_barrido_de_limites_a_b_y_vuelco():
    malos = 0
    for dd in range(0, 360, 3):
        for a, f1 in {5: 1.0, 10: 0.85, 20: 0.70, 30: 0.40}.items():
            malos += _uno(_cara(dd, 75), [("J1", (dd + a) % 360, 50.0)]).smr_cases[0].discrete.f1 != f1
        for b, f2 in {20: 0.40, 30: 0.70, 35: 0.85, 45: 1.00}.items():
            malos += _uno(_cara(dd, 75), [("J1", dd, float(b))]).smr_cases[0].discrete.f2 != f2
        for jdip, f3 in ((50.0, -6), (60.0, -25)):  # vuelco con C = 110 y C = 120
            malos += _uno(_cara(dd, 60), [("J1", (dd + 180) % 360, jdip)]).smr_cases[0].discrete.f3 != f3
    assert malos == 0


@pytest.mark.parametrize("familia", [None, "J1"])
def test_plano_horizontal_no_depende_de_la_cara_ni_de_la_notacion(familia):
    rs = [_uno(_cara(g, 60, rmr=69.0), [(familia, d, 0.0)] * (2 if familia else 1))
          for g in (0, 90, 180, 270) for d in (0, 180)]
    assert len({round(r.smr_discrete.discrete.smr, 9) for r in rs}) == 1
    assert len({round(r.smr_continuous.continuous.smr, 9) for r in rs}) == 1
    assert rs[0].smr_discrete.discrete.smr == pytest.approx(60.0)  # planar con A = 0: 1 · 0.15 · (-60)


@pytest.mark.parametrize("giro", [45, 90, 180, 270])
def test_giro_no_cambia_el_smr_con_familias(giro):
    planos = [("J1", 20, 60), ("J1", 25, 62), ("J2", 100, 70), ("J2", 105, 68), ("J3", 200, 50), (None, 300, 40)]

    def corre(g):
        return _uno(_cara((133 + g) % 360, 72), [(f, (d + g) % 360, b) for f, d, b in planos])
    a, b = corre(0), corre(giro)
    assert b.smr_discrete.discrete.smr == pytest.approx(a.smr_discrete.discrete.smr)
    assert b.smr_continuous.continuous.smr == pytest.approx(a.smr_continuous.continuous.smr)
    assert [c.label for c in a.smr_cases] == [c.label for c in b.smr_cases]
    assert [c.discrete.smr for c in a.smr_cases] == pytest.approx([c.discrete.smr for c in b.smr_cases])


@pytest.mark.parametrize("lim", [95.0, 0.0, float("nan")])
def test_limite_lateral_de_la_api_no_se_atribuye_a_la_hoja(lim):
    with pytest.raises(ValueError) as e:
        rm.assess_slopes([_cara(133, 72)], _filas([("J1", 133, 60)]), lateral_limit_deg=lim)
    m = str(e.value)
    assert "lateral_limit_deg" in m and "row" not in m and "sheet" not in m and "95" not in m


def test_muchas_filas_sueltas_dejan_nota():
    def notas(n):
        return _uno(_cara(133, 72), [(None, (7 * i) % 360, 20 + i % 60) for i in range(n)])
    assert not any("loose rows" in x for x in notas(30).notes)
    r = notas(31)
    k = sum(c.mode == "wedge" for c in r.smr_cases)
    assert f"31 loose rows produce {k} wedge cases; group them into families" in r.notes
    assert not r.warnings or all("loose" not in w for w in r.warnings)
