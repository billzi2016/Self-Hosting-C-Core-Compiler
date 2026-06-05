"""CLI 测试：验证命令行参数和调试输出入口。"""

from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from _helpers import PROJECT_ROOT
from c_core_compiler.cli import main


class CLITests(unittest.TestCase):
    def test_emit_tokens_prints_token_stream(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_path = Path(tmp) / "sample.c"
            source_path.write_text("int main() { return 0; }", encoding="utf-8")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main([str(source_path), "--emit-tokens"])
            self.assertEqual(exit_code, 0)
            self.assertIn("KW_INT", buffer.getvalue())

    def test_emit_ast_prints_ast(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_path = Path(tmp) / "sample.c"
            source_path.write_text("int main() { return 0; }", encoding="utf-8")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main([str(source_path), "--emit-ast"])
            self.assertEqual(exit_code, 0)
            self.assertIn("FunctionDecl", buffer.getvalue())

    def test_emit_ir_prints_ir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_path = Path(tmp) / "sample.c"
            source_path.write_text("int main() { return 0; }", encoding="utf-8")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main([str(source_path), "--emit-ir"])
            self.assertEqual(exit_code, 0)
            self.assertIn("func main", buffer.getvalue())

    def test_missing_output_or_emit_mode_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_path = Path(tmp) / "sample.c"
            source_path.write_text("int main() { return 0; }", encoding="utf-8")
            with self.assertRaises(SystemExit) as ctx:
                main([str(source_path)])
            self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
