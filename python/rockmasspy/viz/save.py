"""Guardado de figuras en png, svg o pdf."""

from __future__ import annotations

import os
from pathlib import Path

from .style import _mpl

_FORMATS = ("png", "svg", "pdf")


def save_figure(fig, path: str | os.PathLike) -> Path:
    _mpl()
    path = Path(path)
    fmt = path.suffix.lower().lstrip(".")
    if fmt not in _FORMATS:
        raise ValueError(f"extension must be one of {', '.join(_FORMATS)}, got {path.suffix!r}")
    path.parent.mkdir(parents=True, exist_ok=True)
    # TrueType (42) en PDF: el texto queda editable y buscable, y las tildes no se vuelven Type 3
    from matplotlib import rc_context

    with rc_context({"pdf.fonttype": 42, "ps.fonttype": 42} if fmt == "pdf" else {}):
        fig.savefig(path, format=fmt, dpi=fig.dpi)
    return path
