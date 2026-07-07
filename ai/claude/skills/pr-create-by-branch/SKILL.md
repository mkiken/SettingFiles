---
name: pr-create-by-branch
description: >
  Create a GitHub Pull Request from the current branch, auto-generating title
  and body from the diff against the target branch.
model: opus
allowed-tools: Bash(gh:*), Bash(git:*), Bash(/bin/cat:*), AskUserQuestion
argument-hint: "[targetBranch]"
disable-model-invocation: true
---

## Instructions

- `TARGET_BRANCH_ARG` = `$ARGUMENTS`.
- For every user confirmation, use `AskUserQuestion`.

## Core Workflow

!`/bin/cat ~/.claude/common/pr_create_by_branch_core.md`
