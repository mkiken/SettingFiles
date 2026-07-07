---
name: config-auditor-conflict
description: Detects contradictions between configuration rules.
kind: local
tools:
  - read_file
  - grep_search
  - glob
  - list_directory
model: gemini-2.5-pro
temperature: 0.2
max_turns: 15
---
