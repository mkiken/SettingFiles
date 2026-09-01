---
name: review-merge
description: >
  Merge multi-AI PR review results into merged.json and an HTML report. Accepts
  a run directory; defaults to the current branch's latest PR run.
---

Parse the arguments after the skill name: the first token, if present, is <RUN_DIR>. If absent, resolve the current branch's PR via `gh pr view --json number --jq .number` and run `bash ~/.config/ai-pr/bin/ai_review_run_dir.sh --latest <PR_NUMBER>` to get <RUN_DIR>.

For the report server, use `mcp__context_mode__ctx_execute` with `background: true` and a short timeout when that tool is available; run `serve_review_report.py` without `--open`. Its returned URL must be independently fetched before opening it once in the browser. If context-mode is unavailable, use the core fallback and still verify the server before one browser-open action.

Merge the per-AI PR review result files in <RUN_DIR> into `merged.json` and generate `report.html`. Respond in Japanese.

## Inputs

- <RUN_DIR>: run directory containing `claude.md` / `gemini.md` / `codex.md` (any subset). If none exists, stop and report the directory path.
- Each file follows the pr-review output format: numbered findings with a header line `N. **[path:line]** 領域 (影響度: XX / 信頼度: XX): summary`, an indented detail bullet, and a `---` separator, grouped under priority sections.

## Workflow

1. Read every existing result file. Parse each finding: original number, file path, line spec, 領域, 影響度, 信頼度, priority section, summary, detail text. Ignore `## [既コメント済] スキップした指摘` and `## 総合評価` sections.
2. Merge findings that point at the same root cause. Two findings merge only when both hold: (a) same `file`; (b) one fix at one place resolves both — the same symbol, same expression, or the same overlapping line range. Differing line numbers do not by themselves block a merge, and identical line numbers do not by themselves justify one: findings at the same line whose fixes are independent stay separate. When you cannot state the single fix that resolves both, do not merge. Never drop any source text: a merged item keeps every AI's original finding verbatim in `sources`.
3. For each merged item set: `file` and `line_spec` from the most confident source, `area` from the most confident source, `priority` = highest among sources (high > medium > low; section headings map 🔴→high, 🟡→medium, 🟢→low), and write a one-sentence Japanese `summary` for the merged item yourself.
4. Number items sequentially (`id` starting at 1), ordered high → medium → low.
5. Carryover: resolve the previous run — the newest sibling run directory of <RUN_DIR> (same parent) that contains `merged.json`, excluding <RUN_DIR> itself. If found, read its `merged.json`, `state.json`, `fix/fix_state.json`, and `post/post_state.json` (each if present). For each new item that matches a previous item (same file and same root cause), branch on the previous `state.json`'s `schema_version`:
   - `1` (legacy): `adopt: false` or unset → `"skipped_before"`; `adopt: true` → the fix outcome lookup below.
   - `2`: `decision` `"dismiss"` or `null` → `"skipped_before"`; `"fix"` → the fix outcome lookup below; `"post"` → the post outcome lookup below.
   - Fix outcome lookup: find the previous item's id in fix_state.json `items` and use its `status`: `fixed` → `"fixed_before"`, `skipped` → `"fix_skipped_before"`, `rejected` → `"fix_rejected_before"`. If fix_state.json is missing or unreadable, its `run_dir` is not the previous run, the id is absent, or the status is `pending` → `"should_be_fixed"`. Never infer an outcome from group status or design files.
   - Post outcome lookup: find the previous item's id in post_state.json `items` and use its `status`: `posted` → `"posted_before"`, `skipped` → `"post_skipped_before"`. If post_state.json is missing or unreadable, its `run_dir` is not the previous run, or the id is absent → `"should_be_posted"`.
   No previous run, no state, or no match → `"carryover": null`.
6. Fetch report metadata before writing JSON: `gh pr view <PR_NUMBER> --json url,title,author,headRefName,headRefOid` and `gh repo view --json nameWithOwner,url`. Store the PR URL/title/author login/head branch/head SHA and repository name/URL in the schema below. The report uses these values for its header, GitHub links, and code-context fallback.
7. Write `<RUN_DIR>/merged.json`, then render/serve the report. Start a server that survives the command environment, without `--open`; obtain its URL, independently verify `<URL>/report.html`, then open it exactly once. On start failure, retry only startup and verification; never open before verification or more than once. Supported fallback:

```bash
python3 ~/.config/ai-pr/bin/generate_review_report.py <RUN_DIR>/merged.json <RUN_DIR>/report.html
nohup python3 ~/.config/ai-pr/bin/serve_review_report.py <RUN_DIR> >/dev/null 2>&1 &
```

8. Print a Japanese summary with per-AI finding counts, merged-item count, duplicate-merge count, carryover counts, and follow-up usage. Decisions are 🔧 修正する / 💬 コメント投稿 / 🚫 対応しない and save to `<RUN_DIR>/state.json`; after all decisions, use the manual save button or accept confirmation. Then the `review-fix` skill with `<RUN_DIR>` auto-selects 修正 items and the `review-post` skill 投稿 items; no item numbers. To reopen after idle shutdown, use zsh function `review-report` or `review-report <PR番号>`, not `report.html`; it is not a skill, so verify with `type review-report`, never skill listing. It reuses or starts this run's server, keeping saves server-backed instead of a file-save dialog. Present it as a shell command, never a skill.

## merged.json schema

```json
{
  "schema_version": 2,
  "pr_number": 123,
  "head_ref_oid": "<sha>",
  "head_ref_name": "feature/example",
  "repository": {
    "name": "owner/repository",
    "url": "https://github.com/owner/repository"
  },
  "pr_url": "https://github.com/owner/repository/pull/123",
  "pr_title": "PR title",
  "pr_author": "author-login",
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

`line_spec` keeps the original notation (`42`, `42-50`, `~42`). `carryover` is `null` / `"skipped_before"` / `"should_be_fixed"` (fix selected, outcome unknown) / `"fixed_before"` / `"fix_skipped_before"` / `"fix_rejected_before"` / `"posted_before"` / `"should_be_posted"` (post selected, outcome unknown) / `"post_skipped_before"`. `schema_version: 1` remains readable by the renderer but cannot show the new PR metadata or GitHub links.
