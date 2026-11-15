"""Criterios para resultados externos: política del SRF, banda cerca del umbral y comparación de métodos (8A, T2)."""
from fractions import Fraction
from types import SimpleNamespace

import pytest

import rockmasspy as rm
from rockmasspy import limit_equilibrium as le
from rockmasspy.criteria import (SSR_BAND, SSR_POLICIES, _threshold, assess_criteria, criteria_assignments,
                                 criteria_attention)
from rockmasspy.external import ExternalRecord, ExternalSet, compare_methods
from rockmasspy.normative import get_profile

RS = get_profile("READ-STACEY-2009")
NDEP = get_profile("NDEP-2021")
AS_OF = "2026-11-14"
S = "ZZSENT"
A, B = f"A-{S}", f"B-{S}"
# el umbral sale del perfil (global, alta) con su política de rango, no se escribe a mano
FS_REQ = _threshold(RS.version("RS-FS-global-alta", AS_OF), RS.range_policy)[0]
SRF_NOTE = "SRF (shear strength reduction), not a limit-equilibrium FS"


def rec(oid, q, v, method=None, kh=None, scale="global", cons="alta", scenario=None):
    return ExternalRecord(oid, q, v, method="ssr" if q == "srf" else method, kh=kh, scale=scale, consequence=cons,
                          scenario=scenario)


def run(records, profile=RS, **kw):
    ext = ExternalSet(tuple(records))
    return assess_criteria(profile, external=ext, assignments=criteria_assignments(external=ext), as_of=AS_OF, **kw)


def get(checks, oid, rule):
    (c,) = [c for c in checks if c.object_id == oid and c.rule == rule]
    return c


def times(x, f):
    """x·f exacto en decimales (1.5 · 1.049 = 1.5735, sin el ruido del float)."""
    return float(Fraction(str(x)) * Fraction(f))


def test_constants():
    assert SSR_BAND == 0.05 and SSR_POLICIES == ("warn", "accept", "not_verifiable")


def test_ext_single_le_method_meets_without_note():
    cs = run([rec(A, "fs", FS_REQ + 0.2, "bishop")])
    c = get(cs, A, "slope_fs_static")
    assert (c.object_kind, c.status, c.reason, c.attention_note) == ("ext", "meets", "", None)
    assert c.obtained == FS_REQ + 0.2 and c.required == FS_REQ and not c.needs_attention
    assert get(cs, A, "slope_pof").status == "not_verifiable"
    assert not [x for x in cs if x.rule == "slope_fs_pseudostatic"]  # sin kh no hay chequeo seudoestático


def test_ext_mixed_methods_policy():
    lo, hi = FS_REQ - 0.1, FS_REQ + 0.1
    rows = [rec(A, "fs", hi, "bishop"), rec(A, "srf", lo), rec(B, "srf", hi)]
    a = get(run(rows), A, "slope_fs_static")
    assert a.status == "fails" and a.obtained == lo and a.needs_attention
    assert "lowest of 2 methods: ssr" in a.reason and SRF_NOTE in a.reason
    b = get(run(rows), B, "slope_fs_static")
    assert (b.status, b.reason) == ("meets", SRF_NOTE)

    cs = run(rows, ssr_policy="not_verifiable")
    a = get(cs, A, "slope_fs_static")
    assert (a.status, a.obtained, a.reason) == ("meets", hi, "")  # se juzga con Bishop
    b = get(cs, B, "slope_fs_static")
    assert (b.status, b.reason, b.obtained) == ("not_verifiable", "SRF not accepted by the policy", None)
    assert b.required == FS_REQ

    a = get(run(rows, ssr_policy="accept"), A, "slope_fs_static")
    assert a.status == "fails" and a.reason == "lowest of 2 methods: ssr"


def test_srf_without_method_is_ssr():
    """E1: un srf armado a mano, sin método (o con otro), se trata igual como «ssr»."""
    raw = ExternalRecord(A, "srf", FS_REQ, scale="global", consequence="alta")
    assert raw.method == "ssr" and ExternalRecord(A, "srf", 1.0, method="bishop").method == "ssr"
    c = get(run([raw]), A, "slope_fs_static")
    assert c.status == "meets" and c.reason == SRF_NOTE and c.attention_note and c.needs_attention
    c = get(run([raw], ssr_policy="not_verifiable"), A, "slope_fs_static")
    assert (c.status, c.reason) == ("not_verifiable", "SRF not accepted by the policy")
    (m,) = compare_methods([raw, ExternalRecord(A, "fs", 1.3, method="bishop")])
    assert set(m.values) == {"ssr", "bishop"}


def test_ext_lowest_names_le_method():
    a = get(run([rec(A, "fs", FS_REQ + 0.1, "bishop"), rec(A, "fs", FS_REQ + 0.05, "spencer"),
                 rec(A, "srf", FS_REQ + 0.3)]), A, "slope_fs_static")
    assert a.reason == "lowest of 3 methods: spencer" and a.attention_note is None


def test_ssr_band_edges():
    vals = [FS_REQ, times(FS_REQ, "1.049"), times(FS_REQ, "1.051")]
    rows = [rec(f"{k}-{S}", "srf", v) for k, v in enumerate(vals)]
    cs = [get(run(rows), f"{k}-{S}", "slope_fs_static") for k in range(3)]
    assert [c.status for c in cs] == ["meets"] * 3
    assert [c.needs_attention for c in cs] == [True, True, False]
    assert cs[0].attention_note and cs[2].attention_note is None and S not in cs[0].attention_note
    assert criteria_attention(cs) == {"slope_fs_static": 2}
    acc = [get(run(rows, ssr_policy="accept"), f"{k}-{S}", "slope_fs_static") for k in range(3)]
    assert [c.status for c in acc] == ["meets"] * 3 and not any(c.needs_attention for c in acc)
    assert all(c.reason == "" for c in acc)
    # la banda es solo para el SRF: un Bishop en el umbral no pide atención
    assert not get(run([rec(A, "fs", FS_REQ, "bishop")]), A, "slope_fs_static").needs_attention


def test_ext_kh_split():
    rows = [rec(A, "fs", 1.4, "bishop"), rec(A, "fs", 1.35, "spencer", kh=0.0), rec(A, "fs", 1.1, "bishop", kh=0.1),
            rec(B, "fs", 1.4, "bishop")]
    cs = run([rec(r.object_id, r.quantity, r.value, r.method, r.kh, scale="pad") for r in rows], profile=NDEP)
    assert get(cs, A, "slope_fs_static").obtained == 1.35
    assert get(cs, A, "slope_fs_pseudostatic").obtained == 1.1
    assert not [c for c in cs if c.object_id == B and c.rule == "slope_fs_pseudostatic"]
    assert not [c for c in cs if c.rule == "deformation_required"]


def test_ext_pof():
    c = get(run([rec(A, "pof_pct", 3.0)]), A, "slope_pof")
    assert c.obtained == 3.0 and c.comparison == "<=" and c.status == "meets"
    assert get(run([rec(A, "pof_pct", 3.0)]), A, "slope_fs_static").status == "not_verifiable"


def test_ext_assignments():
    ext = ExternalSet((rec(A, "fs", 1.4, "bishop"), rec(A, "u_total_m", 0.01, cons=None)))
    assert criteria_assignments(external=ext) == {("ext", ("", "", A)): ("global", "alta")}
    bad = ExternalSet((rec(A, "fs", 1.4, "bishop"), rec(A, "srf", 1.3, cons="media")))
    with pytest.raises(ValueError, match="consequence") as e:
        criteria_assignments(external=bad)
    assert S not in str(e.value)
    with pytest.raises(ValueError, match="ssr_policy"):
        run([rec(A, "fs", 1.4, "bishop")], ssr_policy="maybe")


def test_ext_same_id_two_scenarios_ordered():
    rows = [rec(A, "fs", FS_REQ + 0.1, "bishop", scenario="s2"), rec(A, "fs", FS_REQ - 0.1, "bishop", scenario="s1")]
    st = [c for c in run(rows) if c.rule == "slope_fs_static"]
    assert [c.obtained for c in st] == [FS_REQ - 0.1, FS_REQ + 0.1] and [c.order for c in st] == [1, 2]
    assert all(S not in c.reason for c in run(rows))


def test_no_external_is_unchanged():
    lea = le.LeAnalysisResult(A, f"S-{S}", 1, "given", (SimpleNamespace(factor_of_safety=1.4),), None, None, None,
                              (), (), (), section=SimpleNamespace(kh=0.0))
    kw = dict(le=[lea], assignments=criteria_assignments(le=[lea]), as_of=AS_OF)
    assert assess_criteria(RS, **kw) == assess_criteria(RS, external=(), **kw)
    assert all(c.attention_note is None for c in assess_criteria(RS, **kw))


def test_compare_methods():
    rows = [rec(A, "fs", 1.30, "bishop"), rec(A, "fs", 1.28, "spencer"), rec(A, "srf", 1.12),
            rec(B, "fs", 1.30, "bishop"), rec(B, "fs", 1.25, "spencer"), rec(f"C-{S}", "fs", 1.3, "bishop")]
    lea = le.LeAnalysisResult(B, f"S-{S}", 1, "given",
                              (SimpleNamespace(factor_of_safety=1.27, method=rm.LeMethod.Bishop),), None, None, None,
                              (), (), (), section=SimpleNamespace(kh=0.0))
    a, b = compare_methods(ExternalSet(tuple(rows)), [lea])  # un solo método no se compara
    assert (a.object_id, a.values) == (A, {"bishop": 1.30, "spencer": 1.28, "ssr": 1.12})
    assert a.spread == pytest.approx(0.1607, abs=1e-4) and a.warning == "methods differ by more than 10 %"
    assert b.values == {"bishop": 1.30, "spencer": 1.25, "rockmasspy:bishop": 1.27} and b.warning is None
    assert compare_methods(rows, threshold=0.15)[0].warning == "methods differ by more than 15 %"
    assert compare_methods(rows, threshold=0.20)[0].warning is None


SSR_REJECTED = "SRF not accepted by the policy"


@pytest.mark.parametrize("kw", [dict(method="SSR"), dict(method=" ssr "), dict(method="shear strength reduction"),
                                dict(method="Strength Reduction"), dict(program="RS2"), dict(program="FLAC3D")],
                         ids=["upper", "spaces", "words", "words-upper", "rs2", "flac3d"])
def test_fs_written_as_ssr_is_judged_as_srf(kw):
    """Revisión final (antiobjetivo): un FS que en realidad es SRF no se juzga en silencio como FS de LE."""
    r = ExternalRecord(A, "fs", 1.5, scale="global", consequence="alta", **kw)
    assert r.method == "ssr"
    c = get(run([r], ssr_policy="not_verifiable"), A, "slope_fs_static")
    assert (c.status, c.reason, c.obtained) == ("not_verifiable", SSR_REJECTED, None)
    assert SRF_NOTE in get(run([r]), A, "slope_fs_static").reason


def test_explicit_le_method_and_le_program_are_kept():
    assert ExternalRecord(A, "fs", 1.5, program="RS2", method=" Bishop ").method == "bishop"
    assert ExternalRecord(A, "fs", 1.5, program="Slide2").method is None
    assert ExternalRecord(A, "u_total_m", 0.1, program="RS2").method is None  # solo el FS se vuelve SRF


def test_lowest_counts_distinct_methods():
    """Dos filas Bishop son un solo método: no hay «lowest of n methods»."""
    c = get(run([rec(A, "fs", FS_REQ + 0.2, "bishop"), rec(A, "fs", FS_REQ + 0.1, "bishop")]), A, "slope_fs_static")
    assert c.reason == "" and c.obtained == FS_REQ + 0.1
    c = get(run([rec(A, "fs", FS_REQ + 0.2, "bishop"), rec(A, "fs", FS_REQ + 0.1, "bishop"),
                 rec(A, "fs", FS_REQ + 0.3, "spencer")]), A, "slope_fs_static")
    assert c.reason == "lowest of 2 methods: bishop"


def _csv_rows(path):
    import csv
    with open(path, encoding="utf-8-sig", newline="") as f:
        text = f.read()
    return list(csv.DictReader(text.splitlines(), delimiter=";" if text.count(";") > text.count(",") else ","))


def test_band_note_written_to_criteria_file(tmp_path):
    from rockmasspy.criteria import SSR_ATTENTION, save_criteria_results

    cs = run([rec(A, "srf", FS_REQ)])
    (row,) = [r for r in _csv_rows(save_criteria_results(cs, tmp_path / "c.csv")) if r["regla"] == "slope_fs_static"]
    assert SRF_NOTE in row["razon"] and SSR_ATTENTION in row["razon"]
    far = run([rec(A, "srf", FS_REQ + 0.5)])
    (row,) = [r for r in _csv_rows(save_criteria_results(far, tmp_path / "f.csv")) if r["regla"] == "slope_fs_static"]
    assert row["razon"] == SRF_NOTE


def test_ext_file_id_keeps_model_and_scenario(tmp_path):
    from rockmasspy.criteria import save_criteria_results

    rows = [ExternalRecord(A, "fs", FS_REQ + 0.2, method="bishop", model="M1", scenario="estatico", scale="global",
                           consequence="alta"),
            ExternalRecord(A, "fs", FS_REQ - 0.1, method="bishop", model="M1", scenario="sismico", kh=0.1,
                           scale="global", consequence="alta"),
            ExternalRecord(B, "fs", FS_REQ + 0.2, method="bishop", scale="global", consequence="alta")]
    cs = run(rows)
    assert {c.object_id for c in cs} == {A, B}  # la API sigue con el id del objeto
    ids = [r["id_objeto"] for r in _csv_rows(save_criteria_results(cs, tmp_path / "c.csv"))]
    assert set(ids) == {f"M1/estatico/{A}", f"M1/sismico/{A}", B}


@pytest.mark.parametrize("kw", [dict(program="PLAXIS 2D"), dict(program="PLAXIS 3D"), dict(program="FLAC/Slope"),
                                dict(method="SSR-FEM"), dict(method="FEM SSR"), dict(method="phi-c reduction"),
                                dict(method="Phi C Reduction"), dict(method="c-phi reduction")])
def test_ssr_variants_judged_as_srf(kw):
    """Re-revisión del antiobjetivo: prefijos de programa y variantes del método de reducción."""
    r = ExternalRecord(A, "fs", 1.5, scale="global", consequence="alta", **kw)
    assert r.method == "ssr"
    c = get(run([r], ssr_policy="not_verifiable"), A, "slope_fs_static")
    assert (c.status, c.reason) == ("not_verifiable", SSR_REJECTED)


@pytest.mark.parametrize("method", ["bishop", "Spencer", "GLE", "janbu", "sarma", "Morgenstern-Price", "M-P"])
def test_le_method_with_fe_program_is_kept(method):
    r = ExternalRecord(A, "fs", FS_REQ + 0.2, program="RS2", method=method, scale="global", consequence="alta")
    assert r.method == method.lower()
    c = get(run([r], ssr_policy="not_verifiable"), A, "slope_fs_static")
    assert c.status == "meets" and c.reason == ""
    assert ExternalRecord(A, "fs", 1.5, program="Slide2").method is None
