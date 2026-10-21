---
name: audit-fix-implementer
description: Applies an approved configuration rewrite design verbatim.
kind: local
tools:
  - read_file
  - grep_search
  - glob
  - list_directory
  - replace
  - write_file
model: flash
temperature: 0.1
max_turns: 20
---
