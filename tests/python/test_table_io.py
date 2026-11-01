import sys

import pytest

import rockmasspy as rm
from test_labor_table import CAT, ctab, rtab

CORR = rm.CustomCorrelation(name="mine RMR-Q", from_="Q", to="RMR", form=rm.CorrelationForm.LogLinear,
                            a=9.0, b=44.0, valid_min=0.1, valid_max=100.0, source="synthetic")


def range_lt():
    return rm.LaborTable("galería", CAT, rtab(), span_m=(3.0, 4.0), correlations=(CORR,),
                         author="Ing. Prueba", date="2026-11-01", notes="nota")


def cells_lt():
    return rm.LaborTable("tajeo", CAT, ctab())


@pytest.mark.parametrize("make", [range_lt, cells_lt])
def test_roundtrip_dict_json_yaml(make, tmp_path):
    t = make()
    assert rm.from_dict(rm.to_dict(t)) == t
    rm.save_json(t, tmp_path / "t.json")
    assert rm.load_json(tmp_path / "t.json") == t
    rm.save_yaml(t, tmp_path / "t.yaml")
    assert rm.load_yaml(tmp_path / "t.yaml") == t


def test_accent_survives_and_file_is_utf8(tmp_path):
    rm.save_json(range_lt(), tmp_path / "t.json")
    assert "galería" in (tmp_path / "t.json").read_text(encoding="utf-8")
    assert rm.load_json(tmp_path / "t.json").labor_type == "galería"


def test_dict_has_schema_and_base_edition():
    d = rm.to_dict(range_lt())
    assert d["schema"] == rm.SCHEMA and d["version"] == 1 and d["table"]["base_edition"] == "RMR89"
    assert d["correlations"][0]["from"] == "Q" and d["correlations"][0]["form"] == "LogLinear"
    assert rm.to_dict(cells_lt())["table"]["chart"] == "GSI-Vallejo-Osinergmin2017"


def test_from_dict_errors_name_the_path():
    d = rm.to_dict(range_lt())
    with pytest.raises(ValueError, match="schema"):
        rm.from_dict({**d, "schema": "otro"})
    with pytest.raises(ValueError, match="version"):
        rm.from_dict({**d, "version": 2})
    del d["table"]["classes"][0]["lo"]
    with pytest.raises(ValueError, match=r"table\.classes\[0\]\.lo: missing"):
        rm.from_dict(d)
    d = rm.to_dict(range_lt())
    d["support_types"][1]["order"] = "2"
    with pytest.raises(ValueError, match=r"support_types\[1\]\.order: expected a number"):
        rm.from_dict(d)
    d = rm.to_dict(cells_lt())
    d["table"]["chart"] = "nope"
    with pytest.raises(ValueError, match="GSI-Vallejo"):
        rm.from_dict(d)


def test_yaml_missing_gives_helpful_importerror(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "yaml", None)
    with pytest.raises(ImportError, match=r"rockmasspy\[io\]"):
        rm.save_yaml(range_lt(), tmp_path / "t.yaml")
    with pytest.raises(ImportError, match=r"rockmasspy\[io\]"):
        rm.load_yaml(tmp_path / "t.yaml")
    import importlib
    importlib.reload(rm)  # import rockmasspy no depende de yaml


def test_equality_by_content():
    a = rm.SupportCatalog([rm.SupportType("I", 1), rm.SupportType("II", 2)])
    assert a == rm.SupportCatalog([rm.SupportType("II", 2), rm.SupportType("I", 1)])
    assert a != rm.SupportCatalog([rm.SupportType("I", 1)])
    r = rtab()
    assert r == rm.RangeTable("RMR", "RMR89", reversed(r.classes)) and r != rtab("II")
    c = ctab()
    assert c == rm.CellTable(c.chart, reversed(c.cells)) and c != rm.CellTable(c.chart, c.cells[:1])
