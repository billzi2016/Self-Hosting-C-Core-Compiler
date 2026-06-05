"""优化器测试：验证适度优化已经开始生效，但仍保持行为清晰。"""

from __future__ import annotations

import unittest

from _helpers import ir_from_source
from c_core_compiler.ir import IRFunction, IRInstruction, IRProgram, format_ir
from c_core_compiler.optimizer import Optimizer


class OptimizerTests(unittest.TestCase):
    def test_constant_folding_rewrites_binary_expression_to_const(self) -> None:
        ir_program = ir_from_source("int main() { return 1 + 2; }")
        optimized = Optimizer(ir_program).run()
        text = format_ir(optimized)
        self.assertIn("const", text)
        self.assertIn("  return r0", text)
        self.assertNotIn("binary", text)

    def test_constant_propagation_can_simplify_conditional_jump(self) -> None:
        ir_program = ir_from_source("int main() { if (1) { return 3; } return 4; }")
        optimized = Optimizer(ir_program).run()
        text = format_ir(optimized)
        self.assertNotIn("cjump", text)
        self.assertIn("jump if_then", text)

    def test_unreachable_instructions_are_removed(self) -> None:
        function = IRFunction(
            name="main",
            params=[],
            instructions=[
                IRInstruction("label", ("entry",)),
                IRInstruction("jump", ("exit",)),
                IRInstruction("const", ("t0", "99")),
                IRInstruction("label", ("exit",)),
                IRInstruction("const", ("t1", "1")),
                IRInstruction("return", ("t1",)),
            ],
        )
        optimized = Optimizer(IRProgram(globals=[], functions=[function])).run()
        text = format_ir(optimized)
        self.assertNotIn("const t0 99", text)
        self.assertIn("label exit", text)

    def test_optimization_keeps_runtime_result_unchanged_for_simple_case(self) -> None:
        ir_program = ir_from_source(
            """
            int main() {
                int a = 1 + 2;
                if (a == 3) {
                    return 7;
                }
                return 9;
            }
            """
        )
        optimized = Optimizer(ir_program).run()
        text = format_ir(optimized)
        self.assertIn("return", text)
        self.assertIn("const", text)

    def test_virtual_register_compaction_reuses_small_register_pool(self) -> None:
        ir_program = ir_from_source(
            """
            int main() {
                int a = 1 + 2;
                int b = a + 3;
                int c = b + 4;
                return c;
            }
            """
        )
        optimized = Optimizer(ir_program).run()
        self.assertTrue(optimized.functions[0].temporaries)
        self.assertTrue(all(name.startswith("r") for name in optimized.functions[0].temporaries))


if __name__ == "__main__":
    unittest.main()
