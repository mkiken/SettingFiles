---
name: pr-create-by-branch
description: >
  Create a new GitHub Pull Request from the current branch to a specified target branch.
  Analyzes the diff to auto-generate PR title and body with summary, file changes,
  review focus points, breaking changes, and additional notes.
  Use this skill when the user wants to create a PR, open a pull request,
  or says things like "PRを作って", "PR作成", "プルリクエスト作りたい",
  "create PR to main", "open a PR". Always use this when creating new PRs.
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
