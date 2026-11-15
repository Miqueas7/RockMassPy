"""Coherencia de Hoek-Brown: valores publicados de tesis peruanas (INTEGRACION §12.2) y el aviso del K."""

import pytest

import rockmasspy as rm
from rockmasspy.hb_consistency import check_hoek_brown, check_k_ratio


def test_rodriguez_peak_is_consistent():
    # tabla 4.1 de Rodríguez Paihua (2021), fila pico
    r = check_hoek_brown(gsi=35, mi=32, d=0, mb=3.14, s=0.00073, a=0.5159, erm_mpa=1406.2, ei_mpa=12400,
                         sigma_ci_mpa=135.79)
    assert r.mismatches == ()
    assert r.implied_d == pytest.approx(0.0, abs=0.01)


def test_rodriguez_residual_declares_d_but_used_zero():
    # la tesis declara D = 0.3, pero su mb y su s salen con D = 0
    r = check_hoek_brown(gsi=30, mi=32, d=0.3, mb=2.626, s=0.000419)
    assert "mb" in r.mismatches
    assert r.implied_d == pytest.approx(0.0, abs=0.01)
    assert "declared D differs from the D implied by mb and s" in r.notes
    assert "declared mb does not match GSI, mi and D" in r.notes


def test_implied_d_none_when_mb_unreachable():
    r = check_hoek_brown(gsi=30, mi=32, d=0.0, mb=50.0)
    assert r.implied_d is None
    assert "mb" in r.mismatches


def test_simplified_erm_when_no_ei():
    e = rm.erm_hoek_diederichs_simplified(40, 0.0).value
    assert check_hoek_brown(gsi=40, mi=10, d=0, erm_mpa=e).mismatches == ()
    assert check_hoek_brown(gsi=40, mi=10, d=0, erm_mpa=e * 1.5).mismatches == ("erm_mpa",)


def test_k_ratio():
    assert check_k_ratio(1.0, 0.3) == ("model K differs from the study K",)
    assert check_k_ratio(0.48, 0.48) == ()


@pytest.mark.parametrize("gsi,mi,mb,s,a,emr", [
    (53, 21.22, 3.961, 0.0054, 0.505, 11920),   # SPP
    (56, 22.01, 4.573, 0.0075, 0.504, 15093),   # SPB
    (50, 26.17, 4.388, 0.0039, 0.506, 9340),    # volcánico
    (53, 28.98, 5.409, 0.0054, 0.505, 11920),   # dique
])
def test_garcia_aquino_table32(gsi, mi, mb, s, a, emr):
    # García Aquino (2024), tabla 32, p. 69: D = 0 y Emr de Hoek-Diederichs simplificado
    r = check_hoek_brown(gsi=gsi, mi=mi, d=0, mb=mb, s=s, a=a, erm_mpa=emr)
    assert r.mismatches == ()
