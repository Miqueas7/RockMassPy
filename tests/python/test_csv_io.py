import pytest

import rockmasspy as rm
from test_labor_table import CAT, rtab
from test_table_io import cells_lt, range_lt

TIPOS = ("codigo_tipo;orden;descripcion;perno_tipo;perno_longitud_m;perno_espaciamiento_m;"
         "shotcrete_espesor_mm;shotcrete_fibra;malla;cimbra;costo_relativo")


def carpeta(tmp_path, tipos_filas, sep=";", enc="utf-8-sig"):
    """Carpeta mínima de tabla por rango; los tipos vienen a mano para probar el formato."""
    (tmp_path / "Tabla.csv").write_text("campo;valor\nschema;rockmasspy.labor_table\nversion;1\nlabor_type;galeria\n"
                                        "tipo_tabla;range\nmetodo;rmr\nedicion_base;1989\n", encoding="utf-8-sig")
    (tmp_path / "Tipos_sostenimiento.csv").write_text(
        "\n".join([TIPOS.replace(";", sep)] + tipos_filas) + "\n", encoding=enc)
    return tmp_path


@pytest.mark.parametrize("make", [range_lt, cells_lt])
def test_roundtrip_csv(make, tmp_path):
    t = make()
    rm.save_csv_dir(t, tmp_path / "c")
    assert rm.load_csv_dir(tmp_path / "c") == t


def test_roundtrip_with_rating(tmp_path):
    t = rm.LaborTable("galería", CAT, rtab(), rating=rm.RatingTable.rmr89_default())
    rm.save_csv_dir(t, tmp_path / "c")
    assert rm.load_csv_dir(tmp_path / "c") == t


def test_written_format(tmp_path):
    out = rm.save_csv_dir(range_lt(), tmp_path / "c")
    raw = (out / "Tipos_sostenimiento.csv").read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf") and raw.split(b"\n")[0].count(b";") == 10
    assert b"." not in b"".join(raw.split(b"\n")[1:2])  # decimales con coma


def test_semicolon_decimal_comma_bom(tmp_path):
    d = carpeta(tmp_path, ["S1;1;;split set;2,4;1,5;;;;;"])
    assert rm.load_support_catalog_csv(d / "Tipos_sostenimiento.csv").get("S1").bolt.length_m == 2.4


def test_semicolon_thousands_rejected(tmp_path):
    d = carpeta(tmp_path, ["S1;1;;split set;1.234,5;1,5;;;;;"])
    with pytest.raises(ValueError, match="sheet 'Tipos_sostenimiento', row 2, column 'perno_longitud_m': expected a number"):
        rm.load_support_catalog_csv(d / "Tipos_sostenimiento.csv")


def test_comma_separator_decimal_comma_is_error(tmp_path):
    d = carpeta(tmp_path, ["S1,1,,a,2.4,1.5,,,,,", 'S2,2,,split set,"3,5",1.5,,,,,'], sep=",")
    with pytest.raises(ValueError) as e:
        rm.load_support_catalog_csv(d / "Tipos_sostenimiento.csv")
    assert str(e.value) == "sheet 'Tipos_sostenimiento', row 3, column 'perno_longitud_m': expected a number, got '3,5'"


def test_comma_separator_with_dot_decimals(tmp_path):
    d = carpeta(tmp_path, ["S1,1,,a,2.4,1.5,,,,,"], sep=",")
    assert rm.load_support_catalog_csv(d / "Tipos_sostenimiento.csv").get("S1").bolt.length_m == 2.4


def test_cp1252(tmp_path):
    d = carpeta(tmp_path, ["S1;1;Galería;a;2,4;1,5;;;;;"], enc="cp1252")
    assert rm.load_support_catalog_csv(d / "Tipos_sostenimiento.csv").get("S1").description == "Galería"


def test_missing_required_file_named(tmp_path):
    rm.save_csv_dir(range_lt(), tmp_path)
    (tmp_path / "Tabla.csv").unlink()
    with pytest.raises(ValueError, match="Tabla.csv"):
        rm.load_csv_dir(tmp_path)
    rm.save_csv_dir(range_lt(), tmp_path)
    (tmp_path / "Clases.csv").unlink()
    with pytest.raises(ValueError, match="Clases.csv"):
        rm.load_csv_dir(tmp_path)


def test_works_without_openpyxl(tmp_path, monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "openpyxl", None)
    rm.save_csv_dir(range_lt(), tmp_path / "c")
    assert rm.load_csv_dir(tmp_path / "c") == range_lt()
