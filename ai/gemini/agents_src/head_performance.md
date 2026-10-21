---
name: pr-reviewer-performance
description: Detects runtime performance regressions in PR diffs.
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
