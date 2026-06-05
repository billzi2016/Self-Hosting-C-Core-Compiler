"""模块说明：使用递归下降把 Token 序列解析成 AST。"""

from __future__ import annotations

from dataclasses import dataclass

from . import ast_nodes as ast
from .tokens import Token, TokenKind


class ParseError(ValueError):
    """当 Token 序列不符合当前支持的语法时抛出。"""


@dataclass(slots=True)
class Parser:
    """一个故意保持显式控制流的手写语法分析器。

    这里优先保证读者能看出每个语法规则是如何落到代码里的，
    而不是把规则隐藏在复杂抽象后面。
    """

    tokens: list[Token]
    index: int = 0

    def parse_program(self) -> ast.Program:
        declarations: list[ast.TopLevelDecl] = []
        while not self._check(TokenKind.EOF):
            declarations.append(self._parse_top_level_decl())
        first = self.tokens[0] if self.tokens else Token(TokenKind.EOF, "", 1, 1)
        return ast.Program(first.line, first.column, declarations)

    def _parse_top_level_decl(self) -> ast.TopLevelDecl:
        # 第一代顶层只支持两类声明：
        # 1. 全局变量声明
        # 2. 函数定义
        int_token = self._consume(TokenKind.KW_INT, "expected 'int' at top level")
        name = self._consume(TokenKind.IDENTIFIER, "expected identifier after 'int'")
        if self._match(TokenKind.LPAREN):
            params = self._parse_parameters()
            body = self._parse_block()
            return ast.FunctionDecl(int_token.line, int_token.column, name.value, params, body)

        initializer = None
        if self._match(TokenKind.ASSIGN):
            initializer = self._parse_expression()
        self._consume(TokenKind.SEMICOLON, "expected ';' after global declaration")
        return ast.GlobalVarDecl(int_token.line, int_token.column, name.value, initializer)

    def _parse_parameters(self) -> list[ast.Parameter]:
        params: list[ast.Parameter] = []
        if self._match(TokenKind.RPAREN):
            return params

        while True:
            int_token = self._consume(TokenKind.KW_INT, "expected 'int' in parameter list")
            name = self._consume(TokenKind.IDENTIFIER, "expected parameter name")
            params.append(ast.Parameter(int_token.line, int_token.column, name.value))
            if self._match(TokenKind.RPAREN):
                return params
            self._consume(TokenKind.COMMA, "expected ',' between parameters")

    def _parse_block(self) -> ast.Block:
        left_brace = self._consume(TokenKind.LBRACE, "expected '{' to start a block")
        items: list[ast.Statement] = []
        while not self._check(TokenKind.RBRACE):
            items.append(self._parse_statement())
        self._consume(TokenKind.RBRACE, "expected '}' to end a block")
        return ast.Block(left_brace.line, left_brace.column, items)

    def _parse_statement(self) -> ast.Statement:
        # 这里按“最容易区分的起始 Token”来分派语句类型，
        # 这样读起来最接近手工分析语法的过程。
        if self._check(TokenKind.LBRACE):
            return self._parse_block()
        if self._match(TokenKind.KW_IF):
            return self._parse_if()
        if self._match(TokenKind.KW_WHILE):
            return self._parse_while()
        if self._match(TokenKind.KW_FOR):
            return self._parse_for()
        if self._match(TokenKind.KW_RETURN):
            return self._parse_return()
        if self._match(TokenKind.KW_INT):
            return self._parse_var_decl_after_int(self._previous())
        if self._match(TokenKind.SEMICOLON):
            token = self._previous()
            return ast.ExpressionStmt(token.line, token.column, None)

        expr = self._parse_expression()
        self._consume(TokenKind.SEMICOLON, "expected ';' after expression")
        return ast.ExpressionStmt(expr.line, expr.column, expr)

    def _parse_if(self) -> ast.IfStmt:
        keyword = self._previous()
        self._consume(TokenKind.LPAREN, "expected '(' after 'if'")
        condition = self._parse_expression()
        self._consume(TokenKind.RPAREN, "expected ')' after if condition")
        then_branch = self._parse_statement()
        else_branch = self._parse_statement() if self._match(TokenKind.KW_ELSE) else None
        return ast.IfStmt(keyword.line, keyword.column, condition, then_branch, else_branch)

    def _parse_while(self) -> ast.WhileStmt:
        keyword = self._previous()
        self._consume(TokenKind.LPAREN, "expected '(' after 'while'")
        condition = self._parse_expression()
        self._consume(TokenKind.RPAREN, "expected ')' after while condition")
        body = self._parse_statement()
        return ast.WhileStmt(keyword.line, keyword.column, condition, body)

    def _parse_for(self) -> ast.ForStmt:
        keyword = self._previous()
        self._consume(TokenKind.LPAREN, "expected '(' after 'for'")

        init: ast.Statement | None
        if self._match(TokenKind.SEMICOLON):
            init = None
        elif self._match(TokenKind.KW_INT):
            # for 的初始化部分允许直接写变量声明，例如：
            # for (int i = 0; i < 10; i = i + 1)
            init = self._parse_var_decl_after_int(self._previous())
        else:
            expr = self._parse_expression()
            self._consume(TokenKind.SEMICOLON, "expected ';' after for initializer")
            init = ast.ExpressionStmt(expr.line, expr.column, expr)

        condition = None
        if not self._check(TokenKind.SEMICOLON):
            condition = self._parse_expression()
        self._consume(TokenKind.SEMICOLON, "expected ';' after for condition")

        update = None
        if not self._check(TokenKind.RPAREN):
            update = self._parse_expression()
        self._consume(TokenKind.RPAREN, "expected ')' after for clauses")
        body = self._parse_statement()
        return ast.ForStmt(keyword.line, keyword.column, init, condition, update, body)

    def _parse_return(self) -> ast.ReturnStmt:
        keyword = self._previous()
        value = None
        if not self._check(TokenKind.SEMICOLON):
            value = self._parse_expression()
        self._consume(TokenKind.SEMICOLON, "expected ';' after return")
        return ast.ReturnStmt(keyword.line, keyword.column, value)

    def _parse_var_decl_after_int(self, int_token: Token) -> ast.VarDeclStmt:
        name = self._consume(TokenKind.IDENTIFIER, "expected variable name after 'int'")
        initializer = None
        if self._match(TokenKind.ASSIGN):
            initializer = self._parse_expression()
        self._consume(TokenKind.SEMICOLON, "expected ';' after variable declaration")
        return ast.VarDeclStmt(int_token.line, int_token.column, name.value, initializer)

    def _parse_expression(self) -> ast.Expression:
        return self._parse_assignment()

    def _parse_assignment(self) -> ast.Expression:
        expr = self._parse_logical_or()
        if self._match(TokenKind.ASSIGN):
            # 赋值是右结合的，因此右边仍然递归走 assignment。
            value = self._parse_assignment()
            return ast.AssignExpr(expr.line, expr.column, expr, value)
        return expr

    def _parse_logical_or(self) -> ast.Expression:
        expr = self._parse_logical_and()
        while self._match(TokenKind.OR):
            operator = self._previous()
            right = self._parse_logical_and()
            expr = ast.BinaryExpr(operator.line, operator.column, operator.value, expr, right)
        return expr

    def _parse_logical_and(self) -> ast.Expression:
        expr = self._parse_equality()
        while self._match(TokenKind.AND):
            operator = self._previous()
            right = self._parse_equality()
            expr = ast.BinaryExpr(operator.line, operator.column, operator.value, expr, right)
        return expr

    def _parse_equality(self) -> ast.Expression:
        expr = self._parse_comparison()
        while self._match(TokenKind.EQ, TokenKind.NE):
            operator = self._previous()
            right = self._parse_comparison()
            expr = ast.BinaryExpr(operator.line, operator.column, operator.value, expr, right)
        return expr

    def _parse_comparison(self) -> ast.Expression:
        expr = self._parse_additive()
        while self._match(TokenKind.LT, TokenKind.LE, TokenKind.GT, TokenKind.GE):
            operator = self._previous()
            right = self._parse_additive()
            expr = ast.BinaryExpr(operator.line, operator.column, operator.value, expr, right)
        return expr

    def _parse_additive(self) -> ast.Expression:
        expr = self._parse_multiplicative()
        while self._match(TokenKind.PLUS, TokenKind.MINUS):
            operator = self._previous()
            right = self._parse_multiplicative()
            expr = ast.BinaryExpr(operator.line, operator.column, operator.value, expr, right)
        return expr

    def _parse_multiplicative(self) -> ast.Expression:
        expr = self._parse_unary()
        while self._match(TokenKind.STAR, TokenKind.SLASH, TokenKind.PERCENT):
            operator = self._previous()
            right = self._parse_unary()
            expr = ast.BinaryExpr(operator.line, operator.column, operator.value, expr, right)
        return expr

    def _parse_unary(self) -> ast.Expression:
        if self._match(TokenKind.PLUS, TokenKind.MINUS, TokenKind.BANG):
            operator = self._previous()
            operand = self._parse_unary()
            return ast.UnaryExpr(operator.line, operator.column, operator.value, operand)
        return self._parse_postfix()

    def _parse_postfix(self) -> ast.Expression:
        expr = self._parse_primary()
        while self._match(TokenKind.LPAREN):
            if not isinstance(expr, ast.Name):
                raise self._error(self._previous(), "only named functions can be called")
            args: list[ast.Expression] = []
            if not self._check(TokenKind.RPAREN):
                while True:
                    args.append(self._parse_expression())
                    if not self._match(TokenKind.COMMA):
                        break
            right_paren = self._consume(TokenKind.RPAREN, "expected ')' after arguments")
            # 第一代只支持“按名字调用函数”，不支持函数指针或更复杂的调用形式。
            expr = ast.CallExpr(right_paren.line, right_paren.column, expr.identifier, args)
        return expr

    def _parse_primary(self) -> ast.Expression:
        if self._match(TokenKind.INTEGER):
            token = self._previous()
            return ast.IntLiteral(token.line, token.column, int(token.value))
        if self._match(TokenKind.IDENTIFIER):
            token = self._previous()
            return ast.Name(token.line, token.column, token.value)
        if self._match(TokenKind.LPAREN):
            expr = self._parse_expression()
            self._consume(TokenKind.RPAREN, "expected ')' after expression")
            return expr
        token = self._peek()
        raise self._error(token, f"unexpected token {token.kind.name}")

    def _match(self, *kinds: TokenKind) -> bool:
        if self._check(*kinds):
            self.index += 1
            return True
        return False

    def _consume(self, kind: TokenKind, message: str) -> Token:
        if self._check(kind):
            self.index += 1
            return self._previous()
        raise self._error(self._peek(), message)

    def _check(self, *kinds: TokenKind) -> bool:
        return self._peek().kind in kinds

    def _peek(self) -> Token:
        return self.tokens[self.index]

    def _previous(self) -> Token:
        return self.tokens[self.index - 1]

    def _error(self, token: Token, message: str) -> ParseError:
        return ParseError(f"{message} at {token.line}:{token.column}")
