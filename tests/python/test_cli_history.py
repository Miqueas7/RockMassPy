"""`rockmass history`: auditoría sola, --correlations, --output, códigos 0/1/2 y el centinela ZZSENT (R12, R13)."""
import csv
import dataclasses
import functools
import json
import sys

import pytest

import rockmasspy as rm
import rockmasspy.report as rp
from rockmasspy.cli import main
from rockmasspy.table_io import correlation_from_dict

from test_batch import CAT, rmr_tab
from test_history import bloqueado

pytest.importorskip("openpyxl")
pred = pytest.importorskip("rockmasspy.predictive")

SENT = "ZZSENT"
N_BOOT = 200  # las pruebas de la CLI no miden la precisión del IC: menos réplicas que las 2000 por defecto


@pytest.fixture(scope="module")
def hist(tmp_path_factory):
    """Cada variante del histórico sintético se escribe una sola vez, como historico.xlsx en su carpeta.

    - limpio / bad_q: labor, zona y litología llevan ZZSENT; bad_q tiene un Q que no cuadra (un hallazgo q_mismatch).
    - sin_gsi: sin GSI, gsi_from_* no tienen pares. solo: un dominio de un solo par (ZZSENT-solo).
    """
    h, _ = pred.synthetic_history(n_zones=4, seed=12)
    sent = [dataclasses.replace(t, labor_codigo=f"{SENT}-{t.labor_codigo}", zona_nivel=f"{SENT}-{t.zona_nivel}",
                                litologia=f"{SENT}-{t.litologia}") for t in h.tramos]
    variantes = {"limpio": sent,
                 "bad_q": [dataclasses.replace(sent[0], q_valor=sent[0].q_valor * 3), *sent[1:]],
                 "sin_gsi": [dataclasses.replace(t, gsi_valor=None) for t in h.tramos],
                 "solo": [dataclasses.replace(h.tramos[0], litologia=f"{SENT}-solo"), *h.tramos[1:]]}
    out = {}
    for nombre, ts in variantes.items():
        p = tmp_path_factory.mktemp(nombre) / "historico.xlsx"
        rm.save_history_xlsx(rm.History(tuple(ts), h.support_types, h.inspections), p)
        out[nombre] = p
    return out


@pytest.fixture(autouse=True)
def pocas_replicas(monkeypatch):
    """La CLI importa fit_site_correlation desde .predictive al ajustar (importación diferida): se cambia ahí."""
    calls = []
    orig = pred.fit_site_correlation

    def rapido(*args, **kw):
        calls.append(kw.get("n_boot"))
        return functools.partial(orig, n_boot=N_BOOT)(*args, **kw)

    monkeypatch.setattr(pred, "fit_site_correlation", rapido)
    return calls


def sin_centinela(capsys):
    cap = capsys.readouterr()
    assert SENT not in cap.out and SENT not in cap.err
    return cap


def test_cli_uses_the_patched_fit(hist, capsys, pocas_replicas, tmp_path):
    assert main(["history", str(hist["limpio"]), "--correlations", "--report", str(tmp_path / "r.html"),
                 "--lang", "en"]) == 2
    sin_centinela(capsys)
    assert len(pocas_replicas) == 3  # los tres pares pasaron por el parche (n_boot lo pone el parche: 200)
    assert "Bootstrap by excavation (200 replicates" in (tmp_path / "r.html").read_text(encoding="utf-8")


def test_audit_only(hist, capsys):
    code = main(["history", str(hist["bad_q"])])
    out = sin_centinela(capsys).out
    assert code == 2  # un hallazgo
    assert "tramos: " in out and "findings: 1" in out and "finding: q_mismatch (1)" in out
    assert "level 1 rmr_from_q: ready (pairs " in out and "level 3 performance:" in out
    assert "correlation" not in out
    assert not any(t.startswith("T0") for t in out.split())  # ningún id_tramo


def test_audit_counts_match_history_audit_counts(hist, capsys):
    main(["history", str(hist["bad_q"])])
    out = sin_centinela(capsys).out
    c = rm.history_audit_counts(rm.audit_history(rm.load_history(hist["bad_q"])))
    assert f"tramos: {c['tramos']}\nsupport types: {c['support_types']}\ninspections: {c['inspections']}\n" in out
    assert f"findings: {c['findings']}\n" in out


def test_audit_clean_exit_0(hist, capsys):
    assert main(["history", str(hist["limpio"])]) == 0
    assert "findings: 0" in sin_centinela(capsys).out


def test_correlations_lines_and_exit(hist, capsys):
    code = main(["history", str(hist["limpio"]), "--correlations"])
    out = sin_centinela(capsys).out
    for kind in pred.KINDS:
        assert f"correlation {kind} mine: n " in out and f"correlation {kind} D1: " in out
        assert f"prior {kind}: " in out
    assert "not_calibrated" in out  # semilla 12: D3 tiene 3 labores
    assert code == 2
    for lit in pred.synthetic.LITHOLOGIES:
        assert lit not in out


def test_correlations_all_site_exit_0(hist, capsys):
    code = main(["history", str(hist["limpio"]), "--correlations", "--group-by", "none"])
    out = sin_centinela(capsys).out
    assert out.count(", site, a ") == 3 and " D1:" not in out
    assert code == 0


def _csv(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.reader(fh))


def test_output_files(hist, capsys, tmp_path):
    out_dir = tmp_path / f"{SENT}-salida"  # la carpeta protegida puede llevar el nombre de la mina
    code = main(["history", str(hist["bad_q"]), "--correlations", "--output", str(out_dir)])
    out = sin_centinela(capsys).out
    assert code == 2
    assert [x for x in out.splitlines() if x.startswith("results: ")] == [
        "results: history_findings.csv", "results: site_correlations.csv", "results: site_correlations.json"]
    rows = _csv(out_dir / "history_findings.csv")
    assert tuple(rows[0]) == rm.FINDING_RESULT_COLUMNS
    assert rows[1][:4] == ["q_mismatch", "Tramos", "2", "T0001"]  # el id_tramo y la fila sí van en el archivo
    fits = _csv(out_dir / "site_correlations.csv")
    assert tuple(fits[0]) == pred.CORRELATION_RESULT_COLUMNS
    assert SENT in "".join(map(str, fits))  # el dominio va en el archivo de resultados
    estado = fits[0].index("estado")
    site = [r for r in fits[1:] if r[estado] == "site"]
    assert "not_calibrated" in {r[estado] for r in fits[1:]}  # D3: sigue en el CSV con su estado
    js = json.loads((out_dir / "site_correlations.json").read_text(encoding="utf-8"))
    assert SENT not in json.dumps(js)  # el JSON va a una tabla por labor: solo etiquetas
    # solo los ajustes «sitio»: los inestables y los no calibrados no se pegan en una tabla
    assert len(js["correlations"]) == len(site) and all("status=site" in c["source"] for c in js["correlations"])
    corrs = [correlation_from_dict(c) for c in js["correlations"]]
    assert {c.name for c in corrs} >= {f"{k}_mine" for k in pred.KINDS}
    # se enchufa en una tabla por labor: la tabla lo valida al cargar
    d = rm.to_dict(rm.LaborTable("galería", CAT, rmr_tab()))
    d["correlations"] = js["correlations"]
    assert len(rm.from_dict(d).correlations) == len(corrs)


def test_report_without_sentinel(hist, capsys, tmp_path):
    docx = pytest.importorskip("docx")
    carpeta = tmp_path / f"{SENT}-informes"
    carpeta.mkdir()
    rep, html = carpeta / "informe.docx", carpeta / "informe.html"
    src = hist["bad_q"]
    assert main(["history", str(src), "--correlations", "--report", str(rep)]) == 2
    assert main(["history", str(src), "--correlations", "--report", str(html), "--lang", "en"]) == 2
    out = sin_centinela(capsys).out  # la carpeta lleva ZZSENT: solo sale el nombre del informe
    assert "report: informe.docx" in out and "report: informe.html" in out
    d = docx.Document(str(rep))
    texto = "\n".join([p.text for p in d.paragraphs]
                      + [c.text for tb in d.tables for row in tb.rows for c in row.cells])
    assert SENT not in texto and "historico" not in texto.lower()
    assert "T0001" in texto  # el id_tramo del hallazgo, en su tabla
    h = html.read_text(encoding="utf-8")
    assert SENT not in h and "historico.xlsx" not in h and "Level 1" in h


def test_errors_exit_1(hist, tmp_path, capsys):
    src = str(hist["limpio"])
    assert main(["history", str(tmp_path / f"{SENT}.xlsx")]) == 1
    assert main(["history", src, "--report", "x.pdf"]) == 1
    assert main(["history", src, "--group-by", SENT]) == 1
    assert main(["history", src, "--deming-ratio", "1"]) == 1
    assert main(["history", src, "--correlations", "--deming-ratio", "0"]) == 1
    cap = sin_centinela(capsys)
    assert cap.out == "" and cap.err.count("error: ") == 5


def test_outputs_checked_before_reading(hist, tmp_path, capsys, monkeypatch):
    """--report sin carpeta y --output que es un archivo fallan con 1 antes de leer el histórico, sin la ruta."""
    def no_leer(*a, **k):
        raise AssertionError("the history was read before checking the outputs")

    monkeypatch.setattr(rm.history, "load_history", no_leer)
    archivo = tmp_path / f"{SENT}.csv"
    archivo.write_text("x", encoding="utf-8")
    assert main(["history", str(hist["limpio"]), "--correlations", "-o", str(archivo)]) == 1
    assert main(["history", str(hist["limpio"]), "--report", str(tmp_path / SENT / "informe.html")]) == 1
    cap = sin_centinela(capsys)
    assert cap.out == "" and cap.err.splitlines() == ["error: --output must be a folder, not a file",
                                                      "error: --report: its folder does not exist"]


def test_locked_history_exit_1(hist, tmp_path, capsys):
    """Abierto en exclusiva (como Excel): una línea sin la ruta, que puede llevar el nombre de la mina."""
    p = tmp_path / f"{SENT}-mina.xlsx"
    p.write_bytes(hist["limpio"].read_bytes())
    with bloqueado(p):
        assert main(["history", str(p)]) == 1
    cap = sin_centinela(capsys)
    assert cap.out == "" and cap.err == "error: history file could not be read (in use or no permission)\n"


def test_locked_result_exit_1(hist, tmp_path, capsys):
    """Un resultado abierto en Excel al reescribirlo: código 1 y una línea sin la ruta."""
    out_dir = tmp_path / f"{SENT}-salida"
    out_dir.mkdir()
    (out_dir / "history_findings.csv").write_text("x", encoding="utf-8")
    with bloqueado(out_dir / "history_findings.csv"):
        assert main(["history", str(hist["limpio"]), "-o", str(out_dir)]) == 1
    cap = sin_centinela(capsys)
    assert cap.err == "error: results or report could not be written (in use or no permission)\n"


def test_deming_ratio(hist, tmp_path, capsys):
    out_dir = tmp_path / "o"
    main(["history", str(hist["limpio"]), "--correlations", "--group-by", "none", "--deming-ratio", "1",
          "-o", str(out_dir)])
    sin_centinela(capsys)
    assert (out_dir / "site_correlations.csv").exists()


def test_not_fitted_kind(hist, tmp_path, capsys):
    """Sin GSI no hay pares para gsi_from_*: la línea lo dice, el resto sigue y el código es 2."""
    out_dir = tmp_path / "o"
    assert main(["history", str(hist["sin_gsi"]), "--correlations", "--group-by", "none", "-o", str(out_dir)]) == 2
    out = capsys.readouterr().out
    assert "correlation gsi_from_rmr: not fitted (gsi_from_rmr: no usable pairs with rmr_edicion RMR76 or RMR89 in the history)" in out
    assert "correlation rmr_from_q mine: " in out
    assert "not_fitted" in (out_dir / "site_correlations.csv").read_text(encoding="utf-8-sig")


def test_missing_ml_extra(hist, capsys, monkeypatch):
    src = hist["limpio"]
    for name in [m for m in sys.modules if m == "rockmasspy.predictive" or m.startswith("rockmasspy.predictive.")]:
        monkeypatch.delitem(sys.modules, name)
    monkeypatch.setitem(sys.modules, "numpy", None)
    assert main(["history", str(src)]) == 0  # la auditoría sola no necesita numpy
    capsys.readouterr()
    assert main(["history", str(src), "--correlations"]) == 1
    cap = capsys.readouterr()
    assert "pip install rockmasspy[ml]" in cap.err and cap.out == ""


def test_single_pair_domain_skipped_in_json(hist, tmp_path, capsys):
    """Un dominio de un solo par no tiene rango de validez ni es «sitio»: va al CSV, pero no al JSON."""
    out_dir = tmp_path / "o"
    assert main(["history", str(hist["solo"]), "--correlations", "-o", str(out_dir)]) == 2
    sin_centinela(capsys)
    js = json.loads((out_dir / "site_correlations.json").read_text(encoding="utf-8"))
    csv_text = (out_dir / "site_correlations.csv").read_text(encoding="utf-8-sig")
    assert csv_text.count(f"{SENT}-solo") == 3  # una fila por par
    assert js["correlations"] and all("n=1," not in c["source"] for c in js["correlations"])


# ---------- niveles 2 y 3: --practice, --performance, --model-output ----------

@pytest.fixture(scope="module")
def grande(tmp_path_factory):
    """Histórico grande con efecto del sitio (el nivel 3 queda «site»), con ZZSENT en labor, zona y litología."""
    h, _ = pred.synthetic_history(seed=0, n_zones=8, labors_per_zone=12, tramos_per_labor=15)
    ts = [dataclasses.replace(t, labor_codigo=f"{SENT}-{t.labor_codigo}", zona_nivel=f"{SENT}-{t.zona_nivel}",
                              litologia=f"{SENT}-{t.litologia}") for t in h.tramos]
    p = tmp_path_factory.mktemp("grande") / "historico.xlsx"
    rm.save_history_xlsx(rm.History(tuple(ts), h.support_types, h.inspections), p)
    return p


@pytest.fixture
def niveles_rapidos(monkeypatch):
    """La CLI llama a predictive.audit_practice y predictive.fit_performance al correr: se cambian ahí."""
    calls = []
    for name in ("audit_practice", "fit_performance"):
        orig = getattr(pred, name)

        def rapido(*args, _orig=orig, _name=name, **kw):
            calls.append(_name)
            return _orig(*args, **{**kw, "n_boot": N_BOOT})

        monkeypatch.setattr(pred, name, rapido)
    return calls


def test_practice_and_performance_site_exit_0(grande, tmp_path, capsys, niveles_rapidos):
    out_dir, modelo, informe = tmp_path / f"{SENT}-res", tmp_path / "modelo.json", tmp_path / "informe.html"
    code = main(["history", str(grande), "--practice", "--performance", "-o", str(out_dir),
                 "--model-output", str(modelo), "--report", str(informe), "--lang", "en",
                 "--threshold", "0.3", "--exposure-days", "200"])
    out = sin_centinela(capsys).out
    assert niveles_rapidos == ["audit_practice", "fit_performance"]
    rb = rp.recommendation_blockers(pred.load_model(modelo))
    assert code == (2 if rb else 0), out  # «site» pero recommend no elegiría: hay que revisar
    assert "practice ln_q: coherent (beta " in out and "practice ln_de: coherent (beta " in out
    assert "practice consistency: consistent (share of tramos given another type at the centre of a " in out
    assert "practice kappa labor: practice " in out and "over ngi " in out and "blockers 0" in out
    assert "practice outside the conformal set: " in out and "practice concordance: n " in out
    assert ("performance: calibration site, but recommend will not choose: " if rb
            else "performance: calibration site (") in out
    assert ("performance model: constant failure rate with a gamma frailty per excavation; P(failure in H days) "
            "for a new excavation = 1 - (1 + theta*lambda*H)^(-1/theta)") in out
    assert "performance poisson_deviance labor: site " in out and "over baseline_ngi " in out
    assert "performance poisson_deviance temporal: " in out and "non-inferiority" in out
    assert "performance coefficient ln_q: " in out and "performance coefficient support_rank: " in out
    # revisión final (I4): la regla vigente, la forma, σ_z con su cota y las compuertas (a) y (d)
    assert "the decision bound is 1 - exp(-lambda_up*H*Z_q), with lambda_up = exp(eta + q*sqrt(se^2 + " \
           "sigma_z_up^2))" in out
    assert "performance form: " in out and "performance new zone: sigma_z estimate " in out
    assert "one-sided upper bound used " in out and "(8 zones)" in out
    assert "performance worst third of rock quality (ln_q <= " in out and "out-of-fold observed/expected " in out
    assert "performance failures by tipo_labor: " in out and "(no choice with fewer than 10)" in out
    assert not any(w.startswith("T0") for w in out.split())  # ningún id_tramo
    assert [x for x in out.splitlines() if x.startswith(("results: ", "model: "))] == [
        "results: history_findings.csv", "results: practice_results.csv", "results: validation_summary.csv",
        "model: modelo.json"]
    prac = _csv(out_dir / "practice_results.csv")
    assert tuple(prac[0]) == pred.PRACTICE_RESULT_COLUMNS and prac[1][0].startswith("T0")  # el id sí va al archivo
    val = _csv(out_dir / "validation_summary.csv")
    assert {r[0] for r in val[1:]} == {"2", "3"} and {"labor", "zone", "temporal"} <= {r[1] for r in val[1:]}
    js = modelo.read_text(encoding="utf-8")
    assert SENT not in js and "T0" not in js
    assert pred.load_model(modelo).calibration == "site"
    html = informe.read_text(encoding="utf-8")
    assert SENT not in html and "historico.xlsx" not in html
    assert "Level 2" in html and "Level 3" in html and "TRIPOD+AI" in html
    assert "set by the engineer: P(failure) ≤ 0.3" in html and "at 200 days of exposure" in html


class _ConBloqueos:
    """El modelo real con un motivo global para que recommend no elija (el campo puede no existir todavía)."""
    recommendation_blockers = ("support effect not significant",)

    def __init__(self, m):
        self._m = m

    def __getattr__(self, name):
        return getattr(self._m, name)


def test_site_with_recommendation_blockers_exit_2(grande, tmp_path, capsys, monkeypatch):
    orig = pred.fit_performance
    monkeypatch.setattr(pred, "fit_performance", lambda *a, **k: _ConBloqueos(orig(*a, **{**k, "n_boot": N_BOOT})))
    informe = tmp_path / "informe.html"
    code = main(["history", str(grande), "--performance", "--report", str(informe), "--lang", "en"])
    out = sin_centinela(capsys).out
    assert code == 2
    assert "performance: calibration site, but recommend will not choose: support effect not significant" in out
    html = informe.read_text(encoding="utf-8")
    assert "recommend will not choose any type with this model" in html and "support effect not significant" in html


def test_small_history_levels_exit_2(hist, capsys, niveles_rapidos):
    """Con unos 250 tramos el nivel 3 no queda «site»: código 2 aunque la auditoría esté limpia."""
    code = main(["history", str(hist["limpio"]), "--practice", "--performance", "--quality", "rmr"])
    out = sin_centinela(capsys).out
    assert code == 2
    assert "practice: n " in out and "performance: calibration " in out
    assert "performance: calibration site" not in out and "quality rmr" in out


def test_level_options_checked_before_reading(hist, tmp_path, capsys, monkeypatch):
    def no_leer(*a, **k):
        raise AssertionError("the history was read before checking the options")

    monkeypatch.setattr(rm.history, "load_history", no_leer)
    src = str(hist["limpio"])
    assert main(["history", src, "--quality", "q"]) == 1
    assert main(["history", src, "--model-output", "m.json"]) == 1
    assert main(["history", src, "--performance", "--model-output", str(tmp_path / f"{SENT}.txt")]) == 1
    assert main(["history", src, "--performance", "--model-output", str(tmp_path / SENT / "m.json")]) == 1
    assert main(["history", src, "--performance", "--quality", "gsi"]) == 1
    assert main(["history", src, "--threshold", "0.3"]) == 1
    assert main(["history", src, "--exposure-days", "100"]) == 1
    assert main(["history", src, "--performance", "--threshold", "1"]) == 1
    assert main(["history", src, "--performance", "--exposure-days", "0"]) == 1
    cap = sin_centinela(capsys)
    assert cap.out == ""
    assert cap.err.splitlines() == [
        "error: --quality needs --performance", "error: --model-output needs --performance",
        "error: --model-output must end in .json", "error: --model-output: its folder does not exist",
        "error: --quality must be one of q, rmr", "error: --threshold needs --performance",
        "error: --exposure-days needs --performance",
        "error: --threshold must be a probability strictly between 0 and 1",
        "error: --exposure-days must be greater than 0"]


def test_model_output_refused_below_100_tramos(tmp_path, capsys, niveles_rapidos):
    """Con menos de 100 tramos usables, save_model se niega (los resúmenes casi reconstruyen las filas): código 1,
    un mensaje claro, sin la ruta, y ningún archivo."""
    h, _ = pred.synthetic_history(seed=1, n_zones=2, labors_per_zone=3, tramos_per_labor=5)
    folder = tmp_path / f"{SENT}-chico"
    folder.mkdir()
    rm.save_history_xlsx(h, folder / "historico.xlsx")
    modelo = folder / "modelo.json"
    code = main(["history", str(folder / "historico.xlsx"), "--performance", "--model-output", str(modelo)])
    cap = sin_centinela(capsys)
    assert code == 1 and not modelo.exists()
    err = cap.err.strip().splitlines()[-1]
    assert err.startswith("error: the model was fitted with fewer than 100 usable tramos")
    assert "modelo.json" not in cap.err and str(tmp_path) not in cap.err
