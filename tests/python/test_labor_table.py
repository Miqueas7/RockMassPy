import pytest

import rockmasspy as rm

CAT = rm.SupportCatalog([
    rm.SupportType("I", 1),
    rm.SupportType("II", 2, shotcrete=rm.Shotcrete(50)),
    rm.SupportType("III", 3, bolt=rm.Bolt("split set", 2.1, 1.5), shotcrete=rm.Shotcrete(75, True)),
])


def rtab(support_iii="III"):
    return rm.RangeTable("RMR", "RMR89", [
        rm.RangeClass(0, 40, "poor", support_iii), rm.RangeClass(40, 60, "fair", "II"),
        rm.RangeClass(60, 100, "good", "I")])


def lab(labor="galería", span=None, table=None):
    return rm.LaborTable(labor, CAT, table or rtab(), span_m=span)


def ctab():
    return rm.CellTable(rm.GSI_CHARTS["GSI-Vallejo-Osinergmin2017"],
                        [rm.CellClass("F/R", "II", label="fr"), rm.CellClass("F/B", "ZZ")])


def test_classify_range():
    c = lab().classify(40)  # límite: la clase peor
    assert (c.label, c.support.code, c.base_edition, c.warnings) == ("poor", "III", "RMR89", ())


def test_classify_cells():
    c = lab(table=ctab()).classify(structure="f", condition="r")
    assert c.label == "fr" and c.support.code == "II" and c.base_edition == "GSI-Vallejo-Osinergmin2017"
    assert lab(table=ctab()).classify(structure="F", condition="B").label == "F/B"


def test_support_missing_gives_warning_not_error():
    c = lab(table=rtab("X")).classify(10)
    assert c.support is None and c.warnings == ("class poor has no support type in the catalog",)
    assert lab(table=ctab()).classify(structure="F", condition="B").support is None


def test_classify_wrong_arguments():
    with pytest.raises(ValueError):
        lab().classify()
    with pytest.raises(ValueError):
        lab().classify(50, structure="F", condition="R")
    with pytest.raises(ValueError):
        lab(table=ctab()).classify(50)
    with pytest.raises(ValueError):
        lab(table=ctab()).classify(structure="F")


def test_span_and_date_validation():
    for bad in [(0, 3), (4, 3), (float("nan"), 3)]:
        with pytest.raises(ValueError):
            lab(span=bad)
    with pytest.raises(ValueError):
        rm.LaborTable("x", CAT, rtab(), date="01/11/2026")
    rm.LaborTable("x", CAT, rtab(), date="2026-11-01")


def test_validate_collects_catalog_and_table():
    t = rm.LaborTable("x", rm.SupportCatalog([rm.SupportType("I", 2)]), rtab())
    kinds = {i.kind for i in t.validate()}
    assert {"order_gap", "unknown_support"} <= kinds


def test_select_table():
    a, b, c = lab("Galería", (2, 4)), lab("galería", (4.5, 6)), lab("rampa")
    assert rm.select_table([a, b, c], " GALERÍA ", 3) is a
    assert rm.select_table([a, b, c], "galería", 5) is b
    assert rm.select_table([a, c], "rampa", 99) is c
    with pytest.raises(ValueError, match="no table"):
        rm.select_table([a, b], "galería", 4.2)
    with pytest.raises(ValueError, match="more than one"):
        rm.select_table([a, lab("galería", (3, 5))], "galería", 3.5)


def test_classify_support_none_and_spaces():
    t = lab(table=rm.RangeTable("RMR", "RMR89", [rm.RangeClass(0, 50, "poor", None), rm.RangeClass(50, 100, "good", " II ")]))
    assert t.classify(10).support is None and t.classify(10).warnings == ("class poor has no support type in the catalog",)
    assert t.classify(70).support.code == "II" and t.classify(70).warnings == ()


def test_date_must_exist():
    for bad in ("2026-13-45", "2026-02-30", "20261101", "01/11/2026"):
        with pytest.raises(ValueError, match="date: expected yyyy-mm-dd"):
            rm.LaborTable("x", CAT, rtab(), date=bad)


def test_select_table_contiguous_spans_take_larger():
    a, b = lab("galería", (3, 4)), lab("galería", (4, 5))
    assert rm.select_table([a, b], "galería", 4.0) is b  # en el límite, la de luces mayores
    assert rm.select_table([b, a], "galería", 4.0) is b
    assert rm.select_table([a, b], "galería", 3.5) is a
    with pytest.raises(ValueError, match="more than one"):
        rm.select_table([lab("galería", (3, 5)), lab("galería", (4, 6))], "galería", 4.5)
    with pytest.raises(ValueError, match="more than one"):
        rm.select_table([a, lab("galería")], "galería", 4.0)  # sin luz cubre todo: es solape real


def test_select_table_ignores_accents():
    t = lab("Galería", (3, 4))
    assert rm.select_table([t], "galeria", 3.5) is t
    assert rm.select_table([lab("galeria", (3, 4))], " GALERÍA ", 3.5).labor_type == "galeria"
