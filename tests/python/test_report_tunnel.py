import pytest

import rockmasspy.report as rp
from rockmasspy import _rockmasspy_core as rm
from rockmasspy.excavation import TunnelInput, analyze_tunnel
from rockmasspy.report.texts import REPORT_TEXTS
from rockmasspy.support_capacity import SupportCapacity

INP = TunnelInput(radius_m=6, p0_mpa=1.62, nu=0.3, criterion="HB", sigma_ci_mpa=7, gsi=15, mi=10)
SUP = SupportCapacity("B34", "bolt", psm_mpa=0.354, eps_sm=0.002)


@pytest.fixture
def res():
    return analyze_tunnel(INP, supports=[SUP], install_distance_m=3, ldp="CHERN1998")


def _capacity():
    s = rm.LiningSection()
    s.area_m2, s.inertia_m4, s.thickness_m, s.sigma_c_mpa, s.sigma_t_mpa = 0.12, 0.0004, 0.2, 40, -5
    f = rm.LiningForce()
    f.n_mn, f.m_mnm = 0.5, 0.05
    return s, [f]


def test_sections_figure_and_inputs(res):
    pytest.importorskip("matplotlib")
    rep = rp.build_tunnel_report([res], inputs=[INP], title="T", date="2026-11-14")
    assert [s.number for s in rep.sections] == ["1", "2", "3", "4", "5"]
    blocks = rep.sections[2].blocks
    assert any(isinstance(b, rp.Figure) and b.png for b in blocks)
    tables = [b for b in blocks if isinstance(b, rp.Table)]
    assert len(tables) == 2 and len(tables[1].rows) == 1  # entradas, resultados
    assert rep.sections[4].blocks[0].text == rp.DISCLAIMER["es"]


def test_capacity_diagram_added(res):
    pytest.importorskip("matplotlib")
    n = lambda rep: sum(isinstance(b, rp.Figure) for b in rep.sections[2].blocks)  # noqa: E731
    base = rp.build_tunnel_report([res], title="T")
    withcap = rp.build_tunnel_report([res], title="T", capacity=_capacity())
    assert n(withcap) == n(base) + 1


def test_english_and_no_untranslated_keys(res, tmp_path):
    rep = rp.build_tunnel_report([res], inputs=[INP], title="T", lang="en", figures=False)
    assert rep.sections[0].title == "Scope"
    html = rp.write_html(rep, tmp_path / "t.html").read_text(encoding="utf-8")
    assert '<html lang="en">' in html
    assert all(set(v) == {"es", "en"} for k, v in REPORT_TEXTS.items() if k.startswith("tn_"))


def test_warnings_listed_and_errors():
    w = analyze_tunnel(TunnelInput(**{**INP.__dict__, "k_ratio": 0.5}))
    rep = rp.build_tunnel_report([w], title="T", figures=False)
    assert rep.sections[3].blocks[0].rows[0][0].startswith("analytical GRC")
    with pytest.raises(ValueError):
        rp.build_tunnel_report([], title="T")
    with pytest.raises(ValueError):
        rp.build_tunnel_report([w], title="T", lang="fr")
