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
gh pr view <PR_NUMBER> --json title,body,baseRefName,headRefName,headRefOid,url,files,commits
gh pr diff <PR_NUMBER>
bash ~/.config/ai-pr/bin/format_pr_diff_with_line_numbers.sh <PR_NUMBER>
gh repo view --json nameWithOwner
git branch --show-current
git rev-parse HEAD
bash ~/.config/ai-pr/bin/fetch_existing_comments.sh <PR_NUMBER>
```

Local mode = current branch matches `headRefName` **and** `git rev-parse HEAD` matches `headRefOid`. If either check fails, use remote mode: subagents must inspect the PR head with `gh api`, not local files. This prevents unpushed or unrelated local commits from being reviewed as part of the PR.

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

### Additional Review Instructions

If `<ADDITIONAL_INSTRUCTIONS>` is non-empty, ensure every specialist received it and use it to prioritize aggregation. It must not override mandatory duplicate detection, line-number, safety, or output-format rules.

### Aggregate

1. Drop "no findings" messages from final findings but count them as zero in the summary.
2. Remove inter-agent duplicates (same root cause at the same file/line); keep the clearest, highest-confidence finding.
3. Recheck existing comments NDJSON. Skip an unresolved duplicate — same path within ±5 lines and same root cause, or same target symbol/concept fixable by the same change — with duplicate confidence >= 70. Never skip resolved or outdated comments; if they overlap, re-report and mention the past resolved comment in the detail. Collect skipped findings for `[既コメント済]`.
4. Route `[既存コード]` findings (critical pre-existing issues) to `## 既存コードに関する指摘`, keeping the critical category in the detail line.
5. Route all other test-related findings to `## テストに関する指摘` regardless of source agent. Pre-existing-vs-changed is decided first: a `[既存コード]` finding about tests goes to `## 既存コードに関する指摘`.
6. Same-root-cause cross-agent overlaps: bug + missing test → keep the bug, mention the test gap as supporting detail unless a distinct test change is required; bug + error-handling gap → keep the bug, fold the handling aspect into its detail unless the handling fix is a separate change; bug + security vulnerability → keep the security finding (attack framing drives the fix), fold the bug behavior into its detail. A merged finding takes the highest confidence and 影響度 of the pair.
7. Keep only actionable findings requiring a concrete response — no praise, compliance confirmations, or non-actionable observations.
8. Assign priority from 影響度 × 信頼度 per the Output Format section below. If an agent omitted 影響度, infer it from category and description.
9. Every finding needs `[path:line]` backed by 行番号根拠 (`[path:~line]` only for pre-existing code outside the diff). Drop findings whose 行番号根拠 is missing, uses `OLD`/deleted/approximate lines, or does not match the line-numbered diff. Spot-check suspicious anchors against the head-revision file. Never show 行番号根拠 in final output.
10. If any finding was skipped as an existing-comment duplicate, report it in the `[既コメント済]` section per the Output Format section below.

### Verify High Findings

Re-verify every High-priority finding as a skeptic before final output; do not verify Medium/Low.

1. In one batched pass (read each cited file at most once), re-read the cited head-revision code plus enough surrounding context to test the claim (local mode: read the file; remote mode: `gh api` contents).
2. Actively seek refuting evidence: existing guards or validation, unreachable paths, framework/library behavior, tests proving the claimed failure cannot occur, or a misread diff.
3. Verdict per finding — confirmed: keep as High; unverifiable: downgrade to Medium and append 「要検証: <理由>」 to its detail; refuted: drop it and subtract it from the summary counts.
4. If any finding was refuted or downgraded, add one line before `## 総合評価`: `検証により High 指摘 N 件を棄却、M 件を Medium に降格しました。`

### Final Format

Finding-header 領域 labels: バグ検出, セキュリティ, アーキテクチャ, エラーハンドリング, Git履歴, テスト品質, パフォーマンス.

Prepend this summary table before the first priority section of the Output Format skeleton below:

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
| パフォーマンス | N | XX |
```

### Output Format

Respond entirely in Japanese.

**Priority mapping (影響度 × 信頼度)** — self-assessed per finding. 影響度: High = data loss/outage/vulnerability/broad breakage, Medium = limited malfunction or degradation, Low = minor. 信頼度 = 0–100 certainty that the issue is real. Priority: High = 影響度High & 信頼度>=75; Medium = 影響度Medium & 信頼度>=75, or 影響度High & 信頼度<75 (append 「要検証」 to the detail); Low = 影響度Low & notable, or 影響度Medium & 信頼度<75 (append 「要検証」). The mapping decides priority only, never whether a finding is reported — the calling skill's actionability rules decide that.

Each finding MUST use this exact three-part structure:

- **Header line**: `N. **[file:line]** 領域 (影響度: XX / 信頼度: XX): 短い一行の要約` — path relative to repository root, `[path:line]` for a single line or `[path:startLine-endLine]` for a range; 領域 is a Japanese area label from the calling skill's dimension list. Inside `## 既存コードに関する指摘`, append `（重大カテゴリ）` to the summary.
- **Detail line**: `   - Full explanation and recommendation (indented sub-bullet)`. Do not cram the explanation into the header line.
- **Separator line**: `---` after every finding, including the last one — a hard structural requirement that must never be omitted.

Number findings sequentially across all sections — never restart numbering per section.

Use this skeleton, omitting empty sections and empty priority levels. The calling skill may prepend extra leading sections (e.g. a summary table) before the first priority section:

```markdown
## 🔴 High Priority（影響度High・信頼度75+）

1. **[path/to/file.ext:line]** 領域 (影響度: XX / 信頼度: XX): 短い一行の要約
   - 詳細説明と推奨対応。

---

## 🟡 Medium Priority

2. （同形式）

## 🟢 Low Priority

3. （同形式）

## テストに関する指摘

### 🟡 Medium Priority

4. （同形式、領域はテスト品質）

## 既存コードに関する指摘

### 🔴 High Priority（影響度High・信頼度75+）

5. （同形式、要約末尾に重大カテゴリ）

## [既コメント済] スキップした指摘

- **[path:line]** 領域: <area> / 既存コメント ID: <id> (resolved=<bool>, ai_origin=<value>) — <reason>

## 総合評価

**マージ可否**: ✅ マージ可 / ⚠️ 条件付きマージ可 / ❌ マージ不可

総合コメント。
```

Place `## [既コメント済] スキップした指摘` immediately before `## 総合評価`, one line per skipped finding as shown; omit the section when nothing was skipped. `## 総合評価` states the merge verdict line plus a short overall comment.

If no actionable findings remain after deduplication, output only (no skeleton, no 総合評価):

```markdown
対応が必要な指摘はありません。
```

If at least one actionable finding remains, append:

> To post any findings as GitHub PR comments, use the `pr-comment-post` skill:
> Tell me: "pr-comment-post スキルで 1 3 5 を投稿して" (specifying item numbers)
