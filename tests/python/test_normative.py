"""Perfil normativo: modelo, cargador JSON y vigencia por fecha (fase 2C, tarea 1)."""
import copy
import json
from pathlib import Path

import pytest

import rockmasspy
from rockmasspy import normative
from rockmasspy.normative import available_profiles, get_profile, load_profile

SUMMARY = {"es": "resumen propio", "en": "own summary"}


def base_profile():
    return {
        "schema": 1,
        "profile_id": "XX-TEST",
        "jurisdiction": "XX",
        "name": {"es": "Perfil de prueba", "en": "Test profile"},
        "instruments": ["Decree 1"],
        "sources": {"src": {"title": "Source", "url": "https://example.org/a"}},
        "items": [
            {"id": "T-none", "instrument": "Decree 1", "article": "art. 1", "page": "1", "source": "src",
             "effective_from": "2016-07-29", "effective_to": None, "force": "law", "verification": "V1",
             "check": "none", "summary": SUMMARY},
            {"id": "T-qc", "instrument": "Decree 1", "article": "art. 2", "page": "2", "source": "src",
             "effective_from": "2016-07-29", "effective_to": None, "force": "law", "verification": "V1",
             "check": "qc_ratio", "value": 1.0, "unit": "%", "comparison": ">=", "summary": SUMMARY,
             "cited_standard": "Std 2001"},
            {"id": "T-fs", "instrument": "Guide", "article": "tab. 1", "page": "3", "source": "src",
             "effective_from": "2016-07-29", "effective_to": "2023-12-30", "force": "guide",
             "verification": "V2", "check": "fs_minimum", "value": 1.1, "unit": "FS", "comparison": ">=",
             "applies_to": ["corto"], "summary": SUMMARY},
            {"id": "T-fs", "instrument": "Guide", "article": "tab. 1", "page": "3", "source": "src",
             "effective_from": "2023-12-31", "effective_to": None, "force": "guide",
             "verification": "V1", "check": "fs_minimum", "value": 1.3, "unit": "FS", "comparison": ">=",
             "applies_to": ["corto"], "summary": SUMMARY},
        ],
    }


def write(tmp_path, data, name="xx-test.json"):
    path = tmp_path / name
    path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    return path


def test_valid_profile_and_effective_dates(tmp_path):
    p = load_profile(write(tmp_path, base_profile()))
    assert p.profile_id == "XX-TEST" and p.name["en"] == "Test profile"
    assert p.item_ids() == ("T-none", "T-qc", "T-fs")
    assert p.version("T-fs", "2020-06-01").value == 1.1
    assert p.version("T-fs", "2024-01-01").value == 1.3
    assert p.version("T-fs", "2023-12-30").value == 1.1  # extremos inclusive
    assert p.version("T-fs", "2023-12-31").value == 1.3
    assert p.version("T-fs", "2000-01-01") is None
    assert len(p.versions("T-fs")) == 2
    qc = p.version("T-qc", "2024-01-01")
    assert qc.cited_standard == "Std 2001" and qc.url == "https://example.org/a"
    assert qc.in_force("2024-01-01") and not qc.in_force("2000-01-01")
    assert p.version("T-fs", "2024-01-01").applies_to == ("corto",)


def mutate(fn):
    def build():
        d = copy.deepcopy(base_profile())
        fn(d)
        return d
    return build


def item(d, i=1):
    return d["items"][i]


# (descripción, constructor, id esperado, campo esperado)
BAD = [
    ("force ley", mutate(lambda d: item(d).update(force="ley")), "T-qc", "force"),
    ("NV", mutate(lambda d: item(d).update(verification="NV")), "T-qc", "verification"),
    ("to antes de from", mutate(lambda d: item(d).update(effective_to="2000-01-01")), "T-qc", "effective_to"),
    ("solape", mutate(lambda d: item(d, 3).update(effective_from="2023-01-01")), "T-fs", "effective_from"),
    ("regla desconocida", mutate(lambda d: item(d).update(check="magic")), "T-qc", "check"),
    ("sin comparación", mutate(lambda d: item(d).pop("comparison")), "T-qc", "comparison"),
    ("fuente inexistente", mutate(lambda d: item(d).update(source="nope")), "T-qc", "source"),
    ("URL http", mutate(lambda d: d["sources"]["src"].update(url="http://example.org")), "T-none", "url"),
    ("resumen sin en", mutate(lambda d: item(d).update(summary={"es": "x"})), "T-qc", "summary"),
    ("fecha 30 de febrero", mutate(lambda d: item(d).update(effective_from="2023-02-30")), "T-qc",
     "effective_from"),
    ("value true", mutate(lambda d: item(d).update(value=True)), "T-qc", "value"),
    ("umbral sin value", mutate(lambda d: item(d).pop("value")), "T-qc", "value"),
    ("umbral sin unit", mutate(lambda d: item(d).update(unit="")), "T-qc", "unit"),
    ("esr sin applies_to", mutate(lambda d: item(d).update(check="esr", value="C")), "T-qc", "applies_to"),
    ("schema 2", mutate(lambda d: d.update(schema=2)), "", "schema"),
]


@pytest.mark.parametrize("desc,build,item_id,field", BAD, ids=[b[0] for b in BAD])
def test_bad_profile_names_file_item_and_field(tmp_path, desc, build, item_id, field):
    path = write(tmp_path, build(), name="bad-profile.json")
    with pytest.raises(ValueError) as exc:
        load_profile(path)
    msg = str(exc.value)
    assert "bad-profile.json" in msg and field in msg
    if item_id:
        assert item_id in msg
    if desc == "NV":
        assert "[NV] items do not enter (spec 13)" in msg


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_nan_and_infinity_raise(tmp_path, token):
    text = json.dumps(base_profile()).replace('"value": 1.0', '"value": ' + token)
    assert token in text
    with pytest.raises(ValueError, match="bad.json"):
        load_profile(write(tmp_path, text, name="bad.json"))


def test_esr_accepts_single_applies_to(tmp_path):
    d = base_profile()
    d["items"].append({"id": "T-esr", "instrument": "Guide", "article": "t", "page": "1", "source": "src",
                       "effective_from": "2017-05-01", "effective_to": None, "force": "guide",
                       "verification": "V1", "check": "esr", "value": "A:3", "applies_to": ["tajeo"],
                       "summary": SUMMARY})
    assert load_profile(write(tmp_path, d)).version("T-esr", "2020-01-01").value == "A:3"
    d["items"][-1]["applies_to"] = ["tajeo", "galeria"]
    with pytest.raises(ValueError, match="applies_to"):
        load_profile(write(tmp_path, d))


def test_available_and_get_profile(tmp_path, monkeypatch):
    write(tmp_path, base_profile())
    monkeypatch.setattr(normative, "_profiles_dir", lambda: tmp_path)
    assert available_profiles() == {"XX-TEST": tmp_path / "xx-test.json"}
    assert get_profile("XX-TEST").profile_id == "XX-TEST"
    with pytest.raises(ValueError, match="XX-TEST"):
        get_profile("ZZ")
    write(tmp_path, base_profile(), name="copy.json")
    with pytest.raises(ValueError, match="XX-TEST"):
        available_profiles()


def test_installed_package_has_profiles_dir():
    assert (Path(rockmasspy.__file__).parent / "profiles").is_dir()
