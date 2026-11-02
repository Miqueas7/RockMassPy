"""Informe de verificación normativa y caras de tajeo en la 4.1 del Anexo 39 B (tarea 5 de la 2C). Solo datos sintéticos."""
import pytest

import rockmasspy as rm
from rockmasspy import report as rp
from rockmasspy.design_inputs import (DesignInputs, PedestrianRefugeSpacing, QcMonth, RefugeStation, SafetyFactor,
                                      StandupTime)
from rockmasspy.normative import get_profile
from rockmasspy.stope_surfaces import assess_stope_surfaces
from rockmasspy.verify import verify

from test_verify import LAB, surf, tr

PE = get_profile("PE-DS024-2016")
AS_OF = "2026-11-02"
LEAK = "SECRETO-123"


def full_verification(ident="x"):
    rs = rm.classify_tramos([tr("A", luz=4, rmr_valor=70)], LAB)
    design = DesignInputs(
        refuge_stations=(RefugeStation(ident, "roca", 70, 400, 30, 20),),
        pedestrian_refuges=(PedestrianRefugeSpacing(ident, "galeria", 40),
                            PedestrianRefugeSpacing(ident + "r", "rampa", 25, "curva")),
        qc=(QcMonth("2026-01", "I", 100, 2),),
        safety_factors=(SafetyFactor(ident, "corto", 2.0), SafetyFactor(ident + "b", "largo", 1.5)),
        standup=(StandupTime("galeria", 10),))
    return verify(PE, as_of=AS_OF, tables=LAB, results=rs, stopes=assess_stope_surfaces([surf("a")]),
                  design=design, report=rp.build_anexo39b(rs, LAB, title="t", figures=False))


def sec(report, number):
    return next(s for s in report.sections if s.number == number)


def tables(section):
    return [b for b in section.blocks if isinstance(b, rp.Table)]


def test_sections_and_counts():
    r = rp.build_verification_report(full_verification(), title="Verificación")
    assert [s.number for s in r.sections] == ["1", "2", "3", "4", "5", "6"]
    assert [s.title for s in r.sections] == ["Alcance", "Perfil", "Resultados", "No revisado por falta de datos",
                                             "No verificable por la librería", "Nota"]
    assert r.methods == ()
    s3, s4, s5 = sec(r, "3"), sec(r, "4"), sec(r, "5")
    arts3 = tables(s3)[1].rows
    assert len(arts3) + len(tables(s4)[0].rows) + len(tables(s5)[0].rows) == 24
    nv = [row[0] for row in tables(s5)[0].rows]
    assert len(nv) == 9 and "Anexo 19, num. 9.1" in nv and "art. 264" in nv
    assert sec(r, "6").blocks[0].text == rp.DISCLAIMER["es"]
    # el conteo por estado suma lo mismo
    assert sum(int(c) for _, c in tables(s3)[0].rows) == 24


def test_profile_section():
    r = rp.build_verification_report(full_verification(), title="v")
    flat = [c for tb in tables(sec(r, "2")) for row in tb.rows for c in row]
    assert any("osinergmin" in c.lower() and c.startswith("https://") for c in flat)
    assert PE.sources["osinergmin2017"][1] in flat
    esr = tables(sec(r, "2"))[2]
    row = next(x for x in esr.rows if x[0] == "galeria")
    assert row[1] == "A:3"
    assert AS_OF in [c for tb in tables(sec(r, "2"))[:1] for rw in tb.rows for c in rw]


def test_force_and_marks():
    r = rp.build_verification_report(full_verification(), title="v")
    rows = tables(sec(r, "3"))[1].rows
    forces = {row[3] for row in rows}
    assert forces == {"ley", "guía"}
    assert {row[4] for row in rows} <= {"V1", "V2"}


def test_english():
    r = rp.build_verification_report(full_verification(), title="v", lang="en")
    assert [s.title for s in r.sections] == ["Scope", "Profile", "Results", "Not checked for lack of data",
                                             "Not verifiable by the library", "Note"]
    rows = tables(sec(r, "3"))[1].rows
    assert {row[0] for row in rows} <= {"complies", "does not comply", "attention", "note"}
    assert {row[3] for row in rows} == {"law", "guide"}


def test_docx_and_html(tmp_path):
    pytest.importorskip("docx")
    import docx
    r = rp.build_verification_report(full_verification(), title="v", author="Ing. X")
    p = tmp_path / "v.docx"
    rp.write_docx(r, p, author="Ing. X")
    d = docx.Document(str(p))
    heads = [t.rows[0].cells[0].text for t in d.tables]
    assert "Estado" in heads


@pytest.mark.parametrize("lang", ["es", "en"])
def test_no_approval_words(lang, tmp_path):
    r = rp.build_verification_report(full_verification(), title="v", lang=lang)
    p = tmp_path / "v.html"
    rp.write_html(r, p)
    low = p.read_text(encoding="utf-8").lower()
    for w in ("aprob", "aprueb", "approv"):
        assert w not in low


def test_foco5_no_leak(tmp_path):
    v = full_verification(ident=LEAK + "-id_refugio")
    r = rp.build_verification_report(v, title="v")
    p = tmp_path / "v.html"
    rp.write_html(r, p)
    html = p.read_text(encoding="utf-8")
    assert LEAK not in html
    for w in ("id_refugio", "id_via", "id_tramo"):
        assert w not in html


def test_bad_lang():
    with pytest.raises(ValueError):
        rp.build_verification_report(full_verification(), title="v", lang="fr")


# --- gancho de la 2B: caras de tajeo en la 4.1 del Anexo 39 B ---

PIN_ES = [
    ("1", "Introducción"), ("2", "Caracterización geomecánica del macizo rocoso"), ("2.1", "galeria (luz 1-5 m)"),
    ("T", "Clases y sostenimiento"), ("T", "Catálogo de sostenimiento"), ("2.2", "rampa"),
    ("T", "Clases y sostenimiento"), ("T", "Catálogo de sostenimiento"),
    ("3", "Condiciones geomecánicas actuales de la labor"),
    ("T", "Tramos de la labor, con su clase y su sostenimiento"), ("4", "Evaluación de estabilidad"),
    ("4.1", "Cálculo empírico"), ("T", "Resultados de la clasificación"), ("T", "Métodos usados y su verificación"),
    ("4.2", "Análisis cinemático de cuñas"), ("4.3", "Modelamiento numérico"),
    ("4.3.1", "Recomendación de excavación o explotación"),
    ("4.3.2", "Recomendación de reforzamiento o sostenimiento"), ("5", "Conclusiones y recomendaciones"),
    ("6", "Anexos"), ("", "Memoria resumen de parámetros de entrada"), ("T", "galeria (luz 1-5 m) (RMR89)"),
    ("T", "rampa (Q-NGI-2025)")]


def structure(sections):
    out = []
    for s in sections:
        out.append((s.number, s.title))
        for b in s.blocks:
            if isinstance(b, rp.Section):
                out += structure([b])
            elif isinstance(b, rp.Table):
                out.append(("T", b.caption))
    return out


def test_anexo39b_without_stopes_is_unchanged():
    rs = rm.classify_tramos([tr("A", luz=4, rmr_valor=70)], LAB)
    base = rp.build_anexo39b(rs, LAB, title="t", figures=False)
    assert structure(base.sections) == PIN_ES
    assert rp.build_anexo39b(rs, LAB, title="t", figures=False, stopes=()) == base


def test_anexo39b_with_stopes():
    rs = rm.classify_tramos([tr("A", luz=4, rmr_valor=70)], LAB)
    faces = assess_stope_surfaces([surf("a"), surf("b", q_prima=0.01)])
    base = rp.build_anexo39b(rs, LAB, title="t", figures=False)
    r = rp.build_anexo39b(rs, LAB, title="t", figures=False, stopes=faces)
    caps = [c for n, c in structure([sec(r, "4")]) if n == "T"]
    assert "Caras evaluadas" in caps and "Caras por zona del gráfico" in caps
    ids = [(m.method_id, m.source) for m in r.methods]
    assert len(ids) == len(set(ids)) and len(ids) > len(base.methods)
    assert "Mathews" in " ".join(m.method_id for m in r.methods) or any("athews" in m.method_id for m in r.methods)
    s41 = next(b for b in sec(r, "4").blocks if getattr(b, "number", "") == "4.1")
    methods_tb = next(b for b in s41.blocks if isinstance(b, rp.Table) and b.caption == "Métodos usados y su verificación")
    assert len(methods_tb.rows) == len(r.methods)
