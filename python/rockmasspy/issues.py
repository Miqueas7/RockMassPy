"""Aviso de validación de tablas: validar avisa, nunca bloquea."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TableIssue:
    kind: str
    message: str
    edition: str | None = None  # edición contra la que se comparó
