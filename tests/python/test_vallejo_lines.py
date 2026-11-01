import math

import pytest

import rockmasspy as rm
from rockmasspy import vallejo_lines as vl
from rockmasspy.gsi_charts import GSI_CHARTS

CELLS = sorted(GSI_CHARTS["GSI-Vallejo-Osinergmin2017"].valid_cells)


def test_rotulos_de_las_laminas():
    assert [ln.value for ln in vl.RMR_PRIME_LINES] == list(range(90, 0, -5))
    assert [ln.value for ln in vl.Q_PRIME_LINES] == [100, 75, 50, 20, 5, 3, 1, 0.5, 0.1, 0.05, 0.01, 0.005, 0.001]


@pytest.mark.parametrize("lines", [vl.RMR_PRIME_LINES, vl.Q_PRIME_LINES], ids=["rmr", "q"])
def test_ordenadas_y_bajan_de_izquierda_a_derecha(lines):
    values = [ln.value for ln in lines]
    assert values == sorted(values, reverse=True)
    # a menor valor, la línea queda más abajo y a la derecha en la cartilla
    mid = [(ln.x0 + ln.x1 + ln.y0 + ln.y1) / 2 for ln in lines]
    assert mid == sorted(mid) and len(set(mid)) == len(mid)
    for ln in lines:
        assert 0 <= min(ln.x0, ln.x1, ln.y0, ln.y1) and max(ln.x0, ln.x1, ln.y0, ln.y1) <= 1
        assert ln.x0 < ln.x1 and ln.y0 > ln.y1  # (x0, y0) abajo a la izquierda, (x1, y1) arriba a la derecha


def test_rangos_de_sentido():
    assert max(vl.rmr_prime_range("LF/MB")) >= 75
    assert min(vl.rmr_prime_range("T/MP")) <= 15
    lo, hi = vl.rmr_prime_range("F/R")
    assert 35 <= lo <= hi <= 75
    assert max(vl.q_prime_range("LF/MB")) >= 20


def test_celda_normalizada_y_rango_ordenado():
    assert vl.rmr_prime_range(" f / r ") == vl.rmr_prime_range("F/R")
    for c in CELLS:
        for f in (vl.rmr_prime_range, vl.q_prime_range):
            lo, hi = f(c)
            assert lo <= hi


@pytest.mark.parametrize("cell", ["T/R", "LF/MP", "X/Y", "FR"])
def test_celda_invalida(cell):
    with pytest.raises(ValueError):
        vl.rmr_prime_range(cell)
    with pytest.raises(ValueError):
        vl.q_prime_range(cell)


def test_mejor_celda_mejor_valor():
    # en cada fila y en cada columna, el RMR′ no sube al empeorar la condición o la estructura
    for f in (vl.rmr_prime_range, vl.q_prime_range):
        assert f("F/B")[1] <= f("F/MB")[1] and f("F/B")[0] <= f("F/MB")[0]
        assert f("MF/R")[1] <= f("F/R")[1] and f("MF/R")[0] <= f("F/R")[0]


def test_sin_cruce_interpola_en_log_para_q():
    # dos líneas paralelas verticales; la celda del medio no las cruza
    lines = (vl.ChartLine(100, 0.1, 1.0, 0.1, 0.0), vl.ChartLine(1, 0.9, 1.0, 0.9, 0.0))
    v = vl._range_in(lines, (0.4, 0.0, 0.6, 1.0), log=True)
    assert v == pytest.approx((10, 10))
    v = vl._range_in(lines, (0.4, 0.0, 0.6, 1.0), log=False)
    assert v == pytest.approx((50.5, 50.5))


def test_fuente_y_exportados():
    assert vl.VALLEJO_LINES_SOURCE == "digitized from Osinergmin (2017), Annex A.17 (Vallejo chart, 2011)"
    assert rm.rmr_prime_range is vl.rmr_prime_range and rm.q_prime_range is vl.q_prime_range
    assert rm.RMR_PRIME_LINES is vl.RMR_PRIME_LINES and rm.ChartLine is vl.ChartLine
    assert all(math.isfinite(ln.value) for ln in vl.Q_PRIME_LINES)
