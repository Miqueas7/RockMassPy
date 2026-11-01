import pytest

import rockmasspy as rm


def test_mi_known_values():
    g = rm.mi_lookup("granite")
    assert (g.mi, g.plus_minus, g.estimate) == (32, 3, False)
    assert rm.mi_lookup("Arenisca").mi == 17 and rm.mi_lookup("sandstone").plus_minus == 4
    assert rm.mi_lookup(" claystone ").mi == 4
    assert rm.mi_lookup("conglomerate").estimate is True  # entre paréntesis en la tabla 3
    assert rm.mi_lookup("volcanic breccia").plus_minus == 5


def test_mr_known_values():
    assert (rm.mr_lookup("sandstone").lo, rm.mr_lookup("sandstone").hi) == (200, 350)
    assert (rm.mr_lookup("siltstone").lo, rm.mr_lookup("siltstone").hi) == (350, 400)
    assert (rm.mr_lookup("claystone").lo, rm.mr_lookup("claystone").hi) == (200, 300)
    assert rm.mr_lookup("greywacke").lo == rm.mr_lookup("greywacke").hi == 350
    assert rm.mr_lookup("gypsum").estimate is True


def test_aliases_cover_every_rock():
    assert set(rm.MI_ALIASES_ES.values()) >= set(rm.MI_TABLE) | set(rm.MR_TABLE)
    assert rm.mi_lookup("pórfido") is rm.mi_lookup("porfido")


def test_unknown_rock_suggests():
    with pytest.raises(KeyError, match="granite"):
        rm.mi_lookup("granit")
    with pytest.raises(KeyError, match="granite"):
        rm.mr_lookup("granit")


def test_table_issue():
    i = rm.TableIssue("gap", "msg")
    assert i.edition is None
