import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
import rockmasspy as rm
from rockmasspy.chart_regions import _classify
from rockmasspy.q_chart_data import Q_CHARTS
from rockmasspy.viz import DEFAULT_SUPPORT_COLORS, Style, plot_q_chart
from rockmasspy.viz.q_chart import _label_point
from rockmasspy.viz.save import save_figure

from test_batch import TABLES, tr

# Los códigos de las tablas sintéticas de test_batch dan 3 rangos como mucho; se arman 8 tramos con q repartido.
_QS = [0.005, 0.03, 0.1, 0.4, 1.5, 4.5, 15.0, 60.0]


def _res(edition="Q-NGI-2025", n=8):
    ts = [tr(f"SECRETO-{i}", "crucero", 3.0 + i, q_valor=_QS[i % 8], labor_codigo="SECRETO-123") for i in range(n)]
    out = rm.add_q_chart_reference(rm.classify_tramos(ts, TABLES), "C", edition=edition)
    return out


def _textos(fig):
    fig.canvas.draw()
    return [t.get_text() for t in fig.findobj(lambda a: hasattr(a, "get_text"))]


def _lum(rgb):
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in rgb[:3]]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _regiones(fig):
    return [p for p in fig.axes[0].patches if p.get_fill()]


def test_nueve_regiones_con_luminosidad_decreciente_y_trama():
    fig = plot_q_chart()
    reg = _regiones(fig)
    assert len(reg) == 9
    lum = [_lum(p.get_facecolor()) for p in reg]
    assert all(a > b for a, b in zip(lum, lum[1:]))
    assert len(DEFAULT_SUPPORT_COLORS) >= 9
    assert any(p.get_hatch() for p in fig.axes[0].patches)
    assert fig.axes[0].get_xscale() == "log" and fig.axes[0].get_yscale() == "log"
    assert fig.axes[0].get_xlim() == (0.001, 1000.0) and fig.axes[0].get_ylim() == (1.0, 100.0)


@pytest.mark.parametrize("ed", sorted(Q_CHARTS))
def test_cada_rotulo_cae_dentro_de_su_region(ed):
    for reg in Q_CHARTS[ed].regions:
        x, y = _label_point(reg.polygon)
        assert _classify(x, y, reg.polygon) > 0, (ed, reg.key)


def test_cuerda_si_el_centroide_cae_fuera():
    u = ((0.0, 0.0), (3.0, 0.0), (3.0, 3.0), (2.0, 3.0), (2.0, 1.0), (1.0, 1.0), (1.0, 3.0), (0.0, 3.0))  # forma de U
    x, y = _label_point(u)
    assert _classify(x, y, u) > 0


def test_ocho_tramos_y_un_punto_suelto_como_estrella():
    fig = plot_q_chart(results=_res())
    assert len(fig.axes[0].collections) == 8
    fig = plot_q_chart(results=_res(), points=[(2.0, 8.0)])
    assert len(fig.axes[0].collections) == 9
    estrella = fig.axes[0].collections[-1]
    assert tuple(estrella.get_facecolor()[0][:3]) == (0.0, 0.0, 0.0)
    assert len({c.get_paths()[0].vertices.tobytes() for c in fig.axes[0].collections}) >= 2


def test_solo_puntos_sin_tramos():
    assert len(plot_q_chart(points=[(1.0, 5.0)]).axes[0].collections) == 1


def test_foco5_ningun_texto_con_ids():
    for fig in (plot_q_chart(results=_res()), plot_q_chart(results=_res(), style=Style(lang="en"))):
        t = _textos(fig)
        assert not any("SECRETO" in x for x in t)
        assert not any("T0" in x for x in t)


def test_pie_con_fuente_y_edicion():
    t = _textos(plot_q_chart())
    assert any("digitalizado" in x and "Q-NGI-2025" in x and "Fig. 4-1" in x for x in t)
    assert any("Fig. 7" in x and "Q-NGI-2015" in x for x in _textos(plot_q_chart("Q-NGI-2015")))


def test_ingles():
    t = _textos(plot_q_chart(style=Style(lang="en")))
    assert "Q index" in t and "Equivalent dimension De (m)" in t
    assert any("digitized" in x for x in t)


def test_errores():
    with pytest.raises(ValueError, match="edition"):
        plot_q_chart("Q-1974")
    sin_ref = rm.classify_tramos([tr("a", "galeria", 4.0, q_valor=1.0)], TABLES)
    with pytest.raises(ValueError, match="reference"):
        plot_q_chart(results=sin_ref)


def test_sin_matplotlib_nombra_el_extra():
    code = ("import sys; sys.modules['matplotlib'] = None; import rockmasspy.viz as v\n"
            "try:\n    v.plot_q_chart()\nexcept ImportError as e:\n    print(e)")
    r = subprocess.run([sys.executable, "-I", "-c", code], check=True, capture_output=True, text=True)
    assert "rockmasspy[viz]" in r.stdout


def test_muestras():
    d = os.environ.get("RMP_SAMPLES_DIR")
    if not d:
        pytest.skip("RMP_SAMPLES_DIR no definido")
    for ed, tag in (("Q-NGI-2025", "2025"), ("Q-NGI-2015", "2015")):
        save_figure(plot_q_chart(ed, results=_res(ed), points=[(2.0, 8.0)]), Path(d) / f"t5_carta_q_{tag}_es.png")
