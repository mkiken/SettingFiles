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
        "PostToolUse": handle_post_tool_use_hook,
        "Stop": handle_stop_hook,
        "UserPromptSubmit": handle_user_prompt_submit_hook,
    }

    handler = handlers.get(hook_event)

    if handler:
        handler(input_data)


def handle_post_tool_use_hook(_: dict):
    update_tmux_window_name(HookStatus.ONGOING)


def handle_user_prompt_submit_hook(_: dict):
    update_tmux_window_name(HookStatus.ONGOING)


def handle_stop_hook(_: dict):
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
