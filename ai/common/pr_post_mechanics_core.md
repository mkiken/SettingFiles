## PR Metadata And Re-Anchoring

1. Get PR metadata:

```bash
gh pr view --json number,headRefOid
gh repo view --json owner,name
```

If `gh pr view` fails, ask the user for the PR number. Inline comments require a valid `commit_id`; if it cannot be retrieved, fall back to `gh pr comment`.

2. If the review result this index was built from was produced against a different head commit (its headRefOid, when known, differs from the current one), do not post with stale anchors: diff the two revisions for the affected files, re-anchor each selected item's line to the current head, and check whether the newer commits already addressed an item. Surface every adjustment (old→new line) and each already-addressed candidate in the preview so the user decides whether to post or skip it.

3. Before building the preview, verify every selected item can actually be an inline comment. GitHub anchors inline comments only to lines the diff shows, so fetch `gh pr diff {pr_number} --patch` and build, per file, the set of head-side line numbers the hunks cover: walk each `@@ -old +start,count @@` header, then count added (`+`) and context (` `) lines forward from `start`, skipping removed (`-`) lines. An item qualifies only when its `line` — and, for a range, both `start_line` and `line` — is in that set. Hunks are non-contiguous, so a line can fall in a gap between them even when the head commit matches and no `~` prefix is present; matching commits do not imply a valid anchor.

   For each item outside the set, look for a diff-covered line inside the same declaration or function body and re-anchor to it, surfacing `old→new` in the preview. Accept a candidate only when it still carries the finding's subject — the statement, field, or signature the item is about; a line that merely sits in the same block (a closing brace, a blank line, an unrelated statement) moves the comment away from what it describes, so treat it as no candidate at all. When no such line exists, mark the item `※diff範囲外（個別コメントで投稿）` in the preview — post it as an individual general comment without asking the user how to handle it; folding into the review body or dropping it are not options. Never send an unverified out-of-range item to the Review API.

   Post exactly one `gh pr comment` for each out-of-range finding after the inline review succeeds. Its body must contain the quoted `{ai_header}`, `対象: {file}:{line_spec}`, and the normal finding body. Build it with `printf`, preflight real newlines (no literal `\\n`), record its returned URL/comment ID, then re-fetch `repos/{owner}/{repo}/issues/comments/{comment_id}` and require the body to match exactly. Do not collapse multiple findings into one general comment or post them before the selected inline review is verified.

## Preview And Confirm

Show only the selected items, keeping their original serial numbers:

```text
投稿予定のレビューコメント一覧:

4. [src/auth.ts:42] 🔴 High | Security: トークンがログに露出する可能性
7. [src/db.ts:120] 🟡 Medium | Performance: N+1クエリ ※diff範囲外（個別コメントで投稿）
```

Before asking for confirmation, verify each listed item's serial number, `file:line`, and 概要 match the same-numbered entry in the source list this skill built its index from; on any mismatch, stop and report the discrepancy instead of proceeding.

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

When saving a JSON payload for later verification, always build the file directly with `jq -n --rawfile body "$file" ...` (or `--arg` from a variable) and redirect jq's own output; never write a JSON string assembled in a shell variable to a file, because a multiline body survives the variable as raw control characters and makes the file invalid JSON.

Never chain a verification `jq -e` with `&& echo OK`: the short-circuit swallows the failure and prints success even under `set -e`. Run the verification as its own command and branch on its exit status.

### No `@file` With `gh api -f`

`gh api -f key="@path/to/file"` does not read the file — `@` is a curl convention `gh api` does not implement, so the literal string `@path/to/file` is sent as the body. Always pass body content as an already-expanded shell variable (`-f body="$comment_body_with_header"`) or via `--input` with a `jq -n --rawfile body "$file" ...`-built JSON payload. After any post built from file content, re-fetch the created comment and confirm its body is the actual text, not a path string, before reporting success.

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

If the `pulls/{pr_number}/comments` fetch itself keeps failing with transient server errors (e.g. HTTP 503) while other endpoints respond, do not abandon verification: run the equivalent check via the GraphQL API, which is served separately and can survive REST partial outages. Field mapping: `side`/`start_side` live on `PullRequestReviewThread` as `diffSide`/`startDiffSide` (not on `PullRequestReviewComment`), `start_line` is `startLine`, the commit is `commit.oid`; match `path`, `line`, `startLine`, and the full `body` verbatim against the payload:

```bash
gh api graphql -f query='
query {
  repository(owner: "{owner}", name: "{repo}") {
    pullRequest(number: {pr_number}) {
      reviews(last: 5) {
        nodes {
          databaseId
          comments(first: 50) { totalCount nodes { path line startLine commit { oid } body } }
        }
      }
      reviewThreads(first: 50) {
        nodes {
          path line startLine diffSide startDiffSide
          comments(first: 1) { nodes { pullRequestReview { databaseId } } }
        }
      }
    }
  }
}'
```

Select the review by `databaseId == $review_id`, verify its comments, and take the side fields from the matching threads (single-line threads report `startLine` equal to `line` and a null `startDiffSide`; treat that as matching a comment posted without a range). Declare verification failure only after both the REST and GraphQL paths are unavailable or mismatch.

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

Ask the user to choose `submit して続行` or `中断`. If continuing, submit the pending review as `COMMENT`, then independently re-fetch its state. Continue only when the state is `COMMENTED`; a submit HTTP error alone is not proof that the state change failed. If re-fetching fails or the state remains `PENDING`, abort without retrying. When `COMMENTED`, retry the Review API exactly once, and abort if that retry fails:

```bash
gh api --method POST repos/{owner}/{repo}/pulls/{pr_number}/reviews/$pending_id/events \
  -f event=COMMENT

gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews/$pending_id --jq .state \
| grep -qx COMMENTED
```

## Final Report

Report the number of posted comments and the path taken: Review API success, PENDING submit then retry success, individual fallback, or PENDING abort. Report inline-review comment count and out-of-range individual-comment count separately. Do not report counts or lists for items that were not posted.
