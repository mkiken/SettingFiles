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

### Review Scope: Changed Code vs Pre-existing Code

**Primary focus**: All findings MUST target lines added or modified in this PR's diff. Do not surface issues whose root cause lives entirely in unchanged code that this PR did not touch.

**Pre-existing-code exception (critical only)**: Subagents MAY report a pre-existing issue only when it falls into one of these critical impact categories:

- **Security breach**: concrete exploitable attack vector (auth bypass, RCE, injection, secret exposure)
- **Data corruption/loss**: silent overwrite, missing transaction, irreversible mutation
- **Service outage**: crash, infinite loop, deadlock, resource exhaustion under realistic load
- **Compliance violation**: PII handling, license breach, audit trail loss

Pre-existing findings must be marked with `[既存コード]` prefix and state which impact category applies. All other pre-existing issues MUST be omitted.

### Gather Context Before Spawning

Fetch the shared review context once in the parent session:

```bash
gh pr view <PR_NUMBER> --json title,body,baseRefName,headRefName,url,files,commits
gh pr diff <PR_NUMBER>
gh repo view --json nameWithOwner
git branch --show-current
bash "$(git rev-parse --show-toplevel)/shell/common/pr/fetch_existing_comments.sh" <PR_NUMBER>
```

Compare the current branch with `headRefName`.

- If they match, local mode is active. Tell subagents to use local read-only commands such as `rg`, `git`, `sed`, and `gh` for deeper investigation.
- If they do not match, remote mode is active. Tell subagents to use `gh api` against `headRefName` for file contents and tree exploration.

Pass each subagent:

- PR number.
- PR metadata.
- Repository owner/name.
- Complete PR diff.
- **Existing PR comments** (the full NDJSON output from the fetch above — inline, issue, and review-summary with `is_resolved`, `is_outdated`, `path`, `line`, `body`, `ai_origin`).
- Local mode flag and head branch.
- The exact focus area for that subagent.
- **Scope rule**: Focus findings on changed lines. For pre-existing issues in unchanged code, report only critical impact categories (security breach, data corruption/loss, service outage, compliance violation) with a `[既存コード]` prefix.

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
- **Remove inter-agent duplicates**: findings citing the same file/line with the same underlying cause; keep the clearest/highest-confidence version.
- **Remove PR-comment duplicates**: for each remaining finding, check against the existing PR comments NDJSON fetched above. Mark as duplicate when the finding overlaps an unresolved existing comment (same path + line within ±5 AND same root cause, OR same target symbol/concept addressable by the same fix) and duplicate confidence is ≥ 70. Do NOT skip if `is_resolved == true` or `is_outdated == true`. Collect all skipped findings to emit in the `[既コメント済]` section below.
- Preserve the `[既存コード]` prefix and the critical impact category on any retained pre-existing finding.
- Keep subagent outputs intact during collection. The parent reviewer, not the subagents, decides final section placement.
- **Route test-related findings by content**: findings about missing tests, weak assertions, brittle tests, incorrect mocks/fixtures, boundary-value tests, negative/error-path tests, and integration coverage must go under `## テストに関する指摘`, regardless of which subagent produced them.
- If a runtime bug and a missing test share the same root cause, keep the bug in the regular priority section. Mention the missing test in the detail line when it is only supporting evidence; create a separate test finding only when a distinct test change is required.
- Output only actionable findings that require a concrete response. Do not output praise, compliance confirmations, "looks good" statements, or non-actionable observations.
- Reclassify priority by confidence:
  - High: 90-100
  - Medium: 75-89
  - Low: notable issues below the main threshold only when a subagent explicitly reports one as worth mentioning.
- Validate that every final finding has a `[path/to/file.ext:line]` or `[path/to/file.ext:~line]` reference. Do not include findings without a line reference.
- Number findings sequentially across regular priority sections and the test section. Do not restart numbering per section.
- Omit empty priority sections and omit `## テストに関する指摘` when there are no actionable test findings.
- Omit `## レビュー注目ポイント` unless it contains concrete unresolved actions not already covered by numbered findings.
- If no actionable findings remain after deduplication, output only `対応が必要な指摘はありません。`
- If any findings were removed in the PR-comment deduplication step above, add a **`## [既コメント済] スキップした指摘`** section immediately before `## 総合評価`: one line per skipped finding as `- **[path:line]** 領域: <area> / 既存コメント ID: <id> (resolved=<bool>, ai_origin=<value>) — <reason>`. Omit this section entirely when nothing was removed.

### Formatting Rules

Respond entirely in Japanese.

Every finding must use this exact three-part structure: header, detail, separator.

- Header: `N. **[file:line]** 領域 (信頼度: XX): 短い一行の要約`
- Pre-existing header: `N. [既存コード] **[file:line]** 領域 (信頼度: XX): 短い一行の要約（重大カテゴリ）`
- Detail: `   - 詳細説明と推奨対応。`
- Separator: `---`

The `---` separator is mandatory after every finding, including the last one.
Regular priority sections must contain only non-test findings. Test-related findings must use the same finding format under `## テストに関する指摘`.

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

## テストに関する指摘

### 🟡 Medium Priority（信頼度75-89）

4. **[path/to/file.ext:line]** テスト品質 (信頼度: XX): 短い一行の要約
   - 詳細説明と推奨対応。

---

## レビュー注目ポイント

このセクションは任意。番号付き指摘でまだ扱っていない具体的な未対応事項がある場合だけ出力する。

---

## 総合評価

**マージ可否**: ✅ マージ可 / ⚠️ 条件付きマージ可 / ❌ マージ不可

総合コメントと優先度の高い対応事項のまとめ。
```

Omit empty priority sections.

### Post-Review: Post to GitHub

If at least one actionable finding remains, display:

> To post any findings as GitHub PR comments, use the `pr-comment-post` skill:
> Tell me: "pr-comment-post スキルで 1 3 5 を投稿して" (specifying item numbers)
