---
name: pr-reviewer-consistency
description: Detects divergence from existing repository conventions and reusable code in PR diffs.
kind: local
tools:
  - read_file
  - grep_search
  - glob
  - run_shell_command
model: gemini-2.5-pro
temperature: 0.2
max_turns: 20
---
