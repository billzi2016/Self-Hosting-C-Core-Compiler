"""词法分析测试：验证 Token 分类、位置和错误处理。"""

from __future__ import annotations

import unittest

from _helpers import tokens_from_source
from c_core_compiler.lexer import LexError
from c_core_compiler.tokens import TokenKind


class LexerTests(unittest.TestCase):
    def test_keywords_identifiers_and_integer_literals(self) -> None:
        tokens = tokens_from_source("int main return foo 123")
        kinds = [token.kind for token in tokens[:-1]]
        self.assertEqual(
            kinds,
            [
                TokenKind.KW_INT,
                TokenKind.IDENTIFIER,
                TokenKind.KW_RETURN,
                TokenKind.IDENTIFIER,
                TokenKind.INTEGER,
            ],
        )

    def test_double_character_operators_are_not_split(self) -> None:
        tokens = tokens_from_source("a==b!=c<=d>=e&&f||g")
        values = [token.value for token in tokens[:-1]]
        self.assertEqual(values, ["a", "==", "b", "!=", "c", "<=", "d", ">=", "e", "&&", "f", "||", "g"])

    def test_comments_and_whitespace_are_ignored(self) -> None:
        tokens = tokens_from_source(
            """
            int main() {
                // line comment
                /* block
                   comment */
                return 1;
            }
            """
        )
        values = [token.value for token in tokens[:-1]]
        self.assertEqual(values, ["int", "main", "(", ")", "{", "return", "1", ";", "}"])

    def test_locations_are_recorded(self) -> None:
        tokens = tokens_from_source("int\n  main")
        self.assertEqual((tokens[1].line, tokens[1].column), (2, 3))

    def test_unexpected_character_raises_error(self) -> None:
        with self.assertRaises(LexError):
            tokens_from_source("@")

    def test_unterminated_block_comment_raises_error(self) -> None:
        with self.assertRaises(LexError):
            tokens_from_source("/* missing end")


if __name__ == "__main__":
    unittest.main()
