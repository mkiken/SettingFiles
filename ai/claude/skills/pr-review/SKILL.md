---
allowed-tools: Bash(gh:*), Bash(git:*), Bash(/bin/cat:*), Read, Glob
description: "Comprehensive PR review using gh command for specified PR number"
argument-hint: [prNumber]
effort: max
---

## Instructions

Use the gh command to fetch and analyze PR #$ARGUMENTS for comprehensive code review, then report findings in the structured format defined in the core rules below.

### Local vs Remote File Access

Determine the file access mode before starting:

1. `git branch --show-current` — current local branch
2. `gh pr view $ARGUMENTS --json title,body,files,commits,baseRefName,headRefName` — PR metadata
3. Compare the current branch with `headRefName`.

**If they match (local mode)** — investigate with the `Read` tool (faster, includes uncommitted local changes) and the `Glob` tool (e.g. `Glob("src/**/*.ts")`).

**If they don't match (remote mode)** — use gh api:
- `gh api repos/{owner}/{repo}/contents/{path}?ref={headRefName} --jq '.content' | base64 -d` — read any file
- `gh api repos/{owner}/{repo}/git/trees/{headRefName}?recursive=1` — explore file structure

### Review Workflow

Fetch primary review materials (PR metadata is already fetched above):

- `gh pr diff $ARGUMENTS` — complete diff (file path arguments are not supported; always fetch the full diff and filter locally if needed)
- `bash ~/.config/ai-pr/bin/fetch_existing_comments.sh $ARGUMENTS` — existing PR comments as NDJSON (inline, issue, and review-summary with resolved/outdated status)

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

!`/bin/cat ~/.claude/common/pr_review_core.md`

### Post-Review: Clean Up & Post to GitHub

After completing the review, you MUST delete any temporary files you created during the process (e.g., `diff.txt`, `pr_diff.txt`) using the Bash tool.

If at least one actionable finding remains, display the following message after outputting the review results and cleaning up:

> To post any findings as GitHub PR comments, run:
> `/pr-comment-post <item numbers>` (e.g., `/pr-comment-post 1 3 5`)
