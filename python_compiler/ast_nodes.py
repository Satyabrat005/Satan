"""AST (Abstract Syntax Tree) node definitions for the Satan language.

These nodes represent the program structure after parsing.
Each node type corresponds to a language construct.
"""

from dataclasses import dataclass, field
from typing import Any


# Base class
@dataclass
class ASTNode:
    line: int = 0
    column: int = 0


# Program (root node)
@dataclass
class Program(ASTNode):
    statements: list[ASTNode] = field(default_factory=list)


# Literals
@dataclass
class IntegerLiteral(ASTNode):
    value: int = 0


@dataclass
class FloatLiteral(ASTNode):
    value: float = 0.0


@dataclass
class StringLiteral(ASTNode):
    value: str = ""


@dataclass
class BooleanLiteral(ASTNode):
    value: bool = False


@dataclass
class NullLiteral(ASTNode):
    pass


# Identifiers
@dataclass
class Identifier(ASTNode):
    name: str = ""


# Expressions
@dataclass
class BinaryOp(ASTNode):
    left: ASTNode = None
    op: str = ""
    right: ASTNode = None


@dataclass
class UnaryOp(ASTNode):
    op: str = ""
    operand: ASTNode = None


@dataclass
class FunctionCall(ASTNode):
    name: str = ""
    arguments: list[ASTNode] = field(default_factory=list)


@dataclass
class ArrayLiteral(ASTNode):
    elements: list[ASTNode] = field(default_factory=list)


@dataclass
class IndexAccess(ASTNode):
    obj: ASTNode = None
    index: ASTNode = None


# Statements
@dataclass
class LetStatement(ASTNode):
    name: str = ""
    value: ASTNode = None


@dataclass
class AssignStatement(ASTNode):
    name: str = ""
    value: ASTNode = None


@dataclass
class PrintStatement(ASTNode):
    expression: ASTNode = None


@dataclass
class ReturnStatement(ASTNode):
    value: ASTNode = None


@dataclass
class ExpressionStatement(ASTNode):
    expression: ASTNode = None


# Control Flow
@dataclass
class IfStatement(ASTNode):
    condition: ASTNode = None
    then_body: list[ASTNode] = field(default_factory=list)
    else_body: list[ASTNode] = field(default_factory=list)


@dataclass
class WhileStatement(ASTNode):
    condition: ASTNode = None
    body: list[ASTNode] = field(default_factory=list)


# Functions
@dataclass
class FunctionDef(ASTNode):
    name: str = ""
    params: list[str] = field(default_factory=list)
    body: list[ASTNode] = field(default_factory=list)
