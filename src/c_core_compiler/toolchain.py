"""模块说明：调用系统工具链，把后端输出变成最终可执行文件。"""

from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .codegen import get_backend
from .ir import IRProgram


class ToolchainError(RuntimeError):
    """当外部工具链执行失败时抛出。"""


def detect_default_target() -> str:
    system = platform.system().lower()
    if system == "darwin":
        return "macos-x86_64"
    if system == "linux":
        return "linux-x86_64"
    raise ToolchainError(f"unsupported host platform: {platform.system()}")


def find_c_compiler() -> str | None:
    return shutil.which("clang") or shutil.which("cc")


@dataclass(slots=True)
class ToolchainDriver:
    """负责从 IR 到后端文本，再到可执行文件的最后一段链路。"""

    target: str

    def emit_backend_text(self, program: IRProgram) -> str:
        backend = get_backend(self.target)
        return backend.emit(program)

    def build_executable(self, program: IRProgram, output_path: Path) -> Path:
        compiler = find_c_compiler()
        if compiler is None:
            raise ToolchainError("no C compiler found; expected clang or cc")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        generated_path = output_path.with_suffix(".generated.c")
        # 先把后端结果写成独立文件，目的是便于调试失败时直接查看生成代码。
        generated_path.write_text(self.emit_backend_text(program), encoding="utf-8")

        command = [compiler, str(generated_path), "-o", str(output_path)]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            raise ToolchainError(
                "toolchain command failed:\n"
                + " ".join(command)
                + "\n"
                + completed.stderr.strip()
            )
        return output_path
