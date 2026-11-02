import csv as csvlib

import pytest

import rockmasspy as rm

CAB = ("id_superficie,q_prima,rqd_pct,jn,jr,ja,ucs_mpa,sigma1_mpa,dif_buz_junta_deg,modo_falla,"
       "inclinacion_cara_deg,buz_junta_deg,area_m2,perimetro_m,ancho_m,largo_m,labor_codigo,este_m,observaciones")
FILAS = [
    "S1,10,,,,,100,20,45,,90,,100,40,,,L-1,123,SECRETO-123",
    "S2,,80,9,1.5,1,100,20,45,gravedad,0,,,,10,20,L-2,124,SECRETO-123",
    "S3,2,,,,,60,40,10,Deslizamiento,,60,60,32,,,L-3,125,SECRETO-123",
    "S4,0.5,,,,,60,40,10,gravedad,90,,40,30,,,L-4,126,SECRETO-123",
    "S5,40,,,,,150,10,90,gravedad,90,,50,30,,,L-5,127,SECRETO-123",
    "S6,0.3,,,,,60,40,10,gravedad,45,,300,70,,,L-6,128,SECRETO-123",
]


def csv(tmp_path, filas=FILAS, cab=CAB, nombre="Superficies.csv"):
    p = tmp_path / nombre
    p.write_text("\n".join([cab, *filas]) + "\n", encoding="utf-8")
    return p


def una(tmp_path, fila, cab=CAB):
    return csv(tmp_path, [fila], cab)


def evaluar(p):
    return rm.assess_stope_surfaces(rm.load_stope_surfaces(p))


def test_ida_y_vuelta_csv_y_excel(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    a = rm.load_stope_surfaces(csv(tmp_path))
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Superficies"
    for linea in [CAB, *FILAS]:
        ws.append([None if c == "" else (float(c) if c.replace(".", "").isdigit() else c) for c in linea.split(",")])
    wb.save(tmp_path / "s.xlsx")
    b = rm.load_stope_surfaces(tmp_path / "s.xlsx")
    assert a == b and len(a) == 6
    assert a[0].dif_rumbo_junta_deg == 0.0 and a[0].modo_falla == "gravedad" and a[0].q_edicion == "Q-NGI-2025"
    assert a[2].modo_falla == "deslizamiento" and a[0].fila == 2


def test_q_prima_de_parametros(tmp_path):
    r = evaluar(csv(tmp_path))[1].mathews
    assert r.q_prime == pytest.approx(13.333333, abs=1e-6)
    assert "Q-NGI-2025" in [m.method_id for m in r.methods]


def test_geometria_por_area_y_por_ancho_largo(tmp_path):
    rs = evaluar(csv(tmp_path))
    assert rs[0].mathews.hr_m == pytest.approx(2.5) and rs[1].mathews.hr_m == pytest.approx(200 / 60)


def test_column_map(tmp_path):
    p = una(tmp_path, "S1,10,,,,,100,20,45,,90,,100,40,,,,,", CAB.replace("q_prima", "Q prima"))
    s = rm.load_stope_surfaces(p, column_map={"Q prima": "q_prima"})
    assert s[0].q_prima == 10


def test_conteo_y_guardado(tmp_path):
    rs = evaluar(csv(tmp_path))
    c = rm.stope_zone_counts(rs)
    assert set(c) == {1, 2, 3} and sum(c.values()) == 6
    out = rm.save_stope_results(rs, tmp_path / "r.csv")
    with open(out, encoding="utf-8-sig", newline="") as fh:
        cab = next(csvlib.reader(fh, delimiter=rm.batch._system_csv_format()[0]))
    assert len(cab) == 13 and cab[0] == "id_superficie" and cab[-1] == "avisos"
    openpyxl = pytest.importorskip("openpyxl")
    x = rm.save_stope_results(rs, tmp_path / "r.xlsx")
    assert openpyxl.load_workbook(x).sheetnames == ["Superficies_resultados"]


def test_area_imposible_para_su_perimetro(tmp_path):
    with pytest.raises(ValueError) as e:
        evaluar(una(tmp_path, "S1,10,,,,,100,20,45,,90,,130,40,,,,,"))
    m = str(e.value)
    assert "row 2" in m and "area too large" in m


@pytest.mark.parametrize("fila,col", [
    ("S1,10,,,,,100,20,45,,90,,,,0,20,,,", "ancho_m"),
    ("S1,10,,,,,100,20,45,,90,,100,,,,,,", "perimetro_m"),
    ("S1,10,,,,,100,20,45,,90,,100,40,10,20,,,", "ancho_m"),
    ("S1,10,,,,,100,20,45,,90,,,,,,,,", "area_m2"),
    ("S1,,80,,1.5,1,100,20,45,,90,,100,40,,,,,", "jn"),
    ("S1,10,80,9,1.5,1,100,20,45,,90,,100,40,,,,,", "q_prima"),
    ("S1,10,,,,,,20,45,,90,,100,40,,,,,", "ucs_mpa"),
])
def test_errores_con_fila_y_columna(tmp_path, fila, col):
    with pytest.raises(ValueError) as e:
        evaluar(una(tmp_path, fila))
    assert "row 2" in str(e.value) and f"column '{col}'" in str(e.value)


@pytest.mark.parametrize("fila", [
    "S1,10,,,,,100,20,45,deslizamiento,,,100,40,,,,,",  # sin buz_junta_deg
    "S1,10,,,,,100,20,45,volteo,90,,100,40,,,,,",
    "S1,10,,,,,100,20,45,gravedad,95,,100,40,,,,,",
])
def test_modos_y_angulos(tmp_path, fila):
    with pytest.raises(ValueError, match="row 2"):
        evaluar(una(tmp_path, fila))


def test_id_repetido(tmp_path):
    with pytest.raises(ValueError, match="duplicate id_superficie in rows 2 and 3"):
        rm.load_stope_surfaces(csv(tmp_path, [FILAS[0], FILAS[0]]))


def test_edicion_q_desconocida():
    s = rm.StopeSurface("X", None, 80, 9, 1.5, 1, "Q-1974", 100, 20, 45, 0.0, "gravedad", 90, None, 100, 40, None, None, 7)
    with pytest.raises(ValueError, match="row 7"):
        rm.assess_stope_surfaces([s])


def test_columnas_extra_no_se_leen(tmp_path):
    p = csv(tmp_path, nombre="buenas.csv")
    ss = rm.load_stope_surfaces(p)
    assert not any("SECRETO-123" in str(v) for s in ss for v in vars(s).values())
    with pytest.raises(ValueError) as e:
        evaluar(una(tmp_path, "S1,10,,,,,100,20,45,,95,,100,40,,,L-1,1,SECRETO-123"))
    assert "SECRETO-123" not in str(e.value)
    out = rm.save_stope_results(evaluar(p), tmp_path / "r.csv")
    assert "SECRETO-123" not in out.read_text(encoding="utf-8-sig")


CAB_Q = CAB + ",q_edicion"


@pytest.mark.parametrize("fila", ["S1,SECRETO-123,,,,,100,20,45,,90,,100,40,,,,,,",
                                  "S1,,80,9,1.5,1,100,20,45,,90,,100,40,,,,,,SECRETO-123"])
def test_celda_mala_no_repite_su_valor(tmp_path, fila):  # I2
    with pytest.raises(ValueError) as e:
        evaluar(una(tmp_path, fila, CAB_Q))
    m = str(e.value)
    assert "SECRETO" not in m and "row 2" in m
    assert "invalid value" in m or "q_edicion" in m


def test_nombre_real_de_la_hoja_en_errores_de_evaluacion(tmp_path):  # M1
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Otra"
    ws.append(CAB.split(","))
    ws.append([None if c == "" else (float(c) if c.replace(".", "").isdigit() else c)
               for c in "S1,10,,,,,100,20,45,,90,,130,40,,,,,".split(",")])
    wb.save(tmp_path / "s.xlsx")
    with pytest.raises(ValueError, match="sheet 'Otra', row 2"):
        rm.assess_stope_surfaces(rm.load_stope_surfaces(tmp_path / "s.xlsx", sheet="Otra"))
    p = csv(tmp_path, ["S1,10,,,,,100,20,45,,90,,130,40,,,,,"], nombre="caras.csv")
    with pytest.raises(ValueError, match="sheet 'caras', row 2"):
        evaluar(p)
    assert "hoja" not in repr(rm.load_stope_surfaces(p)[0])


def test_grafico_que_no_es_de_n_prima(tmp_path):  # M5
    with pytest.raises(ValueError, match="is not a Mathews stability graph"):
        rm.assess_stope_surfaces(rm.load_stope_surfaces(csv(tmp_path)), graph="Laubscher1994-stability")
    with pytest.raises(ValueError, match="is not a Mathews stability graph"):
        rm.mathews_stability(10, 5, ucs_mpa=100, sigma1_mpa=20, dip_difference_deg=45, surface_inclination_deg=90,
                             graph="Laubscher1994-stability")
