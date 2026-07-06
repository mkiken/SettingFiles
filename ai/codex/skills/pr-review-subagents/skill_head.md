---
name: pr-review-subagents
description: >
  Comprehensive PR review using six parallel Codex custom subagents for bugs,
  security, architecture, error handling, git history, and tests. Use when the
  user wants PR review with subagents, review-subagents, or parallel specialist
  reviewers. Accepts an optional PR number; if omitted, detect the current branch PR.
---

<!-- GENERATED FILE NOTICE: SKILL.md is generated from skill_head.md + ai/common/pr_review_subagents/orchestrator_core.md + skill_tail.md by mac/initialization/ai/codex.sh and mac/updates/codex.sh. Edit those sources, not SKILL.md. -->

## Instructions

Review a PR with six read-only specialist Codex subagents.

PR number: extract it from the user message, or run:

```bash
gh pr view --json number --jq .number
```

### Gather Once

Fetch context in the parent session:

```bash
gh pr view <PR_NUMBER> --json title,body,baseRefName,headRefName,url,files,commits
gh pr diff <PR_NUMBER>
gh repo view --json nameWithOwner
git branch --show-current
bash ~/.config/ai-pr/bin/fetch_existing_comments.sh <PR_NUMBER>
```

Local mode = current branch matches `headRefName`; subagents may then use read-only local commands (`rg`, `git`, `sed`, `gh`), otherwise they must inspect `headRefName` with `gh api`.

Pass every subagent: PR number, metadata, repo owner/name, full diff, existing comments NDJSON, local mode, and head branch. Each subagent's focus and review rules are in its definition.

### Spawn

Run all six in parallel and wait for all:

- `pr_reviewer_bugs`
- `pr_reviewer_security`
- `pr_reviewer_architecture`
- `pr_reviewer_errors`
- `pr_reviewer_history`
- `pr_reviewer_tests`

Each subagent stays read-only and returns Japanese findings in its configured format.
