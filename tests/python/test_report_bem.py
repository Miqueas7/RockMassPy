import re

import pytest

import rockmasspy.report as rp
from rockmasspy.bem import BemMaterial, analyze_bem, circle
from rockmasspy.report.texts import REPORT_TEXTS


@pytest.fixture(scope="module")
def res():
    return analyze_bem([circle(0, 0, 3, 64)], sigma1_mpa=30, sigma3_mpa=15, e_mpa=10000, nu=0.2,
                       material=BemMaterial("MC", c_mpa=5, phi_deg=30), grid=(-9, 9, -9, 9, 15, 15))


def test_sections_and_figures(res):
    pytest.importorskip("matplotlib")
    rep = rp.build_bem_report([res], title="T", date="2026-11-14", inputs=[{"sigma1": "30"}])
    assert [s.number for s in rep.sections] == ["1", "2", "3", "4", "5"]
    assert sum(isinstance(b, rp.Figure) and b.png is not None for b in rep.sections[2].blocks) == 2
    assert any(isinstance(b, rp.Paragraph) and "esfuerzo" in b.text for s in rep.sections for b in s.blocks)


def test_languages_without_untranslated_keys(res, tmp_path):
    assert all(set(v) == {"es", "en"} for k, v in REPORT_TEXTS.items() if k.startswith("bem_"))
    for lang in ("es", "en"):
        rep = rp.build_bem_report([res], title="T", lang=lang, figures=False)
        html = rp.write_html(rep, tmp_path / f"{lang}.html").read_text(encoding="utf-8")
        assert not re.search(r"\bbem_\w+", html)
    en = rp.build_bem_report([res], title="T", lang="en", figures=False)
    assert any("elastic analysis" in b.text.lower() for s in en.sections for b in s.blocks if isinstance(b, rp.Paragraph))


def test_errors(res):
    with pytest.raises(ValueError):
        rp.build_bem_report([], title="T")
    with pytest.raises(ValueError):
        rp.build_bem_report([res], title="T", lang="fr")


def test_mask_leaves_no_unpainted_triangle_outside_the_opening(tmp_path):
    pytest.importorskip("matplotlib")
    import numpy as np
    from rockmasspy.viz import plot_bem
    from rockmasspy.viz.bem import bem_triangulation

    r = analyze_bem([circle(0, 0, 3, 128)], sigma1_mpa=30, sigma3_mpa=15, e_mpa=10000, nu=0.2,
                    material=BemMaterial("MC", c_mpa=5, phi_deg=30), grid=(-9, 9, -9, 9, 20, 20))
    tri, _ = bem_triangulation(r, r.field.sf)
    tx, ty = np.array(r.field.x)[tri.triangles].mean(axis=1), np.array(r.field.y)[tri.triangles].mean(axis=1)
    outside = np.hypot(tx, ty) > 3.0 + 1e-9
    assert not tri.mask[outside & (np.hypot(tx, ty) < 6)].any()
    assert plot_bem(r, tmp_path / "f.png").stat().st_size > 0
