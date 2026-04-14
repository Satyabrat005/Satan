"""Tree-walking Interpreter (Code Generator) for the Satan language.

Executes the optimized AST by walking the tree and evaluating nodes.
Input: Optimized AST
Output: Program execution (side effects like print, return values)

This serves as the "Code Generator" stage — instead of emitting machine code,
it directly interprets the AST, which is equivalent for a scripting language.
"""

from ast_nodes import (
    ASTNode, Program, IntegerLiteral, FloatLiteral, StringLiteral,
    BooleanLiteral, NullLiteral, Identifier, BinaryOp, UnaryOp,
    FunctionCall, ArrayLiteral, IndexAccess, LetStatement, AssignStatement,
    PrintStatement, ReturnStatement, ExpressionStatement, IfStatement,
    WhileStatement, FunctionDef,
)


class RuntimeError(Exception):
    def __init__(self, message, line=0, column=0):
        self.line = line
        self.column = column
        super().__init__(f"Runtime Error at L{line}:{column}: {message}")


class ReturnSignal(Exception):
    """Used to unwind the call stack when a return statement is hit."""
    def __init__(self, value):
        self.value = value


class Environment:
    """Variable scope with parent chain for lexical scoping."""

    def __init__(self, parent=None):
        self.variables = {}
        self.parent = parent

    def get(self, name: str):
        if name in self.variables:
            return self.variables[name]
        if self.parent:
            return self.parent.get(name)
        return None

    def has(self, name: str) -> bool:
        if name in self.variables:
            return True
        if self.parent:
            return self.parent.has(name)
        return False

    def set(self, name: str, value):
        self.variables[name] = value

    def update(self, name: str, value):
        """Update an existing variable, searching up the scope chain."""
        if name in self.variables:
            self.variables[name] = value
            return True
        if self.parent:
            return self.parent.update(name, value)
        return False


class SatanFunction:
    """Represents a user-defined Satan function."""
    def __init__(self, name, params, body, closure_env):
        self.name = name
        self.params = params
        self.body = body
        self.closure_env = closure_env

    def __repr__(self):
        return f"<fn {self.name}({', '.join(self.params)})>"


class Interpreter:
    def __init__(self):
        self.global_env = Environment()
        self.output = []  # Captured print output
        self._setup_builtins()

    def _setup_builtins(self):
        """Register built-in functions."""
        self.builtins = {
            "len": self._builtin_len,
            "str": self._builtin_str,
            "int": self._builtin_int,
            "float": self._builtin_float,
            "type": self._builtin_type,
            "input": self._builtin_input,
            "push": self._builtin_push,
            "pop": self._builtin_pop,
            "range": self._builtin_range,
            "abs": self._builtin_abs,
            "min": self._builtin_min,
            "max": self._builtin_max,
        }

    def run(self, program: Program):
        """Execute the entire program."""
        self.execute_statements(program.statements, self.global_env)

    def execute_statements(self, statements: list[ASTNode], env: Environment):
        """Execute a list of statements in the given environment."""
        for stmt in statements:
            self.execute(stmt, env)

    def execute(self, node: ASTNode, env: Environment):
        """Execute a single AST node."""
        if isinstance(node, LetStatement):
            value = self.evaluate(node.value, env)
            env.set(node.name, value)

        elif isinstance(node, AssignStatement):
            value = self.evaluate(node.value, env)
            if not env.update(node.name, value):
                raise RuntimeError(f"Undefined variable: '{node.name}'", node.line, node.column)

        elif isinstance(node, PrintStatement):
            value = self.evaluate(node.expression, env)
            output_str = self._to_string(value)
            print(output_str)
            self.output.append(output_str)

        elif isinstance(node, ReturnStatement):
            value = self.evaluate(node.value, env) if node.value else None
            raise ReturnSignal(value)

        elif isinstance(node, ExpressionStatement):
            self.evaluate(node.expression, env)

        elif isinstance(node, IfStatement):
            condition = self.evaluate(node.condition, env)
            if self._is_truthy(condition):
                self.execute_statements(node.then_body, env)
            elif node.else_body:
                self.execute_statements(node.else_body, env)

        elif isinstance(node, WhileStatement):
            iteration = 0
            max_iterations = 1_000_000
            while self._is_truthy(self.evaluate(node.condition, env)):
                self.execute_statements(node.body, env)
                iteration += 1
                if iteration > max_iterations:
                    raise RuntimeError("Infinite loop detected (exceeded 1M iterations)", node.line, node.column)

        elif isinstance(node, FunctionDef):
            func = SatanFunction(node.name, node.params, node.body, env)
            env.set(node.name, func)

        else:
            raise RuntimeError(f"Unknown statement type: {type(node).__name__}", node.line, node.column)

    def evaluate(self, node: ASTNode, env: Environment):
        """Evaluate an expression and return its value."""
        if isinstance(node, IntegerLiteral):
            return node.value
        if isinstance(node, FloatLiteral):
            return node.value
        if isinstance(node, StringLiteral):
            return node.value
        if isinstance(node, BooleanLiteral):
            return node.value
        if isinstance(node, NullLiteral):
            return None

        if isinstance(node, Identifier):
            if not env.has(node.name):
                raise RuntimeError(f"Undefined variable: '{node.name}'", node.line, node.column)
            return env.get(node.name)

        if isinstance(node, BinaryOp):
            return self._eval_binary(node, env)

        if isinstance(node, UnaryOp):
            return self._eval_unary(node, env)

        if isinstance(node, FunctionCall):
            return self._call_function(node, env)

        if isinstance(node, ArrayLiteral):
            return [self.evaluate(el, env) for el in node.elements]

        if isinstance(node, IndexAccess):
            obj = self.evaluate(node.obj, env)
            index = self.evaluate(node.index, env)
            if isinstance(obj, list):
                if not isinstance(index, int):
                    raise RuntimeError("Array index must be an integer", node.line, node.column)
                if index < 0 or index >= len(obj):
                    raise RuntimeError(f"Index {index} out of bounds (array length {len(obj)})", node.line, node.column)
                return obj[index]
            if isinstance(obj, str):
                if not isinstance(index, int):
                    raise RuntimeError("String index must be an integer", node.line, node.column)
                if index < 0 or index >= len(obj):
                    raise RuntimeError(f"Index {index} out of bounds (string length {len(obj)})", node.line, node.column)
                return obj[index]
            raise RuntimeError("Cannot index into this type", node.line, node.column)

        raise RuntimeError(f"Unknown expression type: {type(node).__name__}", node.line, node.column)

    def _eval_binary(self, node: BinaryOp, env: Environment):
        # Short-circuit evaluation for and/or
        op = node.op
        if op == 'and':
            left = self.evaluate(node.left, env)
            if not self._is_truthy(left):
                return left
            return self.evaluate(node.right, env)
        if op == 'or':
            left = self.evaluate(node.left, env)
            if self._is_truthy(left):
                return left
            return self.evaluate(node.right, env)

        left = self.evaluate(node.left, env)
        right = self.evaluate(node.right, env)

        try:
            if op == '+':
                if isinstance(left, str) or isinstance(right, str):
                    return self._to_string(left) + self._to_string(right)
                return left + right
            elif op == '-':
                return left - right
            elif op == '*':
                if isinstance(left, str) and isinstance(right, int):
                    return left * right
                return left * right
            elif op == '/':
                if right == 0:
                    raise RuntimeError("Division by zero", node.line, node.column)
                if isinstance(left, int) and isinstance(right, int):
                    return left // right  # Integer division for int/int
                return left / right
            elif op == '%':
                if right == 0:
                    raise RuntimeError("Modulo by zero", node.line, node.column)
                return left % right
            elif op == '==':
                return left == right
            elif op == '!=':
                return left != right
            elif op == '<':
                return left < right
            elif op == '>':
                return left > right
            elif op == '<=':
                return left <= right
            elif op == '>=':
                return left >= right
        except TypeError as e:
            raise RuntimeError(
                f"Type error: cannot apply '{op}' to {type(left).__name__} and {type(right).__name__}",
                node.line, node.column
            )

        raise RuntimeError(f"Unknown operator: {op}", node.line, node.column)

    def _eval_unary(self, node: UnaryOp, env: Environment):
        operand = self.evaluate(node.operand, env)
        if node.op == '-':
            if not isinstance(operand, (int, float)):
                raise RuntimeError("Cannot negate non-numeric value", node.line, node.column)
            return -operand
        if node.op == 'not':
            return not self._is_truthy(operand)
        raise RuntimeError(f"Unknown unary operator: {node.op}", node.line, node.column)

    def _call_function(self, node: FunctionCall, env: Environment):
        """Call a function (user-defined or builtin)."""
        # Check builtins first
        if node.name in self.builtins:
            args = [self.evaluate(arg, env) for arg in node.arguments]
            return self.builtins[node.name](args, node)

        # Look up user-defined function
        if not env.has(node.name):
            raise RuntimeError(f"Undefined function: '{node.name}'", node.line, node.column)

        func = env.get(node.name)
        if not isinstance(func, SatanFunction):
            raise RuntimeError(f"'{node.name}' is not a function", node.line, node.column)

        # Check argument count
        if len(node.arguments) != len(func.params):
            raise RuntimeError(
                f"Function '{node.name}' expects {len(func.params)} arguments, got {len(node.arguments)}",
                node.line, node.column
            )

        # Evaluate arguments
        args = [self.evaluate(arg, env) for arg in node.arguments]

        # Create new scope for function execution
        func_env = Environment(parent=func.closure_env)
        for param, arg in zip(func.params, args):
            func_env.set(param, arg)

        # Execute function body
        try:
            self.execute_statements(func.body, func_env)
        except ReturnSignal as ret:
            return ret.value

        return None  # Functions without return statement return null

    def _is_truthy(self, value) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        if isinstance(value, float):
            return value != 0.0
        if isinstance(value, str):
            return len(value) > 0
        if isinstance(value, list):
            return len(value) > 0
        return True

    def _to_string(self, value) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, list):
            return "[" + ", ".join(self._to_string(v) for v in value) + "]"
        if isinstance(value, SatanFunction):
            return repr(value)
        return str(value)

    # ---- Built-in functions ----

    def _builtin_len(self, args, node):
        if len(args) != 1:
            raise RuntimeError("len() takes exactly 1 argument", node.line, node.column)
        val = args[0]
        if isinstance(val, (str, list)):
            return len(val)
        raise RuntimeError("len() argument must be a string or array", node.line, node.column)

    def _builtin_str(self, args, node):
        if len(args) != 1:
            raise RuntimeError("str() takes exactly 1 argument", node.line, node.column)
        return self._to_string(args[0])

    def _builtin_int(self, args, node):
        if len(args) != 1:
            raise RuntimeError("int() takes exactly 1 argument", node.line, node.column)
        try:
            return int(args[0])
        except (ValueError, TypeError):
            raise RuntimeError(f"Cannot convert to int: {args[0]!r}", node.line, node.column)

    def _builtin_float(self, args, node):
        if len(args) != 1:
            raise RuntimeError("float() takes exactly 1 argument", node.line, node.column)
        try:
            return float(args[0])
        except (ValueError, TypeError):
            raise RuntimeError(f"Cannot convert to float: {args[0]!r}", node.line, node.column)

    def _builtin_type(self, args, node):
        if len(args) != 1:
            raise RuntimeError("type() takes exactly 1 argument", node.line, node.column)
        val = args[0]
        if val is None:
            return "null"
        if isinstance(val, bool):
            return "boolean"
        if isinstance(val, int):
            return "integer"
        if isinstance(val, float):
            return "float"
        if isinstance(val, str):
            return "string"
        if isinstance(val, list):
            return "array"
        if isinstance(val, SatanFunction):
            return "function"
        return "unknown"

    def _builtin_input(self, args, node):
        if len(args) > 1:
            raise RuntimeError("input() takes 0 or 1 arguments", node.line, node.column)
        prompt = self._to_string(args[0]) if args else ""
        return input(prompt)

    def _builtin_push(self, args, node):
        if len(args) != 2:
            raise RuntimeError("push() takes exactly 2 arguments (array, value)", node.line, node.column)
        if not isinstance(args[0], list):
            raise RuntimeError("First argument to push() must be an array", node.line, node.column)
        args[0].append(args[1])
        return args[0]

    def _builtin_pop(self, args, node):
        if len(args) != 1:
            raise RuntimeError("pop() takes exactly 1 argument (array)", node.line, node.column)
        if not isinstance(args[0], list):
            raise RuntimeError("Argument to pop() must be an array", node.line, node.column)
        if len(args[0]) == 0:
            raise RuntimeError("Cannot pop from empty array", node.line, node.column)
        return args[0].pop()

    def _builtin_range(self, args, node):
        if len(args) == 1:
            return list(range(int(args[0])))
        elif len(args) == 2:
            return list(range(int(args[0]), int(args[1])))
        elif len(args) == 3:
            return list(range(int(args[0]), int(args[1]), int(args[2])))
        raise RuntimeError("range() takes 1 to 3 arguments", node.line, node.column)

    def _builtin_abs(self, args, node):
        if len(args) != 1:
            raise RuntimeError("abs() takes exactly 1 argument", node.line, node.column)
        return abs(args[0])

    def _builtin_min(self, args, node):
        if len(args) == 1 and isinstance(args[0], list):
            return min(args[0])
        if len(args) >= 2:
            return min(args)
        raise RuntimeError("min() requires at least 2 arguments or 1 array", node.line, node.column)

    def _builtin_max(self, args, node):
        if len(args) == 1 and isinstance(args[0], list):
            return max(args[0])
        if len(args) >= 2:
            return max(args)
        raise RuntimeError("max() requires at least 2 arguments or 1 array", node.line, node.column)
