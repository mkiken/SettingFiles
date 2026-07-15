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
10. For any finding that depends on a specific external CLI/API/parser/library behavior or output format, require a minimal reproduction against the applicable version or an authoritative primary source. If neither is available, report it only as `要検証` with confidence below 75, or drop it. This applies at every priority level; code-only claims do not need this extra verification.
11. If any finding was skipped as an existing-comment duplicate, report it in the `[既コメント済]` section per the Output Format section below.

### Verify High Findings

Re-verify every High-priority finding as a skeptic before final output. Findings that depend on external CLI/API/parser/library behavior or output formats must also satisfy Aggregate item 10 regardless of priority; do not otherwise re-verify Medium/Low findings.

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
