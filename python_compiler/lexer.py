"""Lexer (Tokenizer) for the Satan language.

Reads source code characters and produces a stream of tokens.
Input: Raw source code text
Output: List of Token objects
"""

from tokens import Token, TokenType, KEYWORDS


class LexerError(Exception):
    def __init__(self, message, line, column):
        self.line = line
        self.column = column
        super().__init__(f"Lexer Error at L{line}:{column}: {message}")


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens = []

    def peek(self) -> str | None:
        if self.pos < len(self.source):
            return self.source[self.pos]
        return None

    def peek_next(self) -> str | None:
        if self.pos + 1 < len(self.source):
            return self.source[self.pos + 1]
        return None

    def advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def add_token(self, token_type: TokenType, value=None):
        self.tokens.append(Token(token_type, value, self.line, self.column))

    def skip_whitespace(self):
        while self.pos < len(self.source) and self.source[self.pos] in (' ', '\t', '\r'):
            self.advance()

    def skip_comment(self):
        # Single-line comment: // ...
        if self.peek() == '/' and self.peek_next() == '/':
            self.advance()  # skip first /
            self.advance()  # skip second /
            while self.pos < len(self.source) and self.source[self.pos] != '\n':
                self.advance()

    def read_string(self) -> str:
        quote = self.advance()  # skip opening quote
        result = []
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch == '\\':
                self.advance()
                if self.pos < len(self.source):
                    escape = self.advance()
                    escape_map = {'n': '\n', 't': '\t', '\\': '\\', '"': '"', "'": "'"}
                    result.append(escape_map.get(escape, escape))
            elif ch == quote:
                self.advance()  # skip closing quote
                return ''.join(result)
            elif ch == '\n':
                raise LexerError("Unterminated string literal", self.line, self.column)
            else:
                result.append(self.advance())
        raise LexerError("Unterminated string literal", self.line, self.column)

    def read_number(self) -> Token:
        start_line = self.line
        start_col = self.column
        num_str = []
        is_float = False

        while self.pos < len(self.source) and (self.source[self.pos].isdigit() or self.source[self.pos] == '.'):
            if self.source[self.pos] == '.':
                if is_float:
                    break
                is_float = True
            num_str.append(self.advance())

        value_str = ''.join(num_str)
        if is_float:
            return Token(TokenType.FLOAT, float(value_str), start_line, start_col)
        else:
            return Token(TokenType.INTEGER, int(value_str), start_line, start_col)

    def read_identifier(self) -> Token:
        start_line = self.line
        start_col = self.column
        chars = []

        while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] == '_'):
            chars.append(self.advance())

        word = ''.join(chars)

        # Check if it's a keyword
        if word in KEYWORDS:
            token_type = KEYWORDS[word]
            if token_type == TokenType.TRUE:
                return Token(token_type, True, start_line, start_col)
            elif token_type == TokenType.FALSE:
                return Token(token_type, False, start_line, start_col)
            elif token_type == TokenType.NULL:
                return Token(token_type, None, start_line, start_col)
            return Token(token_type, word, start_line, start_col)

        return Token(TokenType.IDENTIFIER, word, start_line, start_col)

    def tokenize(self) -> list[Token]:
        while self.pos < len(self.source):
            self.skip_whitespace()

            if self.pos >= len(self.source):
                break

            ch = self.source[self.pos]

            # Comments
            if ch == '/' and self.peek_next() == '/':
                self.skip_comment()
                continue

            # Newlines (significant for statement separation)
            if ch == '\n':
                self.add_token(TokenType.NEWLINE, '\\n')
                self.advance()
                continue

            # Strings
            if ch in ('"', "'"):
                start_line = self.line
                start_col = self.column
                value = self.read_string()
                self.tokens.append(Token(TokenType.STRING, value, start_line, start_col))
                continue

            # Numbers
            if ch.isdigit():
                self.tokens.append(self.read_number())
                continue

            # Identifiers and keywords
            if ch.isalpha() or ch == '_':
                self.tokens.append(self.read_identifier())
                continue

            # Two-character operators
            start_line = self.line
            start_col = self.column

            if ch == '=' and self.peek_next() == '=':
                self.advance(); self.advance()
                self.tokens.append(Token(TokenType.EQ, '==', start_line, start_col))
                continue
            if ch == '!' and self.peek_next() == '=':
                self.advance(); self.advance()
                self.tokens.append(Token(TokenType.NEQ, '!=', start_line, start_col))
                continue
            if ch == '<' and self.peek_next() == '=':
                self.advance(); self.advance()
                self.tokens.append(Token(TokenType.LTE, '<=', start_line, start_col))
                continue
            if ch == '>' and self.peek_next() == '=':
                self.advance(); self.advance()
                self.tokens.append(Token(TokenType.GTE, '>=', start_line, start_col))
                continue

            # Single-character operators and delimiters
            single_chars = {
                '+': TokenType.PLUS,
                '-': TokenType.MINUS,
                '*': TokenType.STAR,
                '/': TokenType.SLASH,
                '%': TokenType.PERCENT,
                '=': TokenType.ASSIGN,
                '<': TokenType.LT,
                '>': TokenType.GT,
                '(': TokenType.LPAREN,
                ')': TokenType.RPAREN,
                '{': TokenType.LBRACE,
                '}': TokenType.RBRACE,
                '[': TokenType.LBRACKET,
                ']': TokenType.RBRACKET,
                ',': TokenType.COMMA,
                ';': TokenType.SEMICOLON,
                ':': TokenType.COLON,
            }

            if ch in single_chars:
                self.advance()
                self.tokens.append(Token(single_chars[ch], ch, start_line, start_col))
                continue

            raise LexerError(f"Unexpected character: {ch!r}", self.line, self.column)

        self.tokens.append(Token(TokenType.EOF, None, self.line, self.column))
        return self.tokens
