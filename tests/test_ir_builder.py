"""IR 测试：验证控制流和调用在中间层中的展开形式。"""

from __future__ import annotations

import unittest

from _helpers import ir_from_source
from c_core_compiler.ir import format_ir


class IRBuilderTests(unittest.TestCase):
    def test_if_and_while_emit_labels_and_jumps(self) -> None:
        ir_program = ir_from_source(
            """
            int main() {
                int a = 0;
                while (a < 3) {
                    if (a == 1) { a = a + 2; } else { a = a + 1; }
                }
                return a;
            }
            """
        )
        text = format_ir(ir_program)
        self.assertIn("cjump", text)
        self.assertIn("while_cond", text)
        self.assertIn("if_then", text)
        self.assertIn("if_end", text)

    def test_for_loop_emits_cond_body_and_update_labels(self) -> None:
        ir_program = ir_from_source(
            """
            int main() {
                int i = 0;
                for (i = 0; i < 2; i = i + 1) {
                    i = i + 1;
                }
                return i;
            }
            """
        )
        text = format_ir(ir_program)
        self.assertIn("for_cond", text)
        self.assertIn("for_body", text)
        self.assertIn("for_update", text)
        self.assertIn("for_end", text)

    def test_function_call_and_return_are_visible_in_ir(self) -> None:
        ir_program = ir_from_source(
            """
            int add(int a, int b) { return a + b; }
            int main() { return add(1, 2); }
            """
        )
        text = format_ir(ir_program)
        self.assertIn("call", text)
        self.assertIn("return", text)

    def test_short_circuit_logic_emits_conditional_jumps(self) -> None:
        ir_program = ir_from_source(
            """
            int main() {
                int a = 1;
                int b = 0;
                return a && b || a;
            }
            """
        )
        text = format_ir(ir_program)
        self.assertGreaterEqual(text.count("cjump"), 2)


if __name__ == "__main__":
    unittest.main()
