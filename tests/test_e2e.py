"""端到端测试：验证能否生成并运行真实可执行文件。"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from _helpers import artifacts_from_source, compiler_available
from c_core_compiler.toolchain import ToolchainDriver, detect_default_target


@unittest.skipUnless(compiler_available(), "本机没有可用的 clang/cc，跳过端到端测试")
class EndToEndTests(unittest.TestCase):
    def test_builds_and_runs_simple_program(self) -> None:
        artifacts = artifacts_from_source("int main() { return 7; }")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "sample"
            ToolchainDriver(detect_default_target()).build_executable(artifacts.optimized_program, output)
            result = subprocess.run([str(output)], check=False)
            self.assertEqual(result.returncode, 7)

    def test_builds_and_runs_loop_program(self) -> None:
        artifacts = artifacts_from_source(
            """
            int main() {
                int sum = 0;
                int i = 0;
                for (i = 0; i < 4; i = i + 1) {
                    sum = sum + i;
                }
                return sum;
            }
            """
        )
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "loop_case"
            ToolchainDriver(detect_default_target()).build_executable(artifacts.optimized_program, output)
            result = subprocess.run([str(output)], check=False)
            self.assertEqual(result.returncode, 6)

    def test_builds_and_runs_recursive_program(self) -> None:
        artifacts = artifacts_from_source(
            """
            int fib(int n) {
                if (n < 2) {
                    return n;
                }
                return fib(n - 1) + fib(n - 2);
            }

            int main() {
                return fib(6);
            }
            """
        )
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "fib_case"
            ToolchainDriver(detect_default_target()).build_executable(artifacts.optimized_program, output)
            result = subprocess.run([str(output)], check=False)
            self.assertEqual(result.returncode, 8)


if __name__ == "__main__":
    unittest.main()
