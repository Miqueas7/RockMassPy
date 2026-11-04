import csv
import math
from types import SimpleNamespace

import pytest

import rockmasspy as rm
from rockmasspy import limit_equilibrium as le

M = rm.LeMethod
EXTRA = ",ZZSENT,ZZSENT,ZZSENT,ZZSENT"
EXTRA_CAB = ",codigo_mina,labor_codigo,este_m,observaciones"
CABS = {"Geometria": ",".join(le.GEOMETRY_COLUMNS), "Estratos": ",".join(le.LAYER_COLUMNS),
        "Materiales_LE": ",".join(le.MATERIAL_COLUMNS), "Analisis_LE": ",".join(le.ANALYSIS_COLUMNS),
        "Sismos": ",".join(le.RECORD_COLUMNS)}
COLS = {"Materiales_LE": le.MATERIAL_COLUMNS, "Analisis_LE": le.ANALYSIS_COLUMNS}


def G(sec, linea, pts):
    return [f"{sec},{linea},{x},{y}" + EXTRA for x, y in pts]


def L(sec, orden, mat, base=""):
    return f"{sec},{orden},{mat},{base}" + EXTRA


def R(sheet, **kw):
    """Una fila de Materiales_LE o Analisis_LE en el orden de sus columnas; lo que no se da queda vacío."""
    return ",".join(str(kw.get(c, "")) for c in COLS[sheet]) + EXTRA


def S(reg, t, a):
    return f"{reg},{t},{a}" + EXTRA


def mat(**kw):
    return R("Materiales_LE", **kw)


def ana(**kw):
    return R("Analisis_LE", **kw)


# Fredlund y Krahn (1977), Slide problema 21 (psf, pcf, ft: unidades coherentes); base en y = 10 para que la malla
# alcance el círculo publicado (120, 90, 80)
FK_SURFACE = [(0, 60), (60, 60), (140, 20), (180, 20)]


def fk_data():
    return {"Geometria": G("SFK-ZZSENT", "superficie", FK_SURFACE),
            "Estratos": [L("SFK-ZZSENT", 1, "MFK-ZZSENT")],
            "Materiales_LE": [mat(material="MFK-ZZSENT", modelo="mohr_coulomb", peso_unitario_kn_m3=120,
                                  cohesion_kpa=600, friccion_grados=20)],
            "Analisis_LE": [ana(id_analisis="AFK-ZZSENT", id_seccion="SFK-ZZSENT", metodos="bishop;spencer",
                                superficie="circular", malla_x_min=110, malla_x_max=130, malla_y_min=80,
                                malla_y_max=100, base_modelo_m=10)]}


# ACADS 1(a), Slide problema 1, con la malla de centros del manual
def acads1a_data():
    return {"Geometria": G("S1A-ZZSENT", "superficie", [(20, 25), (30, 25), (50, 35), (70, 35)]),
            "Estratos": [L("S1A-ZZSENT", 1, "M1A-ZZSENT")],
            "Materiales_LE": [mat(material="M1A-ZZSENT", modelo="mohr_coulomb", peso_unitario_kn_m3=20,
                                  cohesion_kpa=3, friccion_grados=19.6)],
            "Analisis_LE": [ana(id_analisis="A1A-ZZSENT", id_seccion="S1A-ZZSENT", metodos="bishop;spencer;gle",
                                superficie="circular", malla_x_min=22.8, malla_x_max=43.7, malla_y_min=42.3,
                                malla_y_max=62.6, base_modelo_m=20)]}


# ACADS 3(b), Slide problema 8: capa débil entre 26.5 y 27.0 y superficie dada de la Tabla 8.2
def acads3b_data(**an):
    return {"Geometria": (G("S3B-ZZSENT", "superficie", [(20, 27.75), (43, 27.75), (67.5, 40), (84, 40)])  # filas 2-5
                          + G("S3B-ZZSENT", "C1-ZZSENT", [(20, 27.0), (63.5, 27.0), (84, 27.0)])  # 6-8
                          + G("S3B-ZZSENT", "C2-ZZSENT", [(20, 26.5), (84, 26.5)])  # 9-10
                          + G("S3B-ZZSENT", "F-ZZSENT", [(41.85, 27.75), (44.0, 26.5), (63.5, 27.0), (73.31, 40.0)])),
            "Estratos": [L("S3B-ZZSENT", 1, "MA-ZZSENT", "C1-ZZSENT"), L("S3B-ZZSENT", 2, "MB-ZZSENT", "C2-ZZSENT"),
                         L("S3B-ZZSENT", 3, "MA-ZZSENT")],
            "Materiales_LE": [mat(material="MA-ZZSENT", modelo="mohr_coulomb", peso_unitario_kn_m3=18.84,
                                  cohesion_kpa=28.5, friccion_grados=20),
                              mat(material="MB-ZZSENT", modelo="mohr_coulomb", peso_unitario_kn_m3=18.84,
                                  cohesion_kpa=0, friccion_grados=10)],
            "Analisis_LE": [ana(**{"id_analisis": "A3B-ZZSENT", "id_seccion": "S3B-ZZSENT", "metodos": "spencer;gle",
                                   "superficie": "dada", "linea_superficie": "F-ZZSENT", "base_modelo_m": 20, **an})]}


def merge(*ds):
    out = {}
    for d in ds:
        for k, v in d.items():
            out.setdefault(k, []).extend(v)
    return out


def hojas(tmp_path, data):
    out = {}
    for h, filas in data.items():
        p = tmp_path / f"{h}.csv"
        p.write_text("\n".join([CABS[h] + EXTRA_CAB, *filas]) + "\n", encoding="utf-8")
        out[h] = p
    return out


def libro(tmp_path, data):
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    for h, filas in data.items():
        ws = wb.create_sheet(h)
        for linea in [CABS[h] + EXTRA_CAB, *filas]:
            fila = []
            for c in linea.split(","):
                try:
                    fila.append(None if c == "" else float(c))
                except ValueError:
                    fila.append(c)
            ws.append(fila)
    del wb["Sheet"]
    x = tmp_path / "le.xlsx"
    wb.save(x)
    return x


def leer(p):
    txt = p.read_text(encoding="utf-8-sig")
    sep = ";" if ";" in txt.splitlines()[0] else ","
    cab, *filas = list(csv.reader(txt.splitlines(), delimiter=sep))
    return cab, [dict(zip(cab, f)) for f in filas]


def fs_of(r, method):
    (x,) = [x for x in r.results if x.method == method]
    return x.factor_of_safety


# ---------------------------------------------------------------- casos publicados por la hoja


@pytest.fixture(scope="module")
def publicados(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("pub")
    data = merge(fk_data(), acads1a_data(), acads3b_data())
    return data, rm.assess_le(hojas(tmp, data)), tmp


def test_fredlund_krahn_por_la_hoja(publicados):
    _, (fk, _, _), _ = publicados
    assert fk.surface_type == "circular" and fk.order == 1
    # la búsqueda alrededor del círculo publicado no da más que el círculo publicado (2.0756 recalculado, F&K 2.080)
    s = rm.LeSection()
    s.surface = [rm.Point2(x, y) for x, y in FK_SURFACE]
    lay = rm.LeLayer()
    lay.bottom, lay.material = [], 0
    m = rm.LeMaterial()
    m.unit_weight, m.cohesion, m.friction_deg = 120, 600, 20
    s.layers, s.materials, s.model_base_y = [lay], [m], 10.0
    c = rm.SlipSurface()
    c.circle = rm.Circle(120, 90, 80)
    for meth in (M.Bishop, M.Spencer):
        f0 = rm.le_factor_of_safety(s, c, meth).factor_of_safety
        assert fs_of(fk, meth) <= f0 + 1e-9  # el círculo de F&K no es el crítico: la búsqueda baja a 1.99
    g = rm.CircularGrid()
    g.x_min, g.x_max, g.y_min, g.y_max = 110, 130, 80, 100
    o = rm.SearchOptions()
    o.method = M.Bishop
    assert fs_of(fk, M.Bishop) == rm.search_circular(s, g, o).best.factor_of_safety  # mismo núcleo, bit a bit
    assert fk.search.evaluated > 0 and fk.surface.circle is not None


def test_acads_1a_por_la_hoja(publicados):
    _, (_, a, _), _ = publicados
    assert fs_of(a, M.Bishop) == pytest.approx(0.9857, abs=2e-3)
    assert fs_of(a, M.Bishop) == pytest.approx(0.987, rel=0.01)  # Slide, ±1 % con búsqueda (R9)
    for meth in (M.Spencer, M.MorgensternPrice):
        assert fs_of(a, meth) == pytest.approx(0.986, rel=0.01)
    assert a.fs_min < 1 and a.needs_attention and "att_le_fs_below_1" in le.le_attention(a)


def test_acads_3b_por_la_hoja(publicados):
    _, (_, _, b), _ = publicados
    assert b.surface_type == "given" and b.search is None
    assert fs_of(b, M.Spencer) == pytest.approx(1.2758, abs=3e-3)
    assert fs_of(b, M.MorgensternPrice) == pytest.approx(1.2601, abs=3e-3)
    assert fs_of(b, M.Spencer) == pytest.approx(1.277, rel=0.005)  # Slide
    assert b.yield_ is None and b.newmark is None


def test_csv_y_excel_dan_lo_mismo(publicados):
    data, a, tmp = publicados
    b = rm.assess_le(libro(tmp, data))
    assert repr(a) == repr(b)
    assert [[x.factor_of_safety for x in r.results] for r in a] == [[x.factor_of_safety for x in r.results] for r in b]
    assert le.le_counts(a) == le.le_counts(b)


def test_conteos_y_archivo_de_resultados(publicados):
    _, rs, tmp = publicados
    c = le.le_counts(rs)
    assert c == {**c, "analyses": 3, "with_fs": 3, "fs_below_1": 1, "circular": 2, "block": 0, "given": 1,
                 "with_newmark": 0}
    cab, filas = leer(le.save_le_results(rs, tmp / "res.csv"))
    assert cab == list(le.RESULT_COLUMNS) and len(cab) == 20
    assert cab[3:7] == ["metodo", "kh", "fs", "fs_estatico"]
    assert all(f["kh"] == "0.0" and f["fs_estatico"] == f["fs"] for f in filas)  # sin kh, el estático es el mismo
    assert [f["metodo"] for f in filas] == ["bishop", "spencer", "bishop", "spencer", "gle", "spencer", "gle"]
    assert [f["superficie"] for f in filas] == ["circular"] * 5 + ["dada"] * 2
    assert [f["fs_menor_o_igual_1"] for f in filas] == ["no", "no", "si", "si", "si", "no", "no"]
    assert filas[0]["xc_m"] != "" and filas[0]["puntos_superficie"] == "" and filas[0]["evaluadas"] != ""
    assert filas[5]["xc_m"] == "" and filas[5]["puntos_superficie"].count(";") == 3 and filas[5]["evaluadas"] == ""
    assert filas[0]["convergio"] == "si" and filas[3]["lambda"] != ""


def test_metodos_son_secondary(publicados):
    _, rs, _ = publicados
    ids = {m.method_id for r in rs for m in r.methods}
    assert {"Bishop-Simplified", "Spencer", "Morgenstern-Price-GLE"} <= ids
    assert all(m.verification == rm.Verification.Secondary for r in rs for m in r.methods)


# ---------------------------------------------------------------- ky y Newmark


def seno(reg="R-ZZSENT", amp=0.3, f=1.0, dt=0.01, total=4.0):
    n = int(round(total / dt))
    return [S(reg, round(k * dt, 10), amp * math.sin(2 * math.pi * f * k * dt)) for k in range(n + 1)]


def test_registro_sintetico_da_ky_y_newmark(tmp_path):
    data = merge(acads3b_data(registro="R-ZZSENT", escala_registro=1.5), {"Sismos": seno()})
    (r,) = rm.assess_le(hojas(tmp_path, data))
    y = r.yield_
    assert y is not None and 0 < y.ky < 0.3 * 1.5
    s = r.section
    s.kh = y.ky
    assert rm.le_factor_of_safety(s, r.surface, M.Spencer).factor_of_safety == pytest.approx(1, abs=1e-6)
    acc = le.read_accelerogram(hojas(tmp_path, {"Sismos": seno()})["Sismos"])["R-ZZSENT"]
    assert acc.dt_s == pytest.approx(0.01) and len(acc.acceleration_g) == 401 and acc.time_s[0] == 0
    ni = rm.NewmarkInput()
    ni.dt_s, ni.acceleration_g, ni.ky, ni.scale, ni.both_directions = acc.dt_s, list(acc.acceleration_g), y.ky, 1.5, True
    assert r.newmark.displacement_m == rm.newmark_rigid_block(ni).displacement_m > 0
    assert le.le_counts([r])["with_newmark"] == 1 and not r.needs_attention  # Newmark no pide atención (R14)
    _, (f, _) = leer(le.save_le_results([r], tmp_path / "res.csv"))
    assert float(f["ky"]) == pytest.approx(y.ky) and float(f["desplazamiento_newmark_m"]) > 0


def test_kh_da_ky_sobre_la_superficie_estatica(tmp_path):
    (r,) = rm.assess_le(hojas(tmp_path, acads3b_data(kh=0.1)))
    assert fs_of(r, M.Spencer) < 1.2758 and r.yield_.ky > 0.1 and r.newmark is None


def test_ky_cero_no_corre_newmark(tmp_path):
    d = acads1a_data()
    d["Analisis_LE"] = [ana(id_analisis="A1A-ZZSENT", id_seccion="S1A-ZZSENT", metodos="bishop",
                            superficie="circular", malla_x_min=22.8, malla_x_max=43.7, malla_y_min=42.3,
                            malla_y_max=62.6, base_modelo_m=20, registro="R-ZZSENT")]
    (r,) = rm.assess_le(hojas(tmp_path, merge(d, {"Sismos": seno()})))
    assert r.yield_.ky == 0 and r.newmark is None
    assert any("ky is 0" in n for n in r.notes) and any("ky:" in w for w in r.warnings)


def test_acelerograma_de_dos_columnas(tmp_path):
    p = tmp_path / "pulso.csv"
    p.write_text("t_s,a_g\n0,0\n0.5,0.2\n1.0,0\n", encoding="utf-8")
    (acc,) = le.read_accelerogram(p).values()
    assert acc.dt_s == 0.5 and acc.acceleration_g == (0, 0.2, 0)
    q = tmp_path / "malo.csv"
    q.write_text("t_s,a_g\n0,0\n0.5,0.2\n1.2,0\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"^sheet 'malo', row 4, column 't_s': the time step must be constant"):
        le.read_accelerogram(q)


# ---------------------------------------------------------------- foco 4: hojas mal escritas


def _err(tmp_path, data):
    with pytest.raises(ValueError) as e:
        rm.assess_le(hojas(tmp_path, data))
    return str(e.value)


def _con(sheet, i, fila):
    def cambio(d):
        if i is None:
            d[sheet].append(fila)
        else:
            d[sheet][i] = fila
    return cambio


_SISMOS = {"Sismos": seno(total=0.05)}


@pytest.mark.parametrize("cambio,hoja,fila,col", [
    (_con("Geometria", None, G("S3B-ZZSENT", "L9-ZZSENT", [(30, 30)])[0]), "Geometria", 15, "linea"),
    (_con("Geometria", 5, G("S3B-ZZSENT", "C1-ZZSENT", [(10, 27.0)])[0]), "Geometria", 7, "x_m"),
    (_con("Geometria", 1, G("S3B-ZZSENT", "superficie", [(43, "nan")])[0]), "Geometria", 3, "y_m"),
    (_con("Geometria", 0, G("S3B-ZZSENT", "superficie", [("abc-ZZSENT", 27.75)])[0]), "Geometria", 2, "x_m"),
    (_con("Estratos", 0, L("S3B-ZZSENT", 1, "MA-ZZSENT", "C9-ZZSENT")), "Estratos", 2, "linea_base"),
    (_con("Estratos", 1, L("S3B-ZZSENT", 2, "M9-ZZSENT", "C2-ZZSENT")), "Estratos", 3, "material"),
    (_con("Estratos", 0, L("S3B-ZZSENT", 1, "MA-ZZSENT")), "Estratos", 2, "linea_base"),
    (_con("Estratos", 0, L("S3B-ZZSENT", 1.5, "MA-ZZSENT", "C1-ZZSENT")), "Estratos", 2, "orden"),
    (_con("Estratos", 2, L("S3B-ZZSENT", 4, "MA-ZZSENT")), "Estratos", 4, "orden"),
    (_con("Estratos", 0, L("S9-ZZSENT", 1, "MA-ZZSENT")), "Estratos", 2, "id_seccion"),
    (_con("Materiales_LE", 0, mat(material="MA-ZZSENT", modelo="ZZSENT", peso_unitario_kn_m3=18.84)),
     "Materiales_LE", 2, "modelo"),
    (_con("Materiales_LE", 0, mat(material="MA-ZZSENT", modelo="mohr_coulomb", peso_unitario_kn_m3=18.84,
                                  cohesion_kpa=28.5, friccion_grados=95)), "Materiales_LE", 2, "friccion_grados"),
    (_con("Materiales_LE", 0, mat(material="MA-ZZSENT", modelo="mohr_coulomb", peso_unitario_kn_m3="nan",
                                  cohesion_kpa=28.5, friccion_grados=20)), "Materiales_LE", 2, "peso_unitario_kn_m3"),
    (_con("Materiales_LE", 0, mat(material="MA-ZZSENT", modelo="hoek_brown", peso_unitario_kn_m3=18.84, gsi=50, mi=10)),
     "Materiales_LE", 2, "sigma_ci_mpa"),
    (_con("Materiales_LE", 0, mat(material="MA-ZZSENT", modelo="hoek_brown", peso_unitario_kn_m3=18.84,
                                  sigma_ci_mpa=50, gsi=50, mi=10, mb=1)), "Materiales_LE", 2, "mb"),
    (_con("Materiales_LE", 1, mat(material="MA-ZZSENT", modelo="mohr_coulomb", peso_unitario_kn_m3=18.84,
                                  cohesion_kpa=0, friccion_grados=10)), "Materiales_LE", 3, "material"),
])
def test_hojas_mal_escritas(tmp_path, cambio, hoja, fila, col):
    d = acads3b_data()
    cambio(d)
    m = _err(tmp_path, d)
    if col == "material" and hoja == "Materiales_LE":  # id repetido: el mensaje de read_records nombra las filas
        assert m.startswith("sheet 'Materiales_LE': duplicate material in rows 2 and 3"), m
    else:
        assert m.startswith(f"sheet '{hoja}', row {fila}, column '{col}':"), m
    assert not any(x in m for x in ("ZZSENT", "nan", "95", "1.5", "abc")), m


@pytest.mark.parametrize("an,sismos,col", [
    (dict(metodos="bishop;ZZSENT"), False, "metodos"),
    (dict(metodos=""), False, "metodos"),
    (dict(superficie="ZZSENT"), False, "superficie"),
    (dict(superficie="circular"), False, "malla_x_min"),
    (dict(superficie="circular", malla_x_min=50, malla_x_max=40, malla_y_min=40, malla_y_max=60), False, "malla_x_max"),
    (dict(superficie="bloque"), False, "linea_debil"),
    (dict(superficie="bloque", linea_debil="L9-ZZSENT"), False, "linea_debil"),
    (dict(linea_superficie="L9-ZZSENT"), False, "linea_superficie"),
    (dict(id_seccion="S9-ZZSENT"), False, "id_seccion"),
    (dict(registro="R9-ZZSENT"), True, "registro"),
    (dict(escala_registro=2), False, "registro"),
    (dict(kh="nan"), False, "kh"),
    (dict(kh=1.5), False, "kh"),
    (dict(tajadas=4), False, "tajadas"),
    (dict(tajadas=10.5), False, "tajadas"),
    (dict(grieta_llenado=0.5), False, "grieta_m"),
    (dict(funcion="ZZSENT"), False, "funcion"),
    (dict(peso_agua_kn_m3=0), False, "peso_agua_kn_m3"),
])
def test_analisis_mal_escritos(tmp_path, an, sismos, col):
    d = acads3b_data(**an)
    if sismos:
        d.update(_SISMOS)
    m = _err(tmp_path, d)
    assert m.startswith(f"sheet 'Analisis_LE', row 2, column '{col}':"), m
    assert not any(x in m for x in ("ZZSENT", "nan", "1.5", "10.5")), m


@pytest.mark.parametrize("filas,fila", [
    ([S("R-ZZSENT", 0.01, 0), S("R-ZZSENT", 0.02, 0.1)], 2),  # no empieza en 0
    ([S("R-ZZSENT", 0, 0), S("R-ZZSENT", 0.01, 0.1), S("R-ZZSENT", 0.01, 0.2)], 4),  # no crece
    ([S("R-ZZSENT", 0, 0), S("R-ZZSENT", 0.01, 0.1), S("R-ZZSENT", 0.03, 0.2)], 4),  # paso variable
    ([S("R-ZZSENT", 0, 0), S("R-ZZSENT", 0.01, "nan")], 3),
])
def test_sismos_mal_escritos(tmp_path, filas, fila):
    d = merge(acads3b_data(registro="R-ZZSENT"), {"Sismos": filas})
    m = _err(tmp_path, d)
    col = "a_g" if "nan" in filas[-1] else "t_s"
    assert m.startswith(f"sheet 'Sismos', row {fila}, column '{col}':"), m
    assert "ZZSENT" not in m and "nan" not in m and "0.03" not in m


def test_error_del_nucleo_con_hoja_y_fila_sin_valor(tmp_path):
    # la polilínea dada no corta la superficie: el núcleo lanza y el mensaje sale con hoja y fila
    d = acads3b_data()
    d["Geometria"][9:] = G("S3B-ZZSENT", "F-ZZSENT", [(41.85, 10.0), (44.0, 9.0), (63.5, 9.5), (73.31, 11.0)])
    m = _err(tmp_path, d)
    assert m.startswith("sheet 'Analisis_LE', row 2: "), m
    assert "Received" not in m and "ZZSENT" not in m and "41.85" not in m


def test_fuente_mal_dada(tmp_path):
    with pytest.raises(ValueError, match="unknown sheet"):
        rm.assess_le({"Otra": tmp_path / "x.csv"})
    with pytest.raises(ValueError, match="expected a .xlsx"):
        rm.assess_le(tmp_path / "x.csv")
    p = hojas(tmp_path, acads3b_data(registro="R-ZZSENT"))
    with pytest.raises(ValueError, match="no accelerogram given"):
        rm.assess_le(p)


def test_hoek_brown_por_gsi_y_por_constantes(tmp_path):
    def con(**kw):
        d = acads3b_data()
        d["Materiales_LE"][0] = mat(material="MA-ZZSENT", modelo="hoek_brown", peso_unitario_kn_m3=18.84,
                                    sigma_ci_mpa=0.5, **kw)
        return d
    hb = rm.hb_params(30, 8, 0)
    (a,) = rm.assess_le(hojas(tmp_path, con(gsi=30, mi=8)))
    (b,) = rm.assess_le(hojas(tmp_path, con(mb=hb.mb, s=hb.s, a=hb.a)))
    assert fs_of(a, M.Spencer) == pytest.approx(fs_of(b, M.Spencer), rel=1e-9)
    m = a.section.materials[0]
    assert m.model == rm.StrengthModel.HoekBrown and m.sigma_ci == pytest.approx(500)  # MPa -> kPa
    assert any(x.method_id == "HB-2018" for x in a.methods)


# ---------------------------------------------------------------- foco 5: privacidad


def test_privacidad(tmp_path):
    data = merge(acads3b_data(registro="R-ZZSENT", kh=0.05), {"Sismos": seno()})
    src = hojas(tmp_path, data)
    inp = le.load_le_inputs(src)
    rs = rm.assess_le(src)
    for o in (*inp.geometry, *inp.layers, *inp.materials, *inp.analyses, *inp.records, inp, *rs):
        assert "ZZSENT" not in repr(o)
    assert rs[0].warnings or rs[0].notes
    assert not any("ZZSENT" in s for r in rs for s in (*r.warnings, *r.notes))
    cab, filas = leer(le.save_le_results(rs, tmp_path / "res.csv"))
    for f in filas:
        assert (f["id_analisis"], f["id_seccion"]) == ("A3B-ZZSENT", "S3B-ZZSENT")
        assert not any("ZZSENT" in v for k, v in f.items() if k not in ("id_analisis", "id_seccion"))


def test_privacidad_xlsx(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    x = libro(tmp_path, merge(acads3b_data(registro="R-ZZSENT"), {"Sismos": seno()}))
    rs = rm.assess_le(x)
    assert not any("ZZSENT" in repr(o) for o in rs)
    ws = openpyxl.load_workbook(le.save_le_results(rs, tmp_path / "res.xlsx"))["Analisis_LE_resultados"]
    celdas = [str(c.value) for fila in ws.iter_rows() for c in fila if c.value is not None]
    assert sorted(c for c in celdas if "ZZSENT" in c) == ["A3B-ZZSENT", "A3B-ZZSENT", "S3B-ZZSENT", "S3B-ZZSENT"]


# ---------------------------------------------------------------- paridad de la regla de atención


def _fake(fs, warnings=(), notes=()):
    res = SimpleNamespace(factor_of_safety=fs, method=M.Bishop, lambda_=None, converged=fs is not None)
    return le.LeAnalysisResult("A", "S", 1, "given", (res,), None, None, None, tuple(warnings), tuple(notes), ())


def test_paridad_de_la_atencion(tmp_path):
    rs = [_fake(x) for x in (0.5, 1.0, 1 + 1e-12, 1.2, None)]
    esperado = [True, True, True, False, False]
    assert [r.needs_attention for r in rs] == esperado
    assert [bool(le.le_attention(r)) for r in rs] == esperado
    assert le.le_counts(rs)["fs_below_1"] == sum(esperado) and le.le_counts(rs)["with_fs"] == 4
    _, filas = leer(le.save_le_results(rs, tmp_path / "par.csv"))
    assert [f["fs_menor_o_igual_1"] == "si" for f in filas] == esperado
    assert [f["fs_menor_o_igual_1"] for f in filas][-1] == ""
    assert not _fake(1.5, notes=("a note",)).needs_attention
    assert le.le_attention(_fake(0.5, warnings=("w",))) == ["att_le_fs_below_1", "att_le_warnings"]
    assert le.le_attention(_fake(1.5, warnings=("w",))) == ["att_le_warnings"]


# ---------------------------------------------------------------- revisión 3C: cobertura, ky por vueltas, mensajes


def _corta(d, pts):
    d["Geometria"] = d["Geometria"] + G("SFK-ZZSENT", "piezometrica", pts)
    return d


def test_piezometrica_corta_lanza_en_la_busqueda_y_en_la_hoja(tmp_path):
    # sondeo p9 del revisor: con la piezométrica desde x = 100 la búsqueda descartaba en silencio (FS 33.4)
    s = rm.LeSection()
    s.surface = [rm.Point2(x, y) for x, y in FK_SURFACE]
    lay = rm.LeLayer()
    lay.material = 0
    m = rm.LeMaterial()
    m.unit_weight, m.cohesion, m.friction_deg = 120, 600, 20
    s.layers, s.materials, s.model_base_y, s.water_unit_weight = [lay], [m], 0.0, 62.4
    s.piezometric = [rm.Point2(100, 30), rm.Point2(180, 20)]
    g = rm.CircularGrid()
    g.x_min, g.x_max, g.y_min, g.y_max = 110, 130, 80, 100
    with pytest.raises(ValueError, match="piezometric"):
        rm.search_circular(s, g, rm.SearchOptions())
    b = rm.BlockSearch()
    b.weak_line = [rm.Point2(0, 30), rm.Point2(180, 30)]
    with pytest.raises(ValueError, match="piezometric"):
        rm.search_block(s, b, rm.SearchOptions())
    # por la hoja: Geometria, la fila del extremo que no cubre (superficie en 2-5, piezométrica en 6-7), sin el valor
    m = _err(tmp_path, _corta(fk_data(), [(100, 30), (180, 20)]))
    assert m.startswith("sheet 'Geometria', row 6, column 'linea': "), m
    assert "ZZSENT" not in m and "100" not in m
    m = _err(tmp_path, _corta(fk_data(), [(0, 30), (150, 20)]))
    assert m.startswith("sheet 'Geometria', row 7, column 'linea': "), m


def test_ky_por_vueltas_hasta_el_menor(tmp_path):
    # sondeo p8c: MC sobre HB con piezométrica; con la crítica estática ky = 0.37273, por vueltas 0.36105
    # (el revisor encontró 0.3611)
    sec = "SKY-ZZSENT"
    d = {"Geometria": G(sec, "superficie", FK_SURFACE) + G(sec, "piezometrica", [(0, 50), (60, 45), (140, 20), (180, 20)])
         + G(sec, "B-ZZSENT", [(0, 40), (180, 40)]),
         "Estratos": [L(sec, 1, "MA-ZZSENT", "B-ZZSENT"), L(sec, 2, "MB-ZZSENT")],
         "Materiales_LE": [mat(material="MA-ZZSENT", modelo="mohr_coulomb", peso_unitario_kn_m3=20, cohesion_kpa=30,
                               friccion_grados=28),
                           mat(material="MB-ZZSENT", modelo="hoek_brown", peso_unitario_kn_m3=20, sigma_ci_mpa=5,
                               mb=0.8, s=0.0005, a=0.52)],
         "Analisis_LE": [ana(id_analisis="AKY-ZZSENT", id_seccion=sec, metodos="bishop", superficie="circular",
                             malla_x_min=110, malla_x_max=130, malla_y_min=80, malla_y_max=100, base_modelo_m=0,
                             registro="R-ZZSENT")],
         "Sismos": seno(amp=0.5, total=2.0)}
    (r,) = rm.assess_le(hojas(tmp_path, d))
    ky = r.yield_.ky
    assert ky <= 0.3612 + 1e-3
    assert any("up to 4 rounds" in n for n in r.notes)
    # el ky informado es el de su superficie y es menor que el de la crítica estática
    static = r.section
    assert rm.le_yield_coefficient(static, r.yield_surface, M.Bishop).ky == ky
    assert rm.le_yield_coefficient(static, r.surface, M.Bishop).ky > ky + 0.005
    # Newmark corre con ese ky
    acc = le.read_accelerogram(hojas(tmp_path, {"Sismos": seno(amp=0.5, total=2.0)})["Sismos"])["R-ZZSENT"]
    ni = rm.NewmarkInput()
    ni.dt_s, ni.acceleration_g, ni.ky, ni.both_directions = acc.dt_s, list(acc.acceleration_g), ky, True
    assert r.newmark.displacement_m == rm.newmark_rigid_block(ni).displacement_m > 0


def test_acelerograma_vacio_o_de_una_muestra(tmp_path):
    p = tmp_path / "vacio.csv"
    p.write_text("t_s,a_g\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no samples"):
        le.read_accelerogram(p)
    q = tmp_path / "vacio_reg.csv"
    q.write_text("registro,t_s,a_g\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no samples"):
        le.read_accelerogram(q)
    u = tmp_path / "una.csv"
    u.write_text("t_s,a_g\n0,0.1\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"^sheet 'una', row 2, column 't_s': a record needs at least two samples"):
        le.read_accelerogram(u)


def test_mensajes_sin_doble_prefijo_ni_repetidos(tmp_path):
    d = fk_data()
    d["Analisis_LE"] = [ana(id_analisis="AFK-ZZSENT", id_seccion="SFK-ZZSENT", metodos="bishop;ordinario",
                            superficie="circular", malla_x_min=110, malla_x_max=130, malla_y_min=80, malla_y_max=100,
                            base_modelo_m=10, grieta_m=12, grieta_llenado=1)]
    (r,) = rm.assess_le(hojas(tmp_path, d))
    assert any(n.startswith("ordinario: the crack water force") for n in r.notes), r.notes
    assert not any("Ordinary:" in n or "Janbu corrected:" in n for n in r.notes + r.warnings)
    out = ["m-alpha below 0.2 in 3 slices"]  # de la búsqueda, sin prefijo
    le._add_messages(out, "bishop", ["m-alpha below 0.2 in 3 slices", "Bishop did not converge"])
    le._add_messages(out, "janbu_corregido", ["Janbu corrected: the bases mix", "Bishop did not converge"])
    le._add_messages(out, "spencer", ["the bases mix"])
    assert out == ["m-alpha below 0.2 in 3 slices", "Bishop did not converge",  # sin «bishop: Bishop ...»
                   "janbu_corregido: the bases mix"]
    assert le._ky("ky not found: Spencer gave no factor of safety at some kh") == \
        "ky: not found: Spencer gave no factor of safety at some kh"


def test_kh_da_fs_estatico_y_ky_solo_en_la_primera_fila(tmp_path):
    (r,) = rm.assess_le(hojas(tmp_path, acads3b_data(kh=0.05)))
    assert r.kh == 0.05 and len(r.static_results) == len(r.results) == 2
    (tmp_path / "sin").mkdir()
    (r0,) = rm.assess_le(hojas(tmp_path / "sin", acads3b_data()))
    assert [x.factor_of_safety for x in r.static_results] == [x.factor_of_safety for x in r0.results]
    assert r0.static_results == () and le.le_static_fs(r0) == [x.factor_of_safety for x in r0.results]
    assert all(s.factor_of_safety > p.factor_of_safety for s, p in zip(r.static_results, r.results))
    assert r.ky_on_critical and not any(n.startswith("ky computed on a different") for n in r.notes)
    _, filas = leer(le.save_le_results([r], tmp_path / "res.csv"))
    assert [f["kh"] for f in filas] == ["0.05", "0.05"]
    assert [float(f["fs_estatico"]) for f in filas] == pytest.approx(le.le_static_fs(r))
    assert filas[0]["ky"] != "" and filas[1]["ky"] == "" and filas[1]["desplazamiento_newmark_m"] == ""


@pytest.mark.parametrize("superficie", ["dada", "circular"])
def test_base_del_modelo_sobre_el_terreno(tmp_path, superficie):
    d = fk_data()
    an = dict(id_analisis="AFK-ZZSENT", id_seccion="SFK-ZZSENT", metodos="bishop", base_modelo_m=70.25)
    if superficie == "dada":
        d["Geometria"] += G("SFK-ZZSENT", "ZZSENTLg", [(40, 60), (90, 32), (130, 22), (150, 20)])
        an.update(superficie="dada", linea_superficie="ZZSENTLg")
    else:
        an.update(superficie="circular", malla_x_min=110, malla_x_max=130, malla_y_min=80, malla_y_max=100)
    d["Analisis_LE"] = [ana(**an)]
    with pytest.raises(ValueError, match=r"^sheet 'Analisis_LE', row 2, column 'base_modelo_m': must be below the "
                                         r"ground surface$"):
        rm.assess_le(hojas(tmp_path, d))


def test_registro_sin_sismos(tmp_path):
    files = hojas(tmp_path, acads3b_data(registro="R-ZZSENT"))
    files.pop("Sismos", None)
    with pytest.raises(ValueError, match=r"^sheet 'Analisis_LE', row 2, column 'registro': no accelerogram given "
                                         r"\(use --records or a Sismos sheet\)$"):
        rm.assess_le(files)


def test_avance_por_analisis(tmp_path):
    vistos = []
    rm.assess_le(hojas(tmp_path, merge(fk_data(), acads3b_data())), progress=lambda k, n: vistos.append((k, n)))
    assert vistos == [(1, 2), (2, 2)]


def test_fs_estatico_sobre_la_critica_estatica(tmp_path):
    def fk(kh, sub):
        d = fk_data()
        d["Analisis_LE"] = [ana(id_analisis="AFK-ZZSENT", id_seccion="SFK-ZZSENT", metodos="bishop;spencer",
                                superficie="circular", malla_x_min=110, malla_x_max=130, malla_y_min=80,
                                malla_y_max=100, base_modelo_m=10, kh=kh)]
        (tmp_path / sub).mkdir()
        (r,) = rm.assess_le(hojas(tmp_path / sub, d))
        return r

    r0, r = fk("", "seco"), fk(0.15, "kh")
    assert r0.static_surface is None and r0.static_results == ()
    assert le.le_static_fs(r0) == [x.factor_of_safety for x in r0.results]  # con kh = 0, el mismo FS, bit a bit
    c0, c = r0.surface.circle, r.static_surface.circle
    assert (c.xc, c.yc, c.radius) == (c0.xc, c0.yc, c0.radius)  # la crítica estática, no la sísmica
    assert le.le_static_fs(r) == [x.factor_of_safety for x in r0.results]
    assert "static FS on the static critical surface" in r.notes
    assert "static FS on the static critical surface" not in r0.notes
