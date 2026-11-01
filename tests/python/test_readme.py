"""Los ejemplos de tablas por labor de los README corren y imprimen lo que dicen sus comentarios."""
import contextlib
import io
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
SECCIONES = [("README.md", "## Per-labor support tables"), ("README.es.md", "## Tablas de sostenimiento por labor")]


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
