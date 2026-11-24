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
