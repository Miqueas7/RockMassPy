import pytest

import rockmasspy as rm


def rmr_table():
    return rm.RangeTable("RMR", "RMR89", [rm.RangeClass(0, 20, "V", "V"), rm.RangeClass(20, 40, "IV", "IV"),
        rm.RangeClass(40, 60, "III", "III"), rm.RangeClass(60, 80, "II", "II"), rm.RangeClass(80, 100, "I", "I")])


def test_boundary_takes_worse_class():                            # Foco 2
    t = rmr_table(); assert t.lookup(40).label == "IV" and t.lookup(40.01).label == "III" and t.lookup(100).label == "I"


def test_lookup_errors():
    with pytest.raises(ValueError): rmr_table().lookup(float("nan"))
    with pytest.raises(ValueError, match="outside every class"):
        rm.RangeTable("RMR", "RMR89", [rm.RangeClass(20, 100, "x")]).lookup(10)


def test_validate_gap_overlap_and_edition():
    t = rm.RangeTable("RMR", "RMR89", [rm.RangeClass(0, 30, "B", "II"), rm.RangeClass(25, 70, "A", "I")])
    kinds = [i.kind for i in t.validate()]
    assert "gap" in kinds and "overlap" in kinds and kinds.count("edition_boundary") == 4
    assert all(i.edition == "RMR89" for i in t.validate())
    gap = next(i for i in t.validate() if i.kind == "gap")
    assert "RMR89" in gap.message and "70" in gap.message and "100" in gap.message


def test_clean_table_has_no_issues_without_catalog():
    assert rmr_table().validate() == []


def test_no_support():
    t = rm.RangeTable("GSI", "GSI-2013", [rm.RangeClass(0, 100, "all", "  ")])
    assert [i.kind for i in t.validate()] == ["no_support"]


def test_support_checks_with_catalog():                           # Foco 5
    c = rm.SupportCatalog([rm.SupportType(k, n, mesh="m") for n, k in enumerate(["I", "II", "III", "IV"], 1)])
    t = rmr_table()                                               # usa "V", que no está en el catálogo
    kinds = [i.kind for i in t.validate(c)]
    assert kinds.count("unknown_support") == 1
    bad = rm.RangeTable("Q", "Q-NGI-2025", [rm.RangeClass(0.001, 1, "poor", "I"), rm.RangeClass(1, 1000, "good", "IV")])
    assert "not_monotonic" in [i.kind for i in bad.validate(c)]
    assert "not_monotonic" not in kinds


def test_unknown_edition_lists_valid():
    with pytest.raises(ValueError, match="RMR89"): rm.RangeTable("RMR", "RMR2000", [rm.RangeClass(0, 100, "x")])
    with pytest.raises(ValueError, match="GSI"): rm.RangeTable("Foo", "RMR89", [rm.RangeClass(0, 100, "x")])
    with pytest.raises(ValueError): rm.RangeTable("RMR", "RMR89", [])


def test_range_class_validation():
    with pytest.raises(ValueError): rm.RangeClass(5, 5, "x")
    with pytest.raises(ValueError): rm.RangeClass(0, float("inf"), "x")
    assert rm.RangeClass(0, 1, "x", " A ").support == "A"
    t = rmr_table()
    assert (t.method, t.base_edition, len(t.classes)) == ("RMR", "RMR89", 5)


def test_label_required_and_support_as_text():
    for bad in ("", "  "):
        with pytest.raises(ValueError, match="label"):
            rm.RangeClass(0, 20, bad)
    c = rm.RangeClass(0, 20, " V ", 3)
    assert (c.label, c.support) == ("V", "3")
    assert rm.RangeClass(0, 20, "V", " ").support is None
    assert rm.CellClass("F/R", 3, label=None) == rm.CellClass("F/R", "3")


def _two(method, edition, edge, lo, hi):
    return rm.RangeTable(method, edition, [rm.RangeClass(lo, edge, "IV", "I"), rm.RangeClass(edge, hi, "III", "I")])


def _near_cl(t, v):
    return rm.LaborTable("g", rm.SupportCatalog([rm.SupportType("I", 1)]), t).classify(v)


def test_near_boundary_points():
    t = _two("RMR", "RMR89", 40, 0, 100)
    for v in (37, 43, 40):
        assert t.near_boundary(v) == ("IV", "III")
        assert "near the boundary between classes IV and III" in _near_cl(t, v).warnings
    for v in (36.9, 43.1):
        assert t.near_boundary(v) is None and _near_cl(t, v).warnings == ()
    assert _near_cl(t, 40).label == "IV"


def test_near_boundary_q_factor():
    t = _two("Q", "Q-NGI-2025", 4, 0.001, 1000)
    assert t.near_boundary(3.2) and t.near_boundary(5.0)
    assert t.near_boundary(3.1) is None and t.near_boundary(5.1) is None


def test_near_boundary_gap_is_not_a_boundary():
    t = rm.RangeTable("RMR", "RMR89", [rm.RangeClass(0, 38, "IV", "I"), rm.RangeClass(42, 100, "III", "I")])
    assert t.near_boundary(40) is None and t.near_boundary(38) is None


def test_near_boundary_q_edge_at_zero_is_skipped():
    t = rm.RangeTable("Q", "Q-NGI-2025", [rm.RangeClass(-5, 0, "x"), rm.RangeClass(0, 10, "y"), rm.RangeClass(10, 1000, "z")])
    assert t.near_boundary(0.05) is None
