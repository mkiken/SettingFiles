---
name: pr-review-subagents
description: >
  Comprehensive PR review using nine Codex custom subagents, parallelized up to the
  runtime limit, for bugs, security, architecture, error handling, git history, tests, performance, consistency, and simplification. Use when the
  user wants PR review with subagents, review-subagents, or parallel specialist
  reviewers. Accepts an optional PR number plus extra review instructions; if omitted,
  detect the current branch PR.
---

## Instructions

Review a PR with nine read-only specialist Codex subagents.

Inputs: parse the user's message as `[prNumber] [additionalInstructions...]`. If the first PR-like token is a PR number (`123` or `#123`) or PR URL, use it as `<PR_NUMBER>` and treat the rest as `<ADDITIONAL_INSTRUCTIONS>`. Otherwise, resolve the current branch's PR and treat any remaining request text as `<ADDITIONAL_INSTRUCTIONS>`:

```bash
gh pr view --json number --jq .number
```

Use only `<PR_NUMBER>` in gh commands. If `<ADDITIONAL_INSTRUCTIONS>` is non-empty, pass it to every subagent and apply it as review emphasis without overriding mandatory duplicate detection, line-number, safety, or output-format rules.

### Gather Once

Fetch context in the parent session:

```bash
gh pr view <PR_NUMBER> --json title,body,baseRefName,baseRefOid,headRefName,headRefOid,url,files,commits
gh pr diff <PR_NUMBER>
bash ~/.config/ai-pr/bin/format_pr_diff_with_line_numbers.sh <PR_NUMBER>
gh repo view --json nameWithOwner
git branch --show-current
git rev-parse HEAD
bash ~/.config/ai-pr/bin/fetch_existing_comments.sh <PR_NUMBER>
```

Local mode = current branch matches `headRefName`, `git rev-parse HEAD` matches `headRefOid`, **and** `git cat-file -e '<baseRefOid>^{commit}'` succeeds. If any check fails, use remote mode: subagents must inspect the PR head with `gh api`, not local files. This prevents unpushed or unrelated local commits, or a missing PR base commit, from contaminating the review.

Capture the full and line-numbered diffs through the configured large-output path, using source labels unique to the PR and `headRefOid`. Count the line-numbered diff before expanding it in the parent context.

When that path is context-mode:

- Use one batch command per gather target. Emit `DIFF_LINE_COUNT` before `NUMBERED_DIFF`; derive and emit `COMPACT_MANIFEST` before `FULL_NDJSON` from one `fetch_existing_comments.sh` result.
- Put each bounded derived block and its raw payload under distinct level-2 Markdown headings (for example, `## COMPACT_MANIFEST` and `## FULL_NDJSON`); a plain marker line can leave both in one indexed chunk. Query only the derived heading.
- Capture `FULL_DIFF` without querying raw hunks, and query only the bounded sections during capture. Design each capture query to return at most 100 lines, querying only a count and focused summary first when the result may be larger.
- Never append the manifest after the raw NDJSON or refetch a captured payload.

If a context-mode gather errors or times out before yielding results:

- Query the expected source labels once; reuse every confirmed capture and never refetch it.
- If verification fails or a target remains unconfirmed, enter degraded mode and recover only that target once with bounded host-shell processing. Record recovered targets, count before emitting, and create no scratch files.
- Recover diffs at the exact `baseRefOid...headRefOid` locally or exact PR revisions via `gh api` remotely. Recover comments by running `fetch_existing_comments.sh` once in one process and emit only the compact manifest; fetch a specific comment by ID only when final duplicate adjudication needs its full body.
- Treat an unconfirmed failed attempt as incomplete and allow at most one degraded recovery. This path is the only exception to retaining the full raw payload in the parent; never dump it into context merely to satisfy that invariant.

Before spawning, derive a compact existing-comment manifest from the NDJSON. Include one record for every top-level inline thread (`kind=inline` and `in_reply_to_id=null`) with `id`, `path`, `line`, `start_line`, `is_resolved`, `is_outdated`, `thread_id`, `ai_origin`, and a concise body excerpt that preserves the root cause and requested fix. Keep the full NDJSON in the parent for final aggregation.

Pass every subagent directly: PR number, metadata, repo owner/name, the compact comment manifest, local mode, base/head names, `baseRefOid`, `headRefOid`, and `<ADDITIONAL_INSTRUCTIONS>`. For a line-numbered diff of at most 100 lines, also pass both diffs directly. For a larger diff, do not paste either full payload; pass the changed-file list and captured source labels instead. Every subagent must inspect every changed file and its relevant diff at the exact PR revisions (local mode: local head file plus `git diff <baseRefOid>...<headRefOid>`; remote mode: `gh api` contents at `headRefOid` plus the PR-files patch). Indexed snippets alone are insufficient. Do not refetch the whole PR diff or make duplicate detection depend only on an indexed source. Each subagent's focus and review rules are in its definition.

### Spawn

Run all nine exactly once, parallelized up to the child-agent slots available at runtime:

- `pr_reviewer_bugs`
- `pr_reviewer_security`
- `pr_reviewer_architecture`
- `pr_reviewer_errors`
- `pr_reviewer_history`
- `pr_reviewer_tests`
- `pr_reviewer_performance`
- `pr_reviewer_consistency`
- `pr_reviewer_simplification`

If fewer than nine child-agent slots are available, use waves. Launch the maximum safe number, start the next specialist whenever a slot becomes free, and continue until all nine have completed. Never combine review dimensions merely to fit the slot limit.

Each subagent stays read-only and returns Japanese findings in its configured format.
Read-only includes not creating scratch files: never redirect diffs, comments, or command output to files in the repository or elsewhere.
Inspect the passed context or indexed sources, or run read-only commands directly.

### Large-Output Invariants

Fetch each gather target at most once. Preserve the full raw payload for final aggregation, but return only bounded derived results to the parent. Count dynamically selected rows before emitting them; above 100 lines, or when few lines carry a large payload (minified JSON, base64, long single lines), return only the count and a focused summary, then narrow or paginate. Never repeat a fetch to recover data that the configured large-output path already captured. If the large-output path writes any temp files (e.g. a redirected diff or comment dump), delete them with `trash` (never `rm`) before finishing the review.

When an indexed capture contains both a bounded derived section and its raw payload, query only the derived section's marker, not field names shared with the raw payload. Do not add queries merely to satisfy generic query-count guidance; keeping the raw payload out of the parent context takes precedence.

### Context Handoff

Embed the compact existing-comment manifest records in every specialist's task payload. References to parent tool output, indexed sources, source labels, or inherited/forked context do not count as direct handoff.

### Additional Review Instructions

If `<ADDITIONAL_INSTRUCTIONS>` is non-empty, ensure every specialist received it and use it to prioritize aggregation. It must not override mandatory duplicate detection, line-number, safety, or output-format rules.

### Aggregate

1. Drop "no findings" messages from final findings but count them as zero in the summary.
2. Remove inter-agent duplicates (same root cause at the same file/line); keep the clearest, highest-confidence finding.
3. Recheck existing comments NDJSON. Skip a duplicate — same path within ±5 lines and same root cause, or same target symbol/concept fixable by the same change — with duplicate confidence >= 70, regardless of `is_resolved` / `is_outdated`. Below 70, or when the finding needs a different fix, keep it. Collect skipped findings for `[既コメント済]`; when the matched comment is resolved or outdated, say so in the reason (e.g. `resolved済みの既存コメント #<id> と同一根本原因`).
4. Route `[既存コード]` findings (critical pre-existing issues) to `## 既存コードに関する指摘`, keeping the critical category in the detail line.
5. Route all other test-related findings to `## テストに関する指摘` regardless of source agent. Pre-existing-vs-changed is decided first: a `[既存コード]` finding about tests goes to `## 既存コードに関する指摘`.
6. Same-root-cause cross-agent overlaps: bug + missing test → keep the bug, mention the test gap as supporting detail unless a distinct test change is required; bug + error-handling gap → keep the bug, fold the handling aspect into its detail unless the handling fix is a separate change; bug + security vulnerability → keep the security finding (attack framing drives the fix), fold the bug behavior into its detail; architecture + consistency → keep the architecture finding (structural framing drives the fix), fold the precedent into its detail; history + consistency → keep the consistency finding (the cited counterpart path points at the fix), fold the commit evidence into its detail; consistency (reuse an existing utility) + simplification (duplicated logic) → keep the consistency finding (it names the concrete reuse target); architecture + simplification on the same structure → keep architecture when the fix crosses module boundaries, otherwise keep simplification. A merged finding takes the highest confidence and 影響度 of the pair.
7. Keep only actionable findings requiring a concrete response — no praise, compliance confirmations, or non-actionable observations.
8. Assign priority from 影響度 × 信頼度 per the Output Format section below. If an agent omitted 影響度, infer it from category and description.
9. Every finding needs `[path:line]` backed by 行番号根拠 (`[path:~line]` only for pre-existing code outside the diff). Drop findings whose 行番号根拠 is missing, uses `OLD`/deleted/approximate lines, or does not match the line-numbered diff. Spot-check suspicious anchors against the head-revision file. Never show 行番号根拠 in final output.
10. For any finding that depends on a specific external CLI/API/parser/library behavior or output format, require a minimal reproduction against the applicable version or an authoritative primary source. If neither is available, report it only as `要検証` with confidence below 75, or drop it. This applies at every priority level; code-only claims do not need this extra verification.
11. If any finding was skipped as an existing-comment duplicate, report it in the `[既コメント済]` section per the Output Format section below.

### Verify High Findings

Re-verify every High-priority finding as a skeptic before final output. Findings that depend on external CLI/API/parser/library behavior or output formats must also satisfy Aggregate item 10 regardless of priority; do not otherwise re-verify Medium/Low findings.

1. In one batched pass (read each cited file at most once), re-read the cited head-revision code plus enough surrounding context to test the claim (local mode: read the file; remote mode: `gh api` contents).
2. Actively seek refuting evidence: existing guards or validation, unreachable paths, framework/library behavior, tests proving the claimed failure cannot occur, or a misread diff.
3. Verdict per finding — confirmed: keep as High; unverifiable: downgrade to Medium and append 「要検証: <理由>」 to its detail; refuted: drop it and subtract it from the summary counts.
4. If any finding was refuted or downgraded, add one line before `## 総合評価`: `検証により High 指摘 N 件を棄却、M 件を Medium に降格しました。`

### Final Format

Finding-header 領域 labels: バグ検出, セキュリティ, アーキテクチャ, エラーハンドリング, Git履歴, テスト品質, パフォーマンス, 一貫性, 簡素化.

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
| 一貫性 | N | XX |
| 簡素化 | N | XX |
```

## Result File Output

Run `printenv AI_REVIEW_OUTPUT_FILE`. If it prints a path: after presenting the final review output, create the parent directory (`mkdir -p`) and write the exact same markdown — from the first line of the review output to the last, with no extra commentary — to that path. Write the file even when the result is `対応が必要な指摘はありません。`. If the variable is unset or empty, skip this section entirely.

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
