---
name: pr-reviewer-tests
description: Reviews test coverage and quality for PR diffs.
kind: local
tools:
  - read_file
  - grep_search
  - glob
  - run_shell_command
model: flash
temperature: 0.2
max_turns: 15
---
