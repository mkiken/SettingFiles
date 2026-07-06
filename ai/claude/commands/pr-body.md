---
allowed-tools: Bash(gh:*), Bash(diff:*), Bash(tr:*), Bash(rm:*), Write
description: "Generate comprehensive PR body content using gh command for specified PR number"
argument-hint: [prNumber]
---

## Instructions

- Before generating the body, check if `.github/PULL_REQUEST_TEMPLATE.md` exists in the repository root
  - If it exists, use its structure as the base for the PR body. Fill in each section with the generated content.
  - If it does not exist, use the default section format defined below.
- First, fetch and review the existing PR body using `gh pr view $ARGUMENTS --json body`
  - If the existing body contains meaningful information (not just template text), preserve and incorporate it
  - Treat manually written TODOs, FIXME notes, free-form notes, incomplete checklists, HTML comments, review requests, and useful background context as meaningful information
  - Do not delete manually written existing content just because it is outside the generated section structure. Keep it in the closest matching section, or move it to **Additional Notes** when no better section exists
  - Template-only content (placeholders, empty sections) can be discarded
- Use the gh command to fetch and analyze PR #$ARGUMENTS
  - Generate content suitable for PR body
  - Exclude template sections
- Analyze the full diff and describe the PR based on the **final state (HEAD)**, not intermediate steps
  - Do not mention reverted changes, overwritten intermediate states, or trial-and-error in the history
  - Background information useful to reviewers (why this approach was chosen, alternatives considered) is acceptable
- Include the following sections:
  - **Summary**: Comprehensive overview grouped by logical changes
  - **Files Changed Summary**: File-by-file breakdown with brief descriptions (DO NOT include line counts like +X/-Y)
  - **Review Focus Points**: Check the existing PR body for this section. If the existing body contains non-default content (anything other than "特になし" or empty), preserve the existing content exactly. Only write "特になし" when creating a new PR body or when the existing section is empty/default.
  - **Breaking Changes**: Any breaking changes or migration requirements
  - **Additional Notes**: Any other relevant information for reviewers
- Output **raw markdown format** that can be directly copied to PR body
  - Wrap the PR body output with ``` code blocks

## Confirmation Flow

After generating the PR body content:

1. **Finalize both bodies as files** before showing anything. Use the session scratchpad directory as `<tmpdir>` (fall back to `mktemp -d` if unavailable):
   - Save the existing body with CRLF normalized to LF (GitHub API bodies contain `\r\n`; without normalization the diff shows every line as changed):
     ```bash
     gh pr view $ARGUMENTS --json body --jq .body | tr -d '\r' > <tmpdir>/pr_body_old.md
     ```
   - Write the complete generated body to `<tmpdir>/pr_body_new.md` with the Write tool (LF line endings, exactly one trailing newline)
   - From this point on, `pr_body_new.md` is the single source of truth for display, diff, and apply. Never reconstruct the body text in chat

2. Display the content of `pr_body_new.md` in a code block

3. **Display the machine-generated diff** between existing body and new body:
   - Show section header: "### 既存body → 新bodyの変更差分"
   - Run the diff command and paste its output **verbatim** inside a ```diff code block:
     ```bash
     diff -u <tmpdir>/pr_body_old.md <tmpdir>/pr_body_new.md
     ```
   - Never construct the diff from memory or prediction, and never omit, summarize, or annotate the output. The displayed diff must be exactly what the command printed
   - If existing body is empty/template-only: display "(既存bodyは空またはテンプレートのみのため、全て新規追加)" instead of the diff
   - Before asking for confirmation, inspect the actual diff output and check that manually written TODOs, notes, incomplete checklist items, HTML comments, review requests, and background context from the existing body were not removed. If any were removed, edit `pr_body_new.md` and redo this step

4. Use AskUserQuestion to confirm: "このPR bodyをPR #$ARGUMENTS に反映しますか？"
   - Options: "はい、反映する" / "いいえ、表示のみ"

5. If user confirms:
   - Apply the exact file that was diffed (do not rebuild the body via heredoc or chat text):
     ```bash
     gh pr edit $ARGUMENTS --body-file <tmpdir>/pr_body_new.md
     ```
   - If the user requested changes after the diff was shown, edit `pr_body_new.md` and restart from the diff display step instead of applying, so the displayed diff and the applied content never diverge
   - Verify the applied body matches the file exactly:
     ```bash
     gh pr view $ARGUMENTS --json body --jq .body | tr -d '\r' | diff - <tmpdir>/pr_body_new.md
     ```
     Expect empty output (a trailing-newline-only difference is acceptable). If anything else differs, re-apply and re-verify
   - Show success message with PR URL
   - Display: "必要に応じて **Review Focus Points** を確認・編集してください"

6. If user declines:
   - End process (user can manually copy the displayed content)

7. Delete the temporary files (`pr_body_old.md`, `pr_body_new.md`) before finishing
