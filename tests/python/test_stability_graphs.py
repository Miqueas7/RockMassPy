import math
import re

import numpy as np
import pytest
from hypothesis import given, settings, strategies as st

import rockmasspy as rm
from rockmasspy.chart_regions import _classify, locate
from rockmasspy.stability_graphs import STABILITY_GRAPHS, GraphReading, StabilityGraph, read_stability_graph

GRAPHS = ["Mathews-Potvin1988", "Laubscher1994-stability"]
STEP = {"Mathews-Potvin1988": (5.0, 1.0), "Laubscher1994-stability": (10.0, 10.0)}  # paso de cuadrícula (x, plano y)
X_MID = {"Mathews-Potvin1988": 10.0, "Laubscher1994-stability": 30.0}


def _frame(g: StabilityGraph):
    f = math.log10 if g.y_log else float
    return g.x_range[0], g.x_range[1], f(g.y_range[0]), f(g.y_range[1])


def _y_at(line, x):
    for (x0, y0), (x1, y1) in zip(line, line[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    raise ValueError("x outside the line")


def _to_value(g, yp):
    return 10 ** yp if g.y_log else yp


def test_catalogo():
    assert set(STABILITY_GRAPHS) == set(GRAPHS)
    m, lb = STABILITY_GRAPHS["Mathews-Potvin1988"], STABILITY_GRAPHS["Laubscher1994-stability"]
    assert (m.x_range, m.y_range, m.y_log) == ((0.0, 25.0), (0.1, 1000.0), True)
    assert (lb.x_range, lb.y_range, lb.y_log) == ((0.0, 80.0), (0.0, 100.0), False)
    assert m.zone_labels == {1: "stable", 2: "transition", 3: "caved"}
    assert lb.zone_labels == {1: "stable", 2: "transitional", 3: "caving"}
    assert (m.x_name, m.y_name, lb.x_name, lb.y_name) == ("hydraulic radius", "N'", "hydraulic radius", "MRMR")
    assert lb.no_data == () and len(m.no_data) >= 1
    for gid, g in STABILITY_GRAPHS.items():
        assert g.graph_id == gid and len(g.boundaries) == 2
        assert sorted(r.key for r in g.regions) == [1, 2, 3]


@pytest.mark.parametrize("gid, fig", [("Mathews-Potvin1988", "Fig. 7.22"), ("Laubscher1994-stability", "Fig. 1")])
def test_info(gid, fig):
    info = STABILITY_GRAPHS[gid].info
    assert info.method_id == gid
    assert info.verification == rm.Verification.Primary
    assert fig in info.source and "digitized" in info.source
    assert re.search(r"error <= \d+\.\d+ grid cell\)", info.source)  # la X quedó reemplazada por el valor medido


@pytest.mark.parametrize("gid", GRAPHS)
def test_polilineas_crecientes_y_dentro_del_marco(gid):
    g = STABILITY_GRAPHS[gid]
    x0, x1, y0, y1 = _frame(g)
    for line in g.boundaries:
        xs = [p[0] for p in line]
        assert all(b > a for a, b in zip(xs, xs[1:]))
        assert all(x0 <= x <= x1 and y0 <= y <= y1 for x, y in line)
        # los extremos tocan el marco
        for x, y in (line[0], line[-1]):
            assert x in (x0, x1) or y in (y0, y1)


@pytest.mark.parametrize("gid", GRAPHS)
def test_cobertura_sin_huecos_ni_solapes(gid):
    g = STABILITY_GRAPHS[gid]
    x0, x1, y0, y1 = _frame(g)
    for x in np.linspace(x0, x1, 200):
        for y in np.linspace(y0, y1, 200):
            where = [_classify(x, y, r.polygon) for r in g.regions]
            assert max(where) >= 0, (x, y)  # cae en alguna región (dentro o en su borde)
            if 1 in where:  # dentro de un polígono: ningún otro lo contiene
                assert where.count(1) == 1 and 0 not in where, (x, y)


@pytest.mark.parametrize("gid", GRAPHS)
@settings(max_examples=300, deadline=None)
@given(u=st.floats(0, 1), v=st.floats(0, 1), du=st.floats(0, 0.5), dv=st.floats(0, 0.5))
def test_monotonia(gid, u, v, du, dv):
    g = STABILITY_GRAPHS[gid]
    x0, x1, y0, y1 = _frame(g)
    x, y = x0 + u * (x1 - x0), y0 + v * (y1 - y0)
    zone = locate(x, y, g.regions)
    assert zone is not None
    assert locate(min(x + du * (x1 - x0), x1), y, g.regions) >= zone  # sube x: no mejora
    assert locate(x, max(y - dv * (y1 - y0), y0), g.regions) >= zone  # baja y: no mejora


@pytest.mark.parametrize("gid", GRAPHS)
def test_regla_del_limite(gid):
    g = STABILITY_GRAPHS[gid]
    for k, line in ((2, g.boundaries[0]), (3, g.boundaries[1])):
        for x, y in line[1:-1]:
            assert locate(x, y, g.regions) == k


@pytest.mark.parametrize("gid", GRAPHS)
def test_zonas_entre_fronteras(gid):
    g = STABILITY_GRAPHS[gid]
    x, (_, step_y) = X_MID[gid], STEP[gid]
    up, low = _y_at(g.boundaries[0], x), _y_at(g.boundaries[1], x)
    assert up > low
    assert locate(x, (up + low) / 2, g.regions) == 2
    assert locate(x, up + step_y / 2, g.regions) == 1
    assert locate(x, low - step_y / 2, g.regions) == 3
    # lo mismo por el lector, con valores del gráfico
    assert read_stability_graph(gid, x, _to_value(g, (up + low) / 2)).zone == 2
    assert read_stability_graph(gid, x, _to_value(g, up + step_y / 2)).zone == 1
    assert read_stability_graph(gid, x, _to_value(g, low - step_y / 2)).zone == 3


def test_lectura_normal():
    r = read_stability_graph("Mathews-Potvin1988", 10.0, 30.0)
    assert isinstance(r, GraphReading)
    assert r.graph_id == "Mathews-Potvin1988" and r.info.method_id == "Mathews-Potvin1988"
    assert r.zone_label == STABILITY_GRAPHS["Mathews-Potvin1988"].zone_labels[r.zone]
    assert (r.x, r.y) == (10.0, 30.0) and r.extrapolated is False and r.warnings == ()


def test_mathews_sobre_el_marco():
    r = read_stability_graph("Mathews-Potvin1988", 3, 5000)
    assert r.y == 1000.0 and r.zone == 1 and r.zone_label == "stable"
    assert "N' above the graph (1000); read at 1000" in r.warnings


def test_mathews_bajo_el_marco():
    r = read_stability_graph("Mathews-Potvin1988", 3, 0.05)
    assert r.zone == 3 and r.zone_label == "caved"
    assert "N' below the graph (0.1): taken as caved" in r.warnings


def test_mathews_mas_alla_del_marco():
    r = read_stability_graph("Mathews-Potvin1988", 30, 500)
    assert r.zone == 3
    assert "hydraulic radius beyond the graph (25 m): taken as caved" in r.warnings


def test_mathews_franja_a_trazos():
    g = STABILITY_GRAPHS["Mathews-Potvin1988"]
    x_dash = min(p[0] for r in g.no_data for p in r.polygon)
    assert 5.0 < x_dash < 25.0
    r = read_stability_graph("Mathews-Potvin1988", (x_dash + 25.0) / 2, 100.0)
    assert r.extrapolated is True
    assert "point where the graph boundaries are dashed (extrapolated)" in r.warnings
    r = read_stability_graph("Mathews-Potvin1988", x_dash / 2, 100.0)
    assert r.extrapolated is False


def test_laubscher_sobre_el_marco():
    r = read_stability_graph("Laubscher1994-stability", 10, 120)
    assert r.y == 100.0 and r.zone == 1
    assert "MRMR above the graph (100); read at 100" in r.warnings


def test_laubscher_mas_alla_del_marco():
    r = read_stability_graph("Laubscher1994-stability", 90, 50)
    assert r.zone == 3 and r.zone_label == "caving"
    assert "hydraulic radius beyond the graph (80 m): taken as caving" in r.warnings


def test_laubscher_mrmr_cero_es_valido():
    assert read_stability_graph("Laubscher1994-stability", 10, 0).zone == 3


@pytest.mark.parametrize("gid, x, y", [
    ("Mathews-Potvin1988", math.nan, 10.0),
    ("Mathews-Potvin1988", 5.0, math.nan),
    ("Mathews-Potvin1988", math.inf, 10.0),
    ("Mathews-Potvin1988", 0.0, 10.0),
    ("Mathews-Potvin1988", -1.0, 10.0),
    ("Mathews-Potvin1988", 5.0, 0.0),
    ("Laubscher1994-stability", 5.0, -1.0),
    ("Laubscher1994-stability", 0.0, 50.0),
])
def test_datos_imposibles(gid, x, y):
    with pytest.raises(ValueError):
        read_stability_graph(gid, x, y)


def test_grafico_desconocido():
    with pytest.raises(ValueError, match="Mathews-Potvin1988"):
        read_stability_graph("Mathews-1980", 5.0, 10.0)
