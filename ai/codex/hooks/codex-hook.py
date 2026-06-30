#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shell" / "tmux"))
from codex_hook_common import analyze_hook_input
from tmux_emoji import EMOJI_PATTERN, EMOJI_ID_CODEX


class HookStatus(Enum):
    COMPLETED = "✅"
    NOTIFICATION = "✋"
    ONGOING = "🤖"


IDENTIFIER = EMOJI_ID_CODEX


def _hook_error_log_path() -> Path:
    override = os.environ.get("CODEX_HOOK_ERROR_LOG")
    if override:
        return Path(override).expanduser()
    return Path(os.environ.get("TMPDIR") or "/tmp") / "codex-hook-error.log"


def log_hook_error(message: str, **fields):
    try:
        log_path = _hook_error_log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        field_text = " ".join(f"{key}={value!r}" for key, value in fields.items())
        line = f"{timestamp} {message}"
        if field_text:
            line = f"{line} {field_text}"
        with log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(line + "\n")
    except Exception:
        pass


def print_visible_hook_error(message: str):
    log_path = _hook_error_log_path()
    print(f"Codex hook error: {message}", file=sys.stderr)
    print(f"Hook error log: {log_path}", file=sys.stderr)


def load_hook_input() -> tuple[dict | None, str | None]:
    raw_input = sys.stdin.read()
    if not raw_input.strip():
        message = "empty hook stdin"
        log_hook_error(message)
        return None, message

    try:
        input_data = json.loads(raw_input)
    except json.JSONDecodeError as exc:
        preview = raw_input[:200].replace("\n", "\\n")
        message = "invalid hook input JSON"
        log_hook_error(
            message,
            input_bytes=len(raw_input.encode("utf-8")),
            error=str(exc),
            preview=preview,
        )
        return None, message

    if not isinstance(input_data, dict):
        message = "hook input JSON is not an object"
        log_hook_error(message, input_type=type(input_data).__name__)
        return None, message

    return input_data, None


def _get_tmux_pane_id() -> str | None:
    """tmuxセッション内の場合のみpane_idを返す。それ以外はNone。
    VSCode等からtmuxを起動した際にTMUX_PANEが継承されるケースを除外するため、
    TERM_PROGRAM=="tmux"も確認する。
    """
    pane_id = os.environ.get("TMUX_PANE")
    if not pane_id:
        return None
    term_program = os.environ.get("TERM_PROGRAM", "")
    if term_program != "tmux":
        return None
    return pane_id


def main() -> int:
    input_data, input_error = load_hook_input()
    if input_data is None:
        print_visible_hook_error(input_error or "failed to read hook input")
        return 1

    hook_event = input_data.get("hook_event_name")

    handlers = {
        "PermissionRequest": handle_permission_request_hook,
        "PostToolUse": handle_post_tool_use_hook,
        "Stop": handle_stop_hook,
        "UserPromptSubmit": handle_user_prompt_submit_hook,
    }

    handler = handlers.get(hook_event)

    if handler:
        try:
            handler(input_data)
        except Exception as exc:
            log_hook_error(
                "hook handler failed",
                hook_event=hook_event,
                session_id=input_data.get("session_id"),
                error=repr(exc),
            )
            print_visible_hook_error("hook handler failed")
            return 1

    return 0


def handle_post_tool_use_hook(_: dict):
    update_tmux_window_name(HookStatus.ONGOING)


def handle_permission_request_hook(_: dict):
    update_tmux_window_name(HookStatus.NOTIFICATION)


def handle_user_prompt_submit_hook(_: dict):
    update_tmux_window_name(HookStatus.ONGOING)


def handle_stop_hook(input_data: dict):
    analysis = analyze_hook_input(input_data)
    if analysis["is_subagent_session"]:
        return

    if analysis["waiting_for_user_response"]:
        update_tmux_window_name(HookStatus.NOTIFICATION)
    else:
        update_tmux_window_name(HookStatus.COMPLETED)


def update_tmux_window_name(status: HookStatus):
    """指定されたステータスでtmuxウィンドウ名を更新"""
    try:
        pane_id = _get_tmux_pane_id()
        if not pane_id:
            return

        result = subprocess.run(
            ["tmux", "display-message", "-p", "-t", pane_id, "#W"],
            capture_output=True,
            text=True,
            check=True,
        )
        current_name = result.stdout.strip()

        result = subprocess.run(
            ["tmux", "display-message", "-p", "-t", pane_id, "#{window_id}"],
            capture_output=True,
            text=True,
            check=True,
        )
        window_id = result.stdout.strip()

        emoji = f"{IDENTIFIER}{status.value}"
        emoji_pattern = EMOJI_PATTERN
        new_name = re.sub(rf"^[{emoji_pattern}]*", f"{emoji}", current_name)
        if not new_name.startswith(emoji):
            new_name = f"{emoji}{current_name}"

        subprocess.run(["tmux", "rename-window", "-t", window_id, new_name], check=True)
    except Exception:
        pass


if __name__ == "__main__":
    raise SystemExit(main())
