---
allowed-tools: Bash(gh:*), Read, Edit, Write, Bash(git:*)
description: "Implement code changes based on PR review comments, with design review phase before implementation."
argument-hint: [prCommentUrl] [instructions...]
---

## Instructions

- Interpret the first argument from `$ARGUMENTS` as the PR comment URL (`$PR_URL`) and the rest as implementation instructions (`$PROMPT`).
- Use `gh pr view $PR_URL --comments` to fetch the review comments. The `gh` command automatically resolves the PR from the comment URL.
- Follow the structured workflow below to implement the requested changes.

## Workflow

### Phase 1: Analysis

1. Fetch and analyze the PR comments related to `$PR_URL`
2. Understand the issue or improvement request based on `$PROMPT`
3. Identify the files and code sections that need modification

### Phase 2: Design Review (MANDATORY)

Create a comprehensive implementation design and present it to the user for approval:

#### **Modification Summary**

- Which comment to address
- What to modify (summary)

#### **Detailed Modification Plan**

- **Target Files**: Specify each file and modification location
- **Specific Changes**: Code-level changes
- **New Files Required**: Files that need to be created (if any)

#### **Impact Analysis**

- Other code affected by these changes
- Test files requiring updates
- Documentation update necessity

#### **Implementation Approach**

- Chosen approach and reasoning
- Alternative approaches if any

#### **Confirmation Points**

- Points requiring user confirmation
- Unclear points or decisions needed

**⚠️ IMPORTANT**: Ask the user: "この設計で実装を進めてよろしいですか？修正点があればお知らせください。"

**Wait for user approval before proceeding to Phase 3.**

### Phase 3: Implementation (Only after approval)

1. Implement the code changes based on the approved design
2. Ensure code quality and consistency with existing codebase
3. Follow project coding standards and best practices

### Phase 4: Review Changes

1. Review all modified files
2. Verify that changes align with the design
3. Check for potential issues or missing updates

### Phase 5: Pre-Action Preparation

Before presenting the unified action selection, resolve all information required to execute each action.

**⚠️ 原則**: 返信対象が review comment (`#discussion_r{id}`) またはスレッド可能な review comment の場合、**必ずスレッド返信API** (`gh api repos/{owner}/{repo}/pulls/{pull_number}/comments/{comment_id}/replies`) を使用すること。`gh pr comment` は thread API が使えない場合 (純粋な issue comment やスレッド対象が無い review) に限定する。

#### Step 5-1: Draft commit message

Generate a commit message that:
- References the PR comment
- Summarizes the changes made
- Follows conventional commit format if applicable

Do **not** create the commit yet — only draft the message.

#### Step 5-2: Resolve reply target

Parse `$PR_URL` and extract `OWNER`, `REPO`, `PULL_NUMBER` from the URL path. Then classify by fragment (`#` 以降):

| Fragment pattern | Action |
|---|---|
| `#discussion_r(\d+)` | Extract `COMMENT_ID` → `REPLY_PATH=thread` |
| `#pullrequestreview-(\d+)` | Extract `review_id` → **Go to Step 5-2a** |
| `#issuecomment-(\d+)` or no fragment | `REPLY_PATH=standalone` (no `COMMENT_ID`) |

If the fragment cannot be classified, use `AskUserQuestion` to ask the user which reply method to use before proceeding.

#### Step 5-2a: Resolve thread for `#pullrequestreview-{review_id}` URL

Fetch the inline comments attached to the review:

```bash
gh api repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}/comments \
  --jq '[.[] | {id: .id, path: .path, body: (.body | .[0:80])}]'
```

- **1 comment found**: Use that `comment_id` → `REPLY_PATH=thread`, `COMMENT_ID=<id>`
- **Multiple comments found**: Use `AskUserQuestion` to let the user select the target comment → `REPLY_PATH=thread`
- **0 comments found**: `REPLY_PATH=standalone`

#### Step 5-3: Determine author (bot / self)

Executed only when `COMMENT_ID` is available (i.e., `REPLY_PATH=thread`).

```bash
META=$(gh api "repos/${OWNER}/${REPO}/pulls/comments/${COMMENT_ID}" \
       --jq '{login: .user.login, type: .user.type}')
COMMENT_AUTHOR=$(echo "$META" | jq -r '.login')
COMMENT_AUTHOR_TYPE=$(echo "$META" | jq -r '.type')
SELF_LOGIN=$(gh api user --jq '.login' 2>/dev/null || echo "")

# Bot: type == "Bot" OR login ends with "[bot]"
IS_BOT=false
[ "$COMMENT_AUTHOR_TYPE" = "Bot" ] && IS_BOT=true
case "$COMMENT_AUTHOR" in *"[bot]") IS_BOT=true ;; esac

# Self
IS_SELF=false
[ -n "$SELF_LOGIN" ] && [ "$COMMENT_AUTHOR" = "$SELF_LOGIN" ] && IS_SELF=true
```

If `gh api user` fails, treat `IS_SELF=false` and proceed (bot detection still works).

#### Step 5-4: Fetch resolve target thread

Executed only when `REPLY_PATH=thread` AND (`IS_BOT=true` OR `IS_SELF=true`).

```bash
THREAD_JSON=$(gh api graphql \
  -F owner="$OWNER" -F name="$REPO" -F number="$PULL_NUMBER" \
  -f query='
    query($owner:String!,$name:String!,$number:Int!){
      repository(owner:$owner,name:$name){
        pullRequest(number:$number){
          reviewThreads(first:100){
            nodes{ id isResolved comments(first:50){ nodes{ databaseId } } }
          }
        }
      }
    }' \
  --jq "[.data.repository.pullRequest.reviewThreads.nodes[]
         | select(any(.comments.nodes[]; .databaseId == ${COMMENT_ID}))][0]")

THREAD_NODE_ID=$(echo "$THREAD_JSON" | jq -r '.id // empty')
THREAD_IS_RESOLVED=$(echo "$THREAD_JSON" | jq -r '.isResolved // false')
```

#### Step 5-5: Compute `CAN_OFFER_RESOLVE`

```
CAN_OFFER_RESOLVE = (REPLY_PATH == "thread")
                 && (IS_BOT || IS_SELF)
                 && (THREAD_NODE_ID is non-empty)
                 && (THREAD_IS_RESOLVED == false)
```

If `THREAD_IS_RESOLVED=true`, do **not** offer resolve (no-op prevention).

#### Step 5-6: Build reply body

```
ご指摘ありがとうございます。対応しました。

- Commit: {full_hash}
  - {commit_subject}
```

(Repeat per commit if multiple)

Note: At this stage the commit has not been created yet. Use the drafted message and placeholder hashes. The actual hashes will be filled in **after** the commit is created in Phase 6.

#### Step 5-7: Output preview

Before calling `AskUserQuestion`, print the following Markdown to chat:

```markdown
## 実装完了。以下を実行する準備ができました。

### コミットメッセージ（草案）
{commit message draft}

### Reply 宛先
- 方法: {Thread reply | Standalone}
- target: comment_id = {id}（author: {login}、type: {Bot|User}、role: {bot|self|other}）
- url: {reply target url}

### Reply 本文プレビュー
{reply body}

### Resolve 対象 thread
- thread_id: {PRRT_...}（現在: unresolved）
（または「対象外: standalone 経路 / 既に resolved / author が他人」）
```

---

### Phase 6: Unified Action Selection

#### Step 6-1: Unified AskUserQuestion

Present a **single** `AskUserQuestion` with the following options. Build the options list dynamically:

```
options = []

if CAN_OFFER_RESOLVE:
  options.append({
    label: "コミット & push & 返信 & resolve",
    description: "さらに元コメントの review thread を resolve します（author が bot/自分のため提示）。"
  })

if REPLY_PATH in ("thread", "standalone"):
  options.append({
    label: "コミット & push & 返信",
    description: "さらに上記プレビューの本文で元PRコメントに返信します（{thread reply|standalone}）。"
  })

options.append({ label: "コミット & push",  description: "commit 後に origin へ push します。返信・resolve はしません。" })
options.append({ label: "コミットのみ",     description: "git commit のみ作成。push も返信も resolve もしません。" })
```

Question: 「実装が完了しました。以下のうちどこまで自動実行しますか？（プレビューは上記参照）」

Wait for user selection before proceeding.

If the user selects "Other" or cancels, do nothing and report that no action was taken.

#### Step 6-2: Execute selected actions sequentially

Execute only the steps covered by the user's choice. Stop immediately if any step fails (unless a retry is chosen).

**Step A — Commit** (all choices)

```bash
git add -A  # or stage specific files reviewed in Phase 4
git commit -m "<drafted message>"
```

If commit fails: report the error and abort. Do not proceed to push/reply/resolve.

After commit, record remote HEAD for later reference:

```bash
BEFORE_SHA=$(git rev-parse origin/$(git branch --show-current) 2>/dev/null || git rev-parse HEAD^)
```

**Step B — Push** (choices 2, 3, 4)

```bash
git push origin HEAD
```

If push fails: use `AskUserQuestion` to ask `(a) 再試行 / (b) 中止`. On retry success, continue. On abort, skip reply and resolve and report.

**Step C — Reply** (choices 3, 4)

Build the actual reply body using real commit hashes from Step A:

```bash
git log ${BEFORE_SHA}..HEAD --format='%H %s'
```

Post using the method determined in Step 5-2:

```bash
# Thread reply
gh api "repos/${OWNER}/${REPO}/pulls/${PULL_NUMBER}/comments/${COMMENT_ID}/replies" \
  -X POST -f body="${BODY}"

# Standalone (issue comment) — only when REPLY_PATH=standalone
gh pr comment "${OWNER}/${REPO}#${PULL_NUMBER}" --body "${BODY}"
```

If thread reply fails:
- **DO NOT silently fall back to `gh pr comment`**.
- Report the error (status code, response body).
- Use `AskUserQuestion` to ask `(a) 再試行 / (b) standalone に降格 / (c) 中止`.
  - If downgrading from `#discussion_r` → warn the user that thread context will be lost.

Track reply result in `REPLY_STATUS` (`success` / `failed` / `skipped`).

**Step D — Resolve** (choice 4 only)

Before resolving, check `REPLY_STATUS`:
- If `REPLY_STATUS=failed`: use `AskUserQuestion` to ask `「返信が失敗しましたが resolve は実行しますか？」 (a) 実行する / (b) スキップ`.
- If `REPLY_STATUS=success` or `skipped by user`: proceed without additional confirmation.

```bash
gh api graphql \
  -F id="$THREAD_NODE_ID" \
  -f query='
    mutation($id:ID!){
      resolveReviewThread(input:{threadId:$id}){ thread{ id isResolved } }
    }'
```

If mutation fails or returns `isResolved=false`:
- Use `AskUserQuestion` to ask `(a) 再試行 / (b) スキップ`.

#### Step 6-3: Final summary

Report the result of each executed step:

```
## 実行結果
- ✅ Commit: {full_hash} {subject}
- ✅ Push: origin/{branch}
- ✅ Reply: {url} （thread reply）
- ✅ Resolve: thread {PRRT_...} を resolved に変更
```

Use `⚠️` for errors and `⏭️` for skipped steps.

---

## Output Format

### During Design Phase (Phase 2)

Output the design in Japanese following the structure above.

### During Implementation (Phase 3-4)

Provide progress updates for each step:

- "✅ ファイルXを修正しました"
- "✅ 変更内容を確認しました"

### During Execution (Phase 6)

- "✅ コミットを作成しました: [commit message]"
- "✅ リモートブランチにプッシュしました"
- "✅ 元のPRコメントに返信しました (<reply_url_or_comment_link>)"
- "✅ review thread を resolve しました (PRRT_...)"

### Final Summary

Provide a summary including:

- Modified files and changes made
- Commit hash and message
- Reply comment URL (if posted)
- Resolve result (if executed)
- Next steps (if any)

## Notes

- Always prioritize user approval on the design before implementation
- If user requests design changes, revise and re-present for approval
- Use Read tool to understand existing code before making changes
- Use Edit tool for precise modifications to existing files
- Use Write tool only when creating new files
- Ensure all changes are tested if applicable
- Follow the project's git commit conventions
- Commit / push / reply / resolve are all selected in a **single** `AskUserQuestion` at the end of Phase 5
- The resolve option is offered only when the original comment author is a bot or the authenticated user themselves, and the thread is currently unresolved
