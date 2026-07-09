---
name: pr-review-subagents
description: >
  Comprehensive PR review using seven parallel Codex custom subagents for bugs,
  security, architecture, error handling, git history, tests, and performance. Use when the
  user wants PR review with subagents, review-subagents, or parallel specialist
  reviewers. Accepts an optional PR number plus extra review instructions; if omitted,
  detect the current branch PR.
---

## Instructions

Review a PR with seven read-only specialist Codex subagents.

Inputs: parse the user's message as `[prNumber] [additionalInstructions...]`. If the first PR-like token is a PR number (`123` or `#123`) or PR URL, use it as `<PR_NUMBER>` and treat the rest as `<ADDITIONAL_INSTRUCTIONS>`. Otherwise, resolve the current branch's PR and treat any remaining request text as `<ADDITIONAL_INSTRUCTIONS>`:

```bash
gh pr view --json number --jq .number
```

Use only `<PR_NUMBER>` in gh commands. If `<ADDITIONAL_INSTRUCTIONS>` is non-empty, pass it to every subagent and apply it as review emphasis without overriding mandatory duplicate detection, line-number, safety, or output-format rules.

### Gather Once

Fetch context in the parent session:

```bash
gh pr view <PR_NUMBER> --json title,body,baseRefName,headRefName,url,files,commits
gh pr diff <PR_NUMBER>
bash ~/.config/ai-pr/bin/format_pr_diff_with_line_numbers.sh <PR_NUMBER>
gh repo view --json nameWithOwner
git branch --show-current
bash ~/.config/ai-pr/bin/fetch_existing_comments.sh <PR_NUMBER>
```

Local mode = current branch matches `headRefName`; subagents may then use read-only local commands (`rg`, `git`, `sed`, `gh`), otherwise they must inspect `headRefName` with `gh api`.

Pass every subagent: PR number, metadata, repo owner/name, full diff, line-numbered diff, existing comments NDJSON, local mode, head branch, and `<ADDITIONAL_INSTRUCTIONS>`. Each subagent's focus and review rules are in its definition.

### Spawn

Run all seven in parallel and wait for all:

- `pr_reviewer_bugs`
- `pr_reviewer_security`
- `pr_reviewer_architecture`
- `pr_reviewer_errors`
- `pr_reviewer_history`
- `pr_reviewer_tests`
- `pr_reviewer_performance`

Each subagent stays read-only and returns Japanese findings in its configured format.
Read-only includes not creating scratch files: never redirect diffs, comments, or command output to files in the repository or elsewhere.
Inspect the passed context or indexed sources, or run read-only commands directly.
