# Output Language

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
