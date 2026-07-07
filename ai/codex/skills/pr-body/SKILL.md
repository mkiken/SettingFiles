---
name: pr-body
description: >
  Generate and optionally update a GitHub Pull Request body using gh.
  Use this skill when the user asks Codex to create, regenerate, rewrite,
  or apply a PR description/body, says "PR body", "PR本文", "PR説明を作って",
  or invokes `$pr-body`. Accepts an optional PR number; if omitted, detect
  the PR for the current branch.
---

## Inputs

Extract the PR number from the user's message; if absent, run:

```bash
gh pr view --json number --jq .number
```

If no PR number is found, ask the user for it. In the rules below,
`<PR_NUMBER>` refers to this PR number.

## Gather Context

Run these commands before drafting:

```bash
gh pr view <PR_NUMBER> --json number,url,title,body,author,headRefName,baseRefName
test -f .github/PULL_REQUEST_TEMPLATE.md && sed -n '1,240p' .github/PULL_REQUEST_TEMPLATE.md || printf '%s\n' 'NO_TEMPLATE'
gh pr diff <PR_NUMBER>
gh pr diff <PR_NUMBER> --name-only
```

## Drafting Rules

- If `.github/PULL_REQUEST_TEMPLATE.md` exists in the repository root, use its structure as the base and fill each section with the generated content; otherwise use the default sections below.
- Preserve meaningful existing-body content (manually written TODOs, FIXME notes, free-form notes, incomplete checklists, HTML comments, review requests, useful background) even when it falls outside the generated structure — keep it in the closest matching section, or in **Additional Notes** when none fits. Template-only content (placeholders, empty sections) can be discarded.
- Analyze the full diff and describe the **final state (HEAD)**: do not mention reverted changes, overwritten intermediate states, or trial-and-error. Reviewer-useful background (why this approach was chosen, alternatives considered) is acceptable.
- If the diff is too large to read at once, redirect it to a file and read it incrementally.
- Default sections:
  - **Summary**: Comprehensive overview grouped by logical changes
  - **Files Changed Summary**: File-by-file breakdown with brief descriptions (DO NOT include line counts like +X/-Y)
  - **Review Focus Points**: If the existing body has non-default content here (anything other than "特になし" or empty), preserve it exactly; write "特になし" only for a new PR body or an empty/default section.
  - **Breaking Changes**: Any breaking changes or migration requirements
  - **Additional Notes**: Any other relevant information for reviewers
- Produce the body as raw markdown directly copyable to the PR body; it is displayed in the Confirmation Flow.

## Confirmation Flow

After generating the PR body content:

1. **Finalize both bodies as files** before showing anything. Use the platform's session temp/scratchpad directory as `<tmpdir>` if one exists (fall back to `mktemp -d`):
   - Save the existing body with CRLF normalized to LF (GitHub API bodies contain `\r\n`; unnormalized, the diff shows every line as changed):
     ```bash
     gh pr view <PR_NUMBER> --json body --jq .body | tr -d '\r' > <tmpdir>/pr_body_old.md
     ```
   - Write the complete generated body to `<tmpdir>/pr_body_new.md` (LF line endings, exactly one trailing newline)
   - From here `pr_body_new.md` is the single source of truth for display, diff, and apply. Never reconstruct the body text in chat

2. Display the content of `pr_body_new.md` in a fenced code block; the fence must be longer than any backtick run inside — at least four backticks (````markdown), since PR bodies usually contain ``` blocks

3. **Display the machine-generated diff**:
   - Show section header: "### 既存body → 新bodyの変更差分"
   - Run the diff command and paste its output **verbatim** — never construct it from memory, and never omit, summarize, or annotate it — inside a fenced code block with the `diff` language tag:
     ```bash
     diff -u <tmpdir>/pr_body_old.md <tmpdir>/pr_body_new.md
     ```
   - The fence must be longer than any backtick run inside the output: at least four backticks (````diff), since PR bodies usually contain ``` blocks; five if the output contains a four-backtick run
   - If existing body is empty/template-only: display "(既存bodyは空またはテンプレートのみのため、全て新規追加)" instead of the diff
   - Before asking for confirmation, check in the actual diff output that no manually written TODOs, notes, incomplete checklist items, HTML comments, review requests, or background context were removed; if any were, edit `pr_body_new.md` and redo this step

4. Ask the user: "このPR bodyをPR #<PR_NUMBER> に反映しますか？"
   - Options: "はい、反映する" / "いいえ、表示のみ"

5. If user confirms:
   - Apply the exact file that was diffed (never rebuild via heredoc or chat text):
     ```bash
     gh pr edit <PR_NUMBER> --body-file <tmpdir>/pr_body_new.md
     ```
   - If the user requested changes after the diff was shown, edit `pr_body_new.md` and restart from the diff display step, so the displayed diff and the applied content never diverge
   - Verify the applied body matches the file exactly:
     ```bash
     gh pr view <PR_NUMBER> --json body --jq .body | tr -d '\r' | diff - <tmpdir>/pr_body_new.md
     ```
     Expect empty output (a trailing-newline-only difference is acceptable); otherwise re-apply and re-verify
   - Show success message with PR URL
   - Display: "必要に応じて **Review Focus Points** を確認・編集してください"

6. If user declines: end process (user can manually copy the displayed content)

7. Delete the temporary files (`pr_body_old.md`, `pr_body_new.md`) before finishing
