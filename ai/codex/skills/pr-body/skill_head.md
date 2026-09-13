---
name: pr-body
description: Draft or update a GitHub Pull Request body. Use when the user asks for a PR description, including `$pr-body`.
---

## Inputs

Extract the PR number from the user's message; if absent, run:

```bash
gh pr view --json number --jq .number
```

If no PR number is found, ask the user for it. In the rules below,
`<PR_NUMBER>` refers to this PR number.

## Gather Context

Run these commands before drafting:

```bash
gh pr view <PR_NUMBER> --json number,url,title,body,author,headRefName,baseRefName
cat .github/PULL_REQUEST_TEMPLATE.md 2>/dev/null || printf '%s\n' 'NO_TEMPLATE'
gh pr diff <PR_NUMBER>
gh pr diff <PR_NUMBER> --name-only
```
