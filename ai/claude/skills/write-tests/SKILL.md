---
description: "Write comprehensive tests for specified code with boundary value analysis and test case review. Use this skill when the user asks to write tests, create test cases, add test coverage, or generate unit/integration tests for any function, class, or module."
model: opus
argument-hint: "[test-target] [-- notes]"
allowed-tools: Bash(/bin/cat:*)
---

## Overview

!`/bin/cat ~/.claude/common/write_tests_core.md`

## Arguments

- `$ARGUMENTS` format: `<test-target> [-- <notes>]`
  - **test-target**: file path, function name, class name, or module to test
  - **notes** (optional): additional context after `--` separator (e.g., edge cases to focus on, known bugs, constraints)

If `$ARGUMENTS` is empty or the test target is ambiguous, ask the user to clarify using AskUserQuestion before proceeding.

Where the workflow above says "the platform's confirmation primitive," use `AskUserQuestion` (multiSelect for Phase 4).

## Notes on Scope

If the user provides notes via the `--` separator, treat them as additional context:
- Focus areas ("-- especially the edge case where amount is 0")
- Known issues ("-- there's a bug when input is empty string")
- Constraints ("-- don't mock the database")

These notes supplement, not replace, the standard analysis.
