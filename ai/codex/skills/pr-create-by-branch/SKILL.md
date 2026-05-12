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

## Purpose

Create a new GitHub Pull Request from the current branch by analyzing the final
diff against the selected base branch and generating a concise title/body.

## Gather Context

Run:

```bash
git branch --show-current
gh repo view --json nameWithOwner
test -f .github/PULL_REQUEST_TEMPLATE.md && sed -n '1,240p' .github/PULL_REQUEST_TEMPLATE.md || printf '%s\n' 'NO_TEMPLATE'
```

Determine the target base branch:

- Use the branch supplied in the user's message when present.
- If the prompt came from `cx-pr-create`, the selected branch should already be
  present in the user's message.
- If no target branch is available, ask with `request_user_input` and offer
  common base branches found in the repository, such as `main` and `develop`.

Fetch and analyze the branch comparison:

```bash
git fetch origin <TARGET_BRANCH>
git log origin/<TARGET_BRANCH>..HEAD --oneline
git diff origin/<TARGET_BRANCH>...HEAD --stat
git diff origin/<TARGET_BRANCH>...HEAD
```

If there are no commits or no diff against `origin/<TARGET_BRANCH>`, warn the
user that the branch may not contain PR-ready changes or may not be pushed.

## Generate Title

Generate one PR title that:

- Is no longer than 70 characters.
- Uses a conventional prefix when it naturally fits, such as `feat:`, `fix:`,
  `refactor:`, `docs:`, or `chore:`.
- Describes what changed and why, not low-level mechanics.

Examples:

```text
feat: add user authentication with JWT token support
fix: resolve race condition in session cleanup
refactor: extract payment processing into dedicated service
```

## Generate Body

Use `.github/PULL_REQUEST_TEMPLATE.md` as the structure when it exists. Fill the
template with concrete generated content and remove unused placeholder text.

When no template exists, use:

```markdown
## Summary

- Logical grouping of changes.
- Focus on what changed and why.

## Files Changed Summary

- `path/to/file.ext`: What changed in this file.

## Review Focus Points

特になし

<!-- レビュー観点はPR作成者が記入 -->

## Breaking Changes

なし

## Additional Notes

- Omit this section when there is nothing useful to add.
```

Rules:

- Describe the final state at `HEAD`, not intermediate commits, reverted work,
  or trial-and-error.
- Background useful to reviewers is acceptable when it explains why the final
  approach was chosen.
- Do not include line counts in `Files Changed Summary`.
- Keep the body useful for reviewers; avoid filler.

## Confirm

Display:

```markdown
## 生成されたPR title

<title>

## 生成されたPR body

<body>
```

Ask with `request_user_input`:

```text
このtitle/bodyでPRを作成しますか？
```

Use exactly these options:

- `はい、作成する`
- `title/bodyを修正したい`
- `キャンセル`

If the user requests a title or body change, ask which content to revise,
collect the corrected content, display the revised title/body, and confirm
again before creating the PR.

## Create PR

Only create the PR after the user chooses `はい、作成する`.

Use stdin for the body:

```bash
cat <<'PREOF' | gh pr create --base <TARGET_BRANCH> --title "<TITLE>" --body-file -
<generated PR body>
PREOF
```

On success:

- Display the PR URL.
- Display `必要に応じて **Review Focus Points** を編集してください`.

On failure:

- Show the `gh pr create` error.
- Check whether the branch has an upstream.
- If the branch is not pushed, offer to run:

```bash
git push -u origin <CURRENT_BRANCH>
```

Then retry `gh pr create` only after user confirmation.

## Cleanup

Delete any temporary files created while preparing the title, body, or diff
before finishing.
