# Output Language

# Default Response Style

Use the installed `caveman` skill at `full` intensity for every conversational response. Load its current `SKILL.md` instead of duplicating its rules here. `/caveman lite|full|ultra|wenyan-lite|wenyan-full|wenyan-ultra` changes intensity for the current session; `/caveman off` or `normal mode` disables it. Persisted files, code, comments, commits, documentation, and third-party messages follow their existing or repository-required style.

# RTK

When `rtk gain` succeeds, prefix supported high-output shell commands with `rtk`. Use the raw command only when full output is required.

# Herdr Tab Labels

For the first substantive user task in a conversation, use the `herdr-tab-label` skill before other task actions. If the active collaboration mode forbids its UI side effect, defer it to the first implementation turn. Do not use it again for later ordinary tasks in the same conversation; workflows such as `worktree-task` may explicitly reuse it.

Respond to the user in Japanese by default.

This applies to normal replies, Plan Mode progress updates, clarification or confirmation questions, and all human-readable content inside `<proposed_plan>` blocks.

Keep required protocol tags and machine-readable identifiers unchanged. For example, use the literal `<proposed_plan>` and `</proposed_plan>` tags exactly as specified.

Use English only when the user explicitly requests it, when preserving source text or API names, or when writing code, commands, identifiers, commit messages, documentation, or user-facing strings that should remain English for the target context.

# OpenAI Docs Manual Cache

When the `openai-docs` skill runs `fetch-codex-manual.mjs`, invoke it through the host shell, not `context-mode` or another ephemeral analysis sandbox. The returned manual and outline must remain readable by later tool calls; pass a host-visible `--cache-dir` when command routing would otherwise isolate the filesystem.

# User Confirmation

When `request_user_input` is available, use it for confirmation, clarification, cleanup, commit, and PR workflow questions that can be expressed as two or three meaningful choices. Put the recommended choice first.

If `request_user_input` returns no selected answer (for example, an empty `answers` object), treat the UI as unavailable for that question: present the same authored options once as a plain-text ordered list and wait. Do not call `request_user_input` again for that question.

When a skill defines authored options, pass each label to the tool exactly once and preserve the authored option count. Do not count the client's auto-provided free-form `Other` as an authored option.

Ask in plain text only when `request_user_input` is unavailable for the current question or a meaningful answer requires free-form text that would be unnatural as choices.

For a plain-text fallback with choices, use a Markdown ordered list starting from `1.` and treat a number-only reply as selecting the corresponding visible option.

When beginning execution of an accepted plan, load the `plan-model-handoff` skill and follow it before starting any task-specific workflow or repository operation for that plan.

# Plan Approval Detail

For a non-trivial `<proposed_plan>`, provide a reviewable implementation explanation, not a generic checklist. For every implementation group, state the target behavior, concrete mechanism, material files or interfaces, failure or edge behavior, and test condition with expected outcome. Preserve accepted user choices in Assumptions. Keep the plan concise, but never omit a material decision merely to shorten it.

# Plan Review Deep-Dive (dig)

This section's skip criterion governs both the `dig` skill offer and the Plan Review Presentation browser offer — the shared file's own line-count/format criteria do not apply here; use this criterion for both instead. Its port-selection and launch mechanics still apply when the browser is actually opened.

When finalizing a plan in Plan Mode, first skip both offers for trivially mechanical plans: renames, bulk replacements, reverts, single-file fixes with no design decision, or plans whose every task is a stated verbatim edit. For those, skip straight to the final `<proposed_plan>` with no dialog.

Otherwise, first output a terminal review preview containing the complete decision-complete plan exactly as it would appear inside `<proposed_plan>`, but without the protocol tags. Do not replace it with a summary or partial update. Only after the full preview is visible, present this question as a plain-text Markdown ordered list; never call `request_user_input` for it because its four authored options exceed the runtime limit. Treat a number-only reply as selecting the corresponding option. Preserve exactly this order:

1. Both: open the browser and also run dig.
2. dig only: run dig without opening the browser.
3. Open the browser now, decide on dig after reading.
4. Neither.

If option 1 is chosen, open the browser first, then load the `dig` skill.

If option 2 is chosen, load the dig skill without launching mdts.

If option 4 is chosen, output the previewed plan unchanged inside the final `<proposed_plan>` block. After any dig round changes the candidate plan, repeat the full terminal preview and review-choice flow with the revised plan before finalizing it.

Codex has no `~/.codex/plans` directory — the plan exists only as this turn's `<proposed_plan>` content, not a file on disk. When the browser is accepted, write the current plan text to a scratchpad file first, then treat it as the SDD case in Plan Review Presentation: find a free port from 8610, launch `mdts -p <found-port> --no-open <scratchpad-dir>`, and stop that instance once the review finishes. Do not reuse the fixed port 8600 / `~/.claude/plans` mount — that path is Claude-only and does not exist here. The written scratchpad file is a session temp; Temp File Cleanup applies.
