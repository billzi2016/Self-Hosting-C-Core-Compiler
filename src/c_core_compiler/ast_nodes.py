"""模块说明：定义 AST 节点，作为语法分析后的结构化表示。"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Iterable


@dataclass(slots=True)
class Node:
    line: int
    column: int


@dataclass(slots=True)
class Program(Node):
    declarations: list["TopLevelDecl"]


@dataclass(slots=True)
class CType:
    """表示一个 C 类型描述。

    - `base`: "int" / "char" / "void" / "struct" / typedef 别名
    - `pointer_level`: 指针层级，例如 `char**` 为 2
    - `array_size`: 固定长度数组大小
    - `struct_name`: 当 base=="struct" 时存储结构体 tag 名
    """

    base: str
    pointer_level: int = 0
    array_size: int | None = None
    struct_name: str | None = None


@dataclass(slots=True)
class Parameter(Node):
    ctype: CType
    name: str


@dataclass(slots=True)
class StructField(Node):
    ctype: CType
    name: str


@dataclass(slots=True)
class StructDecl(Node):
    """struct 定义，兼容三种形式：
    - struct Tag { ... };                  → tag="Tag", alias=None
    - typedef struct Tag { ... } Alias;   → tag="Tag", alias="Alias"
    - typedef struct { ... } Alias;       → tag=None,  alias="Alias"
    """
    tag: str | None
    alias: str | None
    fields: "list[StructField] | None"


@dataclass(slots=True)
class TypedefDecl(Node):
    """typedef existing_type Alias; 不带 struct 体的简单别名。"""
    ctype: CType
    alias: str


@dataclass(slots=True)
class FuncPrototype(Node):
    """函数声明（无函数体），对应 extern 或前向声明。"""
    return_type: CType
    name: str
    params: "list[Parameter]"
    is_variadic: bool = False
    is_extern: bool = False


@dataclass(slots=True)
class GlobalVarDecl(Node):
    ctype: CType
    name: str
    initializer: "Expression | None"


@dataclass(slots=True)
class FunctionDecl(Node):
    return_type: CType
    name: str
    params: list[Parameter]
    body: "Block"


TopLevelDecl = GlobalVarDecl | FunctionDecl | StructDecl | TypedefDecl | FuncPrototype


@dataclass(slots=True)
class Statement(Node):
    pass


@dataclass(slots=True)
class Block(Statement):
    items: list[Statement]


@dataclass(slots=True)
class VarDeclStmt(Statement):
    ctype: CType
    name: str
    initializer: "Expression | None"


@dataclass(slots=True)
class ExpressionStmt(Statement):
    expression: "Expression | None"


@dataclass(slots=True)
class IfStmt(Statement):
    condition: "Expression"
    then_branch: Statement
    else_branch: Statement | None


@dataclass(slots=True)
class WhileStmt(Statement):
    condition: "Expression"
    body: Statement


@dataclass(slots=True)
class ForStmt(Statement):
    init: Statement | None
    condition: "Expression | None"
    update: "Expression | None"
    body: Statement


@dataclass(slots=True)
class ReturnStmt(Statement):
    value: "Expression | None"


@dataclass(slots=True)
class BreakStmt(Statement):
    pass


@dataclass(slots=True)
class ContinueStmt(Statement):
    pass


@dataclass(slots=True)
class Expression(Node):
    pass


@dataclass(slots=True)
class IntLiteral(Expression):
    value: int


@dataclass(slots=True)
class CharLiteral(Expression):
    value: str


@dataclass(slots=True)
class StringLiteral(Expression):
    value: str


@dataclass(slots=True)
class Name(Expression):
    identifier: str


@dataclass(slots=True)
class UnaryExpr(Expression):
    operator: str
    operand: Expression


@dataclass(slots=True)
class BinaryExpr(Expression):
    operator: str
    left: Expression
    right: Expression


@dataclass(slots=True)
class CallExpr(Expression):
    callee: str
    args: list[Expression] = field(default_factory=list)


@dataclass(slots=True)
class IndexExpr(Expression):
    target: Expression
    index: Expression


@dataclass(slots=True)
class AssignExpr(Expression):
    target: Expression
    value: Expression


@dataclass(slots=True)
class CastExpr(Expression):
    """(CType)operand"""
    ctype: CType
    operand: Expression


@dataclass(slots=True)
class SizeofExpr(Expression):
    """sizeof(type) 或 sizeof(expr)，二者必有一个非 None。"""
    ctype: CType | None
    expr: "Expression | None"


@dataclass(slots=True)
class MemberExpr(Expression):
    """target.member 或 target->member"""
    target: Expression
    member: str
    arrow: bool


@dataclass(slots=True)
class PostfixIncDecExpr(Expression):
    """operand++ 或 operand--"""
    operand: Expression
    op: str


def format_ast(node: Node) -> str:
    """把 AST 渲染成稳定、可读的树形文本，便于调试和测试。"""

    return "\n".join(_format_lines(node))


def _format_lines(value: object, indent: int = 0) -> Iterable[str]:
    prefix = "  " * indent
    if isinstance(value, Node):
        yield f"{prefix}{value.__class__.__name__}"
        for item in fields(value):
            field_value = getattr(value, item.name)
            if item.name in {"line", "column"}:
                continue
            yield from _format_named(item.name, field_value, indent + 1)
        return

    if isinstance(value, list):
        yield f"{prefix}[]"
        for item in value:
            yield from _format_lines(item, indent + 1)
        return

    yield f"{prefix}{value!r}"


def _format_named(name: str, value: object, indent: int) -> Iterable[str]:
    prefix = "  " * indent
    if isinstance(value, Node):
        yield f"{prefix}{name}:"
        yield from _format_lines(value, indent + 1)
    elif isinstance(value, list):
        yield f"{prefix}{name}:"
        if not value:
            yield f"{prefix}  []"
        else:
            for item in value:
                yield from _format_lines(item, indent + 1)
    else:
        yield f"{prefix}{name}: {value!r}"
