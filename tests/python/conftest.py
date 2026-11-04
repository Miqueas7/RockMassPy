# Las pruebas esperan el CSV con ',' y '.'; la librería sigue el formato de cada computador (es-PE usa ';').
# Se fija aquí para que la suite no dependa de la PC; las que prueban la lectura real llevan real_csv_format.
import pytest

from rockmasspy import batch, csv_io


def pytest_configure(config):
    config.addinivalue_line("markers", "real_csv_format: usa el formato CSV real del computador")


@pytest.fixture(autouse=True)
def _formato_csv_fijo(request, monkeypatch):
    if request.node.get_closest_marker("real_csv_format") is None:
        monkeypatch.setattr(csv_io, "_system_csv_format", lambda: (",", "."))
        monkeypatch.setattr(batch, "_system_csv_format", lambda: (",", "."))
