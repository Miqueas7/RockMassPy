import os
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")

from matplotlib.colors import to_hex  # noqa: E402

import rockmasspy as rm  # noqa: E402
from rockmasspy.cell_table import CellClass, CellTable  # noqa: E402
from rockmasspy.gsi_charts import GSI_CHARTS  # noqa: E402
from rockmasspy.labor_table import LaborTable  # noqa: E402
from rockmasspy.range_table import RangeClass, RangeTable  # noqa: E402
from rockmasspy.support import Bolt, Shotcrete, SupportCatalog, SupportType  # noqa: E402
from rockmasspy.viz import Style, plot_cartilla, save_figure, support_color  # noqa: E402

CHART = GSI_CHARTS["GSI-Vallejo-Osinergmin2017"]
CATALOG = SupportCatalog([
    SupportType("S0", 1),
    SupportType("S1", 2, bolt=Bolt("helicoidal", 2.1, 1.2)),
    SupportType("S2", 4, bolt=Bolt("helicoidal", 2.1, 1.2), shotcrete=Shotcrete(50, True), mesh="x"),
    SupportType("S3", 7, shotcrete=Shotcrete(100), arch="x"),
])


def _full_cells():
    codes = sorted(CHART.valid_cells)
    return [CellClass(c, ["S0", "S1", "S2", "S3"][i % 4]) for i, c in enumerate(codes)]


def _labor(table, **kw):
    return LaborTable("Galería", CATALOG, table, **kw)


def _texts(fig):
    return [t.get_text() for t in fig.findobj(lambda a: hasattr(a, "get_text"))]


def _ticks(fig):
    ax = fig.axes[0]
    return [t.get_text() for t in ax.get_xticklabels() + ax.get_yticklabels()]


def _grid_patches(fig):
    return [p for p in fig.axes[0].patches if p.get_gid()]


def test_celdas_vallejo_completa_25_parches():
    fig = plot_cartilla(_labor(CellTable(CHART, _full_cells())))
    patches = _grid_patches(fig)
    assert len(patches) == 25
    assert sum(1 for p in patches if p.get_gid().startswith("dashed:")) == 7


def test_color_de_celda_es_el_de_su_tipo():
    st = Style(size="cartilla")
    fig = plot_cartilla(_labor(CellTable(CHART, _full_cells())), style=st)
    cells = {c.cell: c.support for c in _full_cells()}
    expected = support_color([t.code for t in CATALOG].index(cells["F/R"]) + 1, 4, st)
    p = next(p for p in _grid_patches(fig) if p.get_gid() == "F/R")
    assert to_hex(p.get_facecolor()) == expected.lower()


def test_leyenda_una_entrada_por_tipo_y_pie():
    fig = plot_cartilla(_labor(CellTable(CHART, _full_cells())))
    legend = fig.axes[1]
    assert len(legend.patches) == 4
    txt = " ".join(_texts(fig))
    assert "Perno helicoidal 2.1 m @ 1.2 m; shotcrete 50 mm con fibra; malla" in txt
    assert "GSI-Vallejo-Osinergmin2017" in txt
    assert "la librería recomienda, el ingeniero decide" in txt


def test_rotulos_de_ejes_en_el_idioma_pedido():
    t = _labor(CellTable(CHART, _full_cells()))
    es = " ".join(_ticks(plot_cartilla(t)))
    assert "levemente fracturada" in es and "slightly" not in es
    en = " ".join(_ticks(plot_cartilla(t, style=Style(lang="en"))))
    assert "slightly fractured" in en and "levemente" not in en


def test_tipo_sin_elementos_y_mayuscula_inicial():
    txt = _texts(plot_cartilla(_labor(CellTable(CHART, _full_cells()))))
    assert "Sin sostenimiento" in txt and "Shotcrete 100 mm sin fibra; cimbra" in txt


def test_ingles():
    fig = plot_cartilla(_labor(CellTable(CHART, _full_cells()), span_m=(3, 4)), style=Style(lang="en"))
    txt = " ".join(_texts(fig))
    assert "Bolt helicoidal 2.1 m @ 1.2 m; shotcrete 50 mm with fibre" in txt
    assert "Span 3.0–4.0 m" in txt


def test_incompleta_y_tipo_desconocido_no_lanza():
    cells = [CellClass("F/R", "S1"), CellClass("F/B", "S2"), CellClass("LF/MB", "S0"), CellClass("MF/P", "ZZ")]
    fig = plot_cartilla(_labor(CellTable(CHART, cells)))
    assert len(_grid_patches(fig)) == 25
    # 14 sin definir + 1 con tipo desconocido (18 válidas - 3 definidas)
    assert sum(t.endswith("\nsin definir") for t in _texts(fig)) == 15


def test_rango_rmr89_cinco_barras():
    t = RangeTable("RMR", "RMR89", [RangeClass(0, 20, "V", "S3"), RangeClass(20, 40, "IV", "S3"),
                                    RangeClass(40, 60, "III", "S2"), RangeClass(60, 80, "II", "S1"),
                                    RangeClass(80, 100, "I", "S0")])
    fig = plot_cartilla(_labor(t), style=Style(size="A4"))
    assert len(fig.axes[0].patches) == 5
    assert fig.axes[0].get_xscale() == "linear"


def test_rango_q_eje_logaritmico():
    t = RangeTable("Q", "Q-NGI-2025", [RangeClass(0.001, 0.1, "malo", "S3"), RangeClass(0.1, 10, "medio", "S1"),
                                       RangeClass(10, 1000, "bueno", "S0")])
    fig = plot_cartilla(_labor(t))
    assert fig.axes[0].get_xscale() == "log"
    assert fig.axes[0].get_xlim() == (0.001, 1000.0)


@pytest.mark.parametrize("ext", ["png", "svg", "pdf"])
def test_tildes_y_enie_se_guardan(tmp_path, ext):
    fig = plot_cartilla(_labor(CellTable(CHART, _full_cells())), style=Style(size="cartilla", brand="Señal SAC"),
                        title="Tajeo norte")
    out = save_figure(fig, tmp_path / f"c.{ext}")
    assert out.stat().st_size > 1000
    if ext == "svg":
        # svg.fonttype=none deja el texto como nodo <text>, así la aserción es verificable
        import matplotlib
        with matplotlib.rc_context({"svg.fonttype": "none"}):
            save_figure(fig, tmp_path / "n.svg")
        svg = (tmp_path / "n.svg").read_text(encoding="utf-8")
        assert "Galería" in svg and "Señal SAC" in svg and "Tajeo norte" in svg


def test_muestras():
    d = os.environ.get("RMP_SAMPLES_DIR")
    if not d:
        pytest.skip("RMP_SAMPLES_DIR no definido")
    d = Path(d)
    full = CellTable(CHART, _full_cells())
    base = dict(span_m=(3.0, 4.0), author="Área de Geomecánica", date="2026-11-01")
    save_figure(plot_cartilla(_labor(full, **base), style=Style(size="cartilla", brand="Señal SAC"), title="Tajeo norte"),
                d / "t5_cartilla_celdas_es.png")
    rng = RangeTable("RMR", "RMR89", [RangeClass(0, 20, "V muy mala", "S3"), RangeClass(20, 40, "IV mala", "S3"),
                                      RangeClass(40, 60, "III regular", "S2"), RangeClass(60, 80, "II buena", "S1"),
                                      RangeClass(80, 100, "I muy buena", "S0")])
    save_figure(plot_cartilla(_labor(rng, **base), style=Style(size="A4")), d / "t5_cartilla_rango_es.png")
    save_figure(plot_cartilla(_labor(full, **base), style=Style(size="cartilla", lang="en")),
                d / "t5_cartilla_celdas_en.png")
    inc = CellTable(CHART, [CellClass("F/R", "S1"), CellClass("F/B", "S2"), CellClass("LF/MB", "S0"), CellClass("MF/P", "ZZ")])
    save_figure(plot_cartilla(_labor(inc, **base), style=Style(size="cartilla")), d / "t5_cartilla_incompleta_es.png")
    save_figure(plot_cartilla(_labor(full, **base), style=Style(size="cartilla", brand="Señal SAC"), title="Tajeo norte",
                              show_lines=True), d / "t6_cartilla_lineas_es.png")


def _rmr_lines(fig):
    return [ln for ln in fig.axes[0].lines if str(ln.get_gid()).startswith("rmr_line:")]


def test_lineas_rmr_y_fuente_en_el_pie():
    from rockmasspy.vallejo_lines import RMR_PRIME_LINES
    t = _labor(CellTable(CHART, _full_cells()))
    fig = plot_cartilla(t)
    assert [ln.get_gid() for ln in _rmr_lines(fig)] == [f"rmr_line:{ln.value:g}" for ln in RMR_PRIME_LINES]
    txt = _texts(fig)
    assert "90" in txt and "5" in txt  # rótulo en el extremo superior de cada línea
    assert any("digitalizado de Osinergmin (2017), Anexo A.17 (cartilla de Vallejo, 2011)" in s for s in txt)
    en = " ".join(_texts(plot_cartilla(t, style=Style(lang="en"))))
    assert "digitized from Osinergmin (2017), Annex A.17 (Vallejo chart, 2011)" in en


def test_sin_lineas_no_dibuja_ni_cita():
    fig = plot_cartilla(_labor(CellTable(CHART, _full_cells())), show_lines=False)
    assert _rmr_lines(fig) == []
    assert not any("Anexo A.17" in s for s in _texts(fig))


def test_otra_cartilla_nunca_lleva_lineas():
    from dataclasses import replace
    other = replace(CHART, chart_id="GSI-propia")
    fig = plot_cartilla(_labor(CellTable(other, [CellClass("F/R", "S1")])))
    assert _rmr_lines(fig) == []
    assert not any("Anexo A.17" in s for s in _texts(fig))


def test_texto_de_fuente_igual_a_la_constante():
    from rockmasspy.vallejo_lines import VALLEJO_LINES_SOURCE
    from rockmasspy.viz import text
    assert text("lines_source", "en") == VALLEJO_LINES_SOURCE
