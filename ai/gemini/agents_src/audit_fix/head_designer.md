---
name: audit-fix-designer
description: Designs configuration rewrites for audit items that have no mechanical diff.
kind: local
tools:
  - read_file
  - grep_search
  - glob
  - list_directory
  - write_file
model: gemini-2.5-pro
temperature: 0.2
max_turns: 20
---
