---
description: "Comprehensive PR review using 9 parallel specialist sub-agents for bugs, security, architecture, error handling, history, tests, performance, consistency, and simplification"
model: opus
allowed-tools: Bash(gh:*), Bash(git:*), Bash(python:*), Bash(/bin/cat:*)
argument-hint: "[prNumber] [additionalInstructions...]"
disable-model-invocation: true
effort: max
---

## Instructions

Review the target PR with 9 read-only specialist sub-agents in parallel.

Inputs: parse `$ARGUMENTS` as `[prNumber] [additionalInstructions...]`. If the first token is a PR number (`123` or `#123`) or PR URL, use it as `<PR_NUMBER>` and treat the rest as `<ADDITIONAL_INSTRUCTIONS>`. Otherwise, resolve the current branch's PR with `gh pr view --json number --jq .number` and treat all arguments as `<ADDITIONAL_INSTRUCTIONS>`.

### Gather Once

Fetch context first:

```bash
gh pr view <PR_NUMBER> --json title,body,baseRefName,baseRefOid,headRefName,headRefOid,url,files,commits
gh pr diff <PR_NUMBER>
bash ~/.config/ai-pr/bin/format_pr_diff_with_line_numbers.sh <PR_NUMBER>
gh repo view --json nameWithOwner
git branch --show-current
git rev-parse HEAD
bash ~/.config/ai-pr/bin/fetch_existing_comments.sh <PR_NUMBER>
```

Local mode = current branch matches `headRefName`, local HEAD matches `headRefOid`, **and** `git cat-file -e '<baseRefOid>^{commit}'` succeeds. Otherwise use remote mode and inspect `headRefOid`, never local files.

Capture the full and line-numbered diffs through the configured large-output path, using source labels unique to the PR and `headRefOid`. Count the line-numbered diff before expanding it in the parent context.

Derive a compact manifest for every top-level inline thread (`kind=inline` and `in_reply_to_id=null`) with `id`, `path`, `line`, `start_line`, `is_resolved`, `is_outdated`, `thread_id`, `ai_origin`, and a concise root-cause/fix excerpt. Keep the full NDJSON in the parent for final aggregation.

Pass every sub-agent directly: PR number, metadata, repo owner/name, the compact comment manifest, local mode, base/head names, `baseRefOid`, `headRefOid`, and `<ADDITIONAL_INSTRUCTIONS>`. For a line-numbered diff of at most 100 lines, also pass both diffs directly. For a larger diff, do not paste either full payload; pass the changed-file list and captured source labels instead. Every sub-agent must inspect every changed file and its relevant diff at the exact PR revisions (local mode: local head file plus `git diff <baseRefOid>...<headRefOid>`; remote mode: `gh api` contents at `headRefOid` plus the PR-files patch). Indexed snippets alone are insufficient. Do not refetch the whole PR diff or make duplicate detection depend only on an indexed source. Each agent's focus and review rules are in its definition.

### Launch

Start all simultaneously:

1. **pr-reviewer-bugs** — バグ検出・ロジックエラー
2. **pr-reviewer-security** — セキュリティ脆弱性
3. **pr-reviewer-architecture** — アーキテクチャ・設計品質
4. **pr-reviewer-errors** — エラーハンドリング品質
5. **pr-reviewer-history** — Git履歴・リグレッションリスク
6. **pr-reviewer-tests** — テスト品質・カバレッジ
7. **pr-reviewer-performance** — パフォーマンス
8. **pr-reviewer-consistency** — 一貫性（既存コードとの整合）
9. **pr-reviewer-simplification** — 簡素化・可読性改善提案

If a launched sub-agent fails mid-run on a transient API error (e.g. session limit), do not respawn it: resume the same agent with SendMessage so it continues with its context intact. For a session-limit failure, check the current time against the reported reset time first and resume only after it has passed.

!`/bin/cat ~/.claude/common/pr_review_subagents/orchestrator_core.md`

!`/bin/cat ~/.claude/common/pr_review_finding_format.md`

If at least one actionable finding remains, append:

> To post any findings as GitHub PR comments, run:
> `/pr-comment-post <item numbers>` (e.g., `/pr-comment-post 1 3 5`)
