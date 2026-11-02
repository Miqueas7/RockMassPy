"""Motor de verificación normativa: estados, hallazgos y las 12 reglas (tarea 3 de la 2C). Solo datos sintéticos."""
import math

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import rockmasspy as rm
from rockmasspy import verify as V
from rockmasspy.design_inputs import (DesignInputs, PedestrianRefugeSpacing, QcMonth, RefugeStation, SafetyFactor,
                                      StandupTime)
from rockmasspy.normative import get_profile
from rockmasspy.report import build_anexo39b, build_memoria
from rockmasspy.stope_surfaces import StopeSurface, assess_stope_surfaces

from test_batch import CAT, cell_tab, q_tab, rmr_tab, tr

PE = get_profile("PE-DS024-2016")
AS_OF = "2026-11-02"
NONE_IDS = {"PE-33-estudios", "PE-33-global-39A", "PE-33-actualizacion", "PE-33-tablas-publicacion",
            "PE-33-sismicidad-39D", "PE-213", "PE-A19-inspeccion", "PE-A19-servicios", "PE-264"}


def run(**kw):
    return V.verify(PE, as_of=AS_OF, **kw)


def by_id(v):
    return {f.item.item_id: f for f in v.findings}


def one(v, iid):
    return by_id(v)[iid]


def test_no_inputs():
    v = run()
    ids = [f.item.item_id for f in v.findings]
    assert len(ids) == 24 == len(set(ids))
    assert ids == [i for i in PE.item_ids() if PE.versions(i)[0].check != "esr"]
    nv = {f.item.item_id for f in v.findings if f.status == "not_verifiable"}
    assert nv == NONE_IDS
    assert sum(f.status == "not_checked" for f in v.findings) == 15
    assert v.exit_code == 0
    assert set(v.counts()) == set(V.STATUSES) and v.counts()["complies"] == 0
    assert one(v, "PE-213").message == "procedural requirement; the library cannot check it"
    assert set(V._RULES) == set(rm.RULES) - {"esr"}


def test_as_of():
    v = V.verify(PE, as_of="2010-01-01")
    assert len(v.findings) == 24 and all(f.status == "not_verifiable" for f in v.findings)
    assert all("applies from" in f.message for f in v.findings)
    assert "no text of this item in force on 2010-01-01 is loaded; the loaded text applies from" in v.findings[0].message
    v = V.verify(PE, as_of="2020-01-01")
    assert one(v, "PE-214b-qc").status == "not_verifiable" and "applies from" in one(v, "PE-214b-qc").message
    assert one(v, "PE-33-actualizacion").item.verification == "V2"
    for bad in ("2026-02-30", "nan"):
        with pytest.raises(ValueError):
            V.verify(PE, as_of=bad)
    assert V.verify(PE).as_of  # por defecto hoy


def stations(*rows):
    return DesignInputs(refuge_stations=tuple(RefugeStation(f"x{i}", *r) for i, r in enumerate(rows)))


E = [("roca", 65, 400, 30, 20), ("roca", 60, 500, 15, 10), ("movil", 55, 500.5, 14.9, 10, True)]


def test_refuge_threshold():
    v = run(design=DesignInputs(refuge_stations=(
        RefugeStation("a", "roca", 65, 400, 30, 20), RefugeStation("b", "roca", 60, 500, 15, 10),
        RefugeStation("c", "movil", 55, 500.5, 14.9, 10, sostenido=True))))
    for iid in ("PE-A19-rmr", "PE-A19-distancia", "PE-A19-area"):
        f = one(v, iid)
        assert f.status == "does_not_comply" and "1 of 3" in f.message
    d = DesignInputs(refuge_stations=(RefugeStation("b", "roca", 60.5, 500, 15, 10),))
    v = run(design=d)
    assert [one(v, i).status for i in ("PE-A19-rmr", "PE-A19-distancia", "PE-A19-area")] == ["complies"] * 3
    assert v.exit_code == 0


def test_walkway():
    P = PedestrianRefugeSpacing
    d = DesignInputs(pedestrian_refuges=(
        P("1", "galeria", 50), P("2", "rampa", 50, "tangente_larga"), P("3", "rampa", 30, "curva"),
        P("4", "rampa", 30.5, "tangente_corta"), P("5", "otra", 51)))
    v = run(design=d)
    a, b, c = (one(v, i) for i in ("PE-214i-peatonal", "PE-216-rampa-larga", "PE-216-rampa-corta-curva"))
    assert (a.status, b.status, c.status) == ("does_not_comply", "complies", "does_not_comply")
    assert "1 of 2" in a.message and "1 of 2" in c.message
    v = run(design=DesignInputs(pedestrian_refuges=(P("1", "galeria", 50),)))
    assert one(v, "PE-216-rampa-larga").status == "not_checked"


def qc(*rows):
    return run(design=DesignInputs(qc=tuple(QcMonth(*r) for r in rows)))


def test_qc():
    f = one(qc(("2026-09", "I", 100, 1), ("2026-09", "II", 101, 1), ("2026-10", "I", 0, 0), ("2026-10", "II", 250, 3)),
            "PE-214b-qc")
    assert f.status == "does_not_comply" and "1 of 3" in f.message
    assert one(qc(("2026-10", "I", 0, 0)), "PE-214b-qc").status == "note"
    assert one(qc(("2026-10", "I", 100, 1)), "PE-214b-qc").status == "complies"


def test_fs_and_standup():
    S = SafetyFactor
    v = run(design=DesignInputs(safety_factors=(S("a", "corto", 1.1), S("b", "mediano", 1.29), S("c", "largo", 1.5),
                                                S("d", "largo", 1.51))))
    assert one(v, "OSI-fs-corto").status == "complies"
    assert one(v, "OSI-fs-mediano").status == "attention"
    f = one(v, "OSI-fs-largo")
    assert f.status == "attention" and "1 of 2" in f.message
    assert v.exit_code == 2
    T = StandupTime
    f = one(run(design=DesignInputs(standup=(T("galeria", 20), T("rampa", 36)))), "OSI-autosoporte-20h")
    assert f.status == "attention" and "1 of 2" in f.message and "apply art. 213" in f.message
    assert one(run(design=DesignInputs(standup=(T("rampa", 36),))), "OSI-autosoporte-20h").status == "note"


finite = st.floats(min_value=0.1, max_value=2000, allow_nan=False)
RANK = {"complies": 0, "note": 0, "attention": 1, "does_not_comply": 2}


@settings(max_examples=60, deadline=None)
@given(rmr=finite, dist=finite, area=finite, d=st.floats(0, 500), r=st.floats(0, 40), a=st.floats(0, 40))
def test_worse_inputs_never_improve(rmr, dist, area, d, r, a):
    def st_of(rmr, dist, area):
        v = run(design=DesignInputs(refuge_stations=(RefugeStation("a", "roca", min(rmr, 100), dist, area, 3),)))
        return [RANK[one(v, i).status] for i in ("PE-A19-rmr", "PE-A19-distancia", "PE-A19-area")]
    base = st_of(rmr, dist, area)
    worse = st_of(rmr - min(r, rmr - 0.1) if rmr > 0.1 else rmr, dist + d, max(area - min(a, area - 0.01), 0.01))
    assert all(w >= b for w, b in zip(worse, base))


@settings(max_examples=40, deadline=None)
@given(inst=st.integers(1, 1000), tested=st.integers(0, 1000), less=st.integers(0, 1000))
def test_fewer_tests_never_improve(inst, tested, less):
    def rank(n):
        return RANK[one(qc(("2026-10", "I", inst, n)), "PE-214b-qc").status]
    assert rank(max(tested - less, 0)) >= rank(tested)


@settings(max_examples=40, deadline=None)
@given(fs=st.lists(st.tuples(st.sampled_from(["corto", "mediano", "largo"]), st.floats(0.1, 3)), max_size=6),
       su=st.lists(st.floats(0.1, 100), max_size=4))
def test_guide_never_does_not_comply(fs, su):
    d = DesignInputs(safety_factors=tuple(SafetyFactor(str(i), p, x) for i, (p, x) in enumerate(fs)),
                     standup=tuple(StandupTime("galeria", s) for s in su))
    v = run(design=d)
    for f in v.findings:
        if f.item.force == "guide":
            assert f.status != "does_not_comply"


def test_messages_and_sources():
    d = DesignInputs(refuge_stations=(RefugeStation("ID-SECRETO", "roca", 10, 900, 1, 10),),
                     pedestrian_refuges=(PedestrianRefugeSpacing("VIA-SECRETA", "galeria", 99),),
                     safety_factors=(SafetyFactor("AN-SECRETO", "corto", 0.5),))
    rs = rm.classify_tramos([tr("ID-SECRETO-T", luz=4, rmr_valor=70, labor_codigo="LAB-SECRETO")], LAB)
    v = run(design=d, tables=[LAB[0]], results=rs, report=build_anexo39b([], [], title="x"))
    for f in v.findings:
        low = f.message.lower()
        assert not any(w in low for w in ("aprob", "aprueb", "approv", "secreto"))
        assert f.item.url and f.item.page


def test_as_of_after_last_version():
    from dataclasses import replace
    v2 = next(i for i in PE.versions("PE-33-actualizacion") if i.effective_to)
    prof = replace(PE, items=(v2,))
    f = V.verify(prof, as_of="2026-11-02").findings[0]
    assert f.status == "not_verifiable"
    assert f"ended on {v2.effective_to}" in f.message and "applies from" not in f.message


def test_result_type_name():
    assert V.VerificationResult is rm.VerificationResult
    assert hasattr(rm.Verification, "Primary")


LAB = [rm.LaborTable("galeria", CAT, rmr_tab(), span_m=(1, 5)), rm.LaborTable("rampa", CAT, q_tab())]


def test_table_content():
    f = one(run(tables=LAB), "PE-33-tablas-contenido")
    assert f.status == "does_not_comply" and "without span range: 1" in f.message
    assert f.message.endswith("posting in the labor is a separate item")
    f = one(run(tables=LAB[:1]), "PE-33-tablas-contenido")
    assert f.status == "complies" and f.message.endswith("posting in the labor is a separate item")
    bad = rm.LaborTable("galeria", CAT, rm.RangeTable("RMR", "RMR89", [rm.RangeClass(0, 100, "x", None)]),
                        span_m=(1, 5))
    assert "no support: 1" in one(run(tables=[bad]), "PE-33-tablas-contenido").message


def test_span_within_table():
    rs = rm.classify_tramos([tr("A", luz=4), tr("B", luz=6), tr("C", labor="rampa", luz=4), tr("D", luz=None)], LAB)
    f = one(run(tables=LAB, results=rs), "PE-214g-luz")
    assert f.status == "does_not_comply"
    for s in ("within 1", "outside 1", "not judged 2", "height is not checked"):
        assert s in f.message
    only = rm.classify_tramos([tr("A", luz=4), tr("C", labor="rampa", luz=4)], LAB)
    assert one(run(tables=LAB, results=only), "PE-214g-luz").status == "attention"
    ok = rm.classify_tramos([tr("A", luz=4)], LAB)
    assert one(run(tables=LAB, results=ok), "PE-214g-luz").status == "complies"
    assert one(run(results=ok), "PE-214g-luz").status == "not_checked"


def surf(i, **kw):
    d = dict(id_superficie=i, hoja="Caras", fila=2, rqd_pct=None, jn=None, jr=None, ja=None, q_edicion=None,
             q_prima=10.0, ucs_mpa=100.0, sigma1_mpa=5.0, dif_buz_junta_deg=30.0, dif_rumbo_junta_deg=0.0,
             modo_falla="gravedad", inclinacion_cara_deg=90.0, buz_junta_deg=None, area_m2=None, perimetro_m=None,
             ancho_m=10.0, largo_m=20.0)
    d.update(kw)
    return StopeSurface(**d)


def test_empirical():
    rs = rm.classify_tramos([tr("A", luz=4, rmr_valor=70), tr("B", luz=4, rmr_valor=30), tr("C", luz=4), tr("D", luz=4)],
                            LAB)
    f = one(run(results=rs), "PE-39B-4.1")
    assert f.status == "attention" and "classified 2 of 4" in f.message
    ok = rm.classify_tramos([tr("A", luz=4, rmr_valor=70)], LAB)
    assert one(run(results=ok), "PE-39B-4.1").status == "complies"
    faces = assess_stope_surfaces([surf("a"), surf("b", q_prima=0.01), surf("c", q_prima=0.01, ancho_m=60.0)])
    f = one(run(stopes=faces), "PE-39B-4.1")
    assert f.status == "complies" and "faces" in f.message
    f = one(run(results=rs, stopes=faces), "PE-39B-4.1")
    assert f.status == "attention" and "faces" in f.message
    assert one(run(), "PE-39B-4.1").status == "not_checked"


def test_report():
    rs = rm.classify_tramos([tr("A", luz=4, rmr_valor=70)], LAB)
    f = one(run(report=build_anexo39b(rs, LAB, title="t", figures=False)), "PE-33-local-39B")
    assert f.status == "attention" and "4.2" in f.message and "4.3" in f.message
    assert "file copy is not reviewed" in f.message
    f = one(run(report=build_memoria(rs, LAB, title="t", figures=False)), "PE-33-local-39B")
    assert f.status == "does_not_comply"


@settings(max_examples=30, deadline=None)
@given(st.lists(st.booleans(), min_size=9, max_size=9))
def test_every_requirement_once(flags):
    t, r, s, rep, a, b, c, d, e = flags
    rs = rm.classify_tramos([tr("A", luz=4, rmr_valor=70)], LAB)
    kw = {}
    if t:
        kw["tables"] = LAB
    if r:
        kw["results"] = rs
    if s:
        kw["stopes"] = assess_stope_surfaces([surf("a")])
    if rep:
        kw["report"] = build_anexo39b(rs, LAB, title="t", figures=False)
    kw["design"] = DesignInputs(
        refuge_stations=(RefugeStation("a", "roca", 70, 10, 10, 2),) if a else (),
        pedestrian_refuges=(PedestrianRefugeSpacing("a", "galeria", 10),) if b else (),
        qc=(QcMonth("2026-01", "I", 10, 1),) if c else (),
        safety_factors=(SafetyFactor("a", "corto", 2),) if d else (),
        standup=(StandupTime("galeria", 10),) if e else ())
    v = run(**kw)
    ids = [f.item.item_id for f in v.findings]
    assert len(ids) == 24 == len(set(ids))


NAN = math.nan


@pytest.mark.parametrize("make,field", [
    (lambda: RefugeStation("a", "roca", NAN, 1, 1, 1), "rmr"),
    (lambda: RefugeStation("a", "roca", 50, NAN, 1, 1), "distancia_frente_m"),
    (lambda: RefugeStation("a", "roca", 50, 1, NAN, 1), "area_m2"),
    (lambda: RefugeStation("a", "roca", 50, 1, 1, 0), "aforo"),
    (lambda: RefugeStation("a", "roca", 50, 1, 1, 2.5), "aforo"),
    (lambda: RefugeStation("a", "flotante", 50, 1, 1, 1), "tipo"),
    (lambda: RefugeStation("a", "roca", 101, 1, 1, 1), "rmr"),
    (lambda: PedestrianRefugeSpacing("a", "galeria", NAN), "espaciado_max_m"),
    (lambda: PedestrianRefugeSpacing("a", "rampa", 30), "geometria"),
    (lambda: PedestrianRefugeSpacing("a", "galeria", 30, "curva"), "geometria"),
    (lambda: PedestrianRefugeSpacing("a", "rampa", 30, "plana"), "geometria"),
    (lambda: PedestrianRefugeSpacing("a", "calle", 30), "via"),
    (lambda: QcMonth("2026-13", "I", 1, 1), "periodo"),
    (lambda: QcMonth("2026-01", "I", 1, -1), "ensayados"),
    (lambda: QcMonth("2026-01", "I", 1, 1.5), "ensayados"),
    (lambda: QcMonth("2026-01", "I", -1, 1), "instalados"),
    (lambda: SafetyFactor("a", "corto", NAN), "fs"),
    (lambda: SafetyFactor("a", "eterno", 1), "plazo"),
    (lambda: StandupTime("galeria", NAN), "autosoporte_h"),
    (lambda: StandupTime("galeria", 0), "autosoporte_h"),
])
def test_design_types_reject(make, field):
    with pytest.raises(ValueError) as e:
        make()
    assert field in str(e.value)
