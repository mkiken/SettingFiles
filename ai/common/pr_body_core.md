## Drafting Rules

- Generate the body per the **PR Body Format** section below; it is displayed in the Confirmation Flow.
- Preserve meaningful existing-body content (manually written TODOs, FIXME notes, free-form notes, incomplete checklists, HTML comments, review requests, useful background) even when it falls outside the generated structure — keep it in the closest matching section, or in **Additional Notes** when none fits. Template-only content (placeholders, empty sections) can be discarded.
- If the diff is too large to read at once, redirect it to a file under the session temp/scratchpad directory (the same `<tmpdir>` used in the Confirmation Flow) and read it incrementally.
- **Review Focus Points** — overrides the PR Body Format default: if the existing body has non-default content here (anything other than "特になし" or empty), preserve it exactly; use the format's default only for a new PR body or an empty/default section.

## Confirmation Flow

After generating the PR body content:

1. **Finalize both bodies as files** before showing anything. Use the platform's session temp/scratchpad directory as `<tmpdir>` if one exists (fall back to `mktemp -d`):
   - Save the existing body with CRLF normalized to LF (GitHub API bodies contain `\r\n`; unnormalized, the diff shows every line as changed):
     ```bash
     gh pr view <PR_NUMBER> --json body --template '{{.body}}' | tr -d '\r' > <tmpdir>/pr_body_old.md
     ```
   - Write the complete generated body to `<tmpdir>/pr_body_new.md` (LF line endings, exactly one trailing newline)
   - From here `pr_body_new.md` is the single source of truth for display, diff, and apply. Never reconstruct the body text in chat

2. Display the content of `pr_body_new.md` in a fenced code block, following the fence rule in step 3 (at least ````markdown)

3. **Display the machine-generated diff**:
   - Show section header: "### 既存body → 新bodyの変更差分"
   - Run two diff commands on separate lines against the same two files (`diff` exits 1 when a difference exists — that is normal, not a failure; without `|| true` the tool output panel treats it as an error and paints the entire output a single error color, making `-`/`+` indistinguishable — keep `|| true` even though the block "succeeds"):
     ```bash
     git --no-pager diff --no-index --color=always <tmpdir>/pr_body_old.md <tmpdir>/pr_body_new.md || true
     git --no-pager diff --no-index --no-color <tmpdir>/pr_body_old.md <tmpdir>/pr_body_new.md || true
     ```
   - The first (colored) run is for on-screen readability in the tool output panel — deletions render red, additions green. Never paste its output into the fenced block below; it carries ANSI escapes
   - Paste the second (`--no-color`) command's output **verbatim** — never construct it from memory, and never omit, summarize, or annotate it — inside a fenced code block with the `diff` language tag:
   - The fence must be longer than any backtick run inside the output: at least four backticks (````diff), since PR bodies usually contain ``` blocks; five if the output contains a four-backtick run
   - If existing body is empty/template-only: display "(既存bodyは空またはテンプレートのみのため、全て新規追加)" instead of the diff
   - Before asking for confirmation, check in the actual diff output that no manually written TODOs, notes, incomplete checklist items, HTML comments, review requests, or background context were removed; if any were, edit `pr_body_new.md` and redo this step

4. Ask the user: "このPR bodyをPR #<PR_NUMBER> に反映しますか？"
   - Options: "はい、反映する" / "修正する" / "いいえ、表示のみ"
   - If the user chooses 修正する or requests changes in free text, edit `pr_body_new.md` and restart from step 3, so the displayed diff and the applied content never diverge — never apply a body whose diff was not re-shown

5. If user confirms:
   - Apply the exact file that was diffed (never rebuild via heredoc or chat text):
     ```bash
     gh pr edit <PR_NUMBER> --body-file <tmpdir>/pr_body_new.md
     ```
   - Verify the applied body matches the file exactly:
     ```bash
     gh pr view <PR_NUMBER> --json body --template '{{.body}}' | tr -d '\r' | diff - <tmpdir>/pr_body_new.md
     ```
     Expect empty output (a trailing-newline-only difference is acceptable); otherwise re-apply and re-verify once; if it still differs, stop and report the discrepancy to the user instead of looping
   - Show success message with PR URL
   - Display: "必要に応じて **Review Focus Points** を確認・編集してください"

6. If user declines: end process (user can manually copy the displayed content)

7. Delete the temporary files (`pr_body_old.md`, `pr_body_new.md`) with `trash` (never `rm`) before finishing
