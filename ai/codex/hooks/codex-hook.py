#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime, timezone
from functools import partial
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shell" / "tmux"))
import tmux_window_name as _twn
from tmux_emoji import EMOJI_ID_CODEX
from tmux_window_name import HookStatus

IDENTIFIER = EMOJI_ID_CODEX
update_tmux_window_name = partial(_twn.update_tmux_window_name, identifier=IDENTIFIER)


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


def main() -> int:
    input_data, input_error = load_hook_input()
    if input_data is None:
        print_visible_hook_error(input_error or "failed to read hook input")
        return 1

    hook_event = input_data.get("hook_event_name")

    # 承認待ち(PermissionRequest)と終了/応答待ち(Stop)のアイコンは
    # codex-stop-notification.sh がMac通知とセットで所有する。ここは進行中🤖のみ担当。
    handlers = {
        "PostToolUse": handle_post_tool_use_hook,
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


def handle_user_prompt_submit_hook(_: dict):
    update_tmux_window_name(HookStatus.ONGOING)


if __name__ == "__main__":
    raise SystemExit(main())
