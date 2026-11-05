"""Gráficos del nivel 3: isoprobabilidades en el plano Q–De y curva de calibración (textos es/en, sin ids)."""
import pytest

pytest.importorskip("matplotlib")
np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from matplotlib.text import Text  # noqa: E402

from rockmasspy.predictive import IsoprobabilityGrid  # noqa: E402
from rockmasspy.viz import Style, plot_calibration, plot_isoprobability  # noqa: E402
from rockmasspy.viz.style import TEXTS  # noqa: E402


def _grid():
    lq, ld = np.meshgrid(np.linspace(-2, 2, 30), np.linspace(0, 1, 30))
    p = 1 / (1 + np.exp(1.5 * lq - 3 * ld))  # P sube con menos Q y más De
    return IsoprobabilityGrid(lq, ld, p, "III", 365.0, None, None)


def _textos(fig):
    fig.canvas.draw()
    return [t.get_text() for t in fig.findobj(Text) if t.get_text()]


@pytest.mark.parametrize("lang", ["es", "en"])
def test_isoprobability_contours_points_and_texts(lang):
    fig = plot_isoprobability(_grid(), stable=[(1.0, 2.0), (10.0, 3.0)], failed=[(0.1, 5.0)], style=Style(lang=lang))
    ax = fig.axes[0]
    assert ax.get_xscale() == ax.get_yscale() == "log"
    pts = [c for c in ax.collections if type(c).__name__ == "PathCollection"]  # los scatter, no el ContourSet
    assert sorted(len(c.get_offsets()) for c in pts) == [1, 2]
    t = _textos(fig)
    assert TEXTS["iso_title"][lang].format(code="III") in t
    assert TEXTS["iso_source"][lang].format(days=365.0) in t
    assert {TEXTS["iso_stable"][lang], TEXTS["iso_failed"][lang]} <= set(t)
    assert any(x == "0.5" for x in t)  # el contorno rotulado


def test_isoprobability_without_points_and_bad_input():
    fig = plot_isoprobability(_grid(), levels=(0.25, 0.75), title="T")
    assert "T" in _textos(fig) and fig.axes[0].get_legend() is None
    with pytest.raises(ValueError, match="levels"):
        plot_isoprobability(_grid(), levels=(0.0, 0.5))
    with pytest.raises(ValueError, match=r"failed\[0\]"):
        plot_isoprobability(_grid(), failed=[(0.0, 2.0)])


@pytest.mark.parametrize("lang", ["es", "en"])
def test_calibration_curve(lang):
    curve = [(0.1, 0.12, 50), (0.4, 0.35, 40), (0.8, 0.82, 10)]
    fig = plot_calibration(curve, metrics={"poisson_deviance": 0.2, "observed_expected": 1.01, "calibration_slope": 0.95},
                           style=Style(lang=lang))
    ax = fig.axes[0]
    assert list(ax.lines[0].get_xdata()) == [0, 1]  # la diagonal
    assert list(ax.lines[1].get_ydata()) == [0.12, 0.35, 0.82]
    t = _textos(fig)
    assert TEXTS["cal_metrics"][lang].format(dev=0.2, oe=1.01, b=0.95) in t
    assert TEXTS["cal_title"][lang] in t


def test_calibration_without_metrics_and_empty():
    fig = plot_calibration([(0.5, 0.5, 3)], metrics={"poisson_deviance": float("nan")})
    assert not any("devianza" in x for x in _textos(fig))
    fig = plot_calibration([(1.5, 2.0, 3)])  # esperados sobre 1: la diagonal y los ejes llegan al mayor
    assert fig.axes[0].get_xlim() == (0, 2.0) and list(fig.axes[0].lines[0].get_xdata()) == [0, 2.0]
    with pytest.raises(ValueError, match="curve"):
        plot_calibration([])
