# Histórico de la mina (Fase 4, tareas 2 y 5): lectura de la plantilla, resultados de desempeño y auditoría.
# Solo datos sintéticos (L001, Z1, T0001); ZZSENT es el centinela de privacidad (R13).
import contextlib
import datetime
import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

import rockmasspy as rm
from rockmasspy import excel_io, history as h

openpyxl = pytest.importorskip("openpyxl")

RAIZ = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("plantilla_historico", RAIZ / "tools" / "plantilla_historico.py")
PH = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(PH)
NO_LEIDAS = {"codigo_mina", "evaluador_codigo", "observaciones"}
D = datetime.date


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory):
    p = tmp_path_factory.mktemp("plantilla") / "vacia.xlsx"
    PH.main(str(p))
    return p


@pytest.fixture
def libro(_plantilla, tmp_path):
    """Copia la plantilla vacía y la llena: libro({hoja: [ {columna: valor} ]}) -> ruta."""
    def llenar(hojas):
        p = tmp_path / "historico.xlsx"
        shutil.copy(_plantilla, p)
        wb = openpyxl.load_workbook(p)
        for hoja, filas in hojas.items():
            ws = wb[hoja]
            cab = [c.value for c in ws[1]]
            for r, fila in enumerate(filas, 2):
                for k, v in fila.items():
                    ws.cell(r, cab.index(k) + 1, v)
        wb.save(p)
        return p
    return llenar


TIPOS = [{"codigo_tipo": "I", "orden": 1, "descripcion": "Pernos", "perno_tipo": "Split Set", "perno_longitud_m": 1.8,
          "perno_espaciamiento_m": 1.5},
         {"codigo_tipo": "II", "orden": 2, "perno_tipo": "Swellex", "perno_longitud_m": 2.4,
          "perno_espaciamiento_m": 1.2, "shotcrete_espesor_mm": 50, "shotcrete_fibra": "Sí"}]


def tramo(id_tramo="T0001", fila=2, **kw):
    """HistoryTramo con todo vacío salvo lo dado (para probar la auditoría sin archivos)."""
    return rm.HistoryTramo(**{**dict.fromkeys(rm.HISTORY_TRAMO_COLUMNS), "id_tramo": id_tramo, **kw}, fila=fila)


def insp(id_tramo, fecha, estado, fila=2):
    return rm.Inspection(id_tramo, fecha, estado, None, None, None, None, None, fila)


def tipo(code, orden):
    return rm.SupportTypeDef(code, orden, "", rm.SupportType(code, orden), orden + 1)


def hallazgos(audit):
    """Hallazgos por tramo: sin los de celdas vacías por columna, que tienen su propia prueba."""
    return [f for f in audit.findings if f.kind != "missing_values"]


def kinds(audit):
    return [(f.kind, f.id_tramo) for f in hallazgos(audit)]


# --- lectura ---

def test_columnas_coinciden_con_la_plantilla():
    cols = lambda hoja: [c[1] for c in PH.COLUMNAS if c[0] == hoja and c[1] not in NO_LEIDAS]
    assert list(rm.HISTORY_TRAMO_COLUMNS) == cols("Tramos")
    assert list(rm.INSPECTION_COLUMNS) == cols("Desempeno")
    assert list(excel_io.TIPOS) == cols("Tipos_sostenimiento")


def test_excel_lee_las_tres_hojas(libro):
    p = libro({"Tramos": [{"id_tramo": "T0001", "codigo_mina": "Cliente A", "labor_codigo": "L001", "zona_nivel": "Z1",
                           "tipo_labor": "Galería", "fecha_evaluacion": D(2026, 1, 5), "luz_m": 4.5, "rqd_pct": 80,
                           "gsi_celda": " f / r ", "sost_instalado": "I", "fecha_instalacion": D(2026, 1, 7),
                           "evaluador_codigo": "E01", "observaciones": "nota", "litologia": "Andesita"},
                          {"id_tramo": "T0002", "fecha_evaluacion": "2026-02-01"}],
               "Tipos_sostenimiento": TIPOS,
               "Desempeno": [{"id_tramo": "T0001", "fecha_inspeccion": D(2026, 3, 1), "estado": "falla",
                              "tipo_falla": "Caída de cuña", "volumen_m3": 2.5}]})
    hi = rm.load_history(p)
    t = hi.tramos[0]
    assert (t.id_tramo, t.labor_codigo, t.zona_nivel, t.fila) == ("T0001", "L001", "Z1", 2)
    assert (t.fecha_evaluacion, t.fecha_instalacion, t.luz_m, t.gsi_celda) == ("2026-01-05", "2026-01-07", 4.5, "F/R")
    assert hi.tramos[1].fecha_evaluacion == "2026-02-01" and hi.tramos[1].luz_m is None
    assert not hasattr(t, "codigo_mina") and not hasattr(t, "observaciones") and not hasattr(t, "evaluador_codigo")
    assert "L001" not in repr(t) and "Z1" not in repr(t) and "Andesita" not in repr(t)
    s = hi.support_types
    assert [(x.codigo_tipo, x.orden, x.fila) for x in s] == [("I", 1, 2), ("II", 2, 3)]
    assert s[0].descripcion == "Pernos" and s[0].elementos.bolt.length_m == 1.8 and s[1].elementos.shotcrete.fiber
    i = hi.inspections[0]
    assert (i.id_tramo, i.fecha_inspeccion, i.estado, i.tipo_falla, i.volumen_m3, i.fila) == \
        ("T0001", "2026-03-01", "Falla", "Caída de cuña", 2.5, 2)


def test_hojas_opcionales_faltan(tmp_path):
    wb = openpyxl.Workbook()
    wb.active.title = "Tramos"
    wb.active.append(["id_tramo", "rmr_valor"])
    wb.active.append(["T0001", 60])
    wb.save(tmp_path / "solo.xlsx")
    hi = rm.load_history(tmp_path / "solo.xlsx")
    assert hi.tramos[0].rmr_valor == 60 and hi.support_types == () and hi.inspections == ()


def test_falta_tramos(tmp_path):
    wb = openpyxl.Workbook()
    wb.active.title = "Desempeno"
    wb.save(tmp_path / "x.xlsx")
    with pytest.raises(ValueError, match="missing sheet 'Tramos'"):
        rm.load_history(tmp_path / "x.xlsx")
    (tmp_path / "csv").mkdir()
    with pytest.raises(ValueError, match="missing file 'Tramos.csv'"):
        rm.load_history(tmp_path / "csv")
    (tmp_path / "x.txt").write_text("a")
    with pytest.raises(ValueError, match="unsupported history input"):
        rm.load_history(tmp_path / "x.txt")


def test_archivo_inexistente_o_invalido_sin_ruta(tmp_path):
    for p, msg in [(tmp_path / "ZZSENT.xlsx", "history file not found"),
                   (tmp_path / "ZZSENT", "history folder not found")]:
        with pytest.raises(FileNotFoundError, match=msg) as e:
            rm.load_history(p)
        assert "ZZSENT" not in str(e.value)
    (tmp_path / "ZZSENT.xlsx").write_text("no es un xlsx")
    with pytest.raises(ValueError, match="history file is not a valid .xlsx file") as e:
        rm.load_history(tmp_path / "ZZSENT.xlsx")
    assert "ZZSENT" not in str(e.value)
    (tmp_path / "ZZSENT.txt").write_text("a")
    with pytest.raises(ValueError, match="unsupported history input") as e:
        rm.load_history(tmp_path / "ZZSENT.txt")
    assert "ZZSENT" not in str(e.value)


def test_csv_carpeta_igual_que_excel(libro, tmp_path):
    d = tmp_path / "csv"
    d.mkdir()
    # nombres en minúsculas, ';' con coma decimal y fecha día/mes/año, como exporta Excel en es-PE
    (d / "tramos.csv").write_text("id_tramo;labor_codigo;luz_m;fecha_instalacion\nT0001;L001;4,5;7/1/2026\n",
                                  encoding="utf-8")
    (d / "TIPOS_SOSTENIMIENTO.csv").write_text(
        ";".join(excel_io.TIPOS) + "\nI;1;Pernos;Split Set;1,8;1,5;;;;;\n", encoding="utf-8")
    (d / "Desempeno.csv").write_text("id_tramo,fecha_inspeccion,estado\nT0001,2026-03-01,Estable\n", encoding="utf-8")
    hc = rm.load_history(d)
    hx = rm.load_history(libro({"Tramos": [{"id_tramo": "T0001", "labor_codigo": "L001", "luz_m": 4.5,
                                            "fecha_instalacion": D(2026, 1, 7)}],
                                "Tipos_sostenimiento": TIPOS[:1],
                                "Desempeno": [{"id_tramo": "T0001", "fecha_inspeccion": "2026-03-01",
                                               "estado": "Estable"}]}))
    assert hc == hx


def test_mapeo_de_columnas(tmp_path):
    wb = openpyxl.Workbook()
    wb.active.title = "Tramos"
    wb.active.append(["ID", "RMR ", "Labor"])
    wb.active.append(["T0001", 70, "L001"])
    wb.save(tmp_path / "m.xlsx")
    t = rm.load_history(tmp_path / "m.xlsx", column_map={"id": "id_tramo", "rmr": "rmr_valor",
                                                         "Labor": "labor_codigo"}).tramos[0]
    assert (t.id_tramo, t.rmr_valor, t.labor_codigo) == ("T0001", 70, "L001")
    with pytest.raises(ValueError, match="valid names: id_tramo"):
        rm.load_history(tmp_path / "m.xlsx", column_map={"ID": "codigo_mina"})  # no se lee: no es un nombre válido


_ERRORES = [({"Tramos": [{"id_tramo": "ZZSENT-T1", "zona_nivel": "ZZSENT", "norte_m": "ZZSENT"}]},
             "sheet 'Tramos', row 2, column 'norte_m': invalid value"),
            ({"Tramos": [{"id_tramo": "ZZSENT-T1", "cota_m": "ZZSENT"}]},
             "sheet 'Tramos', row 2, column 'cota_m': invalid value"),
            ({"Tramos": [{"id_tramo": "ZZSENT-T1", "litologia": "ZZSENT", "luz_m": "x"}]},
             "sheet 'Tramos', row 2, column 'luz_m': expected a number, got 'x'"),
            ({"Tramos": [{"id_tramo": "ZZSENT-T1", "fecha_instalacion": "31/31/2026"}]},
             "sheet 'Tramos', row 2, column 'fecha_instalacion': expected a date yyyy-mm-dd"),
            ({"Tramos": [{"id_tramo": "ZZSENT-T1", "labor_codigo": "ZZSENT"}, {"id_tramo": "ZZSENT-T1"}]},
             "sheet 'Tramos': duplicate id_tramo in rows 2 and 3"),
            ({"Tramos": [{"labor_codigo": "ZZSENT", "luz_m": 4}]},
             "sheet 'Tramos', row 2, column 'id_tramo': required value is empty"),
            ({"Tramos": [{"id_tramo": "T1"}], "Desempeno": [{"id_tramo": "ZZSENT-T1", "fecha_inspeccion": "2026-1-1",
                                                              "estado": "Estable"}]},
             "sheet 'Desempeno', row 2, column 'fecha_inspeccion': expected a date"),
            ({"Tramos": [{"id_tramo": "T1"}], "Desempeno": [{"id_tramo": "ZZSENT-T1",
                                                              "fecha_inspeccion": "2026-01-01", "estado": "Roto"}]},
             "sheet 'Desempeno', row 2, column 'estado': expected one of Estable, Falla, Reparado, Abandonado"),
            ({"Tramos": [{"id_tramo": "T1"}], "Desempeno": [{"id_tramo": "ZZSENT-T1", "estado": "Falla"}]},
             "sheet 'Desempeno', row 2, column 'fecha_inspeccion': required value is empty")]


def carpeta_csv(d, hojas):
    """Una carpeta con un CSV por hoja; la cabecera lleva las columnas obligatorias aunque vengan vacías."""
    base = {"Tramos": ["id_tramo"], "Desempeno": ["id_tramo", "fecha_inspeccion", "estado"]}
    d.mkdir()
    for hoja, filas in hojas.items():
        cab = list(dict.fromkeys([*base.get(hoja, []), *(k for f in filas for k in f)]))
        lineas = [",".join(cab)] + [",".join(str(f.get(k, "")) for k in cab) for f in filas]
        (d / f"{hoja}.csv").write_text("".join(f"{x}\n" for x in lineas), encoding="utf-8")
    return d


def test_errores_con_fila_y_columna_sin_ids_xlsx(libro):
    with pytest.raises(ValueError, match="sheet 'Tramos', row 2, column 'este_m': invalid value") as e:
        rm.load_history(libro({"Tramos": [{"id_tramo": "ZZSENT-T1", "labor_codigo": "ZZSENT", "este_m": "ZZSENT"}]}))
    assert "ZZSENT" not in str(e.value)


@pytest.mark.parametrize("hojas, msg", _ERRORES)
def test_errores_con_fila_y_columna_sin_ids(tmp_path, hojas, msg):
    with pytest.raises(ValueError, match=msg) as e:
        rm.load_history(carpeta_csv(tmp_path / "csv", hojas))
    assert "ZZSENT" not in str(e.value)


@contextlib.contextmanager
def bloqueado(path):
    """Abre `path` en exclusiva (sin compartir), como Excel con el libro abierto. Solo en Windows."""
    if sys.platform != "win32":
        pytest.skip("the exclusive lock uses CreateFileW (Windows only)")
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateFileW.restype = wintypes.HANDLE
    k32.CreateFileW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
                                wintypes.DWORD, wintypes.HANDLE)
    k32.CloseHandle.argtypes = (wintypes.HANDLE,)
    # GENERIC_READ, share mode 0 (nadie más lo abre), OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL
    h = k32.CreateFileW(str(path), 0x80000000, 0, None, 3, 0x80, None)
    if h in (None, ctypes.c_void_p(-1).value):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        yield
    finally:
        k32.CloseHandle(h)


def test_archivo_bloqueado_sin_ruta(libro, tmp_path):
    p = tmp_path / "ZZSENT-mina" / "ZZSENT.xlsx"
    p.parent.mkdir()
    p.write_bytes(libro({"Tramos": [{"id_tramo": "T1"}]}).read_bytes())
    with bloqueado(p), pytest.raises(OSError) as e:
        rm.load_history(p)
    assert str(e.value) == "history file could not be read (in use or no permission)"
    assert e.value.__cause__ is None and e.value.__suppress_context__
    d = carpeta_csv(tmp_path / "ZZSENT-csv", {"Tramos": [{"id_tramo": "T1"}]})
    with bloqueado(d / "Tramos.csv"), pytest.raises(OSError) as e:
        rm.load_history(d)
    assert str(e.value) == "history folder could not be read (in use or no permission)"
    assert rm.load_history(p).tramos[0].id_tramo == "T1"  # sin el bloqueo se lee bien


def test_tipos_de_sostenimiento_unicos_y_orden_entero(libro):
    dup = {**TIPOS[1], "codigo_tipo": "I"}
    for tipos, msg in [([TIPOS[0], dup], "duplicate codigo_tipo in rows 2 and 3"),
                       ([TIPOS[0], {**TIPOS[1], "orden": 1}], "duplicate orden in rows 2 and 3"),
                       ([{**TIPOS[0], "orden": 1.5}], "row 2, column 'orden': expected an integer, got '1.5'"),
                       ([{**TIPOS[0], "perno_longitud_m": None}], "row 2, column 'perno_longitud_m': required")]:
        with pytest.raises(ValueError, match=msg):
            rm.load_history(libro({"Tramos": [{"id_tramo": "T1"}], "Tipos_sostenimiento": tipos}))


# --- resultados de desempeño (R9) ---

def test_outcomes():
    ts = (tramo("T1", fecha_instalacion="2026-01-01"),
          tramo("T2", fecha_instalacion="2026-01-01"),
          tramo("T3", fecha_instalacion="2026-01-01"),
          tramo("T4", fecha_evaluacion="2026-01-11"),  # sin fecha_instalacion: respaldo
          tramo("T5", fecha_instalacion="2026-01-01"),  # sin inspección: no entra
          tramo("T6"),  # sin fechas: entra sin exposición
          tramo("T7", fecha_instalacion="2026-05-01"))  # inspección anterior a la instalación
    ins = (insp("T1", "2026-03-01", "Estable"), insp("T1", "2026-02-01", "Falla"), insp("T1", "2026-04-01", "Estable"),
           insp("T2", "2026-01-31", "Reparado"),
           insp("T3", "2026-02-15", "Estable"), insp("T3", "2026-03-02", "Abandonado"),
           insp("T4", "2026-01-21", "Estable"), insp("T6", "2026-01-21", "Falla"), insp("T7", "2026-04-01", "Estable"),
           insp("T9", "2026-01-21", "Falla"))  # id inexistente: no entra
    o = {x.id_tramo: x for x in rm.tramo_outcomes(rm.History(ts, (), ins))}
    assert list(o) == ["T1", "T2", "T3", "T4", "T6", "T7"]
    assert (o["T1"].failed, o["T1"].end_date, o["T1"].exposure_days, o["T1"].inspections) == (True, "2026-02-01", 31, 3)
    assert (o["T2"].failed, o["T2"].exposure_days) == (True, 30)  # Reparado cuenta como falla
    assert (o["T3"].failed, o["T3"].end_date, o["T3"].exposure_days) == (False, "2026-03-02", 60)
    assert (o["T4"].exposure_days, o["T4"].start_from_evaluation) == (10, True)
    assert not o["T1"].start_from_evaluation
    assert (o["T6"].exposure_days, o["T6"].start_from_evaluation) == (None, False)
    assert o["T7"].exposure_days is None


# --- auditoría (R3) ---

def test_q_recalculado():
    q = 80 / 9 * 1.5 / 1 * 1 / 1
    comp = dict(rqd_pct=80, jn=9, jr=1.5, ja=1, jw=1, srf=1)
    ts = (tramo("T1", 2, q_valor=round(q, 2), **comp),  # dentro de la tolerancia
          tramo("T2", 3, q_valor=q * 1.05, q_edicion="Q-NGI-2015", **comp),
          tramo("T3", 4, q_valor=5.0, q_edicion="Q-1974", **comp),
          tramo("T4", 5, q_valor=5.0, **{**comp, "jn": -1}),
          tramo("T5", 6, q_valor=5.0, rqd_pct=80))  # sin todos los componentes: no se revisa
    a = rm.audit_history(rm.History(ts, (), ()))
    assert kinds(a) == [("q_mismatch", "T2"), ("q_mismatch", "T3"), ("not_recomputed", "T4")]
    assert "NGI2015" in hallazgos(a)[0].message and hallazgos(a)[0].fila == 3 and hallazgos(a)[0].sheet == "Tramos"
    assert "(NGI2015; parameters taken from the 1974 tables)" in hallazgos(a)[1].message  # Q-1974 se recalcula


def test_q_edicion_sin_mayusculas_y_desconocida():
    comp = dict(rqd_pct=80, jn=9, jr=1.5, ja=1, jw=1, srf=1, q_valor=5.0)
    ts = (tramo("T1", 2, q_edicion=" q-ngi-2015 ", **comp), tramo("T2", 3, q_edicion="q-1974", **comp),
          tramo("T3", 4, q_edicion="ZZSENT-ED", **comp), tramo("T4", 5, **comp))
    m = [f.message for f in hallazgos(rm.audit_history(rm.History(ts, (), ())))]
    assert m[0].endswith("(NGI2015)") and "1974 tables" in m[1]
    assert m[2].endswith("(NGI2025; unknown q_edicion, NGI2025 used)") and "ZZSENT" not in m[2]
    assert m[3].endswith("(NGI2025)")


def test_q_tolerancia_relativa_en_q_bajo():
    # Fase 5B: la tolerancia absoluta de 0.005 escondía un Q ×3 con Q < 0.0075; ahora manda |ln Q − ln Q′| ≤ ln 1.01
    # con un piso que solo cubre un Q escrito con 4 decimales
    comp = dict(rqd_pct=10, jn=20, jr=0.5, ja=8, jw=0.5, srf=10)  # Q = 0.0015625
    q = 10 / 20 * 0.5 / 8 * 0.5 / 10
    ts = (tramo("T1", 2, q_valor=round(q, 4), **comp),  # 0.0016: redondeo a 4 decimales, sin hallazgo
          tramo("T2", 3, q_valor=float(f"{q:.4g}"), **comp),  # 4 cifras significativas, sin hallazgo
          tramo("T3", 4, q_valor=3 * q, **comp), tramo("T4", 5, q_valor=q / 3, **comp),  # ×3 y ÷3 sí
          tramo("T5", 6, q_valor=0.004, **comp),  # ×2.6: antes pasaba con la tolerancia de 0.005
          tramo("T6", 7, q_valor=0.0, **comp))  # Q registrado 0: sin logaritmo, siempre hallazgo
    a = rm.audit_history(rm.History(ts, (), ()))
    assert kinds(a) == [("q_mismatch", "T3"), ("q_mismatch", "T4"), ("q_mismatch", "T5"), ("q_mismatch", "T6")]
    # Q alto: el 1 % relativo manda igual que antes
    big = dict(rqd_pct=100, jn=1, jr=4, ja=0.75, jw=1, srf=1)  # Q = 533.33
    a = rm.audit_history(rm.History((tramo("T1", q_valor=538.0, **big), tramo("T2", 3, q_valor=540.0, **big)), (), ()))
    assert kinds(a) == [("q_mismatch", "T2")]


def test_celdas_vacias_por_columna_solo_conteos():
    ts = [_usable(k, rmr_valor=60, gsi_valor=50, rqd_pct=70, jn=6, jr=2, ja=1, profundidad_m=300) for k in range(10)]
    ts[2] = _usable(2, rmr_valor=60, gsi_valor=None, rqd_pct=70, jn=6, jr=2, ja=1, profundidad_m=300)
    ts[5] = _usable(5, rmr_valor=60, gsi_valor=None, rqd_pct=70, jn=6, jr=2, ja=1, profundidad_m=None, q_valor=None)
    a = rm.audit_history(rm.History(tuple(ts), (tipo("I", 1), tipo("II", 2)), ()))
    faltan = [f for f in a.findings if f.kind == "missing_values"]
    assert [(f.sheet, f.fila, f.id_tramo) for f in faltan] == [("Tramos", None, None)] * 3
    assert [f.message for f in faltan] == [
        "column gsi_valor is empty in 2 of 10 tramos (used by level 1)",
        "column q_valor is empty in 1 of 10 tramos (used by levels 1, 2 and 3)",
        "column profundidad_m is empty in 1 of 10 tramos (used by level 3)"]
    assert rm.history_audit_counts(a)["missing_values"] == 3
    # columnas que nadie llena (jw, srf, coordenadas...) no son hallazgo: la preparación de cada nivel ya lo dice
    assert not [f for f in faltan if "jw" in f.message or "este_m" in f.message]


def test_rmr89_basico_recalculado():
    base = dict(rmr_edicion="RMR89", ucs_mpa=60, rqd_pct=80, espaciamiento_m=0.3, puntaje_condicion_juntas=20,
                agua="Húmedo")  # 7 + 17 + 10 + 20 + 10 = 64
    ts = (tramo("T1", 2, rmr_valor=65, **base),
          tramo("T2", 3, rmr_valor=59, **base),
          tramo("T3", 4, rmr_valor=40, **{**base, "rmr_edicion": "RMR76"}),
          tramo("T4", 5, rmr_valor=40, **{**base, "agua": "Lluvia"}),
          tramo("T5", 6, rmr_valor=59, **{**base, "agua": "seco"}))  # 69 con Seco
    a = rm.audit_history(rm.History(ts, (), ()))
    assert kinds(a) == [("rmr_mismatch", "T2"), ("not_recomputed", "T4"), ("rmr_mismatch", "T5")]
    assert "may include the orientation adjustment" in hallazgos(a)[0].message
    assert "basic RMR89 64" in hallazgos(a)[0].message and "basic RMR89 69" in hallazgos(a)[2].message


def test_rmr_edicion_normalizada():
    base = dict(ucs_mpa=60, rqd_pct=80, espaciamiento_m=0.3, puntaje_condicion_juntas=20, agua="Húmedo", rmr_valor=50)
    ts = tuple(tramo(f"T{k}", k + 2, rmr_edicion=e, **base) for k, e in enumerate(["RMR-89", "rmr 89", "RMR89 "]))
    assert [k for k, _ in kinds(rm.audit_history(rm.History(ts, (), ())))] == ["rmr_mismatch"] * 3


def test_registros_no_independientes():
    comp = dict(rqd_pct=70, jn=6, jr=2, ja=1, jw=1, srf=1)
    ts = (tramo("T1", 2, labor_codigo="L001", progresiva_inicio_m=0, progresiva_fin_m=50, rqd_pct=60),
          tramo("T2", 3, labor_codigo="L001", progresiva_inicio_m=10, progresiva_fin_m=20, rqd_pct=61),
          tramo("T3", 4, labor_codigo="L001", progresiva_inicio_m=30, progresiva_fin_m=40, rqd_pct=62),  # no contiguo
          tramo("T4", 5, labor_codigo="L001", progresiva_inicio_m=50, progresiva_fin_m=60, rqd_pct=63),  # toca: no
          tramo("T5", 6, labor_codigo="L002", progresiva_inicio_m=0, progresiva_fin_m=10, **comp),
          tramo("T6", 7, labor_codigo="L002", progresiva_inicio_m=10, progresiva_fin_m=20, **comp),
          tramo("T7", 8, labor_codigo="L003", progresiva_inicio_m=5, progresiva_fin_m=9, **comp),  # otra labor
          tramo("T8", 9, labor_codigo="L004"), tramo("T9", 10, labor_codigo="L004"))  # sin componentes: no
    a = rm.audit_history(rm.History(ts, (), ()))
    assert kinds(a) == [("overlapping_chainage", "T2"), ("overlapping_chainage", "T3"),
                        ("repeated_components", "T6")]
    assert "row 2" in hallazgos(a)[1].message and "not independent" in hallazgos(a)[2].message


def test_progresiva_al_reves_y_clave_de_labor():
    ts = (tramo("T1", 2, labor_codigo="L001", zona_nivel="Z1", progresiva_inicio_m=50, progresiva_fin_m=0),
          tramo("T2", 3, labor_codigo="L001", zona_nivel="Z1", progresiva_inicio_m=20, progresiva_fin_m=10),
          tramo("T3", 4, labor_codigo="L001", zona_nivel="Z2", progresiva_inicio_m=10, progresiva_fin_m=20),  # otra zona
          tramo("T4", 5, labor_codigo="L001", progresiva_inicio_m=60, progresiva_fin_m=70, rqd_pct=70),
          tramo("T5", 6, labor_codigo="L001", progresiva_inicio_m=70, progresiva_fin_m=80, rqd_pct=70))  # 1 componente
    a = rm.audit_history(rm.History(ts, (), ()))
    assert kinds(a) == [("overlapping_chainage", "T2")] and "row 2" in hallazgos(a)[0].message
    assert [rm.labor_key(t) for t in ts[2:4]] == [("Z2", "L001"), (None, "L001")]
    assert rm.labor_key(tramo("T9")) is None


def test_componentes_repetidos_exigen_dos():
    ts = (tramo("T1", 2, labor_codigo="L001", rqd_pct=70, jn=6), tramo("T2", 3, labor_codigo="L001", rqd_pct=70, jn=6))
    assert kinds(rm.audit_history(rm.History(ts, (), ()))) == [("repeated_components", "T2")]


def test_coherencia_entre_hojas():
    ts = (tramo("T1", 2, sost_instalado="I", sost_recomendado="IV", fecha_instalacion="2026-02-01"),
          tramo("T2", 3, sost_instalado="X"))
    ins = (insp("T1", "2026-01-15", "Estable", 2), insp("T1", "2026-02-01", "Estable", 3), insp("T9", "2026-03-01",
                                                                                                "Falla", 4))
    a = rm.audit_history(rm.History(ts, (tipo("I", 1), tipo("II", 2)), ins))
    assert [(f.kind, f.sheet, f.fila, f.id_tramo) for f in hallazgos(a)] == [
        ("unknown_support", "Tramos", 2, "T1"), ("unknown_support", "Tramos", 3, "T2"),
        ("inspection_before_installation", "Desempeno", 2, "T1"), ("unknown_tramo", "Desempeno", 4, "T9")]
    assert "sost_recomendado 'IV'" in hallazgos(a)[0].message


def test_sin_tipos_de_sostenimiento_un_solo_hallazgo():
    ts = tuple(tramo(f"T{k}", k + 2, sost_instalado="I") for k in range(5)) + (tramo("T9", 9),)
    a = rm.audit_history(rm.History(ts, (), ()))
    assert [(f.kind, f.sheet, f.fila, f.id_tramo) for f in hallazgos(a)] == [
        ("unknown_support", "Tipos_sostenimiento", None, None)]
    assert "5 tramos" in hallazgos(a)[0].message


def test_inspeccion_despues_de_abandonado():
    ts = (tramo("T1", fecha_instalacion="2026-01-01"),)
    ins = (insp("T1", "2026-03-01", "Falla", 4), insp("T1", "2026-02-01", "Abandonado", 3),
           insp("T1", "2026-01-15", "Estable", 2))
    hi = rm.History(ts, (), ins)
    o = rm.tramo_outcomes(hi)[0]
    assert (o.failed, o.end_date, o.exposure_days, o.inspections) == (False, "2026-02-01", 31, 2)
    assert [(f.kind, f.fila) for f in rm.audit_history(hi).findings] == [("inspection_after_abandonment", 4)]


def test_exposicion_de_cero_dias_se_recorta_a_uno():
    hi = rm.History((tramo("T1", fecha_instalacion="2026-01-01"),), (), (insp("T1", "2026-01-01", "Falla"),))
    assert rm.tramo_outcomes(hi)[0].exposure_days == 1


def _usable(k, **kw):
    """Tramo completo para los niveles 2 y 3: Q, luz, ESR, tipo definido y fecha de instalación."""
    # cada labor en una sola zona: la clave (zona, labor) da 6 labores
    base = dict(labor_codigo=f"L{k % 6:03d}", zona_nivel=f"Z{k % 6 % 3}", q_valor=5, luz_m=4, esr=1.6,
                rmr_edicion="RMR89", sost_instalado="I" if k % 2 else "II", fecha_instalacion="2026-01-01",
                tipo_labor="Galería")
    return tramo(f"T{k:04d}", k + 2, **{**base, **kw})


def test_preparacion_niveles_1_y_2_solo_filas_usables():
    ts = [_usable(k, rmr_valor=60, gsi_valor=55 if k < 20 else None, rqd_pct=50 + k, jn=6, jr=2, ja=1)
          for k in range(40)]
    ts[0] = _usable(0, rmr_valor=60, q_valor=0)  # Q = 0: no hay ln Q
    ts[1] = _usable(1, rmr_valor=60, esr=None)  # sin ESR: no cuenta en el nivel 2
    ts[3] = _usable(3, rmr_valor=60, sost_instalado="Z")  # tipo no definido
    a = rm.audit_history(rm.History(tuple(ts), (tipo("I", 1), tipo("II", 2), tipo("III", 3)), ()))
    r = {(x.level, x.item): x for x in a.readiness}
    assert list(r) == [(1, "rmr_from_q"), (1, "gsi_from_rmr"), (1, "gsi_from_q_prime"),
                       (2, "I"), (2, "II"), (2, "III"), (3, "performance")]
    assert r[1, "rmr_from_q"].counts == {"pairs": 39, "labors": 6, "total": 40} and r[1, "rmr_from_q"].ready
    assert r[1, "gsi_from_rmr"].counts == {"pairs": 17, "labors": 6, "total": 40}
    assert r[1, "gsi_from_rmr"].missing == {"pairs": 13, "labors": 0} and not r[1, "gsi_from_rmr"].ready
    assert r[2, "I"].counts == {"tramos": 18, "labors": 3, "total": 19} and not r[2, "I"].ready  # impares: 3 labores
    assert r[2, "II"].counts == {"tramos": 19, "labors": 3, "total": 20}
    assert r[2, "III"].counts == {"tramos": 0, "labors": 0, "total": 0}
    c = rm.history_audit_counts(a)
    assert (c["tramos"], c["support_types"], c["inspections"], c["items_ready"]) == (40, 3, 0, 1)
    assert "levels_ready" not in c and set(rm.FINDING_KINDS) <= set(c)


def test_preparacion_nivel_3_clase_menor_y_parametros():
    ts = [_usable(k) for k in range(60)]
    ts[0] = _usable(0, luz_m=None)  # no usable
    ins = [insp(f"T{k:04d}", "2026-03-01", "Falla" if k < 15 else "Estable") for k in range(50)]
    p = rm.audit_history(rm.History(tuple(ts), (tipo("I", 1), tipo("II", 2)), tuple(ins))).readiness[-1]
    assert p.counts == {"minority_class": 14, "zones": 3, "usable": 49, "failures": 14, "non_failures": 35,
                        "parameters": 3, "failures_total": 15, "tramos": 60, "tramos_with_inspections": 50,
                        "tramos_without_inspections": 10, "start_from_evaluation": 0, "without_exposure": 0}
    assert p.minimums == {"minority_class": 30, "zones": 3} and p.missing == {"minority_class": 16, "zones": 0}
    # profundidad en todas las filas usables: +1; tres tipos de labor: +2
    ts = [_usable(k, profundidad_m=300, tipo_labor=("Galería", "Rampa", "Crucero")[k % 3]) for k in range(60)]
    p = rm.audit_history(rm.History(tuple(ts), (tipo("I", 1), tipo("II", 2)), tuple(ins))).readiness[-1]
    assert p.counts["parameters"] == 6 and p.minimums["minority_class"] == 60


def test_centinela_no_aparece_en_mensajes(libro):
    """R13: ZZSENT en id, labor, zona y litología; los hallazgos lo llevan en campos, nunca en el texto."""
    s = "ZZSENT"
    comp = dict(rqd_pct=80, jn=9, jr=1.5, ja=1, jw=1, srf=1, ucs_mpa=60, espaciamiento_m=0.3,
                puntaje_condicion_juntas=20, agua="Húmedo", rmr_edicion="RMR89", rmr_valor=50, q_valor=99,
                q_edicion=s)  # edición desconocida: la nota no la repite
    filas = [{"id_tramo": f"{s}-T{k}", "labor_codigo": f"{s}-L", "zona_nivel": f"{s}-Z", "litologia": s,
              "este_m": 1000.5 + k, "norte_m": 2000.5, "progresiva_inicio_m": 0, "progresiva_fin_m": 10,
              "sost_instalado": "IV", "fecha_instalacion": D(2026, 2, 1), **comp} for k in (1, 2)]
    p = libro({"Tramos": filas, "Tipos_sostenimiento": TIPOS,
               "Desempeno": [{"id_tramo": f"{s}-T1", "fecha_inspeccion": D(2026, 1, 1), "estado": "Falla"},
                             {"id_tramo": f"{s}-T9", "fecha_inspeccion": D(2026, 3, 1), "estado": "Falla"}]})
    hi = rm.load_history(p)
    assert hi.tramos[0].labor_codigo == f"{s}-L" and hi.tramos[0].este_m == 1001.5
    a = rm.audit_history(hi)
    assert {f.kind for f in a.findings} == {"q_mismatch", "rmr_mismatch", "overlapping_chainage",
                                            "repeated_components", "unknown_support", "unknown_tramo",
                                            "inspection_before_installation"}
    assert all(f.id_tramo.startswith(s) for f in a.findings)
    textos = [f.message for f in a.findings] + [str(r) for r in a.readiness] + [str(rm.history_audit_counts(a))]
    assert not [x for x in textos if s in x]


def test_q_prime_fuera_de_dominio_es_hallazgo_y_no_cuenta_en_el_nivel_1():
    ts = (tramo("T1", 2, gsi_valor=50, rqd_pct=150, jn=6, jr=2, ja=1),  # sin Q completo: lo reporta el Q′
          tramo("T2", 3, gsi_valor=50, rqd_pct=80, jn=0, jr=2, ja=1),
          tramo("T3", 4, gsi_valor=50, rqd_pct=80, jn=6, jr=2, ja=0, q_valor=5, jw=1, srf=1),  # ya lo dice _audit_q
          tramo("T4", 5, gsi_valor=50, rqd_pct=80, jn=6, jr=2, ja=1))
    h = rm.History(ts, (), ())
    a = rm.audit_history(h)
    assert kinds(a) == [("not_recomputed", "T1"), ("not_recomputed", "T2"), ("not_recomputed", "T3")]
    assert [f.message.startswith("Q' not computable") for f in hallazgos(a)] == [True, True, False]
    assert {r.item: r.counts["pairs"] for r in a.readiness if r.level == 1}["gsi_from_q_prime"] == 1
    sel = rm.level1_rows(h, "gsi_from_q_prime")
    assert [t.id_tramo for t in sel.tramos] == ["T4"] and sel.excluded_x == 3
    assert sel.x == pytest.approx((80 / 6 * 2,))


def test_nivel_1_usa_la_edicion_mayoritaria_de_rmr():
    ts = tuple(tramo(f"T{k}", k + 2, q_valor=5, rmr_valor=60, rmr_edicion=e)
               for k, e in enumerate(["RMR89", "RMR-89", "RMR76", None, "RMR14", "rmr 89"]))
    h = rm.History(ts, (), ())
    sel = rm.level1_rows(h, "rmr_from_q")
    assert (sel.edition, len(sel.tramos), sel.excluded_edition) == ("RMR89", 3, 3)
    assert rm.level1_rows(h, "rmr_from_q", rmr_edition="RMR-76").edition == "RMR76"
    assert rm.level1_rows(rm.History(ts[3:5], (), ()), "rmr_from_q").edition is None
    with pytest.raises(ValueError, match="rmr_edition"):
        rm.level1_rows(h, "rmr_from_q", rmr_edition="RMR14")
