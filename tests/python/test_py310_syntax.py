import ast
import io
import sys
import tokenize
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2] / "python" / "rockmasspy"


def _nested_fstring_quotes(source: str) -> list[int]:
    """Líneas con comillas iguales anidadas dentro de un f-string (PEP 701, solo válido desde 3.12).

    Con un intérprete >= 3.12 `ast.parse(feature_version=(3, 10))` no lo detecta, por eso se mira el tokenizador.
    """
    if sys.version_info < (3, 12):
        return []  # el parser propio ya lo rechaza
    stack, bad = [], []
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.FSTRING_END:
            stack.pop()
            continue
        if tok.type in (tokenize.STRING, tokenize.FSTRING_START):
            quote = tok.string.lstrip("rbfuRBFU")[:1]
            if stack and quote == stack[-1]:
                bad.append(tok.start[0])
            if tok.type == tokenize.FSTRING_START:
                stack.append(quote)
    return bad


# El proyecto declara python >= 3.10: nada de sintaxis nueva.
@pytest.mark.parametrize("path", sorted(ROOT.rglob("*.py")), ids=lambda p: p.relative_to(ROOT).as_posix())
def test_sintaxis_python_310(path):
    source = path.read_text(encoding="utf-8")
    try:
        ast.parse(source, filename=str(path), feature_version=(3, 10))
    except SyntaxError as e:
        pytest.fail(f"{path} no es válido en Python 3.10: {e}")
    assert not _nested_fstring_quotes(source), f"{path}: comillas anidadas en f-string (solo 3.12+), líneas {_nested_fstring_quotes(source)}"
