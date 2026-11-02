"""Los ejemplos de tablas por labor de los README corren y imprimen lo que dicen sus comentarios."""
import contextlib
import io
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
SECCIONES = [("README.md", "## Per-labor support tables"), ("README.es.md", "## Tablas de sostenimiento por labor")]
GRAFICOS = [("README.md", "## Per-labor support tables", "## Charts"),
            ("README.es.md", "## Tablas de sostenimiento por labor", "## Gráficos")]


def bloques(archivo, titulo):
    texto = (RAIZ / archivo).read_text(encoding="utf-8")
    seccion = texto.split(titulo, 1)[1].split("\n## ", 1)[0]
    return re.findall(r"```python\n(.*?)```", seccion, re.S)


@pytest.mark.parametrize("archivo,titulo", SECCIONES)
def test_readme_per_labor_example(archivo, titulo):
    codigo = bloques(archivo, titulo)
    assert codigo, f"{archivo}: no python block under {titulo!r}"
    for bloque in codigo:
        # cada print(...) con «# texto» debe imprimir exactamente ese texto
        esperado = [ln.split("#", 1)[1].strip() for ln in bloque.splitlines() if ln.startswith("print(") and "#" in ln]
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            exec(compile(bloque, archivo, "exec"), {})
        assert salida.getvalue().splitlines() == esperado


@pytest.mark.parametrize("archivo,previo,titulo", GRAFICOS)
def test_readme_charts_example(archivo, previo, titulo, tmp_path, monkeypatch):
    pytest.importorskip("matplotlib")
    monkeypatch.chdir(tmp_path)  # el bloque guarda figs/cartilla.png
    monkeypatch.setenv("MPLBACKEND", "Agg")
    codigo = bloques(archivo, previo) + bloques(archivo, titulo)  # el bloque de gráficos usa `labor` del anterior
    assert len(codigo) == 2, f"{archivo}: expected one block per section"
    esperado = [ln.split("#", 1)[1].strip() for ln in codigo[1].splitlines() if ln.startswith("print(") and "#" in ln]
    espacio, salida = {}, io.StringIO()
    with contextlib.redirect_stdout(salida):
        for bloque in codigo:
            exec(compile(bloque, archivo, "exec"), espacio)
    assert salida.getvalue().splitlines()[-len(esperado):] == esperado
    assert (tmp_path / "figs" / "cartilla.png").stat().st_size > 0


SALIDA = {"README.md": "report.html", "README.es.md": "informe.html"}
TRAMOS = [("README.md", "## Per-labor support tables", "## Tramos, batch, report and CLI"),
          ("README.es.md", "## Tablas de sostenimiento por labor", "## Tramos, lote, informe y CLI")]


@pytest.mark.parametrize("archivo,previo,titulo", TRAMOS)
def test_readme_tramos_example(archivo, previo, titulo, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # el bloque escribe tramos.csv y el informe
    monkeypatch.setenv("MPLBACKEND", "Agg")
    codigo = bloques(archivo, previo) + bloques(archivo, titulo)  # el bloque usa `labor` del primero
    assert len(codigo) == 2, f"{archivo}: expected one block per section"
    esperado = [ln.split("#", 1)[1].strip() for ln in codigo[1].splitlines() if ln.startswith("print(") and "#" in ln]
    espacio, salida = {}, io.StringIO()
    with contextlib.redirect_stdout(salida):
        for bloque in codigo:
            exec(compile(bloque, archivo, "exec"), espacio)
    assert salida.getvalue().splitlines()[-len(esperado):] == esperado
    assert (tmp_path / SALIDA[archivo]).is_file()


QSECCION = [("README.md", "## Q support chart (reference)"), ("README.es.md", "## Carta de sostenimiento Q (referencia)")]


@pytest.mark.parametrize("archivo,titulo", QSECCION)
def test_readme_q_chart_example(archivo, titulo):
    codigo = bloques(archivo, titulo)
    assert len(codigo) == 1, f"{archivo}: expected one python block under {titulo!r}"
    esperado = [ln.split("#", 1)[1].strip() for ln in codigo[0].splitlines() if ln.startswith("print(") and "#" in ln]
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida):
        exec(compile(codigo[0], archivo, "exec"), {})
    assert salida.getvalue().splitlines() == esperado


SSECCION = [("README.md", "## Stope stability (Mathews) and MRMR"), ("README.es.md", "## Estabilidad de tajeos (Mathews) y MRMR")]


@pytest.mark.parametrize("archivo,titulo", SSECCION)
def test_readme_stope_example(archivo, titulo):
    codigo = bloques(archivo, titulo)
    assert len(codigo) == 1, f"{archivo}: expected one python block under {titulo!r}"
    esperado = [ln.split("#", 1)[1].strip() for ln in codigo[0].splitlines() if ln.startswith("print(") and "#" in ln]
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida):
        exec(compile(codigo[0], archivo, "exec"), {})
    assert salida.getvalue().splitlines() == esperado


VSECCION = [("README.md", "## Normative verification (Peru, DS 024-2016-EM)"),
            ("README.es.md", "## Verificación normativa (Perú, DS 024-2016-EM)")]


@pytest.mark.parametrize("archivo,titulo", VSECCION)
def test_readme_verify_example(archivo, titulo):
    codigo = bloques(archivo, titulo)
    assert len(codigo) == 1, f"{archivo}: expected one python block under {titulo!r}"
    esperado = [ln.split("#", 1)[1].strip() for ln in codigo[0].splitlines() if ln.startswith("print(") and "#" in ln]
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida):
        exec(compile(codigo[0], archivo, "exec"), {})
    assert salida.getvalue().splitlines() == esperado


TSECCION = [("README.md", "## Slope kinematics, SMR and Q-slope"), ("README.es.md", "## Cinemática de taludes, SMR y Q-slope")]


@pytest.mark.parametrize("archivo,titulo", TSECCION)
def test_readme_slope_example(archivo, titulo):
    codigo = bloques(archivo, titulo)
    assert len(codigo) == 1, f"{archivo}: expected one python block under {titulo!r}"
    esperado = [ln.split("#", 1)[1].strip() for ln in codigo[0].splitlines() if ln.startswith("print(") and "#" in ln]
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida):
        exec(compile(codigo[0], archivo, "exec"), {})
    assert salida.getvalue().splitlines() == esperado
