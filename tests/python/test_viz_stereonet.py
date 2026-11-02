import math
import random
import subprocess
import sys

import pytest

pytest.importorskip("matplotlib")
import rockmasspy as rm
from rockmasspy.viz import Style, plot_stereonet
from rockmasspy.viz.save import save_figure
from rockmasspy.viz.stereonet import MODES

P = rm.PlaneOrientation
FACE = P(180, 60)


def _conjunto():
    rng = random.Random(20261102)  # el de la tarea 3: 40 planares, 30 flexurales, 30 de buzamiento 10
    planes = [P(rng.uniform(170, 190), rng.uniform(40, 55)) for _ in range(40)]
    planes += [P(rng.uniform(350, 370) % 360, rng.uniform(65, 80)) for _ in range(30)]
    planes += [P(rng.uniform(0, 360), 10) for _ in range(30)]
    return planes


def _lineas(planes):
    ki = rm.KinematicInput(FACE, 30, 30)
    out = []
    for i in range(0, len(planes), 9):
        for j in range(i + 1, min(i + 9, len(planes))):
            ln = rm.plane_intersection(planes[i], planes[j])
            if ln is not None:
                out.append(ln)
    return out


def _fig(mode=None, planes=None, lang="es", **kw):
    planes = _conjunto() if planes is None else planes
    extra = dict(face=FACE, friction_deg=30, lateral_limit_deg=30, mode=mode, intersections=_lineas(planes)) if mode else {}
    return plot_stereonet(planes, families=[("F1", P(180, 45)), ("F2", P(0, 72))], style=Style(lang=lang), **extra, **kw)


def _textos(fig):
    from matplotlib.text import Text

    fig.canvas.draw()
    return [t.get_text() for t in fig.findobj(Text)]


@pytest.mark.parametrize("proj", ["equal_area", "equal_angle"])
@pytest.mark.parametrize("mode", MODES)
def test_una_figura_por_modo(mode, proj):
    fig = _fig(mode, projection=proj)
    txt = "\n".join(_textos(fig))
    assert " de " in txt
    assert "F1" in txt and "N" in _textos(fig)


def _esperado(mode):
    planes = _conjunto()
    ki = rm.KinematicInput(FACE, 30, 30)
    if mode in ("planar", "flexural_toppling"):
        return sum(getattr(rm.check_plane(p, ki), mode) for p in planes), len(planes), None
    ch = [rm.check_intersection(x, ki) for x in _lineas(planes)]
    if mode == "direct_toppling":
        return sum(c.direct_toppling for c in ch), len(ch), sum(c.direct_toppling_oblique for c in ch)
    return sum(c.wedge_primary or c.wedge_secondary for c in ch), len(ch), None


METODO = {"planar": "Kinematic-PlanarSliding", "wedge": "Kinematic-WedgeSliding",
          "flexural_toppling": "Kinematic-FlexuralToppling-Goodman1980",
          "direct_toppling": "Kinematic-DirectToppling-HudsonHarrison1997"}


@pytest.mark.parametrize("lang, de", [("es", "de"), ("en", "of")])
@pytest.mark.parametrize("mode", MODES)
def test_linea_de_conteo_y_metodo(mode, lang, de):
    k, n, k2 = _esperado(mode)
    textos = _textos(_fig(mode, lang=lang))
    if k2 is None:
        cab = f"{k} {de} {n} ({100 * k / n:.0f} %) | "
    else:
        ob = {"es": "oblicuo", "en": "oblique"}[lang]
        di = {"es": "directo", "en": "direct"}[lang]
        cab = f"{di} {k} {de} {n} ({100 * k / n:.0f} %), {ob} {k2} {de} {n} ({100 * k2 / n:.0f} %) | "
    assert any(t.startswith(cab) for t in textos)
    assert any(METODO[mode] in t for t in textos)


def test_conteo_planar():
    assert any("40 de 100 (40 %)" in t for t in _textos(_fig("planar")))


def test_rotulos_de_familias_del_mismo_rumbo():
    fig = plot_stereonet([], families=[("F1", P(180, 45)), ("F2", P(0, 72))])
    ax = fig.axes[0]
    pos = {t.get_text(): t.get_position() for t in ax.texts if t.get_text() in ("F1", "F2")}
    assert pos["F1"][1] < 0 < pos["F2"][1]  # lados opuestos de la red
    for code, plane in (("F1", P(180, 45)), ("F2", P(0, 72))):
        pts = [(q.x, q.y) for q in rm.great_circle(plane, rm.Projection.EqualArea, 181)]
        assert min(math.hypot(pos[code][0] - x, pos[code][1] - y) for x, y in pts) < 0.05


def _colecciones(fig):
    from matplotlib.collections import PathCollection

    return [c for c in fig.axes[0].collections if isinstance(c, PathCollection)]


def test_marcadores_blancos_con_borde_negro():
    cols = _colecciones(_fig("wedge"))
    assert len(cols) >= 2  # polos e intersecciones
    for c in cols:
        assert (c.get_facecolors()[:, :3] == 1).all() and (c.get_edgecolors()[:, :3] == 0).all()


def test_igual_area_contra_igual_angulo():
    for proj, esperado in (("equal_area", 0.5412), ("equal_angle", 0.4142)):
        fig = plot_stereonet([P(180, 45)], projection=proj)
        (x, y), = _colecciones(fig)[0].get_offsets().tolist()
        assert (x, y) == pytest.approx((0, esperado), abs=1e-4)


def test_errores():
    with pytest.raises(ValueError, match="face"):
        plot_stereonet(mode="planar", friction_deg=30, lateral_limit_deg=30)
    with pytest.raises(ValueError, match="friction"):
        plot_stereonet(mode="planar", face=FACE, lateral_limit_deg=30)
    with pytest.raises(ValueError, match="lateral"):
        plot_stereonet(mode="planar", face=FACE, friction_deg=30)
    plot_stereonet(mode="wedge", face=FACE, friction_deg=30)  # la cuña no lleva límite lateral
    with pytest.raises(ValueError, match="projection"):
        plot_stereonet(projection="schmidt")
    with pytest.raises(ValueError, match="mode"):
        plot_stereonet(mode="volteo", face=FACE, friction_deg=30, lateral_limit_deg=30)


def test_sin_matplotlib():
    code = ("import sys; sys.modules['matplotlib'] = None; import rockmasspy as rm, rockmasspy.viz as v\n"
            "try:\n    v.plot_stereonet([rm.PlaneOrientation(180, 45)])\nexcept ImportError as e:\n    print(e)")
    r = subprocess.run([sys.executable, "-I", "-c", code], check=True, capture_output=True, text=True)
    assert "rockmasspy[viz]" in r.stdout


@pytest.mark.parametrize("lang, palabras", [("es", ("Red estereográfica", "Polos", "factibilidad, no probabilidad")),
                                            ("en", ("Stereonet", "Plane poles", "feasibility, not probability"))])
def test_idiomas(lang, palabras):
    txt = "\n".join(_textos(_fig("planar", lang=lang)))
    for p in palabras:
        assert p in txt
    assert "Kinematic-PlanarSliding" in txt


def test_solo_la_cara():
    fig = plot_stereonet(face=FACE)
    assert not _colecciones(fig)
    assert len(fig.axes) == 1  # sin barra de densidad


def test_densidad_con_escala():
    assert len(_fig().axes) == 2
    assert len(_fig(density=False).axes) == 1
    assert len(plot_stereonet([P(180, 45), P(181, 45)]).axes) == 1  # menos de 3 polos


@pytest.mark.parametrize("mode", [None, *MODES])
def test_sin_identificadores(tmp_path, mode):
    from rockmasspy.slopes import assess_slopes, load_families, load_slope_faces

    cab_t = ("id_talud,id_tramo,buz_cara_grados,dir_buz_cara_grados,friccion_grados,limite_lateral_grados,rmr_basico,"
             "excavacion,rqd_pct,jn,jr_a,ja_a,o_a,jwice,jr_b,ja_b,o_b,srf_a,srf_b,srf_c,codigo_mina,labor_codigo,este_m,observaciones")
    (tmp_path / "Taludes.csv").write_text(cab_t + "\nT-ZZSENT,R-ZZSENT,60,180,30,30,,,,,,,,,,,,,,,ZZSENT,ZZSENT,ZZSENT,ZZSENT\n",
                                          encoding="utf-8")
    jf = ["R-ZZSENT,F1,45,180,ZZSENT,ZZSENT,ZZSENT,ZZSENT"] * 2 + ["R-ZZSENT,F2,72,0,ZZSENT,ZZSENT,ZZSENT,ZZSENT"] * 2
    (tmp_path / "Familias.csv").write_text(
        "id_tramo,familia,buzamiento_grados,dir_buzamiento_grados,codigo_mina,labor_codigo,este_m,observaciones\n"
        + "\n".join(jf) + "\n", encoding="utf-8")
    (r,) = assess_slopes(load_slope_faces(tmp_path / "Taludes.csv"), load_families(tmp_path / "Familias.csv"))
    extra = dict(face=r.face, friction_deg=30, lateral_limit_deg=30, mode=mode) if mode else {}
    fig = plot_stereonet(r.planes, families=[(f.familia, f.mean_plane) for f in r.families], **extra)
    svg = save_figure(fig, tmp_path / "s.svg").read_text(encoding="utf-8")
    assert "ZZSENT" not in svg and "F1" in svg


def _oblicuo():
    face, planes = P(180, 80), [P(254, 81), P(233, 79)]
    ln = rm.plane_intersection(*planes)
    ci = rm.check_intersection(ln, rm.KinematicInput(face, 35, 30))
    assert ci.direct_toppling_oblique and not ci.direct_toppling
    return dict(face=face, friction_deg=35, lateral_limit_deg=30, mode="direct_toppling", intersections=[ln])


@pytest.mark.parametrize("lang, de, ob", [("es", "de", "oblicuo"), ("en", "of", "oblique")])
def test_volteo_oblicuo_solo(lang, de, ob):
    fig = plot_stereonet([P(254, 81), P(233, 79)], density=False, style=Style(lang=lang), **_oblicuo())
    textos = _textos(fig)
    assert any(f", {ob} 1 {de} 1 (100 %) | " in t and t.startswith(("directo 0", "direct 0")) for t in textos)
    assert any(t in ("Zona oblicua", "Oblique zone") for t in textos)
    assert any(pt.get_hatch() for pt in fig.axes[0].get_legend().get_patches())  # la trama de la zona 3


def test_volteo_directo_solo():
    fig = plot_stereonet([P(180, 45)], face=FACE, friction_deg=30, lateral_limit_deg=30, mode="direct_toppling",
                         intersections=[rm.LineOrientation(0, 60)])
    assert any(t.startswith("directo 1 de 1 (100 %), oblicuo 0 de 1 (0 %) | ") for t in _textos(fig))
