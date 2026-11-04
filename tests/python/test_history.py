# Histórico de la mina (Fase 4, tareas 2 y 5): lectura de la plantilla, resultados de desempeño y auditoría.
# Solo datos sintéticos (L001, Z1, T0001); ZZSENT es el centinela de privacidad (R13).
import datetime
import importlib.util
import shutil
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


def kinds(audit):
    return [(f.kind, f.id_tramo) for f in audit.findings]


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
    with pytest.raises(ValueError, match="unsupported input"):
        rm.load_history(tmp_path / "x.txt")


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


def test_errores_con_fila_y_columna_sin_ids(libro):
    casos = [({"Tramos": [{"id_tramo": "ZZSENT-T1", "labor_codigo": "ZZSENT", "este_m": "ZZSENT"}]},
              "sheet 'Tramos', row 2, column 'este_m': invalid value"),
             ({"Tramos": [{"id_tramo": "ZZSENT-T1", "zona_nivel": "ZZSENT", "norte_m": "ZZSENT"}]},
              "sheet 'Tramos', row 2, column 'norte_m': invalid value"),
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
    for hojas, msg in casos:
        with pytest.raises(ValueError, match=msg) as e:
            rm.load_history(libro(hojas))
        assert "ZZSENT" not in str(e.value)


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
    assert kinds(a) == [("q_mismatch", "T2"), ("not_recomputed", "T3"), ("not_recomputed", "T4")]
    assert "NGI2015" in a.findings[0].message and a.findings[0].fila == 3 and a.findings[0].sheet == "Tramos"


def test_q_tolerancia_absoluta_en_q_bajo():
    comp = dict(rqd_pct=10, jn=20, jr=0.5, ja=8, jw=0.5, srf=10)  # Q ≈ 0.0016: manda la tolerancia de 0.005
    a = rm.audit_history(rm.History((tramo("T1", q_valor=0.004, **comp),), (), ()))
    assert a.findings == ()


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
    assert "may include the orientation adjustment" in a.findings[0].message
    assert "basic RMR89 64" in a.findings[0].message and "basic RMR89 69" in a.findings[2].message


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
    assert "row 2" in a.findings[1].message and "not independent" in a.findings[2].message


def test_coherencia_entre_hojas():
    ts = (tramo("T1", 2, sost_instalado="I", sost_recomendado="IV", fecha_instalacion="2026-02-01"),
          tramo("T2", 3, sost_instalado="X"))
    ins = (insp("T1", "2026-01-15", "Estable", 2), insp("T1", "2026-02-01", "Estable", 3), insp("T9", "2026-03-01",
                                                                                                "Falla", 4))
    a = rm.audit_history(rm.History(ts, (tipo("I", 1), tipo("II", 2)), ins))
    assert [(f.kind, f.sheet, f.fila, f.id_tramo) for f in a.findings] == [
        ("unknown_support", "Tramos", 2, "T1"), ("unknown_support", "Tramos", 3, "T2"),
        ("inspection_before_installation", "Desempeno", 2, "T1"), ("unknown_tramo", "Desempeno", 4, "T9")]
    assert "sost_recomendado 'IV'" in a.findings[0].message


def test_preparacion_por_nivel():
    ts = []
    for k in range(40):
        labor = f"L{k % 6:03d}"
        ts.append(tramo(f"T{k:04d}", k + 2, labor_codigo=labor, zona_nivel=f"Z{k % 4}", rmr_valor=60, q_valor=5,
                        gsi_valor=55 if k < 20 else None, rqd_pct=50 + k, jn=6, jr=2, ja=1,
                        sost_instalado="I" if k < 12 else "II" if k < 30 else "Z",
                        fecha_instalacion="2026-01-01"))
    ins = [insp(f"T{k:04d}", "2026-03-01", "Falla") for k in range(35)]
    a = rm.audit_history(rm.History(tuple(ts), (tipo("I", 1), tipo("II", 2), tipo("III", 3)), tuple(ins)))
    r = {(x.level, x.item): x for x in a.readiness}
    assert list(r) == [(1, "rmr_from_q"), (1, "gsi_from_rmr"), (1, "gsi_from_q_prime"),
                       (2, "I"), (2, "II"), (2, "III"), (2, "Z"), (3, "performance")]
    assert r[1, "rmr_from_q"].counts == {"pairs": 40, "labors": 6} and r[1, "rmr_from_q"].ready
    assert r[1, "gsi_from_rmr"].counts == {"pairs": 20, "labors": 6}
    assert r[1, "gsi_from_rmr"].missing == {"pairs": 10, "labors": 0} and not r[1, "gsi_from_rmr"].ready
    assert r[2, "I"].counts == {"tramos": 12, "labors": 6} and r[2, "I"].ready
    assert r[2, "III"].counts == {"tramos": 0, "labors": 0} and r[2, "Z"].counts["tramos"] == 10
    p = r[3, "performance"]
    assert p.counts == {"failures": 35, "zones": 4, "tramos_with_inspections": 35, "tramos_without_inspections": 5,
                        "start_from_evaluation": 0, "without_exposure": 0}
    assert p.minimums == {"failures": 40, "zones": 3} and p.missing == {"failures": 5, "zones": 0}
    c = rm.history_audit_counts(a)
    assert (c["tramos"], c["support_types"], c["inspections"], c["levels_ready"]) == (40, 3, 35, 4)  # rmr_from_q, I, II, Z
    assert c["findings"] == c["unknown_support"] == 10  # los diez «Z»
    assert set(rm.FINDING_KINDS) <= set(c)


def test_centinela_no_aparece_en_mensajes(libro):
    """R13: ZZSENT en id, labor, zona y litología; los hallazgos lo llevan en campos, nunca en el texto."""
    s = "ZZSENT"
    comp = dict(rqd_pct=80, jn=9, jr=1.5, ja=1, jw=1, srf=1, ucs_mpa=60, espaciamiento_m=0.3,
                puntaje_condicion_juntas=20, agua="Húmedo", rmr_edicion="RMR89", rmr_valor=50, q_valor=99)
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
