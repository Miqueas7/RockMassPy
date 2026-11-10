"""CSV (importar y exportar) de LaborTable: una carpeta con un CSV por hoja de Excel, mismos nombres y columnas.

Solo biblioteca estándar (no necesita el extra [io]). Las reglas son las de excel_io: este módulo solo aporta
la fuente de filas; la validación y los errores (hoja = nombre del archivo sin .csv, fila, columna) son los mismos.

Formato, por archivo: UTF-8 con o sin BOM, y si falla, cp1252 (Excel antiguo); si tampoco, ValueError con el
archivo. Separador ';' o ',' (se detecta en la primera línea; si no se puede, ';'). Con ';' una coma decimal vale
("3,5" = 3.5), como exporta Excel en español de España; solo decimales planos: "1.234,5" (miles con punto) se
rechaza. Con ',' solo vale el punto decimal. Los nombres de archivo se reconocen sin importar mayúsculas
(TABLA.CSV = Tabla) y la fecha acepta también d/m/aaaa (día primero, como en el Perú).
Al escribir sale UTF-8 con BOM y en el formato numérico del computador (en Windows, el del registro que usa Excel;
en otros sistemas, la configuración regional): así un colega en España o EE. UU. lo abre bien en su Excel. Con
separator/decimal se fuerza uno. Solo se escribe ',' o ';' (el tabulador no: la lectura no lo detecta).
"""

import csv
import datetime
import io
import locale
import re
import sys
from pathlib import Path

from .excel_io import _catalog, _hojas, _load
from .labor_table import LaborTable
from .support import SupportCatalog
from .table_io import to_dict


# nombres canónicos de las hojas: un archivo «tabla.csv» se lee como «Tabla»
_HOJAS = ("Tabla", "Tipos_sostenimiento", "Clases", "Celdas", "Correlaciones", "Puntajes")


def _leer(path):
    """(filas crudas, ¿coma decimal?) de un CSV."""
    raw = Path(path).read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = raw.decode("cp1252")
        except UnicodeDecodeError:  # cp1252 deja 5 bytes sin definir (0x81, 0x8D, 0x8F, 0x90, 0x9D)
            raise ValueError(f"{Path(path).name}: could not decode as UTF-8 or cp1252") from None
    first = text.split("\n", 1)[0]
    try:
        sep = csv.Sniffer().sniff(first, delimiters=";,").delimiter
    except csv.Error:
        sep = ";"
    return list(csv.reader(io.StringIO(text, newline=""), delimiter=sep)), sep == ";"


class _CsvSource:
    """Misma interfaz que _ExcelSource: la hoja es el nombre del archivo sin .csv."""

    def __init__(self, files):
        self.files = files  # {nombre_de_hoja: ruta}
        self.sheetnames = list(files)
        self._cache = {}

    def _get(self, sheet):
        if sheet not in self._cache:
            self._cache[sheet] = _leer(self.files[sheet])
        return self._cache[sheet]

    def rows(self, sheet):
        return self._get(sheet)[0]

    def decimal_comma(self, sheet):
        return self._get(sheet)[1]

    def missing(self, sheet):
        return f"missing file '{sheet}.csv'"

    def date(self, v):
        """d/m/aaaa o dd/mm/aaaa (día primero) -> aaaa-mm-dd; lo demás pasa tal cual y lo valida from_dict."""
        m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", v or "")
        if m:
            try:
                return datetime.date(int(m[3]), int(m[2]), int(m[1])).isoformat()
            except ValueError:  # 13/31/2026: no es una fecha día/mes, se deja para el error con su ubicación
                pass
        return v


def load_csv_dir(path) -> LaborTable:
    """Lee la carpeta: Tabla, Tipos_sostenimiento y Clases o Celdas son obligatorios; Correlaciones y Puntajes no.

    Los nombres de archivo se reconocen sin importar mayúsculas (tabla.csv o TABLA.CSV son la hoja Tabla).
    """
    return _load(_CsvSource(_csv_files(path, _HOJAS)))


def _csv_files(path, hojas) -> dict:
    """{hoja: archivo} de una carpeta; `hojas` da los nombres canónicos (sin importar mayúsculas)."""
    canon = {h.lower(): h for h in hojas}
    files = {}
    for f in sorted(Path(path).glob("*")):  # glob: una carpeta inexistente da «missing file», como antes
        if f.suffix.lower() != ".csv":
            continue
        sheet = canon.get(f.stem.lower(), f.stem)
        if sheet in files:  # tabla.csv y Tabla.csv juntos (posible fuera de Windows): no se elige uno a ciegas
            raise ValueError(f"two files for sheet '{sheet}': {files[sheet].name} and {f.name}")
        files[sheet] = f
    return files


def load_support_catalog_csv(path) -> SupportCatalog:
    """Lee un solo CSV de tipos de sostenimiento (el archivo, no la carpeta)."""
    p = Path(path)
    if p.is_dir():  # en Windows abrir una carpeta da PermissionError, que no dice qué falta
        raise ValueError("load_support_catalog_csv expects the path of the CSV file, not a folder "
                         "(use load_csv_dir for a folder)")
    return _catalog(_CsvSource({p.stem: p}), p.stem)[1]


def _system_csv_format() -> tuple[str, str]:
    """(separador de listas, marca decimal) del computador, como los usa Excel; sin tocar estado global."""
    try:
        if sys.platform == "win32":
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\International") as k:
                dec, sep = winreg.QueryValueEx(k, "sDecimal")[0], winreg.QueryValueEx(k, "sList")[0]
        else:
            antes = locale.setlocale(locale.LC_NUMERIC)
            try:
                locale.setlocale(locale.LC_NUMERIC, "")
                dec = locale.localeconv()["decimal_point"]
            finally:
                locale.setlocale(locale.LC_NUMERIC, antes)
            sep = ";" if dec == "," else ","
        # shortcut: el tabulador no se escribe (la lectura solo detecta ',' y ';'); si Windows lo usa, se cae a ',' o ';'
        if dec not in (".", ","):
            return ",", "."
        if sep not in (",", ";") or sep == dec:
            sep = ";" if dec == "," else ","
        return sep, dec
    except Exception:  # sin registro, sin locale o valores raros: el formato de siempre
        return ",", "."


def _celda(v, decimal):
    if v is None:
        return ""
    if isinstance(v, float):
        return repr(v).replace(".", decimal)  # repr es exacto: la ida y vuelta no pierde decimales
    return str(v)


def save_csv_dir(t: LaborTable, path, *, separator: str | None = None, decimal: str | None = None) -> Path:
    """Una carpeta con un CSV por hoja, UTF-8 con BOM, en el formato numérico de este computador.

    Sin argumentos, separador y marca decimal salen de la configuración regional (la de Excel en Windows).
    separator (',' o ';') y decimal ('.' o ',') fuerzan uno; deben ser distintos. load_csv_dir lee las dos formas.
    """
    if separator is not None and separator not in (",", ";"):
        raise ValueError(f"separator must be ',' or ';', got {separator!r}")
    if decimal is not None and decimal not in (".", ","):
        raise ValueError(f"decimal must be '.' or ',', got {decimal!r}")
    if separator is None or decimal is None:
        sep0, dec0 = _system_csv_format()
        if separator is None:  # si solo se fuerza la marca decimal, el separador se ajusta para no chocar
            separator = sep0 if decimal is None or sep0 != decimal else (";" if decimal == "," else ",")
        if decimal is None:
            decimal = dec0 if dec0 != separator else ("." if separator == "," else ",")
    if separator == decimal:
        raise ValueError(f"separator and decimal must differ, got {separator!r} for both")
    out = Path(path)
    out.mkdir(parents=True, exist_ok=True)
    for name, cols, rows in _hojas(to_dict(t)):
        with open(out / f"{name}.csv", "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f, delimiter=separator)
            w.writerow(cols)
            for r in rows:
                w.writerow([_celda(v, decimal) for v in r])
    return out
