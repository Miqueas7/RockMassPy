import math

import pytest
from hypothesis import given, strategies as st

import rockmasspy as rm

NAN, INF = float("nan"), float("inf")


def test_ritchie():
    # Fig. 3.3 imprime 4.6 m (errata); la ec. 3.1 da 4.5
    assert rm.ritchie_berm_width(12).width_m == pytest.approx(6.9, abs=1e-12)
    assert rm.ritchie_berm_width(15).width_m == pytest.approx(7.5, abs=1e-12)
    assert rm.ritchie_berm_width(12).info.method_id == "Berm-ModifiedRitchie"
    assert rm.ritchie_berm_width(12).info.verification == rm.Verification.PrimaryLaterAuthors


@pytest.mark.parametrize("h,face,w", [(12, 65, 17.956), (12, 81, 21.651), (12, 39, 8.733),
                                      (24, 71, 38.839), (24, 81, 43.301), (24, 49, 26.240)])
def test_figure_38(h, face, w):
    assert rm.bench_width(h, 27, face) == pytest.approx(w, abs=1e-3)


def face_for(h, ir, w):
    # la biblioteca no expone la inversa en la cara: se resuelve aquí (publicados 41.4 y 34.7)
    return math.degrees(math.atan(1 / (1 / math.tan(math.radians(ir)) - w / h)))


def test_face_for_published_widths():
    assert face_for(12, 27, 10.0) == pytest.approx(41.53, abs=0.01)
    assert face_for(24, 27, 12.4) == pytest.approx(34.67, abs=0.01)


def test_interramp():
    assert rm.interramp_angle(12, 17.956, 65) == pytest.approx(27.0, abs=1e-3)
    assert rm.interramp_angle(15, 8, 70) == pytest.approx(48.098, abs=1e-3)


@given(st.floats(1, 50), st.floats(10, 80), st.floats(30, 89))
def test_inverse(h, ir, face):
    w = rm.bench_width(h, ir, face)
    if w >= 0:
        assert rm.interramp_angle(h, w, face) == pytest.approx(ir, abs=1e-6)


def test_reliability():
    r = rm.berm_reliability([5, 6.9, 7, 8], 6.9)
    assert (r.n, r.n_meeting, r.reliability) == (4, 2, 0.5)
    assert r.width_mean == pytest.approx(6.725) and r.width_min == 5 and r.width_max == 8
    assert rm.berm_reliability([6.9 + 1e-12], 6.9).n_meeting == 0
    assert rm.berm_reliability([6.9 + 1e-8], 6.9).n_meeting == 1
    assert rm.berm_reliability([5], 6.9).info.verification == rm.Verification.PrimaryLaterAuthors


@given(st.lists(st.floats(0, 30), min_size=1, max_size=20), st.floats(0, 30), st.floats(0, 10))
def test_reliability_monotone(ws, req, extra):
    assert rm.berm_reliability(ws, req + extra).reliability <= rm.berm_reliability(ws, req).reliability


@pytest.mark.parametrize("call", [
    lambda: rm.ritchie_berm_width(0), lambda: rm.ritchie_berm_width(NAN),
    lambda: rm.bench_width(0, 27, 65), lambda: rm.bench_width(12, 27, 0), lambda: rm.bench_width(12, 27, 95),
    lambda: rm.bench_width(12, 90, 65), lambda: rm.bench_width(12, NAN, 65), lambda: rm.bench_width(12, 27, INF),
    lambda: rm.interramp_angle(12, 8, 0), lambda: rm.interramp_angle(12, NAN, 65),
    lambda: rm.berm_reliability([], 6.9), lambda: rm.berm_reliability([5, NAN], 6.9),
    lambda: rm.berm_reliability([5], NAN), lambda: rm.bench_width(12, 0, 65),
    lambda: rm.interramp_angle(12, -1, 65), lambda: rm.ritchie_berm_width(INF), lambda: rm.bench_width(INF, 27, 65)])
def test_throws(call):
    with pytest.raises(ValueError):
        call()
