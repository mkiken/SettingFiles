# Prompt Shortening Guide

Procedure for "shorten a prompt without changing meaning or behavior" tasks.

## Must keep verbatim (behavior-defining content)

- Trigger surfaces: skill/command `description`, trigger keywords, argument hints
- Output formats: required headings, response structure, language directives
- Command and API invocations: exact `gh`/shell command lists, code blocks
- Operational steps: IDs, ordering, sorting keys, branching conditions, thresholds

## Condense (prose only)

- Merge bullets that restate the same rule from different angles
- Replace narrative phrasing ("For X, always do Y before Z") with compact
  conditional lists, keeping every operative element
- Drop connective filler; keep each rule self-contained and unambiguous
- Generator-injected boilerplate (e.g. GENERATED-file notices) also loads
  into runtime context; shorten the string inside the generator script,
  never the generated output itself

## Workflow

1. Identify which files are runtime-loaded sources vs generated outputs
   (see CLAUDE.md); edit sources only, never generated files.
2. Record before-size with `wc -w -c` on every affected file.
3. Condense prose per the rules above.
4. Regenerate every affected output with its matching generator when a
   source changed (`mac/initialization/ai/codex.sh` for concatenated
   SKILL.md files, `generate_pr_reviewer_agents` in `mac/scripts/common.sh`
   for reviewer agents — see CLAUDE.md); verify with `git diff` that
   generated diffs derive only from edited sources.
5. Self-review: list the operative elements of the original and confirm
   each survives in the shortened version.
6. Report before/after `wc -w` numbers.

## Estimating reduction

Use only the prose portion as the denominator. Files dominated by
behavior-defining content (command lists, output formats) yield small
totals — 10–20% is typical there; do not promise 40% from file size alone.
