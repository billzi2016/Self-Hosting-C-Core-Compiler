"""模块说明：在进入 IR 之前做名称解析和基础语义检查。"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import ast_nodes as ast
from .symbol_table import Symbol, SymbolTable


class SemanticError(ValueError):
    """当 AST 违反当前支持的语言规则时抛出。"""


@dataclass(slots=True)
class SemanticAnalyzer:
    """执行语义检查。支持 void、struct、break/continue、cast、extern 调用等扩展特性。"""

    program: ast.Program
    functions: dict[str, ast.FunctionDecl] = field(init=False, default_factory=dict)
    globals: dict[str, ast.GlobalVarDecl] = field(init=False, default_factory=dict)
    variables: SymbolTable = field(init=False, default_factory=SymbolTable)
    typedef_names: set[str] = field(init=False, default_factory=set)
    struct_names: set[str] = field(init=False, default_factory=set)
    _saw_return: bool = field(init=False, default=False)
    _current_return_void: bool = field(init=False, default=False)
    _loop_depth: int = field(init=False, default=0)

    def analyze(self) -> None:
        self.functions = {}
        self.globals = {}
        self.variables = SymbolTable()
        self._install_builtin_functions()

        # 第一遍：收集顶层名字（struct / typedef / 全局变量 / 函数）
        for decl in self.program.declarations:
            if isinstance(decl, ast.StructDecl):
                if decl.tag:
                    self.struct_names.add(decl.tag)
                if decl.alias:
                    self.typedef_names.add(decl.alias)
                continue
            if isinstance(decl, ast.TypedefDecl):
                self.typedef_names.add(decl.alias)
                continue
            if isinstance(decl, ast.FuncPrototype):
                # 注册为已知函数；arity=-1 表示可接受任意参数数量
                arity = -1 if decl.is_variadic else len(decl.params)
                self.variables.define(Symbol(decl.name, "function", arity=arity))
                continue
            if isinstance(decl, ast.GlobalVarDecl):
                if decl.name in self.globals or decl.name in self.functions:
                    self._error(decl, f"duplicate top-level name '{decl.name}'")
                self.globals[decl.name] = decl
                self.variables.define(Symbol(decl.name, "global"))
                continue
            if isinstance(decl, ast.FunctionDecl):
                if decl.name in self.globals or decl.name in self.functions:
                    self._error(decl, f"duplicate top-level name '{decl.name}'")
                self.functions[decl.name] = decl

        for function in self.functions.values():
            self.variables.define(Symbol(function.name, "function", arity=len(function.params)))

        # 第二遍：检查全局变量初始化表达式
        for global_decl in self.globals.values():
            if global_decl.initializer is not None:
                self._ensure_const_expr(global_decl.initializer)

        # 第三遍：逐函数分析
        for function in self.functions.values():
            self._analyze_function(function)

    def _analyze_function(self, function: ast.FunctionDecl) -> None:
        self._current_return_void = (function.return_type.base == "void" and function.return_type.pointer_level == 0)
        self.variables.push()
        for param in function.params:
            if not self.variables.define(Symbol(param.name, "variable")):
                self._error(param, f"duplicate parameter '{param.name}'")

        self._saw_return = False
        self._visit_stmt(function.body)
        self.variables.pop()

        # void 函数不强制要求显式 return
        if not self._saw_return and not self._current_return_void:
            self._error(function, f"function '{function.name}' must contain a return statement")

    def _visit_stmt(self, stmt: ast.Statement) -> None:
        if isinstance(stmt, ast.Block):
            self.variables.push()
            for item in stmt.items:
                self._visit_stmt(item)
            self.variables.pop()
            return

        if isinstance(stmt, ast.VarDeclStmt):
            if not self.variables.define(Symbol(stmt.name, "variable")):
                self._error(stmt, f"duplicate variable '{stmt.name}'")
            if stmt.initializer is not None:
                self._visit_expr(stmt.initializer)
            return

        if isinstance(stmt, ast.ExpressionStmt):
            if stmt.expression is not None:
                self._visit_expr(stmt.expression)
            return

        if isinstance(stmt, ast.IfStmt):
            self._visit_expr(stmt.condition)
            self._visit_stmt(stmt.then_branch)
            if stmt.else_branch is not None:
                self._visit_stmt(stmt.else_branch)
            return

        if isinstance(stmt, ast.WhileStmt):
            self._visit_expr(stmt.condition)
            self._loop_depth += 1
            self._visit_stmt(stmt.body)
            self._loop_depth -= 1
            return

        if isinstance(stmt, ast.ForStmt):
            self.variables.push()
            if stmt.init is not None:
                self._visit_stmt(stmt.init)
            if stmt.condition is not None:
                self._visit_expr(stmt.condition)
            if stmt.update is not None:
                self._visit_expr(stmt.update)
            self._loop_depth += 1
            self._visit_stmt(stmt.body)
            self._loop_depth -= 1
            self.variables.pop()
            return

        if isinstance(stmt, ast.ReturnStmt):
            self._saw_return = True
            if stmt.value is None:
                if not self._current_return_void:
                    self._error(stmt, "return value is required in non-void function")
                return
            self._visit_expr(stmt.value)
            return

        if isinstance(stmt, ast.BreakStmt):
            if self._loop_depth == 0:
                self._error(stmt, "break outside of loop")
            return

        if isinstance(stmt, ast.ContinueStmt):
            if self._loop_depth == 0:
                self._error(stmt, "continue outside of loop")
            return

        raise AssertionError(f"unhandled statement type: {type(stmt)!r}")

    def _visit_expr(self, expr: ast.Expression) -> None:
        if isinstance(expr, ast.IntLiteral):
            return
        if isinstance(expr, ast.CharLiteral):
            return
        if isinstance(expr, ast.StringLiteral):
            return
        if isinstance(expr, ast.Name):
            symbol = self.variables.lookup(expr.identifier)
            if symbol is None or symbol.kind == "function":
                self._error(expr, f"undefined variable '{expr.identifier}'")
            return
        if isinstance(expr, ast.UnaryExpr):
            if expr.operator == "&":
                if not isinstance(expr.operand, (ast.Name, ast.IndexExpr)):
                    self._error(expr, "address-of operand must be a variable or indexed element")
            self._visit_expr(expr.operand)
            return
        if isinstance(expr, ast.BinaryExpr):
            self._visit_expr(expr.left)
            self._visit_expr(expr.right)
            return
        if isinstance(expr, ast.IndexExpr):
            self._visit_expr(expr.target)
            self._visit_expr(expr.index)
            return
        if isinstance(expr, ast.AssignExpr):
            if not self._is_assignable_target(expr.target):
                self._error(expr.target, "assignment target must be a variable, dereference, or indexed element")
            self._visit_expr(expr.target)
            self._visit_expr(expr.value)
            return
        if isinstance(expr, ast.CallExpr):
            symbol = self.variables.lookup(expr.callee)
            if symbol is None:
                self._error(expr, f"undefined function '{expr.callee}'")
            if symbol.kind != "function":
                self._error(expr, f"'{expr.callee}' is not a function")
            # arity == -1 表示可变参数函数，不检查参数数量
            if symbol.arity is not None and symbol.arity >= 0:
                if symbol.arity != len(expr.args):
                    self._error(expr, f"function '{expr.callee}' expects {symbol.arity} arguments but got {len(expr.args)}")
            for arg in expr.args:
                self._visit_expr(arg)
            return
        if isinstance(expr, ast.CastExpr):
            self._visit_expr(expr.operand)
            return
        if isinstance(expr, ast.SizeofExpr):
            if expr.expr is not None:
                self._visit_expr(expr.expr)
            return
        if isinstance(expr, ast.MemberExpr):
            self._visit_expr(expr.target)
            return
        if isinstance(expr, ast.PostfixIncDecExpr):
            self._visit_expr(expr.operand)
            return
        raise AssertionError(f"unhandled expression type: {type(expr)!r}")

    def _is_assignable_target(self, expr: ast.Expression) -> bool:
        if isinstance(expr, ast.Name):
            return True
        if isinstance(expr, ast.IndexExpr):
            return True
        if isinstance(expr, ast.UnaryExpr) and expr.operator == "*":
            return True
        if isinstance(expr, ast.MemberExpr):
            return True
        return False

    def _ensure_const_expr(self, expr: ast.Expression) -> int:
        if isinstance(expr, ast.IntLiteral):
            return expr.value
        if isinstance(expr, ast.CharLiteral):
            return _decode_char_literal(expr.value)
        if isinstance(expr, ast.UnaryExpr):
            value = self._ensure_const_expr(expr.operand)
            if expr.operator == "+":
                return value
            if expr.operator == "-":
                return -value
            if expr.operator == "!":
                return int(not value)
        if isinstance(expr, ast.BinaryExpr):
            left = self._ensure_const_expr(expr.left)
            right = self._ensure_const_expr(expr.right)
            return _evaluate_binary(expr.operator, left, right)
        self._error(expr, "global initializer must be a constant integer expression")

    def _error(self, node: ast.Node, message: str) -> None:
        raise SemanticError(f"{message} at {node.line}:{node.column}")

    def _install_builtin_functions(self) -> None:
        self.variables.define(Symbol("print_int", "function", arity=1))


def _evaluate_binary(operator: str, left: int, right: int) -> int:
    if operator == "+":
        return left + right
    if operator == "-":
        return left - right
    if operator == "*":
        return left * right
    if operator == "/":
        return int(left / right)
    if operator == "%":
        return left % right
    if operator == "==":
        return int(left == right)
    if operator == "!=":
        return int(left != right)
    if operator == "<":
        return int(left < right)
    if operator == "<=":
        return int(left <= right)
    if operator == ">":
        return int(left > right)
    if operator == ">=":
        return int(left >= right)
    if operator == "&&":
        return int(bool(left) and bool(right))
    if operator == "||":
        return int(bool(left) or bool(right))
    raise AssertionError(f"unsupported constant operator: {operator}")


def _decode_char_literal(text: str) -> int:
    """把 `'a'` 或 `'\n'` 这样的字符字面量转成整数值。"""

    body = text[1:-1]
    if body.startswith("\\"):
        escapes = {"n": "\n", "t": "\t", "\\": "\\", "'": "'"}
        return ord(escapes.get(body[1], body[1]))
    return ord(body)
