"""语法分析测试：验证 AST 结构和表达式优先级。"""

from __future__ import annotations

import unittest

from _helpers import program_from_source
from c_core_compiler import ast_nodes as ast
from c_core_compiler.parser import ParseError


class ParserTests(unittest.TestCase):
    def test_parses_function_and_return(self) -> None:
        program = program_from_source("int main() { return 1; }")
        self.assertEqual(len(program.declarations), 1)
        function = program.declarations[0]
        self.assertIsInstance(function, ast.FunctionDecl)
        self.assertEqual(function.name, "main")
        self.assertIsInstance(function.body.items[0], ast.ReturnStmt)

    def test_expression_precedence_is_preserved(self) -> None:
        program = program_from_source("int main() { return 1 + 2 * 3; }")
        return_stmt = program.declarations[0].body.items[0]
        self.assertIsInstance(return_stmt, ast.ReturnStmt)
        expr = return_stmt.value
        self.assertIsInstance(expr, ast.BinaryExpr)
        self.assertEqual(expr.operator, "+")
        self.assertIsInstance(expr.right, ast.BinaryExpr)
        self.assertEqual(expr.right.operator, "*")

    def test_parses_if_else_while_and_for(self) -> None:
        program = program_from_source(
            """
            int main() {
                int i = 0;
                while (i < 3) { i = i + 1; }
                if (i == 3) { i = i + 2; } else { i = i + 4; }
                for (i = 0; i < 2; i = i + 1) { i = i + 1; }
                return i;
            }
            """
        )
        items = program.declarations[0].body.items
        self.assertIsInstance(items[1], ast.WhileStmt)
        self.assertIsInstance(items[2], ast.IfStmt)
        self.assertIsInstance(items[3], ast.ForStmt)

    def test_parses_function_call(self) -> None:
        program = program_from_source(
            """
            int add(int a, int b) { return a + b; }
            int main() { return add(1, 2); }
            """
        )
        return_stmt = program.declarations[1].body.items[0]
        self.assertIsInstance(return_stmt.value, ast.CallExpr)
        self.assertEqual(return_stmt.value.callee, "add")

    def test_reports_missing_semicolon(self) -> None:
        with self.assertRaises(ParseError):
            program_from_source("int main() { return 1 }")


if __name__ == "__main__":
    unittest.main()
