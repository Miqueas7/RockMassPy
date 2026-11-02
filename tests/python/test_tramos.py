import subprocess
import sys
from pathlib import Path

import pytest

import rockmasspy as rm

openpyxl = pytest.importorskip("openpyxl")

RAIZ = Path(__file__).resolve().parents[2]
CABECERA = ["id_tramo", "tipo_labor", "labor_codigo", "fecha_evaluacion", "luz_m", "rqd_pct", "rmr_valor", "gsi_celda"]
FILAS = [["T1", "galeria", "L1", "2026-01-05", 4.5, 80, 65, "F/R"],
         ["T2", "crucero", "L2", "2026-01-06", 5.0, 60, 50, None],
         ["T3", "galeria", "L3", None, None, None, None, None]]


def xlsx(tmp_path, cab=CABECERA, filas=FILAS):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Tramos"
    ws.append(cab)
    for f in filas:
        ws.append(f)
    p = tmp_path / "t.xlsx"
    wb.save(p)
    return p


def csv(tmp_path, texto, nombre="tramos.csv"):
    p = tmp_path / nombre
    p.write_text(texto, encoding="utf-8")
    return p


def test_excel_tres_tramos(tmp_path):
    ts = rm.load_tramos(xlsx(tmp_path))
    assert [t.id_tramo for t in ts] == ["T1", "T2", "T3"]
    assert ts[0].luz_m == 4.5 and ts[0].fila == 2 and ts[2].luz_m is None
    assert ts[0].fecha_evaluacion == "2026-01-05" and ts[0].labor_codigo == "L1"


def test_csv_tres_tramos_coma_decimal(tmp_path):
    p = csv(tmp_path, "id_tramo;tipo_labor;luz_m\nT1;galeria;4,5\nT2;crucero;5\nT3;galeria;\n")
    ts = rm.load_tramos(p)
    assert [t.luz_m for t in ts] == [4.5, 5.0, None]


def test_mapeo(tmp_path):
    p = xlsx(tmp_path, ["ID", "Labor", "RMR"], [["T1", "galeria", 70]])
    ts = rm.load_tramos(p, column_map={"id": "id_tramo", "LABOR ": "tipo_labor", "RMR": "rmr_valor"})
    assert ts[0].id_tramo == "T1" and ts[0].rmr_valor == 70 and ts[0].tipo_labor == "galeria"


def test_mapeo_columna_inexistente(tmp_path):
    with pytest.raises(ValueError, match="column 'zzz' in column_map not found in sheet 'Tramos'"):
        rm.load_tramos(xlsx(tmp_path), column_map={"zzz": "rmr_valor"})


def test_mapeo_nombre_invalido_y_duplicado(tmp_path):
    with pytest.raises(ValueError, match="valid names: id_tramo"):
        rm.load_tramos(xlsx(tmp_path), column_map={"luz_m": "nada"})
    with pytest.raises(ValueError, match="two columns map to 'rmr_valor'"):
        rm.load_tramos(xlsx(tmp_path), column_map={"rqd_pct": "rmr_valor"})


def test_falta_columna_obligatoria(tmp_path):
    p = xlsx(tmp_path, ["id_tramo", "luz_m"], [["T1", 4]])
    with pytest.raises(ValueError, match="required column 'tipo_labor' not found") as e:
        rm.load_tramos(p)
    assert "column_map" not in str(e.value)
    with pytest.raises(ValueError, match=r"required column 'tipo_labor' not found \(column_map maps: \{'X': 'luz_m'\}\)"):
        rm.load_tramos(xlsx(tmp_path, ["id_tramo", "X"], [["T1", 4]]), column_map={"X": "luz_m"})


def test_id_repetido_da_filas_no_valor(tmp_path):
    p = xlsx(tmp_path, ["id_tramo", "tipo_labor"], [["T1", "a"], ["T2", "a"], ["T1", "a"]])
    with pytest.raises(ValueError, match="duplicate id_tramo in rows 2 and 4") as e:
        rm.load_tramos(p)
    assert "T1" not in str(e.value)


def test_numero_invalido_en_csv_con_coma(tmp_path):
    p = csv(tmp_path, 'id_tramo,tipo_labor,luz_m\nT1,galeria,"3,5"\n')
    with pytest.raises(ValueError, match=r"sheet 'tramos', row 2, column 'luz_m': expected a number, got '3,5'"):
        rm.load_tramos(p)


def test_foco3_identificacion_no_se_filtra(tmp_path):
    p = xlsx(tmp_path, ["id_tramo", "tipo_labor", "labor_codigo", "este_m"], [["T1", "galeria", "SECRETO-123", "x"]])
    with pytest.raises(ValueError, match="row 2, column 'este_m': invalid value") as e:
        rm.load_tramos(p)
    assert "SECRETO-123" not in str(e.value) and "'x'" not in str(e.value)


def test_gsi_celda_normalizada(tmp_path):
    p = xlsx(tmp_path, ["id_tramo", "tipo_labor", "gsi_celda"], [["T1", "galeria", " f / r "]])
    assert rm.load_tramos(p)[0].gsi_celda == "F/R"


def test_plantilla_tiene_gsi_celda(tmp_path):
    out = tmp_path / "p.xlsx"
    subprocess.run([sys.executable, "-X", "utf8", str(RAIZ / "tools" / "plantilla_historico.py"), str(out)], check=True,
                   capture_output=True)
    cab = [c.value for c in openpyxl.load_workbook(out)["Tramos"][1]]  # solo la cabecera
    assert "gsi_celda" in cab and set(rm.TRAMO_COLUMNS) <= set(cab)
