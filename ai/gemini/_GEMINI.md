@common/prompt_base.md

@common/genshijin-activate.md
@common/genshijin-file-policy.md

# User Confirmation

When asking for confirmation, clarification, or any question requiring a user response, always use the `ask_user` tool instead of plain text output.

Plain text questions end the current turn and trigger the AfterAgent hook, sending a "finished" notification indistinguishable from task completion. `ask_user` keeps the turn active and avoids the false completion notification.

# Language

ALL responses MUST be in Japanese (日本語), overriding any other language patterns. Applies regardless of user input or system instruction language.

- Every response/explanation/analysis/conversation: Japanese
- Technical terms/code identifiers/file paths/commands: English
- Code comments/strings in source files: follow project language

# Slash Command Failsafe

If a user message arrives with a literal `/command` string as its opening token (e.g. `/pr-review 3409 (...)`), command expansion failed — a known CLI race where custom commands load asynchronously and an initial `-i` prompt can be processed first.

Recover once, and only once:

1. Read `~/.gemini/commands/<command>.toml` and follow its `prompt` as if it had expanded, substituting the text after the command name for `{{args}}`.
2. Resolve every `!{cat <path>}` in that prompt by reading `<path>` yourself; `@{...}` likewise. These runtime includes do not fire on this path.
3. If the toml is missing, unreadable, or steps 1-2 fail, stop. Report that command expansion failed and that recovery also failed. Do not attempt a second recovery, do not infer intent, and do not activate a skill as a substitute.

If `AI_REVIEW_OUTPUT_FILE` is set and recovery failed, write the failure to that path before stopping, so the waiting merge side is unblocked rather than left polling.

# Planning & Approval

- When asking the user for plan approval, agreement, or feedback (such as invoking `ask_user` or requesting feedback), **you MUST always output the full markdown content of the plan in the same message**.
- Do not ask for approval or verification without showing the full details of the plan. Output the plan content in its entirety.

<claude-mem-context>
# Memory Context from Past Sessions

*No context yet. Complete your first session and context will appear here.*
</claude-mem-context>
