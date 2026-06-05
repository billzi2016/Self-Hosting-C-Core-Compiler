"""模块说明：定义词法分析器和语法分析器共享的 Token 体系。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class TokenKind(Enum):
    """枚举当前编译器需要识别的 Token 类型。"""

    EOF = auto()
    IDENTIFIER = auto()
    INTEGER = auto()
    CHAR_LITERAL = auto()
    STRING_LITERAL = auto()

    KW_INT = auto()
    KW_CHAR = auto()
    KW_IF = auto()
    KW_ELSE = auto()
    KW_WHILE = auto()
    KW_FOR = auto()
    KW_RETURN = auto()

    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    COMMA = auto()
    SEMICOLON = auto()

    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    BANG = auto()
    AMPERSAND = auto()
    ASSIGN = auto()

    EQ = auto()
    NE = auto()
    LT = auto()
    LE = auto()
    GT = auto()
    GE = auto()
    AND = auto()
    OR = auto()


KEYWORDS = {
    "int": TokenKind.KW_INT,
    "char": TokenKind.KW_CHAR,
    "if": TokenKind.KW_IF,
    "else": TokenKind.KW_ELSE,
    "while": TokenKind.KW_WHILE,
    "for": TokenKind.KW_FOR,
    "return": TokenKind.KW_RETURN,
}


@dataclass(frozen=True, slots=True)
class Token:
    """同时保存 Token 的语义类别和精确源码位置。"""

    kind: TokenKind
    value: str
    line: int
    column: int

    def display(self) -> str:
        return f"{self.kind.name}({self.value!r})@{self.line}:{self.column}"
