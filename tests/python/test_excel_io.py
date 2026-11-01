import sys

import pytest

import rockmasspy as rm
from test_table_io import cells_lt, range_lt

openpyxl = pytest.importorskip("openpyxl")

# Orden de columnas de la plantilla del histórico (tools/plantilla_historico.py), sin leer ningún archivo lleno.
COLS = ["codigo_tipo", "orden", "descripcion", "perno_tipo", "perno_longitud_m", "perno_espaciamiento_m",
        "shotcrete_espesor_mm", "shotcrete_fibra", "malla", "cimbra", "costo_relativo"]


def libro(tmp_path, filas, hoja="Tipos_sostenimiento"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = hoja
    ws.append(COLS)
    for f in filas:
        ws.append(f)
    p = tmp_path / "t.xlsx"
    wb.save(p)
    return p


@pytest.mark.parametrize("make", [range_lt, cells_lt])
def test_roundtrip_excel(make, tmp_path):
    t = make()
    rm.save_excel(t, tmp_path / "t.xlsx")
    assert rm.load_excel(tmp_path / "t.xlsx") == t


def test_sheet_and_column_names(tmp_path):
    rm.save_excel(range_lt(), tmp_path / "t.xlsx")
    wb = openpyxl.load_workbook(tmp_path / "t.xlsx")
    assert wb.sheetnames == ["Tabla", "Tipos_sostenimiento", "Clases", "Correlaciones"]
    assert [c.value for c in wb["Tipos_sostenimiento"][1]] == COLS
    campos = dict(wb["Tabla"].iter_rows(min_row=2, values_only=True))
    assert campos["edicion_base"] == "RMR89" and campos["tipo_tabla"] == "range"
    rm.save_excel(cells_lt(), tmp_path / "c.xlsx")
    c = dict(openpyxl.load_workbook(tmp_path / "c.xlsx")["Tabla"].iter_rows(min_row=2, values_only=True))
    assert c["cartilla"] == c["edicion_base"] == "GSI-Vallejo-Osinergmin2017"


def test_support_catalog_from_any_workbook(tmp_path):
    p = libro(tmp_path, [["I", 1, "liviano", None, None, None, 0, None, None, None, None],
                         ["II", 2, "", "Split Set", 1.8, " 1.2 ", 50, "Sí", "electrosoldada", None, 2]])
    cat = rm.load_support_catalog_excel(p)
    assert cat.get("I").is_empty()
    t = cat.get("II")
    assert t.bolt == rm.Bolt("Split Set", 1.8, 1.2) and t.shotcrete == rm.Shotcrete(50, True)
    assert t.mesh == "electrosoldada" and t.relative_cost == 2
    with pytest.raises(ValueError, match="Otra"):
        rm.load_support_catalog_excel(p, sheet="Otra")


def test_comma_decimal_names_sheet_row_column(tmp_path):
    p = libro(tmp_path, [["I", 1, "", None, None, None, None, None, None, None, None],
                         ["II", 2, "", "Split Set", "3,5", 1.2, None, None, None, None, None]])
    with pytest.raises(ValueError) as e:
        rm.load_support_catalog_excel(p)
    assert str(e.value) == "sheet 'Tipos_sostenimiento', row 3, column 'perno_longitud_m': expected a number, got '3,5'"


def test_text_number_with_spaces_is_accepted(tmp_path):
    p = libro(tmp_path, [["I", 1, "", "Split Set", " 2.5 ", 1.0, None, None, None, None, None]])
    assert rm.load_support_catalog_excel(p).get("I").bolt.length_m == 2.5


def test_empty_required_column(tmp_path):
    p = libro(tmp_path, [["I", None, "", None, None, None, None, None, None, None, None]])
    with pytest.raises(ValueError, match="sheet 'Tipos_sostenimiento', row 2, column 'orden'"):
        rm.load_support_catalog_excel(p)


def test_extra_sheets_and_columns_ignored_missing_sheet_named(tmp_path):
    rm.save_excel(range_lt(), tmp_path / "t.xlsx")
    wb = openpyxl.load_workbook(tmp_path / "t.xlsx")
    wb.create_sheet("Notas")
    wb["Clases"].cell(row=1, column=9, value="extra")
    wb.save(tmp_path / "t.xlsx")
    assert rm.load_excel(tmp_path / "t.xlsx") == range_lt()
    del wb["Clases"]
    wb.save(tmp_path / "u.xlsx")
    with pytest.raises(ValueError, match="Clases"):
        rm.load_excel(tmp_path / "u.xlsx")


def test_missing_openpyxl_gives_helpful_importerror(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "openpyxl", None)
    with pytest.raises(ImportError, match=r"rockmasspy\[io\]"):
        rm.save_excel(range_lt(), tmp_path / "t.xlsx")
    with pytest.raises(ImportError, match=r"rockmasspy\[io\]"):
        rm.load_excel(tmp_path / "t.xlsx")
    with pytest.raises(ImportError, match=r"rockmasspy\[io\]"):
        rm.load_support_catalog_excel(tmp_path / "t.xlsx")


def test_loaders_release_the_file(tmp_path):
    rm.save_excel(range_lt(), tmp_path / "t.xlsx")
    rm.load_excel(tmp_path / "t.xlsx")
    (tmp_path / "t.xlsx").unlink()
    p = libro(tmp_path, [["I", 1, "", None, None, None, None, None, None, None, None]])
    rm.load_support_catalog_excel(p)
    p.unlink()


def _edit(tmp_path, make, fn):
    rm.save_excel(make(), tmp_path / "t.xlsx")
    wb = openpyxl.load_workbook(tmp_path / "t.xlsx")
    fn(wb)
    wb.save(tmp_path / "t.xlsx")
    return tmp_path / "t.xlsx"


def _campo_row(ws, campo):
    return next(r[0].row for r in ws.iter_rows(min_row=2) if r[0].value == campo)


def test_native_excel_date_in_fecha(tmp_path):
    import datetime

    def f(wb):
        ws = wb["Tabla"]
        ws.cell(row=_campo_row(ws, "fecha"), column=2).value = datetime.datetime(2026, 11, 1)
    assert rm.load_excel(_edit(tmp_path, range_lt, f)).date == "2026-11-01"


def test_tabla_numeric_error_has_excel_row(tmp_path):
    def f(wb):
        ws = wb["Tabla"]
        ws.cell(row=_campo_row(ws, "luz_min_m"), column=2).value = "3,5"
    p = _edit(tmp_path, range_lt, f)
    n = _campo_row(openpyxl.load_workbook(p)["Tabla"], "luz_min_m")
    with pytest.raises(ValueError) as e:
        rm.load_excel(p)
    assert str(e.value) == f"sheet 'Tabla', row {n}, column 'valor': expected a number, got '3,5'"


def test_validation_error_locates_row_after_blank_row(tmp_path):
    p = libro(tmp_path, [["I", 1, "", None, None, None, None, None, None, None, None], [None] * 11,
                         ["II", 2, "", "Split Set", -3, 1.2, None, None, None, None, None]])
    with pytest.raises(ValueError, match=r"sheet 'Tipos_sostenimiento', row 4: .*length_m"):
        rm.load_support_catalog_excel(p)


def test_validation_error_in_classes_row(tmp_path):
    def f(wb):
        wb["Clases"].insert_rows(2)  # fila vacía; la clase real baja a la 3
        wb["Clases"].cell(row=3, column=1).value = 90
        wb["Clases"].cell(row=3, column=2).value = 10
    with pytest.raises(ValueError, match=r"sheet 'Clases', row 3: "):
        rm.load_excel(_edit(tmp_path, range_lt, f))
