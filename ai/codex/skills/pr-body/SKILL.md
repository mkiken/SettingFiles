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

If no PR is found, ask the user for a PR number in plain text.

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
- Preserve meaningful information from the existing PR body. This includes
  manually written TODOs, FIXME notes, free-form notes, incomplete checklists,
  HTML comments, review requests, and useful background context.
- Treat placeholder-only or template-only content as disposable.
- Do not delete manually written existing content just because it is outside the
  generated section structure. Keep it in the closest matching section, or move
  it to `Additional Notes` when no better section exists.
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

First, finalize both bodies as files. Create a temp directory with `mktemp -d`
and use it as `<TMPDIR>`:

```bash
gh pr view <PR_NUMBER> --json body --jq .body | tr -d '\r' > <TMPDIR>/pr_body_old.md
```

CRLF normalization (`tr -d '\r'`) is required: GitHub API bodies contain
`\r\n`, and without it the diff shows every line as changed.

Write the complete generated body to `<TMPDIR>/pr_body_new.md` (LF line
endings, exactly one trailing newline). From this point on,
`pr_body_new.md` is the single source of truth for display, diff, and apply.
Never reconstruct the body text in chat.

Display the content of `pr_body_new.md` in a markdown code block.

Then display the machine-generated diff from the existing body to the
generated body. Run:

```bash
diff -u <TMPDIR>/pr_body_old.md <TMPDIR>/pr_body_new.md
```

and paste its output verbatim under the header, inside a fenced code block
with the `diff` language tag, so additions (`+`) render green and deletions
(`-`) render red:

`````markdown
### 既存body → 新bodyの変更差分

````diff
<verbatim diff command output>
````
`````

The code fence must be longer than any backtick run inside the diff output —
use at least four backticks (````diff) as shown above. PR bodies usually
contain ``` code blocks, and a three-backtick fence would be closed early by
them, breaking the color highlighting. If the output contains a four-backtick
run, use five.

Never construct the diff from memory or prediction, and never omit,
summarize, or annotate the output. The displayed diff must be exactly what
the command printed.

If the existing body is empty or template-only, display this instead of the
diff:

```text
(既存bodyは空またはテンプレートのみのため、全て新規追加)
```

Before asking for confirmation, inspect the actual diff output and confirm
that manually written TODOs, notes, incomplete checklist items, HTML
comments, review requests, and background context from the existing body were
not removed. If any were removed, edit `pr_body_new.md` and redo the diff
display step.

Ask in plain text:

```text
このPR bodyをPR #<PR_NUMBER> に反映しますか？
```

Use exactly these options:

1. `はい、反映する`
2. `いいえ、表示のみ`

## Apply

Only apply after the user chooses `はい、反映する`.

Apply the exact file that was diffed. Do not rebuild the body via heredoc or
chat text:

```bash
gh pr edit <PR_NUMBER> --body-file <TMPDIR>/pr_body_new.md
```

If the user requested changes after the diff was shown, edit
`pr_body_new.md` and restart from the diff display step instead of applying,
so the displayed diff and the applied content never diverge.

Verify the applied body matches the file exactly:

```bash
gh pr view <PR_NUMBER> --json body --jq .body | tr -d '\r' | diff - <TMPDIR>/pr_body_new.md
```

Expect empty output (a trailing-newline-only difference is acceptable). If
anything else differs, re-apply and re-verify.

After success, show the PR URL and:

```text
必要に応じて **Review Focus Points** を確認・編集してください
```

If the user declines, make no GitHub changes.

## Cleanup

Delete any temporary files created while preparing the diff or body before
finishing.
