# User Confirmation

When asking for confirmation, clarification, or any question requiring a user response, prefer the `request_user_input` tool over plain text output.

Plain text questions end the current turn and trigger the Stop hook, sending a "finished" notification indistinguishable from task completion. `request_user_input` keeps the turn active and avoids the false completion notification.

Note: `request_user_input` is unavailable in some modes (e.g., `codex exec` non-interactive runs). In those cases, fall back to a concise plain text question.
