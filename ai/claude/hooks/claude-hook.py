#!/usr/bin/env python3
# [Claude Code Hooksでtmuxのウィンドウ名を変更して通知の代わりにする #ClaudeCode - Qiita](https://qiita.com/miya10kei/items/d9dd12e8fde42fb222e2)
import json
import os
import re
import subprocess
import sys
from enum import Enum


class HookStatus(Enum):
    COMPLETED = "✅"
    NOTIFICATION = "✋"
    ONGOING = "🤖"

    @classmethod
    def get_emoji_pattern(cls) -> str:
        return "".join(status.value for status in cls) + "💎✴️" # Geminiで💎を使っているため追加している


IDENTIFIER = "✴️"


class SoundType(Enum):
    STOP = "stop"
    NOTIFICATION = "notification"


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


def handle_stop_hook(_: dict):
    update_tmux_window_name(HookStatus.COMPLETED)


def handle_session_end_hook(_: dict):
    """セッション終了時にtmuxウィンドウ名からアイコンを削除"""
    remove_tmux_window_icon()


def update_tmux_window_name(status: HookStatus):
    """指定されたステータスでtmuxウィンドウ名を更新"""
    try:
        # 実際のtmuxセッション内でのみ更新（VSCode等からの継承を除外）
        pane_id = _get_tmux_pane_id()
        if not pane_id:
            return

        # pane_idから直接ウィンドウ名を取得（pane_idはグローバルにユニーク）
        result = subprocess.run(
            ["tmux", "display-message", "-p", "-t", pane_id, "#W"],
            capture_output=True,
            text=True,
            check=True,
        )
        current_name = result.stdout.strip()

        # pane_idからグローバルにユニークなwindow_idを取得
        result = subprocess.run(
            ["tmux", "display-message", "-p", "-t", pane_id, "#{window_id}"],
            capture_output=True,
            text=True,
            check=True,
        )
        window_id = result.stdout.strip()

        emoji = f"{IDENTIFIER}{status.value}"
        # 既存の絵文字を置き換え（または追加）
        emoji_pattern = HookStatus.get_emoji_pattern()
        new_name = re.sub(rf"^[{emoji_pattern}]*", f"{emoji}", current_name)
        if not new_name.startswith(emoji):
            new_name = f"{emoji}{current_name}"

        # グローバルにユニークなwindow_idでrename
        subprocess.run(["tmux", "rename-window", "-t", window_id, new_name], check=True)
    except Exception:
        pass  # tmux環境外やエラーは無視


def remove_tmux_window_icon():
    """tmuxウィンドウ名から状態アイコンを削除"""
    try:
        # 実際のtmuxセッション内でのみ更新（VSCode等からの継承を除外）
        pane_id = _get_tmux_pane_id()
        if not pane_id:
            return

        # pane_idから直接ウィンドウ名を取得（pane_idはグローバルにユニーク）
        result = subprocess.run(
            ["tmux", "display-message", "-p", "-t", pane_id, "#W"],
            capture_output=True,
            text=True,
            check=True,
        )
        current_name = result.stdout.strip()

        # pane_idからグローバルにユニークなwindow_idを取得
        result = subprocess.run(
            ["tmux", "display-message", "-p", "-t", pane_id, "#{window_id}"],
            capture_output=True,
            text=True,
            check=True,
        )
        window_id = result.stdout.strip()

        # 先頭の絵文字パターンを削除
        emoji_pattern = HookStatus.get_emoji_pattern()
        new_name = re.sub(rf"^[{emoji_pattern}]+", "", current_name)

        # 名前が変わった場合のみ更新
        if new_name != current_name:
            subprocess.run(
                ["tmux", "rename-window", "-t", window_id, new_name],
                check=True
            )
    except Exception:
        pass


if __name__ == "__main__":
    main()

