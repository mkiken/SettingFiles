---
name: pr-create-by-branch
description: >
  Create a GitHub Pull Request from the current branch to a target base branch.
  Analyze the branch diff to generate a PR title and body, confirm with the
  user, then run gh pr create. Use when the user wants to create or open a PR,
  says "PRを作って", "PR作成", "プルリクエスト作りたい", "create PR",
  "open a pull request", or invokes `$pr-create-by-branch`. Accepts an
  optional target base branch.
---

## Instructions

- `TITLE_ARG` = the PR title in the user's message (quoted string preferred;
  otherwise free text that is not a branch name).
- `TARGET_BRANCH_ARG` = the target base branch in the user's message.
- For every user confirmation, ask in plain text with numbered options.

## Purpose

Create a new GitHub Pull Request from the current branch by analyzing the diff against the target base branch to auto-generate the PR title and body.

## Gather Context

Run:

```bash
git branch --show-current
/bin/cat .github/PULL_REQUEST_TEMPLATE.md 2>/dev/null || echo "NO_TEMPLATE"
```

Template handling is defined in the **PR Body Format** section below.

Determine the target base branch: use `TARGET_BRANCH_ARG` when present; otherwise ask the user with the confirmation method from Instructions, offering `main`, `develop`, and manual entry.

Fetch and collect the branch comparison:

```bash
git fetch origin <TARGET_BRANCH>
git log origin/<TARGET_BRANCH>..HEAD --oneline
git diff origin/<TARGET_BRANCH>...HEAD --stat
git diff origin/<TARGET_BRANCH>...HEAD
```

If there are no commits or no diff, warn: 「このブランチにはまだコミットがないか、originにpushされていません。」

## Determine Title

If `TITLE_ARG` is present, use it as the PR title as-is.

Otherwise generate 2–3 candidate titles from the diff and ask the user to pick one or enter their own, with the confirmation method from Instructions. Candidate rules:

- Within 70 characters.
- Conventional prefix when it fits: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`, etc.
- Describe what changed and why — not how.

Examples:

```text
feat: add user authentication with JWT token support
fix: resolve race condition in session cleanup
refactor: extract payment processing into dedicated service
```

## Generate Body

Generate the body following the **PR Body Format** section below. When a template exists, fill it with concrete generated content and remove unused placeholder text.

## Confirm

Display the generated title and body fenced with ````markdown (longer than any code fence the body may contain):

````markdown
## 生成されたPR title

<title>

## 生成されたPR body

<body>
````

Then ask 「このtitle/bodyでPRを作成しますか？」 with the confirmation method from Instructions, with exactly these options:

1. `はい、作成する`
2. `titleを修正したい`
3. `bodyを修正したい`
4. `キャンセル`

On a modification choice, collect the corrected content, re-display, and confirm again. Create the PR only after the user chooses `はい、作成する`.

## Create PR

Pass the body via stdin to avoid escaping issues:

```bash
/bin/cat <<'PREOF' | gh pr create --base <TARGET_BRANCH> --title "<TITLE>" --body-file -
<generated PR body>
PREOF
```

On success:

- Display the PR URL.
- Display 「必要に応じて **Review Focus Points** を編集してください」.

On failure:

- Show the `gh pr create` error and check whether the branch has an upstream.
- If the branch is not pushed, offer `git push -u origin <CURRENT_BRANCH>`, then retry only after user confirmation.

## Cleanup

Delete any temporary files created while preparing the title, body, or diff before finishing.

### PR Body Format

If `.github/PULL_REQUEST_TEMPLATE.md` exists in the repository root, use its structure as the base and fill each section in the same style as the default sections below (short overview first, structured bullets for implementation details). Otherwise use:

````markdown
## Summary

- 1–3 sentences: what this PR changes and why, at a glance.

## 実装内容

- One top-level bullet per logical change group (**bold** short title).
  - Nested bullets listing the related files as `path`: what changed.

## Review Focus Points

特になし

<!-- レビュー観点はPR作成者が記入 -->

## Breaking Changes

- Breaking changes or migration requirements; if none: "なし"

## Additional Notes

- Reviewer-useful background (e.g. why this approach was chosen); omit this section when empty.
````

Rules:

- Describe the final state at HEAD: never reverted changes, overwritten intermediate states, or trial-and-error.
- Group by logical change; no separate file-by-file section — file details live in 実装内容 as nested bullets. Do not include line counts like +X/-Y.
- Keep Summary short; 実装内容 carries the structure. If the diff is large (e.g. exceeds 500 lines), summarize by change group rather than line-by-line.
- Be concise, no filler; produce raw markdown directly usable as the PR body.
