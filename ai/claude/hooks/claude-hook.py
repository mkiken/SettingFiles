#!/usr/bin/env python3
# [Claude Code Hooksでtmuxのウィンドウ名を変更して通知の代わりにする #ClaudeCode - Qiita](https://qiita.com/miya10kei/items/d9dd12e8fde42fb222e2)
import json
import os
import sys
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shell" / "tmux"))
import tmux_window_name as _twn
from tmux_emoji import EMOJI_ID_CLAUDE
from tmux_window_name import HookStatus, remove_tmux_window_icon

IDENTIFIER = EMOJI_ID_CLAUDE
update_tmux_window_name = partial(_twn.update_tmux_window_name, identifier=IDENTIFIER)


def main():
    if os.environ.get("HERDR_ENV") == "1":
        return

    input_data = json.load(sys.stdin)

    # サブエージェント由来のイベントは無視（メインエージェントの動向のみ追跡）。
    # agent_id はサブエージェント内で発火した場合のみ存在する（公式仕様）。
    if input_data.get("agent_id"):
        return

    hook_event = input_data.get("hook_event_name")

    # 承認待ち(Notification)と終了(Stop)のアイコンは stop-send-notification.sh が
    # Mac通知とセットで所有する。ここは進行中🤖とSessionEndの掃除のみ担当。
    handlers = {
        "PostToolUse": handle_post_tool_use_hook,
        "SessionEnd": handle_session_end_hook,
        "UserPromptSubmit": handle_user_prompt_submit_hook,
    }

    handler = handlers.get(hook_event)

    if handler:
        handler(input_data)


def handle_post_tool_use_hook(_: dict):
    update_tmux_window_name(HookStatus.ONGOING)


def handle_user_prompt_submit_hook(_: dict):
    update_tmux_window_name(HookStatus.ONGOING)


def handle_session_end_hook(_: dict):
    """セッション終了時にtmuxウィンドウ名からアイコンを削除"""
    remove_tmux_window_icon()


if __name__ == "__main__":
    main()
