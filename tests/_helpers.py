"""测试辅助模块：统一提供导入路径和常用编译辅助函数。"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from c_core_compiler.ast_nodes import Program
from c_core_compiler.ir import IRProgram
from c_core_compiler.pipeline import CompilationArtifacts, compile_source, parse_source, tokenize_source


def artifacts_from_source(source: str) -> CompilationArtifacts:
    return compile_source(source)


def tokens_from_source(source: str):
    return tokenize_source(source)


def program_from_source(source: str) -> Program:
    _, program = parse_source(source)
    return program


def ir_from_source(source: str) -> IRProgram:
    return compile_source(source).optimized_program


def compiler_available() -> bool:
    return shutil.which("clang") is not None or shutil.which("cc") is not None
