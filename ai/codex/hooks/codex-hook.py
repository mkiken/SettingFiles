#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
from enum import Enum
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shell" / "tmux"))
from tmux_emoji import EMOJI_PATTERN, EMOJI_ID_CODEX


class HookStatus(Enum):
    COMPLETED = "✅"
    NOTIFICATION = "✋"
    ONGOING = "🤖"


IDENTIFIER = EMOJI_ID_CODEX


def is_subagent_metadata(data: dict) -> bool:
    source = data.get("source")
    has_subagent_source = isinstance(source, dict) and source.get("subagent") is not None
    return has_subagent_source or bool(data.get("agent_role")) or bool(data.get("agent_nickname"))


def is_subagent_session(input_data: dict) -> bool:
    if is_subagent_metadata(input_data):
        return True

    transcript_path = input_data.get("transcript_path")
    if not transcript_path:
        return False

    path = Path(transcript_path)
    if not path.is_file():
        return False

    try:
        with path.open(encoding="utf-8") as transcript:
            for line in transcript:
                if not line.strip():
                    continue

                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if event.get("type") != "session_meta":
                    continue

                payload = event.get("payload")
                if isinstance(payload, dict) and is_subagent_metadata(payload):
                    return True
    except Exception:
        return False

    return False


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


def main():
    input_data = json.load(sys.stdin)
    hook_event = input_data.get("hook_event_name")

    handlers = {
        "PermissionRequest": handle_permission_request_hook,
        "PostToolUse": handle_post_tool_use_hook,
        "Stop": handle_stop_hook,
        "UserPromptSubmit": handle_user_prompt_submit_hook,
    }

    handler = handlers.get(hook_event)

    if handler:
        handler(input_data)


def handle_post_tool_use_hook(_: dict):
    update_tmux_window_name(HookStatus.ONGOING)


def handle_permission_request_hook(_: dict):
    update_tmux_window_name(HookStatus.NOTIFICATION)


def handle_user_prompt_submit_hook(_: dict):
    update_tmux_window_name(HookStatus.ONGOING)


def handle_stop_hook(input_data: dict):
    if is_subagent_session(input_data):
        return

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
    main()
