---
description: "Comprehensive PR review using 6 parallel specialist sub-agents for bugs, security, architecture, error handling, history, and tests"
model: opus
allowed-tools: Bash(gh:*), Bash(git:*), Bash(python:*)
argument-hint: "[prNumber]"
---

## Instructions

Perform a comprehensive PR review of PR #$ARGUMENTS using 6 specialist sub-agents in parallel.

### Phase 1: Gather PR Information

Fetch all required PR data before launching sub-agents:

```bash
gh pr view $ARGUMENTS --json title,body,baseRefName,headRefName,url
gh pr diff $ARGUMENTS  # NOTE: file path arguments are not supported; fetch full diff and filter locally if needed
gh repo view --json nameWithOwner
```

### Phase 2: Launch All 6 Sub-Agents in Parallel

Pass the following to each sub-agent as context:

- PR number: `$ARGUMENTS`
- PR metadata (title, body, base/head branch, repository owner/name)
- Complete PR diff

Launch all agents simultaneously:

1. **pr-reviewer-bugs** — バグ検出・ロジックエラー
2. **pr-reviewer-security** — セキュリティ脆弱性
3. **pr-reviewer-architecture** — アーキテクチャ・設計品質
4. **pr-reviewer-errors** — エラーハンドリング品質
5. **pr-reviewer-history** — Git履歴・リグレッションリスク
6. **pr-reviewer-tests** — テスト品質・カバレッジ

### Phase 3: Aggregate and Deduplicate Results

Collect all sub-agent findings, then:

1. Remove duplicate findings (same file:line reported by multiple agents)
2. Reclassify priorities based on confidence scores
3. Assign sequential numbers to all findings across all priority sections (continue numbering across sections — do not restart per section)
4. Format structured output — **IMPORTANT: insert a blank line between each finding item. Consecutive items without spacing severely hurt readability.**
5. **Validate line numbers**: any finding not in `[path/to/file.ext:line]` format must be supplemented by referencing the original diff; findings without a line number must not appear in the final output

### Output Format

Respond entirely in **Japanese**.

---

## レビューサマリー

| 領域               | 指摘数 | 最高信頼度 |
| ------------------ | ------ | ---------- |
| バグ検出           | N      | XX         |
| セキュリティ       | N      | XX         |
| アーキテクチャ     | N      | XX         |
| エラーハンドリング | N      | XX         |
| Git履歴            | N      | XX         |
| テスト品質         | N      | XX         |

---

## 🔴 High Priority（信頼度90-100）

> **アクション必須**: マージ前に対処が必要な問題

1. **[path/to/file.ext:line]** 領域 (信頼度: XX): 問題の説明

2. **[path/to/file.ext:line]** 領域 (信頼度: XX): 問題の説明

---

## 🟡 Medium Priority（信頼度75-89）

> **推奨対処**: 品質向上のために対処を推奨

3. **[path/to/file.ext:line]** 領域 (信頼度: XX): 問題の説明

4. **[path/to/file.ext:line]** 領域 (信頼度: XX): 問題の説明

---

## 🟢 Low Priority（特筆すべきもの）

> **任意対応**: 将来的に検討する価値がある改善点

5. **[path/to/file.ext:line]** 領域 (信頼度: XX): 問題の説明

6. **[path/to/file.ext:line]** 領域 (信頼度: XX): 問題の説明

---

## レビュー注目ポイント

- 特別な注意が必要な領域
- 追加テストが必要な箇所
- ドキュメント更新が必要な箇所

---

## 総合評価

**マージ可否**: ✅ マージ可 / ⚠️ 条件付きマージ可 / ❌ マージ不可

総合コメントと優先度の高い対応事項のまとめ。

---

## Post-Review: Post to GitHub

After outputting the review results, display the following message to the user:

> To post any findings as GitHub PR comments, run:
> `/pr-comment-post <item numbers>` (e.g., `/pr-comment-post 1 3 5`)
