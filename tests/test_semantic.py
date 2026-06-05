"""语义分析测试：验证定义、引用和函数调用规则。"""

from __future__ import annotations

import unittest

from _helpers import program_from_source
from c_core_compiler.semantic import SemanticAnalyzer, SemanticError


def analyze(source: str) -> None:
    SemanticAnalyzer(program_from_source(source)).analyze()


class SemanticTests(unittest.TestCase):
    def test_rejects_duplicate_top_level_names(self) -> None:
        with self.assertRaises(SemanticError):
            analyze("int main() { return 0; } int main() { return 1; }")

    def test_rejects_undefined_variable(self) -> None:
        with self.assertRaises(SemanticError):
            analyze("int main() { return value; }")

    def test_rejects_undefined_function(self) -> None:
        with self.assertRaises(SemanticError):
            analyze("int main() { return missing(1); }")

    def test_rejects_wrong_argument_count(self) -> None:
        with self.assertRaises(SemanticError):
            analyze(
                """
                int add(int a, int b) { return a + b; }
                int main() { return add(1); }
                """
            )

    def test_rejects_invalid_assignment_target(self) -> None:
        with self.assertRaises(SemanticError):
            analyze("int main() { (1 + 2) = 3; return 0; }")

    def test_requires_explicit_return(self) -> None:
        with self.assertRaises(SemanticError):
            analyze("int main() { int a = 1; }")

    def test_accepts_valid_program(self) -> None:
        analyze(
            """
            int add(int a, int b) { return a + b; }
            int main() {
                int value = add(2, 3);
                return value;
            }
            """
        )

    def test_accepts_block_scope_shadowing(self) -> None:
        analyze(
            """
            int main() {
                int value = 1;
                {
                    int value = 2;
                    value = value + 1;
                }
                return value;
            }
            """
        )


if __name__ == "__main__":
    unittest.main()
