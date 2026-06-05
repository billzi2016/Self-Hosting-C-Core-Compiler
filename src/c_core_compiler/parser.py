"""模块说明：使用递归下降把 Token 序列解析成 AST。"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import ast_nodes as ast
from .tokens import Token, TokenKind


class ParseError(ValueError):
    """当 Token 序列不符合当前支持的语法时抛出。"""


@dataclass(slots=True)
class Parser:
    """一个故意保持显式控制流的手写语法分析器。"""

    tokens: list[Token]
    index: int = 0
    typedef_names: set[str] = field(default_factory=set)
    struct_names: set[str] = field(default_factory=set)

    def parse_program(self) -> ast.Program:
        declarations: list[ast.TopLevelDecl] = []
        while not self._check(TokenKind.EOF):
            declarations.append(self._parse_top_level_decl())
        first = self.tokens[0] if self.tokens else Token(TokenKind.EOF, "", 1, 1)
        return ast.Program(first.line, first.column, declarations)

    def _parse_top_level_decl(self) -> ast.TopLevelDecl:
        # typedef struct / typedef existing_type
        if self._match(TokenKind.KW_TYPEDEF):
            return self._parse_typedef()

        is_extern = self._match(TokenKind.KW_EXTERN)

        type_token, base_type = self._parse_type_spec()

        # struct Tag { ... }; — 纯结构体定义（无后续声明名）
        if base_type.base == "struct" and self._check(TokenKind.LBRACE):
            fields = self._parse_struct_body()
            if base_type.struct_name:
                self.struct_names.add(base_type.struct_name)
            struct_decl = ast.StructDecl(
                type_token.line, type_token.column,
                tag=base_type.struct_name, alias=None, fields=fields,
            )
            if self._check(TokenKind.SEMICOLON):
                self._consume(TokenKind.SEMICOLON, "expected ';' after struct definition")
                return struct_decl
            # struct Tag { ... } varname; — 继续解析变量声明
            base_type = ast.CType("struct", struct_name=base_type.struct_name)

        name, decl_type = self._parse_declarator(base_type)

        if self._match(TokenKind.LPAREN):
            params, is_variadic = self._parse_parameters_ext()
            if self._check(TokenKind.SEMICOLON):
                # 函数原型（无函数体）
                self._consume(TokenKind.SEMICOLON, "expected ';'")
                return ast.FuncPrototype(
                    type_token.line, type_token.column,
                    return_type=decl_type, name=name,
                    params=params, is_variadic=is_variadic, is_extern=is_extern,
                )
            body = self._parse_block()
            return ast.FunctionDecl(type_token.line, type_token.column, decl_type, name, params, body)

        initializer = None
        if self._match(TokenKind.ASSIGN):
            initializer = self._parse_expression()
        self._consume(TokenKind.SEMICOLON, "expected ';' after global declaration")
        return ast.GlobalVarDecl(type_token.line, type_token.column, decl_type, name, initializer)

    # ── typedef 解析 ─────────────────────────────────────────────────────────

    def _parse_typedef(self) -> ast.StructDecl | ast.TypedefDecl:
        token = self._previous()

        if self._match(TokenKind.KW_STRUCT):
            # typedef struct [Tag] { ... } Alias;
            tag: str | None = None
            if self._check(TokenKind.IDENTIFIER):
                tag = self._peek().value
                self._consume(TokenKind.IDENTIFIER, "")

            fields: list[ast.StructField] | None = None
            if self._match(TokenKind.LBRACE):
                fields = self._parse_struct_fields_until_rbrace()

            alias_tok = self._consume(TokenKind.IDENTIFIER, "expected typedef alias name")
            self._consume(TokenKind.SEMICOLON, "expected ';' after typedef")
            self.typedef_names.add(alias_tok.value)
            if tag:
                self.struct_names.add(tag)
            return ast.StructDecl(token.line, token.column, tag=tag, alias=alias_tok.value, fields=fields)

        # typedef existing_type [*...] Alias;
        _, base_type = self._parse_type_spec()
        name, decl_type = self._parse_declarator(base_type)
        self._consume(TokenKind.SEMICOLON, "expected ';' after typedef")
        self.typedef_names.add(name)
        return ast.TypedefDecl(token.line, token.column, ctype=decl_type, alias=name)

    # ── struct 体 ─────────────────────────────────────────────────────────────

    def _parse_struct_body(self) -> list[ast.StructField]:
        self._consume(TokenKind.LBRACE, "expected '{' to start struct body")
        return self._parse_struct_fields_until_rbrace()

    def _parse_struct_fields_until_rbrace(self) -> list[ast.StructField]:
        fields: list[ast.StructField] = []
        while not self._check(TokenKind.RBRACE):
            if self._check(TokenKind.EOF):
                raise self._error(self._peek(), "unterminated struct body")
            field_type_tok, field_base = self._parse_type_spec()
            field_name, field_ctype = self._parse_declarator(field_base)
            self._consume(TokenKind.SEMICOLON, "expected ';' after struct field")
            fields.append(ast.StructField(field_type_tok.line, field_type_tok.column, field_ctype, field_name))
        self._consume(TokenKind.RBRACE, "expected '}' to end struct body")
        return fields

    # ── 参数列表（支持 ...） ───────────────────────────────────────────────────

    def _parse_parameters_ext(self) -> tuple[list[ast.Parameter], bool]:
        """返回 (params, is_variadic)。"""
        params: list[ast.Parameter] = []
        is_variadic = False

        if self._match(TokenKind.RPAREN):
            return params, is_variadic

        while True:
            if self._match(TokenKind.ELLIPSIS):
                is_variadic = True
                self._consume(TokenKind.RPAREN, "expected ')' after '...'")
                return params, is_variadic

            type_token, base_type = self._parse_type_spec()
            # void 单参数 → 空参数列表：func(void)
            if base_type.base == "void" and self._check(TokenKind.RPAREN):
                self._consume(TokenKind.RPAREN, "")
                return params, is_variadic

            name, decl_type = self._parse_declarator(base_type)
            params.append(ast.Parameter(type_token.line, type_token.column, decl_type, name))

            if self._match(TokenKind.RPAREN):
                return params, is_variadic
            self._consume(TokenKind.COMMA, "expected ',' between parameters")

    def _parse_parameters(self) -> list[ast.Parameter]:
        params, _ = self._parse_parameters_ext()
        return params

    # ── 语句 ─────────────────────────────────────────────────────────────────

    def _parse_block(self) -> ast.Block:
        left_brace = self._consume(TokenKind.LBRACE, "expected '{' to start a block")
        items: list[ast.Statement] = []
        while not self._check(TokenKind.RBRACE):
            items.append(self._parse_statement())
        self._consume(TokenKind.RBRACE, "expected '}' to end a block")
        return ast.Block(left_brace.line, left_brace.column, items)

    def _parse_statement(self) -> ast.Statement:
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
        if self._match(TokenKind.KW_BREAK):
            token = self._previous()
            self._consume(TokenKind.SEMICOLON, "expected ';' after break")
            return ast.BreakStmt(token.line, token.column)
        if self._match(TokenKind.KW_CONTINUE):
            token = self._previous()
            self._consume(TokenKind.SEMICOLON, "expected ';' after continue")
            return ast.ContinueStmt(token.line, token.column)
        if self._is_type_start():
            type_token, base_type = self._parse_type_spec()
            return self._parse_var_decl_after_type(type_token.line, type_token.column, base_type)
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
        elif self._is_type_start():
            type_token, base_type = self._parse_type_spec()
            init = self._parse_var_decl_after_type(type_token.line, type_token.column, base_type)
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

    def _parse_var_decl_after_type(self, line: int, column: int, base_type: ast.CType) -> ast.VarDeclStmt:
        name, decl_type = self._parse_declarator(base_type)
        initializer = None
        if self._match(TokenKind.ASSIGN):
            initializer = self._parse_expression()
        self._consume(TokenKind.SEMICOLON, "expected ';' after variable declaration")
        return ast.VarDeclStmt(line, column, decl_type, name, initializer)

    # ── 表达式 ────────────────────────────────────────────────────────────────

    def _parse_expression(self) -> ast.Expression:
        return self._parse_assignment()

    def _parse_assignment(self) -> ast.Expression:
        expr = self._parse_logical_or()
        if self._match(TokenKind.ASSIGN):
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
        # 前缀 ++ / --
        if self._match(TokenKind.PLUS_PLUS, TokenKind.MINUS_MINUS):
            operator = self._previous()
            operand = self._parse_unary()
            return ast.UnaryExpr(operator.line, operator.column, operator.value, operand)
        if self._match(TokenKind.PLUS, TokenKind.MINUS, TokenKind.BANG, TokenKind.AMPERSAND, TokenKind.STAR):
            operator = self._previous()
            operand = self._parse_unary()
            return ast.UnaryExpr(operator.line, operator.column, operator.value, operand)
        return self._parse_postfix()

    def _parse_postfix(self) -> ast.Expression:
        expr = self._parse_primary()
        while True:
            if self._match(TokenKind.LPAREN):
                if not isinstance(expr, ast.Name):
                    raise self._error(self._previous(), "only named functions can be called")
                args: list[ast.Expression] = []
                if not self._check(TokenKind.RPAREN):
                    while True:
                        args.append(self._parse_expression())
                        if not self._match(TokenKind.COMMA):
                            break
                right_paren = self._consume(TokenKind.RPAREN, "expected ')' after arguments")
                expr = ast.CallExpr(right_paren.line, right_paren.column, expr.identifier, args)
                continue
            if self._match(TokenKind.LBRACKET):
                index = self._parse_expression()
                right_bracket = self._consume(TokenKind.RBRACKET, "expected ']' after index expression")
                expr = ast.IndexExpr(right_bracket.line, right_bracket.column, expr, index)
                continue
            if self._match(TokenKind.DOT):
                member_tok = self._consume(TokenKind.IDENTIFIER, "expected member name after '.'")
                expr = ast.MemberExpr(member_tok.line, member_tok.column, expr, member_tok.value, arrow=False)
                continue
            if self._match(TokenKind.ARROW):
                member_tok = self._consume(TokenKind.IDENTIFIER, "expected member name after '->'")
                expr = ast.MemberExpr(member_tok.line, member_tok.column, expr, member_tok.value, arrow=True)
                continue
            if self._match(TokenKind.PLUS_PLUS):
                op_tok = self._previous()
                expr = ast.PostfixIncDecExpr(op_tok.line, op_tok.column, expr, "++")
                continue
            if self._match(TokenKind.MINUS_MINUS):
                op_tok = self._previous()
                expr = ast.PostfixIncDecExpr(op_tok.line, op_tok.column, expr, "--")
                continue
            break
        return expr

    def _parse_primary(self) -> ast.Expression:
        if self._match(TokenKind.INTEGER):
            token = self._previous()
            value = int(token.value, 16) if token.value.startswith(("0x", "0X")) else int(token.value)
            return ast.IntLiteral(token.line, token.column, value)
        if self._match(TokenKind.CHAR_LITERAL):
            token = self._previous()
            return ast.CharLiteral(token.line, token.column, token.value)
        if self._match(TokenKind.STRING_LITERAL):
            token = self._previous()
            return ast.StringLiteral(token.line, token.column, token.value)
        if self._match(TokenKind.IDENTIFIER):
            token = self._previous()
            return ast.Name(token.line, token.column, token.value)
        if self._match(TokenKind.KW_SIZEOF):
            return self._parse_sizeof()
        if self._match(TokenKind.LPAREN):
            # 判断是类型转换 (Type)expr 还是分组表达式 (expr)
            if self._is_type_start():
                return self._parse_cast_from_open_paren()
            expr = self._parse_expression()
            self._consume(TokenKind.RPAREN, "expected ')' after expression")
            return expr
        token = self._peek()
        raise self._error(token, f"unexpected token {token.kind.name}")

    def _parse_sizeof(self) -> ast.SizeofExpr:
        token = self._previous()
        self._consume(TokenKind.LPAREN, "expected '(' after sizeof")
        if self._is_type_start():
            ctype = self._parse_type_for_cast()
            self._consume(TokenKind.RPAREN, "expected ')' after sizeof type")
            return ast.SizeofExpr(token.line, token.column, ctype=ctype, expr=None)
        expr = self._parse_expression()
        self._consume(TokenKind.RPAREN, "expected ')'")
        return ast.SizeofExpr(token.line, token.column, ctype=None, expr=expr)

    def _parse_cast_from_open_paren(self) -> ast.CastExpr:
        """调用时已消耗 '('，当前位置在类型名起始处。"""
        ctype = self._parse_type_for_cast()
        tok = self._consume(TokenKind.RPAREN, "expected ')' after cast type")
        operand = self._parse_unary()
        return ast.CastExpr(tok.line, tok.column, ctype, operand)

    def _parse_type_for_cast(self) -> ast.CType:
        """解析一个完整的类型（含指针层级），用于 cast 和 sizeof。"""
        _, base = self._parse_type_spec()
        pointer_level = 0
        while self._match(TokenKind.STAR):
            pointer_level += 1
        return ast.CType(base.base, pointer_level=pointer_level, struct_name=base.struct_name)

    # ── 类型解析工具 ─────────────────────────────────────────────────────────

    def _is_type_start(self) -> bool:
        """当前 token 是否可以作为类型声明的开头。"""
        k = self._peek().kind
        if k in (TokenKind.KW_INT, TokenKind.KW_CHAR, TokenKind.KW_VOID,
                 TokenKind.KW_STRUCT, TokenKind.KW_EXTERN):
            return True
        if k == TokenKind.IDENTIFIER and self._peek().value in self.typedef_names:
            return True
        return False

    def _parse_type_spec(self) -> tuple[Token, ast.CType]:
        if self._match(TokenKind.KW_INT):
            return self._previous(), ast.CType("int")
        if self._match(TokenKind.KW_CHAR):
            return self._previous(), ast.CType("char")
        if self._match(TokenKind.KW_VOID):
            return self._previous(), ast.CType("void")
        if self._match(TokenKind.KW_STRUCT):
            token = self._previous()
            tag: str | None = None
            if self._check(TokenKind.IDENTIFIER):
                tag = self._peek().value
                self._consume(TokenKind.IDENTIFIER, "")
            return token, ast.CType("struct", struct_name=tag)
        if self._check(TokenKind.IDENTIFIER) and self._peek().value in self.typedef_names:
            token = self._consume(TokenKind.IDENTIFIER, "")
            return token, ast.CType(token.value)
        token = self._peek()
        raise self._error(token, "expected type specifier")

    def _parse_declarator(self, base_type: ast.CType) -> tuple[str, ast.CType]:
        pointer_level = 0
        while self._match(TokenKind.STAR):
            pointer_level += 1

        name_token = self._consume(TokenKind.IDENTIFIER, "expected declarator name")
        array_size = None
        if self._match(TokenKind.LBRACKET):
            if self._check(TokenKind.RBRACKET):
                self._consume(TokenKind.RBRACKET, "expected ']' after array declarator")
            else:
                size_token = self._consume(TokenKind.INTEGER, "expected array size integer")
                array_size = int(size_token.value)
                self._consume(TokenKind.RBRACKET, "expected ']' after array size")

        decl_type = ast.CType(
            base_type.base,
            pointer_level=pointer_level,
            array_size=array_size,
            struct_name=base_type.struct_name,
        )
        return name_token.value, decl_type

    # ── 底层工具 ─────────────────────────────────────────────────────────────

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
