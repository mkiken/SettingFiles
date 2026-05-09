# User Confirmation

When asking for confirmation, clarification, or any question requiring a user response, prefer the `request_user_input` tool over plain text output when it is available.

Plain text questions end the current turn and trigger the Stop hook, sending a "finished" notification indistinguishable from task completion. `request_user_input` keeps the turn active and avoids the false completion notification.

Note: This configuration enables `default_mode_request_user_input`, so try `request_user_input` first when the tool is listed, including in Default mode. If the tool still returns unavailable (e.g., in `codex exec` non-interactive runs), fall back to a concise plain text question and state that the tool was unavailable.
