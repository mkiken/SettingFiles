---
name: review-merge
description: >
  Merge multi-AI PR review result files into merged.json and an HTML report.
  Use this skill when the user wants to merge, consolidate, or de-duplicate
  PR review findings from multiple AIs (Claude/Gemini/Codex) into one report,
  or says things like "レビュー結果をマージして", "merge the review results",
  "レポートを作って". Accepts an optional run directory; if none is given,
  detects the latest run for the current branch's PR automatically.
---

Parse the arguments after the skill name: the first token, if present, is <RUN_DIR>. If absent, resolve the current branch's PR via `gh pr view --json number --jq .number` and run `bash ~/.config/ai-pr/bin/ai_review_run_dir.sh --latest <PR_NUMBER>` to get <RUN_DIR>.

Merge the per-AI PR review result files in <RUN_DIR> into `merged.json` and generate `report.html`. Respond in Japanese.

## Inputs

- <RUN_DIR>: run directory containing `claude.md` / `gemini.md` / `codex.md` (any subset). If none exists, stop and report the directory path.
- Each file follows the pr-review output format: numbered findings with a header line `N. **[path:line]** 領域 (影響度: XX / 信頼度: XX): summary`, an indented detail bullet, and a `---` separator, grouped under priority sections.

## Workflow

1. Read every existing result file. Parse each finding: original number, file path, line spec, 領域, 影響度, 信頼度, priority section, summary, detail text. Ignore `## [既コメント済] スキップした指摘` and `## 総合評価` sections.
2. Merge findings that point at the same root cause (same file and same/overlapping lines, or clearly the same issue in meaning even if line numbers differ slightly). Never drop any source text: a merged item keeps every AI's original finding verbatim in `sources`.
3. For each merged item set: `file` and `line_spec` from the most confident source, `area` from the most confident source, `priority` = highest among sources (high > medium > low; section headings map 🔴→high, 🟡→medium, 🟢→low), and write a one-sentence Japanese `summary` for the merged item yourself.
4. Number items sequentially (`id` starting at 1), ordered high → medium → low.
5. Carryover: resolve the previous run — the newest sibling run directory of <RUN_DIR> (same parent) that contains `merged.json`, excluding <RUN_DIR> itself. If found, read its `merged.json` and `state.json` (if present). For each new item that matches a previous item (same file and same root cause):
   - previous state `adopt: false` (or unset) → `"carryover": "skipped_before"`
   - previous state `adopt: true` → `"carryover": "should_be_fixed"`
   No previous run, no state, or no match → `"carryover": null`.
6. Record the current PR head: `gh pr view <PR_NUMBER> --json headRefOid --jq .headRefOid` (PR number from the run directory path `pr-<N>`), stored as `head_ref_oid`.
7. Write `<RUN_DIR>/merged.json` (schema below), then render and open the report:

```bash
python3 ~/.config/ai-pr/bin/generate_review_report.py <RUN_DIR>/merged.json <RUN_DIR>/report.html
open -a "Google Chrome" <RUN_DIR>/report.html
```

8. Print a Japanese summary: per-AI finding counts, merged item count, how many duplicates were merged, carryover counts, and the follow-up usage — check items in the browser (状態ファイルを接続 → save state.json into <RUN_DIR>), then run `review-post` (PRコメント投稿) or `review-fix` (修正) with <RUN_DIR>.

## merged.json schema

```json
{
  "schema_version": 1,
  "pr_number": 123,
  "head_ref_oid": "<sha>",
  "run_dir": "/abs/path/to/run",
  "sources": ["claude", "codex"],
  "items": [
    {
      "id": 1,
      "file": "src/auth.ts",
      "line_spec": "42",
      "area": "セキュリティ",
      "priority": "high",
      "summary": "merged one-line Japanese summary",
      "carryover": null,
      "sources": [
        {"ai": "claude", "original_number": 4, "priority": "high",
         "impact": "High", "confidence": 85, "text": "original detail text"}
      ]
    }
  ]
}
```

`line_spec` keeps the original notation (`42`, `42-50`, `~42`). `carryover` is `null` / `"skipped_before"` / `"should_be_fixed"`.
