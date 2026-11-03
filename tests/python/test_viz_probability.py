import re
import subprocess
import sys

import pytest

pytest.importorskip("matplotlib")
from matplotlib.text import Text

from rockmasspy.probabilistic import run_probabilistic, summarize_fs
from rockmasspy.viz import Style, plot_fs_cdf, plot_fs_histogram
from rockmasspy.viz.save import save_figure
from rockmasspy.viz.style import TEXTS

from test_probabilistic import SMP_VARS, smp_base

FIGS = [plot_fs_histogram, plot_fs_cdf]


@pytest.fixture(scope="module")
def res():
    return run_probabilistic("planar", smp_base(), SMP_VARS, n=500, seed=3)


def _textos(fig):
    fig.canvas.draw()
    return [t.get_text() for t in fig.findobj(Text) if t.get_text()]


def _pof(res, lang):
    return f"{TEXTS['prob_pof'][lang]} = {res.pof * 100:.1f} %"


@pytest.mark.parametrize("plot", FIGS)
@pytest.mark.parametrize("lang", ["es", "en"])
def test_pof_text_parity_and_language(res, plot, lang):
    fig = plot(res, title="Bloque 1", style=Style(lang=lang))
    t = _textos(fig)
    assert _pof(res, lang) in t
    assert "Bloque 1" in t
    assert TEXTS["prob_fs"][lang] in t
    pie = [x for x in t if res.info.method_id in x][0]
    assert TEXTS["prob_samples"][lang].format(valid=res.n_valid, n=res.n) in pie
    assert f"{TEXTS['prob_seed'][lang]} {res.seed}" in pie
    assert TEXTS["prob_lhs"][lang] in pie
    other = "en" if lang == "es" else "es"
    assert TEXTS["prob_samples"][other].format(valid=res.n_valid, n=res.n) not in pie


def test_default_title_from_texts(res):
    assert TEXTS["prob_hist_title"]["es"] in _textos(plot_fs_histogram(res))
    assert TEXTS["prob_cdf_title"]["en"] in _textos(plot_fs_cdf(res, style=Style(lang="en")))


def test_hist_failure_bars_hatched_and_count(res):
    fig = plot_fs_histogram(res)
    ax = fig.axes[0]
    fail = [p for p in ax.patches if p.get_hatch()]
    assert fail and all(p.get_hatch() for p in fail)
    ok = [p for p in ax.patches if not p.get_hatch()]
    assert ok
    # el alto de cada barra es el conteo: las de falla suman n_failed
    assert round(sum(p.get_height() for p in fail)) == res.n_failed
    assert round(sum(p.get_height() for p in fail + ok)) == res.n_valid - sum(
        1 for f in res.fs if f is not None and f == float("inf"))
    assert any(abs(l.get_xdata()[0] - 1.0) < 1e-12 for l in ax.lines)  # línea FS = 1


def test_hist_exactly_one_counts_as_failure():
    r = summarize_fs([1.0] * 5 + [2.0] * 5, model="planar", sampling="lhs", n=10, seed=1, variables=("x",))
    ax = plot_fs_histogram(r, bins=4).axes[0]
    fail = [p for p in ax.patches if p.get_hatch()]
    assert round(sum(p.get_height() for p in fail)) == r.n_failed == 5


def test_cdf_marker_white_black_at_pof(res):
    ax = plot_fs_cdf(res).axes[0]
    m = [c for c in ax.collections if len(c.get_offsets()) == 1][0]
    assert tuple(m.get_facecolor()[0][:3]) == (1, 1, 1)
    assert tuple(m.get_edgecolor()[0][:3]) == (0, 0, 0)
    x, y = m.get_offsets()[0]
    assert x == 1.0 and y == pytest.approx(res.pof)
    assert any(abs(l.get_xdata()[0] - 1.0) < 1e-12 for l in ax.lines)


@pytest.mark.parametrize("plot", FIGS)
def test_non_formed_samples_say_so(plot):
    fs = [0.8, 1.2, None, 1.5, None, 0.9, 2.0, 1.1]
    r = summarize_fs(fs, model="wedge", sampling="monte_carlo", n=8, seed=4, variables=("x",))
    t = _textos(plot(r, style=Style(lang="en")))
    assert any("6 of 8 valid samples" in x for x in t) and any(TEXTS["prob_monte_carlo"]["en"] in x for x in t)
    assert _pof(r, "en") in t


@pytest.mark.parametrize("plot", FIGS)
def test_no_valid_samples(plot):
    r = summarize_fs([None, None], model="wedge", sampling="lhs", n=2, seed=1, variables=("x",))
    t = _textos(plot(r))
    assert TEXTS["prob_no_valid"]["es"] in t
    assert not any("PoF =" in x for x in t)


def test_bins_and_matplotlib_message(res):
    with pytest.raises(ValueError, match="bins"):
        plot_fs_histogram(res, bins=0)
    code = ("import sys; sys.modules['matplotlib']=None\nfrom rockmasspy.viz import plot_fs_cdf\n"
            "import rockmasspy.probabilistic as p\n"
            "r=p.summarize_fs([2.0],model='planar',sampling='lhs',n=1,seed=1,variables=())\n"
            "plot_fs_cdf(r)")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert "rockmasspy[viz]" in out.stderr


def _allowed(res, lang):
    ok = {v[lang] for k, v in TEXTS.items() if "{" not in v[lang]}
    ok.add(res.info.method_id)
    ok.add(TEXTS["prob_samples"][lang].format(valid=res.n_valid, n=res.n))
    ok.add(f"{TEXTS['prob_seed'][lang]} {res.seed}")
    k = sum(1 for f in res.fs if f is not None and f == float("inf"))
    ok.add(TEXTS["prob_infinite"][lang].format(k=k))
    ok.add(f"{TEXTS['prob_pof'][lang]} = {res.pof * 100:.1f} %" if res.pof is not None else "")
    return ok


@pytest.mark.parametrize("plot", FIGS)
@pytest.mark.parametrize("lang", ["es", "en"])
def test_all_text_from_texts_or_numbers(res, plot, lang):
    inf = summarize_fs([0.5, 2.0, float("inf"), float("inf"), None], model="planar", sampling="lhs", n=5,
                       seed=1, variables=("x",))
    for r in (res, inf):
        ok = _allowed(r, lang)
        for t in _textos(plot(r, style=Style(lang=lang))):
            for part in t.split(" | "):
                assert part in ok or re.fullmatch(r"[\d.−-]+", part), part


def test_inf_note_both_languages():
    r = summarize_fs([0.5, 2.0, float("inf"), float("inf")], model="planar", sampling="lhs", n=4, seed=1,
                     variables=("x",))
    for plot in FIGS:
        for lang in ("es", "en"):
            assert TEXTS["prob_infinite"][lang].format(k=2) in _textos(plot(r, style=Style(lang=lang)))
    assert TEXTS["prob_infinite"]["es"].format(k=1) not in _textos(plot_fs_histogram(
        summarize_fs([0.5, 2.0], model="planar", sampling="lhs", n=2, seed=1, variables=("x",))))


def test_all_infinite():
    r = summarize_fs([float("inf")] * 3, model="planar", sampling="lhs", n=3, seed=1, variables=("x",))
    assert r.n_valid == 3 and r.pof == 0
    for plot in FIGS:
        t = _textos(plot(r))
        assert "PoF = 0.0 %" in t and TEXTS["prob_infinite"]["es"].format(k=3) in t


@pytest.mark.parametrize("bins", [1, 3, 40])
def test_one_is_bin_edge_and_no_mixed_bars(res, bins):
    ax = plot_fs_histogram(res, bins=bins).axes[0]
    edges = [e for p in ax.patches for e in (p.get_x(), p.get_x() + p.get_width())]
    assert any(abs(e - 1.0) < 1e-12 for e in edges)
    for p in ax.patches:  # ninguna barra cruza FS = 1; las rayadas quedan a la izquierda
        assert p.get_x() + p.get_width() <= 1 + 1e-12 or p.get_x() >= 1 - 1e-12
        assert bool(p.get_hatch()) == (p.get_x() < 1 - 1e-12)
    assert round(sum(p.get_height() for p in ax.patches if p.get_hatch())) == res.n_failed


@pytest.mark.parametrize("plot", FIGS)
def test_no_identifier_leak(res, plot, tmp_path):
    fig = plot(res, title="Bloque 1")
    p = save_figure(fig, tmp_path / "f.svg")
    assert "ZZSENT" not in p.read_text(encoding="utf-8")
