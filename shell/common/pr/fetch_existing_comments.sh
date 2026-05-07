#!/usr/bin/env bash
# Fetch all existing PR comments and output as NDJSON (one comment per line).
# Usage: fetch_existing_comments.sh <pr_number>
#
# Output fields per line:
#   id, kind (inline|issue|review_summary), path, line, start_line, side,
#   body, author, is_self, ai_origin (claude|codex|gemini|null),
#   is_resolved, is_outdated, thread_id, in_reply_to_id, created_at
#
# is_resolved / is_outdated come from GitHub GraphQL reviewThreads.
# On GraphQL failure (e.g. GitHub Enterprise), both default to false.

set -euo pipefail

PR_NUMBER="${1:?Usage: $0 <pr_number>}"

REPO_INFO=$(gh repo view --json owner,name)
OWNER=$(echo "$REPO_INFO" | jq -r '.owner.login')
REPO=$(echo "$REPO_INFO" | jq -r '.name')
CURRENT_USER=$(gh api user --jq .login 2>/dev/null || echo "")

# Build comment_id -> {thread_id, is_resolved, is_outdated} from GraphQL reviewThreads.
# On failure, THREAD_MAP stays as empty object → all comments get is_resolved=false.
THREAD_MAP='{}'
THREAD_DATA=$(gh api graphql \
  -f query='query($owner:String!,$repo:String!,$pr:Int!){
    repository(owner:$owner,name:$repo){
      pullRequest(number:$pr){
        reviewThreads(first:100){
          nodes{id isResolved isOutdated comments(first:100){nodes{databaseId}}}
        }
      }
    }
  }' \
  -f owner="$OWNER" -f repo="$REPO" -F pr="$PR_NUMBER" \
  --jq '.data.repository.pullRequest.reviewThreads.nodes // []' 2>/dev/null) || THREAD_DATA='[]'

THREAD_MAP=$(echo "$THREAD_DATA" | jq -c '
  reduce .[] as $t ({};
    reduce $t.comments.nodes[] as $c (.;
      .[$c.databaseId | tostring] = {
        thread_id: $t.id,
        is_resolved: $t.isResolved,
        is_outdated: $t.isOutdated
      }
    )
  )
')

emit() {
  local raw="$1" kind="$2"
  echo "$raw" | jq -c \
    --arg kind "$kind" \
    --arg cur "$CURRENT_USER" \
    --argjson tm "$THREAD_MAP" '
    (.id | tostring) as $id |
    ($tm[$id] // {thread_id:null,is_resolved:false,is_outdated:false}) as $t |
    (.body // "") as $b |
    {
      id: .id,
      kind: $kind,
      path: (.path // null),
      line: (.line // .original_line // null),
      start_line: (.start_line // .original_start_line // null),
      side: (.side // null),
      body: $b,
      author: (.user.login // null),
      is_self: (.user.login == $cur),
      ai_origin: (
        if ($b | test("🤖 \\*\\*Claude Code Review\\*\\*")) then "claude"
        elif ($b | test("🤖 \\*\\*Codex Review\\*\\*")) then "codex"
        elif ($b | test("🤖 \\*\\*Gemini Code Review\\*\\*")) then "gemini"
        else null end
      ),
      is_resolved: $t.is_resolved,
      is_outdated: $t.is_outdated,
      thread_id: $t.thread_id,
      in_reply_to_id: (.in_reply_to_id // null),
      created_at: (.created_at // null)
    }
  '
}

# Issue / PR conversation comments
gh api "repos/$OWNER/$REPO/issues/$PR_NUMBER/comments" --paginate 2>/dev/null \
  | jq -c '.[]' | while IFS= read -r c; do emit "$c" "issue"; done

# Review summary bodies (skip blank bodies — GitHub auto-generates empty review objects)
gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/reviews" --paginate 2>/dev/null \
  | jq -c '.[] | select(.body and .body != "")' | while IFS= read -r c; do emit "$c" "review_summary"; done

# Inline code review comments
gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments" --paginate 2>/dev/null \
  | jq -c '.[]' | while IFS= read -r c; do emit "$c" "inline"; done
