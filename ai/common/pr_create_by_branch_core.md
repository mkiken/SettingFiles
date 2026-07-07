## Purpose

Create a new GitHub Pull Request from the current branch by analyzing the diff against the target base branch to auto-generate the PR title and body.

## Gather Context

Run:

```bash
git branch --show-current
/bin/cat .github/PULL_REQUEST_TEMPLATE.md 2>/dev/null || echo "NO_TEMPLATE"
```

If a template exists, use its structure as the body format instead of the default sections.

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

When a template exists, fill it with concrete generated content and remove unused placeholder text. Otherwise use:

```markdown
## Summary

- 1–3 sentences: what this PR changes and why.

## Implementation Details

- One bullet per logical change group.
  - Nested bullets with the concrete changes in that group.

## Review Focus Points

特になし

<!-- レビュー観点はPR作成者が記入 -->

## Breaking Changes

- Breaking changes or migration requirements; if none: "なし"

## Additional Notes

- Background for reviewers (e.g. why this approach was chosen); omit this section when empty.
```

Rules:

- Keep Summary short (1–3 sentences); Implementation Details carries the structure — group changes logically and nest specifics under each group.
- Describe the final state at HEAD; never intermediate or reverted changes.
- Do not include line counts.
- Be concise; no filler. If the diff exceeds 500 lines, summarize by change group rather than line-by-line.

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
