"""Catálogo de tipos de sostenimiento de la mina (datos propios de cada operación, sin E/S).

Cada tipo lleva su código, su orden de menor a mayor exigencia y los elementos que lo componen.
Validar avisa con TableIssue y nunca bloquea; solo los datos imposibles (longitud ≤ 0, NaN,
códigos repetidos) lanzan ValueError. El catálogo es de la mina, por eso edition = None.
"""

import math
from collections.abc import Iterable
from dataclasses import dataclass

from .issues import TableIssue


def _positive(name: str, value: float) -> None:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and > 0, got {value!r}")


@dataclass(frozen=True)
class Bolt:
    kind: str
    length_m: float
    spacing_m: float

    def __post_init__(self):
        _positive("length_m", self.length_m)
        _positive("spacing_m", self.spacing_m)


@dataclass(frozen=True)
class Shotcrete:
    thickness_mm: float
    fiber: bool = False

    def __post_init__(self):
        _positive("thickness_mm", self.thickness_mm)


@dataclass(frozen=True)
class SupportType:
    code: str
    order: int
    description: str = ""
    bolt: Bolt | None = None
    shotcrete: Shotcrete | None = None
    mesh: str | None = None
    arch: str | None = None
    relative_cost: float | None = None

    def __post_init__(self):
        code = self.code.strip()
        if not code:
            raise ValueError("support code must not be empty")
        object.__setattr__(self, "code", code)
        if self.order < 1:
            raise ValueError(f"order must be >= 1, got {self.order!r}")
        if self.relative_cost is not None:
            _positive("relative_cost", self.relative_cost)

    def is_empty(self) -> bool:
        return not (self.bolt or self.shotcrete or self.mesh or self.arch)


class SupportCatalog:
    def __init__(self, types: Iterable[SupportType]):
        self._by_code: dict[str, SupportType] = {}
        for t in types:
            if t.code in self._by_code:
                raise ValueError(f"duplicate support code '{t.code}'")
            self._by_code[t.code] = t

    def get(self, code: str) -> SupportType:
        try:
            return self._by_code[code]
        except KeyError:
            raise KeyError(f"unknown support code {code!r}; valid codes: {list(self._by_code)}") from None

    def __contains__(self, code: str) -> bool:
        return code in self._by_code

    def ordered(self) -> list[SupportType]:
        return sorted(self._by_code.values(), key=lambda t: t.order)

    def __iter__(self):
        return iter(self.ordered())

    def __len__(self) -> int:
        return len(self._by_code)

    def validate(self) -> list[TableIssue]:
        issues: list[TableIssue] = []
        types = self.ordered()
        orders = [t.order for t in types]
        if orders != list(range(1, len(types) + 1)):
            issues.append(TableIssue("order_gap", f"orders {orders} are not 1..{len(types)}"))
        for o in sorted({o for o in orders if orders.count(o) > 1}):
            codes = [t.code for t in types if t.order == o]
            issues.append(TableIssue("order_tie", f"order {o} is shared by {codes}"))
        for t in types:
            if t.order > 1 and t.is_empty():
                issues.append(TableIssue("empty_type", f"support type '{t.code}' has no elements"))
        return issues
