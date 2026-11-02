import pytest
from hypothesis import given, strategies as st

import rockmasspy as rm


def test_hoek_chamber_values():
    assert rm.max_unsupported_span(4.5, 1.6).value == pytest.approx(5.840298, abs=1e-6)
    assert rm.bolt_length_barton1980(15, 1.6).value == 3.40625
    p = rm.roof_pressure_grimstad_barton(4.5, 4, 3)
    assert p.value == pytest.approx(0.269203, abs=1e-6)
    assert p.unit == "" and any("unit not stated" in w for w in p.warnings)
    assert p.info.method_id == "Q-GrimstadBarton1993"
    assert rm.max_unsupported_span(1, 1).info.verification == rm.Verification.Secondary


def test_keyword_args_and_errors():
    assert rm.max_unsupported_span(q=1, esr=1).value == 2.0
    with pytest.raises(ValueError):
        rm.max_unsupported_span(float("nan"), 1)
    with pytest.raises(ValueError):
        rm.roof_pressure_grimstad_barton(1, 4, 0.4)


def test_methodinfo_constructible():
    assert rm.MethodInfo("X", rm.Verification.Primary, "src").source == "src"


q_st = st.floats(0.001, 1000, allow_nan=False)
esr_st = st.floats(0.5, 5, allow_nan=False)


@given(q_st, q_st, esr_st)
def test_span_grows_with_q(a, b, esr):
    lo, hi = sorted((a, b))
    assert rm.max_unsupported_span(lo, esr).value <= rm.max_unsupported_span(hi, esr).value


@given(q_st, esr_st, esr_st)
def test_span_grows_with_esr(q, a, b):
    lo, hi = sorted((a, b))
    assert rm.max_unsupported_span(q, lo).value <= rm.max_unsupported_span(q, hi).value


@given(q_st, q_st)
def test_pressure_falls_with_q(a, b):
    lo, hi = sorted((a, b))
    assert rm.roof_pressure_grimstad_barton(hi, 4, 3).value <= rm.roof_pressure_grimstad_barton(lo, 4, 3).value
