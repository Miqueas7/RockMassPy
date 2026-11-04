import math

import numpy as np
import pytest
from hypothesis import given, settings, strategies as st

import rockmasspy as rm

NAN, INF = float("nan"), float("inf")
G = 9.80665


def make(acc, dt, ky, **kw):
    i = rm.NewmarkInput()
    i.acceleration_g, i.dt_s, i.ky = list(acc), dt, ky
    for k, v in kw.items():
        setattr(i, k, v)
    return i


def run(acc, dt, ky, **kw):
    return rm.newmark_rigid_block(make(acc, dt, ky, **kw))


def sample(f, dt, total):
    return [float(f(k * dt)) for k in range(int(round(total / dt)) + 1)]


def rect(A, t0):
    return lambda t: A if t <= t0 + 1e-9 else 0.0


def half_sine(A, tp):
    return lambda t: np.where(t <= tp, A * np.sin(np.pi * t / tp), 0.0)


def triangle(A, t_peak, tp):
    return lambda t: np.where(t <= t_peak, A * t / t_peak, np.where(t <= tp, A * (tp - t) / (tp - t_peak), 0.0))


def reference(f, ky, total, dt=1e-6):
    # Integración propia, misma mecánica, para un pulso único: arranca en a > ky, trapecio sobre la aceleración
    # relativa y se detiene en el primer v <= 0 (después el registro es cero y el bloque ya no arranca).
    t = np.arange(0.0, total, dt)
    r = (f(t) - ky) * G
    start = int(np.argmax(r > 0))
    r = r[start:]
    v = np.concatenate([[0.0], np.cumsum(0.5 * (r[1:] + r[:-1]) * dt)])
    stop = int(np.argmax(v[1:] <= 0)) + 1
    v = v[:stop]
    return float(np.sum(0.5 * (v[1:] + v[:-1]) * dt)), float(v.max())


def test_rectangular_pulse():
    # d = g t0² A (A - ky) / (2 ky): acelera (A - ky) g durante t0 y desacelera ky g hasta parar
    closed = G * 0.5**2 * 0.3 * (0.3 - 0.1) / (2 * 0.1)
    assert closed == pytest.approx(0.73550, abs=1e-5)
    r = run(sample(rect(0.3, 0.5), 1e-4, 2.0), 1e-4, 0.1)
    assert r.displacement_m == pytest.approx(closed, rel=0.005)
    assert r.max_velocity_m_s == pytest.approx(0.2 * G * 0.5, rel=0.005)
    assert r.time_of_max_s == pytest.approx(0.5, abs=2e-4)
    assert r.displacement_history_m[-1] == r.displacement_m
    assert r.warnings == [] and r.notes == []
    assert r.info.method_id == "Newmark-RigidBlock"
    assert r.info.verification == rm.Verification.Secondary
    assert "Newmark (1965)" in r.info.source
    assert run(sample(rect(0.3, 0.5), 1e-3, 2.0), 1e-3, 0.1).displacement_m == pytest.approx(closed, rel=0.01)


@pytest.mark.parametrize("f,ky", [(half_sine(0.4, 0.6), 0.15), (triangle(0.5, 0.2, 0.6), 0.1)])
def test_against_fine_reference(f, ky):
    d_ref, v_ref = reference(f, ky, 3.0)
    r = run(sample(f, 1e-3, 3.0), 1e-3, ky)
    assert r.displacement_m == pytest.approx(d_ref, rel=1e-3)
    assert r.max_velocity_m_s == pytest.approx(v_ref, rel=1e-3)
    assert r.warnings == []


def test_half_sine_time_of_max():
    # la velocidad relativa es máxima donde a vuelve a bajar a ky
    A, tp, ky = 0.4, 0.6, 0.15
    r = run(sample(half_sine(A, tp), 1e-3, 3.0), 1e-3, ky)
    assert r.time_of_max_s == pytest.approx(tp - tp / math.pi * math.asin(ky / A), abs=1e-3)


@pytest.mark.parametrize("ky", [0.3, 0.8])
def test_ky_at_or_above_peak(ky):
    r = run(sample(rect(0.3, 0.5), 1e-3, 1.0), 1e-3, ky)
    assert r.displacement_m == 0.0 and r.max_velocity_m_s == 0.0
    assert len(r.notes) == 1 and "does not slide" in r.notes[0]


def test_still_sliding_warns():
    r = run(sample(rect(0.3, 1.0), 1e-3, 1.0), 1e-3, 0.1)
    assert len(r.warnings) == 1 and "still sliding" in r.warnings[0]


def test_both_directions():
    # +0.3 g por 0.5 s y, tras una pausa, -0.5 g por 0.4 s: el invertido manda
    dt = 1e-4
    acc = sample(lambda t: 0.3 if t <= 0.5 + 1e-9 else (-0.5 if 2.5 - 1e-9 <= t <= 2.9 + 1e-9 else 0.0), dt, 6.0)
    orig = run(acc, dt, 0.1)
    both = run(acc, dt, 0.1, both_directions=True)
    assert orig.displacement_m == pytest.approx(G * 0.25 * 0.3 * 0.2 / 0.2, rel=0.005)
    assert both.displacement_m == pytest.approx(G * 0.16 * 0.5 * 0.4 / 0.2, rel=0.005)
    assert both.displacement_m == run([-a for a in acc], dt, 0.1).displacement_m
    assert len(both.notes) == 1 and "inverted record governs" in both.notes[0]
    back = run([-a for a in acc], dt, 0.1, both_directions=True)
    assert "original record governs" in back.notes[0]


@pytest.mark.parametrize("field,value,match", [
    ("ky", 0.0, r"'ky' must be strictly positive \(> 0\)"), ("ky", -0.1, "'ky'"), ("ky", NAN, "'ky'"),
    ("dt_s", 0.0, "'dt_s'"), ("dt_s", -1e-3, "'dt_s'"), ("dt_s", INF, "'dt_s'"),
    ("scale", 0.0, "'scale'"), ("scale", -2.0, "'scale'"), ("scale", NAN, "'scale'"),
    ("acceleration_g", [], "'acceleration_g'"), ("acceleration_g", [0.2], "'acceleration_g'"),
    ("acceleration_g", [0.1, NAN, 0.2], r"'acceleration_g\[1\]'"),
    ("acceleration_g", [0.1, 0.2, -INF], r"'acceleration_g\[2\]'"),
])
def test_raises(field, value, match):
    i = make([0.0, 0.3, 0.0], 0.01, 0.1)
    setattr(i, field, value)
    with pytest.raises(ValueError, match=match):
        rm.newmark_rigid_block(i)


def test_unset_inputs_raise():
    with pytest.raises(ValueError, match="'dt_s'"):
        rm.newmark_rigid_block(rm.NewmarkInput())
    i = rm.NewmarkInput()
    i.dt_s, i.acceleration_g = 0.01, [0.0, 0.3]
    with pytest.raises(ValueError, match="'ky'"):
        rm.newmark_rigid_block(i)


records = st.lists(st.floats(-1.0, 1.0, allow_nan=False), min_size=2, max_size=200)
dts = st.floats(1e-3, 0.05)
kys = st.floats(0.01, 1.0)


@settings(max_examples=200, deadline=None)
@given(records, dts, kys, st.floats(0.0, 0.5))
def test_properties(acc, dt, ky, dk):
    r = run(acc, dt, ky)
    h = r.displacement_history_m
    assert r.displacement_m >= 0.0 and r.max_velocity_m_s >= 0.0
    assert len(h) == len(acc) and h[0] == 0.0 and h[-1] == r.displacement_m
    assert all(b >= a for a, b in zip(h, h[1:]))
    assert run(acc, dt, ky + dk).displacement_m <= r.displacement_m * (1 + 1e-9) + 1e-12


@settings(max_examples=200, deadline=None)
@given(records, dts, kys, st.floats(0.1, 5.0))
def test_scale_equals_scaled_record(acc, dt, ky, k):
    a = run(acc, dt, ky, scale=k).displacement_m
    assert a == pytest.approx(run([k * x for x in acc], dt, ky).displacement_m, rel=1e-12, abs=1e-15)
