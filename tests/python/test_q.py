import pytest

import rockmasspy as rm


def test_hoek_example_via_python():
    assert abs(rm.q_value(rm.QInput(90, 4, 3, 1, 1, 15)).q - 4.5) < 5e-3


def test_default_constructor_and_fields():
    q = rm.QInput()
    q.rqd_pct = 90
    assert rm.q_value(q).q_base == 90.0


def test_wall_and_de_via_python():
    assert rm.wall_q(10, 5, 10, False) == 25
    assert rm.wall_q(0.5, 5, 10, False, rm.QEdition.NGI2015) == 1.25
    assert rm.equivalent_dimension(15, 1.6, 4.5, "C").de_m == pytest.approx(9.375)
    with pytest.raises(ValueError):
        rm.equivalent_dimension(15, 1.6, 4.5, "Z")


def test_lookup_2025():
    assert rm.q_lookup("Jr", "A") == (4.0, 4.0)
    assert rm.q_lookup("SRF", "K") == (50.0, 200.0)
    assert rm.q_lookup("Jn", "J", "Q-NGI-2015") == (20.0, 20.0)
    assert rm.q_lookup("Ja", "P") == (13.0, 20.0)


def test_lookup_unknown_letter_lists_valid():
    with pytest.raises(KeyError, match="A"):
        rm.q_lookup("Jw", "Z")
    with pytest.raises(KeyError, match="Jw"):
        rm.q_lookup("Xx", "A")
    with pytest.raises(KeyError, match="Q-NGI-2025"):
        rm.q_lookup("Jw", "A", "Q-1974")


def test_srf_values_equal_across_editions():
    a, b = rm.Q_TABLES["Q-NGI-2025"]["SRF"], rm.Q_TABLES["Q-NGI-2015"]["SRF"]
    assert a.keys() == b.keys()
    for letter in a:
        assert a[letter][:2] == b[letter][:2], letter


def test_srf_category_counts():
    assert len(set(rm.SRF_CATEGORIES["Q-NGI-2025"].values())) == 5
    assert len(set(rm.SRF_CATEGORIES["Q-NGI-2015"].values())) == 4


def test_srf_category_differs_for_h_to_p():
    c25, c15 = rm.SRF_CATEGORIES["Q-NGI-2025"], rm.SRF_CATEGORIES["Q-NGI-2015"]
    for letter in "HJKLMNOP":
        assert c25[letter] != c15[letter], letter
    for letter in "ABCDEFG":
        assert c25[letter] == c15[letter], letter
