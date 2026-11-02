import math

import numpy as np
import pytest
from hypothesis import given, settings, strategies as st

import rockmasspy as rm
from rockmasspy.chart_regions import _classify, locate
from rockmasspy.q_chart_data import ESR_TABLES, Q_CHART_FRAME, Q_CHARTS

EDITIONS = ["Q-NGI-2025", "Q-NGI-2015"]
ESR = {"A": (3.0, 5.0), "B": (2.0, 2.5), "C": (1.6, 1.6), "D": (1.3, 1.3), "E": (1.0, 1.0), "F": (0.8, 0.8),
       "G": (0.5, 0.5)}
LQ0, LQ1 = math.log10(Q_CHART_FRAME[0]), math.log10(Q_CHART_FRAME[1])
LD0, LD1 = math.log10(Q_CHART_FRAME[2]), math.log10(Q_CHART_FRAME[3])


def test_marco():
    assert Q_CHART_FRAME == (0.001, 1000.0, 1.0, 100.0)
    assert set(Q_CHARTS) == set(EDITIONS)


@pytest.mark.parametrize("ed", EDITIONS)
def test_esr_por_letra(ed):
    assert {k: v[:2] for k, v in ESR_TABLES[ed].items()} == ESR
    assert "circular" in ESR_TABLES[ed]["B"][2] and "rectangular" in ESR_TABLES[ed]["B"][2]


def test_esr_igual_en_las_dos_ediciones():
    assert {k: v[:2] for k, v in ESR_TABLES["Q-NGI-2025"].items()} == \
        {k: v[:2] for k, v in ESR_TABLES["Q-NGI-2015"].items()}


@pytest.mark.parametrize("ed", EDITIONS)
def test_cobertura_sin_huecos_ni_solapes(ed):
    regions = Q_CHARTS[ed].regions
    assert sorted(r.key for r in regions) == list(range(1, 10))
    for x in np.linspace(LQ0, LQ1, 200):
        for y in np.linspace(LD0, LD1, 200):
            where = [_classify(x, y, r.polygon) for r in regions]
            assert max(where) >= 0, (x, y)  # cae en alguna región (dentro o en su borde)
            if 1 in where:  # dentro de un polígono: ningún otro lo contiene
                assert where.count(1) == 1 and 0 not in where, (x, y)


@pytest.mark.parametrize("ed", EDITIONS)
@settings(max_examples=300, deadline=None)
@given(x=st.floats(LQ0, LQ1), y=st.floats(LD0, LD1), dx=st.floats(0, 2), dy=st.floats(0, 1))
def test_monotonia(ed, x, y, dx, dy):
    regions = Q_CHARTS[ed].regions
    cat = locate(x, y, regions)
    assert locate(max(x - dx, LQ0), y, regions) >= cat  # baja Q: no mejora
    assert locate(x, min(y + dy, LD1), regions) >= cat  # sube De: no mejora


@pytest.mark.parametrize("ed", EDITIONS)
@pytest.mark.parametrize("lo, hi", [(4, 5), (7, 8)])
def test_regla_del_limite_en_vertices_compartidos(ed, lo, hi):
    regions = Q_CHARTS[ed].regions
    poly = {r.key: set(r.polygon) for r in regions}
    # vértices de la frontera entre lo y hi que no tocan una tercera región (los extremos tocan el marco o la 9)
    shared = {v for v in poly[lo] & poly[hi] if not any(v in poly[k] for k in poly if k not in (lo, hi))}
    assert len(shared) >= 3
    for x, y in shared:
        assert locate(x, y, regions) == hi


@pytest.mark.parametrize("ed", EDITIONS)
def test_zonas_sin_datos(ed):
    nd = Q_CHARTS[ed].no_data
    assert locate(-2.0, math.log10(2.0), nd) is not None  # bajo el corte De = 3
    assert locate(2.9, 1.0, nd) is not None  # más allá de Q = 400
    assert locate(0.0, 1.5, nd) is None


def test_leyenda():
    c25, c15 = Q_CHARTS["Q-NGI-2025"].categories, Q_CHARTS["Q-NGI-2015"].categories
    assert sorted(c25) == sorted(c15) == list(range(1, 10))
    assert c25[4].sfr_energy_j == 700 and c15[4].sfr_energy_j == 500
    assert c25[6].rrs == "RRS-A" and c15[6].rrs == "RRS I"
    assert c25[8].rrs == "RRS-C" and c15[8].rrs == "RRS III"
    assert c25[8].shotcrete_mm == (250, None) and c15[8].shotcrete_mm == (250, None)
    assert c25[1].shotcrete_mm is None and c25[3].shotcrete_mm == (50, 60)
    assert "cast concrete" in c15[8].label and "cast concrete" not in c25[8].label
    assert Q_CHARTS["Q-NGI-2025"].rrs_specs["RRS-A"] == {5.0: None, 10.0: "Si30/6 Ø16-20", 20.0: "D40/6+4 Ø16-20"}
    assert Q_CHARTS["Q-NGI-2015"].rrs_specs["RRS I"][20.0] == "D40/6+2 Ø16-20"
    assert Q_CHARTS["Q-NGI-2015"].rrs_specs["RRS II"][10.0] == "D45/6+2 Ø16-20"
    assert Q_CHARTS["Q-NGI-2025"].rrs_specs["RRS-C"][20.0] is None


@pytest.mark.parametrize("ed", EDITIONS)
def test_marcas(ed):
    ch = Q_CHARTS[ed]
    for marks, values in [
        (ch.spacing_with_sfr, [1.0, 1.2, 1.3, 1.5, 1.7, 2.1, 2.3, 2.5]),
        (ch.spacing_without_sfr, [1.6, 2.0, 3.0, 4.0]),
        (ch.bolt_length, [1.5, 2.4, 3, 5, 7, 11, 20]),
        (ch.rrs_spacing, [1.0, 1.7, 2.3, 2.9, 4.0]),
    ]:
        pos = [p for p, _ in marks]
        assert [m for _, m in marks] == values
        assert pos == sorted(pos) and len(set(pos)) == len(pos)
    for (q, _), q_ref in zip(ch.rrs_spacing, [0.001, 0.004, 0.01, 0.04, 0.1]):
        assert abs(math.log10(q) - math.log10(q_ref)) <= 0.02


@pytest.mark.parametrize("ed, method_id, fig", [("Q-NGI-2025", "Q-NGI-2025-chart", "Fig. 4-1"),
                                                ("Q-NGI-2015", "Q-NGI-2015-chart", "Fig. 7")])
def test_info(ed, method_id, fig):
    ch = Q_CHARTS[ed]
    assert ch.edition == ed
    assert ch.info.method_id == method_id
    assert ch.info.verification == rm.Verification.Primary
    assert fig in ch.info.source and "digitized" in ch.info.source


def test_fuente_declara_el_error_maximo_con_empalmes():  # I4
    assert "error <= 0.017 decade" in Q_CHARTS["Q-NGI-2025"].info.source
    assert "error <= 0.008 decade" in Q_CHARTS["Q-NGI-2015"].info.source
