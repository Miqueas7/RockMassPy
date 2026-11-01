import subprocess
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
    pytest.importorskip("yaml")
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


def full_lt():
    cat = rm.SupportCatalog([
        rm.SupportType("I", 1),
        rm.SupportType("II", 2, "ligero", rm.Bolt("split set", 2.1, 1.5), rm.Shotcrete(50, False), "malla 4x4", "cimbra", 1.5)])
    ct = rm.CellTable(rm.GSI_CHARTS["GSI-Vallejo-Osinergmin2017"],
                      [rm.CellClass("F/R", "II", (45, 55), "regular"), rm.CellClass("F/B", "I")])
    return rm.LaborTable("galería", cat, ct, span_m=(3, 4), correlations=(CORR,), date="2026-11-01")


def test_roundtrip_fully_populated(tmp_path):
    pytest.importorskip("yaml")
    t = full_lt()
    assert rm.from_dict(rm.to_dict(t)) == t
    rm.save_json(t, tmp_path / "t.json")
    assert rm.load_json(tmp_path / "t.json") == t
    rm.save_yaml(t, tmp_path / "t.yaml")
    back = rm.load_yaml(tmp_path / "t.yaml")
    assert back == t and back.table.cells[0].gsi_range == (45, 55)
    assert back.catalog.get("II").shotcrete.fiber is False and back.correlations[0].source == "synthetic"


def test_import_without_yaml_in_fresh_interpreter():
    r = subprocess.run([sys.executable, "-I", "-c", "import sys; sys.modules['yaml'] = None; import rockmasspy; print('ok')"],
                       check=True, capture_output=True, text=True)
    assert r.stdout.strip() == "ok"


def test_yaml_unquoted_date(tmp_path):
    pytest.importorskip("yaml")
    rm.save_yaml(range_lt(), tmp_path / "t.yaml")
    txt = (tmp_path / "t.yaml").read_text(encoding="utf-8").replace("'2026-11-01'", "2026-11-01").replace('"2026-11-01"', "2026-11-01")
    assert "date: 2026-11-01" in txt
    (tmp_path / "h.yaml").write_text(txt, encoding="utf-8")
    assert rm.load_yaml(tmp_path / "h.yaml").date == "2026-11-01"


def test_fiber_strings():
    d = rm.to_dict(full_lt())
    d["support_types"][1]["shotcrete"]["fiber"] = " False "
    assert rm.from_dict(d).catalog.get("II").shotcrete.fiber is False
    d["support_types"][1]["shotcrete"]["fiber"] = "Sí"
    assert rm.from_dict(d).catalog.get("II").shotcrete.fiber is True
    d["support_types"][1]["shotcrete"]["fiber"] = "maybe"
    with pytest.raises(ValueError, match=r"support_types\[1\]\.shotcrete\.fiber: expected true/false"):
        rm.from_dict(d)


def test_yaml_missing_gives_helpful_importerror(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "yaml", None)
    with pytest.raises(ImportError, match=r"rockmasspy\[io\]"):
        rm.save_yaml(range_lt(), tmp_path / "t.yaml")
    with pytest.raises(ImportError, match=r"rockmasspy\[io\]"):
        rm.load_yaml(tmp_path / "t.yaml")


def test_equality_by_content():
    a = rm.SupportCatalog([rm.SupportType("I", 1), rm.SupportType("II", 2)])
    assert a == rm.SupportCatalog([rm.SupportType("II", 2), rm.SupportType("I", 1)])
    assert a != rm.SupportCatalog([rm.SupportType("I", 1)])
    r = rtab()
    assert r == rm.RangeTable("RMR", "RMR89", reversed(r.classes)) and r != rtab("II")
    c = ctab()
    assert c == rm.CellTable(c.chart, reversed(c.cells)) and c != rm.CellTable(c.chart, c.cells[:1])
