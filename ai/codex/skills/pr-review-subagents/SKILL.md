---
name: pr-review-subagents
description: >
  Comprehensive PR review using six parallel Codex custom subagents for bugs,
  security, architecture, error handling, git history, and tests. Use when the
  user wants PR review with subagents, review-subagents, or parallel specialist
  reviewers. Accepts an optional PR number; if omitted, detect the current branch PR.
---

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

Compare the current branch with `headRefName`.

- Match: local mode. Subagents may use read-only local commands such as `rg`, `git`, `sed`, and `gh`.
- Mismatch: remote mode. Subagents must inspect `headRefName` with `gh api`.

Pass every subagent: PR number, metadata, repo owner/name, full diff, existing comments NDJSON, local mode, head branch, focus area, and the scope rule below.

### Scope Rule

Findings must target PR-added or modified lines. Report unchanged pre-existing code only for critical impact: security breach, data corruption/loss, service outage, or compliance violation. Prefix these with `[既存コード]` and name the category; omit all other pre-existing issues.

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

- Drop "no findings" messages from final findings, but count them as zero in the summary.
- Remove inter-agent duplicates by same root cause at the same file/line; keep the clearest/highest-confidence finding.
- Recheck existing comments NDJSON. Skip an unresolved duplicate when same path within ±5 lines and same root cause, or same target symbol/concept fixable by the same change, with duplicate confidence >= 70. Do not skip resolved or outdated comments. Collect skipped findings for `[既コメント済]`.
- Preserve `[既存コード]` and its critical category.
- Route all test-related findings to `## テストに関する指摘`, regardless of source agent.
- If a bug and missing test share the same root cause, keep the bug as the finding and mention the test gap only as supporting detail unless a distinct test change is required.
- Output only actionable findings requiring a concrete response. No praise, compliance confirmations, "looks good", or non-actionable observations.
- Reclassify by confidence: High 90-100, Medium 75-89, Low only when explicitly notable below threshold.
- Every final finding needs `[path:line]` or `[path:~line]`; drop findings without line references.
- Number findings sequentially across regular and test sections. Omit empty sections and omit `## レビュー注目ポイント` unless it adds concrete unresolved actions not already numbered.
- If no actionable findings remain, output only `対応が必要な指摘はありません。`
- If any finding was skipped as an existing-comment duplicate, add `## [既コメント済] スキップした指摘` immediately before `## 総合評価`, one line each:
  `- **[path:line]** 領域: <area> / 既存コメント ID: <id> (resolved=<bool>, ai_origin=<value>) — <reason>`

### Final Format

Respond entirely in Japanese. Every finding must be header, indented detail bullet, then `---` separator, including the last finding.

Header forms:

- `N. **[file:line]** 領域 (信頼度: XX): 短い一行の要約`
- `N. [既存コード] **[file:line]** 領域 (信頼度: XX): 短い一行の要約（重大カテゴリ）`

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

## 総合評価

**マージ可否**: ✅ マージ可 / ⚠️ 条件付きマージ可 / ❌ マージ不可

総合コメント。
```

If at least one actionable finding remains, append:

> To post any findings as GitHub PR comments, use the `pr-comment-post` skill:
> Tell me: "pr-comment-post スキルで 1 3 5 を投稿して" (specifying item numbers)
