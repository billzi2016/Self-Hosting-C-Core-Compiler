"""模块说明：把 AST 显式下降为以标签和跳转为核心的 IR。"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import ast_nodes as ast
from .ir import IRFunction, IRGlobal, IRInstruction, IRProgram
from .semantic import _evaluate_binary


@dataclass(slots=True)
class IRBuilder:
    program: ast.Program
    current: IRFunction = field(init=False)
    temp_index: int = field(init=False, default=0)
    label_index: int = field(init=False, default=0)
    local_names: set[str] = field(init=False, default_factory=set)
    global_names: set[str] = field(init=False, default_factory=set)

    def build(self) -> IRProgram:
        if _requires_ast_backend(self.program):
            return IRProgram(globals=[], functions=[], source_program=self.program, requires_ast_backend=True)

        globals_out: list[IRGlobal] = []
        functions_out: list[IRFunction] = []
        self.global_names = {
            decl.name for decl in self.program.declarations if isinstance(decl, ast.GlobalVarDecl)
        }
        for decl in self.program.declarations:
            if isinstance(decl, ast.GlobalVarDecl):
                initializer = self._const_eval(decl.initializer) if decl.initializer is not None else None
                globals_out.append(IRGlobal(decl.name, initializer))
            else:
                functions_out.append(self._build_function(decl))
        return IRProgram(globals_out, functions_out, source_program=self.program, requires_ast_backend=False)

    def _build_function(self, function: ast.FunctionDecl) -> IRFunction:
        self.current = IRFunction(function.name, [param.name for param in function.params])
        self.temp_index = 0
        self.label_index = 0
        self.local_names = {param.name for param in function.params}
        # 统一从入口标签开始，方便后续做控制流分析或插入优化。
        self._emit("label", f"fn_{function.name}_entry")
        self._visit_stmt(function.body)
        if not self.current.instructions or self.current.instructions[-1].opcode != "return":
            zero = self._emit_const(0)
            self._emit("return", zero)
        return self.current

    def _visit_stmt(self, stmt: ast.Statement) -> None:
        if isinstance(stmt, ast.Block):
            for item in stmt.items:
                self._visit_stmt(item)
            return
        if isinstance(stmt, ast.VarDeclStmt):
            self._declare_local(stmt.name)
            if stmt.initializer is not None:
                value = self._visit_expr(stmt.initializer)
                self._emit("store", stmt.name, value)
            return
        if isinstance(stmt, ast.ExpressionStmt):
            if stmt.expression is not None:
                self._visit_expr(stmt.expression)
            return
        if isinstance(stmt, ast.IfStmt):
            cond = self._visit_expr(stmt.condition)
            then_label = self._new_label("if_then")
            else_label = self._new_label("if_else") if stmt.else_branch is not None else None
            end_label = self._new_label("if_end")
            # 条件分支在 IR 里都显式拆成 cjump + label + jump，
            # 这样后端无需再猜语义结构。
            self._emit("cjump", cond, then_label, else_label or end_label)
            self._emit("label", then_label)
            self._visit_stmt(stmt.then_branch)
            self._emit("jump", end_label)
            if stmt.else_branch is not None:
                self._emit("label", else_label)
                self._visit_stmt(stmt.else_branch)
                self._emit("jump", end_label)
            self._emit("label", end_label)
            return
        if isinstance(stmt, ast.WhileStmt):
            cond_label = self._new_label("while_cond")
            body_label = self._new_label("while_body")
            end_label = self._new_label("while_end")
            self._emit("jump", cond_label)
            self._emit("label", cond_label)
            cond = self._visit_expr(stmt.condition)
            self._emit("cjump", cond, body_label, end_label)
            self._emit("label", body_label)
            self._visit_stmt(stmt.body)
            self._emit("jump", cond_label)
            self._emit("label", end_label)
            return
        if isinstance(stmt, ast.ForStmt):
            if stmt.init is not None:
                self._visit_stmt(stmt.init)
            cond_label = self._new_label("for_cond")
            body_label = self._new_label("for_body")
            update_label = self._new_label("for_update")
            end_label = self._new_label("for_end")
            # for 被统一展开成四段：init / cond / body / update。
            self._emit("jump", cond_label)
            self._emit("label", cond_label)
            if stmt.condition is None:
                always = self._emit_const(1)
                self._emit("cjump", always, body_label, end_label)
            else:
                cond = self._visit_expr(stmt.condition)
                self._emit("cjump", cond, body_label, end_label)
            self._emit("label", body_label)
            self._visit_stmt(stmt.body)
            self._emit("label", update_label)
            if stmt.update is not None:
                self._visit_expr(stmt.update)
            self._emit("jump", cond_label)
            self._emit("label", end_label)
            return
        if isinstance(stmt, ast.ReturnStmt):
            value = self._visit_expr(stmt.value) if stmt.value is not None else self._emit_const(0)
            self._emit("return", value)
            return
        raise AssertionError(f"unhandled statement: {type(stmt)!r}")

    def _visit_expr(self, expr: ast.Expression) -> str:
        if isinstance(expr, ast.IntLiteral):
            return self._emit_const(expr.value)
        if isinstance(expr, ast.Name):
            self._declare_local_if_needed(expr.identifier)
            temp = self._new_temp()
            # 显式 load 的目的是让“变量读取”在 IR 里单独可见。
            self._emit("load", temp, expr.identifier)
            return temp
        if isinstance(expr, ast.UnaryExpr):
            operand = self._visit_expr(expr.operand)
            temp = self._new_temp()
            self._emit("unary", temp, expr.operator, operand)
            return temp
        if isinstance(expr, ast.BinaryExpr):
            if expr.operator in {"&&", "||"}:
                return self._emit_short_circuit(expr)
            left = self._visit_expr(expr.left)
            right = self._visit_expr(expr.right)
            temp = self._new_temp()
            self._emit("binary", temp, expr.operator, left, right)
            return temp
        if isinstance(expr, ast.AssignExpr):
            assert isinstance(expr.target, ast.Name)
            value = self._visit_expr(expr.value)
            self._declare_local_if_needed(expr.target.identifier)
            self._emit("store", expr.target.identifier, value)
            temp = self._new_temp()
            # 赋值表达式本身也有值，因此这里再复制一份作为表达式结果。
            self._emit("copy", temp, value)
            return temp
        if isinstance(expr, ast.CallExpr):
            args = [self._visit_expr(arg) for arg in expr.args]
            temp = self._new_temp()
            self._emit("call", temp, expr.callee, *args)
            return temp
        raise AssertionError(f"unhandled expression: {type(expr)!r}")

    def _emit_short_circuit(self, expr: ast.BinaryExpr) -> str:
        result = self._new_temp()
        end_label = self._new_label("logic_end")
        left = self._visit_expr(expr.left)
        mid_label = self._new_label("logic_mid")
        if expr.operator == "&&":
            # 对于 &&，默认结果先放 0，只有左侧为真时才继续计算右侧。
            self._emit("const", result, "0")
            self._emit("cjump", left, mid_label, end_label)
            self._emit("label", mid_label)
            right = self._visit_expr(expr.right)
            truthy = self._emit_truthy(right)
            self._emit("copy", result, truthy)
            self._emit("label", end_label)
            return result
        # 对于 ||，默认结果先放 1，只有左侧为假时才继续计算右侧。
        self._emit("const", result, "1")
        self._emit("cjump", left, end_label, mid_label)
        self._emit("label", mid_label)
        right = self._visit_expr(expr.right)
        truthy = self._emit_truthy(right)
        self._emit("copy", result, truthy)
        self._emit("label", end_label)
        return result

    def _emit_const(self, value: int) -> str:
        temp = self._new_temp()
        self._emit("const", temp, str(value))
        return temp

    def _emit_truthy(self, operand: str) -> str:
        """把任意整数值规整成 C 语义下的 0/1。"""

        zero = self._emit_const(0)
        temp = self._new_temp()
        self._emit("binary", temp, "!=", operand, zero)
        return temp

    def _declare_local(self, name: str) -> None:
        if name not in self.local_names:
            self.local_names.add(name)
            self.current.locals.append(name)

    def _declare_local_if_needed(self, name: str) -> None:
        if name in self.global_names:
            return
        if name in self.current.params or name in self.current.locals:
            return
        # 正常情况下，未声明变量应由语义分析提前拦截。
        # 这里保留兜底逻辑，是为了让 IRBuilder 在单独测试时也能稳定运行。
        self._declare_local(name)

    def _new_temp(self) -> str:
        name = f"t{self.temp_index}"
        self.temp_index += 1
        self.current.temporaries.append(name)
        return name

    def _new_label(self, prefix: str) -> str:
        name = f"{prefix}_{self.label_index}"
        self.label_index += 1
        return name

    def _emit(self, opcode: str, *args: str) -> None:
        self.current.instructions.append(IRInstruction(opcode, tuple(args)))

    def _const_eval(self, expr: ast.Expression) -> int:
        if isinstance(expr, ast.IntLiteral):
            return expr.value
        if isinstance(expr, ast.CharLiteral):
            body = expr.value[1:-1]
            if body.startswith("\\"):
                escapes = {"n": "\n", "t": "\t", "\\": "\\", "'": "'"}
                return ord(escapes.get(body[1], body[1]))
            return ord(body)
        if isinstance(expr, ast.UnaryExpr):
            value = self._const_eval(expr.operand)
            if expr.operator == "+":
                return value
            if expr.operator == "-":
                return -value
            if expr.operator == "!":
                return int(not value)
        if isinstance(expr, ast.BinaryExpr):
            left = self._const_eval(expr.left)
            right = self._const_eval(expr.right)
            return _evaluate_binary(expr.operator, left, right)
        raise ValueError("global initializer must be constant")


def _requires_ast_backend(program: ast.Program) -> bool:
    for decl in program.declarations:
        if isinstance(decl, ast.GlobalVarDecl):
            if _type_requires_ast_backend(decl.ctype):
                return True
            if decl.initializer is not None and _expr_requires_ast_backend(decl.initializer):
                return True
            continue
        if _type_requires_ast_backend(decl.return_type):
            return True
        for param in decl.params:
            if _type_requires_ast_backend(param.ctype):
                return True
        if _stmt_requires_ast_backend(decl.body):
            return True
    return False


def _type_requires_ast_backend(ctype: ast.CType) -> bool:
    return ctype.base != "int" or ctype.pointer_level > 0 or ctype.array_size is not None


def _stmt_requires_ast_backend(stmt: ast.Statement) -> bool:
    if isinstance(stmt, ast.Block):
        return any(_stmt_requires_ast_backend(item) for item in stmt.items)
    if isinstance(stmt, ast.VarDeclStmt):
        return _type_requires_ast_backend(stmt.ctype) or (
            stmt.initializer is not None and _expr_requires_ast_backend(stmt.initializer)
        )
    if isinstance(stmt, ast.ExpressionStmt):
        return stmt.expression is not None and _expr_requires_ast_backend(stmt.expression)
    if isinstance(stmt, ast.IfStmt):
        return (
            _expr_requires_ast_backend(stmt.condition)
            or _stmt_requires_ast_backend(stmt.then_branch)
            or (stmt.else_branch is not None and _stmt_requires_ast_backend(stmt.else_branch))
        )
    if isinstance(stmt, ast.WhileStmt):
        return _expr_requires_ast_backend(stmt.condition) or _stmt_requires_ast_backend(stmt.body)
    if isinstance(stmt, ast.ForStmt):
        return (
            (stmt.init is not None and _stmt_requires_ast_backend(stmt.init))
            or (stmt.condition is not None and _expr_requires_ast_backend(stmt.condition))
            or (stmt.update is not None and _expr_requires_ast_backend(stmt.update))
            or _stmt_requires_ast_backend(stmt.body)
        )
    if isinstance(stmt, ast.ReturnStmt):
        return stmt.value is not None and _expr_requires_ast_backend(stmt.value)
    return False


def _expr_requires_ast_backend(expr: ast.Expression) -> bool:
    if isinstance(expr, (ast.CharLiteral, ast.StringLiteral, ast.IndexExpr)):
        return True
    if isinstance(expr, ast.UnaryExpr):
        return expr.operator in {"&", "*"} or _expr_requires_ast_backend(expr.operand)
    if isinstance(expr, ast.BinaryExpr):
        return _expr_requires_ast_backend(expr.left) or _expr_requires_ast_backend(expr.right)
    if isinstance(expr, ast.AssignExpr):
        return _expr_requires_ast_backend(expr.target) or _expr_requires_ast_backend(expr.value)
    if isinstance(expr, ast.CallExpr):
        return any(_expr_requires_ast_backend(arg) for arg in expr.args)
    return False
