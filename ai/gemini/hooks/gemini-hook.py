#!/usr/bin/env python3
import json
import sys
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shell" / "tmux"))
import tmux_window_name as _twn
from tmux_emoji import EMOJI_ID_GEMINI
from tmux_window_name import HookStatus, remove_tmux_window_icon

IDENTIFIER = EMOJI_ID_GEMINI
update_tmux_window_name = partial(_twn.update_tmux_window_name, identifier=IDENTIFIER)


def main():
    # 引数からイベント名を取得
    if len(sys.argv) < 2:
        return

    event_name = sys.argv[1]

    # 標準入力からJSONを読み込む（必要に応じて）
    data = {}
    try:
        if not sys.stdin.isatty():
             data = json.load(sys.stdin)
    except Exception:
        pass

    if event_name == "notification":
        if data.get("notification_type") == "ToolPermission":
            update_tmux_window_name(HookStatus.NOTIFICATION)
    elif event_name in ["after_agent"]:
        update_tmux_window_name(HookStatus.COMPLETED)
    elif event_name in ["before_agent", "before_tool"]:
        update_tmux_window_name(HookStatus.ONGOING)
    elif event_name in ["after_tool"]:
        update_tmux_window_name(HookStatus.ONGOING)
    elif event_name in ["session_end"]:
        remove_tmux_window_icon()


if __name__ == "__main__":
    main()
