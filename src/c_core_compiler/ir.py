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


def format_ir(program: IRProgram) -> str:
    """把 IR 渲染成稳定文本，方便测试快照和人工检查。"""

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
