"""`rockmass history`: auditoría sola, --correlations, --output, códigos 0/1/2 y el centinela ZZSENT (R12, R13)."""
import csv
import dataclasses
import json
import sys

import pytest

import rockmasspy as rm
from rockmasspy.cli import main
from rockmasspy.table_io import correlation_from_dict

from test_batch import CAT, rmr_tab

pytest.importorskip("openpyxl")
pred = pytest.importorskip("rockmasspy.predictive")

SENT = "ZZSENT"


def historico(tmp_path, *, sentinel=True, bad_q=False, seed=12, n_zones=4):
    """Histórico sintético en .xlsx; con `sentinel`, labor, zona y litología llevan ZZSENT."""
    h, _ = pred.synthetic_history(n_zones=n_zones, seed=seed)
    ts = list(h.tramos)
    if sentinel:
        ts = [dataclasses.replace(t, labor_codigo=f"{SENT}-{t.labor_codigo}", zona_nivel=f"{SENT}-{t.zona_nivel}",
                                  litologia=f"{SENT}-{t.litologia}") for t in ts]
    if bad_q:  # un Q registrado que no cuadra con sus componentes: un hallazgo q_mismatch
        ts[0] = dataclasses.replace(ts[0], q_valor=ts[0].q_valor * 3)
    p = tmp_path / "historico.xlsx"
    rm.save_history_xlsx(rm.History(tuple(ts), h.support_types, h.inspections), p)
    return p


def sin_centinela(capsys):
    cap = capsys.readouterr()
    assert SENT not in cap.out and SENT not in cap.err
    return cap


def test_audit_only(tmp_path, capsys):
    code = main(["history", str(historico(tmp_path, bad_q=True))])
    out = sin_centinela(capsys).out
    assert code == 2  # un hallazgo
    assert "tramos: " in out and "findings: 1" in out and "finding: q_mismatch (1)" in out
    assert "level 1 rmr_from_q: ready (pairs " in out and "level 3 performance:" in out
    assert "correlation" not in out
    assert not any(t.startswith("T0") for t in out.split())  # ningún id_tramo


def test_audit_clean_exit_0(tmp_path, capsys):
    assert main(["history", str(historico(tmp_path))]) == 0
    assert "findings: 0" in sin_centinela(capsys).out


def test_correlations_lines_and_exit(tmp_path, capsys):
    code = main(["history", str(historico(tmp_path)), "--correlations"])
    out = sin_centinela(capsys).out
    for kind in pred.KINDS:
        assert f"correlation {kind} mine: n " in out and f"correlation {kind} D1: " in out
        assert f"prior {kind}: " in out
    assert "not_calibrated" in out  # semilla 12: D3 tiene 3 labores
    assert code == 2
    for lit in pred.synthetic.LITHOLOGIES:
        assert lit not in out


def test_correlations_all_site_exit_0(tmp_path, capsys):
    code = main(["history", str(historico(tmp_path)), "--correlations", "--group-by", "none"])
    out = sin_centinela(capsys).out
    assert out.count(", site, a ") == 3 and " D1:" not in out
    assert code == 0


def test_output_files(tmp_path, capsys):
    out_dir = tmp_path / "salida"
    code = main(["history", str(historico(tmp_path, bad_q=True)), "--correlations", "--output", str(out_dir)])
    sin_centinela(capsys)
    assert code == 2
    with open(out_dir / "history_findings.csv", newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh, delimiter=_sep(out_dir)))
    assert rows[0] == ["hallazgo", "hoja", "fila", "id_tramo", "mensaje"]
    assert rows[1][:4] == ["q_mismatch", "Tramos", "2", "T0001"]  # el id_tramo y la fila sí van en el archivo
    text = (out_dir / "site_correlations.csv").read_text(encoding="utf-8-sig")
    assert SENT in text  # el dominio va en el archivo de resultados
    js = json.loads((out_dir / "site_correlations.json").read_text(encoding="utf-8"))
    assert SENT not in json.dumps(js)  # el JSON va a una tabla por labor: solo etiquetas
    corrs = [correlation_from_dict(c) for c in js["correlations"]]
    assert {c.name for c in corrs} >= {f"{k}_mine" for k in pred.KINDS}
    # se enchufa en una tabla por labor: la tabla lo valida al cargar
    d = rm.to_dict(rm.LaborTable("galería", CAT, rmr_tab()))
    d["correlations"] = js["correlations"]
    assert len(rm.from_dict(d).correlations) == len(corrs)


def _sep(folder):
    first = (folder / "history_findings.csv").read_text(encoding="utf-8-sig").splitlines()[0]
    return ";" if ";" in first else ","


def test_report_without_sentinel(tmp_path, capsys):
    docx = pytest.importorskip("docx")
    rep = tmp_path / "informe.docx"
    html = tmp_path / "informe.html"
    src = historico(tmp_path, bad_q=True)
    assert main(["history", str(src), "--correlations", "--report", str(rep)]) == 2
    assert main(["history", str(src), "--correlations", "--report", str(html), "--lang", "en"]) == 2
    sin_centinela(capsys)
    d = docx.Document(str(rep))
    texto = "\n".join([p.text for p in d.paragraphs]
                      + [c.text for tb in d.tables for row in tb.rows for c in row.cells])
    assert SENT not in texto and "historico" not in texto.lower()
    assert "T0001" in texto  # el id_tramo del hallazgo, en su tabla
    h = html.read_text(encoding="utf-8")
    assert SENT not in h and "historico.xlsx" not in h and "Level 1" in h


def test_errors_exit_1(tmp_path, capsys):
    assert main(["history", str(tmp_path / f"{SENT}.xlsx")]) == 1
    assert main(["history", str(historico(tmp_path)), "--report", "x.pdf"]) == 1
    assert main(["history", str(historico(tmp_path)), "--group-by", SENT]) == 1
    assert main(["history", str(historico(tmp_path)), "--deming-ratio", "1"]) == 1
    assert main(["history", str(historico(tmp_path)), "--correlations", "--deming-ratio", "0"]) == 1
    cap = sin_centinela(capsys)
    assert cap.out == "" and cap.err.count("error: ") == 5


def test_deming_ratio(tmp_path, capsys):
    out_dir = tmp_path / "o"
    main(["history", str(historico(tmp_path)), "--correlations", "--group-by", "none", "--deming-ratio", "1",
          "-o", str(out_dir)])
    sin_centinela(capsys)
    assert (out_dir / "site_correlations.csv").exists()


def test_not_fitted_kind(tmp_path, capsys):
    """Sin GSI no hay pares para gsi_from_*: la línea lo dice, el resto sigue y el código es 2."""
    h, _ = pred.synthetic_history(seed=12)
    p = tmp_path / "h.xlsx"
    rm.save_history_xlsx(rm.History(tuple(dataclasses.replace(t, gsi_valor=None) for t in h.tramos),
                                    h.support_types, h.inspections), p)
    out_dir = tmp_path / "o"
    assert main(["history", str(p), "--correlations", "--group-by", "none", "-o", str(out_dir)]) == 2
    out = capsys.readouterr().out
    assert "correlation gsi_from_rmr: not fitted (gsi_from_rmr: no complete pairs in the history)" in out
    assert "correlation rmr_from_q mine: " in out
    assert "not_fitted" in (out_dir / "site_correlations.csv").read_text(encoding="utf-8-sig")


def test_missing_ml_extra(tmp_path, capsys, monkeypatch):
    src = historico(tmp_path)
    for name in [m for m in sys.modules if m == "rockmasspy.predictive" or m.startswith("rockmasspy.predictive.")]:
        monkeypatch.delitem(sys.modules, name)
    monkeypatch.setitem(sys.modules, "numpy", None)
    assert main(["history", str(src)]) == 0  # la auditoría sola no necesita numpy
    capsys.readouterr()
    assert main(["history", str(src), "--correlations"]) == 1
    cap = capsys.readouterr()
    assert "pip install rockmasspy[ml]" in cap.err and cap.out == ""
