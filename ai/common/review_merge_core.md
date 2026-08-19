Merge the per-AI PR review result files in <RUN_DIR> into `merged.json` and generate `report.html`. Respond in Japanese.

## Inputs

- <RUN_DIR>: run directory containing `claude.md` / `gemini.md` / `codex.md` (any subset). If none exists, stop and report the directory path.
- Each file follows the pr-review output format: numbered findings with a header line `N. **[path:line]** 領域 (影響度: XX / 信頼度: XX): summary`, an indented detail bullet, and a `---` separator, grouped under priority sections.

## Workflow

1. Read every existing result file. Parse each finding: original number, file path, line spec, 領域, 影響度, 信頼度, priority section, summary, detail text. Ignore `## [既コメント済] スキップした指摘` and `## 総合評価` sections.
2. Merge findings that point at the same root cause (same file and same/overlapping lines, or clearly the same issue in meaning even if line numbers differ slightly). Never drop any source text: a merged item keeps every AI's original finding verbatim in `sources`.
3. For each merged item set: `file` and `line_spec` from the most confident source, `area` from the most confident source, `priority` = highest among sources (high > medium > low; section headings map 🔴→high, 🟡→medium, 🟢→low), and write a one-sentence Japanese `summary` for the merged item yourself.
4. Number items sequentially (`id` starting at 1), ordered high → medium → low.
5. Carryover: resolve the previous run — the newest sibling run directory of <RUN_DIR> (same parent) that contains `merged.json`, excluding <RUN_DIR> itself. If found, read its `merged.json`, `state.json`, `fix/fix_state.json`, and `post/post_state.json` (each if present). For each new item that matches a previous item (same file and same root cause), branch on the previous `state.json`'s `schema_version`:
   - `1` (legacy): `adopt: false` or unset → `"skipped_before"`; `adopt: true` → the fix outcome lookup below.
   - `2`: `decision` `"dismiss"` or `null` → `"skipped_before"`; `"fix"` → the fix outcome lookup below; `"post"` → the post outcome lookup below.
   - Fix outcome lookup: find the previous item's id in fix_state.json `items` and use its `status`: `fixed` → `"fixed_before"`, `skipped` → `"fix_skipped_before"`, `rejected` → `"fix_rejected_before"`. If fix_state.json is missing or unreadable, its `run_dir` is not the previous run, the id is absent, or the status is `pending` → `"should_be_fixed"`. Never infer an outcome from group status or design files.
   - Post outcome lookup: find the previous item's id in post_state.json `items` and use its `status`: `posted` → `"posted_before"`, `skipped` → `"post_skipped_before"`. If post_state.json is missing or unreadable, its `run_dir` is not the previous run, or the id is absent → `"should_be_posted"`.
   No previous run, no state, or no match → `"carryover": null`.
6. Fetch report metadata before writing JSON: `gh pr view <PR_NUMBER> --json url,title,author,headRefName,headRefOid` and `gh repo view --json nameWithOwner,url`. Store the PR URL/title/author login/head branch/head SHA and repository name/URL in the schema below. The report uses these values for its header, GitHub links, and code-context fallback.
7. Write `<RUN_DIR>/merged.json`, then render and serve the report. Start the server **without** `--open` through a mechanism that survives the current command environment. Obtain its URL and independently confirm that `<URL>/report.html` responds successfully before opening that URL in a browser exactly once. If the server start fails, retry only the server start and verification; never open a browser before verification or repeat the browser-open step. A supported fallback is:

```bash
python3 ~/.config/ai-pr/bin/generate_review_report.py <RUN_DIR>/merged.json <RUN_DIR>/report.html
nohup python3 ~/.config/ai-pr/bin/serve_review_report.py <RUN_DIR> >/dev/null 2>&1 &
```

8. Print a Japanese summary: per-AI finding counts, merged item count, how many duplicates were merged, carryover counts, and the follow-up usage — each item is decided as 🔧 修正する / 💬 コメント投稿 / 🚫 対応しない, and the decisions save directly to `state.json` in <RUN_DIR>; use the manual save button or accept the confirmation after all items are decided. After saving, the `review-fix` (修正) skill auto-selects the 修正 items and `review-post` (PRコメント投稿) the 投稿 items — invoke either with <RUN_DIR>, no item numbers needed. To reopen the report later (the report server stops after being idle), the user runs the **zsh shell function** `review-report` (or `review-report <PR番号>`) instead of opening `report.html` directly — not a skill, so it is absent from the skill list; verify with `type review-report`, never by listing `~/.claude/skills/`. It reuses a live server for this run or starts a new one, so state saves stay server-backed instead of falling back to a file-save dialog. Present it to the user as a shell command, never as a skill.

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
