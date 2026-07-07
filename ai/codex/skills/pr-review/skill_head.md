---
name: pr-review
description: >
  Comprehensive PR review using gh command. Use this skill when the user wants to
  review a pull request, analyze a PR for bugs/security/architecture/readability,
  or says things like "PRレビューして", "review PR", "このPRをレビュー", "review pull request".
  Accepts an optional PR number; if not provided, detects from the current branch automatically.
---

## Instructions

Perform a comprehensive code review for the specified PR (or the PR associated with the current branch if no number is given), then report findings in the structured format defined in the core rules below.

PR number: extract from the user's message if provided. If not provided, run:
```bash
gh pr view --json number --jq .number
```

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

For deeper investigation (files outside the diff, surrounding context), use the access mode determined above.

### Existing Comment Deduplication

Before finalizing each finding, check whether it is already covered by an existing PR comment:

1. `is_resolved == true` or `is_outdated == true` → treat as non-existing. Re-reporting is allowed; append `(参考: 過去にresolved済みの既存コメント #<id> と同様の指摘)` to the detail line.
2. **Mark as duplicate** when: same `path` + line within ±5 AND same root cause, OR same target symbol/concept addressable by the same fix.
3. **Do NOT skip**: same problem type at a different file, or a more specific finding requiring a different fix.
4. Skip only when duplicate confidence is ≥ 70. Below 70, output both.
5. `ai_origin` (author being human/bot/AI) does not affect the duplicate decision — judge on content only.

When findings are skipped, add `## [既コメント済] スキップした指摘` immediately before the Post-Review block (omit entirely when nothing is skipped):

```
- **[path:line]** Category / 既存コメント ID: <id> (resolved=<bool>, ai_origin=<value>) — <reason>
```

### Core Review Rules
