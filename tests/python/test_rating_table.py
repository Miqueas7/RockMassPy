import math

import pytest
from hypothesis import given, settings, strategies as st

import rockmasspy as rm

BASE = dict(ucs_mpa=120, rqd_pct=80, spacing_m=0.5, persistence_m=2, aperture_mm=0.5, roughness="Rough",
            infilling="None", weathering="Slightly", water="Dry")


def test_default_reproduces_core_rmr89():                         # paridad con el núcleo
    @settings(deadline=None, max_examples=300)
    @given(st.floats(0, 400), st.floats(0, 100), st.floats(0.001, 5), st.floats(0, 30), st.floats(0, 10),
           st.sampled_from(["VeryRough", "Rough", "SlightlyRough", "Smooth", "Slickensided"]),
           st.sampled_from(["None", "HardUnder5mm", "HardOver5mm", "SoftUnder5mm", "SoftOver5mm"]),
           st.sampled_from(["Unweathered", "Slightly", "Moderately", "Highly", "Decomposed"]),
           st.sampled_from(["Dry", "Damp", "Wet", "Dripping", "Flowing"]))
    def check(ucs, rqd, sp, pers, ap, ro, inf, we, wa):
        inp = rm.Rmr89Input()
        inp.ucs_mpa, inp.rqd_pct, inp.spacing_m = ucs, rqd, sp
        inp.joint_condition = rm.JointCondition89(
            pers, ap, getattr(rm.Roughness, ro), getattr(rm.Infilling, "None_" if inf == "None" else inf),
            getattr(rm.Weathering, we))
        inp.water = getattr(rm.Water, wa)
        inp.orientation = rm.OrientationClass.Fair
        vals = dict(ucs_mpa=ucs, rqd_pct=rqd, spacing_m=sp, persistence_m=pers, aperture_mm=ap, roughness=ro,
                    infilling=inf, weathering=we, water=wa)
        assert rm.RatingTable.rmr89_default().rate(vals, "Fair").total == rm.rmr89(inp).rmr
    check()


def test_boundaries_and_point_bin():
    t = rm.RatingTable.rmr89_default()
    pts = lambda **kw: t.rate({**BASE, **kw}).points
    assert pts(ucs_mpa=100)["ucs_mpa"] == 7 and pts(aperture_mm=0)["aperture_mm"] == 6 and pts(aperture_mm=0.1)["aperture_mm"] == 4


def test_custom_weights_warn():
    t = rm.RatingTable("RMR89", [rm.NumericParam("ucs_mpa", "MPa", (rm.RatingBin(0, 100, 5), rm.RatingBin(100, math.inf, 25)), "higher")])
    kinds = [i.kind for i in t.validate()]
    assert "max_points" in kinds and all(i.edition == "RMR89" for i in t.validate())


def test_default_validates_clean():
    assert rm.RatingTable.rmr89_default().validate() == []


def test_gap_and_monotonic():
    t = rm.RatingTable("X", [rm.NumericParam("a", "u", (rm.RatingBin(0, 1, 5), rm.RatingBin(2, math.inf, 1)), "higher")])
    assert {i.kind for i in t.validate()} == {"gap", "not_monotonic"}


def test_missing_value_raises():
    with pytest.raises(ValueError, match="water"): rm.RatingTable.rmr89_default().rate({k: v for k, v in BASE.items() if k != "water"})


def test_rate_errors():
    t = rm.RatingTable.rmr89_default()
    for bad, match in [(dict(ucs_mpa=-1), "outside every bin"), (dict(ucs_mpa=float("nan")), "ucs_mpa"),
                       (dict(ucs_mpa="x"), "ucs_mpa"), (dict(water="Soaked"), "Dry"), (dict(extra=1), "unknown parameter 'extra'")]:
        with pytest.raises(ValueError, match=match): t.rate({**BASE, **bad})
    with pytest.raises(ValueError, match="Fair"): t.rate(BASE, "Nope")


def test_adjustment_warning_and_duplicates():
    t = rm.RatingTable.rmr89_default()
    r = t.rate(BASE); assert r.adjustment == 0 and r.warnings == ["no adjustment applied: total is the basic rating"]
    assert t.rate(BASE, "Fair").warnings == []
    p = rm.CategoricalParam("w", {"a": 1})
    assert rm.RatingTable("X", [p]).rate({"w": "a"}).warnings == []
    with pytest.raises(ValueError, match="duplicate"): rm.RatingTable("X", [p, p])


def _core_rmr(vals, orientation):
    inp = rm.Rmr89Input()
    inp.ucs_mpa, inp.rqd_pct, inp.spacing_m = vals["ucs_mpa"], vals["rqd_pct"], vals["spacing_m"]
    inp.joint_condition = rm.JointCondition89(
        vals["persistence_m"], vals["aperture_mm"], getattr(rm.Roughness, vals["roughness"]),
        getattr(rm.Infilling, "None_" if vals["infilling"] == "None" else vals["infilling"]),
        getattr(rm.Weathering, vals["weathering"]))
    inp.water = getattr(rm.Water, vals["water"])
    inp.orientation = getattr(rm.OrientationClass, orientation)
    return rm.rmr89(inp).rmr


BOUNDARIES = {"ucs_mpa": [0, 1, 5, 25, 50, 100, 250], "rqd_pct": [0, 25, 50, 75, 90, 100],
              "spacing_m": [0.06, 0.2, 0.6, 2], "persistence_m": [0, 1, 3, 10, 20], "aperture_mm": [0, 0.1, 1, 5]}


@pytest.mark.parametrize("name,value", [(n, v) for n, vs in BOUNDARIES.items() for v in vs])
def test_boundary_parity_with_core(name, value):                  # el límite es donde tabla y núcleo podrían divergir
    vals = {**BASE, name: value}
    assert rm.RatingTable.rmr89_default().rate(vals, "Fair").total == _core_rmr(vals, "Fair")


@pytest.mark.parametrize("orientation", ["VeryFavourable", "Favourable", "Fair", "Unfavourable", "VeryUnfavourable"])
def test_orientation_adjustment_parity_with_core(orientation):
    assert rm.RatingTable.rmr89_default().rate(BASE, orientation).total == _core_rmr(BASE, orientation)
