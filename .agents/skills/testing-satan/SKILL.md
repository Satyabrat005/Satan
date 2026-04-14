# Testing the Satan Language Interpreter & REPL

## Build

No Makefile or CMake yet. Build manually:

```bash
g++ -std=c++20 -I include -o satan main.cpp src/lexer.cpp src/parser.cpp src/interpreter.cpp src/environment.cpp src/repl.cpp
```

## Running

- **REPL mode:** `./satan` (no arguments)
- **File mode:** `./satan <script.satan>`
- **Usage error:** `./satan arg1 arg2` exits with code 1 and prints `Usage: satan [script.satan]`

## Testing the REPL via Shell

The REPL reads from stdin, so pipe input for automated testing:

```bash
echo -e 'let x = 5 + 3;\nsummon x;\nexit' | ./satan
```

Each line is evaluated independently. Use `exit` or `quit` to cleanly exit. EOF (Ctrl+D / empty stdin) also exits cleanly.

The REPL prompt `satan>` appears for each line of input, so piped output will show `satan>` interleaved with results.

## Key Test Scenarios

1. **Basic arithmetic:** `let a = 2 + 3; summon a;` should print `5`
2. **Error recovery:** Invalid syntax or runtime errors (e.g., division by zero) should print an error message but NOT crash the REPL
3. **Variable persistence:** Variables defined on one line are accessible on subsequent lines
4. **Cross-line function calls:** Define a function on one line, call it on the next. This tests that function bodies survive across REPL iterations (previously a use-after-free bug with `unique_ptr`, now fixed with `shared_ptr`)
5. **File execution:** `./satan tests/test_if.satan` should print `Hello, World!` and `x is large`

## Language Syntax Notes

- Variable declaration: `let x = <expr>;` or `var x = <expr>;`
- Print output: `summon <expr>;` (domain-specific keyword for printing)
- Function declaration: `func <name>(<params>) { <body> }` or `fun <name>(<params>) { <body> }` (both keywords accepted)
- Return: `return <expr>;`
- Other keywords: `print`, `assemble`, `if/else`, `while`, `for`, `break`, `continue`

## Known Behaviors

- **Single-line REPL only:** Multi-line constructs must be entered on a single line (e.g., `func foo(x) { summon x * 2; }`). No multi-line continuation support.
- **String values evaluate to `0.0`:** Only `summon` has special-case string printing. `print` and `assemble` will print `0` for strings.
- **Variable shadowing warning:** Re-declaring a variable in the same scope prints `[env] variable x shadows outer variable`.
- **Error format:** Parse errors start with `[error]`, runtime errors start with `[runtime error]`.

## Devin Secrets Needed

None — this is a local C++ project with no external dependencies or services.
