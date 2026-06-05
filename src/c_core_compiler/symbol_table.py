"""模块说明：提供一个小而清晰的作用域栈，供语义分析阶段使用。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Symbol:
    name: str
    kind: str
    arity: int | None = None


@dataclass(slots=True)
class Scope:
    symbols: dict[str, Symbol] = field(default_factory=dict)


class SymbolTable:
    """保持作用域操作足够直白，避免过度抽象。"""

    def __init__(self) -> None:
        self._scopes: list[Scope] = [Scope()]

    def push(self) -> None:
        self._scopes.append(Scope())

    def pop(self) -> None:
        self._scopes.pop()

    def define(self, symbol: Symbol) -> bool:
        scope = self._scopes[-1]
        if symbol.name in scope.symbols:
            return False
        scope.symbols[symbol.name] = symbol
        return True

    def lookup(self, name: str) -> Symbol | None:
        for scope in reversed(self._scopes):
            if name in scope.symbols:
                return scope.symbols[name]
        return None

    def contains_in_current_scope(self, name: str) -> bool:
        return name in self._scopes[-1].symbols
