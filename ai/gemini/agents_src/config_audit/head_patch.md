---
name: config-auditor-patch
description: Flags one-off patch rules lacking general value.
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
