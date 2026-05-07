# Existing PR Comments Policy

When performing a PR review, you MUST check whether each finding you are about to report already exists as a comment on the PR. This section defines how to do that.

## Fetching Existing Comments

Before generating review findings, fetch the existing PR comments as NDJSON using:

```bash
bash <REPO_ROOT>/shell/common/pr/fetch_existing_comments.sh <PR_NUMBER>
```

Each output line is a JSON object with these fields:
- `id` — GitHub comment ID
- `kind` — `inline` (code-line comment), `issue` (conversation comment), or `review_summary`
- `path` — file path (inline only; null otherwise)
- `line` — line number (inline only; null otherwise)
- `body` — comment text
- `author` — GitHub username
- `is_self` — true if the current `gh` user posted it
- `ai_origin` — `"claude"`, `"codex"`, `"gemini"`, or `null`
- `is_resolved` — true if the review thread was resolved in GitHub UI
- `is_outdated` — true if the commented line no longer exists (diff moved)

## Duplicate Detection Rules

For each candidate finding, run through these checks **in order**:

1. **Exclude resolved and outdated comments from duplicate matching.**
   `is_resolved == true` or `is_outdated == true` → treat as non-existing. Re-reporting these is allowed (and useful — resolved does not mean fixed). When re-reporting a previously resolved issue, append to the finding's detail line: `(参考: 過去にresolved済みの既存コメント #<id> と同様の指摘)`

2. **Check for semantic overlap** with the remaining unresolved comments.
   A finding overlaps when **any one** of these holds:
   - Same `path` AND line within ±5 of the existing comment's `line` AND the same root cause (same bug type, vulnerability class, or design smell).
   - Same target symbol or concept regardless of path (e.g., both refer to the same function, same architectural decision).
   - The finding can be fully addressed by applying the fix already suggested in the existing comment.

3. **Do NOT treat these as duplicates:**
   - Same type of problem in a different file or at a different symbol (e.g., null-check missing in `auth.ts` vs. a newly added null-check missing in `profile.ts`).
   - A more specific finding that cannot be resolved by the same fix (e.g., generic "test coverage missing" vs. "boundary test for `getCount` missing").

4. **Confidence threshold for skipping.**
   Only skip if your confidence that the two findings describe the same issue is **≥ 70**. Below 70, output both — false negatives (missed issues) cost more than false positives (duplicate notices).

5. **Signal vs. noise: `ai_origin` is informational only.**
   Whether the existing comment was written by a human, a bot, or another AI model does not affect the duplicate decision. Judge on content, not authorship. Use `ai_origin` only in the skip log for context.

## Output: Skip Log Section

When one or more findings are skipped due to duplication, add a **`## [既コメント済] スキップした指摘`** section immediately before the `## 総合評価` / summary section of your output.

Format each skipped entry as:
```
- **[path:line]** 領域: <area> / 既存コメント ID: <id> (resolved=<bool>, ai_origin=<value>) — <one-line reason>
```

If no findings were skipped, omit this section entirely.

Example:
```markdown
## [既コメント済] スキップした指摘

> 既存PRコメントと意味的に重複したため出力から除外:

- **[src/auth.ts:42]** 領域: セキュリティ / 既存コメント ID: 1234567890 (resolved=false, ai_origin=claude) — トークンログ露出を `@reviewer-a` が指摘済み
- **[src/api.ts:88]** 領域: バグ検出 / 既存コメント ID: 1234567999 (resolved=false, ai_origin=gemini) — 同一のnull参照を Gemini が前回指摘済み
```
