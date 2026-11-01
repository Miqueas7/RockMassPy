"""CSV (importar y exportar) de LaborTable: una carpeta con un CSV por hoja de Excel, mismos nombres y columnas.

Solo biblioteca estándar (no necesita el extra [io]). Las reglas son las de excel_io: este módulo solo aporta
la fuente de filas; la validación y los errores (hoja = nombre del archivo sin .csv, fila, columna) son los mismos.

Formato, por archivo: UTF-8 con o sin BOM, y si falla, cp1252 (Excel antiguo). Separador ';' o ',' (se detecta
en la primera línea; si no se puede, ';'). Con ';' una coma decimal vale ("3,5" = 3.5), como exporta Excel en
español; solo decimales planos: "1.234,5" (miles con punto) se rechaza. Con ',' solo vale el punto decimal.
Al escribir siempre sale UTF-8 con BOM, ';' y coma decimal, que es lo que Excel en español abre bien.
"""

import csv
import io
from pathlib import Path

from .excel_io import _catalog, _hojas, _load
from .labor_table import LaborTable
from .support import SupportCatalog
from .table_io import to_dict


def _leer(path):
    """(filas crudas, ¿coma decimal?) de un CSV."""
    raw = Path(path).read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252")
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


def load_csv_dir(path) -> LaborTable:
    """Lee la carpeta: Tabla, Tipos_sostenimiento y Clases o Celdas son obligatorios; Correlaciones y Puntajes no."""
    return _load(_CsvSource({f.stem: f for f in Path(path).glob("*.csv")}))


def load_support_catalog_csv(path) -> SupportCatalog:
    """Lee un solo CSV de tipos de sostenimiento (el archivo, no la carpeta)."""
    p = Path(path)
    return _catalog(_CsvSource({p.stem: p}), p.stem)[1]


def _celda(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return repr(v).replace(".", ",")  # repr es exacto: la ida y vuelta no pierde decimales
    return str(v)


def save_csv_dir(t: LaborTable, path) -> Path:
    out = Path(path)
    out.mkdir(parents=True, exist_ok=True)
    for name, cols, rows in _hojas(to_dict(t)):
        with open(out / f"{name}.csv", "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(cols)
            for r in rows:
                w.writerow([_celda(v) for v in r])
    return out
