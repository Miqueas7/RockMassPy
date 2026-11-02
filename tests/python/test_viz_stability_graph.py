import math
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
import rockmasspy as rm
from rockmasspy.chart_regions import _classify
from rockmasspy.stability_graphs import STABILITY_GRAPHS
from rockmasspy.viz import Style, plot_stability_graph
from rockmasspy.viz._label import _label_point
from rockmasspy.viz.save import save_figure

from test_stope_surfaces import csv as csv_caras

LAUB = "Laubscher1994-stability"
CASOS = {"Mathews-Potvin1988": [(2.0, 0.5), (4.0, 3.0), (6.0, 12.0), (8.0, 40.0), (10.0, 150.0), (14.0, 0.8)],
         LAUB: [(5.0, 80.0), (10.0, 60.0), (20.0, 45.0), (30.0, 30.0), (40.0, 70.0), (60.0, 20.0)]}


ESTRELLA = {"Mathews-Potvin1988": (12.0, 20.0), LAUB: (15.0, 50.0)}


def _textos(fig):
    fig.canvas.draw()
    return [t.get_text() for t in fig.findobj(lambda a: hasattr(a, "get_text"))]


def _lum(rgb):
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in rgb[:3]]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _regiones(fig):
    return [p for p in fig.axes[0].patches if p.get_fill()]


@pytest.mark.parametrize("gid", sorted(STABILITY_GRAPHS))
def test_tres_zonas_con_luminosidad_decreciente(gid):
    reg = _regiones(plot_stability_graph(gid))
    assert len(reg) == 3
    lum = [_lum(p.get_facecolor()) for p in reg]
    assert lum[0] > lum[1] > lum[2]


def test_trama_y_ejes_por_grafico():
    ax = plot_stability_graph().axes[0]
    assert any(p.get_hatch() for p in ax.patches) and ax.get_yscale() == "log"
    assert ax.get_xlim() == (0.0, 25.0) and ax.get_ylim() == (0.1, 1000.0)
    ax = plot_stability_graph(LAUB).axes[0]
    assert not any(p.get_hatch() for p in ax.patches) and ax.get_yscale() == "linear"
    assert ax.get_xlim() == (0.0, 80.0) and ax.get_ylim() == (0.0, 100.0)


@pytest.mark.parametrize("gid", sorted(STABILITY_GRAPHS))
def test_cada_rotulo_cae_dentro_de_su_region(gid):
    for reg in STABILITY_GRAPHS[gid].regions:
        x, y = _label_point(reg.polygon)
        assert _classify(x, y, reg.polygon) > 0, (gid, reg.key)


@pytest.mark.parametrize("gid", sorted(STABILITY_GRAPHS))
def test_seis_casos_blancos_y_una_estrella(gid):
    fig = plot_stability_graph(gid, cases=CASOS[gid])
    cols = fig.axes[0].collections
    assert len(cols) == 6
    reg = {tuple(p.get_facecolor()) for p in _regiones(fig)}
    for c in cols:
        assert tuple(c.get_facecolor()[0]) == (1.0, 1.0, 1.0, 1.0) and tuple(c.get_facecolor()[0]) not in reg
        assert tuple(c.get_edgecolor()[0][:3]) == (0.0, 0.0, 0.0)
    fig = plot_stability_graph(gid, cases=CASOS[gid], points=[CASOS[gid][0]])
    assert len(fig.axes[0].collections) == 7
    assert tuple(fig.axes[0].collections[-1].get_facecolor()[0][:3]) == (0.0, 0.0, 0.0)


def test_foco5_ningun_texto_con_ids(tmp_path):
    res = rm.assess_stope_surfaces(rm.load_stope_surfaces(csv_caras(tmp_path)))
    cases = [(r.mathews.reading.x, r.mathews.reading.y) for r in res]
    for st in (Style(), Style(lang="en")):
        t = _textos(plot_stability_graph(cases=cases, style=st))
        assert not any("SECRETO" in x or "S1" in x or "L-1" in x for x in t)


def test_pie_con_fuente():
    t = _textos(plot_stability_graph())
    assert any("digitalizado" in x and "Fig. 7.22" in x and "Mathews-Potvin1988" in x for x in t)
    assert any("digitalizado" in x and "Fig. 1" in x for x in _textos(plot_stability_graph(LAUB)))


def test_ingles():
    t = _textos(plot_stability_graph(style=Style(lang="en")))
    assert "Hydraulic radius HR (m)" in t and "Stability number N′" in t and "Stable" in t
    assert any("digitized" in x for x in t)
    assert "MRMR (points)" in _textos(plot_stability_graph(LAUB, style=Style(lang="en")))


def test_grafico_inexistente():
    with pytest.raises(ValueError, match="unknown stability graph"):
        plot_stability_graph("Nickson")


@pytest.mark.parametrize("gid,bad", [("Mathews-Potvin1988", (float("nan"), 5.0)), ("Mathews-Potvin1988", (1.0, float("inf"))),
                                     ("Mathews-Potvin1988", (0.0, 5.0)), ("Mathews-Potvin1988", (1.0, 0.0)),
                                     (LAUB, (1.0, -2.0)), (LAUB, (-1.0, 5.0)), (LAUB, (5.0, float("nan")))])
@pytest.mark.parametrize("arg", ["cases", "points"])
def test_valores_invalidos(gid, bad, arg):
    with pytest.raises(ValueError, match=arg):
        plot_stability_graph(gid, **{arg: [bad]})


def test_mrmr_cero_es_valido():
    plot_stability_graph(LAUB, cases=[(5.0, 0.0)])


def test_sin_matplotlib_nombra_el_extra():
    code = ("import sys; sys.modules['matplotlib'] = None; import rockmasspy.viz as v\n"
            "try:\n    v.plot_stability_graph()\nexcept ImportError as e:\n    print(e)")
    r = subprocess.run([sys.executable, "-I", "-c", code], check=True, capture_output=True, text=True)
    assert "rockmasspy[viz]" in r.stdout


def test_muestras():
    d = os.environ.get("RMP_SAMPLES_DIR")
    if not d:
        pytest.skip("RMP_SAMPLES_DIR no definido")
    for gid, tag in (("Mathews-Potvin1988", "mathews"), (LAUB, "laubscher")):
        save_figure(plot_stability_graph(gid, cases=CASOS[gid], points=[ESTRELLA[gid]]), Path(d) / f"t6_estabilidad_{tag}_es.png")


@pytest.mark.parametrize("gid,fuera", [("Mathews-Potvin1988", [(10.0, 0.05), (30.0, 5.0), (30.0, 5000.0)]),
                                       (LAUB, [(100.0, 50.0), (10.0, 150.0)])])
def test_casos_fuera_del_marco_se_dibujan_en_el_borde(gid, fuera):  # I1
    cases = [CASOS[gid][0], *fuera]
    ax = plot_stability_graph(gid, cases=cases).axes[0]
    assert len(ax.collections) == len(cases)
    (x0, x1), (y0, y1) = ax.get_xlim(), ax.get_ylim()
    for c in ax.collections:
        x, y = c.get_offsets()[0]
        assert x0 <= x <= x1 and y0 <= y <= y1
        assert tuple(c.get_facecolor()[0]) == (1.0, 1.0, 1.0, 1.0)


@pytest.mark.parametrize("gid", sorted(STABILITY_GRAPHS))
def test_rotulo_de_transicion_dentro_de_su_banda(gid):  # M2
    g = STABILITY_GRAPHS[gid]
    zona2 = next(r for r in g.regions if r.key == 2)
    fig = plot_stability_graph(gid)
    fig.canvas.draw()
    ax = fig.axes[0]
    t = next(t for t in ax.texts if t.get_text() == "Transición")
    bb = t.get_window_extent().transformed(ax.transData.inverted())
    cx, cy = (bb.x0 + bb.x1) / 2, (bb.y0 + bb.y1) / 2
    assert _classify(cx, math.log10(cy) if g.y_log else cy, zona2.polygon) > 0
    assert t.get_fontsize() == Style().font_size - 2


def test_rotulos_de_zona_iguales_a_la_lectura_en_ingles():  # M7
    for gid, g in STABILITY_GRAPHS.items():
        t = _textos(plot_stability_graph(gid, style=Style(lang="en")))
        for k in (1, 2, 3):
            assert g.zone_labels[k].capitalize() in t, (gid, k)
