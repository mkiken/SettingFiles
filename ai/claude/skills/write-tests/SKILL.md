---
description: "Write comprehensive tests for specified code with boundary value analysis and test case review. Use this skill when the user asks to write tests, create test cases, add test coverage, or generate unit/integration tests for any function, class, or module."
model: opus
argument-hint: "[test-target] [-- notes]"
---

## Overview

Write thorough, meaningful tests for the specified code target. The skill focuses on boundary value analysis, exhaustive test case enumeration, and interactive review with the user before implementation.

## Arguments

- `$ARGUMENTS` format: `<test-target> [-- <notes>]`
  - **test-target**: file path, function name, class name, or module to test
  - **notes** (optional): additional context after `--` separator (e.g., edge cases to focus on, known bugs, constraints)

If `$ARGUMENTS` is empty or the test target is ambiguous, ask the user to clarify using AskUserQuestion before proceeding.

## Workflow

### Phase 1: Understand the Target

Read the target code thoroughly. Identify:

- Input parameters, their types, and valid ranges
- Return values and side effects
- Branching logic (if/else, switch, early returns, guard clauses)
- Loop boundaries and termination conditions
- Error handling paths (try/catch, error returns)
- Dependencies and external calls
- State mutations

**Skip these** — they don't need tests:
- Simple getters/setters with no logic
- Trivial delegation methods that just forward calls
- Auto-generated code (e.g., ORM models, protobuf stubs)

Focus on code with actual logic: conditionals, calculations, transformations, validation, state machines.

### Phase 2: Detect Test Framework

Inspect the project to determine the test framework and conventions:

- **JavaScript/TypeScript**: check `package.json` for vitest, jest, mocha, etc. Look at existing test files for patterns.
- **Python**: check for pytest, unittest in requirements/pyproject.toml. Look at existing tests.
- **Go**: standard `testing` package. Check for testify usage.
- **Rust**: standard `#[cfg(test)]` module or integration tests.
- **Other**: look for existing test files and follow their conventions.

Also detect:
- Test file naming conventions (e.g., `*.test.ts`, `*_test.go`, `test_*.py`)
- Test directory structure (co-located vs. separate `__tests__/` or `tests/` directory)
- Assertion style (expect/assert/should)
- Mock/stub libraries in use

Follow the project's existing conventions exactly.

#### Scan Existing Tests

Find the test file(s) corresponding to the target using the detected naming convention. If they exist, read them and extract:
- All test names (e.g., `it('...')`, `test('...')`, `def test_...`, `func Test...`)
- describe/suite block names for context

Build a map of what is already covered. You'll use this in Phase 4 to annotate each proposed test case.

### Phase 3: Enumerate Test Cases

Generate a comprehensive list of test cases. For each logical branch or behavior, consider:

#### Boundary Value Analysis
For every numeric parameter, string length, array size, or comparable value:
- **At the boundary**: the exact boundary value
- **Just below**: boundary - 1 (or minimum increment)
- **Just above**: boundary + 1 (or minimum increment)

Example: if a function accepts ages 0-120:
- Test with: -1, 0, 1, 119, 120, 121

#### Standard Test Categories
- **Normal cases**: typical valid inputs that exercise the happy path
- **Boundary values**: edges of valid ranges as described above
- **Equivalence partitioning**: one representative from each equivalence class
- **Error cases**: invalid inputs, null/undefined, wrong types, empty collections
- **State transitions**: if the target has state, test transition sequences
- **Concurrency** (if applicable): race conditions, ordering dependencies

### Phase 4: Review Test Cases with User

Present ALL enumerated test cases in a structured list using AskUserQuestion. Format:

For each test case, include:
- **Name**: short descriptive name
- **Status**: coverage status based on the existing test scan from Phase 2:
  - `NEW` — no existing test covers this case
  - `EXISTS` — already covered (show the existing test name and file)
  - `PARTIAL` — a similar test exists but misses boundary values or key assertions
- **Reason**: why this test is necessary (or why it might be unnecessary)
- **Verdict**: NEEDED / OPTIONAL / SKIP

Default verdict rules:
- `EXISTS` → default SKIP (already done; let user override if they want to replace or strengthen it)
- `PARTIAL` → default NEEDED
- `NEW` → NEEDED or OPTIONAL based on importance

Group by category (normal, boundary, error, etc.).

Let the user confirm which tests to implement. Respect their decisions — if they say skip something, skip it.

### Phase 5: Implement Tests

Write the confirmed test cases following these principles:

- **One assertion per logical concept** — a test can have multiple `expect()` calls if they verify the same behavior, but don't test unrelated things together
- **Arrange-Act-Assert** structure: setup, execute, verify
- **Descriptive test names** that explain the scenario and expected outcome (e.g., `should return error when age is negative` not `test1`)
- **No test interdependence** — each test must work in isolation
- **Minimal mocking** — only mock external dependencies (network, filesystem, databases), not internal modules
- **Use the project's existing test patterns** — match style, naming, structure

#### Boundary Value Implementation Pattern

When implementing boundary tests, group related boundaries:

```
describe('age validation') {
  test('rejects age below minimum (boundary - 1)')
  test('accepts minimum age (boundary)')
  test('accepts age just above minimum (boundary + 1)')
  test('accepts age just below maximum (boundary - 1)')
  test('accepts maximum age (boundary)')
  test('rejects age above maximum (boundary + 1)')
}
```

### Phase 6: Verify

After writing the tests, run them to confirm they pass. If any test fails:
- Read the failure message
- Determine if it's a test bug or a code bug
- Fix test bugs silently; report code bugs to the user

## Notes on Scope

If the user provides notes via the `--` separator, treat them as additional context:
- Focus areas ("-- especially the edge case where amount is 0")
- Known issues ("-- there's a bug when input is empty string")
- Constraints ("-- don't mock the database")

These notes supplement, not replace, the standard analysis.
