---
name: audit-fix-considerer
description: Judges whether one audit item should be applied and writes the recommendation to a file.
kind: local
tools:
  - read_file
  - grep_search
  - glob
  - list_directory
  - write_file
model: flash
temperature: 0.2
max_turns: 20
---
