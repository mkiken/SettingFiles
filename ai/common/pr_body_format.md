### PR Body Format

If `.github/PULL_REQUEST_TEMPLATE.md` exists in the repository root, use its structure as the base and fill each section in the same style as the default sections below (short overview first, structured bullets for implementation details). Otherwise use:

````markdown
## Summary

- 1–3 sentences: what this PR changes and why, at a glance.

## 実装内容

- One top-level bullet per logical change group (**bold** short title).
  - Nested bullets listing the related files as `path`: what changed.

## Review Focus Points

特になし

<!-- レビュー観点はPR作成者が記入 -->

## Breaking Changes

- Breaking changes or migration requirements; if none: "なし"

## Additional Notes

- Reviewer-useful background (e.g. why this approach was chosen); omit this section when empty.
````

Rules:

- Describe the final state at HEAD: never reverted changes, overwritten intermediate states, or trial-and-error.
- Group by logical change; no separate file-by-file section — file details live in 実装内容 as nested bullets. Do not include line counts like +X/-Y.
- Keep Summary short; 実装内容 carries the structure. Describe each change group by its intent and effect; add a nested file bullet only where a reviewer needs that file called out, never one bullet per changed file.
- Be concise, no filler; produce raw markdown directly usable as the PR body.
