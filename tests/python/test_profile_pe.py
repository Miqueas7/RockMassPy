"""Perfil Perú PE-DS024-2016: ítems, fuentes y ESR por labor (tarea 2 de la 2C)."""
import pytest

from rockmasspy.batch import add_q_chart_reference, classify_tramos, parse_esr_spec
from rockmasspy.normative import get_profile, profile_esr_specs

from test_batch import TABLES, tr

pe = get_profile("PE-DS024-2016")
D34, D16, D17, OSI = "2023-12-31", "2016-07-29", "2017-08-19", "2017-05-01"
LAW, GUIDE = "law", "guide"

# id, article, page, force, check, value, comparison, unit, applies_to, effective_from
TABLE = [
    ("PE-33-estudios", "art. 33, párr. 1", "56", LAW, "none", None, None, "", (), D34),
    ("PE-33-global-39A", "art. 33, párr. 2; Anexo 39 A", "56; 275", LAW, "none", None, None, "", (), D34),
    ("PE-33-local-39B", "art. 33, párr. 3; Anexo 39 B", "56; 276", LAW, "anexo39b_structure", None, None, "", (), D34),
    ("PE-39B-4.1", "Anexo 39 B, 4.1", "276", LAW, "empirical_calculation", None, None, "", (), D34),
    ("PE-33-actualizacion", "art. 33, párr. 3", "56", LAW, "none", None, None, "", (), D34),
    ("PE-33-tablas-contenido", "art. 33, párr. 3", "56", LAW, "table_content", None, None, "", (), D34),
    ("PE-33-tablas-publicacion", "art. 33, párr. 3", "56", LAW, "none", None, None, "", (), D34),
    ("PE-33-sismicidad-39D", "art. 33, párr. 4; Anexo 39 D", "56; 279–280", LAW, "none", None, None, "", (), D34),
    ("PE-213", "art. 213", "108", LAW, "none", None, None, "", (), D16),
    ("PE-214b-qc", "art. 214 b)", "108", LAW, "qc_ratio", 1, ">=", "%", (), D34),
    ("PE-214g-luz", "art. 214 g)", "109", LAW, "span_within_table", None, None, "", (), D34),
    ("PE-214i-peatonal", "art. 214 i)", "109", LAW, "walkway_spacing", 50, "<=", "m", ("galeria", "otra"), D16),
    ("PE-216-rampa-larga", "art. 216", "109", LAW, "walkway_spacing", 50, "<=", "m", ("rampa:tangente_larga",), D17),
    ("PE-216-rampa-corta-curva", "art. 216", "109", LAW, "walkway_spacing", 30, "<=", "m",
     ("rampa:tangente_corta", "rampa:curva"), D17),
    ("PE-A19-rmr", "Anexo 19, num. 2.1 y 2.2 (art. 151)", "237", LAW, "refuge_rock_quality", 60, ">", "RMR", (), D17),
    ("PE-A19-distancia", "Anexo 19, num. 1", "237", LAW, "refuge_distance", 500, "<=", "m", (), D17),
    ("PE-A19-area", "Anexo 19, num. 2.1 y 2.2", "237", LAW, "refuge_area_per_person", 1.5, ">=", "m2/person", (), D17),
    ("PE-A19-inspeccion", "Anexo 19, num. 9.1", "238", LAW, "none", 3, None, "months", (), D17),
    ("PE-A19-servicios", "Anexo 19, num. 2 a 8, 9.2 y 10", "237–238", LAW, "none", None, None, "", (), D17),
    ("PE-264", "art. 264", "128", LAW, "none", 100, None, "years", (), D16),
    ("OSI-autosoporte-20h", "§8.4", "80 / 81", GUIDE, "standup_time", 20, "<=", "h", (), OSI),
    ("OSI-fs-corto", "Tabla 5-1", "47 / 48", GUIDE, "fs_minimum", 1.1, ">=", "FS", ("corto",), OSI),
    ("OSI-fs-mediano", "Tabla 5-1", "47 / 48", GUIDE, "fs_minimum", 1.3, ">=", "FS", ("mediano",), OSI),
    ("OSI-fs-largo", "Tabla 5-1", "47 / 48", GUIDE, "fs_minimum", 1.5, ">", "FS", ("largo",), OSI),
]
ESR = {"rampa": "C", "bypass": "C", "inclinado": "C", "refugio": "C", "polvorin": "C",
       "tajeo": "A:3", "galeria": "A:3", "subnivel": "A:3", "crucero": "A:3"}


def _current(item_id):
    return pe.version(item_id, "2026-11-02")


def test_loads_with_expected_counts():
    reqs = [i for i in pe.items if i.check != "esr"]
    assert pe.profile_id == "PE-DS024-2016" and pe.jurisdiction == "PE"
    assert pe.instruments == ("DS 024-2016-EM", "DS 023-2017-EM", "DS 034-2023-EM", "Osinergmin 2017")
    assert set(pe.sources) == {"minem2026", "osinergmin2017", "tastem2021"}
    assert len({i.item_id for i in reqs}) == 24 and len(reqs) == 25
    assert sum(i.check == "esr" for i in pe.items) == 9


@pytest.mark.parametrize("row", TABLE, ids=[r[0] for r in TABLE])
def test_item_matches_verified_sources(row):
    iid, article, page, force, check, value, comp, unit, applies, start = row
    i = _current(iid)
    assert (i.article, i.page, i.force, i.verification, i.check) == (article, page, force, "V1", check)
    assert (i.value, i.comparison, i.unit, i.applies_to, i.effective_from) == (value, comp, unit, applies, start)
    assert i.effective_to is None


def test_amended_by_and_cited_standard():
    for iid in pe.item_ids():
        a = _current(iid).amended_by
        if iid in ("PE-214b-qc", "PE-214g-luz") or iid.startswith("PE-33-") or iid == "PE-39B-4.1":
            assert any("DS 034-2023-EM art. 2" in x for x in a), iid
        elif iid.startswith(("PE-216-", "PE-A19-")):
            assert any("DS 023-2017-EM art. 1" in x for x in a), iid
        else:
            assert a == (), iid
    assert _current("PE-33-global-39A").cited_standard == "RMR (Anexo 39 A, 3.4.3; edition not stated)"
    assert all(i.cited_standard == "Q-NGI-2025 Table 4-1 (p. 29 / 33)" for i in pe.items if i.check == "esr")


def test_force_marks_and_old_art33():
    assert all(i.force == "guide" for i in pe.items if i.item_id.startswith("OSI-"))
    assert all(i.force == "law" for i in pe.items if i.item_id.startswith("PE-"))
    assert all(i.verification != "NV" for i in pe.items)
    assert [i.item_id for i in pe.items if i.verification == "V2"] == ["PE-33-actualizacion"]
    old = pe.version("PE-33-actualizacion", "2020-01-01")
    assert old.source == "tastem2021" and old.verification == "V2" and old.effective_to == "2023-12-30"
    assert "monthly" in old.summary["en"]
    assert "monthly" not in pe.version("PE-33-actualizacion", "2026-11-02").summary["en"]


def test_summaries_short_and_neutral():
    for i in pe.items:
        for lang in ("es", "en"):
            s = i.summary[lang]
            assert 0 < len(s) <= 200, i.item_id
            assert not any(w in s.lower() for w in ("aprob", "aprueb", "approv", "—")), i.item_id


def test_esr_specs_and_chart_reference():
    specs = profile_esr_specs(pe, "2026-11-02")
    assert specs == {"rampa": "C", "bypass": "C", "inclinado": "C", "refugio": "C", "polvorin": "C",
                     "tajeo": ("A", 3.0), "galeria": ("A", 3.0), "subnivel": ("A", 3.0), "crucero": ("A", 3.0)}
    assert "*" not in specs
    assert profile_esr_specs(pe, "2017-01-01") == {}  # antes de la guía no hay ESR
    tramos = [tr(f"T{k}", lab, 5.0, q_valor=4.5) for k, lab in enumerate(("rampa", "galeria", "chimenea"))]
    out = add_q_chart_reference(classify_tramos(tramos, TABLES), specs)
    assert out[0].q_chart.esr_used == 1.6 and out[1].q_chart.esr_used == 3.0
    assert out[2].q_chart is None and "no ESR for this labor" in out[2].q_chart_warnings


def test_parse_esr_spec():
    assert parse_esr_spec("A:4") == ("A", 4.0)
    assert parse_esr_spec("c") == "C"
    for bad in ("A:x", "", "A:", ":4"):
        with pytest.raises(ValueError):
            parse_esr_spec(bad)
