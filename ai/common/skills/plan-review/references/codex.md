# Codex Plan Review

The always-on prompt has already established that both review gates hold.
First output the complete decision-complete plan exactly as it would appear
inside `<proposed_plan>`, without the protocol tags. Do not substitute a
summary or partial update.

Only after the full preview is visible, present this plain-text Markdown
ordered list. Do not call `request_user_input`: four authored options exceed
its runtime limit. A number-only reply selects the corresponding visible item.

1. Both: open the browser and also run the deep-dive.
2. Deep-dive only: run grilling then dig without opening the browser.
3. Open the browser now, decide on the deep-dive after reading.
4. Neither.

The deep-dive is one fixed pair. Never offer grilling and dig separately.
When selected, complete grilling until its frontier is empty and the user
confirms shared understanding; only then run dig on grilling's resulting plan.

For option 1, open the browser first, then run the pair. For option 3, open the
browser, wait for the user to finish reading, then ask whether to run the whole
pair or proceed. For option 4, output the previewed plan unchanged inside the
final `<proposed_plan>` block.

After dig changes the plan, repeat the complete preview and this choice flow
once, after dig and not between the two stages. Finalize only the revised plan.

Codex has no `~/.codex/plans`. For browser review, write the plan to a
session-owned scratchpad directory, then read `references/browser.md` and use
its small-directory flow. Never use Claude's port 4649 or `~/.claude/plans`.
The scratchpad is a temporary artifact and must be cleaned up after review.
