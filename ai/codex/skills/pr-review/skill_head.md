---
name: pr-review
description: >
  Review the current or specified GitHub PR with gh. Accepts an optional PR
  number and extra review instructions.
---

## Instructions

Perform a comprehensive code review for the specified PR (or the PR associated with the current branch if no number is given), then report findings in the structured format defined in the core rules below.

Keep the review read-only. Never create scratch files in the reviewed repository; if a payload needs a file, use the session scratchpad.

Inputs: parse the user's message as `[prNumber] [additionalInstructions...]`. If the first PR-like token is a PR number (`123` or `#123`) or PR URL, use it as `<PR_NUMBER>` and treat the rest as `<ADDITIONAL_INSTRUCTIONS>`. Otherwise, resolve the current branch's PR and treat any remaining request text as `<ADDITIONAL_INSTRUCTIONS>`:
```bash
gh pr view --json number --jq .number
```

Use only `<PR_NUMBER>` in gh commands. If `<ADDITIONAL_INSTRUCTIONS>` is non-empty, apply it as review emphasis without overriding mandatory duplicate detection, line-number, safety, or output-format rules.

### Local vs Remote File Access

Determine the file access mode before starting:

1. `git branch --show-current` — current local branch
2. `gh pr view <PR_NUMBER> --json title,body,files,commits,baseRefName,baseRefOid,headRefName,headRefOid --jq '{title,body,baseRefName,baseRefOid,headRefName,headRefOid,files:[.files[]|{path,additions,deletions,changeType}],commits:[.commits[]|{oid,messageHeadline}]}'` — bounded PR metadata
3. `git rev-parse HEAD` — current local revision
4. `git cat-file -e '<baseRefOid>^{commit}'` — check that the exact PR base commit is available locally.

Commit bodies, authors, and dates are intentionally omitted. If a headline needs investigation, fetch that commit on demand with `git show <oid> --no-patch` (local mode) or `gh api repos/{owner}/{repo}/commits/{oid}` (remote mode).

**Local mode** requires all three checks: current branch equals `headRefName`, local HEAD equals `headRefOid`, and the exact base commit exists. Read files with read-only shell commands (`sed`, `rg`, `git show`) and find paths with `rg --files`. Local working-tree changes may provide context, but anchor findings to the exact PR revisions and diff.

**Remote mode** applies if any check fails. Use `headRefOid` for all PR-head reads with gh api:
- `gh api 'repos/{owner}/{repo}/contents/{path}?ref={headRefOid}' --jq '.content' | base64 -d` — read any file
- `gh api 'repos/{owner}/{repo}/git/trees/{headRefOid}?recursive=1'` — explore file structure

### Review Workflow

Fetch primary review materials (PR metadata is already fetched above). Capture both diffs through the configured large-output path; do not print an uncounted payload directly into the conversation:

- `gh pr diff <PR_NUMBER>` — complete diff (file path arguments are not supported; always fetch the full diff and filter locally if needed)
- `bash ~/.config/ai-pr/bin/fetch_existing_comments.sh <PR_NUMBER>` — existing PR comments as NDJSON (inline, issue, and review-summary with resolved/outdated status)
- `bash ~/.config/ai-pr/bin/format_pr_diff_with_line_numbers.sh <PR_NUMBER>` — line-numbered diff; the authoritative source for review line numbers (see Line Number Source in the core rules)

Inspect every changed file and its relevant diff at the exact PR revisions. For changed behavior, trace callers, related tests, and similar implementations before deciding whether a finding is actionable. For deeper investigation, use the access mode determined above.

Count the line-numbered diff before expanding it. Retain the full payload for investigation, but emit only counts and focused summaries when output exceeds 100 lines. Never paste a larger diff directly into the conversation.

### Core Review Rules
