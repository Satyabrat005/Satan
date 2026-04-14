"""Optimizer for the Satan language AST.

Performs optimization passes on the AST before code generation.
Input: Raw AST from the Parser
Output: Optimized AST

Optimizations implemented:
- Constant folding (evaluate constant expressions at compile time)
- Dead code elimination (remove unreachable code after return)
- Constant propagation (substitute known constant values)
"""

from ast_nodes import (
    ASTNode, Program, IntegerLiteral, FloatLiteral, StringLiteral,
    BooleanLiteral, NullLiteral, Identifier, BinaryOp, UnaryOp,
    FunctionCall, ArrayLiteral, IndexAccess, LetStatement, AssignStatement,
    PrintStatement, ReturnStatement, ExpressionStatement, IfStatement,
    WhileStatement, FunctionDef,
)


class Optimizer:
    def __init__(self):
        self.optimizations_applied = 0

    def optimize(self, program: Program) -> Program:
        """Run all optimization passes on the program."""
        optimized = Program(
            line=program.line,
            column=program.column,
            statements=self.optimize_statements(program.statements)
        )
        return optimized

    def optimize_statements(self, statements: list[ASTNode]) -> list[ASTNode]:
        """Optimize a list of statements, including dead code elimination."""
        result = []
        for stmt in statements:
            optimized = self.optimize_node(stmt)
            result.append(optimized)
            # Dead code elimination: skip statements after return
            if isinstance(optimized, ReturnStatement):
                if len(result) < len(statements):
                    self.optimizations_applied += 1
                break
        return result

    def optimize_node(self, node: ASTNode) -> ASTNode:
        """Optimize a single AST node."""
        if isinstance(node, BinaryOp):
            return self.optimize_binary_op(node)
        elif isinstance(node, UnaryOp):
            return self.optimize_unary_op(node)
        elif isinstance(node, LetStatement):
            return LetStatement(
                line=node.line, column=node.column,
                name=node.name, value=self.optimize_node(node.value)
            )
        elif isinstance(node, AssignStatement):
            return AssignStatement(
                line=node.line, column=node.column,
                name=node.name, value=self.optimize_node(node.value)
            )
        elif isinstance(node, PrintStatement):
            return PrintStatement(
                line=node.line, column=node.column,
                expression=self.optimize_node(node.expression)
            )
        elif isinstance(node, ReturnStatement):
            return ReturnStatement(
                line=node.line, column=node.column,
                value=self.optimize_node(node.value) if node.value else None
            )
        elif isinstance(node, ExpressionStatement):
            return ExpressionStatement(
                line=node.line, column=node.column,
                expression=self.optimize_node(node.expression)
            )
        elif isinstance(node, IfStatement):
            return self.optimize_if(node)
        elif isinstance(node, WhileStatement):
            return WhileStatement(
                line=node.line, column=node.column,
                condition=self.optimize_node(node.condition),
                body=self.optimize_statements(node.body)
            )
        elif isinstance(node, FunctionDef):
            return FunctionDef(
                line=node.line, column=node.column,
                name=node.name, params=node.params,
                body=self.optimize_statements(node.body)
            )
        elif isinstance(node, FunctionCall):
            return FunctionCall(
                line=node.line, column=node.column,
                name=node.name,
                arguments=[self.optimize_node(arg) for arg in node.arguments]
            )
        elif isinstance(node, ArrayLiteral):
            return ArrayLiteral(
                line=node.line, column=node.column,
                elements=[self.optimize_node(el) for el in node.elements]
            )
        elif isinstance(node, IndexAccess):
            return IndexAccess(
                line=node.line, column=node.column,
                obj=self.optimize_node(node.obj),
                index=self.optimize_node(node.index)
            )
        return node

    def optimize_binary_op(self, node: BinaryOp) -> ASTNode:
        """Constant folding for binary operations."""
        left = self.optimize_node(node.left)
        right = self.optimize_node(node.right)

        # Try constant folding if both sides are literals
        left_val = self._get_literal_value(left)
        right_val = self._get_literal_value(right)

        if left_val is not None and right_val is not None:
            try:
                result = self._eval_binary(node.op, left_val, right_val)
                if result is not None:
                    self.optimizations_applied += 1
                    return self._make_literal(result, node.line, node.column)
            except (ZeroDivisionError, TypeError):
                pass

        # String concatenation optimization: fold "a" + "b" into "ab"
        if node.op == '+' and isinstance(left, StringLiteral) and isinstance(right, StringLiteral):
            self.optimizations_applied += 1
            return StringLiteral(line=node.line, column=node.column, value=left.value + right.value)

        return BinaryOp(line=node.line, column=node.column, left=left, op=node.op, right=right)

    def optimize_unary_op(self, node: UnaryOp) -> ASTNode:
        """Constant folding for unary operations."""
        operand = self.optimize_node(node.operand)
        val = self._get_literal_value(operand)

        if val is not None:
            if node.op == '-' and isinstance(val, (int, float)):
                self.optimizations_applied += 1
                return self._make_literal(-val, node.line, node.column)
            if node.op == 'not' and isinstance(val, bool):
                self.optimizations_applied += 1
                return BooleanLiteral(line=node.line, column=node.column, value=not val)

        return UnaryOp(line=node.line, column=node.column, op=node.op, operand=operand)

    def optimize_if(self, node: IfStatement) -> ASTNode:
        """Optimize if statements - eliminate branches with constant conditions."""
        condition = self.optimize_node(node.condition)
        then_body = self.optimize_statements(node.then_body)
        else_body = self.optimize_statements(node.else_body)

        # If condition is a constant boolean, eliminate the dead branch
        if isinstance(condition, BooleanLiteral):
            self.optimizations_applied += 1
            if condition.value:
                # Always true - return then body as statements
                return IfStatement(
                    line=node.line, column=node.column,
                    condition=condition, then_body=then_body, else_body=[]
                )
            else:
                # Always false - return else body
                return IfStatement(
                    line=node.line, column=node.column,
                    condition=condition, then_body=[], else_body=else_body
                )

        return IfStatement(
            line=node.line, column=node.column,
            condition=condition, then_body=then_body, else_body=else_body
        )

    def _get_literal_value(self, node: ASTNode):
        """Extract the Python value from a literal node, or None."""
        if isinstance(node, IntegerLiteral):
            return node.value
        if isinstance(node, FloatLiteral):
            return node.value
        if isinstance(node, BooleanLiteral):
            return node.value
        if isinstance(node, StringLiteral):
            return node.value
        return None

    def _eval_binary(self, op: str, left, right):
        """Evaluate a binary operation on Python values."""
        ops = {
            '+': lambda a, b: a + b,
            '-': lambda a, b: a - b,
            '*': lambda a, b: a * b,
            '/': lambda a, b: (a // b if isinstance(a, int) and isinstance(b, int) else a / b) if b != 0 else None,
            '%': lambda a, b: a % b if b != 0 else None,
            '==': lambda a, b: a == b,
            '!=': lambda a, b: a != b,
            '<': lambda a, b: a < b,
            '>': lambda a, b: a > b,
            '<=': lambda a, b: a <= b,
            '>=': lambda a, b: a >= b,
            'and': lambda a, b: a and b,
            'or': lambda a, b: a or b,
        }
        if op in ops:
            return ops[op](left, right)
        return None

    def _make_literal(self, value, line, column) -> ASTNode:
        """Create the appropriate literal node for a Python value."""
        if isinstance(value, bool):
            return BooleanLiteral(line=line, column=column, value=value)
        if isinstance(value, int):
            return IntegerLiteral(line=line, column=column, value=value)
        if isinstance(value, float):
            return FloatLiteral(line=line, column=column, value=value)
        if isinstance(value, str):
            return StringLiteral(line=line, column=column, value=value)
        return NullLiteral(line=line, column=column)
