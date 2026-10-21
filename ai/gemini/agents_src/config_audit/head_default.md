---
name: config-auditor-default
description: Flags config rules duplicating assistant default behavior.
kind: local
tools:
  - read_file
  - grep_search
  - glob
  - list_directory
model: flash
temperature: 0.2
max_turns: 15
---
