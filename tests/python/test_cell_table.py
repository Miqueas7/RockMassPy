import pytest

import rockmasspy as rm

V = "GSI-Vallejo-Osinergmin2017"


def test_vallejo_chart_cells():
    ch = rm.GSI_CHARTS[V]
    assert len(ch.valid_cells) == 18 and "LF/MP" not in ch.valid_cells and "T/P" in ch.valid_cells
    assert ch.verification == "secondary" and ch.chart_id == V


def test_normalize_cell():
    assert rm.normalize_cell(" f / r ") == "F/R" == rm.normalize_cell("F/R ")
    with pytest.raises(ValueError):
        rm.normalize_cell("FR")


def full_table(support_for):
    ch = rm.GSI_CHARTS[V]
    return rm.CellTable(ch, [rm.CellClass(c, support_for(c)) for c in sorted(ch.valid_cells)])


def test_lookup_and_invalid():
    t = full_table(lambda c: "II")
    assert t.lookup("f", "r").support == "II" and t.base_edition == V
    with pytest.raises(ValueError, match="T/R"):
        t.lookup("T", "R")
    with pytest.raises(ValueError, match="LF"):
        rm.CellTable(rm.GSI_CHARTS[V], [rm.CellClass("XX/R")])
    with pytest.raises(ValueError, match="MB"):
        rm.CellTable(rm.GSI_CHARTS[V], [rm.CellClass("LF/ZZ")])
    with pytest.raises(ValueError, match="twice|duplicate"):
        rm.CellTable(rm.GSI_CHARTS[V], [rm.CellClass("F/R"), rm.CellClass("f / r")])
    partial = rm.CellTable(rm.GSI_CHARTS[V], [rm.CellClass("F/R")])
    with pytest.raises(ValueError, match="not defined"):
        partial.lookup("LF", "B")


def test_cellclass_checks():
    assert rm.CellClass("f/r", "  ").cell == "F/R" and rm.CellClass("F/R", "  ").support is None
    with pytest.raises(ValueError):
        rm.CellClass("F/R", gsi_range=(50, 40))
    with pytest.raises(ValueError):
        rm.CellClass("F/R", gsi_range=(-1, 40))


def test_validate_missing_invalid_and_monotonic():
    ch = rm.GSI_CHARTS[V]
    t = rm.CellTable(ch, [rm.CellClass("F/R", "III"), rm.CellClass("F/P", "I"), rm.CellClass("T/R", "V")])
    c = rm.SupportCatalog([rm.SupportType(k, n, mesh="m") for n, k in enumerate(["I", "II", "III", "IV", "V"], 1)])
    kinds = [i.kind for i in t.validate(c)]
    assert kinds.count("missing_cell") == 16 and "invalid_cell" in kinds and "not_monotonic" in kinds
    assert kinds.count("not_monotonic") == 1
    assert all(i.edition == V for i in t.validate(c))


def test_validate_no_and_unknown_support():
    ch = rm.GSI_CHARTS[V]
    t = rm.CellTable(ch, [rm.CellClass("F/R"), rm.CellClass("F/P", "ZZ")])
    c = rm.SupportCatalog([rm.SupportType("I", 1, mesh="m")])
    kinds = [i.kind for i in t.validate(c)]
    assert "no_support" in kinds and "unknown_support" in kinds and "not_monotonic" not in kinds
