---
name: pr-reviewer-claims
description: Adversarially verifies PR claims (description, commits) against the actual diff.
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
