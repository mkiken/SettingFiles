---
name: external-tools
description: Use when evaluating, adopting, replacing, or removing an external tool in this repository — comparing CLIs, plugins, packages, or editor extensions; migrating away from one; or running an external installer (herdr integration install, npx skills add) in a disposable target.
---

# External Tools

## Evaluating External Tools

When comparing or selecting an external tool to adopt here (CLI, plugin, package, editor extension), check each candidate's maintenance activity and recent third-party assessment before recommending one, and report the dates you found:

- Last commit and last release date, open issue count, archived status — from the primary source (the repo's API or release page), not a summary article.
- Never treat cumulative popularity (stars, download counts) as evidence of current health; it measures accumulated history, not whether the project still works. State star counts as popularity only.
- Note when a candidate is young — repository age under 12 months, a `0.x` version, or fewer than roughly 100 commits — as a maintenance risk to surface, not a disqualifier.
- Prefer secondary sources published within the last 12 months and give their date; for older ones, state the age and discount accordingly. When a source's author also authored a compared candidate, say so and discount accordingly.

## Removing External Tools

When removing or replacing a tool whose configuration was installed outside this repository (browser extension styles, GUI app preferences, OS-level settings), enumerate those external copies in the plan and state whether each needs manual removal by the user. Deleting the repository source or its setup instructions does not deactivate an already-installed copy. Migrating from mdts to mdv hit exactly this: `mdts-plans.user.css` stayed active in the Stylus extension and, being scoped to `domain("localhost")` rather than a port, kept restyling mdv until it was removed by hand.

## Running External Installers

Before running an external installer (e.g. `herdr integration install`, `npx skills add`) in a disposable target, identify and baseline its known shared or global state roots; a temporary destination alone does not prove isolation. Compare those roots afterward and clean up only artifacts attributable to the run.
