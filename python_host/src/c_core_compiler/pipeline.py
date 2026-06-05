"""模块说明：统一封装编译各阶段，避免 CLI 和测试各自重复拼流程。"""

from __future__ import annotations

from dataclasses import dataclass

from .ast_nodes import Program
from .ir import IRProgram
from .ir_builder import IRBuilder
from .lexer import Lexer
from .optimizer import Optimizer
from .parser import Parser
from .semantic import SemanticAnalyzer
from .tokens import Token


@dataclass(slots=True)
class CompilationArtifacts:
    """保存编译过程中各阶段的关键产物，便于调试、测试和 CLI 输出。"""

    tokens: list[Token]
    program: Program
    ir_program: IRProgram
    optimized_program: IRProgram


def tokenize_source(source: str) -> list[Token]:
    """只执行词法分析。"""

    return Lexer(source).tokenize()


def parse_source(source: str) -> tuple[list[Token], Program]:
    """执行到 AST 为止，适合调试前端。"""

    tokens = tokenize_source(source)
    program = Parser(tokens).parse_program()
    return tokens, program


def compile_source(source: str) -> CompilationArtifacts:
    """按统一顺序执行第一代编译链路。"""

    tokens, program = parse_source(source)
    SemanticAnalyzer(program).analyze()
    ir_program = IRBuilder(program).build()
    optimized_program = Optimizer(ir_program).run()
    return CompilationArtifacts(tokens, program, ir_program, optimized_program)
