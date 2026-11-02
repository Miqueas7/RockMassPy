import os
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
import rockmasspy as rm
from rockmasspy.batch import TramoResult
from rockmasspy.tramos import Tramo
from rockmasspy.viz import Style, plot_labor_profile, plot_plan_map
from rockmasspy.viz.save import save_figure

CAT = rm.SupportCatalog([rm.SupportType("I", 1), rm.SupportType("II", 2), rm.SupportType("III", 3)])
_F = [f for f in Tramo.__dataclass_fields__ if f not in ("id_tramo", "tipo_labor", "fila")]


def _res(i, labor="galeria", ini=0.0, fin=5.0, e=100.0, n=200.0, order=1, datum="WGS84-18S", ed="RMR89"):
    t = Tramo(id_tramo=f"SECRETO-{i}", tipo_labor=labor, fila=i + 2,
              **{f: None for f in _F if f not in ("progresiva_inicio_m", "progresiva_fin_m", "este_m", "norte_m", "datum")},
              progresiva_inicio_m=ini, progresiva_fin_m=fin, este_m=e, norte_m=n, datum=datum)
    if order is None:
        return TramoResult(tramo=t, labor_type=labor, base_edition=ed, warnings=("x",))
    s = CAT.ordered()[order - 1]
    return TramoResult(tramo=t, labor_type=labor, base_edition=ed, label=f"C{order}", support=s, support_order=order)


def _six():
    return [_res(i, labor="galeria" if i < 3 else "rampa", ini=i * 5.0, fin=i * 5.0 + 5, e=i * 10.0, n=i * 7.0,
                 order=i % 3 + 1) for i in range(6)]


def _patches(fig):
    from matplotlib.patches import Rectangle
    return [p for p in fig.axes[0].patches if isinstance(p, Rectangle)]


def _textos(fig):
    return [t.get_text() for t in fig.findobj(lambda a: hasattr(a, "get_text"))]


def test_perfil_seis_parches_y_filtro():
    assert len(_patches(plot_labor_profile(_six(), catalog=CAT))) == 6
    assert len(_patches(plot_labor_profile(_six(), labor_type="rampa", catalog=CAT))) == 3


def test_perfil_sin_clasificar_gris():
    r = _six() + [_res(9, order=None, ini=40, fin=45)]
    fig = plot_labor_profile(r, catalog=CAT)
    assert len(_patches(fig)) == 7
    assert "sin clasificar" in _textos(fig)
    assert plot_labor_profile(r, catalog=CAT, style=Style(lang="en")) and \
        "unclassified" in _textos(plot_labor_profile(r, catalog=CAT, style=Style(lang="en")))


def test_perfil_sin_progresivas_en_la_nota_y_pie():
    r = _six() + [_res(9, ini=None, fin=None)]
    fig = plot_labor_profile(r, catalog=CAT)
    assert len(_patches(fig)) == 6
    assert any("1 tramos sin progresivas" in t for t in _textos(fig))
    assert any("RMR89" in t for t in _textos(fig))


def test_perfil_color_sigue_el_rango_del_catalogo():
    fig = plot_labor_profile([_res(0, order=3)], catalog=CAT)
    assert _patches(fig)[0].get_facecolor()[:3] != _patches(plot_labor_profile([_res(0, order=1)], catalog=CAT))[0].get_facecolor()[:3]


def test_planta_seis_puntos_igual_aspecto_y_sin_ids():
    fig = plot_plan_map(_six(), catalog=CAT)
    assert len(fig.axes[0].collections[0].get_offsets()) == 6
    assert fig.axes[0].get_aspect() == 1.0
    assert not any("SECRETO" in t for t in _textos(fig))
    assert any("WGS84-18S" in t for t in _textos(fig))


def test_planta_datums_mixtos_y_omitidos():
    r = _six() + [_res(9, e=None, n=None), _res(10, datum="PSAD56")]
    t = _textos(plot_plan_map(r, catalog=CAT))
    assert "datums mixtos" in t
    assert any("1 tramos sin coordenadas" in x for x in t)


def test_perfil_sin_id():
    assert not any("SECRETO" in t for t in _textos(plot_labor_profile(_six(), catalog=CAT)))


def test_nada_dibujable_lanza():
    with pytest.raises(ValueError):
        plot_labor_profile([_res(0, ini=None, fin=None)])
    with pytest.raises(ValueError):
        plot_plan_map([_res(0, e=None, n=None)])
    with pytest.raises(ValueError):
        plot_labor_profile(_six(), labor_type="no existe")


def test_sin_catalogo_usa_el_maximo_orden():
    assert len(_patches(plot_labor_profile(_six()))) == 6


def test_muestras():
    d = os.environ.get("RMP_SAMPLES_DIR")
    if not d:
        pytest.skip("RMP_SAMPLES_DIR no definido")
    r = [_res(i, labor=("galeria" if i < 8 else "rampa"), ini=(i % 8) * 6.0, fin=(i % 8) * 6.0 + 6,
              e=1000 + i * 9.0 + (i % 3) * 4, n=5000 + i * 5.0 - (i % 2) * 6, order=[1, 2, 2, 3, 1, 1, 2, 3, 3, 2, 1, None][i % 12])
         for i in range(16)]
    save_figure(plot_labor_profile(r, catalog=CAT), Path(d) / "t3_perfil_es.png")
    save_figure(plot_plan_map(r, catalog=CAT), Path(d) / "t3_planta_es.png")
