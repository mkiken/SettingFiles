---
name: pr-body
description: >
  Generate and optionally update a GitHub Pull Request body using gh.
  Use this skill when the user asks Codex to create, regenerate, rewrite,
  or apply a PR description/body, says "PR body", "PR本文", "PR説明を作って",
  or invokes `$pr-body`. Accepts an optional PR number; if omitted, detect
  the PR for the current branch.
---

## Inputs

Extract the PR number from the user's message; if absent, run:

```bash
gh pr view --json number --jq .number
```

Ask all questions and confirmations in plain text, including asking for a PR
number when none is found. In the rules below, `<PR_NUMBER>` refers to this PR
number.

## Gather Context

Run these commands before drafting:

```bash
gh pr view <PR_NUMBER> --json number,url,title,body,author,headRefName,baseRefName
test -f .github/PULL_REQUEST_TEMPLATE.md && sed -n '1,240p' .github/PULL_REQUEST_TEMPLATE.md || printf '%s\n' 'NO_TEMPLATE'
gh pr diff <PR_NUMBER>
gh pr diff <PR_NUMBER> --name-only
```
