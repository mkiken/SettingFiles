---
name: pr-create-by-branch
description: >
  Create a new GitHub Pull Request from the current branch to a specified target branch.
  Analyzes the diff to auto-generate PR title and body with summary, file changes,
  review focus points, breaking changes, and additional notes.
  Use this skill when the user wants to create a PR, open a pull request,
  or says things like "PRを作って", "PR作成", "プルリクエスト作りたい",
  "create PR to main", "open a PR". Always use this when creating new PRs.
model: opus
allowed-tools: Bash(gh:*), Bash(git:*), AskUserQuestion
argument-hint: "[targetBranch]"
---

## Purpose

Create a new GitHub Pull Request from the current branch by analyzing the diff to auto-generate an appropriate title and body.

## Phase 1: Gather information

### Get current branch

```bash
git branch --show-current
```

### Determine target branch

If `$ARGUMENTS` is empty, use `AskUserQuestion` to ask the user which branch to merge into.

Suggested options:

- `main`
- `develop`
- Enter manually

### Collect diff information

```bash
# Commit list
git log origin/{target}..HEAD --oneline

# Full diff
git diff origin/{target}...HEAD

# File change summary
git diff origin/{target}...HEAD --stat
```

## Phase 2: Generate title

Based on the commit history and diff, summarize the essence of the PR in one line:

- Within 70 characters
- Recommended conventional commit format: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`, etc.
- Describe what changed and why — not how

Examples:

```
feat: add user authentication with JWT token support
fix: resolve race condition in session cleanup
refactor: extract payment processing into dedicated service
```

## Phase 3: Generate body

Generate body using the sections below. Write based on the **final state (HEAD)**. Do not mention intermediate states or reverted changes.

### Section format

```markdown
## Summary

- Logical grouping of changes (bullet points)
- Focus on "what changed" and "why"

## Files Changed Summary

- `path/to/file.ext`: What changed in this file (do NOT include line counts)
- `path/to/another.ext`: What changed in this file

## Review Focus Points

- Points requiring special attention during review
- If nothing in particular: "特になし"

## Breaking Changes

- Breaking changes or migration requirements
- If none: "なし"

## Additional Notes

- Other information for reviewers
- Background on why this approach was chosen
- If nothing: omit this section
```

### diff analysis policy

- Describe based on the final state (HEAD). Do not mention intermediate states or reverted changes.
- Background information for reviewers (why this approach was chosen, etc.) may be included.
- Be concise. Avoid padding or filler text.

## Phase 4: Confirm with user

Display the generated title and body in a code block:

```
## 生成されたPR title

{title}

## 生成されたPR body

{body}
```

Then use `AskUserQuestion` to confirm:

> このtitle/bodyでPRを作成しますか？

Options:

- 「はい、作成する」
- 「titleを修正したい」
- 「bodyを修正したい」
- 「キャンセル」

If the user wants modifications, accept the corrected content and re-confirm before proceeding.

## Phase 5: Create PR

Use a heredoc to pass the body to `gh pr create` to avoid escaping issues:

```bash
cat <<'PREOF' | gh pr create --base {target} --title "{title}" --body-file -
{body}
PREOF
```

### On success

- Display the PR URL
- Display: 「必要に応じて **Review Focus Points** を編集してください」

### On failure

If `gh pr create` fails:

- Display the error message
- Suggest possible causes (e.g., branch not pushed, already exists, no upstream)
- If the branch is not pushed, offer: `git push -u origin {current_branch}` then retry

## Notes

- If `git log origin/{target}..HEAD` returns nothing, warn: 「このブランチにはまだコミットがないか、originにpushされていません。」
- If the diff is very large (over 500 lines), summarize by file group rather than line-by-line analysis.
- Do NOT include line counts in the Files Changed Summary section — focus on what changed, not how much.
