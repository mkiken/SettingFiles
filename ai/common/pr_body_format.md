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
- Omit any section that does not apply — 検討した代替案 when no alternative was worth weighing, Breaking Changes when there are none, Additional Notes when empty. Do not fill a section with "なし" or a placeholder. Review Focus Points is the exception: always keep it, since the author fills it in after the fact.
- For every section, ask "can a reviewer understand the decision without it?" — if yes, drop it. Write boilerplate sections such as terminology, background, or purpose only when a reviewer cannot judge the change without them.
- Be concise, no filler; produce raw markdown directly usable as the PR body.
