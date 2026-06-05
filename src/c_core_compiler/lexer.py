"""模块说明：把源代码字符流拆成带精确位置的 Token 序列。

当前版本在第一代整数子集的基础上，继续支持：
1. `char` 关键字；
2. 字符字面量；
3. 字符串字面量；
4. 数组和指针相关的 `[` `]` `&`。
"""

from __future__ import annotations

from dataclasses import dataclass

from .tokens import KEYWORDS, Token, TokenKind


class LexError(ValueError):
    """当词法分析器遇到无法识别的字符序列时抛出。"""


@dataclass(slots=True)
class Lexer:
    """一个刻意保持直白写法的手写词法分析器。

    这里不追求“技巧感”，而是优先保证：
    1. 读者容易顺着流程看懂；
    2. 出错时容易定位；
    3. 后续加语法特性时容易扩展。
    """

    source: str
    index: int = 0
    line: int = 1
    column: int = 1

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        while not self._at_end():
            # 每轮先跳过空白和注释，避免主流程被这些细节打断。
            self._skip_ignored_text()
            if self._at_end():
                break

            start_line = self.line
            start_column = self.column
            ch = self._peek()

            if ch.isalpha() or ch == "_":
                # 标识符和关键字共享同一套扫描规则，扫描完后再判定是不是关键字。
                text = self._scan_identifier()
                kind = KEYWORDS.get(text, TokenKind.IDENTIFIER)
                tokens.append(Token(kind, text, start_line, start_column))
                continue

            if ch.isdigit():
                text = self._scan_number()
                tokens.append(Token(TokenKind.INTEGER, text, start_line, start_column))
                continue

            if ch == "'":
                text = self._scan_char_literal()
                tokens.append(Token(TokenKind.CHAR_LITERAL, text, start_line, start_column))
                continue

            if ch == '"':
                text = self._scan_string_literal()
                tokens.append(Token(TokenKind.STRING_LITERAL, text, start_line, start_column))
                continue

            three_char = self.source[self.index : self.index + 3]
            if three_char == "...":
                self._advance()
                self._advance()
                self._advance()
                tokens.append(Token(TokenKind.ELLIPSIS, "...", start_line, start_column))
                continue

            two_char = self.source[self.index : self.index + 2]
            if two_char in {"==", "!=", "<=", ">=", "&&", "||", "->", "++", "--"}:
                # 双字符运算符必须先识别，否则会被拆成两个单字符 Token。
                self._advance()
                self._advance()
                tokens.append(Token(_DOUBLE_CHAR_TOKENS[two_char], two_char, start_line, start_column))
                continue

            if ch in _SINGLE_CHAR_TOKENS:
                self._advance()
                tokens.append(Token(_SINGLE_CHAR_TOKENS[ch], ch, start_line, start_column))
                continue

            raise LexError(f"Unexpected character {ch!r} at {start_line}:{start_column}")

        tokens.append(Token(TokenKind.EOF, "", self.line, self.column))
        return tokens

    def _skip_ignored_text(self) -> None:
        while not self._at_end():
            ch = self._peek()
            nxt = self.source[self.index : self.index + 2]

            if ch in " \t\r\n":
                self._advance()
                continue

            if nxt == "//":
                # 单行注释直接跳到换行符为止。
                while not self._at_end() and self._peek() != "\n":
                    self._advance()
                continue

            if nxt == "/*":
                # 多行注释要显式找结束标记，找不到就说明源码本身不完整。
                self._advance()
                self._advance()
                while not self._at_end() and self.source[self.index : self.index + 2] != "*/":
                    self._advance()
                if self._at_end():
                    raise LexError(f"Unterminated block comment at {self.line}:{self.column}")
                self._advance()
                self._advance()
                continue

            return

    def _scan_identifier(self) -> str:
        start = self.index
        while not self._at_end() and (self._peek().isalnum() or self._peek() == "_"):
            self._advance()
        return self.source[start:self.index]

    def _scan_number(self) -> str:
        start = self.index
        if self._peek() == "0" and self.index + 1 < len(self.source) and self.source[self.index + 1] in "xX":
            self._advance()  # '0'
            self._advance()  # 'x' or 'X'
            while not self._at_end() and self._peek() in "0123456789abcdefABCDEF":
                self._advance()
        else:
            while not self._at_end() and self._peek().isdigit():
                self._advance()
        return self.source[start:self.index]

    def _scan_char_literal(self) -> str:
        start = self.index
        self._advance()
        if self._at_end():
            raise LexError(f"Unterminated char literal at {self.line}:{self.column}")
        if self._peek() == "\\":
            self._advance()
            if self._at_end():
                raise LexError(f"Unterminated char literal at {self.line}:{self.column}")
            self._advance()
        else:
            self._advance()
        if self._at_end() or self._peek() != "'":
            raise LexError(f"Unterminated char literal at {self.line}:{self.column}")
        self._advance()
        return self.source[start:self.index]

    def _scan_string_literal(self) -> str:
        start = self.index
        self._advance()
        while not self._at_end() and self._peek() != '"':
            if self._peek() == "\\":
                self._advance()
                if self._at_end():
                    raise LexError(f"Unterminated string literal at {self.line}:{self.column}")
            if self._peek() == "\n":
                raise LexError(f"Unterminated string literal at {self.line}:{self.column}")
            self._advance()
        if self._at_end():
            raise LexError(f"Unterminated string literal at {self.line}:{self.column}")
        self._advance()
        return self.source[start:self.index]

    def _peek(self) -> str:
        return self.source[self.index]

    def _advance(self) -> str:
        ch = self.source[self.index]
        self.index += 1
        if ch == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def _at_end(self) -> bool:
        return self.index >= len(self.source)


_SINGLE_CHAR_TOKENS = {
    "(": TokenKind.LPAREN,
    ")": TokenKind.RPAREN,
    "{": TokenKind.LBRACE,
    "}": TokenKind.RBRACE,
    "[": TokenKind.LBRACKET,
    "]": TokenKind.RBRACKET,
    ",": TokenKind.COMMA,
    ";": TokenKind.SEMICOLON,
    "+": TokenKind.PLUS,
    "-": TokenKind.MINUS,
    "*": TokenKind.STAR,
    "/": TokenKind.SLASH,
    "%": TokenKind.PERCENT,
    "!": TokenKind.BANG,
    "&": TokenKind.AMPERSAND,
    "=": TokenKind.ASSIGN,
    "<": TokenKind.LT,
    ">": TokenKind.GT,
    ".": TokenKind.DOT,
}

_DOUBLE_CHAR_TOKENS = {
    "==": TokenKind.EQ,
    "!=": TokenKind.NE,
    "<=": TokenKind.LE,
    ">=": TokenKind.GE,
    "&&": TokenKind.AND,
    "||": TokenKind.OR,
    "->": TokenKind.ARROW,
    "++": TokenKind.PLUS_PLUS,
    "--": TokenKind.MINUS_MINUS,
}
