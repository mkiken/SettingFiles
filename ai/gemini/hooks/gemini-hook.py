#!/usr/bin/env python3
import os
import sys
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shell" / "tmux"))
import tmux_window_name as _twn
from tmux_emoji import EMOJI_ID_GEMINI
from tmux_window_name import (
    HookStatus,
    remove_herdr_tab_icon,
    remove_tmux_window_icon,
    update_herdr_tab_icon,
)

IDENTIFIER = EMOJI_ID_GEMINI
update_tmux_window_name = partial(_twn.update_tmux_window_name, identifier=IDENTIFIER)
update_herdr_tab_icon = partial(update_herdr_tab_icon, identifier=IDENTIFIER)


def main():
    # Geminiはnotify-richから外れているため、Herdr下でもhookがタブ名を直接書く
    in_herdr = os.environ.get("HERDR_ENV") == "1"
    set_ongoing = update_herdr_tab_icon if in_herdr else update_tmux_window_name
    clear_icon = remove_herdr_tab_icon if in_herdr else remove_tmux_window_icon

    # 引数からイベント名を取得
    if len(sys.argv) < 2:
        return

    event_name = sys.argv[1]

    # 標準入力は読み捨てる（書き込み側のSIGPIPEを避けるため）
    try:
        if not sys.stdin.isatty():
            sys.stdin.read()
    except Exception:
        pass

    # 承認待ち(notification)と終了(after_agent)のアイコンは notification.sh が
    # Mac通知とセットで所有する。ここは進行中🤖とsession_endの掃除のみ担当。
    if event_name in ["before_agent", "before_tool", "after_tool"]:
        set_ongoing(HookStatus.ONGOING)
    elif event_name in ["session_end"]:
        clear_icon()


if __name__ == "__main__":
    main()
