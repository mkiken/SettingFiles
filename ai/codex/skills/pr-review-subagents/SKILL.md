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

### Aggregate

1. Drop "no findings" messages from final findings but count them as zero in the summary.
2. Remove inter-agent duplicates (same root cause at the same file/line); keep the clearest, highest-confidence finding.
3. Recheck existing comments NDJSON. Skip an unresolved duplicate — same path within ±5 lines and same root cause, or same target symbol/concept fixable by the same change — with duplicate confidence >= 70. Never skip resolved or outdated comments; if they overlap, re-report and mention the past resolved comment in the detail. Collect skipped findings for `[既コメント済]`.
4. Route `[既存コード]` findings (critical pre-existing issues) to `## 既存コードに関する指摘`, keeping the critical category in the detail line.
5. Route all other test-related findings to `## テストに関する指摘` regardless of source agent. Pre-existing-vs-changed is decided first: a `[既存コード]` finding about tests goes to `## 既存コードに関する指摘`.
6. If a bug and a missing test share a root cause, keep the bug and mention the test gap only as supporting detail unless a distinct test change is required.
7. Keep only actionable findings requiring a concrete response — no praise, compliance confirmations, or non-actionable observations.
8. Reclassify by confidence: High 90-100, Medium 75-89, Low only when explicitly notable below threshold.
9. Every finding needs `[path:line]` or `[path:~line]`; drop findings without line references. Verify each anchor against the head-revision file (read-only inspection in local mode) — sub-agents may report diff-text positions; fix mismatches or downgrade to `~line`.
10. Number findings sequentially across regular, test, and pre-existing-code sections. Omit empty sections; omit `## レビュー注目ポイント` unless it adds concrete unresolved actions not already numbered.
11. If no actionable findings remain, output only `対応が必要な指摘はありません。`
12. If any finding was skipped as an existing-comment duplicate, add `## [既コメント済] スキップした指摘` immediately before `## 総合評価`, one line each:
    `- **[path:line]** 領域: <area> / 既存コメント ID: <id> (resolved=<bool>, ai_origin=<value>) — <reason>`

### Final Format

Respond entirely in Japanese. Each finding: header, indented detail bullet, then `---` separator (including the last finding).

Header: `N. **[file:line]** 領域 (信頼度: XX): 短い一行の要約` — inside `## 既存コードに関する指摘`, append `（重大カテゴリ）` to the summary.

Use this structure and omit empty sections:

```markdown
## レビューサマリー

| 領域 | 指摘数 | 最高信頼度 |
| ---- | ------ | ---------- |
| バグ検出 | N | XX |
| セキュリティ | N | XX |
| アーキテクチャ | N | XX |
| エラーハンドリング | N | XX |
| Git履歴 | N | XX |
| テスト品質 | N | XX |

## 🔴 High Priority（信頼度90-100）

1. **[path/to/file.ext:line]** 領域 (信頼度: XX): 短い一行の要約
   - 詳細説明と推奨対応。

---

## 🟡 Medium Priority（信頼度75-89）

2. （同形式）

## 🟢 Low Priority（特筆すべきもの）

3. （同形式）

## テストに関する指摘

### 🟡 Medium Priority（信頼度75-89）

4. （同形式、領域はテスト品質）

## 既存コードに関する指摘

### 🔴 High Priority（信頼度90-100）

5. （同形式、要約末尾に重大カテゴリ）

## 総合評価

**マージ可否**: ✅ マージ可 / ⚠️ 条件付きマージ可 / ❌ マージ不可

総合コメント。
```

If at least one actionable finding remains, append:

> To post any findings as GitHub PR comments, use the `pr-comment-post` skill:
> Tell me: "pr-comment-post スキルで 1 3 5 を投稿して" (specifying item numbers)
