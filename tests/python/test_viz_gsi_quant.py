import os
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")

from rockmasspy.viz import Style, plot_gsi_quantified, save_figure  # noqa: E402


def _texts(fig):
    return [t.get_text() for t in fig.texts] + [t.get_text() for t in fig.axes[0].texts]


def test_ejes_y_limites():
    fig = plot_gsi_quantified()
    assert len(fig.axes) == 1
    ax = fig.axes[0]
    assert ax.get_xlim() == (0, 30)
    assert ax.get_ylim() == (0, 100)


def test_una_isolinea_por_contorno():
    fig = plot_gsi_quantified(contours=(20, 40, 60))
    assert len(fig.axes[0].collections) == 3
    assert len(plot_gsi_quantified().axes[0].collections) == 9


def test_titulo_en_ingles():
    assert "Quantified" in plot_gsi_quantified(style=Style(lang="en")).axes[0].get_title()
    assert "cuantificada" in plot_gsi_quantified().axes[0].get_title()


def test_punto_dibujado_y_rotulo():
    fig = plot_gsi_quantified([(22, 70)], labels=["P1"])
    ax = fig.axes[0]
    offs = [tuple(o) for c in ax.collections for o in c.get_offsets()]
    assert (22.0, 70.0) in offs
    assert "P1" in [t.get_text() for t in ax.texts]


def test_punto_fuera_del_dominio():
    with pytest.raises(ValueError, match="0"):
        plot_gsi_quantified([(31, 50)])
    with pytest.raises(ValueError, match="1"):
        plot_gsi_quantified([(10, 50), (10, 101)])


def test_pie():
    assert any("GSI-2013" in t for t in _texts(plot_gsi_quantified()))


def test_muestras():
    d = os.environ.get("RMP_SAMPLES_DIR")
    if not d:
        pytest.skip("RMP_SAMPLES_DIR no definido")
    for lang in ("es", "en"):
        fig = plot_gsi_quantified([(22, 70), (8, 35)], labels=["P1", "P2"], style=Style(lang=lang))
        save_figure(fig, Path(d) / f"t3_gsi_quant_{lang}.png")
