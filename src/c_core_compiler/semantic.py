"""模块说明：在进入 IR 之前做名称解析和基础语义检查。"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import ast_nodes as ast
from .symbol_table import Symbol, SymbolTable


class SemanticError(ValueError):
    """当 AST 违反当前支持的语言规则时抛出。"""


@dataclass(slots=True)
class SemanticAnalyzer:
    """执行第一代所需的严格但范围可控的语义检查。"""

    program: ast.Program
    functions: dict[str, ast.FunctionDecl] = field(init=False, default_factory=dict)
    globals: dict[str, ast.GlobalVarDecl] = field(init=False, default_factory=dict)
    variables: SymbolTable = field(init=False, default_factory=SymbolTable)
    _saw_return: bool = field(init=False, default=False)

    def analyze(self) -> None:
        # 先收集顶层名字，目的是尽早发现重名问题，
        # 同时让函数之间可以互相调用。
        self.functions: dict[str, ast.FunctionDecl] = {}
        self.globals: dict[str, ast.GlobalVarDecl] = {}
        self.variables = SymbolTable()

        for decl in self.program.declarations:
            if isinstance(decl, ast.GlobalVarDecl):
                if decl.name in self.globals or decl.name in self.functions:
                    self._error(decl, f"duplicate top-level name '{decl.name}'")
                self.globals[decl.name] = decl
                self.variables.define(Symbol(decl.name, "global"))
            else:
                if decl.name in self.globals or decl.name in self.functions:
                    self._error(decl, f"duplicate top-level name '{decl.name}'")
                self.functions[decl.name] = decl

        for function in self.functions.values():
            self.variables.define(Symbol(function.name, "function", arity=len(function.params)))

        for global_decl in self.globals.values():
            if global_decl.initializer is not None:
                # 第一代把全局初始化限制为常量表达式，
                # 这样后端生成逻辑会简单很多，也更容易测试。
                self._ensure_const_expr(global_decl.initializer)

        for function in self.functions.values():
            self._analyze_function(function)

    def _analyze_function(self, function: ast.FunctionDecl) -> None:
        self.variables.push()
        for param in function.params:
            if not self.variables.define(Symbol(param.name, "variable")):
                self._error(param, f"duplicate parameter '{param.name}'")

        self._saw_return = False
        self._visit_stmt(function.body)
        self.variables.pop()

        if not self._saw_return:
            # 第一代先采用更严格的规则：每个函数都必须显式写 return。
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
            self._visit_stmt(stmt.body)
            return

        if isinstance(stmt, ast.ForStmt):
            self.variables.push()
            if stmt.init is not None:
                self._visit_stmt(stmt.init)
            if stmt.condition is not None:
                self._visit_expr(stmt.condition)
            if stmt.update is not None:
                self._visit_expr(stmt.update)
            self._visit_stmt(stmt.body)
            self.variables.pop()
            return

        if isinstance(stmt, ast.ReturnStmt):
            self._saw_return = True
            if stmt.value is None:
                self._error(stmt, "return value is required in the first-generation compiler")
            self._visit_expr(stmt.value)
            return

        raise AssertionError(f"unhandled statement type: {type(stmt)!r}")

    def _visit_expr(self, expr: ast.Expression) -> None:
        if isinstance(expr, ast.IntLiteral):
            return
        if isinstance(expr, ast.Name):
            symbol = self.variables.lookup(expr.identifier)
            if symbol is None or symbol.kind == "function":
                self._error(expr, f"undefined variable '{expr.identifier}'")
            return
        if isinstance(expr, ast.UnaryExpr):
            self._visit_expr(expr.operand)
            return
        if isinstance(expr, ast.BinaryExpr):
            self._visit_expr(expr.left)
            self._visit_expr(expr.right)
            return
        if isinstance(expr, ast.AssignExpr):
            if not isinstance(expr.target, ast.Name):
                # 这里明确限制左值必须是名字，
                # 是为了先把“变量赋值”这条链路做清楚。
                self._error(expr.target, "assignment target must be a named variable")
            self._visit_expr(expr.target)
            self._visit_expr(expr.value)
            return
        if isinstance(expr, ast.CallExpr):
            symbol = self.variables.lookup(expr.callee)
            if symbol is None or symbol.kind != "function":
                self._error(expr, f"undefined function '{expr.callee}'")
            if symbol.arity != len(expr.args):
                self._error(expr, f"function '{expr.callee}' expects {symbol.arity} arguments but got {len(expr.args)}")
            for arg in expr.args:
                self._visit_expr(arg)
            return
        raise AssertionError(f"unhandled expression type: {type(expr)!r}")

    def _ensure_const_expr(self, expr: ast.Expression) -> int:
        if isinstance(expr, ast.IntLiteral):
            return expr.value
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
