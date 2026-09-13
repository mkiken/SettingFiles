---
name: plan-review
description: Review a completed plan when repository instructions require browser rendering or a grilling-and-dig deep-dive.
---

# Plan Review

Use only after the always-on prompt says the current plan meets its review
criteria. Preserve that prompt's gate result; do not broaden it here.

Read exactly one platform workflow:

- Codex: `references/codex.md`
- Claude: `references/claude.md`
- Gemini: `references/gemini.md`

Read `references/browser.md` only when the user chooses browser review, or when
the platform workflow explicitly requires opening the plan. If any required
reference is missing or unreadable, report its path and stop before opening a
browser or starting the deep-dive.

Keep the plan's completion criteria, authorization boundaries, and accepted
decisions intact. Browser review does not approve implementation or any
external action.
