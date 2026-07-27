---
# GENERATED (SKILL.md): edit skill_head.md / skill_tail.md / ai/common/write_tests_core.md, then regenerate
name: write-tests
description: "Write comprehensive tests for specified code with boundary value analysis and test case review. Use this skill when the user asks to write tests, create test cases, add test coverage, or generate unit/integration tests for any function, class, or module."
---

## Overview

Write thorough, meaningful tests for the specified code target. Focus on boundary value analysis, exhaustive test case enumeration, and interactive review with the user before implementation.

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

Detect the project's test framework and conventions:
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

Present ALL enumerated test cases as a structured markdown table in the response text, then confirm which to implement with the platform's confirmation primitive (multi-select). Format:

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

When writing tests, cover boundary values; when multiple input variations exercise the same code path, structure them as table-driven tests (follow the existing suite's idiom when it differs). Introduce a new test mechanism only when none exists.

- **One assertion per logical concept** — a test can have multiple `expect()` calls if they verify the same behavior, but don't test unrelated things together
- **Minimal mocking** — only mock external dependencies (network, filesystem, databases), not internal modules

#### Boundary Value Implementation Pattern

When implementing boundary tests, group related boundaries. When the existing suite's idiom is table-driven, express the group as one table-driven test with a case per boundary rather than one declaration per case:

```
describe('age validation') {
  test.each([
    ['rejects age below minimum', -1, false],
    ['accepts minimum age', 0, true],
    ['accepts age just above minimum', 1, true],
    ['accepts age just below maximum', 119, true],
    ['accepts maximum age', 120, true],
    ['rejects age above maximum', 121, false],
  ])('%s (%i)', (name, age, valid) => { ... })
}
```

If the existing suite instead declares one test per case, follow that idiom and keep the boundaries grouped together for readability.

### Phase 6: Verify

After writing the tests, run them to confirm they pass. If any test fails:
- Read the failure message
- Determine if it's a test bug or a code bug
- Fix test bugs silently; report code bugs to the user

### Scope

If a test target is given, apply this workflow to it directly. If the target is ambiguous or missing, ask the user to clarify using `ask_user` before proceeding.

Where the workflow above says "the platform's confirmation primitive," use `ask_user`; for Phase 4's multi-select review, list the verdict options and let the user pick multiple by number or name.
