"""Parser for the Satan language.

Reads a stream of tokens and builds an Abstract Syntax Tree (AST).
Input: Token stream from the Lexer
Output: AST (Program node with nested statement/expression nodes)

Uses recursive descent parsing with operator precedence.
"""

from tokens import Token, TokenType
from ast_nodes import (
    Program, IntegerLiteral, FloatLiteral, StringLiteral, BooleanLiteral,
    NullLiteral, Identifier, BinaryOp, UnaryOp, FunctionCall, ArrayLiteral,
    IndexAccess, LetStatement, AssignStatement, PrintStatement, ReturnStatement,
    ExpressionStatement, IfStatement, WhileStatement, FunctionDef, ASTNode,
)


class ParseError(Exception):
    def __init__(self, message, token=None):
        self.token = token
        loc = f" at L{token.line}:{token.column}" if token else ""
        super().__init__(f"Parse Error{loc}: {message}")


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def current(self) -> Token:
        return self.tokens[self.pos]

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def peek_type(self) -> TokenType:
        return self.tokens[self.pos].type

    def advance(self) -> Token:
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def expect(self, token_type: TokenType) -> Token:
        token = self.current()
        if token.type != token_type:
            raise ParseError(f"Expected {token_type.name}, got {token.type.name} ({token.value!r})", token)
        return self.advance()

    def match(self, *types: TokenType) -> Token | None:
        if self.current().type in types:
            return self.advance()
        return None

    def skip_newlines(self):
        while self.current().type == TokenType.NEWLINE:
            self.advance()

    def at_statement_end(self) -> bool:
        return self.current().type in (TokenType.NEWLINE, TokenType.EOF, TokenType.RBRACE, TokenType.SEMICOLON)

    def expect_statement_end(self):
        if self.current().type == TokenType.SEMICOLON:
            self.advance()
        elif self.current().type == TokenType.NEWLINE:
            self.advance()
        elif self.current().type in (TokenType.EOF, TokenType.RBRACE):
            pass  # OK, end of file or block
        else:
            raise ParseError(f"Expected end of statement, got {self.current().type.name}", self.current())

    # ---- Top-level parsing ----

    def parse(self) -> Program:
        program = Program(statements=[])
        self.skip_newlines()
        while self.current().type != TokenType.EOF:
            stmt = self.parse_statement()
            if stmt:
                program.statements.append(stmt)
            self.skip_newlines()
        return program

    # ---- Statement parsing ----

    def parse_statement(self) -> ASTNode:
        token = self.current()

        if token.type == TokenType.LET:
            return self.parse_let_statement()
        elif token.type == TokenType.FN:
            return self.parse_function_def()
        elif token.type == TokenType.IF:
            return self.parse_if_statement()
        elif token.type == TokenType.WHILE:
            return self.parse_while_statement()
        elif token.type == TokenType.RETURN:
            return self.parse_return_statement()
        elif token.type == TokenType.PRINT:
            return self.parse_print_statement()
        elif token.type == TokenType.IDENTIFIER and self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].type == TokenType.ASSIGN:
            return self.parse_assign_statement()
        else:
            return self.parse_expression_statement()

    def parse_let_statement(self) -> LetStatement:
        token = self.expect(TokenType.LET)
        name_token = self.expect(TokenType.IDENTIFIER)
        self.expect(TokenType.ASSIGN)
        value = self.parse_expression()
        self.expect_statement_end()
        return LetStatement(line=token.line, column=token.column, name=name_token.value, value=value)

    def parse_assign_statement(self) -> AssignStatement:
        name_token = self.expect(TokenType.IDENTIFIER)
        self.expect(TokenType.ASSIGN)
        value = self.parse_expression()
        self.expect_statement_end()
        return AssignStatement(line=name_token.line, column=name_token.column, name=name_token.value, value=value)

    def parse_print_statement(self) -> PrintStatement:
        token = self.expect(TokenType.PRINT)
        self.expect(TokenType.LPAREN)
        expr = self.parse_expression()
        self.expect(TokenType.RPAREN)
        self.expect_statement_end()
        return PrintStatement(line=token.line, column=token.column, expression=expr)

    def parse_return_statement(self) -> ReturnStatement:
        token = self.expect(TokenType.RETURN)
        value = None
        if not self.at_statement_end():
            value = self.parse_expression()
        self.expect_statement_end()
        return ReturnStatement(line=token.line, column=token.column, value=value)

    def parse_expression_statement(self) -> ExpressionStatement:
        expr = self.parse_expression()
        self.expect_statement_end()
        return ExpressionStatement(line=expr.line, column=expr.column, expression=expr)

    def parse_if_statement(self) -> IfStatement:
        token = self.expect(TokenType.IF)
        condition = self.parse_expression()
        then_body = self.parse_block()

        else_body = []
        self.skip_newlines()
        if self.current().type == TokenType.ELSE:
            self.advance()
            self.skip_newlines()
            if self.current().type == TokenType.IF:
                # else if chain
                else_body = [self.parse_if_statement()]
            else:
                else_body = self.parse_block()

        return IfStatement(
            line=token.line, column=token.column,
            condition=condition, then_body=then_body, else_body=else_body
        )

    def parse_while_statement(self) -> WhileStatement:
        token = self.expect(TokenType.WHILE)
        condition = self.parse_expression()
        body = self.parse_block()
        return WhileStatement(line=token.line, column=token.column, condition=condition, body=body)

    def parse_function_def(self) -> FunctionDef:
        token = self.expect(TokenType.FN)
        name_token = self.expect(TokenType.IDENTIFIER)
        self.expect(TokenType.LPAREN)

        params = []
        if self.current().type != TokenType.RPAREN:
            params.append(self.expect(TokenType.IDENTIFIER).value)
            while self.match(TokenType.COMMA):
                params.append(self.expect(TokenType.IDENTIFIER).value)

        self.expect(TokenType.RPAREN)
        body = self.parse_block()

        return FunctionDef(
            line=token.line, column=token.column,
            name=name_token.value, params=params, body=body
        )

    def parse_block(self) -> list[ASTNode]:
        self.skip_newlines()
        self.expect(TokenType.LBRACE)
        self.skip_newlines()

        statements = []
        while self.current().type != TokenType.RBRACE:
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)
            self.skip_newlines()

        self.expect(TokenType.RBRACE)
        return statements

    # ---- Expression parsing (precedence climbing) ----

    def parse_expression(self) -> ASTNode:
        return self.parse_or()

    def parse_or(self) -> ASTNode:
        left = self.parse_and()
        while self.current().type == TokenType.OR:
            op_token = self.advance()
            right = self.parse_and()
            left = BinaryOp(line=op_token.line, column=op_token.column, left=left, op="or", right=right)
        return left

    def parse_and(self) -> ASTNode:
        left = self.parse_equality()
        while self.current().type == TokenType.AND:
            op_token = self.advance()
            right = self.parse_equality()
            left = BinaryOp(line=op_token.line, column=op_token.column, left=left, op="and", right=right)
        return left

    def parse_equality(self) -> ASTNode:
        left = self.parse_comparison()
        while self.current().type in (TokenType.EQ, TokenType.NEQ):
            op_token = self.advance()
            right = self.parse_comparison()
            left = BinaryOp(line=op_token.line, column=op_token.column, left=left, op=op_token.value, right=right)
        return left

    def parse_comparison(self) -> ASTNode:
        left = self.parse_addition()
        while self.current().type in (TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE):
            op_token = self.advance()
            right = self.parse_addition()
            left = BinaryOp(line=op_token.line, column=op_token.column, left=left, op=op_token.value, right=right)
        return left

    def parse_addition(self) -> ASTNode:
        left = self.parse_multiplication()
        while self.current().type in (TokenType.PLUS, TokenType.MINUS):
            op_token = self.advance()
            right = self.parse_multiplication()
            left = BinaryOp(line=op_token.line, column=op_token.column, left=left, op=op_token.value, right=right)
        return left

    def parse_multiplication(self) -> ASTNode:
        left = self.parse_unary()
        while self.current().type in (TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op_token = self.advance()
            right = self.parse_unary()
            left = BinaryOp(line=op_token.line, column=op_token.column, left=left, op=op_token.value, right=right)
        return left

    def parse_unary(self) -> ASTNode:
        if self.current().type in (TokenType.MINUS, TokenType.NOT):
            op_token = self.advance()
            operand = self.parse_unary()
            return UnaryOp(line=op_token.line, column=op_token.column, op=op_token.value, operand=operand)
        return self.parse_postfix()

    def parse_postfix(self) -> ASTNode:
        node = self.parse_primary()

        while True:
            if self.current().type == TokenType.LBRACKET:
                self.advance()
                index = self.parse_expression()
                self.expect(TokenType.RBRACKET)
                node = IndexAccess(line=node.line, column=node.column, obj=node, index=index)
            else:
                break

        return node

    def parse_primary(self) -> ASTNode:
        token = self.current()

        if token.type == TokenType.INTEGER:
            self.advance()
            return IntegerLiteral(line=token.line, column=token.column, value=token.value)

        if token.type == TokenType.FLOAT:
            self.advance()
            return FloatLiteral(line=token.line, column=token.column, value=token.value)

        if token.type == TokenType.STRING:
            self.advance()
            return StringLiteral(line=token.line, column=token.column, value=token.value)

        if token.type in (TokenType.TRUE, TokenType.FALSE):
            self.advance()
            return BooleanLiteral(line=token.line, column=token.column, value=token.value)

        if token.type == TokenType.NULL:
            self.advance()
            return NullLiteral(line=token.line, column=token.column)

        if token.type == TokenType.IDENTIFIER:
            self.advance()
            # Check for function call
            if self.current().type == TokenType.LPAREN:
                self.advance()  # skip (
                args = []
                if self.current().type != TokenType.RPAREN:
                    args.append(self.parse_expression())
                    while self.match(TokenType.COMMA):
                        args.append(self.parse_expression())
                self.expect(TokenType.RPAREN)
                return FunctionCall(line=token.line, column=token.column, name=token.value, arguments=args)
            return Identifier(line=token.line, column=token.column, name=token.value)

        if token.type == TokenType.LPAREN:
            self.advance()
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return expr

        if token.type == TokenType.LBRACKET:
            return self.parse_array_literal()

        raise ParseError(f"Unexpected token: {token.type.name} ({token.value!r})", token)

    def parse_array_literal(self) -> ArrayLiteral:
        token = self.expect(TokenType.LBRACKET)
        elements = []
        if self.current().type != TokenType.RBRACKET:
            elements.append(self.parse_expression())
            while self.match(TokenType.COMMA):
                elements.append(self.parse_expression())
        self.expect(TokenType.RBRACKET)
        return ArrayLiteral(line=token.line, column=token.column, elements=elements)
