---
name: config-auditor-ambiguity
description: Flags ambiguous config rules with unstable interpretations.
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
