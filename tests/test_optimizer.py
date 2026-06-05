"""优化器测试：第一代先验证接口稳定和行为保守。"""

from __future__ import annotations

import unittest

from _helpers import ir_from_source
from c_core_compiler.optimizer import Optimizer


class OptimizerTests(unittest.TestCase):
    def test_first_generation_optimizer_is_noop(self) -> None:
        ir_program = ir_from_source("int main() { return 1 + 2; }")
        optimized = Optimizer(ir_program).run()
        self.assertIs(optimized, ir_program)


if __name__ == "__main__":
    unittest.main()
