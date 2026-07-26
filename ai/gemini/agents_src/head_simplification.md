---
name: pr-reviewer-simplification
description: Proposes behavior-preserving readability and simplification improvements for PR diffs.
kind: local
tools:
  - read_file
  - grep_search
  - glob
  - run_shell_command
model: gemini-2.5-pro
temperature: 0.2
max_turns: 15
---
