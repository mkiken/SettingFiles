---
name: pr-comment-post
description: >
  Post specific findings from pr-review results as GitHub PR inline comments.
  Use this skill when the user wants to post review findings to a GitHub PR,
  comment on a PR with specific numbered review items, or push review results to GitHub
  as inline code comments. Trigger whenever the user says things like "PRにコメントして",
  "レビュー結果を投稿して", "番号を指定してコメント", "GitHubにコメント" after running
  a PR review with pr-review skill. Accepts space- or comma-separated item numbers
  (e.g., "1 3 5" or "1,3,5").
---

## Instructions

- `ITEM_NUMBERS` = the item numbers in the user's message.
- `{ai_header}` = `🤖 **Codex Review**`.

## Goal

Post selected numbered findings from a previous `pr-review` result as one GitHub Pull Request Review, confirmed once, submitted together when possible.

## Workflow

1. Build an internal numbered index from the previous `pr-review` output. Its serial numbers are the source of truth: preserve them exactly and never reorder or renumber, across regular priority sections, `## テストに関する指摘`, and `## 既存コードに関する指摘` (single continuous numbering; never restart at 1).
   - Format: `N. [path/to/file.ext:line] Priority | Category: 概要`, where `N` is the original serial number. The review header is `N. **[path:line]** 領域 (影響度: XX / 信頼度: XX): 概要` — use the 領域 label as `Category` and the surrounding priority section heading as `Priority`; never copy the `(影響度: XX / 信頼度: XX)` parenthetical into posted comment bodies.
   - If `ITEM_NUMBERS` is empty, show the available numbered items and ask which to post; otherwise do not display the index.
2. Parse `ITEM_NUMBERS` as space- or comma-separated original serial numbers.
3. For each requested number, copy that index entry's `file_path`, `line_spec`, `priority`, `category`, and full description verbatim — never reconstruct or infer an item's content from its number. If a number has no matching entry, stop and report the mismatch instead of substituting another item.
   - Priority emoji: High `🔴`, Medium `🟡`, Low `🟢`.
   - Items anchored `[path:~line]` (pre-existing code outside the diff) cannot be inline comments: exclude them from the Review API `comments` array and post each via the no-file/line `gh pr comment` fallback, prefixing the body with `**[path:~line]**`.
4. Get PR metadata:

```bash
gh pr view --json number,headRefOid
gh repo view --json owner,name
```

If `gh pr view` fails, ask the user for the PR number. Inline comments require a valid `commit_id`; if it cannot be retrieved, fall back to `gh pr comment`.

5. If the `pr-review` result was produced against a different head commit (its headRefOid, when known, differs from the current one), do not post with stale anchors: diff the two revisions for the affected files, re-anchor each selected item's line to the current head, and check whether the newer commits already addressed an item. Surface every adjustment (old→new line) and each already-addressed candidate in the preview so the user decides whether to post or skip it.

## Preview And Confirm

Show only the selected items, keeping their original serial numbers:

```text
投稿予定のレビューコメント一覧:

4. [src/auth.ts:42] 🔴 High | Security: トークンがログに露出する可能性
```

Before asking for confirmation, verify each listed item's serial number, `file:line`, and 概要 match the same-numbered entry in the original `pr-review` output; on any mismatch, stop and report the discrepancy instead of proceeding.

Ask the user:

```text
上記 N 件をまとめて Pull Request Review として投稿しますか？
```

If confirmed, post exactly the displayed list. Otherwise abort without posting and ask the user to rerun with the desired item numbers.

Generate a 1-3 sentence Japanese review summary for the top-level review body, mentioning general concern areas, not file names or line numbers.

## Posting

Inline comment body format, with no AI header and no item number:

```markdown
{priority_emoji} **{Priority}** / **{Category}**: {Description}
```

### Newline Safety

Never write `\n` inside a normal quoted string in shell and expect it to become a newline. Build multiline bodies with `printf`, pass the resulting variable to `jq`/`gh`, and preflight that the body contains real blank lines and no literal `\n` sequences (the `jq -n ... -e` lines below). If a preflight fails, rebuild the body with `printf` and re-run it; never post a body that failed preflight.

Prefer the Review API:

```bash
summary="{summary}"
review_body=$(printf '{ai_header}\n\n%s' "$summary")
jq -n --arg body "$review_body" -e '$body | (contains("\\n") | not) and contains("\n\n")' >/dev/null

comments='[
  {"path":"path/to/file.ext","line":42,"side":"RIGHT","body":"🔴 **High** / **Security**: Description"},
  {"path":"path/to/file2.ext","start_line":15,"start_side":"RIGHT","line":20,"side":"RIGHT","body":"🟡 **Medium** / **Architecture**: Description"}
]'

api_response=$(jq -n \
  --arg body "$review_body" \
  --arg event "COMMENT" \
  --arg commit_id "{head_sha}" \
  --argjson comments "$comments" \
  '{body:$body,event:$event,commit_id:$commit_id,comments:$comments}' \
| gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews --input - 2>&1)
api_exit_code=$?
review_id=$(printf '%s' "$api_response" | jq -r '.id')
```

Every Review API comment must pair `line` with `side`. For a range, also pair `start_line` with `start_side`. Use `RIGHT` for lines in the PR head. Never send line-only objects: GitHub can interpret an unqualified location as a legacy diff position instead of a file line.

If `api_exit_code == 0`, continue to post-verification before reporting success. If it fails and `$api_response` contains `one pending review` or `pending review per pull request`, handle PENDING. Otherwise use individual-comment fallback.

After a successful Review API call, re-fetch the created review and verify the top-level body contains real newlines, not escaped text:

```bash
gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews/$review_id \
  --jq '.body | (contains("\\n") | not) and contains("\n\n")' \
| grep -qx true
```

If this verification fails, fix the body in place and re-verify — never post the review again:

```bash
gh api --method PUT repos/{owner}/{repo}/pulls/{pr_number}/reviews/$review_id \
  -f body="$review_body"
```

Then re-fetch the created review comments and verify every requested inline comment. Match by path and body, and require the expected commit, file line, side, and range start fields. Fetch via `pulls/{pr_number}/comments` filtered by `pull_request_review_id` — the `reviews/{review_id}/comments` endpoint returns legacy-schema objects without `line`/`side` and always fails this verification:

```bash
posted_comments=$(gh api "repos/{owner}/{repo}/pulls/{pr_number}/comments?per_page=100" --paginate \
  | jq --argjson rid "$review_id" '[.[] | select(.pull_request_review_id == $rid)]')
jq -n \
  --argjson expected "$comments" \
  --argjson actual "$posted_comments" \
  --arg commit_id "{head_sha}" \
  -e '
    ($actual | length) == ($expected | length) and
    all($expected[]; . as $want |
      any($actual[];
        .path == $want.path and
        .body == $want.body and
        .commit_id == $commit_id and
        .line == $want.line and
        .side == $want.side and
        (.start_line // null) == ($want.start_line // null) and
        (.start_side // null) == ($want.start_side // null)
      )
    )
  ' >/dev/null
```

Treat a null `line`, a legacy-only `position`, a count mismatch, or any anchor/body/commit mismatch as verification failure. Do not retry or repost, because that can create duplicate review comments. Report the review URL or ID and the exact mismatch for manual correction. Report success only after both the review-body and inline-comment verifications pass.

## Fallbacks

For non-PENDING Review API failures, first post the review summary once with `gh pr comment {pr_number} --body "$review_body"`, then post comments individually:

```bash
comment_body="{comment_body}"
comment_body_with_header=$(printf '> {ai_header}\n\n%s' "$comment_body")
jq -n --arg body "$comment_body_with_header" -e '$body | (contains("\\n") | not) and contains("\n\n")' >/dev/null

gh api repos/{owner}/{repo}/pulls/{pr_number}/comments \
  -f body="$comment_body_with_header" \
  -f commit_id="{head_sha}" \
  -f path="{file_path}" \
  -F line={end_line} \
  -f side="RIGHT"
```

For ranges, add `-F start_line={start_line} -f start_side="RIGHT"`. In individual fallback only, prefix each body with:

```markdown
> {ai_header}

{priority_emoji} **{Priority}** / **{Category}**: {Description}
```

If no file/line is available, use:

```bash
comment_body="{comment_body}"
gh pr comment {pr_number} --body "$comment_body"
```

For PENDING conflicts, retrieve the existing pending review:

```bash
viewer=$(gh api user --jq .login)
pending_id=$(gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews \
  --jq ".[] | select(.state==\"PENDING\" and .user.login==\"$viewer\") | .id" | head -1)
```

Ask the user to choose `submit して続行` or `中断`. If continuing, submit the pending review as `COMMENT`, retry the Review API exactly once, and abort if that retry fails:

```bash
gh api --method POST repos/{owner}/{repo}/pulls/{pr_number}/reviews/$pending_id/events \
  -f event=COMMENT
```

## Final Report

Report the number of posted comments and the path taken: Review API success, PENDING submit then retry success, individual fallback, or PENDING abort. Do not report counts or lists for items that were not posted.
