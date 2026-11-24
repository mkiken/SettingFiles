---
name: pr-body
description: Draft or update a GitHub Pull Request body. Use when the user asks for a PR description, including `$pr-body`.
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
cat .github/PULL_REQUEST_TEMPLATE.md 2>/dev/null || printf '%s\n' 'NO_TEMPLATE'
gh pr diff <PR_NUMBER>
gh pr diff <PR_NUMBER> --name-only
```

## Drafting Rules

- Generate the body per the **PR Body Format** section below; it is displayed in the Confirmation Flow.
- Preserve meaningful existing-body content (manually written TODOs, FIXME notes, free-form notes, incomplete checklists, HTML comments, review requests, useful background) even when it falls outside the generated structure — keep it in the closest matching section, or in **Additional Notes** when none fits. Template-only content (placeholders, empty sections) can be discarded.
- If the diff is too large to read at once, redirect it to a file under the session temp/scratchpad directory (the same `<tmpdir>` used in the Confirmation Flow) and read it incrementally.
- **Review Focus Points** — overrides the PR Body Format default: if the existing body has non-default content here (anything other than "特になし" or empty), preserve it exactly; for a new PR body or an empty/default section, fill it as defined by the Review Focus Points section of the PR Body Format.

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
     git --no-pager diff --no-index --color=always <tmpdir>/pr_body_old.md <tmpdir>/pr_body_new.md | /bin/cat || true
     git --no-pager diff --no-index --no-color <tmpdir>/pr_body_old.md <tmpdir>/pr_body_new.md | /bin/cat || true
     ```
   - Keep `| /bin/cat`: without it the rtk PreToolUse hook rewrites the command to `rtk git diff`, which drops all output when git exits 1 (a difference exists)
   - The first (colored) run is for on-screen readability in the tool output panel — deletions render red, additions green. Never paste its output into the fenced block below; it carries ANSI escapes
   - Paste the second (`--no-color`) command's output **verbatim** — never construct it from memory, and never omit, summarize, or annotate it — inside a fenced code block with the `diff` language tag:
   - The fence must be longer than any backtick run inside the output: at least four backticks (````diff), since PR bodies usually contain ``` blocks; five if the output contains a four-backtick run
   - If existing body is empty/template-only: display "(既存bodyは空またはテンプレートのみのため、全て新規追加)" instead of the diff, and skip the change summary below
   - Below the diff block, show "### 変更点の概要" followed by a bullet list that makes the raw diff easy to grasp:
     - Start each bullet with 追加 / 削除 / 変更 / 移動, then name the section and the change in content (never a contentless label like "文言修正")
     - Derive it from the pasted `--no-color` diff, not from memory. Every hunk must map to at least one bullet — omit nothing; whitespace/line-break-only changes may share one bullet but are still listed
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

### PR Body Format

If `.github/PULL_REQUEST_TEMPLATE.md` exists in the repository root, use its structure as the base and fill each section in the same style as the default sections below (conclusion first, structured bullets for implementation details). Otherwise use:

````markdown
## Summary

- The conclusion in 3 lines or fewer: what this PR adopts and why.

## 実装内容

- One top-level bullet per logical change group (**bold** short title).
  - Nested bullets listing the related files as `path`: what changed.

## 検討した代替案

| 案 | 却下理由 |
|---|---|
| Rejected option | One line on why it was rejected |

## Review Focus Points

特になし

<!-- レビュー観点はPR作成者が記入 -->

## テスト

- Verification commands actually run and their results. If not run, say so and why.

## リスクと戻し方

- Blast radius, and how to roll back (plain `git revert`, or manual config/data steps).

## Breaking Changes

- Breaking changes or migration requirements.

## Additional Notes

- Reviewer-useful background (e.g. a constraint that is not visible in the diff).
````

Rules:

- Describe the final state at HEAD: never reverted changes, overwritten intermediate states, or trial-and-error.
- Group by logical change; no separate file-by-file section — file details live in 実装内容 as nested bullets. Do not include line counts like +X/-Y.
- Lead with the conclusion. Summary states what was adopted and why in 3 lines or fewer; never replay the evaluation process and leave the conclusion for the end. 実装内容 carries the structure. Describe each change group by its intent and effect; add a nested file bullet only where a reviewer needs that file called out, never one bullet per changed file.
- When covering alternatives, use the two-column table (案 / 却下理由) — never write merits and demerits out as prose, and never give an option the requirements rule out from the start the same weight as the adopted one.
- Do not enumerate out-of-scope generalities or possible future extensions. Note only a deliberately excluded scope that a reviewer would otherwise misread, as a single line in Summary.
- Omit any section that does not apply — 検討した代替案 when no alternative was worth weighing, Breaking Changes when there are none, Additional Notes when empty. Do not fill a section with "なし" or a placeholder. Review Focus Points is the exception: always keep it; fill it per the Review Focus Points section below.
- For every section, ask "can a reviewer understand the decision without it?" — if yes, drop it. Write boilerplate sections such as terminology, background, or purpose only when a reviewer cannot judge the change without them.
- Be concise, no filler; produce raw markdown directly usable as the PR body.

### Task-Based Pull Requests

A PR is task-based when the request or conversation explicitly references a task in a task-management tool (issue, ticket, task) by URL or ID. Never infer it from a branch name.

- Body: add one line at the end of Summary (or the top of the body if the template has no Summary): `- 関連タスク: [<task title>](<task URL>)`, comma-separated for several tasks. It does not count toward Summary's 3-line limit. Fetch an unknown title with an available tool; ask the user if it cannot be fetched.
- After the PR is created and verified, check each task's current status and available transitions using the task-management tool. If a transition suitable for the PR review stage is identifiable, propose its actual name with the current status (e.g. `対応中 → レビュー待ち`). If status or transitions are absent or unavailable, the task is already at the candidate, or no suitable transition is identifiable, continue with the comment confirmation alone.
- Present the comment draft and any status change together, and ask the user per task for separate approval of each operation. The comment holds the PR title and URL as a link in the tool's link syntax. Execute only approved operations; verify each result by independently re-fetching it. If commenting is unavailable, report that and show the text for pasting; if status updates are unavailable, report the proposed destination for manual change. Report each operation's failure separately.

### Review Focus Points

The Review Focus Points section holds only design decisions the user made in this conversation (answers to confirmation questions, plan discussion, direction corrections). Never write conclusions the AI reached alone.

- Before writing it, draft candidates — one bullet per decision: the decision, the option chosen and why, and what the reviewer should check — and ask through the platform's confirmation mechanism with exactly: `記載する` / `修正する` / `記載しない`. Write only the confirmed text; on `修正する`, apply the correction and ask again.
- With no candidates, or on `記載しない`, write the template default (`特になし`) without asking.
- Never overwrite existing non-default content in that section.
