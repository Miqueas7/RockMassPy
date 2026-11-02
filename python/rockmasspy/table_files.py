"""Carga una tabla por labor eligiendo el lector según la extensión de la ruta."""

from pathlib import Path

from .csv_io import load_csv_dir
from .excel_io import load_excel
from .labor_table import LaborTable
from .table_io import load_json, load_yaml

_READERS = {".json": load_json, ".yaml": load_yaml, ".yml": load_yaml, ".xlsx": load_excel}


def load_table(path) -> LaborTable:
    """.json, .yaml/.yml, .xlsx o una carpeta de CSV; cualquier otra cosa es ValueError."""
    p = Path(path)
    if p.is_dir():
        return load_csv_dir(p)
    reader = _READERS.get(p.suffix.lower())
    if reader is None:
        raise ValueError(f"unsupported table file '{p.name}': use {', '.join(_READERS)} or a folder of CSV files")
    return reader(p)
