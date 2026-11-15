import re

import pytest

pytest.importorskip("scipy")

import rockmasspy.report as rp
from rockmasspy.predictive.surrogate import fit_surrogate, surrogate_pof, validate_surrogate
from rockmasspy.predictive.surrogate_bench import planar_runs
from rockmasspy.probabilistic import Distribution
from rockmasspy.report.texts import REPORT_TEXTS


@pytest.fixture(scope="module")
def parts():
    d = planar_runs(100, seed=3)
    s = fit_surrogate(d, kind="poly2")
    # una cola ancha para que haya muestras fuera del dominio
    pof = surrogate_pof(s, {"friction_deg": Distribution("normal", 5, 60, 32, 12)}, n=3000)
    return validate_surrogate(d, kind="poly2"), s, pof


def test_keys_have_both_languages():
    assert all(set(v) == {"es", "en"} for k, v in REPORT_TEXTS.items() if k.startswith("sg_"))


@pytest.mark.parametrize("lang", ["es", "en"])
def test_no_untranslated_texts(parts, tmp_path, lang):
    val, s, pof = parts
    rep = rp.build_surrogate_report(val, surrogate=s, pof=pof, title="T", lang=lang)
    html = rp.write_html(rep, tmp_path / f"{lang}.html").read_text(encoding="utf-8")
    assert not re.search(r"\bsg_\w+", html)
    # los avisos de la librería salen traducidos, no en inglés crudo (en es)
    assert lang == "en" or "sobrestiman" in html or "quadratic" not in html
    assert pof.n_out_of_domain > 0
    key = "Cota inferior" if lang == "es" else "Lower bound"
    assert key in html


def test_without_pof_and_surrogate(parts):
    val, _, _ = parts
    rep = rp.build_surrogate_report(val, title="T")
    assert [s.number for s in rep.sections] == ["1", "2", "3", "4", "5", "6"]
