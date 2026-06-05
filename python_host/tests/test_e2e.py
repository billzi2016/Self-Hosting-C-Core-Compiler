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

    def test_builds_and_runs_char_program(self) -> None:
        artifacts = artifacts_from_source(
            """
            int main() {
                char c = 'A';
                return c;
            }
            """
        )
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "char_case"
            ToolchainDriver(detect_default_target()).build_executable(artifacts.optimized_program, output)
            result = subprocess.run([str(output)], check=False)
            self.assertEqual(result.returncode, 65)

    def test_builds_and_runs_array_program(self) -> None:
        artifacts = artifacts_from_source(
            """
            int main() {
                int values[3];
                values[0] = 2;
                values[1] = 3;
                values[2] = values[0] + values[1];
                return values[2];
            }
            """
        )
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "array_case"
            ToolchainDriver(detect_default_target()).build_executable(artifacts.optimized_program, output)
            result = subprocess.run([str(output)], check=False)
            self.assertEqual(result.returncode, 5)

    def test_builds_and_runs_pointer_program(self) -> None:
        artifacts = artifacts_from_source(
            """
            int main() {
                int value = 9;
                int *ptr = &value;
                return *ptr;
            }
            """
        )
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "pointer_case"
            ToolchainDriver(detect_default_target()).build_executable(artifacts.optimized_program, output)
            result = subprocess.run([str(output)], check=False)
            self.assertEqual(result.returncode, 9)

    def test_builds_and_runs_string_index_program(self) -> None:
        artifacts = artifacts_from_source(
            """
            int main() {
                char *text = "hi";
                return text[1];
            }
            """
        )
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "string_case"
            ToolchainDriver(detect_default_target()).build_executable(artifacts.optimized_program, output)
            result = subprocess.run([str(output)], check=False)
            self.assertEqual(result.returncode, 105)

    def test_builtin_print_int_writes_stdout(self) -> None:
        artifacts = artifacts_from_source(
            """
            int main() {
                return print_int(7);
            }
            """
        )
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "print_case"
            ToolchainDriver(detect_default_target()).build_executable(artifacts.optimized_program, output)
            result = subprocess.run([str(output)], check=False, capture_output=True, text=True)
            self.assertEqual(result.returncode, 7)
            self.assertEqual(result.stdout, "7\n")

    def test_fibonacci_sequence_stdout_is_human_readable(self) -> None:
        artifacts = artifacts_from_source(
            """
            int fib(int n) {
                if (n < 2) {
                    return n;
                }
                return fib(n - 1) + fib(n - 2);
            }

            int main() {
                int i = 1;
                while (i <= 7) {
                    print_int(fib(i));
                    i = i + 1;
                }
                return 0;
            }
            """
        )
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "fib_sequence_case"
            ToolchainDriver(detect_default_target()).build_executable(artifacts.optimized_program, output)
            result = subprocess.run([str(output)], check=False, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "1\n1\n2\n3\n5\n8\n13\n")


if __name__ == "__main__":
    unittest.main()
