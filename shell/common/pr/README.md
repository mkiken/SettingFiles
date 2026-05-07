# shell/common/pr

PR review utilities shared across Claude Code, Gemini CLI, and Codex.

## fetch_existing_comments.sh

Fetches all existing comments on a GitHub PR and outputs them as NDJSON (one JSON object per line).

### Usage

```bash
bash shell/common/pr/fetch_existing_comments.sh <pr_number>
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
bash shell/common/pr/fetch_existing_comments.sh <pr> | jq -c .kind | sort | uniq -c

# Count resolved comments (should match GitHub UI)
bash shell/common/pr/fetch_existing_comments.sh <pr> | jq 'select(.is_resolved==true)' | wc -l

# Verify self-detection
bash shell/common/pr/fetch_existing_comments.sh <pr> | jq 'select(.is_self==true) | .author'

# Verify ai_origin detection
bash shell/common/pr/fetch_existing_comments.sh <pr> | jq 'select(.ai_origin != null) | {id, author, ai_origin}'
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
