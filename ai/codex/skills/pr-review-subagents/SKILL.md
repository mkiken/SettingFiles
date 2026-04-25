---
name: pr-review-subagents
description: >
  Comprehensive PR review using six parallel Codex custom subagents for bugs,
  security, architecture, error handling, git history, and tests. Use when the
  user wants PR review with subagents, review-subagents, or parallel specialist
  reviewers. Accepts an optional PR number; if omitted, detect the current branch PR.
---

## Instructions

Perform a comprehensive PR review with six specialist Codex subagents.

PR number: extract from the user's message if provided. If not provided, run:

```bash
gh pr view --json number --jq .number
```

### Gather Context Before Spawning

Fetch the shared review context once in the parent session:

```bash
gh pr view <PR_NUMBER> --json title,body,baseRefName,headRefName,url,files,commits
gh pr diff <PR_NUMBER>
gh repo view --json nameWithOwner
git branch --show-current
```

Compare the current branch with `headRefName`.

- If they match, local mode is active. Tell subagents to use local read-only commands such as `rg`, `git`, `sed`, and `gh` for deeper investigation.
- If they do not match, remote mode is active. Tell subagents to use `gh api` against `headRefName` for file contents and tree exploration.

Pass each subagent:

- PR number.
- PR metadata.
- Repository owner/name.
- Complete PR diff.
- Local mode flag and head branch.
- The exact focus area for that subagent.

### Spawn Subagents

Spawn all six custom agents in parallel and wait for all results:

- `pr_reviewer_bugs`
- `pr_reviewer_security`
- `pr_reviewer_architecture`
- `pr_reviewer_errors`
- `pr_reviewer_history`
- `pr_reviewer_tests`

Each subagent must stay read-only and return Japanese findings in its own configured format.

### Aggregate Results

After all subagents finish:

- Drop "no findings" messages from the final findings list, but include them in the summary counts as zero.
- Remove duplicates. Treat findings as duplicates when they cite the same file/line and same underlying cause; keep the clearest/highest-confidence version.
- Reclassify priority by confidence:
  - High: 90-100
  - Medium: 75-89
  - Low: notable issues below the main threshold only when a subagent explicitly reports one as worth mentioning.
- Validate that every final finding has a `[path/to/file.ext:line]` or `[path/to/file.ext:~line]` reference. Do not include findings without a line reference.
- Number findings sequentially across all priority sections. Do not restart numbering per section.

### Formatting Rules

Respond entirely in Japanese.

Every finding must use this exact three-part structure: header, detail, separator.

- Header: `N. **[file:line]** 領域 (信頼度: XX): 短い一行の要約`
- Detail: `   - 詳細説明と推奨対応。`
- Separator: `---`

The `---` separator is mandatory after every finding, including the last one.

### Output Format

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

---

## 🔴 High Priority（信頼度90-100）

> **アクション必須**: マージ前に対処が必要な問題

1. **[path/to/file.ext:line]** 領域 (信頼度: XX): 短い一行の要約
   - 詳細説明と推奨対応。

---

## 🟡 Medium Priority（信頼度75-89）

> **推奨対処**: 品質向上のために対処を推奨

2. **[path/to/file.ext:line]** 領域 (信頼度: XX): 短い一行の要約
   - 詳細説明と推奨対応。

---

## 🟢 Low Priority（特筆すべきもの）

> **任意対応**: 将来的に検討する価値がある改善点

3. **[path/to/file.ext:line]** 領域 (信頼度: XX): 短い一行の要約
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
```

Omit empty priority sections.

### Post-Review: Post to GitHub

After outputting the review results, display:

> To post any findings as GitHub PR comments, use the `pr-comment-post` skill:
> Tell me: "pr-comment-post スキルで 1 3 5 を投稿して" (specifying item numbers)
