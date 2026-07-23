---
name: pr-create-by-branch
description: >
  Create a GitHub Pull Request from the current branch to a target base branch.
  Analyze the branch diff to generate a PR title and body, confirm with the
  user, then run gh pr create. Use when the user wants to create or open a PR,
  says "PRを作って", "PR作成", "プルリクエスト作りたい", "create PR",
  "open a pull request", or invokes `$pr-create-by-branch`. Accepts an
  optional target base branch.
---

## Instructions

- `TITLE_ARG` = the PR title in the user's message (quoted string preferred;
  otherwise free text that is not a branch name).
- `TARGET_BRANCH_ARG` = the target base branch in the user's message.
- For every user confirmation, prefer `request_user_input` when all required choices fit within the tool's option limit, passing each required label exactly once. If they exceed the limit, ask in plain text with numbered options.
