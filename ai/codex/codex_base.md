# Output Language

Respond to the user in Japanese by default.

This applies to normal replies, Plan Mode progress updates, clarification or confirmation questions, and all human-readable content inside `<proposed_plan>` blocks.

Keep required protocol tags and machine-readable identifiers unchanged. For example, use the literal `<proposed_plan>` and `</proposed_plan>` tags exactly as specified.

Use English only when the user explicitly requests it, when preserving source text or API names, or when writing code, commands, identifiers, commit messages, documentation, or user-facing strings that should remain English for the target context.

# User Confirmation

Do not use the `request_user_input` tool in Codex.

Ask confirmation, clarification, cleanup, commit, and PR workflow questions in plain text as the final response.

When presenting plain-text choices, format them as a Markdown ordered list starting from `1.`. Treat a number-only reply as selecting the corresponding visible option. If shared instructions or skill examples show unordered choice bullets, convert them to ordered lists when presenting them. `Use exactly these options` in a skill means keeping the option labels and count, while still displaying them as an ordered list.

Reason: `request_user_input` waits do not emit Codex hook events, so Stop/notification hooks do not run and tmux can remain in the ongoing state.

This rule takes precedence over shared instructions or skill instructions that mention Ask-style tools.
