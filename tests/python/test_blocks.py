import csv
import math
import re
from types import SimpleNamespace

import pytest

import rockmasspy as rm
from rockmasspy import blocks as bk
from rockmasspy.probabilistic import exponential, normal, run_probabilistic

from test_slopes import T, fam, tal

EXTRA = ",ZZSENT,ZZSENT,ZZSENT,ZZSENT"
EXTRA_CAB = ",codigo_mina,labor_codigo,este_m,observaciones"
DIS_CAB = "id_bloque,variable,distribucion,media,desviacion,minimo,maximo"


def B(**kw):
    """Una fila de `Bloques` en el orden de BLOCK_COLUMNS; lo que no se da queda vacío."""
    return ",".join(str(kw.get(c, "")) for c in bk.BLOCK_COLUMNS) + EXTRA


def D(id_, var, dist, media="", desv="", mn="", mx=""):
    return f"{id_},{var},{dist},{media},{desv},{mn},{mx}" + EXTRA


def hoja(tmp_path, nombre, cab, filas):
    p = tmp_path / f"{nombre}.csv"
    p.write_text("\n".join([cab + EXTRA_CAB, *filas]) + "\n", encoding="utf-8")
    return p


def leer(p):
    txt = p.read_text(encoding="utf-8-sig")
    sep = ";" if ";" in txt.splitlines()[0] else ","
    cab, *filas = list(csv.reader(txt.splitlines(), delimiter=sep))
    return cab, [dict(zip(cab, f)) for f in filas]


def blq(tmp_path, filas):
    return hoja(tmp_path, "Bloques", ",".join(bk.BLOCK_COLUMNS), filas)


def dis(tmp_path, filas):
    return hoja(tmp_path, "Distribuciones", DIS_CAB, filas)


def talud(id_="T1", tramo="R1", buz="50", dir_="180", **kw):
    return T(id_, tramo, buz, dir_, **{"fr": "", "rmr": "", "exc": "", **kw})


def correr(tmp_path, jf, tf, bf, df=(), **kw):
    slopes = rm.assess_slopes(rm.load_slope_faces(tal(tmp_path, tf)), rm.load_families(fam(tmp_path, jf)))
    dists = rm.load_distributions(dis(tmp_path, df)) if df else ()
    return rm.assess_blocks(rm.load_blocks(blq(tmp_path, bf)), slopes, dists, **kw), slopes


# PL-1 (Sau Mau Ping) pasado a kN: el FS no cambia
PL1 = dict(id_bloque="B1", id_talud="T1", modelo="planar", altura_m=60, peso_unitario_kn_m3=27, peso_agua_kn_m3=10,
           familia_1="J1", cohesion_1_kpa=100, friccion_1_grados=35, kh=0.08, llenado_agua=1)
J35 = ["R1,J1,35,180"] * 3
# CU-2 (Priest ej. 1) en kN y kPa
CU2_J = ["R1,J1,47,203", "R1,J2,52,287"]
CU2 = dict(id_bloque="C1", id_talud="T1", modelo="cuña", altura_m=6.7978, peso_unitario_kn_m3=26, familia_1="J1",
           familia_2="J2", cohesion_1_kpa=10, friccion_1_grados=40, cohesion_2_kpa=20, friccion_2_grados=35,
           presion_1_kpa=5, presion_2_kpa=15, carga_kn=180, carga_tendencia_grados=168, carga_inmersion_grados=70,
           buz_sup_grados=5, dir_sup_grados=225)
# VO-1 (Goodman y Bray 1976, ej. 1d)
VO1 = dict(id_bloque="V1", id_talud="T1", modelo="volteo", peso_unitario_kn_m3=25, friccion_1_grados=38.66,
           ancho_bloque_m=10, buz_base_grados=30, a1_m=5, a2_m=5, b_m=1, n_bloques=16, bloque_cresta=10,
           soporte_kn_m=2013)
BERMA = dict(id_bloque="M1", id_talud="T1", modelo="berma", altura_banco_m=12, ancho_berma_m=10.0)
# Sau Mau Ping probabilístico (Hoek 2023, cap. 9) con t pasadas a kN (× 9.81): cada FS queda igual
G = 9.81
SMP = dict(id_bloque="S1", id_talud="T1", modelo="planar", altura_m=60, peso_unitario_kn_m3=2.6 * G,
           peso_agua_kn_m3=1.0 * G, familia_1="J1", cohesion_1_kpa=10 * G, friccion_1_grados=35, dist_grieta_m=15.3,
           llenado_agua=0.5, kh=0.08)
SMP_D = [D("S1", "friccion_1_grados", "normal", 35, 5, 15, 70),
         D("S1", "cohesion_1_kpa", "normal", 10 * G, 2 * G, 0, 25 * G),
         D("S1", "dist_grieta_m", "normal", 15.3, 4, 0, 35.3429),
         D("S1", "llenado_agua", "exponencial", 0.5, "", 0, 1),
         D("S1", "kh", "exponencial", 0.08, "", 0, 0.16)]


def test_planar_por_la_hoja(tmp_path):
    (r,), _ = correr(tmp_path, J35, [talud()], [B(**PL1, retroanalisis="si")])
    assert r.model == "planar" and r.order == 1
    assert r.fs == pytest.approx(0.818425, abs=1e-6)
    assert r.deterministic.formed
    b = r.back_analysis
    assert list(b.friction_deg) == [10, 15, 20, 25, 30, 35, 40, 45, 50] and len(b.cohesion) == 9
    assert b.friction_at_zero_cohesion_deg == pytest.approx(70.5924, abs=1e-4)
    assert r.warnings == () and r.needs_attention  # FS < 1
    assert bk.block_attention(r) == ["att_fs_below_1"]


def test_cuna_por_la_hoja(tmp_path):
    (r,), _ = correr(tmp_path, CU2_J, [talud(buz="60", dir_="230")], [B(**CU2)])
    assert r.model == "wedge" and r.fs == pytest.approx(1.4966, abs=1e-4)
    assert r.deterministic.mode == rm.WedgeMode.TwoPlanes
    assert r.deterministic.volume == pytest.approx(45.201, abs=1e-3)
    assert not r.needs_attention


def test_volteo_por_la_hoja(tmp_path):
    (r,), _ = correr(tmp_path, J35, [talud()], [B(**VO1)])
    assert r.model == "toppling" and r.fs == pytest.approx(1.231, abs=1e-3)


def test_berma_por_la_hoja(tmp_path):
    rs, _ = correr(tmp_path, J35, [talud(buz="65")],
                   [B(**BERMA), B(**{**BERMA, "id_bloque": "M2", "ancho_requerido_m": 10})],
                   [D("M2", "buz_cara_grados", "normal", 65, 10, 39, 81)])
    a, b = (r.berm for r in rs)
    assert a.face_angle_deg == 65 and a.interramp_deg == pytest.approx(37.576, abs=1e-3)
    assert a.ritchie.width_m == pytest.approx(6.9) and a.required_width_m == pytest.approx(6.9)
    assert not a.narrower_than_required and a.reliability is None
    assert rs[0].fs is None and not rs[0].needs_attention
    assert b.required_width_m == 10 and 0 < b.reliability.reliability < 1 and b.reliability.n == 5000
    assert bk.block_counts(rs)["berm_reliability_evaluated"] == 1


def test_berma_con_retroquiebre(tmp_path):
    (r,), _ = correr(tmp_path, J35, [talud(buz="65")], [B(**BERMA)],
                     [D("M1", "retroquiebre_m", "uniforme", "", "", 2, 9)], iterations=200)
    w = r.berm.reliability
    h_cot_ir = 12 / math.tan(math.radians(r.berm.interramp_deg))
    assert w.width_max == pytest.approx(h_cot_ir - 2, abs=0.1) and w.width_min == pytest.approx(h_cot_ir - 9, abs=0.1)


def test_sau_mau_ping_por_la_hoja(tmp_path):
    (r,), slopes = correr(tmp_path, J35, [talud()], [B(**SMP)], SMP_D)
    p = r.probabilistic
    assert p.pof * 100 == pytest.approx(6.4, abs=1.5) and p.n == 5000 and p.seed == 1 and p.sampling == "lhs"
    base = rm.PlanarInput()
    base.height_m, base.face_dip_deg = 60, 50
    base.plane_dip_deg = slopes[0].families[0].mean_plane.dip_deg
    base.unit_weight, base.water_unit_weight, base.cohesion, base.friction_deg = 2.6 * G, 1.0 * G, 10 * G, 35
    base.tension_crack_distance_m = 15.3
    mano = run_probabilistic("planar", base, {
        "friction_deg": normal(35, 5, 15, 70), "cohesion": normal(10 * G, 2 * G, 0, 25 * G),
        "tension_crack_distance_m": normal(15.3, 4, 0, 35.3429), "water_fill": exponential(0.5, 0, 1),
        "kh": exponential(0.08, 0, 0.16)}, n=5000, sampling="lhs", seed=1)
    assert p == mano
    assert bk.block_counts([r])["pof_above_0"] == 1 and not r.needs_attention  # la PoF no pide atención (R14)


def _todas(tmp_path):
    jf = J35 + ["R2,J1,47,203", "R2,J2,52,287"]
    tf = [talud(), talud("T2", "R2", "60", "230"), talud("T3", "R1", "65")]
    bf = [B(**PL1, retroanalisis="si"), B(**{**CU2, "id_talud": "T2"}), B(**VO1),
          B(**{**BERMA, "id_talud": "T3", "ancho_requerido_m": 10}), B(**SMP)]
    df = SMP_D + [D("M1", "buz_cara_grados", "normal", 65, 10, 39, 81)]
    return jf, tf, bf, df


def test_ida_y_vuelta_csv_y_excel(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    jf, tf, bf, df = _todas(tmp_path)
    a, _ = correr(tmp_path, jf, tf, bf, df, iterations=300)
    from test_slopes import EXTRA_F, EXTRA_T, FAM_CAB, TAL_CAB
    wb = openpyxl.Workbook()
    for nombre, cab, filas in (("Familias", FAM_CAB, [f + EXTRA_F for f in jf]),
                               ("Taludes", TAL_CAB, [t + EXTRA_T for t in tf]),
                               ("Bloques", ",".join(bk.BLOCK_COLUMNS) + EXTRA_CAB, bf),
                               ("Distribuciones", DIS_CAB + EXTRA_CAB, df)):
        ws = wb.create_sheet(nombre)
        for linea in [cab, *filas]:
            fila = []
            for c in linea.split(","):
                try:
                    fila.append(None if c == "" else float(c))
                except ValueError:
                    fila.append(c)
            ws.append(fila)
    del wb["Sheet"]
    x = tmp_path / "x.xlsx"
    wb.save(x)
    slopes = rm.assess_slopes(rm.load_slope_faces(x), rm.load_families(x))
    b = rm.assess_blocks(rm.load_blocks(x), slopes, rm.load_distributions(x), iterations=300)
    assert repr(a) == repr(b)
    assert [r.fs for r in a] == [r.fs for r in b]
    assert [r.probabilistic.fs if r.probabilistic else None for r in a] == \
           [r.probabilistic.fs if r.probabilistic else None for r in b]
    assert bk.block_counts(a) == bk.block_counts(b)
    assert [r.id_bloque for r in b] == ["B1", "C1", "V1", "M1", "S1"]


def test_conteos_y_archivo_de_resultados(tmp_path):
    jf, tf, bf, df = _todas(tmp_path)
    rs, _ = correr(tmp_path, jf, tf, bf, df, iterations=300)
    c = bk.block_counts(rs)
    assert c["blocks"] == 5 and (c["planar"], c["wedge"], c["toppling"], c["berm"]) == (2, 1, 1, 1)
    assert c["formed"] == 4 and c["with_fs"] == 4 and c["fs_below_1"] == 1 and c["probabilistic"] == 1
    assert c["berm_reliability_evaluated"] == 1 and c["berm_narrower"] == 1  # 10 m contra 10 m requeridos
    cab, filas = leer(bk.save_block_results(rs, tmp_path / "res.csv"))
    assert cab == list(bk.RESULT_COLUMNS) and len(cab) == 25
    assert [f["modelo"] for f in filas] == ["planar", "cuna", "volteo", "berma", "planar"]
    assert [f["modo"] for f in filas] == ["planar", "dos_planos", "volteo", "", "planar"]
    assert [f["fs_menor_o_igual_1"] for f in filas] == ["si", "no", "no", "", "no"]
    assert filas[4]["iteraciones"] == "300" and filas[4]["muestreo"] == "lhs" and filas[4]["semilla"] == "1"
    assert filas[0]["phi_c0_grados"] != "" and filas[3]["confiabilidad_berma_pct"] != ""
    assert sum(f["fs_menor_o_igual_1"] == "si" for f in filas) == c["fs_below_1"]


def test_berma_reproducible_desde_el_archivo(tmp_path):
    (r,), _ = correr(tmp_path, J35, [talud(buz="65")], [B(**BERMA)],
                     [D("M1", "buz_cara_grados", "normal", 65, 10, 39, 81)], iterations=300, seed=7,
                     sampling="monte_carlo")
    assert (r.berm.sampling, r.berm.seed, r.berm.reliability.n) == ("monte_carlo", 7, 300)
    _, (f,) = leer(bk.save_block_results([r], tmp_path / "res.csv"))
    assert (f["muestreo"], f["iteraciones"], f["semilla"], f["iteraciones_validas"]) == ("monte_carlo", "300", "7", "")


def test_fs_infinito_en_csv_y_xlsx(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    (r,), _ = correr(tmp_path, J35, [talud()], [B(**{**PL1, "perno_kn_m": 1e6, "perno_inclinacion_grados": 0,
                                                       "perno_tipo": "activo"})])
    assert r.fs == math.inf and not r.needs_attention
    _, (f,) = leer(bk.save_block_results([r], tmp_path / "res.csv"))
    assert f["fs"] == "inf" and f["fs_menor_o_igual_1"] == "no" and f["formado"] == "si"
    ws = openpyxl.load_workbook(bk.save_block_results([r], tmp_path / "res.xlsx"))["Bloques_resultados"]
    cab = [c.value for c in ws[1]]
    fila = dict(zip(cab, [c.value for c in ws[2]]))
    assert fila["fs"] == "inf" and fila["fs_menor_o_igual_1"] == "no" and fila["formado"] == "si"


# ---------------------------------------------------------------- foco 1: límites


def test_familia_con_el_buzamiento_de_la_cara_no_forma(tmp_path):
    (r,), _ = correr(tmp_path, ["R1,J1,50,180"], [talud()], [B(**PL1, retroanalisis="si")])
    assert not r.deterministic.formed and r.fs is None
    assert any("not formed" in n for n in r.notes) and r.warnings == ()
    assert not r.needs_attention and bk.block_attention(r) == []


def test_berma_igual_al_requerido_es_mas_angosta(tmp_path):
    (r,), _ = correr(tmp_path, J35, [talud(buz="65")], [B(**{**BERMA, "ancho_berma_m": 6.9})])
    assert r.berm.required_width_m == pytest.approx(6.9) and r.berm.narrower_than_required
    assert not r.needs_attention  # la comparación con Ritchie se informa (R14)


def test_familia_vertical_no_forma_planar(tmp_path):
    (r,), _ = correr(tmp_path, ["R1,J1,90,180"], [talud()], [B(**PL1)])
    assert r.fs is None and any("not formed" in n for n in r.notes) and r.warnings == ()


@pytest.mark.parametrize("jf", [["R1,J1,0.5,0", "R1,J1,0.5,180"],  # media de Fisher con buzamiento 0 exacto
                                ["R1,J1,0.0001,180"], ["R1,J1,0,0"]])
def test_familia_horizontal_toma_el_limite_0_mas(tmp_path, jf):
    # con grieta llena y sismo un plano casi horizontal falla: el corte en 0 no puede dar el lado favorable
    fila = {**PL1, "dist_grieta_m": 10, "kh": 0.3}
    (r,), slopes = correr(tmp_path, jf, [talud()], [B(**fila)])
    assert r.fs == pytest.approx(0.9476, abs=1e-3) and r.needs_attention
    assert bk.block_attention(r) == ["att_fs_below_1"]  # sin dirección: no hay aviso lateral


def test_bloque_no_formado_con_distribuciones_no_pide_atencion(tmp_path):
    fila = {**CU2, "buz_sup_grados": 80, "dir_sup_grados": 230}
    (r,), _ = correr(tmp_path, CU2_J, [talud(buz="60", dir_="230")], [B(**fila)],
                     [D("C1", "friccion_1_grados", "uniforme", "", "", 30, 45)], iterations=50)
    assert r.fs is None and r.probabilistic.n_valid == 0
    assert "probabilistic: no valid samples" in r.notes and r.warnings == () and not r.needs_attention


def test_berma_con_anchos_negativos_deja_nota(tmp_path):
    (r,), _ = correr(tmp_path, J35, [talud(buz="65")], [B(**BERMA)],
                     [D("M1", "buz_cara_grados", "uniforme", "", "", 20, 30)], iterations=100)
    assert r.berm.reliability.reliability == 0 and r.berm.reliability.width_max < 0
    assert bk._NEGATIVE_WIDTH_NOTE in r.notes and not r.needs_attention


# ---------------------------------------------------------------- foco 2: ejes


def test_familia_vertical_en_los_dos_sentidos_da_la_misma_cuna(tmp_path):
    fila = {**CU2, "carga_kn": "", "carga_tendencia_grados": "", "carga_inmersion_grados": ""}
    tf = [talud(buz="60", dir_="230")]
    (a,), _ = correr(tmp_path, ["R1,J1,90,110", "R1,J1,90,290", "R1,J2,50,170"], tf, [B(**fila)])
    (b,), _ = correr(tmp_path, ["R1,J1,90,110", "R1,J1,90,110", "R1,J2,50,170"], tf, [B(**fila)])
    assert a.deterministic.mode == b.deterministic.mode == rm.WedgeMode.PlaneOne
    assert a.fs == pytest.approx(b.fs, abs=1e-9)


def test_limite_lateral_de_la_cinematica_o_de_la_llamada(tmp_path):
    jf = ["R1,J1,35,140"]  # 40° de la cara
    (r,), _ = correr(tmp_path, jf, [talud()], [B(**PL1)])
    assert r.warnings == ("planar block: the plane dip direction differs from the face by more than the lateral limit "
                          "(2D analysis)",) and r.needs_attention
    (r,), _ = correr(tmp_path, jf, [talud()], [B(**PL1)], lateral_limit_deg=45)
    assert r.warnings == ()
    (r,), _ = correr(tmp_path, jf, [talud(fr="30", lim="45")], [B(**PL1)])  # el de la cinemática del talud
    assert r.warnings == ()


# ---------------------------------------------------------------- foco 4: hoja mal escrita


def _err(tmp_path, bf, df=(), jf=J35, tf=None):
    with pytest.raises(ValueError) as e:
        correr(tmp_path, jf, tf or [talud()], bf, df)
    return str(e.value)


@pytest.mark.parametrize("fila,col", [
    (dict(modelo="ZZSENT"), "modelo"),
    (dict(altura_m=""), "altura_m"),
    (dict(altura_m="nan"), "altura_m"),
    (dict(altura_m="abc-ZZSENT"), "altura_m"),
    (dict(llenado_agua=1.5), "llenado_agua"),
    (dict(kh=-0.25), "kh"),
    (dict(perno_kn_m=50, perno_inclinacion_grados=20, perno_tipo="ZZSENT"), "perno_tipo"),
    (dict(perno_kn_m=50), "perno_inclinacion_grados"),
    (dict(carga_kn=50), "carga_angulo_grados"),
    (dict(retroanalisis="ZZSENT"), "retroanalisis"),
    (dict(id_talud="T-ZZSENT"), "id_talud"),
    (dict(familia_1="F-ZZSENT"), "familia_1"),
])
def test_bloques_mal_escritos(tmp_path, fila, col):
    m = _err(tmp_path, [B(**{**PL1, **fila})])
    assert m.startswith("sheet 'Bloques', row 2, column '" + col + "':"), m
    assert "ZZSENT" not in m and "1.5" not in m and "nan" not in m and "-0.25" not in m


@pytest.mark.parametrize("fila,col", [
    (dict(modelo="volteo", n_bloques=16.5), "n_bloques"),
    (dict(modelo="volteo", bloque_cresta=17), "bloque_cresta"),
    (dict(modelo="volteo", friccion_1_grados=0), "friccion_1_grados"),
    (dict(modelo="cuña", familia_2=""), "familia_2"),
])
def test_columnas_por_modelo(tmp_path, fila, col):
    base = {**VO1} if fila.get("modelo") == "volteo" else {**CU2}
    m = _err(tmp_path, [B(**{**base, **fila})], jf=CU2_J)
    assert m.startswith("sheet 'Bloques', row 2, column '" + col + "':"), m


def test_id_bloque_repetido(tmp_path):
    m = _err(tmp_path, [B(**{**PL1, "id_bloque": "B-ZZSENT"}), B(**{**PL1, "id_bloque": "B-ZZSENT"})])
    assert "sheet 'Bloques'" in m and "rows 2 and 3" in m and "id_bloque" in m and "ZZSENT" not in m


@pytest.mark.parametrize("filas,col", [
    ([D("B-ZZSENT", "kh", "uniforme", "", "", 0, 0.1)], "id_bloque"),
    ([D("B1", "ZZSENT", "uniforme", "", "", 0, 0.1)], "variable"),
    ([D("B1", "presion_1_kpa", "uniforme", "", "", 0, 0.1)], "variable"),  # columna de la cuña, no del planar
    ([D("B1", "kh", "ZZSENT", "", "", 0, 0.1)], "distribucion"),
    ([D("B1", "kh", "uniforme", "", "", 0, 0.1), D("B1", "kh", "uniforme", "", "", 0, 0.2)], "variable"),
    ([D("B1", "kh", "normal", 0.05, "", 0, 0.1)], "desviacion"),
    ([D("B1", "kh", "exponencial", "", "", 0, 0.1)], "media"),
    ([D("B1", "kh", "uniforme", 0.05, "", 0, 0.1)], "media"),
    ([D("B1", "kh", "uniforme", "", "", "", 0.1)], "minimo"),
])
def test_distribuciones_mal_escritas(tmp_path, filas, col):
    m = _err(tmp_path, [B(**PL1)], filas)
    assert re.match(rf"sheet 'Distribuciones', row [23], column '{col}':", m), m
    assert "ZZSENT" not in m


def test_distribucion_imposible_nombra_la_fila(tmp_path):
    m = _err(tmp_path, [B(**PL1)], [D("B1", "kh", "uniforme", "", "", 0.2, 0.1)])
    assert m.startswith("sheet 'Distribuciones', row 2") and "0.2" not in m


def test_variable_permitida_trae_la_lista(tmp_path):
    m = _err(tmp_path, [B(**PL1)], [D("B1", "presion_1_kpa", "uniforme", "", "", 0, 1)])
    assert "friccion_1_grados" in m and "buz_plano_grados" in m


def test_berma_toma_una_sola_distribucion(tmp_path):
    m = _err(tmp_path, [B(**BERMA)], [D("M1", "buz_cara_grados", "uniforme", "", "", 60, 70),
                                       D("M1", "retroquiebre_m", "uniforme", "", "", 2, 9)])
    assert m.startswith("sheet 'Distribuciones', row 3, column 'variable':"), m


def test_error_del_nucleo_con_hoja_y_fila_sin_valor(tmp_path):
    # b mayor que bmax: solo el núcleo lo sabe (combinación de celdas)
    m = _err(tmp_path, [B(**{**PL1, "dist_grieta_m": 77.125})])
    assert m.startswith("sheet 'Bloques', row 2:") and "Received" not in m and "77.125" not in m
    assert "dist_grieta_m" in m  # el campo del núcleo se nombra con su columna
    assert "Domain error" not in m and "parameter" not in m and "tension_crack" not in m


@pytest.mark.parametrize("var,mn,mx,col", [("friccion_1_grados", 80, 95, "maximo"), ("kh", -0.5, 0.1, "minimo"),
                                           ("buz_plano_grados", 20, 90, "maximo"),
                                           ("buz_cara_grados", 0, 60, "minimo")])
def test_distribucion_fuera_del_dominio_de_la_variable(tmp_path, var, mn, mx, col):
    m = _err(tmp_path, [B(**PL1)], [D("B1", var, "uniforme", "", "", mn, mx)])
    assert m.startswith(f"sheet 'Distribuciones', row 2, column '{col}':") and "95" not in m, m


@pytest.mark.parametrize("mn,mx,col", [(-5, 2, "minimo"), (0, math.inf, "maximo")])
def test_retroquiebre_acotado(tmp_path, mn, mx, col):
    m = _err(tmp_path, [B(**BERMA)], [D("M1", "retroquiebre_m", "uniforme", "", "", mn, mx)])
    assert m.startswith(f"sheet 'Distribuciones', row 2, column '{col}':"), m


def test_error_de_una_combinacion_muestreada_lo_dice(tmp_path):
    # el determinístico (ψp 35, bmax 35.3) es válido; con ψp muestreado hasta 45, bmax baja de 15 m
    m = _err(tmp_path, [B(**{**PL1, "dist_grieta_m": 15})], [D("B1", "buz_plano_grados", "uniforme", "", "", 20, 45)])
    assert m.startswith("sheet 'Bloques', row 2: during sampling: 'dist_grieta_m'"), m
    assert "Received" not in m and "Domain error" not in m


@pytest.mark.parametrize("fila,var,col", [
    (dict(PL1), "carga_kn", "carga_angulo_grados"),
    (dict(PL1), "perno_kn_m", "perno_inclinacion_grados"),
    (dict(CU2, carga_kn="", carga_tendencia_grados="", carga_inmersion_grados=""), "carga_kn",
     "carga_tendencia_grados"),
    (dict(VO1), "soporte_kn_m", "soporte_inclinacion_grados"),
])
def test_magnitud_muestreada_exige_su_direccion(tmp_path, fila, var, col):
    m = _err(tmp_path, [B(**fila)], [D(fila["id_bloque"], var, "uniforme", "", "", 0, 100)], jf=J35 + CU2_J[1:]
             if fila["modelo"] != "cuña" else CU2_J)
    assert m.startswith(f"sheet 'Bloques', row 2, column '{col}': required when {var} is sampled"), m


@pytest.mark.parametrize("fila,col", [(dict(b_m=50), "b_m"), (dict(a1_m=1, a2_m=0.1, b_m=0.6, n_bloques=12), "a1_m"),
                                      (dict(soporte_inclinacion_grados=89.5), "soporte_inclinacion_grados"),
                                      (dict(soporte_altura_m=5), "soporte_altura_m")])
def test_geometria_del_volteo_en_la_carga(tmp_path, fila, col):
    p = blq(tmp_path, [B(**{**VO1, **fila})])
    with pytest.raises(ValueError) as e:
        rm.load_blocks(p)  # en la carga, no al evaluar
    m = str(e.value)
    assert m.startswith(f"sheet 'Bloques', row 2, column '{col}':"), m
    for core in ("heights_m", "base_dip_deg", "support_angle_deg", "Domain error", "89.5", "50"):
        assert core not in m, m


def test_cruces_revisados_antes_de_evaluar(tmp_path, monkeypatch):
    def nunca(*a, **k):
        raise AssertionError("evaluated a row before validating every cross-reference")

    monkeypatch.setattr(bk, "_assess_one", nunca)
    for mala, col in ((dict(id_talud="T9"), "id_talud"), (dict(familia_1="J9"), "familia_1")):
        m = _err(tmp_path, [B(**PL1), B(**{**PL1, "id_bloque": "B2", **mala})])
        assert m.startswith(f"sheet 'Bloques', row 3, column '{col}':"), m


def test_filas_a_mano_con_el_mismo_validador(tmp_path):
    (fila,) = rm.load_blocks(blq(tmp_path, [B(**PL1)]))
    slopes = rm.assess_slopes(rm.load_slope_faces(tal(tmp_path, [talud()])), rm.load_families(fam(tmp_path, J35)))
    from dataclasses import replace
    for cambio, col in ((dict(llenado_agua=1.5), "llenado_agua"), (dict(altura_m="abc-ZZSENT"), "altura_m"),
                        (dict(kh=math.nan), "kh"), (dict(modelo="ZZSENT"), "modelo"), (dict(perno_kn_m=5.0),
                                                                                         "perno_inclinacion_grados")):
        with pytest.raises(ValueError) as e:
            rm.assess_blocks([replace(fila, **cambio)], slopes)
        assert str(e.value).startswith(f"sheet 'Bloques', row 2, column '{col}':") and "ZZSENT" not in str(e.value)
    (r,) = rm.assess_blocks([replace(fila, modelo="PLANAR ")], slopes)  # se normaliza igual que al cargar
    assert r.fs == pytest.approx(0.818425, abs=1e-6)


@pytest.mark.parametrize("kw", [dict(iterations=0), dict(iterations=2.5), dict(iterations=True),
                                dict(sampling="sobol"), dict(seed=-1), dict(lateral_limit_deg=90),
                                dict(lateral_limit_deg=math.nan)])
def test_argumentos_de_la_llamada(kw):
    with pytest.raises(ValueError):
        rm.assess_blocks(iter(()), [], **kw)


# ---------------------------------------------------------------- foco 5: privacidad


def test_privacidad(tmp_path):
    jf = ["R-ZZSENT,F-ZZSENT,35,140", "R-ZZSENT,F-ZZSENT,36,141"]
    tf = [talud("T-ZZSENT", "R-ZZSENT")]
    bf = [B(**{**PL1, "id_bloque": "B-ZZSENT", "id_talud": "T-ZZSENT", "familia_1": "F-ZZSENT",
               "retroanalisis": "si"})]
    df = [D("B-ZZSENT", "friccion_1_grados", "normal", 35, 5, 15, 70)]
    rows = rm.load_blocks(blq(tmp_path, bf))
    dists = rm.load_distributions(dis(tmp_path, df))
    slopes = rm.assess_slopes(rm.load_slope_faces(tal(tmp_path, tf)), rm.load_families(fam(tmp_path, jf)))
    rs = rm.assess_blocks(rows, slopes, dists, iterations=200)
    assert rs[0].warnings  # el aviso del límite lateral existe y no lleva identificadores
    for o in (*rows, *dists, *rs):
        assert "ZZSENT" not in repr(o)
    assert not any("ZZSENT" in s for r in rs for s in (*r.warnings, *r.notes))
    txt = bk.save_block_results(rs, tmp_path / "res.csv").read_text(encoding="utf-8-sig")
    assert "B-ZZSENT" in txt and "T-ZZSENT" in txt and txt.count("ZZSENT") == 2


def test_privacidad_xlsx(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    from test_slopes import EXTRA_F, EXTRA_T, FAM_CAB, TAL_CAB
    jf = ["R-ZZSENT,F-ZZSENT,35,140", "R-ZZSENT,F-ZZSENT,36,141"]
    tf = [talud("T-ZZSENT", "R-ZZSENT")]
    bf = [B(**{**PL1, "id_bloque": "B-ZZSENT", "id_talud": "T-ZZSENT", "familia_1": "F-ZZSENT",
               "retroanalisis": "si"}),
          B(**{**BERMA, "id_bloque": "M-ZZSENT", "id_talud": "T-ZZSENT"})]
    df = [D("B-ZZSENT", "friccion_1_grados", "normal", 35, 5, 15, 70),
          D("M-ZZSENT", "retroquiebre_m", "uniforme", "", "", 2, 9)]
    wb = openpyxl.Workbook()
    for nombre, cab, filas in (("Familias", FAM_CAB, [f + EXTRA_F for f in jf]),
                               ("Taludes", TAL_CAB, [t + EXTRA_T for t in tf]),
                               ("Bloques", ",".join(bk.BLOCK_COLUMNS) + EXTRA_CAB, bf),
                               ("Distribuciones", DIS_CAB + EXTRA_CAB, df)):
        ws = wb.create_sheet(nombre)
        for linea in [cab, *filas]:
            fila = []
            for c in linea.split(","):
                try:
                    fila.append(None if c == "" else float(c))
                except ValueError:
                    fila.append(c)
            ws.append(fila)
    del wb["Sheet"]
    x = tmp_path / "x.xlsx"
    wb.save(x)
    rows, dists = rm.load_blocks(x), rm.load_distributions(x)
    rs = rm.assess_blocks(rows, rm.assess_slopes(rm.load_slope_faces(x), rm.load_families(x)), dists, iterations=100)
    for o in (*rows, *dists, *rs):
        assert "ZZSENT" not in repr(o)
    assert not any("ZZSENT" in s for r in rs for s in (*r.warnings, *r.notes))
    ws = openpyxl.load_workbook(bk.save_block_results(rs, tmp_path / "res.xlsx"))["Bloques_resultados"]
    celdas = [str(c.value) for fila in ws.iter_rows() for c in fila if c.value is not None]
    assert sorted(c for c in celdas if "ZZSENT" in c) == ["B-ZZSENT", "M-ZZSENT", "T-ZZSENT", "T-ZZSENT"]
    with pytest.raises(ValueError) as e:
        rm.assess_blocks(rows, [], dists)
    assert "ZZSENT" not in str(e.value)


# ---------------------------------------------------------------- paridad de la regla de atención


def _fake(fs, warnings=(), notes=(), pof=None):
    det = None if fs is None else SimpleNamespace(factor_of_safety=fs, formed=True)
    prob = None if pof is None else SimpleNamespace(pof=pof, n_valid=10)
    return bk.BlockResult("B", "T", 1, "planar", det, None, prob, None, tuple(warnings), tuple(notes), ())


def test_paridad_de_la_atencion(tmp_path):
    rs = [_fake(x) for x in (0.5, 1.0, 1 + 1e-12, 1.2, None)]
    esperado = [True, True, True, False, False]
    assert [r.needs_attention for r in rs] == esperado
    assert [bool(bk.block_attention(r)) for r in rs] == esperado
    assert bk.block_counts(rs)["fs_below_1"] == sum(esperado)
    _, filas = leer(bk.save_block_results(rs, tmp_path / "par.csv"))
    assert [f["fs_menor_o_igual_1"] == "si" for f in filas] == esperado
    assert not _fake(1.5, pof=0.4).needs_attention
    assert not _fake(1.5, notes=("a note",)).needs_attention
    assert _fake(1.5, warnings=("w (3 of 10 samples)",)).needs_attention
    assert bk.block_attention(_fake(0.5, warnings=("w",))) == ["att_fs_below_1", "att_block_warnings"]


def test_avisos_de_muestras_piden_atencion(tmp_path):
    # con φ muy bajo y agua, algunas muestras tienen normal efectiva negativa: aviso agregado del núcleo
    fila = {**PL1, "cohesion_1_kpa": 300, "friccion_1_grados": 5}
    (r,), _ = correr(tmp_path, J35, [talud()], [B(**fila)],
                     [D("B1", "peso_agua_kn_m3", "uniforme", "", "", 10, 60)], iterations=100)
    assert r.fs > 1 and r.deterministic.warnings == []
    assert any("samples)" in w for w in r.warnings) and r.needs_attention
    (w,) = r.warnings
    assert re.fullmatch(r"probabilistic: effective normal force on the plane is negative: friction taken as zero "
                        r"\(\d+ of 100 samples\)", w), w


def test_textos_agregados_del_volteo_se_leen(tmp_path):
    fila = {**VO1, "soporte_kn_m": "", "friccion_1_grados": 20, "buz_base_grados": 60}
    (r,), _ = correr(tmp_path, J35, [talud()], [B(**fila)],
                     [D("V1", "friccion_1_grados", "uniforme", "", "", 15, 25)], iterations=60)
    textos = (*r.warnings, *r.notes)
    assert textos and not any("(N)" in t or "above N" in t or "below N" in t for t in textos), textos
    assert any(re.search(r"\(8\)-\(9\) fail in N blocks \(\d+ of 60 samples\)", t) for t in textos), textos


def test_methods(tmp_path):
    jf, tf, bf, df = _todas(tmp_path)
    rs, _ = correr(tmp_path, jf, tf, bf, df, iterations=100)
    ids = [[m.method_id for m in r.methods] for r in rs]
    for i in ids:
        assert len(i) == len(set(i))
    assert ids[0] == ["Planar-HoekBray"]
    assert ids[1] == ["Wedge-Tetrahedral-Vector"]
    assert ids[2] == ["Toppling-GoodmanBray1976"]
    assert ids[3] == ["Berm-ModifiedRitchie", "Berm-Reliability-RyanPryor2000", "Probabilistic-MC-LHS"]
    assert ids[4] == ["Planar-HoekBray", "Probabilistic-MC-LHS"]


# --- ola final de la 3B ------------------------------------------------------------------------------------------

@pytest.mark.parametrize("fila,var", [
    (dict(PL1, kh=""), "kh"),
    (dict(PL1, llenado_agua=""), "llenado_agua"),
    (dict(PL1), "dist_grieta_m"),
    (dict(CU2, presion_1_kpa=""), "presion_1_kpa"),
    (dict(VO1), "soporte_altura_m"),
])
def test_variable_muestreada_exige_su_columna(tmp_path, fila, var):
    # si no, el FS determinístico correría otro modelo que las muestras (I2)
    m = _err(tmp_path, [B(**fila)], [D(fila["id_bloque"], var, "uniforme", "", "", 0.1, 0.2)],
             jf=CU2_J if fila["modelo"] == "cuña" else J35)
    assert m == f"sheet 'Bloques', row 2, column '{var}': required because it is sampled in Distribuciones", m


def test_sau_mau_ping_trae_agua_y_sismo_en_la_fila(tmp_path):
    (r,), _ = correr(tmp_path, J35, [talud()], [B(**SMP)], SMP_D, iterations=50)
    assert r.fs == pytest.approx(1.2202, abs=1e-4)  # zw/z 0.5 y kh 0.08, los mismos supuestos que muestrea


def test_n_bloques_acotado(tmp_path):
    m = _err(tmp_path, [B(**{**VO1, "n_bloques": 3e9})])
    assert m == "sheet 'Bloques', row 2, column 'n_bloques': out of range", m
    m = _err(tmp_path, [B(**{**VO1, "n_bloques": 1001})])
    assert m.endswith("'n_bloques': out of range")


@pytest.mark.parametrize("var,mn,mx,col", [("buz_plano_grados", 0, 40, "minimo"),
                                           ("buz_plano_grados", 20, 90, "maximo"),
                                           ("altura_m", 0, 40, "minimo")])
def test_limite_abierto_lo_dice(tmp_path, var, mn, mx, col):
    m = _err(tmp_path, [B(**PL1)], [D("B1", var, "uniforme", "", "", mn, mx)])
    assert m == f"sheet 'Distribuciones', row 2, column '{col}': out of range (open bound)", m


def test_block_mode_es_publico(tmp_path):
    jf, tf, bf, df = _todas(tmp_path)
    rs, _ = correr(tmp_path, jf, tf, bf, df, iterations=50)
    assert [bk.block_mode(r) for r in rs] == ["planar", "dos_planos", "volteo", None, "planar"]


def test_avisos_agrupados_entre_bloques():
    rs = [_fake(1.5, warnings=("probabilistic: w (3 of 10 samples)", "Goodman-Bray conditions (8)-(9) fail in 2 blocks")),
          _fake(1.5, warnings=("probabilistic: w (7 of 10 samples)", "Goodman-Bray conditions (8)-(9) fail in 3 blocks")),
          _fake(1.5, warnings=("other",))]
    assert bk.warning_counts(rs) == {"probabilistic: w": 2, "Goodman-Bray conditions (8)-(9) fail in N blocks": 2,
                                     "other": 1}
