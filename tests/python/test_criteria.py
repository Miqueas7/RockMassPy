"""Criterios de aceptación como perfiles versionados y su evaluación (fase 3D, tarea 2)."""
import copy
import csv
import json
from types import SimpleNamespace

import pytest

import rockmasspy as rm
from rockmasspy import blocks as bk
from rockmasspy import limit_equilibrium as le
from rockmasspy.criteria import assess_criteria, criteria_attention, criteria_counts, load_criteria_table
from rockmasspy.normative import get_profile, load_profile

RS = get_profile("READ-STACEY-2009")
NDEP = get_profile("NDEP-2021")
WA = get_profile("DMIRS-WA-2019")
RP = get_profile("RYAN-PRYOR-2000")
S = "ZZSENT"


# ---------------------------------------------------------------- objetos armados a mano

def blk(fs=None, pof=None, model="planar", reliability=None, id_=f"B-{S}", order=1, prob=False):
    """BlockResult a mano: `pof` da un probabilístico; `prob=True` sin pof da uno sin muestras válidas."""
    det = None if fs is None else SimpleNamespace(factor_of_safety=fs)
    p = SimpleNamespace(pof=pof) if pof is not None or prob else None
    berm = (SimpleNamespace(reliability=None if reliability is None else SimpleNamespace(reliability=reliability))
            if model == "berm" else None)
    return bk.BlockResult(id_, f"T-{S}", order, model, det, None, p, berm, (), (), ())


def lea(fs=(1.4,), static=None, kh=0.0, newmark=False, id_=f"A-{S}", order=1):
    res = tuple(SimpleNamespace(factor_of_safety=x) for x in fs)
    st = () if static is None else tuple(SimpleNamespace(factor_of_safety=x) for x in static)
    return le.LeAnalysisResult(id_, f"S-{S}", order, "given", res, None, None,
                               SimpleNamespace(displacement_m=0.1) if newmark else None, (), (), (),
                               section=SimpleNamespace(kh=kh), static_results=st)


def one(profile, *, blocks=(), le=(), assignments, **kw):
    return assess_criteria(profile, blocks=blocks, le=le, assignments=assignments, **kw)


def by_rule(checks, rule):
    (c,) = [c for c in checks if c.rule == rule]
    return c


# ---------------------------------------------------------------- perfiles cargados

def _thr(p, iid):
    i = p.version(iid, "2026-11-04")
    return i.value if i.value_range is None else i.value_range


def test_read_stacey_values():
    assert RS.range_policy == "conservative"
    exp = {"banco-todas": (1.1, (25, 50)), "interrampa-baja": ((1.15, 1.20), 25), "interrampa-media": (1.20, 20),
           "interrampa-alta": ((1.20, 1.30), 10), "global-baja": ((1.20, 1.30), (15, 20)),
           "global-media": (1.30, (5, 10)), "global-alta": ((1.30, 1.50), 5)}
    for tag, (fs, pof) in exp.items():
        assert _thr(RS, f"RS-FS-{tag}") == fs and _thr(RS, f"RS-PoF-{tag}") == pof
    for i in RS.items:
        assert (i.verification, i.force, i.page, i.source) == ("V2", "guide", "3", "moffitt2023")
        assert "9.9" in i.article and "Moffitt" in i.article
        assert i.comparison == (">=" if i.check == "slope_fs_static" else "<=")
    assert not [i for i in RS.items if i.check == "slope_fs_pseudostatic"]  # la columna dinámica es [NV]


def test_ndep_dmirs_ryan_values():
    n = {i.item_id: i for i in NDEP.items}
    assert (n["NDEP-6-estatico"].value, n["NDEP-6-seudoestatico"].value, n["NDEP-7-deformacion"].value) == \
           (1.30, 1.05, 1.05)
    assert n["NDEP-7-deformacion"].comparison == "<" and n["NDEP-7-deformacion"].check == "deformation_required"
    assert all(i.verification == "V1" and i.force == "guide" and i.applies_to == ("pad:*",) for i in NDEP.items)
    w = {i.applies_to[0]: i.value for i in WA.items}
    assert w == {"*:moderada": 1.2, "*:seria": 1.5, "*:extrema": 2.0}
    assert all(i.verification == "V1" and i.force == "guide" and i.article == "tabla 3.2" for i in WA.items)
    (r,) = RP.items
    assert (r.value_range, r.page, r.check, r.comparison) == ((50, 90), "31", "berm_reliability", ">=")
    assert r.verification == "PrimaryLaterAuthors"


def test_pe_profile_still_loads():
    pe = get_profile("PE-DS024-2016")
    assert pe.range_policy == "conservative" and all(i.value_range is None for i in pe.items)
    assert pe.version("PE-264", "2026-11-04").check == "none"


# ---------------------------------------------------------------- esquema: value_range y range_policy

def _base():
    return {"schema": 1, "profile_id": "XX-CR", "jurisdiction": "XX", "name": {"es": "x", "en": "x"},
            "instruments": ["G"], "sources": {"s": {"title": "S", "url": "https://example.org"}},
            "items": [{"id": "X-1", "instrument": "G", "article": "t", "page": "1", "source": "s", "force": "guide",
                       "verification": "V1", "effective_from": "2020-01-01", "check": "slope_fs_static",
                       "value_range": [1.2, 1.3], "unit": "FS", "comparison": ">=", "applies_to": ["global:alta"],
                       "summary": {"es": "x", "en": "x"}}]}


BAD = [
    ("rango y valor", lambda d: d["items"][0].update(value=1.2), "value_range"),
    ("rango invertido", lambda d: d["items"][0].update(value_range=[1.3, 1.2]), "value_range"),
    ("rango de una cifra", lambda d: d["items"][0].update(value_range=[1.2, 1.2]), "value_range"),
    ("rango de tres", lambda d: d["items"][0].update(value_range=[1, 2, 3]), "value_range"),
    ("rango con texto", lambda d: d["items"][0].update(value_range=[1, "x"]), "value_range"),
    ("rango en regla sin umbral", lambda d: d["items"][0].update(check="none"), "value_range"),
    ("política mala", lambda d: d.update(range_policy="middle"), "range_policy"),
    ("escala mala", lambda d: d["items"][0].update(applies_to=["tajo:alta"]), "applies_to"),
    ("sin consecuencia", lambda d: d["items"][0].update(applies_to=["global"]), "applies_to"),
    ("sin umbral", lambda d: d["items"][0].pop("value_range"), "value"),
]


@pytest.mark.parametrize("build,field", [b[1:] for b in BAD], ids=[b[0] for b in BAD])
def test_bad_criteria_schema(tmp_path, build, field):
    d = copy.deepcopy(_base())
    build(d)
    p = tmp_path / "bad-cr.json"
    p.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(ValueError) as e:
        load_profile(p)
    assert "bad-cr.json" in str(e.value) and field in str(e.value)


def test_range_policy_in_profile_and_call(tmp_path):
    d = _base()
    p = tmp_path / "ok.json"
    p.write_text(json.dumps(d), encoding="utf-8")
    prof = load_profile(p)
    a = {("le", f"A-{S}"): ("global", "alta")}
    r = lea(fs=(1.25,))
    (c,) = one(prof, le=[r], assignments=a)
    assert (c.required, c.status, c.range_used) == (1.3, "fails", "upper of 1.2-1.3")  # conservador: el alto
    (c,) = one(prof, le=[r], assignments=a, range_policy="lower")
    assert (c.required, c.status, c.range_used) == (1.2, "meets", "lower of 1.2-1.3")
    d["range_policy"] = "lower"
    p.write_text(json.dumps(d), encoding="utf-8")
    assert one(load_profile(p), le=[r], assignments=a)[0].required == 1.2
    with pytest.raises(ValueError, match="range_policy"):
        one(prof, le=[r], assignments=a, range_policy="mid")


def test_conservative_pof_takes_lower():
    a = {("block", f"B-{S}"): ("global", "media")}
    c = by_rule(one(RS, blocks=[blk(fs=2.0, pof=0.07)], assignments=a), "slope_pof")
    assert (c.required, c.status, c.range_used) == (5, "fails", "lower of 5-10")
    c = by_rule(one(RS, blocks=[blk(fs=2.0, pof=0.07)], assignments=a, range_policy="upper"), "slope_pof")
    assert (c.required, c.status) == (10, "meets")


# ---------------------------------------------------------------- límites (R2)

def test_fs_limit_equal_meets_and_just_below_fails():
    a = {("le", f"A-{S}"): ("interrampa", "media")}
    assert by_rule(one(RS, le=[lea(fs=(1.2,))], assignments=a), "slope_fs_static").status == "meets"
    assert by_rule(one(RS, le=[lea(fs=(1.2 - 1e-12,))], assignments=a), "slope_fs_static").status == "fails"
    b = {("block", f"B-{S}"): ("interrampa", "media")}
    assert by_rule(one(RS, blocks=[blk(fs=1.2)], assignments=b), "slope_fs_static").status == "meets"
    assert by_rule(one(RS, blocks=[blk(fs=float("inf"))], assignments=b), "slope_fs_static").status == "meets"


def test_pof_equal_limit_meets():
    a = {("block", f"B-{S}"): ("interrampa", "alta")}
    c = by_rule(one(RS, blocks=[blk(fs=2, pof=0.1)], assignments=a), "slope_pof")
    assert (c.required, c.status) == (10, "meets") and c.obtained == pytest.approx(10)
    assert by_rule(one(RS, blocks=[blk(fs=2, pof=0.1001)], assignments=a), "slope_pof").status == "fails"


def test_le_static_uses_lowest_method_and_static_results():
    a = {("le", f"A-{S}"): ("global", "media")}
    c = by_rule(one(RS, le=[lea(fs=(1.0, 0.9), static=(1.5, 1.35), kh=0.1)], assignments=a), "slope_fs_static")
    assert (c.obtained, c.status, c.reason) == (1.35, "meets", "lowest of 2 methods")


# ---------------------------------------------------------------- asignación incompleta (foco 2)

@pytest.mark.parametrize("assign,reason", [
    (None, "no scale assigned"),
    (("", "media"), "no scale assigned"),
    (("pad", "media"), "the profile has no criterion for this scale"),
    (("global", None), "no consequence assigned"),
])
def test_missing_assignment_is_not_verifiable(assign, reason):
    a = {} if assign is None else {("block", f"B-{S}"): assign}
    cs = one(RS, blocks=[blk(fs=5, pof=0.0)], assignments=a)
    assert [c.status for c in cs] == ["not_verifiable"] * 2 and {c.reason for c in cs} == {reason}
    assert criteria_counts(cs)["meets"] == 0


def test_dmirs_needs_only_consequence():
    a = {("le", f"A-{S}"): (None, "seria"), ("le", "A2"): ("global", "no_seria")}
    cs = one(WA, le=[lea(fs=(1.6,)), lea(fs=(3,), id_="A2", order=2)], assignments=a)
    assert [(c.item_id, c.status) for c in cs] == [("WA-3.2-seria", "meets"), ("", "not_verifiable")]
    assert cs[1].reason == "the profile has no criterion for this consequence"


def test_missing_values_are_not_verifiable():
    a = {("block", f"B-{S}"): ("banco", "alta"), ("berm", "M"): ("banco", "alta"), ("le", f"A-{S}"): ("pad", "alta")}
    cs = one(RS, blocks=[blk(fs=None)], assignments=a)
    assert {c.reason for c in cs} == {"no deterministic FS", "no probabilistic analysis"}
    cs = one(RS, blocks=[blk(fs=2, prob=True)], assignments=a)
    assert by_rule(cs, "slope_pof").reason == "no valid probabilistic samples"
    assert by_rule(one(RP, blocks=[blk(model="berm", id_="M")], assignments=a), "berm_reliability").reason == \
           "berm reliability not evaluated"
    cs = one(NDEP, le=[lea(fs=(float("nan"),))], assignments=a)
    assert by_rule(cs, "slope_fs_static").reason == "no static FS"
    assert by_rule(cs, "slope_fs_pseudostatic").reason == "no pseudo-static analysis"
    assert by_rule(cs, "deformation_required").reason == "no pseudo-static analysis"


def test_bad_assignment_raises_without_echo():
    with pytest.raises(ValueError) as e:
        one(RS, blocks=[blk(fs=2)], assignments={("block", f"B-{S}"): (f"x-{S}", "alta")})
    assert "scale" in str(e.value) and S not in str(e.value)
    with pytest.raises(ValueError, match="pair"):
        one(RS, blocks=[blk(fs=2)], assignments={("block", f"B-{S}"): "banco"})


# ---------------------------------------------------------------- berma y NDEP

def test_berm_reliability_against_ryan_pryor():
    a = {("berm", "M1"): ("banco", "media"), ("berm", "M2"): ("banco", "media")}
    cs = one(RP, blocks=[blk(model="berm", reliability=0.9, id_="M1"), blk(model="berm", reliability=0.6, id_="M2")],
             assignments=a)
    assert [(c.object_kind, c.status, c.required) for c in cs] == [("berm", "meets", 90), ("berm", "fails", 90)]
    assert cs[0].range_used == "upper of 50-90"
    assert one(RS, blocks=[blk(model="berm", reliability=0.9, id_="M1")], assignments=a) == []  # RS no tiene bermas


def test_ndep_deformation_required():
    a = {("le", f"A-{S}"): ("pad", "alta")}
    cs = one(NDEP, le=[lea(fs=(1.0,), static=(1.4,), kh=0.15)], assignments=a)
    assert [(c.rule, c.status) for c in cs] == [("slope_fs_static", "meets"), ("slope_fs_pseudostatic", "fails"),
                                                ("deformation_required", "fails")]
    assert cs[2].reason == "deformation analysis required and missing"
    c = by_rule(one(NDEP, le=[lea(fs=(1.0,), static=(1.4,), kh=0.15, newmark=True)], assignments=a),
                "deformation_required")
    assert (c.status, c.reason) == ("meets", "deformation analysis required and given")
    c = by_rule(one(NDEP, le=[lea(fs=(1.05,), static=(1.4,), kh=0.15)], assignments=a), "deformation_required")
    assert (c.status, c.reason) == ("meets", "deformation analysis not required")


# ---------------------------------------------------------------- art. 264 (motor; su uso con PE-264 es de la tarea 3)

def _pe264(tmp_path):
    d = _base()
    d["items"][0] = {**d["items"][0], "check": "pseudostatic_analysis_present", "value": 100, "unit": "years",
                     "comparison": ">=", "applies_to": []}
    d["items"][0].pop("value_range")
    p = tmp_path / "pe264.json"
    p.write_text(json.dumps(d), encoding="utf-8")
    return load_profile(p)


def test_pseudostatic_analysis_present(tmp_path):
    prof = _pe264(tmp_path)
    g = {("le", f"A-{S}"): ("global", "alta")}
    r = lea(kh=0.1)

    def st(**kw):
        (c,) = one(prof, **kw)
        assert c.object_kind == "le_set" and c.object_id == ""
        return c.status, c.reason

    assert st(le=[r], assignments=g, return_periods={f"A-{S}": 100}) == ("meets", "")
    assert st(le=[r], assignments=g, return_periods={f"A-{S}": 50})[0] == "fails"
    assert st(le=[lea(kh=0.0)], assignments=g, return_periods={f"A-{S}": 100})[0] == "fails"
    assert st(le=[r], assignments=g) == ("not_verifiable",
                                         "return period not given for a pseudo-static overall analysis")
    assert st(le=[r], assignments={}, return_periods={f"A-{S}": 100}) == ("not_verifiable", "no scale assigned")
    assert st(le=[], assignments={}) == ("not_verifiable", "no limit equilibrium analyses given")


# ---------------------------------------------------------------- tabla propia (R7)

CAB = ",".join(rm.CRITERIA_COLUMNS) + ",codigo_mina"


def _table_rows():
    return [f"global,alta,1.4,1.1,3,,Estudio {S},{S}", f"banco,*,1.2,,30,80,Plan {S},{S}"]


def test_user_table_csv_and_excel(tmp_path):
    p = tmp_path / "criterios.csv"
    p.write_text("\n".join([CAB, *_table_rows()]) + "\n", encoding="utf-8")
    prof = load_criteria_table(p)
    assert prof.profile_id == "USER-TABLE" and {i.verification for i in prof.items} == {"user"}
    assert {i.force for i in prof.items} == {"guide"} and len(prof.items) == 6
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Criterios"
    for line in [CAB, *_table_rows()]:
        ws.append([None if c == "" else (float(c) if c.replace(".", "").isdigit() else c) for c in line.split(",")])
    x = tmp_path / "c.xlsx"
    wb.save(x)
    px = load_criteria_table(x)
    strip = [(i.check, i.value, i.comparison, i.applies_to, i.instrument) for i in prof.items]
    assert strip == [(i.check, i.value, i.comparison, i.applies_to, i.instrument) for i in px.items]
    a = {("le", f"A-{S}"): ("global", "alta"), ("block", f"B-{S}"): ("banco", "baja"), ("berm", "M"): ("banco", "alta")}
    cs = assess_criteria(px, le=[lea(fs=(1.0,), static=(1.5,), kh=0.1)],
                         blocks=[blk(fs=1.3, pof=0.2), blk(model="berm", reliability=0.85, id_="M", order=2)],
                         assignments=a)
    got = [(c.object_kind, c.rule, c.status) for c in cs]
    assert got == [("block", "slope_fs_static", "meets"), ("block", "slope_pof", "meets"),
                   ("berm", "berm_reliability", "meets"),
                   ("le", "slope_fs_static", "meets"), ("le", "slope_fs_pseudostatic", "fails")]
    assert all(c.verification == "user" for c in cs)


@pytest.mark.parametrize("row,col", [
    (f"tajo-{S},alta,1.4,,,,F", "escala"),
    (f"global,{S},1.4,,,,F", "consecuencia"),
    ("global,alta,-1,,,,F", "fs_estatico_min"),
    ("global,alta,,,120,,F", "pof_max_pct"),
    (f"global,alta,abc-{S},,,,F", "fs_estatico_min"),
    ("global,alta,,,,,F", "fs_estatico_min"),
    ("global,alta,1.4,,,,", "fuente"),
])
def test_user_table_errors_without_echo(tmp_path, row, col):
    p = tmp_path / "Criterios.csv"
    p.write_text("\n".join([CAB, row + f",{S}"]) + "\n", encoding="utf-8")
    with pytest.raises(ValueError) as e:
        load_criteria_table(p)
    m = str(e.value)
    assert "row 2" in m and col in m and S not in m


def test_user_table_duplicate_key(tmp_path):
    p = tmp_path / "Criterios.csv"
    p.write_text("\n".join([CAB, "global,alta,1.4,,,,F,x", "global,alta,1.5,,,,G,x"]) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="first in row 2"):
        load_criteria_table(p)


# ---------------------------------------------------------------- paridad y privacidad

def _leer(p):
    txt = p.read_text(encoding="utf-8-sig")
    sep = ";" if ";" in txt.splitlines()[0] else ","
    cab, *filas = list(csv.reader(txt.splitlines(), delimiter=sep))
    return cab, [dict(zip(cab, f)) for f in filas]


def _mixed():
    a = {("block", f"B-{S}"): ("global", "media"), ("le", f"A-{S}"): ("interrampa", "baja")}
    return one(RS, blocks=[blk(fs=1.2, pof=0.05), blk(fs=1.5, pof=0.2, id_=f"B2-{S}", order=2)],
               le=[lea(fs=(1.15,))], assignments=a)


def test_parity_counts_attention_and_file(tmp_path):
    cs = _mixed()
    n = criteria_counts(cs)
    assert n == {"checks": 5, "meets": 1, "fails": 2, "not_verifiable": 2}
    assert criteria_attention(cs) == {"slope_fs_static": 2}
    assert sum(criteria_attention(cs).values()) == n["fails"] == sum(c.needs_attention for c in cs)
    cab, filas = _leer(rm.save_criteria_results(cs, tmp_path / "cr.csv"))
    assert tuple(cab) == rm.CRITERIA_RESULT_COLUMNS
    estados = [f["estado"] for f in filas]
    assert estados.count("cumple") == n["meets"] and estados.count("no_cumple") == n["fails"]
    assert estados.count("no_verificable") == n["not_verifiable"]
    assert filas[0]["tipo_objeto"] == "bloque" and filas[0]["id_objeto"] == f"B-{S}"
    assert {f["fuerza"] for f in filas} == {"guia"} and {f["marca"] for f in filas} == {"V2"}
    assert filas[-1]["rango_usado"] == "upper of 1.15-1.2" and filas[-1]["requerido"].replace(",", ".") == "1.2"
    assert not criteria_attention([c for c in cs if c.status != "fails"])


def test_xlsx_sheet_and_inf(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    cs = one(RS, blocks=[blk(fs=float("inf"))], assignments={("block", f"B-{S}"): ("banco", "baja")})
    wb = openpyxl.load_workbook(rm.save_criteria_results(cs, tmp_path / "cr.xlsx"))
    ws = wb["Criterios_resultados"]
    assert ws.cell(2, 8).value == "inf" and ws.cell(2, 9).value == "cumple"


def test_privacy_no_ids_in_repr_or_reasons():
    cs = _mixed() + one(RS, blocks=[blk(fs=1)], assignments={})
    for c in cs:
        assert S not in repr(c) and S not in c.reason


def test_never_approved(tmp_path):
    cs = _mixed()
    assert {c.status for c in cs} <= set(rm.CRITERIA_STATUSES)
    p = rm.save_criteria_results(cs, tmp_path / "cr.csv")
    assert "aprob" not in p.read_text(encoding="utf-8-sig").casefold()


def test_verify_marks_criteria_as_not_verifiable():
    from rockmasspy.verify import verify
    r = verify(RS, as_of="2026-11-04")
    assert {f.status for f in r.findings} == {"not_verifiable"} and r.exit_code == 0


# ---------------------------------------------------------------- con las APIs reales de la 3B y la 3C

def test_real_block_and_le_results(tmp_path):
    from test_blocks import BERMA, J35, PL1, correr, talud
    from test_limit_equilibrium import acads3b_data, hojas, merge, seno
    bres, _ = correr(tmp_path, J35, [talud(buz="50")], [bk_row(PL1), bk_row(BERMA)])
    (lr,) = rm.assess_le(hojas(tmp_path, merge(acads3b_data(kh=0.1, registro="R-ZZSENT"), {"Sismos": seno()})))
    a = {("block", "B1"): ("banco", "alta"), ("berm", "M1"): ("banco", "alta"), ("le", lr.id_analisis): ("pad", "alta")}
    cs = assess_criteria(RS, blocks=bres, le=[lr], assignments=a)
    fs = by_rule([c for c in cs if c.object_kind == "block"], "slope_fs_static")
    assert fs.obtained == pytest.approx(bres[0].fs) and fs.status == ("meets" if bres[0].fs >= 1.1 else "fails")
    cs = assess_criteria(NDEP, le=[lr], assignments=a)
    c = by_rule(cs, "slope_fs_static")
    assert c.obtained == pytest.approx(min(x for x in le.le_static_fs(lr) if x is not None))
    assert by_rule(cs, "slope_fs_pseudostatic").obtained == pytest.approx(lr.fs_min)
    d = by_rule(cs, "deformation_required")
    assert lr.newmark is not None and lr.fs_min < 1.05
    assert (d.status, d.reason) == ("meets", "deformation analysis required and given")
    assert fs.status == "fails" and bres[0].fs < 1.1  # PL-1 (0.818) contra 1.1 en banco


def bk_row(d):
    from test_blocks import B
    return B(**d)
