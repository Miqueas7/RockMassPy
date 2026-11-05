"""El ejemplo 12 corre: histórico sintético, auditoría, correlaciones propias e informe, con lo que dice su README."""
import importlib.util
import json
from pathlib import Path

import pytest

pytest.importorskip("openpyxl")
pred = pytest.importorskip("rockmasspy.predictive")

RUTA = Path(__file__).resolve().parents[2] / "examples" / "12-historico-prediccion" / "historico.py"


def cargar():
    spec = importlib.util.spec_from_file_location("historico", RUTA)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_historico(tmp_path, capsys):
    r = cargar().main(tmp_path)
    salida = capsys.readouterr().out
    assert r["counts"]["findings"] == 0 and all(r["ready"].values())
    for kind, fits in r["fits"].items():
        assert fits[0][0] == "mine" and fits[0][3] == "site", kind
        assert [f[0] for f in fits if f[3] == "not_calibrated"] == ["D3"], kind
    for kind, (a_true, _) in r["truth"].items():  # el ajuste recupera la pendiente verdadera
        a, _, ci = r["mine"][kind]
        assert ci[0] <= a_true <= ci[1], kind
    for nombre in r["files"]:
        assert (tmp_path / nombre).stat().st_size > 0, nombre
    assert r["files"][-3:] == ["resultados/history_findings.csv", "resultados/site_correlations.csv",
                               "resultados/site_correlations.json"]
    js = json.loads((tmp_path / "resultados" / "site_correlations.json").read_text(encoding="utf-8"))
    # solo los ajustes «sitio»: 3 pares × (mina + 4 dominios), menos D3 («no calibrada al sitio») en cada par
    sitio = sum(f[3] == "site" for fits in r["fits"].values() for f in fits)
    assert len(js["correlations"]) == sitio == 12
    html = (tmp_path / "historico.html").read_text(encoding="utf-8")
    for lit in pred.synthetic.LITHOLOGIES:  # ni en la salida de la CLI ni en el informe
        assert lit not in salida and lit not in html
    assert "historico.xlsx" not in html
    docx = pytest.importorskip("docx")
    d = docx.Document(str(tmp_path / "historico.docx"))
    heads = [p.text for p in d.paragraphs if p.style.name == "Heading 1"]
    assert heads == ["1. Datos", "2. Auditoría de ingesta", "3. Preparación por nivel",
                     "4. Nivel 1: correlaciones propias del sitio", "5. Limitaciones"]
