---
name: pr-create-by-branch
description: >
  Create a GitHub PR from the current branch. Accepts an optional target base
  branch.
---

## Instructions

- `TITLE_ARG` = the PR title in the user's message (quoted string preferred;
  otherwise free text that is not a branch name).
- `TARGET_BRANCH_ARG` = the target base branch in the user's message.
- For every user confirmation, prefer `request_user_input` when all required choices fit within the tool's option limit, passing each required label exactly once. If they exceed the limit, ask in plain text with numbered options.
