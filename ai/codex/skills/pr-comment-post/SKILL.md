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

## Goal

Post selected numbered findings from a previous `pr-review` result as one GitHub Pull Request Review, confirmed once, submitted together when possible.

## Workflow

1. Build an internal numbered index from the previous `pr-review` output. The serial numbers assigned by `pr-review` are the source of truth: preserve them exactly and never renumber.
   - Format: `N. [path/to/file.ext:line] Priority | Category: 概要`, where `N` is the original `pr-review` serial number for that item.
   - Include regular priority sections and `## テストに関する指摘`, keeping the single continuous numbering used by `pr-review` (do not restart at 1 per section).
   - If the user's message already has numbers, do not display the full index.
   - If no numbers are specified, ask which numbers to post and show the available numbered items.
2. Parse requested numbers from spaces or commas. These refer to the original serial numbers from step 1.
3. For each requested number, look it up in the step 1 index and copy that entry's `file_path`, `line_spec`, `priority`, `category`, and full description verbatim. Do not reconstruct or infer an item's content from its number, and do not reorder or renumber. If a requested number has no matching entry, stop and report the mismatch instead of substituting another item.
   - Priority emoji: High `🔴`, Medium `🟡`, Low `🟢`.
4. Get PR metadata:

```bash
gh pr view --json number,headRefOid
gh repo view --json owner,name
```

If `gh pr view` fails, ask the user for the PR number. A valid `commit_id` is required for inline comments; if it cannot be retrieved, fall back to `gh pr comment`.

## Preview And Confirm

Show only the selected posting list, keeping each item's original `pr-review` serial number (do not renumber from 1):

```text
投稿予定のレビューコメント一覧:

4. [src/auth.ts:42] 🔴 High | Security: トークンがログに露出する可能性
```

Do not display any items that are not in the posting list.

Before asking for confirmation, self-check every item in the posting list: confirm its serial number, `file:line`, and 概要 match the same-numbered entry in the original `pr-review` output. If any number, file/line, or summary does not match its source item, stop and report the discrepancy instead of proceeding.

Ask:

```text
上記 N 件をまとめて Pull Request Review として投稿しますか？
```

If confirmed, continue with exactly the displayed list. Otherwise abort without posting and ask the user to rerun the request with the desired item numbers.

Generate a 1-3 sentence Japanese review summary for the top-level review body. Mention general concern areas, not file names or line numbers.

## Posting

Inline comment body format, with no AI header and no item number:

```markdown
{priority_emoji} **{Priority}** / **{Category}**: {Description}
```

Prefer the Review API:

```bash
api_response=$(jq -n \
  --arg body "🤖 **Codex Review**

{summary}" \
  --arg event "COMMENT" \
  --arg commit_id "{head_sha}" \
  --argjson comments '[
    {"path":"path/to/file.ext","line":42,"body":"🔴 **High** / **Security**: Description"},
    {"path":"path/to/file2.ext","start_line":15,"line":20,"body":"🟡 **Medium** / **Architecture**: Description"}
  ]' \
  '{body:$body,event:$event,commit_id:$commit_id,comments:$comments}' \
| gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews --input - 2>&1)
api_exit_code=$?
```

If `api_exit_code == 0`, report success. If it fails and `$api_response` contains `one pending review` or `pending review per pull request`, handle PENDING. Otherwise use individual-comment fallback.

## Fallbacks

For non-PENDING Review API failures, post comments individually:

```bash
gh api repos/{owner}/{repo}/pulls/{pr_number}/comments \
  -f body="{comment_body_with_header}" \
  -f commit_id="{head_sha}" \
  -f path="{file_path}" \
  -F line={end_line} \
  -f side="RIGHT"
```

For ranges, add `-F start_line={start_line} -f start_side="RIGHT"`. In individual fallback only, prefix each body with:

```markdown
> 🤖 **Codex Review**

{priority_emoji} **{Priority}** / **{Category}**: {Description}
```

If no file/line is available, use:

```bash
gh pr comment {pr_number} --body "{comment_body}"
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
