"""Resultados externos: formato largo, unidades, lector con alias y tabla RocData (Fase 8A, Tarea 1)."""

import pytest

import rockmasspy as rm
from rockmasspy.external import QUANTITIES, load_external, load_rocdata_table, check_rocdata

LARGO = """programa,modelo,escenario,etapa,tipo_objeto,id,magnitud,metodo,valor,unidad,kh
Slide2,M1,estatico,,section,S1,fs,Bishop,1.45,-,0
Slide2,M1,estatico,,section,S1,fs,Spencer,1.50,,0
RS2,M1,estatico,,section,S1,srf,,1.38,,0
Slide2,M1,estatico,,section,S2,fs,Bishop,1.20,,0
Slide2,M1,estatico,,section,S2,fs,Spencer,1.22,,0
RS2,M1,estatico,,point,P1,u_total_m,,0.020,m,
"""


def _w(tmp_path, text, name="r.csv"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_load_external_long_spanish(tmp_path):
    s = load_external(_w(tmp_path, LARGO))
    assert len(s.records) == 6
    srf = [r for r in s.records if r.quantity == "srf"]
    assert srf[0].method == "ssr" and srf[0].program == "RS2"
    assert [r.method for r in s.records if r.quantity == "fs"][:2] == ["bishop", "spencer"]
    assert set(s.objects()) == {("M1", "estatico", "S1"), ("M1", "estatico", "S2"), ("M1", "estatico", "P1")}
    assert QUANTITIES["u_total_m"] == "m" and QUANTITIES["pof_pct"] == "%"


def test_load_external_comma_and_units(tmp_path):
    p = _w(tmp_path, "ID;Factor of Safety (-);Total Displacement (mm)\nZZSENT-1;1,25;35,5\n")
    s = load_external(p)
    got = {r.quantity: r.value for r in s.records}
    assert got == pytest.approx({"fs": 1.25, "u_total_m": 0.0355})
    assert all(r.unit == QUANTITIES[r.quantity] for r in s.records)


def test_column_map_and_defaults(tmp_path):
    p = _w(tmp_path, "id,FoS\nA,1.3\n")
    with pytest.raises(ValueError, match="quantity"):
        load_external(p)
    s = load_external(p, column_map={"FoS": "fs"}, defaults={"program": "Slide2", "version": "9.045"})
    r = s.records[0]
    assert (r.quantity, r.value, r.program, r.version) == ("fs", 1.3, "Slide2", "9.045")


def test_unit_conversions_long(tmp_path):
    p = _w(tmp_path, "id,magnitud,valor,unidad\n"
           "a,sigma1_mpa,2500,kPa\nb,axial_force_mn,100,t\nc,moment_mnm,10,t·m\nd,convergence_m,5,cm\n")
    v = {r.object_id: r.value for r in load_external(p).records}
    assert v == pytest.approx({"a": 2.5, "b": 0.98066500, "c": 0.0980665, "d": 0.05})


def test_incompatible_unit_names_row_and_column_no_values(tmp_path):
    p = _w(tmp_path, "id,magnitud,valor,unidad\na,fs,1.2,-\nZZSENT,fs,1.7777,mm\n")
    with pytest.raises(ValueError) as e:
        load_external(p)
    m = str(e.value)
    assert "row 3" in m and "'unidad'" in m and "ZZSENT" not in m and "1.7777" not in m


def test_nonnumeric_value_error_has_no_text(tmp_path):
    p = _w(tmp_path, "id,magnitud,valor\na,fs,ZZSENT\n")
    with pytest.raises(ValueError) as e:
        load_external(p)
    assert "row 2" in str(e.value) and "'valor'" in str(e.value) and "ZZSENT" not in str(e.value)


def test_unknown_quantity_column_ignored(tmp_path):
    s = load_external(_w(tmp_path, "id,FS,Plastic Strain\na,1.3,0.2\n"))
    assert [r.quantity for r in s.records] == ["fs"]
    assert any("unrecognized columns ignored" in n for n in s.notes)
    assert not any("Plastic" in n for n in s.notes)
    with pytest.raises(ValueError, match="column"):
        load_external(_w(tmp_path, "ID,Plastic Strain\na,0.2\n", "q.csv"))


def test_missing_id_error(tmp_path):
    with pytest.raises(ValueError, match="'id'"):
        load_external(_w(tmp_path, "FS\n1.2\n"))


ROC = """Material,UCS (MPa),GSI,mi,mb,s,a,Erm (MPa),Poisson's ratio,Unit Weight (MN/m3)
SPP,45,53,21.22,3.961,0.0054,0.505,11920,0.25,{g}
SPB,49,56,22.01,4.573,0.0075,0.504,15093,0.25,{g}
Volcanico,75,50,26.17,4.388,0.0039,0.506,9340,0.23,{g}
Dique,110,53,28.98,5.409,0.0054,0.505,11920,0.24,{g}
"""


def test_rocdata_table_consistent_and_gamma_note(tmp_path):
    rows = load_rocdata_table(_w(tmp_path, ROC.format(g="0.027")))
    assert len(rows) == 4 and rows[0].sigma_ci_mpa == 45 and rows[0].nu == 0.25
    res = check_rocdata(rows)
    assert all(not c.mismatches and not c.notes for c in res)
    bad = check_rocdata(load_rocdata_table(_w(tmp_path, ROC.format(g="0.042"), "g.csv")))
    assert all("unit weight outside the usual range; check units" in c.notes for c in bad)


def test_rocdata_gamma_kn(tmp_path):
    t = ROC.replace("(MN/m3)", "(kN/m3)").format(g="27")
    assert not any(c.notes for c in check_rocdata(load_rocdata_table(_w(tmp_path, t))))


FE_NOTE = "FS from a finite-element/difference program treated as SRF"


def test_fs_from_fe_program_without_method_is_ssr_with_note(tmp_path):
    """Revisión final: un FS de RS2/FLAC3D sin método es un SRF; la nota va agrupada y sin ids."""
    s = load_external(_w(tmp_path, "programa,id,magnitud,metodo,valor\nRS2,ZZSENT-a,fs,,1.5\n"
                                   "FLAC3D,ZZSENT-b,fs,,1.4\nSlide2,ZZSENT-c,fs,,1.3\nRS2,ZZSENT-d,fs,Bishop,1.2\n"))
    assert [r.method for r in s.records] == ["ssr", "ssr", None, "bishop"]
    assert s.notes.count(FE_NOTE) == 1 and not any("ZZSENT" in n or "1.5" in n for n in s.notes)
    assert FE_NOTE not in load_external(_w(tmp_path, "programa,id,magnitud,valor\nSlide2,a,fs,1.3\n", "s.csv")).notes


def test_column_map_targets_accept_aliases(tmp_path):
    p = _w(tmp_path, "Section ID,FoS,Probability of Failure (%)\nZZSENT-1,1.3,2.5\n")
    s = load_external(p, column_map={"Section ID": "id", "FoS": "Factor of Safety"})
    assert {(r.object_id, r.quantity, r.value) for r in s.records} == {("ZZSENT-1", "fs", 1.3),
                                                                      ("ZZSENT-1", "pof_pct", 2.5)}
    s = load_external(_w(tmp_path, "Node,Total Displacement (mm)\nZZSENT-N1,35\n", "n.csv"),
                      column_map={"Node": "Object ID"})
    assert s.records[0].object_id == "ZZSENT-N1"


def test_probability_of_failure_alias(tmp_path):
    (r,) = load_external(_w(tmp_path, "id,Probability of Failure (%)\na,2.5\n")).records
    assert (r.quantity, r.value, r.unit) == ("pof_pct", 2.5, "%")


def test_long_format_with_quantity_columns_notes_them(tmp_path):
    s = load_external(_w(tmp_path, "id,magnitud,valor,FS\nZZSENT-a,fs,1.3,1.4\n"))
    assert [(r.quantity, r.value) for r in s.records] == [("fs", 1.3)]
    assert "quantity columns ignored in long format" in s.notes
    assert not any("FS" in n or "ZZSENT" in n for n in s.notes)
