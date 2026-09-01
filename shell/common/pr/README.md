# shell/common/pr

PR review utilities shared across Claude Code, Gemini CLI, and Codex.

Despite the directory name, the report scripts here also serve the `config-audit` skill:
`serve_review_report.py` detects which flow a run directory belongs to from its manifest
(`merged.json` → PR review, `audit.json` → config audit) and enforces that flow's decision set.
The whole directory is symlinked to `~/.config/ai-pr/bin` by `setup_ai_pr_tools`.

## format_pr_diff_with_line_numbers.sh

Renders a PR diff with explicit current-side line numbers for AI review prompts.
This avoids having models infer GitHub review lines from raw hunk headers.

### Usage

```bash
bash ~/.config/ai-pr/bin/format_pr_diff_with_line_numbers.sh <pr_number>
bash ~/.config/ai-pr/bin/format_pr_diff_with_line_numbers.sh --stdin < diff.patch
```

### Output records

| Record | Meaning |
|---|---|
| `FILE <path>` | Current file path for following hunks |
| `@@ ... @@` | Original unified diff hunk header |
| `NEW <line> <content>` | Added or modified line in the PR head |
| `CTX <line> <content>` | Unchanged context line in the PR head |
| `OLD <line> <content>` | Removed base-side line; do not use for GitHub review comments |
| `DELETED_FILE <path>` | File has no current-side target lines |

Review prompts should prefer `NEW` line numbers. Use `CTX` only when no changed
line can carry the finding, and never post an inline review comment using `OLD`.

## fetch_existing_comments.sh

Fetches all existing comments on a GitHub PR and outputs them as NDJSON (one JSON object per line).

### Usage

```bash
bash ~/.config/ai-pr/bin/fetch_existing_comments.sh <pr_number>
```

### Output fields

| Field | Type | Description |
|---|---|---|
| `id` | number | GitHub comment ID |
| `kind` | string | `inline`, `issue`, or `review_summary` |
| `path` | string\|null | File path (inline only) |
| `line` | number\|null | Line number (inline only) |
| `start_line` | number\|null | Start line for multi-line comments |
| `side` | string\|null | `RIGHT` or `LEFT` |
| `body` | string | Comment text |
| `author` | string\|null | GitHub username |
| `is_self` | boolean | True if posted by the current `gh` user |
| `ai_origin` | string\|null | `claude`, `codex`, `gemini`, or null |
| `is_resolved` | boolean | True if the review thread was resolved |
| `is_outdated` | boolean | True if the commented line no longer exists |
| `thread_id` | string\|null | GraphQL review thread ID |
| `in_reply_to_id` | number\|null | Parent comment ID for replies |
| `created_at` | string\|null | ISO 8601 timestamp |

`ai_origin` is detected by matching comment body prefixes:
- `🤖 **Claude Code Review**` → `claude`
- `🤖 **Codex Review**` → `codex`
- `🤖 **Gemini Code Review**` → `gemini`

`is_resolved` / `is_outdated` come from GitHub GraphQL `reviewThreads`. On failure (e.g., older GitHub Enterprise), both default to `false`.

### Unit tests

```bash
# Verify all three kinds are returned
bash ~/.config/ai-pr/bin/fetch_existing_comments.sh <pr> | jq -c .kind | sort | uniq -c

# Count resolved comments (should match GitHub UI)
bash ~/.config/ai-pr/bin/fetch_existing_comments.sh <pr> | jq 'select(.is_resolved==true)' | wc -l

# Verify self-detection
bash ~/.config/ai-pr/bin/fetch_existing_comments.sh <pr> | jq 'select(.is_self==true) | .author'

# Verify ai_origin detection
bash ~/.config/ai-pr/bin/fetch_existing_comments.sh <pr> | jq 'select(.ai_origin != null) | {id, author, ai_origin}'
```

### False-positive skip checklist

Use these cases when validating that the deduplication logic doesn't over-suppress findings:

| Scenario | Expected |
|---|---|
| Existing: `auth.ts:42` null ref / New finding: `profile.ts:88` same null ref pattern | Both reported (different path) |
| Existing: "`save` is doing too much" / New finding: "`saveAndNotify` (newly added) is doing too much" | New finding reported (different symbol) |
| Existing (resolved): magic number `3000` / New finding: same | New finding reported (resolved = not duplicate) |
| Existing (ai_origin=claude, unresolved): token log exposure / New finding: same | Skipped, logged as `[既コメント済スキップ]` |
| Existing (Bot `github-actions`): SQL injection / New finding: same location + same issue | Skipped (content match regardless of authorship) |
| Existing: "test coverage missing" (generic) / New finding: "boundary test for `getCount` missing" (specific) | New finding reported (granularity differs, different fix needed) |

## generate_audit_report.py

Renders `audit.json` (written by the `config-audit` skill) into a self-contained `report.html`
where each finding is decided as ✅ 適用する / 🚫 対応しない.

### Usage

```bash
python3 generate_audit_report.py <RUN_DIR>/audit.json <RUN_DIR>/report.html
```

Findings are grouped by `category` (`default` / `overlap` / `patch` / `ambiguity` / `concise` /
`conflict`) rather than by priority. Each item anchors to a file plus a named section, so the
surrounding code context is located by searching for the item's verbatim `quote` — not by line
number. A quote that no longer matches renders as a "見つかりません" notice, which flags a stale
finding instead of failing the render.

Items may declare `depends_on`. The report treats those as a symmetric, transitive group: choosing
適用する on one member prompts to include the rest, and saving stays blocked while any member of an
applied group is not itself applied.

## ai_audit_run_dir.sh

Run-directory management for config audits, keyed by platform instead of PR number (audits also run
outside any repository, so this one never touches `git remote`).

```bash
ai_audit_run_dir.sh <platform>            # create a run directory, print its path
ai_audit_run_dir.sh --latest <platform>   # print the newest run directory
```

`<platform>` is `claude` / `codex` / `gemini`. Layout is
`${AI_AUDIT_CACHE_ROOT:-~/.cache/ai-audit}/<platform>/<run-id>` with a `latest` symlink;
`AI_AUDIT_KEEP_RUNS` (default 5) older runs are pruned with `trash`.

Reopen a saved report with the zsh function `audit-report [platform]`, which reuses a live server
for that run so state saves stay server-backed.
