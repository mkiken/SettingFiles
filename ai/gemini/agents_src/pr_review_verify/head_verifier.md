---
name: pr-review-verifier
description: Adversarially re-verifies High-priority review findings in a fresh context.
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
