"""CSV (importar y exportar) de LaborTable: una carpeta con un CSV por hoja de Excel, mismos nombres y columnas.

Solo biblioteca estándar (no necesita el extra [io]). Las reglas son las de excel_io: este módulo solo aporta
la fuente de filas; la validación y los errores (hoja = nombre del archivo sin .csv, fila, columna) son los mismos.

Formato, por archivo: UTF-8 con o sin BOM, y si falla, cp1252 (Excel antiguo); si tampoco, ValueError con el
archivo. Separador ';' o ',' (se detecta en la primera línea; si no se puede, ';'). Con ';' una coma decimal vale
("3,5" = 3.5), como exporta Excel en español de España; solo decimales planos: "1.234,5" (miles con punto) se
rechaza. Con ',' solo vale el punto decimal. Los nombres de archivo se reconocen sin importar mayúsculas
(TABLA.CSV = Tabla) y la fecha acepta también d/m/aaaa (día primero, como en el Perú).
Al escribir sale UTF-8 con BOM y, por defecto, ',' con punto decimal: Excel en es-PE usa punto decimal y ',' como
separador de listas. Con separator=';' sale coma decimal (Excel en es-ES).
"""

import csv
import datetime
import io
import re
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
    canon = {h.lower(): h for h in _HOJAS}
    files = {}
    for f in sorted(Path(path).glob("*")):  # glob: una carpeta inexistente da «missing file», como antes
        if f.suffix.lower() != ".csv":
            continue
        sheet = canon.get(f.stem.lower(), f.stem)
        if sheet in files:  # tabla.csv y Tabla.csv juntos (posible fuera de Windows): no se elige uno a ciegas
            raise ValueError(f"two files for sheet '{sheet}': {files[sheet].name} and {f.name}")
        files[sheet] = f
    return _load(_CsvSource(files))


def load_support_catalog_csv(path) -> SupportCatalog:
    """Lee un solo CSV de tipos de sostenimiento (el archivo, no la carpeta)."""
    p = Path(path)
    return _catalog(_CsvSource({p.stem: p}), p.stem)[1]


def _celda(v, decimal_comma):
    if v is None:
        return ""
    if isinstance(v, float):
        s = repr(v)  # repr es exacto: la ida y vuelta no pierde decimales
        return s.replace(".", ",") if decimal_comma else s
    return str(v)


def save_csv_dir(t: LaborTable, path, *, separator: str = ",") -> Path:
    """Una carpeta con un CSV por hoja, UTF-8 con BOM.

    separator=',' (por defecto): punto decimal, lo que abre bien Excel en es-PE o en inglés.
    separator=';': coma decimal, para Excel en es-ES. load_csv_dir lee los dos.
    """
    if separator not in (",", ";"):
        raise ValueError(f"separator must be ',' or ';', got {separator!r}")
    out = Path(path)
    out.mkdir(parents=True, exist_ok=True)
    for name, cols, rows in _hojas(to_dict(t)):
        with open(out / f"{name}.csv", "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f, delimiter=separator)
            w.writerow(cols)
            for r in rows:
                w.writerow([_celda(v, separator == ";") for v in r])
    return out
