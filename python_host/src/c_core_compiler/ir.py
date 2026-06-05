"""模块说明：定义前端和后端之间使用的简洁 IR。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class IRGlobal:
    name: str
    initializer: int | None


@dataclass(slots=True)
class IRInstruction:
    opcode: str
    args: tuple[str, ...]


@dataclass(slots=True)
class IRFunction:
    name: str
    params: list[str]
    locals: list[str] = field(default_factory=list)
    temporaries: list[str] = field(default_factory=list)
    instructions: list[IRInstruction] = field(default_factory=list)


@dataclass(slots=True)
class IRProgram:
    globals: list[IRGlobal]
    functions: list[IRFunction]
    source_program: object | None = None
    requires_ast_backend: bool = False


def format_ir(program: IRProgram) -> str:
    """把 IR 渲染成稳定文本，方便测试快照和人工检查。"""

    if program.requires_ast_backend:
        return "high_level_program: uses AST backend for advanced language features"

    lines: list[str] = []
    for global_var in program.globals:
        if global_var.initializer is None:
            lines.append(f"global {global_var.name}")
        else:
            lines.append(f"global {global_var.name} = {global_var.initializer}")
    for function in program.functions:
        lines.append(f"func {function.name}({', '.join(function.params)})")
        if function.locals:
            lines.append(f"  locals: {', '.join(function.locals)}")
        if function.temporaries:
            lines.append(f"  temps: {', '.join(function.temporaries)}")
        for instruction in function.instructions:
            lines.append(f"  {instruction.opcode} {' '.join(instruction.args)}".rstrip())
    return "\n".join(lines)


def format_ir_dot(program: IRProgram) -> str:
    """把 IR 渲染成 Graphviz DOT，便于可视化查看控制流。"""

    lines = ["digraph IR {", "  rankdir=LR;", '  node [shape=box fontname="Menlo"];']
    for function in program.functions:
        lines.append(f'  subgraph cluster_{function.name} {{')
        lines.append(f'    label="{function.name}";')
        labels = [instruction.args[0] for instruction in function.instructions if instruction.opcode == "label"]
        for label in labels:
            lines.append(f'    "{function.name}:{label}" [label="{label}"];')

        previous_label: str | None = None
        for instruction in function.instructions:
            if instruction.opcode == "label":
                previous_label = instruction.args[0]
                continue
            if previous_label is None:
                continue
            if instruction.opcode == "jump":
                lines.append(f'    "{function.name}:{previous_label}" -> "{function.name}:{instruction.args[0]}";')
            elif instruction.opcode == "cjump":
                lines.append(
                    f'    "{function.name}:{previous_label}" -> "{function.name}:{instruction.args[1]}" [label="true"];'
                )
                lines.append(
                    f'    "{function.name}:{previous_label}" -> "{function.name}:{instruction.args[2]}" [label="false"];'
                )
        lines.append("  }")
    lines.append("}")
    return "\n".join(lines)
