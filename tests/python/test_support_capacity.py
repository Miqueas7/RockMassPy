"""Hoja de capacidades del sostenimiento y tabla de presiones de Hoek (PRE Fig. 8)."""

import pytest

import rockmasspy as rm
from rockmasspy.support_capacity import HOEK_SUPPORT_TABLE, SupportCapacity, hoek_psm, load_support_capacity

ES = """codigo;tipo;psm_mpa;eps_sm;espesor_m;e_mpa;nu;sigma_c_mpa;sigma_t_mpa;capacidad_traccion_mn;adherencia_mn_m;espaciamiento_m;item_hoek
SC50;shotcrete;;;0.05;25000;0.2;35;3.5;;;;Concrete or shotcrete lining 50 mm 28 days 35 MPa
PB;bolt;0.2;0.002;;;;;;0.12;0.4;1.5;
"""
EN = """Code,Kind,Maximum Support Pressure (MPa),Maximum Average Strain,Thickness (m),Young's Modulus (MPa),Poisson's Ratio,Compressive Strength (MPa),Tensile Strength (MPa),Tensile Capacity (MN),Bond Strength (MN/m),Out-of-Plane Spacing (m),item_hoek
SC50,shotcrete,,,0.05,25000,0.2,35,3.5,,,,Concrete or shotcrete lining 50 mm 28 days 35 MPa
PB,bolt,0.2,0.002,,,,,,0.12,0.4,1.5,
""".replace(",", ";")


def test_table_has_26_items_and_eps_only_where_published():
    assert len(HOEK_SUPPORT_TABLE) == 26
    assert {i.kind for i in HOEK_SUPPORT_TABLE} == {"bolt", "set", "lining"}
    con_eps = {i.name: i.eps_sm for i in HOEK_SUPPORT_TABLE if i.eps_sm is not None}
    assert con_eps == {"34 mm rockbolt": 0.002, "Concrete or shotcrete lining 50 mm 28 days 35 MPa": 0.001}
    assert all("246" in i.source_page for i in HOEK_SUPPORT_TABLE)


def test_hoek_psm_published_cases():
    assert hoek_psm("34 mm rockbolt", spacing_m=1.0) == pytest.approx(0.354)
    assert hoek_psm("Concrete or shotcrete lining 50 mm 28 days 35 MPa", diameter_m=12) == pytest.approx(0.3246, abs=1e-4)


def test_hoek_psm_missing_parameter_names_it():
    with pytest.raises(ValueError, match="spacing_m"):
        hoek_psm("34 mm rockbolt")
    with pytest.raises(ValueError, match="diameter_m"):
        hoek_psm("Concrete or shotcrete lining 50 mm 28 days 35 MPa")


def test_to_element_from_hoek_and_eps():
    cap = SupportCapacity(code="PB", kind="bolt", hoek_item="34 mm rockbolt", spacing_m=1.0)
    el = cap.to_element(5.0)
    assert isinstance(el, rm.SupportElement)
    assert el.psm_mpa == pytest.approx(0.354)
    assert el.stiffness_mpa == pytest.approx(0.354 / 0.002)


def test_to_element_without_eps_or_stiffness_names_it():
    with pytest.raises(ValueError, match="eps_sm"):
        SupportCapacity(code="X", kind="bolt", psm_mpa=0.2).to_element(5.0)


def test_capacity_sheet_phase2_headers_and_comma(tmp_path):
    a, b = tmp_path / "a" / "Capacidad_sostenimiento.csv", tmp_path / "b" / "Capacidad_sostenimiento.csv"
    a.parent.mkdir(), b.parent.mkdir()
    a.write_text(ES, encoding="utf-8")
    b.write_text(EN.replace("0.", "0,").replace("3.5", "3,5").replace("1.5", "1,5"), encoding="utf-8")
    x, y = load_support_capacity(a), load_support_capacity(b)
    assert x == y
    assert x["PB"].tensile_capacity_mn == 0.12 and x["PB"].spacing_m == 1.5
    assert x["SC50"].hoek_item == "Concrete or shotcrete lining 50 mm 28 days 35 MPa" and x["SC50"].e_mpa == 25000


def test_capacity_sheet_excel(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Capacidad_sostenimiento"
    ws.append(["code", "Kind", "Maximum Support Pressure", "Maximum Average Strain"])
    ws.append(["PB", "bolt", 0.2, 0.002])
    wb.save(tmp_path / "c.xlsx")
    assert load_support_capacity(tmp_path / "c.xlsx")["PB"].eps_sm == 0.002


def test_catalog_unknown_code_names_row_not_code(tmp_path):
    p = tmp_path / "Capacidad_sostenimiento.csv"
    p.write_text("codigo,tipo,psm_mpa,eps_sm\nZZSENT,bolt,0.2,0.002\n", encoding="utf-8")
    cat = rm.SupportCatalog([rm.SupportType("S1", 1)])
    with pytest.raises(ValueError, match="row 2") as e:
        load_support_capacity(p, catalog=cat)
    assert "ZZSENT" not in str(e.value)


def test_sentinel_never_in_errors(tmp_path):
    p = tmp_path / "Capacidad_sostenimiento.csv"
    p.write_text("codigo,tipo,psm_mpa\nZZSENT,bolt,abc\n", encoding="utf-8")
    with pytest.raises(ValueError) as e:
        load_support_capacity(p)
    assert "ZZSENT" not in str(e.value)
    p.write_text("codigo,tipo\nZZSENT,bolt\nZZSENT,bolt\n", encoding="utf-8")
    with pytest.raises(ValueError) as e:
        load_support_capacity(p)
    assert "ZZSENT" not in str(e.value)
