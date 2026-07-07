---
name: pr-create-by-branch
description: >
  Create a GitHub Pull Request from the current branch, auto-generating title
  and body from the diff against the target branch.
model: opus
allowed-tools: Bash(gh:*), Bash(git:*), Bash(/bin/cat:*), AskUserQuestion
argument-hint: '["<title>"] [targetBranch]'
disable-model-invocation: true
---

## Instructions

- Parse `$ARGUMENTS`:
  - Starts with `"` or `'`: the quoted string is `TITLE_ARG`; a remaining token is `TARGET_BRANCH_ARG`.
  - Unquoted single token that is an existing branch on origin: `TARGET_BRANCH_ARG`.
  - Any other non-empty text: the whole text is `TITLE_ARG`.
  - Empty: both unset.
- For every user confirmation, use `AskUserQuestion`.

## Core Workflow

!`/bin/cat ~/.claude/common/pr_create_by_branch_core.md`

!`/bin/cat ~/.claude/common/pr_body_format.md`
