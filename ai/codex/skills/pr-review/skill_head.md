---
name: pr-review
description: >
  Comprehensive PR review using gh command. Use this skill when the user wants to
  review a pull request, analyze a PR for bugs/security/architecture/readability,
  or says things like "PRレビューして", "review PR", "このPRをレビュー", "review pull request".
  Accepts an optional PR number plus extra review instructions; if no PR is provided,
  detects from the current branch automatically.
---

## Instructions

Perform a comprehensive code review for the specified PR (or the PR associated with the current branch if no number is given), then report findings in the structured format defined in the core rules below.

Keep the review read-only and do not create scratch files: never redirect diffs, comments, or command output to files in the repository or elsewhere.
Inspect command output or indexed sources, or run read-only commands directly.

Inputs: parse the user's message as `[prNumber] [additionalInstructions...]`. If the first PR-like token is a PR number (`123` or `#123`) or PR URL, use it as `<PR_NUMBER>` and treat the rest as `<ADDITIONAL_INSTRUCTIONS>`. Otherwise, resolve the current branch's PR and treat any remaining request text as `<ADDITIONAL_INSTRUCTIONS>`:
```bash
gh pr view --json number --jq .number
```

Use only `<PR_NUMBER>` in gh commands. If `<ADDITIONAL_INSTRUCTIONS>` is non-empty, apply it as review emphasis without overriding mandatory duplicate detection, line-number, safety, or output-format rules.

### Local vs Remote File Access

Determine the file access mode before starting:

1. `git branch --show-current` — current local branch
2. `gh pr view <PR_NUMBER> --json title,body,files,commits,baseRefName,headRefName --jq '{title,body,baseRefName,headRefName,files:[.files[]|{path,additions,deletions,changeType}],commits:[.commits[]|{oid,messageHeadline}]}'` — bounded PR metadata
3. Compare the current branch with `headRefName`.

Commit bodies, authors, and dates are intentionally omitted. If a headline needs investigation, fetch that commit on demand with `git show <oid> --no-patch` (local mode) or `gh api repos/{owner}/{repo}/commits/{oid}` (remote mode).

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
