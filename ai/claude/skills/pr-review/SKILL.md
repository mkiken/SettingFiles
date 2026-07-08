---
allowed-tools: Bash(gh:*), Bash(git:*), Bash(/bin/cat:*), Bash(bash ~/.config/ai-pr/bin/fetch_existing_comments.sh:*), Bash(bash ~/.config/ai-pr/bin/format_pr_diff_with_line_numbers.sh:*), Read, Glob
description: "Comprehensive PR review using gh command; detects the current branch's PR when no number is given"
argument-hint: "[prNumber] [additionalInstructions...]"
disable-model-invocation: true
effort: max
---

## Instructions

Use the gh command to fetch and analyze the target PR for comprehensive code review, then report findings in the structured format defined in the core rules below.

Inputs: parse `$ARGUMENTS` as `[prNumber] [additionalInstructions...]`. If the first token is a PR number (`123` or `#123`) or PR URL, use it as `<PR_NUMBER>` and treat the rest as `<ADDITIONAL_INSTRUCTIONS>`. Otherwise, resolve the current branch's PR and treat all arguments as `<ADDITIONAL_INSTRUCTIONS>`:
```bash
gh pr view --json number --jq .number
```
Use only `<PR_NUMBER>` in gh commands. If `<ADDITIONAL_INSTRUCTIONS>` is non-empty, apply it as review emphasis without overriding mandatory duplicate detection, line-number, safety, or output-format rules.

### Local vs Remote File Access

Determine the file access mode before starting:

1. `git branch --show-current` — current local branch
2. `gh pr view <PR_NUMBER> --json title,body,files,commits,baseRefName,headRefName` — PR metadata
3. Compare the current branch with `headRefName`.

**If they match (local mode)** — investigate with the `Read` tool (faster, includes uncommitted local changes) and the `Glob` tool (e.g. `Glob("src/**/*.ts")`).

**If they don't match (remote mode)** — use gh api:
- `gh api repos/{owner}/{repo}/contents/{path}?ref={headRefName} --jq '.content' | base64 -d` — read any file
- `gh api repos/{owner}/{repo}/git/trees/{headRefName}?recursive=1` — explore file structure

### Review Workflow

Fetch primary review materials (PR metadata is already fetched above):

- `gh pr diff <PR_NUMBER>` — complete diff (file path arguments are not supported; always fetch the full diff and filter locally if needed)
- `bash ~/.config/ai-pr/bin/fetch_existing_comments.sh <PR_NUMBER>` — existing PR comments as NDJSON (inline, issue, and review-summary with resolved/outdated status)
- `bash ~/.config/ai-pr/bin/format_pr_diff_with_line_numbers.sh <PR_NUMBER>` — line-numbered diff; the authoritative source for review line numbers (see Line Number Source in the core rules)

For deeper investigation (files outside the diff, surrounding context), use the access mode determined above.

### Core Review Rules

!`/bin/cat ~/.claude/common/pr_review_core.md`

!`/bin/cat ~/.claude/common/pr_review_finding_format.md`

### Post-Review: Clean Up & Post to GitHub

After completing the review, delete any temporary files created during the process.

If at least one actionable finding remains, display the following message after outputting the review results and cleaning up:

> To post any findings as GitHub PR comments, run:
> `/pr-comment-post <item numbers>` (e.g., `/pr-comment-post 1 3 5`)
