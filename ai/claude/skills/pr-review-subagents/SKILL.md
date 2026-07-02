---
description: "Comprehensive PR review using 6 parallel specialist sub-agents for bugs, security, architecture, error handling, history, and tests"
model: opus
allowed-tools: Bash(gh:*), Bash(git:*), Bash(python:*)
argument-hint: "[prNumber]"
disable-model-invocation: true
effort: max
---

## Instructions

Review PR #$ARGUMENTS with 6 read-only specialist sub-agents in parallel.

### Scope Rule

Findings must target PR-added or modified lines. Report unchanged pre-existing code only for critical impact: security breach, data corruption/loss, service outage, or compliance violation. Route these to `## 既存コードに関する指摘` (see Aggregate step 4 and Final Format) and name the category; omit all other pre-existing issues.

### Gather Once

Fetch required context before launching sub-agents:

```bash
gh pr view $ARGUMENTS --json title,body,baseRefName,headRefName,url
gh pr diff $ARGUMENTS
gh repo view --json nameWithOwner
git branch --show-current
bash ~/.config/ai-pr/bin/fetch_existing_comments.sh $ARGUMENTS
```

Compare `git branch --show-current` with `headRefName`. If they match, local mode is true and sub-agents may use `Read`/`Glob`; otherwise they must use `gh api` against `headRefName`.

Pass every sub-agent: PR number, metadata, repo owner/name, full diff, existing comments NDJSON, local mode, head branch, focus area, and the scope rule.

### Launch

Start all simultaneously:

1. **pr-reviewer-bugs** — バグ検出・ロジックエラー
2. **pr-reviewer-security** — セキュリティ脆弱性
3. **pr-reviewer-architecture** — アーキテクチャ・設計品質
4. **pr-reviewer-errors** — エラーハンドリング品質
5. **pr-reviewer-history** — Git履歴・リグレッションリスク
6. **pr-reviewer-tests** — テスト品質・カバレッジ

### Aggregate

1. Drop "no findings" messages from final findings, but count them as zero in the summary.
2. Remove inter-agent duplicates by same root cause at the same file/line; keep the clearest/highest-confidence finding.
3. Recheck existing comments NDJSON. Skip an unresolved duplicate when same path within ±5 lines and same root cause, or same target symbol/concept fixable by the same change, with duplicate confidence >= 70. Do not skip resolved or outdated comments; if they overlap, re-report and mention the past resolved comment in the detail. Collect skipped findings for `[既コメント済]`.
4. Route findings marked `[既存コード]` to `## 既存コードに関する指摘`, keeping their critical category noted in the detail line.
5. Route all test-related findings to `## テストに関する指摘`, regardless of source agent.
6. **Pre-existing code takes priority over test routing**: a `[既存コード]` finding about tests still goes to `## 既存コードに関する指摘`, not `## テストに関する指摘`. Decide pre-existing-vs-changed first, then test-vs-regular for the remainder.
7. If a bug and missing test share the same root cause, keep the bug as the finding and mention the test gap only as supporting detail unless a distinct test change is required.
8. Output only actionable findings requiring a concrete response. No praise, compliance confirmations, "looks good", or non-actionable observations.
9. Reclassify by confidence: High 90-100, Medium 75-89, Low only when explicitly notable below threshold.
10. Every final finding needs `[path:line]` or `[path:~line]`; drop findings without line references.
11. Number findings sequentially across regular, test, and pre-existing-code sections. Omit empty sections and omit `## レビュー注目ポイント` unless it adds concrete unresolved actions not already numbered.
12. If no actionable findings remain, output only `対応が必要な指摘はありません。`
13. If any finding was skipped as an existing-comment duplicate, add `## [既コメント済] スキップした指摘` immediately before `## 総合評価`, one line each:
    `- **[path:line]** 領域: <area> / 既存コメント ID: <id> (resolved=<bool>, ai_origin=<value>) — <reason>`

### Final Format

Respond entirely in Japanese. Every finding must be header, indented detail bullet, then `---` separator, including the last finding.

Header forms:

- `N. **[file:line]** 領域 (信頼度: XX): 短い一行の要約`
- `N. **[file:line]** 領域 (信頼度: XX): 短い一行の要約（重大カテゴリ）` (used only inside `## 既存コードに関する指摘`)

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

2. **[path/to/file.ext:line]** 領域 (信頼度: XX): 短い一行の要約
   - 詳細説明と推奨対応。

---

## 🟢 Low Priority（特筆すべきもの）

3. **[path/to/file.ext:line]** 領域 (信頼度: XX): 短い一行の要約
   - 詳細説明と推奨対応。

---

## テストに関する指摘

### 🟡 Medium Priority（信頼度75-89）

4. **[path/to/file.ext:line]** テスト品質 (信頼度: XX): 短い一行の要約
   - 詳細説明と推奨対応。

---

## 既存コードに関する指摘

### 🔴 High Priority（信頼度90-100）

5. **[src/db/query.ts:120]** セキュリティ (信頼度: XX): 既存ヘルパーにSQLインジェクション（Security breach category）
   - PRの新機能から呼ばれる未変更コードが生のユーザー入力をクエリ文字列に連結している。具体的な攻撃ベクトル: 任意の文字列入力で任意のSQL実行が可能。

---

## 総合評価

**マージ可否**: ✅ マージ可 / ⚠️ 条件付きマージ可 / ❌ マージ不可

総合コメント。
```

If at least one actionable finding remains, append:

> To post any findings as GitHub PR comments, run:
> `/pr-comment-post <item numbers>` (e.g., `/pr-comment-post 1 3 5`)
