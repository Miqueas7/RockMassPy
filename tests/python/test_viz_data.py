import math
import os
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")

from matplotlib.colors import to_hex  # noqa: E402

import rockmasspy as rm  # noqa: E402
from rockmasspy.range_table import RangeClass, RangeTable  # noqa: E402
from rockmasspy.support import SupportCatalog, SupportType  # noqa: E402
from rockmasspy.viz import Style, plot_class_histogram, plot_correlation, save_figure, support_color  # noqa: E402


def _pairs(n=20):
    import random

    rnd = random.Random(7)
    out = []
    for _ in range(n):
        q = 10 ** rnd.uniform(-2, 2)
        out.append((q, 9 * math.log(q) + 44 + rnd.gauss(0, 5)))
    return out


def _site(name, a):
    return rm.CustomCorrelation(name=name, from_="Q", to="RMR89", form=rm.CorrelationForm.LogLinear,
                                a=9.0, b=a, valid_min=0.05, valid_max=50.0)


def _texts(fig):
    return [t.get_text() for t in fig.findobj(lambda a: hasattr(a, "get_text"))]


def test_dispersion_tres_curvas_puntos_y_eje_log():
    fig = plot_correlation(_pairs(), x="Q", y="RMR89", global_correlations=[rm.Correlation.RmrFromQ_Huang2026],
                           site=[_site("a", 44.0), _site("b", 40.0)])
    ax = fig.axes[0]
    assert ax.get_xscale() == "log"
    assert len(ax.lines) == 3
    assert len(ax.collections[0].get_offsets()) == 20
    assert sorted(ln.get_label() for ln in ax.lines) == ["RmrFromQ_Huang2026", "sitio:a", "sitio:b"]
    assert any("dispersión" in t for t in _texts(fig))


def test_curva_del_sitio_se_recorta_a_su_rango_valido():
    fig = plot_correlation(_pairs(), x="Q", y="RMR89", site=[_site("a", 44.0)])
    xs = fig.axes[0].lines[0].get_xdata()
    assert min(xs) >= 0.05 - 1e-12 and max(xs) <= 50.0 + 1e-12


def test_curva_global_omite_valores_fuera_de_validez():
    pairs = [(30.0, 40.0), (60.0, 55.0), (90.0, 80.0)]
    fig = plot_correlation(pairs, x="RMR89'", y="GSI",
                           global_correlations=[rm.Correlation.GsiFromRmr89Prime_HoekDiederichs2006])
    xs = fig.axes[0].lines[0].get_xdata()
    assert len(xs) > 10 and min(xs) > 23


def test_ingles():
    fig = plot_correlation(_pairs(), x="Q", y="RMR89", global_correlations=[rm.Correlation.RmrFromQ_Huang2026],
                           site=[_site("a", 44.0)], style=Style(lang="en"))
    assert any("calibrate a site correlation" in t for t in _texts(fig))
    assert "site:a" in [ln.get_label() for ln in fig.axes[0].lines]
    assert any(t == "RmrFromQ_Huang2026, site:a" for t in _texts(fig))  # el pie


def test_from_o_to_distinto_lanza():
    with pytest.raises(ValueError, match="RmrFromQ_Huang2026"):
        plot_correlation(_pairs(), x="Q'", y="RMR89", global_correlations=[rm.Correlation.RmrFromQ_Huang2026])
    with pytest.raises(ValueError, match="RmrFromQ_Bieniawski1976"):
        plot_correlation(_pairs(), x="Q", y="RMR89", global_correlations=[rm.Correlation.RmrFromQ_Bieniawski1976])
    with pytest.raises(ValueError, match="site:a"):
        plot_correlation(_pairs(), x="Q", y="GSI", site=[_site("a", 44.0)])


def test_pares_invalidos_con_indice():
    for bad in ((1.0, float("nan")), (float("inf"), 1.0)):
        with pytest.raises(ValueError, match="pairs.*1"):
            plot_correlation([(1.0, 50.0), bad], x="Q", y="RMR89")
    with pytest.raises(ValueError, match="pairs.*2"):
        plot_correlation([(1.0, 50.0), (2.0, 50.0), (0.0, 50.0)], x="Q", y="RMR89")


def test_sin_pares_lanza():
    with pytest.raises(ValueError, match="pairs"):
        plot_correlation([], x="Q", y="RMR89")


RMR = RangeTable("RMR", "RMR89", [RangeClass(0, 20, "V", "S3"), RangeClass(20, 40, "IV", "S3"),
                                  RangeClass(40, 60, "III", "S2"), RangeClass(60, 80, "II", "S1"),
                                  RangeClass(80, 100, "I", "S0")])
CATALOG = SupportCatalog([SupportType("S0", 1), SupportType("S1", 2), SupportType("S2", 3), SupportType("S3", 4)])


def _heights(fig):
    return [p.get_height() for p in fig.axes[0].patches]


def test_histograma_cinco_barras_suman_30_y_limite_al_peor():
    values = [40.0] + [5 + 3.2 * i for i in range(29)]
    fig = plot_class_histogram(values, RMR, catalog=CATALOG)
    h = _heights(fig)
    assert len(h) == 5 and sum(h) == 30
    labels = [t.get_text() for t in fig.axes[0].get_xticklabels()]
    assert labels == ["V", "IV", "III", "II", "I"]
    # 40 exacto cuenta en IV (la peor), no en III
    assert RMR.lookup(40.0).label == "IV"
    assert h[1] == sum(1 for v in values if RMR.lookup(v).label == "IV")


def test_histograma_40_exacto_va_a_la_clase_iv():
    # sin lookup: el valor 40 está en el límite entre IV [20, 40] y III [40, 60]; cae en la peor (IV)
    assert _heights(plot_class_histogram([40.0], RMR)) == [0, 1, 0, 0, 0]


def test_histograma_cantidad_y_rango_sobre_la_barra():
    fig = plot_class_histogram([10, 50, 55], RMR, catalog=CATALOG)
    txt = _texts(fig)
    assert "III (40–60): 2" in txt and "V (0–20): 1" in txt and "I (80–100): 0" in txt


def test_curva_recortada_se_corta_donde_empieza_el_recorte():
    fig = plot_correlation([(20.0, 22.0), (100.0, 100.0)], x="RMR89", y="RMR14",
                           global_correlations=[rm.Correlation.Rmr14FromRmr89_Osinergmin2017])
    xs = fig.axes[0].lines[0].get_xdata()
    assert max(xs) <= 89.2


def test_sin_globales_no_hay_nota_y_curva_vacia_no_se_dibuja():
    fig = plot_correlation(_pairs(), x="Q", y="RMR89", site=[_site("a", 44.0)])
    assert not any("dispersión" in t for t in _texts(fig))
    far = rm.CustomCorrelation(name="lejos", from_="Q", to="RMR89", form=rm.CorrelationForm.LogLinear,
                               a=9.0, b=44.0, valid_min=1e4, valid_max=1e5)
    fig = plot_correlation(_pairs(), x="Q", y="RMR89", site=[far])
    assert len(fig.axes[0].lines) == 0
    assert "sitio:lejos" not in [t.get_text() for t in fig.axes[0].get_legend().get_texts()]


def test_histograma_fuera_de_clases_y_color():
    gap = RangeTable("RMR", "RMR89", [RangeClass(0, 20, "V", "S3"), RangeClass(40, 60, "III", "S0")])
    st = Style()
    fig = plot_class_histogram([10, 30, 50, 55, 120], gap, catalog=CATALOG, style=st)
    assert _heights(fig) == [1, 2]
    assert any("fuera" in t.lower() and "2" in t for t in _texts(fig))
    ps = fig.axes[0].patches
    assert to_hex(ps[0].get_facecolor()) == support_color(4, 4, st).lower()
    assert to_hex(ps[1].get_facecolor()) == support_color(1, 4, st).lower()
    assert any("RMR89" in t for t in _texts(fig))


def test_histograma_sin_catalogo_gris_y_nan_lanza():
    fig = plot_class_histogram([10, 50], RMR)
    assert len({to_hex(p.get_facecolor()) for p in fig.axes[0].patches}) == 1
    with pytest.raises(ValueError, match="values.*1"):
        plot_class_histogram([10, float("nan")], RMR)


def test_muestras():
    d = os.environ.get("RMP_SAMPLES_DIR")
    if not d:
        pytest.skip("RMP_SAMPLES_DIR no definido")
    d = Path(d)
    pairs = _pairs(40)
    for lang in ("es", "en"):
        fig = plot_correlation(pairs, x="Q", y="RMR89", global_correlations=[rm.Correlation.RmrFromQ_Huang2026],
                               site=[_site("sintetica", 44.0)], style=Style(lang=lang))
        save_figure(fig, d / f"t10_correlacion_{lang}.png")
    import random

    rnd = random.Random(3)
    values = [min(100, max(0, rnd.gauss(55, 18))) for _ in range(120)] + [40.0, 40.0, 150.0]
    save_figure(plot_class_histogram(values, RMR, catalog=CATALOG), d / "t10_histograma_es.png")
