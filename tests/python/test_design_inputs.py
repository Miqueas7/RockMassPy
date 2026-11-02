import datetime
import re

import pytest

import rockmasspy as rm
from rockmasspy.design_inputs import DesignInputs
from rockmasspy.normative import get_profile
from rockmasspy.verify import verify

# hojas sintéticas: nombre -> (cabecera, filas)
EST = (["id_refugio", "tipo", "rmr", "distancia_frente_m", "area_m2", "aforo", "sostenido"],
       [["E1", "Roca", 65, 400, 30, 20, ""], ["E2", "Móvil", 55, 500.5, 14.9, 10, "Sí"]])
PEA = (["id_via", "via", "geometria", "espaciado_max_m"],
       [["V1", "Galería", "", 50], ["V2", "rampa", "curva", 30.5]])
QC = (["periodo", "sostenimiento", "instalados", "ensayados"],
      [["2026-01", "Perno", 100, 1], ["2026-02", "Perno", 101, 1]])
FS = (["id_analisis", "plazo", "fs"], [["A1", "corto", 1.1], ["A2", "Largo", 1.5]])
AUT = (["tipo_labor", "autosoporte_h"], [["Galería", 12], ["crucero", 30.5]])
HOJAS = {"Estaciones_refugio": EST, "Refugios_peatonales": PEA, "Resumen_QC": QC, "Factores_seguridad": FS,
         "Autosoporte": AUT}


def csv(tmp_path, nombre, cab, filas, sep=","):
    p = tmp_path / nombre
    p.write_text("\n".join(sep.join(str(c) for c in f) for f in [cab, *filas]) + "\n", encoding="utf-8")
    return p


def csvs(tmp_path, hojas=HOJAS):
    return [csv(tmp_path, f"{n}.csv", *h) for n, h in hojas.items()]


def xlsx(tmp_path, hojas=HOJAS):
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for n, (cab, filas) in hojas.items():
        ws = wb.create_sheet(n)
        ws.append(cab)
        for f in filas:
            ws.append([None if c == "" else c for c in f])
    p = tmp_path / "diseno.xlsx"
    wb.save(p)
    return p


def con(hojas, nombre, cab=None, filas=None):
    h = dict(hojas)
    c0, f0 = h[nombre]
    h[nombre] = (cab or c0, filas if filas is not None else f0)
    return h


def test_ida_y_vuelta_csv_y_excel(tmp_path):
    a = rm.load_design_inputs(csvs(tmp_path))
    d = tmp_path / "x"
    d.mkdir()
    b = rm.load_design_inputs([xlsx(d)])
    assert a == b
    assert isinstance(a, DesignInputs)
    assert [r.sostenido for r in a.refuge_stations] == [False, True]
    assert a.refuge_stations[1].tipo == "movil" and a.pedestrian_refuges[0].via == "galeria"
    assert a.pedestrian_refuges[0].geometria is None
    assert a.safety_factors[1].plazo == "largo" and a.standup[0].tipo_labor == "galeria"
    assert (a.qc[0].periodo, a.qc[0].instalados) == ("2026-01", 100)
    assert a.refuge_stations[0].aforo == 20 and isinstance(a.refuge_stations[0].aforo, int)
    assert a.refuge_stations[1].fila == 3


def test_periodo_fecha_de_excel(tmp_path):
    h = con(HOJAS, "Resumen_QC", filas=[[datetime.datetime(2026, 3, 15), "Perno", 10, 1]])
    assert rm.load_design_inputs([xlsx(tmp_path, h)]).qc[0].periodo == "2026-03"


def test_csv_fecha_dia_primero_y_coma_decimal(tmp_path):
    p = csv(tmp_path, "resumen_qc.csv", QC[0], [["15/03/2026", "Perno", 10, 1]], sep=";")
    assert rm.load_design_inputs([p]).qc[0].periodo == "2026-03"
    q = csv(tmp_path, "autosoporte.csv", AUT[0], [["galeria", "12,5"]], sep=";")
    assert rm.load_design_inputs([q]).standup[0].autosoporte_h == 12.5


def test_hojas_opcionales_y_vacio(tmp_path):
    d = rm.load_design_inputs([csv(tmp_path, "Autosoporte.csv", *AUT)])
    assert len(d.standup) == 2 and d.refuge_stations == () and d.qc == ()


def test_excel_sin_hojas_de_diseno(tmp_path):
    with pytest.raises(ValueError, match="Estaciones_refugio.*Autosoporte"):
        rm.load_design_inputs([xlsx(tmp_path, {"Otra": (["a"], [[1]])})])


def test_otro_tipo(tmp_path):
    p = tmp_path / "d.txt"
    p.write_text("x")
    with pytest.raises(ValueError, match="unsupported file type"):
        rm.load_design_inputs([p])


def test_hoja_repetida(tmp_path):
    a = csv(tmp_path, "Autosoporte.csv", *AUT)
    d = tmp_path / "otro"
    d.mkdir()
    b = csv(d, "autosoporte.csv", *AUT)
    with pytest.raises(ValueError, match="Autosoporte"):
        rm.load_design_inputs([a, b])


def falla(tmp_path, nombre, cab, filas, hoja, fila, col, valor=None):
    p = csv(tmp_path, nombre, cab, filas)
    with pytest.raises(ValueError) as e:
        rm.load_design_inputs([p])
    m = str(e.value)
    assert f"sheet '{hoja}', row {fila}, column '{col}'" in m, m
    if valor is not None:
        assert str(valor) not in m
    return m


def test_foco4_nombre_desconocido(tmp_path):
    p = csv(tmp_path, "Refugios.csv", *EST)
    with pytest.raises(ValueError, match="Estaciones_refugio"):
        rm.load_design_inputs([p])


@pytest.mark.parametrize("col,val,k", [("distancia_frente_m", "nan", 3), ("aforo", 0, 5), ("aforo", 2.5, 5),
                                       ("tipo", "flotante", 1)])
def test_foco4_estaciones(tmp_path, col, val, k):
    f = list(EST[1][0])
    f[k] = val
    falla(tmp_path, "Estaciones_refugio.csv", EST[0], [f], "Estaciones_refugio", 2, col, val)


def test_foco4_periodo(tmp_path):
    falla(tmp_path, "Resumen_QC.csv", QC[0], [["2026-13", "Perno", 1, 1]], "Resumen_QC", 2, "periodo", "2026-13")


@pytest.mark.parametrize("val", [-1, 1.5])
def test_foco4_ensayados(tmp_path, val):
    falla(tmp_path, "Resumen_QC.csv", QC[0], [["2026-01", "Perno", 5, val]], "Resumen_QC", 2, "ensayados", val)


def test_foco4_par_repetido(tmp_path):
    m = falla(tmp_path, "Resumen_QC.csv", QC[0], [["2026-01", "Perno", 5, 1], ["2026-02", "X", 5, 1],
                                                  ["2026-01", "PERNO", 5, 1]], "Resumen_QC", 4, "sostenimiento")
    assert "row 2" in m


def test_foco4_rampa_sin_geometria(tmp_path):
    falla(tmp_path, "Refugios_peatonales.csv", PEA[0], [["V1", "rampa", "", 30]], "Refugios_peatonales", 2, "geometria")


def test_foco4_sostenido_desconocido(tmp_path):
    falla(tmp_path, "Estaciones_refugio.csv", EST[0], [["E1", "roca", 65, 1, 20, 5, "quizas"]],
          "Estaciones_refugio", 2, "sostenido", "quizas")


def test_foco4_id_repetido_y_vacio(tmp_path):
    p = csv(tmp_path, "Factores_seguridad.csv", FS[0], [["SECRETO-9", "corto", 1.2], ["SECRETO-9", "corto", 1.2]])
    with pytest.raises(ValueError) as e:
        rm.load_design_inputs([p])
    assert "SECRETO-9" not in str(e.value) and "rows 2 and 3" in str(e.value)
    falla(tmp_path, "Factores_seguridad.csv", FS[0], [["A", "corto", ""]], "Factores_seguridad", 2, "fs")


def test_foco5_sin_fuga(tmp_path):
    extra = ["labor_codigo", "este_m", "observaciones"]
    hojas = {}
    for n, (cab, filas) in HOJAS.items():
        hojas[n] = ([*cab, *extra], [[*f, "SECRETO-123", "SECRETO-123", "SECRETO-123"] for f in filas])
    hojas["Estaciones_refugio"] = (hojas["Estaciones_refugio"][0],
                                   [[f"E{i}-SECRETO-123", *f[1:]] for i, f in enumerate(hojas["Estaciones_refugio"][1])])
    d = rm.load_design_inputs(csvs(tmp_path, hojas))
    assert "SECRETO-123" not in repr(d).replace("E0-SECRETO-123", "").replace("E1-SECRETO-123", "")
    r = verify(get_profile("PE-DS024-2016"), as_of="2026-11-02", design=d)
    assert all("SECRETO-123" not in f.message for f in r.findings)
    # un error en una celda numérica tampoco repite el valor
    bad = con(hojas, "Estaciones_refugio", filas=[["E-SECRETO-123", "roca", "SECRETO-123", 1, 2, 3, ""]])
    with pytest.raises(ValueError) as e:
        rm.load_design_inputs([csv(tmp_path, "Estaciones_refugio.csv", *bad["Estaciones_refugio"])])
    assert "SECRETO-123" not in str(e.value)
    assert re.search(r"sheet 'Estaciones_refugio', row 2, column 'rmr'", str(e.value))


def test_read_records_sin_id_column(tmp_path):
    from rockmasspy.csv_io import _CsvSource
    from rockmasspy.tramos import read_records
    p = csv(tmp_path, "h.csv", ["a", "b"], [[1, 2], [1, 2]])
    out = read_records(_CsvSource({"h": p}), "h", None, columns=("a", "b"), text=(), required=("a",), ident=(),
                       id_column=None)
    assert len(out) == 2
