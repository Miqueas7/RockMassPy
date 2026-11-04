import io

import pytest

pytest.importorskip("matplotlib")
from matplotlib.collections import PathCollection
from matplotlib.text import Text

import rockmasspy as rm
from rockmasspy.viz import Style, plot_le_section, plot_newmark
from rockmasspy.viz.style import TEXTS

import test_limit_equilibrium as tl


# ACADS 1(c), Slide problema 3: tres estratos con los contactos de la figura 3.1 (como test_slip_search.cpp)
def acads1c_data():
    s = "S1C-ZZSENT"
    return {"Geometria": tl.G(s, "superficie", [(20, 25), (30, 25), (50, 35), (70, 35)])
            + tl.G(s, "C1-ZZSENT", [(20, 25), (30, 25), (40, 27), (50, 29), (54, 31), (70, 31)])
            + tl.G(s, "C2-ZZSENT", [(20, 25), (30, 25), (40, 27), (52, 24), (70, 24)]),
            "Estratos": [tl.L(s, 1, "MA-ZZSENT", "C1-ZZSENT"), tl.L(s, 2, "MB-ZZSENT", "C2-ZZSENT"),
                         tl.L(s, 3, "MC-ZZSENT")],
            "Materiales_LE": [tl.mat(material=m, modelo="mohr_coulomb", peso_unitario_kn_m3=19.5, cohesion_kpa=c,
                                     friccion_grados=f)
                              for m, c, f in (("MA-ZZSENT", 0, 38), ("MB-ZZSENT", 5.3, 23), ("MC-ZZSENT", 7.2, 20))],
            "Analisis_LE": [tl.ana(id_analisis="A1C-ZZSENT", id_seccion=s, metodos="bishop;spencer;gle",
                                   superficie="circular", malla_x_min=22.8, malla_x_max=43.7, malla_y_min=42.3,
                                   malla_y_max=62.6, base_modelo_m=20)]}


@pytest.fixture(scope="module")
def casos(tmp_path_factory):
    c1, = rm.assess_le(tl.hojas(tmp_path_factory.mktemp("v1c"), acads1c_data()))
    b, = rm.assess_le(tl.hojas(tmp_path_factory.mktemp("v3b"), tl.merge(tl.acads3b_data(registro="R-ZZSENT", escala_registro=1.5),
                                             {"Sismos": tl.seno()})))
    return c1, b


def _textos(fig):
    fig.canvas.draw()
    return [t.get_text() for t in fig.findobj(Text) if t.get_text()]


def _svg(fig):
    buf = io.StringIO()
    fig.savefig(buf, format="svg")
    return buf.getvalue()


@pytest.mark.parametrize("lang", ["es", "en"])
def test_textos_de_texts_y_estratos_por_orden(casos, lang):
    c1, _ = casos
    t = " ".join(_textos(plot_le_section(c1, style=Style(lang=lang))))
    for k in ("le_section_title", "le_x_axis", "le_y_axis", "le_ground", "le_critical", "le_centre",
              "le_method_Bishop", "le_method_Spencer", "le_method_MorgensternPrice"):
        assert TEXTS[k][lang] in t, k
    for n in (1, 2, 3):
        assert TEXTS["le_layer"][lang].format(n=n) in t
    assert TEXTS["le_top"][lang].format(n=10) in t
    other = "en" if lang == "es" else "es"
    for k in ("le_section_title", "le_layer", "le_critical"):
        assert TEXTS[k][other].format(n=1) not in t
    for x in c1.results:  # el FS sale del resultado, uno por método
        assert f"FS = {x.factor_of_safety:.3f}" in t
    pie = [x for x in _textos(plot_le_section(c1)) if "Bishop-Simplified" in x][0]
    assert all(m.method_id in pie for m in c1.methods)


def test_diez_mejores_en_gris_y_centro_blanco(casos):
    c1, _ = casos
    ax = plot_le_section(c1).axes[0]
    grises = [ln for ln in ax.get_lines() if ln.get_color() == "#8C8C8C"]
    assert len(c1.search.top) == 10 and len(grises) == 10
    (centro,) = [c for c in ax.collections if isinstance(c, PathCollection)]
    assert tuple(centro.get_facecolor()[0]) == (1, 1, 1, 1) and tuple(centro.get_edgecolor()[0][:3]) == (0, 0, 0)
    c = c1.surface.circle
    assert tuple(centro.get_offsets()[0]) == pytest.approx((c.xc, c.yc))
    assert ax.get_ylim()[1] > c.yc  # el centro se ve


def test_superficie_dada_sin_centro_ni_grises_y_con_ky(casos):
    _, b = casos
    fig = plot_le_section(b, style=Style(lang="en"))
    t = _textos(fig)
    assert TEXTS["le_given"]["en"] in t and TEXTS["le_centre"]["en"] not in t
    assert not [c for c in fig.axes[0].collections if isinstance(c, PathCollection)]
    assert any(f"ky = {b.yield_.ky:.3f}" in x for x in t)


def test_ningun_id_en_el_svg(casos):
    c1, b = casos
    figs = [plot_le_section(c1), plot_le_section(b, style=Style(lang="en")),
            plot_newmark(b.newmark, b.record, b.yield_.ky)]
    for fig in figs:
        assert "ZZSENT" not in _svg(fig)


def test_sin_superficie_valida(casos):
    c1, _ = casos
    from dataclasses import replace

    r = replace(c1, surface=None, results=(c1.search.best,))
    assert TEXTS["le_no_surface"]["es"] in _textos(plot_le_section(r))


def test_sin_seccion_lanza(casos):
    from dataclasses import replace

    with pytest.raises(ValueError, match="section"):
        plot_le_section(replace(casos[0], section=None))


@pytest.mark.parametrize("lang", ["es", "en"])
def test_newmark(casos, lang):
    _, b = casos
    fig = plot_newmark(b.newmark, b.record, b.yield_.ky, style=Style(lang=lang))
    t = _textos(fig)
    for k in ("newmark_title", "newmark_time", "newmark_acc", "newmark_disp", "newmark_record"):
        assert TEXTS[k][lang] in t, k
    assert TEXTS["newmark_total"][lang].format(d=b.newmark.displacement_m) in t
    assert f"ky = {b.yield_.ky:.3f} g" in t and "Newmark-RigidBlock" in t
    ky_lines = [ln for ln in fig.axes[0].get_lines() if ln.get_linestyle() == "--"]
    assert sorted(ln.get_ydata()[0] for ln in ky_lines) == pytest.approx([-b.yield_.ky, b.yield_.ky])  # dos sentidos
    assert max(fig.axes[0].get_lines()[0].get_ydata()) == pytest.approx(0.45, abs=1e-9)  # registro escalado × 1.5


def test_newmark_lanza(casos):
    _, b = casos
    with pytest.raises(ValueError, match="ky"):
        plot_newmark(b.newmark, b.record, 0.0)
    with pytest.raises(ValueError, match="lengths"):
        plot_newmark(b.newmark, rm.Accelerogram(0.01, (0.0, 0.1)), b.yield_.ky)


def test_textos_en_los_dos_idiomas():
    for k, v in TEXTS.items():
        if k.startswith(("le_", "newmark_")):
            assert set(v) == {"es", "en"} and all(v.values()), k
