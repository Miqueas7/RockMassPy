import sys

import pytest

import rockmasspy as rm
from test_labor_table import CAT, rtab
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


CORR_COL = {c: i + 1 for i, c in enumerate(("nombre", "desde", "hacia", "forma", "a", "b", "valido_min", "valido_max",
                                              "fuente"))}


def _excel_error(tmp_path, make, fn):
    with pytest.raises(ValueError) as e:
        rm.load_excel(_edit(tmp_path, make, fn))
    return str(e.value)


def test_correlation_error_locates_row(tmp_path):
    def f(wb):
        wb["Correlaciones"].cell(row=2, column=CORR_COL["valido_min"]).value = 500
    msg = _excel_error(tmp_path, range_lt, f)
    assert msg.startswith("sheet 'Correlaciones', row 2: ") and "valid_min" in msg and "correlations[" not in msg

    def g(wb):
        wb["Correlaciones"].cell(row=2, column=CORR_COL["forma"]).value = "Cubic"
    assert _excel_error(tmp_path, range_lt, g).startswith("sheet 'Correlaciones', row 2: form: expected one of")


def test_cell_error_locates_row(tmp_path):
    def f(wb):
        ws = wb["Celdas"]
        ws.cell(row=3, column=3).value = 60  # gsi_min
        ws.cell(row=3, column=4).value = 40  # gsi_max
    assert _excel_error(tmp_path, cells_lt, f).startswith("sheet 'Celdas', row 3: gsi_range must satisfy")

    def g(wb):
        wb["Celdas"].cell(row=3, column=1).value = "F/R"  # celda repetida
    assert _excel_error(tmp_path, cells_lt, g) == "sheet 'Celdas': cell F/R is defined twice"


def test_half_filled_bolt_is_an_error(tmp_path):
    p = libro(tmp_path, [["I", 1, "", None, None, None, None, None, None, None, None],
                         ["II", 2, "", "Split Set", 1.8, None, None, None, None, None, None]])
    with pytest.raises(ValueError) as e:
        rm.load_support_catalog_excel(p)
    assert str(e.value) == "sheet 'Tipos_sostenimiento', row 3, column 'perno_espaciamiento_m': required when the bolt is given"
    p = libro(tmp_path, [["II", 2, "", None, 1.8, 1.2, None, None, None, None, None]])
    with pytest.raises(ValueError) as e:
        rm.load_support_catalog_excel(p)
    assert str(e.value) == "sheet 'Tipos_sostenimiento', row 2, column 'perno_tipo': required when the bolt is given"


def test_fiber_without_thickness_is_an_error(tmp_path):
    for espesor in (None, 0):
        p = libro(tmp_path, [["II", 2, "", None, None, None, espesor, "si", None, None, None]])
        with pytest.raises(ValueError) as e:
            rm.load_support_catalog_excel(p)
        assert str(e.value) == ("sheet 'Tipos_sostenimiento', row 2, column 'shotcrete_espesor_mm': "
                                "required when the shotcrete is given")
    p = libro(tmp_path, [["I", 1, "", None, None, None, 0, "no", None, None, None]])
    assert rm.load_support_catalog_excel(p).get("I").shotcrete is None


def test_row_validation_has_no_dict_path(tmp_path):
    p = libro(tmp_path, [["I", 1, "", None, None, None, None, None, None, None, None],
                         ["II", 2, "", "Split Set", -3, 1.2, None, None, None, None, None]])
    with pytest.raises(ValueError) as e:
        rm.load_support_catalog_excel(p)
    assert str(e.value) == "sheet 'Tipos_sostenimiento', row 3: length_m must be finite and > 0, got -3"
    p = libro(tmp_path, [["I", 1, "", None, None, None, None, None, None, None, None],
                         ["I", 2, "", None, None, None, None, None, None, None, None]])
    with pytest.raises(ValueError) as e:
        rm.load_support_catalog_excel(p)
    assert str(e.value) == "sheet 'Tipos_sostenimiento': duplicate support code 'I'"


def test_tabla_errors_name_the_campo(tmp_path):
    def fecha(wb):
        ws = wb["Tabla"]
        ws.cell(row=_campo_row(ws, "fecha"), column=2).value = "01/11/2026"
    assert _excel_error(tmp_path, range_lt, fecha) == "sheet 'Tabla', campo 'fecha': expected yyyy-mm-dd, got '01/11/2026'"

    def luz(wb):
        ws = wb["Tabla"]
        ws.cell(row=_campo_row(ws, "luz_min_m"), column=2).value = 9
    assert _excel_error(tmp_path, range_lt, luz).startswith("sheet 'Tabla', campo 'luz_min_m/luz_max_m': must satisfy")

    def edicion(wb):
        ws = wb["Tabla"]
        ws.cell(row=_campo_row(ws, "edicion_base"), column=2).value = "RMR2000"
    assert _excel_error(tmp_path, range_lt, edicion).startswith("sheet 'Tabla', campo 'metodo/edicion_base': unknown edition")


def test_cells_edicion_base_must_match_cartilla(tmp_path):
    def f(wb):
        ws = wb["Tabla"]
        ws.cell(row=_campo_row(ws, "edicion_base"), column=2).value = "GSI-2013"
    assert _excel_error(tmp_path, cells_lt, f).startswith("sheet 'Tabla', campo 'edicion_base': expected the chart id")


def test_empty_texts_survive_excel(tmp_path):
    cat = rm.SupportCatalog([rm.SupportType("I", 1, " "),
                             rm.SupportType("II", 2, "x", rm.Bolt("split set", 2, 1), mesh="", arch=" ")])
    t = rm.LaborTable("galería", cat, rm.CellTable(rm.GSI_CHARTS["GSI-Vallejo-Osinergmin2017"],
                                                    [rm.CellClass("F/R", "II", label=" ")]))
    rm.save_excel(t, tmp_path / "t.xlsx")
    assert rm.load_excel(tmp_path / "t.xlsx") == t


def test_roundtrip_rating_excel(tmp_path):
    t = rm.LaborTable("galería", CAT, rtab(), rating=rm.RatingTable.rmr89_default())
    rm.save_excel(t, tmp_path / "t.xlsx")
    assert rm.load_excel(tmp_path / "t.xlsx") == t
    rm.save_excel(range_lt(), tmp_path / "s.xlsx")
    assert rm.load_excel(tmp_path / "s.xlsx").rating is None


def _rated():
    return rm.LaborTable("galería", CAT, rtab(), rating=rm.RatingTable.rmr89_default())


def test_puntajes_comma_decimal_names_sheet_row_column(tmp_path):
    def f(wb):
        wb["Puntajes"].cell(row=3, column=5).value = "3,5"
    msg = _excel_error(tmp_path, _rated, f)
    assert "sheet 'Puntajes', row 3, column 'desde'" in msg


def test_puntajes_row_errors_locate_the_row(tmp_path):
    def f(wb):
        wb["Puntajes"].cell(row=2, column=4).value = "arriba"  # mejor
    assert "sheet 'Puntajes', row 2" in _excel_error(tmp_path, _rated, f)

    def g(wb):
        wb["Puntajes"].cell(row=2, column=2).value = "raro"  # tipo
    assert "sheet 'Puntajes', row 2, column 'tipo'" in _excel_error(tmp_path, _rated, g)


def test_puntajes_empty_hasta_only_in_last_interval(tmp_path):
    def last(wb):  # ucs: filas 2-8, la 8 es el último intervalo
        wb["Puntajes"].cell(row=8, column=6).value = None
    assert rm.load_excel(_edit(tmp_path, _rated, last)) == _rated()

    def middle(wb):
        wb["Puntajes"].cell(row=3, column=6).value = None
    assert "empty 'hasta'" in _excel_error(tmp_path, _rated, middle)


def test_puntajes_rows_without_edition_is_an_error(tmp_path):
    def f(wb):
        ws = wb["Tabla"]
        ws.cell(row=_campo_row(ws, "edicion_puntajes"), column=2).value = None
    assert "campo 'edicion_puntajes': required when sheet 'Puntajes' exists" in _excel_error(tmp_path, _rated, f)

    def vacia(wb):  # hoja solo con cabecera y sin edición = sin puntajes propios
        ws = wb["Tabla"]
        ws.cell(row=_campo_row(ws, "edicion_puntajes"), column=2).value = None
        wb["Puntajes"].delete_rows(2, wb["Puntajes"].max_row)
    assert rm.load_excel(_edit(tmp_path, _rated, vacia)).rating is None


def test_puntajes_duplicates_are_errors(tmp_path):
    def adj(wb):  # última fila = ajuste VeryUnfavourable; se repite el anterior
        ws = wb["Puntajes"]
        ws.cell(row=ws.max_row, column=7).value = "Fair"
    m = _excel_error(tmp_path, _rated, adj)
    assert "column 'categoria'" in m and "duplicate" in m and "Fair" in m

    def cat(wb):
        ws = wb["Puntajes"]
        fila = next(r[0].row for r in ws.iter_rows(min_row=2) if r[0].value == "water")
        ws.cell(row=fila + 1, column=7).value = "Dry"
    m = _excel_error(tmp_path, _rated, cat)
    assert "duplicate" in m and "Dry" in m
