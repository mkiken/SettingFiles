# Output Language

# Detailed Explanations

When the user explicitly asks for a detailed explanation—such as more detail, clarity, background, rationale, or step-by-step instructions—suspend genshijin style for that response. Use ordinary Japanese prose and provide enough structure and context to make the explanation easy to follow. Resume genshijin style on the next response unless the user repeats the request or explicitly disables genshijin.

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

When a skill defines authored options, pass each label to the tool exactly once and preserve the authored option count. Do not count the client's auto-provided free-form `Other` as an authored option.

Ask in plain text only when `request_user_input` is unavailable for the current question or a meaningful answer requires free-form text that would be unnatural as choices.

For a plain-text fallback with choices, use a Markdown ordered list starting from `1.` and treat a number-only reply as selecting the corresponding visible option.

When finalizing a plan in Plan Mode or starting implementation of an accepted plan, load the `plan-model-handoff` skill and follow it before emitting the final plan or causing the first implementation side effect.

# Plan Approval Detail

For a non-trivial `<proposed_plan>`, provide a reviewable implementation explanation, not a generic checklist. For every implementation group, state the target behavior, concrete mechanism, material files or interfaces, failure or edge behavior, and test condition with expected outcome. Preserve accepted user choices in Assumptions. Keep the plan concise, but never omit a material decision merely to shorten it.

# Plan Review Deep-Dive (dig)

This section's skip criterion governs both the `dig` skill offer and the Plan Review Presentation browser offer — the shared file's own line-count/format criteria do not apply here; use this criterion for both instead. Its port-selection and launch mechanics still apply when the browser is actually opened.

When finalizing a plan in Plan Mode, offer both — but first skip both for trivially mechanical plans: renames, bulk replacements, reverts, single-file fixes with no design decision, or plans whose every task is a stated verbatim edit. For those, skip straight to the final `<proposed_plan>` with no dialog.

Otherwise, offer a single choice via `request_user_input` (or its plain-text fallback) with exactly three options in this order:

1. Both: open the browser and also run dig.
2. Open the browser now, decide on dig after reading.
3. Neither.

If option 1 is chosen, open the browser first, then load the `dig` skill.

Codex has no `~/.codex/plans` directory — the plan exists only as this turn's `<proposed_plan>` content, not a file on disk. When the browser is accepted, write the current plan text to a scratchpad file first, then treat it as the SDD case in Plan Review Presentation: find a free port from 8610, launch `mdts -p <found-port> --no-open <scratchpad-dir>`, and stop that instance once the review finishes. Do not reuse the fixed port 8600 / `~/.claude/plans` mount — that path is Claude-only and does not exist here. The written scratchpad file is a session temp; Temp File Cleanup applies.
