import subprocess
import sys

import pytest

pytest.importorskip("matplotlib")
import rockmasspy.viz as viz  # noqa: E402
from rockmasspy.viz import Style  # noqa: E402


def test_style_defaults_and_validation():
    s = Style()
    assert (s.lang, s.size, s.brand, s.dpi, s.font_size) == ("es", "A4", "", 200, 9.0)
    assert len(s.support_colors) == 9
    with pytest.raises(ValueError, match="es.*en"):
        Style(lang="fr")
    with pytest.raises(ValueError, match="cartilla.*A4.*A3"):
        Style(size="A5")
    with pytest.raises(ValueError, match="dpi"):
        Style(dpi=10)


def test_text_lookup():
    assert viz.text("undefined", "es") == "sin definir"
    assert viz.text("undefined", "en") == "undefined"
    with pytest.raises(KeyError, match="nope"):
        viz.text("nope", "es")


def test_new_figure_size_and_brand():
    fig = viz.new_figure(Style(size="A3", brand="Señal Ñ"))
    w, h = fig.get_size_inches()
    assert (w, h) == pytest.approx((42 / 2.54, 29.7 / 2.54))
    assert any(t.get_text() == "Señal Ñ" for t in fig.texts)
    viz.footer(fig, "RMR89", Style())
    assert any(t.get_text() == "RMR89" for t in fig.texts)


@pytest.mark.parametrize("ext", ["PNG", "svg", "pdf"])
def test_save_figure_creates_folders(tmp_path, ext):
    fig = viz.new_figure(Style(dpi=50))
    out = viz.save_figure(fig, tmp_path / "a" / "b" / f"c.{ext}")
    assert out.stat().st_size > 0


def test_save_figure_bad_extension(tmp_path):
    with pytest.raises(ValueError, match="png.*svg.*pdf"):
        viz.save_figure(viz.new_figure(Style()), tmp_path / "c.jpg")


def test_support_color_stable_and_ordered():
    s = Style()
    assert viz.support_color(1, 5, s) != viz.support_color(5, 5, s)
    assert viz.support_color(2, 5, s) == viz.support_color(2, 5, s)
    assert viz.support_color(1, 5, s) == s.support_colors[0]
    assert viz.support_color(5, 5, s) == s.support_colors[-1]
    assert viz.support_color(1, 1, s) == s.support_colors[0]
    for bad in (0, 6):
        with pytest.raises(ValueError, match="order"):
            viz.support_color(bad, 5, s)


def test_import_and_call_without_matplotlib_in_fresh_interpreter():
    code = ("import sys; sys.modules['matplotlib'] = None; import rockmasspy, rockmasspy.viz as v\n"
            "try:\n    v.save_figure(None, 'x.png')\nexcept ImportError as e:\n    print(e)")
    r = subprocess.run([sys.executable, "-I", "-c", code], check=True, capture_output=True, text=True)
    assert "rockmasspy[viz]" in r.stdout
