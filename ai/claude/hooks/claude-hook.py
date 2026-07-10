#!/usr/bin/env python3
# [Claude Code Hooksでtmuxのウィンドウ名を変更して通知の代わりにする #ClaudeCode - Qiita](https://qiita.com/miya10kei/items/d9dd12e8fde42fb222e2)
import json
import sys
from enum import Enum
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shell" / "tmux"))
import tmux_window_name as _twn
from tmux_emoji import EMOJI_ID_CLAUDE
from tmux_window_name import HookStatus, remove_tmux_window_icon

IDENTIFIER = EMOJI_ID_CLAUDE
update_tmux_window_name = partial(_twn.update_tmux_window_name, identifier=IDENTIFIER)


class SoundType(Enum):
    STOP = "stop"
    NOTIFICATION = "notification"


def main():
    input_data = json.load(sys.stdin)

    # サブエージェント由来のイベントは無視（メインエージェントの動向のみ追跡）。
    # agent_id はサブエージェント内で発火した場合のみ存在する（公式仕様）。
    if input_data.get("agent_id"):
        return

    hook_event = input_data.get("hook_event_name")

    handlers = {
        "Notification": handle_notification_hook,
        "PostToolUse": handle_post_tool_use_hook,
        "SessionEnd": handle_session_end_hook,
        "Stop": handle_stop_hook,
        "UserPromptSubmit": handle_user_prompt_submit_hook,
    }

    handler = handlers.get(hook_event)

    if handler:
        handler(input_data)


def handle_notification_hook(input_data: dict):
    if input_data.get("notification_type") == "permission_prompt":
        update_tmux_window_name(HookStatus.NOTIFICATION)


def handle_post_tool_use_hook(_: dict):
    update_tmux_window_name(HookStatus.ONGOING)


def handle_user_prompt_submit_hook(_: dict):
    update_tmux_window_name(HookStatus.ONGOING)


def handle_stop_hook(input_data: dict):
    # バックグラウンドタスク（サブエージェント等）がrunning中にメインのStopが
    # 発火した場合、実際はまだ作業中なので✅にせず、直前のPostToolUseの🤖を維持する。
    if _has_running_background_tasks(input_data):
        return
    update_tmux_window_name(HookStatus.COMPLETED)


def _has_running_background_tasks(input_data: dict) -> bool:
    """background_tasks 内に status=="running" の要素があれば True。

    フィールド不在（旧バージョン）やNone、空配列は False。
    完了済みタスクが配列に残り続けても、statusで判定するため誤判定しない。
    """
    tasks = input_data.get("background_tasks")
    if not tasks:
        return False
    return any(task.get("status") == "running" for task in tasks)


def handle_session_end_hook(_: dict):
    """セッション終了時にtmuxウィンドウ名からアイコンを削除"""
    remove_tmux_window_icon()


if __name__ == "__main__":
    main()

