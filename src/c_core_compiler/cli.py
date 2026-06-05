"""模块说明：把各个编译阶段串起来，对外暴露一个小而清晰的命令行入口。"""

from __future__ import annotations

import argparse
from pathlib import Path

from .ast_nodes import format_ast
from .ir import format_ir, format_ir_dot
from .pipeline import compile_source, parse_source, tokenize_source
from .toolchain import ToolchainDriver, detect_default_target


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compile a constrained C subset.")
    parser.add_argument("input", type=Path, help="path to the source file")
    parser.add_argument("-o", "--output", type=Path, help="output executable path")
    parser.add_argument("--target", default=detect_default_target(), help="backend target name")
    parser.add_argument("--emit-tokens", action="store_true", help="print tokens and exit")
    parser.add_argument("--emit-ast", action="store_true", help="print AST and exit")
    parser.add_argument("--emit-ir", action="store_true", help="print IR and exit")
    parser.add_argument("--emit-ir-dot", action="store_true", help="print IR graph in DOT format and exit")
    parser.add_argument("--emit-c", action="store_true", help="print generated backend C and exit")
    parser.add_argument("--emit-asm", action="store_true", help="alias of --emit-c in the first generation")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    source = args.input.read_text(encoding="utf-8")

    if args.emit_tokens:
        print("\n".join(token.display() for token in tokenize_source(source)))
        return 0

    if args.emit_ast:
        _, program = parse_source(source)
        print(format_ast(program))
        return 0

    artifacts = compile_source(source)
    if args.emit_ir:
        print(format_ir(artifacts.optimized_program))
        return 0
    if args.emit_ir_dot:
        print(format_ir_dot(artifacts.optimized_program))
        return 0

    driver = ToolchainDriver(args.target)
    if args.emit_c or args.emit_asm:
        print(driver.emit_backend_text(artifacts.optimized_program))
        return 0

    if args.output is None:
        parser.error("either provide -o/--output or request an --emit-* mode")
    driver.build_executable(artifacts.optimized_program, args.output)
    return 0
