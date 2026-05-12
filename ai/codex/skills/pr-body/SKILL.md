---
name: pr-body
description: >
  Generate and optionally update a GitHub Pull Request body using gh.
  Use this skill when the user asks Codex to create, regenerate, rewrite,
  or apply a PR description/body, says "PR body", "PR本文", "PR説明を作って",
  or invokes `$pr-body`. Accepts an optional PR number; if omitted, detect
  the PR for the current branch.
---

## Purpose

Generate a review-ready PR body from the final PR diff, preserve meaningful
existing body content, show the change diff, and update GitHub only after user
confirmation.

## Inputs

Extract the PR number from the user's message if present. If it is not present,
run:

```bash
gh pr view --json number --jq .number
```

If no PR is found, ask the user for a PR number with `request_user_input`.

## Gather Context

Run these commands before drafting:

```bash
gh pr view <PR_NUMBER> --json number,url,title,body,author,headRefName,baseRefName
test -f .github/PULL_REQUEST_TEMPLATE.md && sed -n '1,240p' .github/PULL_REQUEST_TEMPLATE.md || printf '%s\n' 'NO_TEMPLATE'
gh pr diff <PR_NUMBER>
gh pr diff <PR_NUMBER> --name-only
```

Use the PR template as the body structure when it exists. Otherwise use the
default section format below.

## Drafting Rules

- Describe the final state at `HEAD`, not intermediate commits, reverted work,
  or trial-and-error.
- Preserve meaningful information from the existing PR body.
- Treat placeholder-only or template-only content as disposable.
- Preserve a non-default `Review Focus Points` section exactly when the existing
  body contains content other than empty text or `特になし`.
- Write `特になし` for `Review Focus Points` only when creating a new body or
  when the existing section is empty/default.
- Do not include line counts such as `+12/-3` in `Files Changed Summary`.
- Keep reviewer-facing content concise and concrete.

Default body format:

```markdown
## Summary

- Logical grouping of changes.
- Explain what changed and why.

## Files Changed Summary

- `path/to/file.ext`: Brief description of what changed.

## Review Focus Points

特になし

<!-- レビュー観点はPR作成者が記入 -->

## Breaking Changes

なし

## Additional Notes

- Omit this section when there is nothing useful to add.
```

## Confirmation Flow

Display the generated body in a markdown code block.

Then display a visual diff from the existing body to the generated body:

````markdown
### 既存body → 新bodyの変更差分

```diff
- removed line
+ added line
  unchanged line
```
````

If the existing body is empty or template-only, display:

```text
(既存bodyは空またはテンプレートのみのため、全て新規追加)
```

Ask with `request_user_input`:

```text
このPR bodyをPR #<PR_NUMBER> に反映しますか？
```

Use exactly these options:

- `はい、反映する`
- `いいえ、表示のみ`

## Apply

Only apply after the user chooses `はい、反映する`.

Use stdin to avoid shell escaping issues:

```bash
cat <<'EOF' | gh pr edit <PR_NUMBER> --body-file -
<generated PR body>
EOF
```

After success, show the PR URL and:

```text
必要に応じて **Review Focus Points** を確認・編集してください
```

If the user declines, make no GitHub changes.

## Cleanup

Delete any temporary files created while preparing the diff or body before
finishing.
