import os
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")

import rockmasspy as rm  # noqa: E402
from rockmasspy.viz import Style, plot_hb_envelopes, save_figure  # noqa: E402

SCI = 50.0


def _hb1():
    p = rm.hb_params(45, 10, 0, rm.HbEdition.HB2002)
    s3 = rm.hb_sigma3max(rm.hb_global_strength(SCI, p), 0.027, 100, rm.HbApplication.Tunnel)
    return p, s3, rm.hb_mohr_coulomb(SCI, p, s3)


def _texts(fig):
    return [t.get_text() for t in fig.texts]


def test_dos_ejes_y_curva_de_sigma_t_a_sigma3max():
    p, s3, _ = _hb1()
    fig = plot_hb_envelopes(SCI, p, sigma3max_mpa=s3)
    assert len(fig.axes) == 2
    x, y = fig.axes[0].lines[0].get_data()
    st = rm.hb_tensile(SCI, p)
    assert x[0] == pytest.approx(st) and x[-1] == pytest.approx(s3)
    assert y[0] == pytest.approx(rm.hb_sigma1(st, SCI, p))
    xn, yn = fig.axes[1].lines[0].get_data()
    assert (xn[0], yn[0]) == (pytest.approx(st), 0.0)


def test_con_mc_dos_lineas_por_eje_y_sin_mc_una():
    p, s3, mc = _hb1()
    fig = plot_hb_envelopes(SCI, p, sigma3max_mpa=s3, mc=mc)
    assert [len(a.lines) for a in fig.axes] == [2, 2]
    fig = plot_hb_envelopes(SCI, p, sigma3max_mpa=s3)
    assert [len(a.lines) for a in fig.axes] == [1, 1]


def test_recta_mc_cerca_de_la_curva_en_el_tramo_del_ajuste():
    import math

    p, s3, mc = _hb1()
    fig = plot_hb_envelopes(SCI, p, sigma3max_mpa=s3, mc=mc)
    x, y = fig.axes[0].lines[1].get_data()
    sin = math.sin(math.radians(mc.phi_deg))
    k = (1 + sin) / (1 - sin)
    assert y[-1] - y[0] == pytest.approx(k * (x[-1] - x[0]))
    # el ajuste es de mínimos cuadrados: en el punto medio de [0, s3] queda cerca de HB
    mid = s3 / 2
    scm = 2 * mc.cohesion_mpa * math.cos(math.radians(mc.phi_deg)) / (1 - sin)
    assert abs(scm + k * mid - rm.hb_sigma1(mid, SCI, p)) < 0.15 * rm.hb_sigma1(mid, SCI, p)


def test_puntos_de_ensayo_solo_en_el_eje_izquierdo():
    p, s3, _ = _hb1()
    fig = plot_hb_envelopes(SCI, p, sigma3max_mpa=s3, tests=[(1.0, 12.0), (2.0, 18.0)])
    offs = [tuple(o) for c in fig.axes[0].collections for o in c.get_offsets()]
    assert offs == [(1.0, 12.0), (2.0, 18.0)]
    assert not fig.axes[1].collections


def test_pie():
    p, s3, mc = _hb1()
    t = " ".join(_texts(plot_hb_envelopes(SCI, p, sigma3max_mpa=s3, mc=mc)))
    assert "HB-2002" in t and "σci 50 MPa" in t and "c′" in t and "φ′" in t
    assert "c′" not in " ".join(_texts(plot_hb_envelopes(SCI, p, sigma3max_mpa=s3)))


def test_idioma():
    p, s3, _ = _hb1()
    assert "Envolvente" in plot_hb_envelopes(SCI, p, sigma3max_mpa=s3).axes[0].get_title()
    assert "envelope" in plot_hb_envelopes(SCI, p, sigma3max_mpa=s3, style=Style(lang="en")).axes[0].get_title()


def test_sigma3max_no_mayor_que_sigma_t():
    p, _, _ = _hb1()
    st = rm.hb_tensile(SCI, p)
    for bad in (st, st - 1, 0.0 if st >= 0 else st):
        with pytest.raises(ValueError, match="sigma3max_mpa"):
            plot_hb_envelopes(SCI, p, sigma3max_mpa=bad)


def test_muestras():
    d = os.environ.get("RMP_SAMPLES_DIR")
    if not d:
        pytest.skip("RMP_SAMPLES_DIR no definido")
    p, s3, mc = _hb1()
    # sintéticos: sobre la curva ±7 %, dentro del rango [0, sigma3max] (en este túnel solo ~1.4 MPa)
    tests = [(f * s3, rm.hb_sigma1(f * s3, SCI, p) * m) for f, m in ((0.1, 1.07), (0.3, 0.94), (0.5, 1.05), (0.75, 0.96), (1.0, 1.04))]
    for lang in ("es", "en"):
        fig = plot_hb_envelopes(SCI, p, sigma3max_mpa=s3, mc=mc, tests=tests, style=Style(lang=lang))
        save_figure(fig, Path(d) / f"t4_envelopes_{lang}.png")
