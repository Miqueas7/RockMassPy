import pytest

import rockmasspy as rm


def cat():
    return rm.SupportCatalog([
        rm.SupportType("I", 1, "spot bolting"),
        rm.SupportType("II", 2, bolt=rm.Bolt("split set", 1.8, 1.5)),
        rm.SupportType("III", 3, bolt=rm.Bolt("helical", 2.1, 1.2), shotcrete=rm.Shotcrete(50, True)),
    ])


def test_catalog_order_and_get():
    c = cat()
    assert [t.code for t in c] == ["I", "II", "III"] and c.get("II").bolt.length_m == 1.8 and "III" in c
    assert len(c) == 3 and c.validate() == []


def test_get_unknown_lists_valid_codes():
    with pytest.raises(KeyError, match="II"):
        cat().get("X")


def test_duplicate_code_raises():
    with pytest.raises(ValueError, match="I"):
        rm.SupportCatalog([rm.SupportType("I", 1), rm.SupportType("I", 2)])


def test_order_issues_warn_not_raise():
    c = rm.SupportCatalog([rm.SupportType("A", 1), rm.SupportType("B", 3), rm.SupportType("C", 3, mesh="welded")])
    kinds = sorted(i.kind for i in c.validate())
    assert kinds == ["empty_type", "order_gap", "order_tie"]
    assert all(i.edition is None for i in c.validate())


def test_bad_elements_raise():
    with pytest.raises(ValueError):
        rm.Bolt("x", 0, 1.0)
    with pytest.raises(ValueError):
        rm.Shotcrete(float("nan"))
    with pytest.raises(ValueError):
        rm.SupportType("  ", 1)
    with pytest.raises(ValueError):
        rm.SupportType("A", 0)
    with pytest.raises(ValueError):
        rm.SupportType("A", 1, relative_cost=float("inf"))
    with pytest.raises(ValueError):
        rm.SupportType("A", 1, relative_cost=0)


def test_code_is_trimmed():
    assert rm.SupportType(" II ", 2).code == "II"


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_order_raises(bad):
    with pytest.raises(ValueError, match="order"):
        rm.SupportType("A", bad)
