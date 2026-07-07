---
description: "Comprehensive PR review using 7 parallel specialist sub-agents for bugs, security, architecture, error handling, history, tests, and performance"
model: opus
allowed-tools: Bash(gh:*), Bash(git:*), Bash(python:*), Bash(/bin/cat:*)
argument-hint: "[prNumber]"
disable-model-invocation: true
effort: max
---

## Instructions

Review PR #$ARGUMENTS with 7 read-only specialist sub-agents in parallel.

### Gather Once

Fetch context first:

```bash
gh pr view $ARGUMENTS --json title,body,baseRefName,headRefName,url
gh pr diff $ARGUMENTS
bash ~/.config/ai-pr/bin/format_pr_diff_with_line_numbers.sh $ARGUMENTS
gh repo view --json nameWithOwner
git branch --show-current
bash ~/.config/ai-pr/bin/fetch_existing_comments.sh $ARGUMENTS
```

Local mode = current branch matches `headRefName`; sub-agents may then use `Read`/`Glob`, otherwise they must use `gh api` against `headRefName`.

Pass every sub-agent: PR number, metadata, repo owner/name, full diff, line-numbered diff, existing comments NDJSON, local mode, and head branch. Each agent's focus and review rules are in its definition.

### Launch

Start all simultaneously:

1. **pr-reviewer-bugs** — バグ検出・ロジックエラー
2. **pr-reviewer-security** — セキュリティ脆弱性
3. **pr-reviewer-architecture** — アーキテクチャ・設計品質
4. **pr-reviewer-errors** — エラーハンドリング品質
5. **pr-reviewer-history** — Git履歴・リグレッションリスク
6. **pr-reviewer-tests** — テスト品質・カバレッジ
7. **pr-reviewer-performance** — パフォーマンス

!`/bin/cat ~/.claude/common/pr_review_subagents/orchestrator_core.md`

!`/bin/cat ~/.claude/common/pr_review_finding_format.md`

If at least one actionable finding remains, append:

> To post any findings as GitHub PR comments, run:
> `/pr-comment-post <item numbers>` (e.g., `/pr-comment-post 1 3 5`)
