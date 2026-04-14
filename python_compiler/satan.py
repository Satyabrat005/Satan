#!/usr/bin/env python3
"""
Satan Compiler - Main CLI Entry Point

Usage:
    python satan.py <file.satan>           Run a .satan file
    python satan.py <file.satan> --tokens  Show lexer token output
    python satan.py <file.satan> --ast     Show parsed AST
    python satan.py <file.satan> --opt     Show optimized AST
    python satan.py -e "code"              Execute inline code
    python satan.py                        Start interactive REPL

Satan Language Compiler Pipeline:
    Source Code → [Lexer] → Tokens → [Parser] → AST → [Optimizer] → Optimized AST → [Interpreter] → Output
"""

import sys
import os

from lexer import Lexer, LexerError
from parser import Parser, ParseError
from optimizer import Optimizer
from interpreter import Interpreter, RuntimeError as SatanRuntimeError
from ast_nodes import (
    Program, IntegerLiteral, FloatLiteral, StringLiteral, BooleanLiteral,
    NullLiteral, Identifier, BinaryOp, UnaryOp, FunctionCall, ArrayLiteral,
    IndexAccess, LetStatement, AssignStatement, PrintStatement, ReturnStatement,
    ExpressionStatement, IfStatement, WhileStatement, FunctionDef,
)


def format_ast(node, indent=0) -> str:
    """Pretty-print an AST node."""
    pad = "  " * indent

    if isinstance(node, Program):
        lines = [f"{pad}Program:"]
        for stmt in node.statements:
            lines.append(format_ast(stmt, indent + 1))
        return "\n".join(lines)

    if isinstance(node, IntegerLiteral):
        return f"{pad}Int({node.value})"
    if isinstance(node, FloatLiteral):
        return f"{pad}Float({node.value})"
    if isinstance(node, StringLiteral):
        return f"{pad}String({node.value!r})"
    if isinstance(node, BooleanLiteral):
        return f"{pad}Bool({node.value})"
    if isinstance(node, NullLiteral):
        return f"{pad}Null"
    if isinstance(node, Identifier):
        return f"{pad}Ident({node.name})"

    if isinstance(node, BinaryOp):
        lines = [f"{pad}BinaryOp({node.op}):"]
        lines.append(format_ast(node.left, indent + 1))
        lines.append(format_ast(node.right, indent + 1))
        return "\n".join(lines)

    if isinstance(node, UnaryOp):
        lines = [f"{pad}UnaryOp({node.op}):"]
        lines.append(format_ast(node.operand, indent + 1))
        return "\n".join(lines)

    if isinstance(node, LetStatement):
        lines = [f"{pad}Let({node.name}):"]
        lines.append(format_ast(node.value, indent + 1))
        return "\n".join(lines)

    if isinstance(node, AssignStatement):
        lines = [f"{pad}Assign({node.name}):"]
        lines.append(format_ast(node.value, indent + 1))
        return "\n".join(lines)

    if isinstance(node, PrintStatement):
        lines = [f"{pad}Print:"]
        lines.append(format_ast(node.expression, indent + 1))
        return "\n".join(lines)

    if isinstance(node, ReturnStatement):
        lines = [f"{pad}Return:"]
        if node.value:
            lines.append(format_ast(node.value, indent + 1))
        return "\n".join(lines)

    if isinstance(node, ExpressionStatement):
        lines = [f"{pad}ExprStmt:"]
        lines.append(format_ast(node.expression, indent + 1))
        return "\n".join(lines)

    if isinstance(node, IfStatement):
        lines = [f"{pad}If:"]
        lines.append(f"{pad}  condition:")
        lines.append(format_ast(node.condition, indent + 2))
        lines.append(f"{pad}  then:")
        for s in node.then_body:
            lines.append(format_ast(s, indent + 2))
        if node.else_body:
            lines.append(f"{pad}  else:")
            for s in node.else_body:
                lines.append(format_ast(s, indent + 2))
        return "\n".join(lines)

    if isinstance(node, WhileStatement):
        lines = [f"{pad}While:"]
        lines.append(f"{pad}  condition:")
        lines.append(format_ast(node.condition, indent + 2))
        lines.append(f"{pad}  body:")
        for s in node.body:
            lines.append(format_ast(s, indent + 2))
        return "\n".join(lines)

    if isinstance(node, FunctionDef):
        lines = [f"{pad}FnDef({node.name}({', '.join(node.params)})):"]
        for s in node.body:
            lines.append(format_ast(s, indent + 1))
        return "\n".join(lines)

    if isinstance(node, FunctionCall):
        lines = [f"{pad}Call({node.name}):"]
        for arg in node.arguments:
            lines.append(format_ast(arg, indent + 1))
        return "\n".join(lines)

    if isinstance(node, ArrayLiteral):
        lines = [f"{pad}Array:"]
        for el in node.elements:
            lines.append(format_ast(el, indent + 1))
        return "\n".join(lines)

    if isinstance(node, IndexAccess):
        lines = [f"{pad}Index:"]
        lines.append(format_ast(node.obj, indent + 1))
        lines.append(format_ast(node.index, indent + 1))
        return "\n".join(lines)

    return f"{pad}<{type(node).__name__}>"


def compile_source(source: str, show_tokens=False, show_ast=False, show_opt=False):
    """Run the full compilation pipeline on source code."""

    # Stage 1: Lexer
    lexer = Lexer(source)
    tokens = lexer.tokenize()

    if show_tokens:
        print("=== LEXER OUTPUT (Token Stream) ===")
        for tok in tokens:
            if tok.type.name != "NEWLINE":
                print(f"  {tok}")
        print()

    # Stage 2: Parser
    parser = Parser(tokens)
    ast = parser.parse()

    if show_ast:
        print("=== PARSER OUTPUT (AST) ===")
        print(format_ast(ast))
        print()

    # Stage 3: Optimizer
    optimizer = Optimizer()
    optimized_ast = optimizer.optimize(ast)

    if show_opt:
        print(f"=== OPTIMIZER OUTPUT (Optimized AST) [{optimizer.optimizations_applied} optimizations] ===")
        print(format_ast(optimized_ast))
        print()

    # Stage 4: Interpreter (Code Generator)
    interpreter = Interpreter()
    if show_tokens or show_ast or show_opt:
        print("=== INTERPRETER OUTPUT ===")
    interpreter.run(optimized_ast)

    return interpreter


def run_file(filename: str, **kwargs):
    """Read and execute a .satan file."""
    if not os.path.exists(filename):
        print(f"Error: File not found: {filename}", file=sys.stderr)
        sys.exit(1)

    with open(filename, 'r') as f:
        source = f.read()

    try:
        compile_source(source, **kwargs)
    except (LexerError, ParseError, SatanRuntimeError) as e:
        print(f"\n{e}", file=sys.stderr)
        sys.exit(1)


def run_repl():
    """Interactive REPL (Read-Eval-Print Loop)."""
    print("Satan Language REPL v1.0")
    print('Type "exit" to quit, "help" for usage.\n')

    interpreter = Interpreter()
    optimizer = Optimizer()

    while True:
        try:
            line = input("satan> ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        line = line.strip()
        if not line:
            continue
        if line == "exit":
            print("Goodbye!")
            break
        if line == "help":
            print("""
Satan Language Quick Reference:
  let x = 10              Variable declaration
  x = 20                  Assignment
  print(x)                Print a value
  fn add(a, b) { ... }   Function definition
  if x > 5 { ... }       Conditional
  while x > 0 { ... }    Loop
  [1, 2, 3]              Array literal
  // comment              Comment

Built-in functions: len, str, int, float, type, input, push, pop, range, abs, min, max
""")
            continue

        try:
            lexer = Lexer(line)
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            ast = parser.parse()
            optimized = optimizer.optimize(ast)
            interpreter.run(optimized)
        except (LexerError, ParseError, SatanRuntimeError) as e:
            print(f"  Error: {e}")


def main():
    args = sys.argv[1:]

    if not args:
        run_repl()
        return

    show_tokens = "--tokens" in args
    show_ast = "--ast" in args
    show_opt = "--opt" in args

    # Filter out flags
    files = [a for a in args if not a.startswith("--") and a != "-e"]

    # Inline execution
    if "-e" in args:
        idx = args.index("-e")
        if idx + 1 < len(args):
            code = args[idx + 1]
            try:
                compile_source(code, show_tokens=show_tokens, show_ast=show_ast, show_opt=show_opt)
            except (LexerError, ParseError, SatanRuntimeError) as e:
                print(f"\n{e}", file=sys.stderr)
                sys.exit(1)
            return

    if files:
        run_file(files[0], show_tokens=show_tokens, show_ast=show_ast, show_opt=show_opt)
    else:
        run_repl()


if __name__ == "__main__":
    main()
