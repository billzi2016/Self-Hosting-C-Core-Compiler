"""后端测试：验证生成代码具备稳定结构和关键语义。"""

from __future__ import annotations

import unittest

from _helpers import artifacts_from_source
from c_core_compiler.toolchain import ToolchainDriver


class CodegenTests(unittest.TestCase):
    def test_generated_c_contains_function_header_and_return(self) -> None:
        artifacts = artifacts_from_source("int main() { return 7; }")
        text = ToolchainDriver("macos-x86_64").emit_backend_text(artifacts.optimized_program)
        self.assertIn("int main(void)", text)
        self.assertIn("return", text)

    def test_generated_c_contains_labels_for_control_flow(self) -> None:
        artifacts = artifacts_from_source(
            """
            int main() {
                int a = 0;
                while (a < 2) { a = a + 1; }
                return a;
            }
            """
        )
        text = ToolchainDriver("linux-x86_64").emit_backend_text(artifacts.optimized_program)
        self.assertIn("while_cond", text)
        self.assertIn("goto", text)

    def test_generated_c_keeps_globals_visible(self) -> None:
        artifacts = artifacts_from_source(
            """
            int seed = 3;
            int main() { return seed; }
            """
        )
        text = ToolchainDriver("linux-x86_64").emit_backend_text(artifacts.optimized_program)
        self.assertIn("int seed = 3;", text)

    def test_generated_c_for_advanced_features_uses_ast_backend(self) -> None:
        artifacts = artifacts_from_source(
            """
            int main() {
                char *text = "hi";
                return text[1];
            }
            """
        )
        text = ToolchainDriver("macos-x86_64").emit_backend_text(artifacts.optimized_program)
        self.assertIn("AST backend", text)
        self.assertIn('char* text = "hi";', text)


if __name__ == "__main__":
    unittest.main()
