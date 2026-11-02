import math

import pytest

from rockmasspy.chart_regions import Region, locate

# dos cuadrados unidos por la arista x = 1
LEFT = Region(2, ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)))
RIGHT = Region(5, ((1.0, 0.0), (2.0, 0.0), (2.0, 1.0), (1.0, 1.0)))
BOTH = (LEFT, RIGHT)


def test_centro_de_cada_cuadrado():
    assert locate(0.5, 0.5, BOTH) == 2
    assert locate(1.5, 0.5, BOTH) == 5


def test_arista_y_vertice_compartidos_dan_la_clave_mayor():
    assert locate(1.0, 0.5, BOTH) == 5
    assert locate(1.0, 1.0, BOTH) == 5
    assert locate(1.0, 0.0, (RIGHT, LEFT)) == 5  # no depende del orden


def test_arista_propia_y_fuera():
    assert locate(0.0, 0.5, BOTH) == 2
    assert locate(2.0, 1.0, BOTH) == 5
    assert locate(3.0, 0.5, BOTH) is None
    assert locate(0.5, -1e-9, BOTH) is None
    assert locate(0.5, 0.5, ()) is None


@pytest.mark.parametrize("x, y", [(math.nan, 0.5), (0.5, math.nan), (math.inf, 0.5)])
def test_no_finito_lanza(x, y):
    with pytest.raises(ValueError):
        locate(x, y, BOTH)
