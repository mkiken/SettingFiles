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

If a user message consists solely of a raw slash command (e.g. `/pr-review 3244`), command expansion failed (known CLI race: custom commands load asynchronously and an initial `-i` prompt can be processed first). Do not infer intent, activate skills, or execute an alternative — reply that command expansion failed and ask the user to re-run the command in the interactive UI, then stop.

# Planning & Approval

- When asking the user for plan approval, agreement, or feedback (such as invoking `ask_user` or requesting feedback), **you MUST always output the full markdown content of the plan in the same message**.
- Do not ask for approval or verification without showing the full details of the plan. Output the plan content in its entirety.

<claude-mem-context>
# Memory Context from Past Sessions

*No context yet. Complete your first session and context will appear here.*
</claude-mem-context>
