---
description: "Comprehensive PR review using 6 parallel specialist sub-agents for bugs, security, architecture, error handling, history, and tests"
model: opus
allowed-tools: Bash(gh:*), Bash(git:*), Bash(python:*)
argument-hint: "[prNumber]"
disable-model-invocation: true
---

## Instructions

Perform a comprehensive PR review of PR #$ARGUMENTS using 6 specialist sub-agents in parallel.

### Review Scope: Changed Code vs Pre-existing Code

**Primary focus**: All findings MUST target lines added or modified in this PR's diff. Do not surface issues whose root cause lives entirely in unchanged code that this PR did not touch.

**Pre-existing-code exception (critical only)**: Sub-agents MAY report a pre-existing issue only when it falls into one of these critical impact categories:

- **Security breach**: concrete exploitable attack vector (auth bypass, RCE, injection, secret exposure)
- **Data corruption/loss**: silent overwrite, missing transaction, irreversible mutation
- **Service outage**: crash, infinite loop, deadlock, resource exhaustion under realistic load
- **Compliance violation**: PII handling, license breach, audit trail loss

Pre-existing findings must be marked with `[既存コード]` prefix and state which impact category applies. All other pre-existing issues MUST be omitted.

---

### Phase 1: Gather PR Information

Fetch all required PR data before launching sub-agents:

```bash
gh pr view $ARGUMENTS --json title,body,baseRefName,headRefName,url
gh pr diff $ARGUMENTS  # NOTE: file path arguments are not supported; fetch full diff and filter locally if needed
gh repo view --json nameWithOwner
git branch --show-current  # Detect local mode
```

Compare the output of `git branch --show-current` with `headRefName`. If they match, **local mode** is active — sub-agents can use `Read` and `Glob` tools directly instead of `gh api`.

### Phase 2: Launch All 6 Sub-Agents in Parallel

Pass the following to each sub-agent as context:

- PR number: `$ARGUMENTS`
- PR metadata (title, body, base/head branch, repository owner/name)
- Complete PR diff
- **Local mode**: whether the current branch matches `headRefName` (true/false). If true, instruct sub-agents to use `Read` and `Glob` tools for file reading instead of `gh api`.
- **Scope rule**: Focus findings on changed lines. For pre-existing issues in unchanged code, report only critical impact categories (security breach, data corruption/loss, service outage, compliance violation) with a `[既存コード]` prefix.

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
4. Format structured output following the Formatting Rules below
5. **Validate line numbers**: any finding not in `[path/to/file.ext:line]` format must be supplemented by referencing the original diff; findings without a line number must not appear in the final output

### Formatting Rules

**Finding Format**: Each item MUST use this exact three-part structure — header, detail, then separator:

- **Header line**: `N. **[file:line]** 領域 (信頼度: XX): 短い一行の要約`
- **Detail line**: `   - 詳細説明と推奨対応（インデントされたサブバレット）`
- **Separator line**: `---` (horizontal rule — MANDATORY after every finding, including the last one)

The `---` separator after each item is a hard structural requirement that must never be omitted.

✅ CORRECT:

1. **[src/auth.ts:42]** セキュリティ (信頼度: 92): トークンがログに平文で露出
   - ロガーにトークンが直接渡されている。ログ出力前にマスキング処理を追加すること。

---

2. **[src/auth.ts:87]** バグ検出 (信頼度: 85): null参照によるTypeError
   - セッション期限切れ時に`getUser()`がnullを返すが、nullチェックが欠落している。

---

3. [既存コード] **[src/db/query.ts:120]** セキュリティ (信頼度: 95): SQLインジェクション（セキュリティ侵害カテゴリ）
   - このPRで変更された関数の呼び出し先に未検査の文字列補間があり、攻撃者が任意のSQLを実行できる。

---

❌ WRONG (missing `---` separator and/or long single line):

1. **[src/auth.ts:42]** セキュリティ (信頼度: 92): トークンがログに露出しているためログ集約システムに認証情報が漏洩する可能性がありマスキング処理が必要。
2. **[src/auth.ts:87]** バグ検出 (信頼度: 85): null参照の可能性がありTypeErrorが発生する。

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

1. **[path/to/file.ext:line]** 領域 (信頼度: XX): 短い一行の要約
   - 詳細説明と推奨対応。

---

2. **[path/to/file.ext:line]** 領域 (信頼度: XX): 短い一行の要約
   - 詳細説明と推奨対応。

---

## 🟡 Medium Priority（信頼度75-89）

> **推奨対処**: 品質向上のために対処を推奨

3. **[path/to/file.ext:line]** 領域 (信頼度: XX): 短い一行の要約
   - 詳細説明と推奨対応。

---

4. **[path/to/file.ext:line]** 領域 (信頼度: XX): 短い一行の要約
   - 詳細説明と推奨対応。

---

## 🟢 Low Priority（特筆すべきもの）

> **任意対応**: 将来的に検討する価値がある改善点

5. **[path/to/file.ext:line]** 領域 (信頼度: XX): 短い一行の要約
   - 詳細説明と推奨対応。

---

6. **[path/to/file.ext:line]** 領域 (信頼度: XX): 短い一行の要約
   - 詳細説明と推奨対応。

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
