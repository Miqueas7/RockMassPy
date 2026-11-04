import sys

import pytest

import rockmasspy as rm
from rockmasspy import csv_io
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


@pytest.mark.parametrize("sep", [",", ";"])
@pytest.mark.parametrize("make", [range_lt, cells_lt])
def test_roundtrip_csv(make, sep, tmp_path):
    t = make()
    rm.save_csv_dir(t, tmp_path / "c", separator=sep)
    assert rm.load_csv_dir(tmp_path / "c") == t


@pytest.mark.parametrize("sep", [",", ";"])
def test_roundtrip_with_rating(sep, tmp_path):
    t = rm.LaborTable("galería", CAT, rtab(), rating=rm.RatingTable.rmr89_default())
    rm.save_csv_dir(t, tmp_path / "c", separator=sep)
    assert rm.load_csv_dir(tmp_path / "c") == t


FORMATOS = [(",", "."), (";", ",")]


@pytest.mark.parametrize("fmt", FORMATOS)
@pytest.mark.parametrize("make", [range_lt, cells_lt])
def test_default_follows_system_format_and_roundtrips(make, fmt, tmp_path, monkeypatch):
    monkeypatch.setattr(csv_io, "_system_csv_format", lambda: fmt)
    t = make()
    out = rm.save_csv_dir(t, tmp_path / "c")
    first = (out / "Tipos_sostenimiento.csv").read_bytes().split(b"\n")[3]
    assert first.startswith(f"III{fmt[0]}3{fmt[0]}{fmt[0]}split set{fmt[0]}2{fmt[1]}1{fmt[0]}1{fmt[1]}5{fmt[0]}".encode())
    assert rm.load_csv_dir(out) == t


def test_explicit_args_override_system_format(tmp_path, monkeypatch):
    monkeypatch.setattr(csv_io, "_system_csv_format", lambda: (";", ","))
    out = rm.save_csv_dir(range_lt(), tmp_path / "c", separator=",", decimal=".")
    assert (out / "Tipos_sostenimiento.csv").read_bytes().split(b"\n")[3].startswith(b"III,3,,split set,2.1,1.5,")
    # solo la marca decimal: el separador se ajusta para no chocar con ella
    out = rm.save_csv_dir(range_lt(), tmp_path / "d", decimal=",")
    assert out and (out / "Tipos_sostenimiento.csv").read_bytes().split(b"\n")[3].startswith(b"III;3;;split set;2,1;1,5;")
    assert rm.load_csv_dir(out) == range_lt()


@pytest.mark.parametrize("kw", [{"separator": "	"}, {"separator": ""}, {"decimal": ";"}, {"decimal": "x"},
                                {"separator": ",", "decimal": ","}, {"separator": ";", "decimal": ";"}])
def test_invalid_separator_decimal(kw, tmp_path):
    with pytest.raises(ValueError, match="separator|decimal"):
        rm.save_csv_dir(range_lt(), tmp_path / "c", **kw)


@pytest.mark.real_csv_format
def test_system_format_failure_falls_back(monkeypatch):
    monkeypatch.setattr(csv_io.locale, "setlocale", lambda *a: (_ for _ in ()).throw(OSError("x")))
    monkeypatch.setattr(csv_io.sys, "platform", "linux")
    assert csv_io._system_csv_format() == (",", ".")


@pytest.mark.real_csv_format
@pytest.mark.skipif(sys.platform != "win32", reason="registro de Windows")
def test_real_system_format_is_accepted(tmp_path):
    sep, dec = csv_io._system_csv_format()
    assert sep in (",", ";") and dec in (".", ",") and sep != dec
    t = range_lt()
    assert rm.load_csv_dir(rm.save_csv_dir(t, tmp_path / "c")) == t


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


def _fecha(carpeta, valor):
    tabla = carpeta / "Tabla.csv"
    filas = tabla.read_text(encoding="utf-8-sig").splitlines()
    tabla.write_text("\n".join(f"fecha,{valor}" if f.startswith("fecha,") else f for f in filas) + "\n",
                     encoding="utf-8-sig")


def test_fecha_dia_primero(tmp_path):
    for valor in ("1/11/2026", "01/11/2026"):
        rm.save_csv_dir(range_lt(), tmp_path)
        _fecha(tmp_path, valor)
        assert rm.load_csv_dir(tmp_path).date == "2026-11-01"


def test_fecha_mes_primero_es_error_con_ubicacion(tmp_path):
    rm.save_csv_dir(range_lt(), tmp_path)
    _fecha(tmp_path, "13/31/2026")
    with pytest.raises(ValueError, match="sheet 'Tabla', campo 'fecha': expected yyyy-mm-dd, got '13/31/2026'"):
        rm.load_csv_dir(tmp_path)


def test_nombres_sin_importar_mayusculas(tmp_path):
    t = range_lt()
    rm.save_csv_dir(t, tmp_path / "a")
    b = tmp_path / "b"
    b.mkdir()
    for i, f in enumerate(sorted((tmp_path / "a").iterdir())):
        nombre = f.name.lower() if i % 2 else f.name.upper()  # tabla.csv, TIPOS_SOSTENIMIENTO.CSV...
        (b / nombre).write_bytes(f.read_bytes())
    nombres = [f.name for f in b.iterdir()]
    assert any(n == n.lower() for n in nombres) and any(n == n.upper() for n in nombres)
    assert rm.load_csv_dir(b) == t
    next(f for f in b.iterdir() if f.stem.lower() == "clases").unlink()
    with pytest.raises(ValueError, match="missing file 'Clases.csv'"):  # el mensaje usa el nombre canónico
        rm.load_csv_dir(b)


def test_byte_indescifrable(tmp_path):
    rm.save_csv_dir(range_lt(), tmp_path)
    (tmp_path / "Tabla.csv").write_bytes(b"campo,valor\nnotas,\x81\n")  # 0x81: ni UTF-8 ni cp1252
    with pytest.raises(ValueError, match=r"^Tabla\.csv: could not decode as UTF-8 or cp1252$"):
        rm.load_csv_dir(tmp_path)


def test_puntajes_con_tildes_y_mayusculas(tmp_path):
    t = rm.LaborTable("galería", CAT, rtab(), rating=rm.RatingTable.rmr89_default())
    rm.save_csv_dir(t, tmp_path)
    f = tmp_path / "Puntajes.csv"
    txt = f.read_text(encoding="utf-8-sig")
    assert ",numerico," in txt and ",mayor," in txt and ",menor," in txt
    f.write_text(txt.replace(",numerico,", ",Numérico,").replace(",mayor,", ",Mayor,").replace(",menor,", ",MENOR,"),
                 encoding="utf-8-sig")
    assert rm.load_csv_dir(tmp_path) == t
