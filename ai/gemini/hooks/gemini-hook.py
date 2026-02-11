#!/usr/bin/env python3
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
        return "".join(status.value for status in cls) + "💎✴️" # Claude Codeで✴️を使っているため追加している


IDENTIFIER = "💎"


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


def get_current_tty() -> str:
    """現在のプロセスの制御端末(TTY)のパスを取得"""
    try:
        # os.ttyname(0)などは /dev/tty を返すことがあり、tmuxの #{pane_tty} (/dev/ttysXXX) と一致しないため
        # psコマンドを使用して具体的なTTYデバイス名を取得する
        result = subprocess.run(
            ["ps", "-p", str(os.getpid()), "-o", "tty="],
            capture_output=True,
            text=True,
            check=True,
        )
        tty_name = result.stdout.strip()

        if not tty_name or tty_name in ["?", "??"]:
            return ""

        if not tty_name.startswith("/"):
            return f"/dev/{tty_name}"
        return tty_name
    except Exception:
        return ""


def is_valid_tmux_context(pane_id: str) -> bool:
    """
    現在のプロセスが指定されたtmuxペイン内で実行されているか確認
    環境変数が継承されただけの別ターミナル（VSCode等）での誤動作を防ぐ
    """
    try:
        current_tty = get_current_tty()
        if not current_tty:
            return False

        # tmuxペインのTTYを取得
        result = subprocess.run(
            ["tmux", "display-message", "-p", "-t", pane_id, "#{pane_tty}"],
            capture_output=True,
            text=True,
            check=True,
        )
        pane_tty = result.stdout.strip()

        return current_tty == pane_tty
    except Exception:
        return False


def update_tmux_window_name(status: HookStatus):
    """指定されたステータスでtmuxウィンドウ名を更新"""
    try:
        # $TMUX_PANE環境変数から実行元のペインIDを取得
        pane_id = os.environ.get("TMUX_PANE")
        if not pane_id:
            return  # tmux環境外では何もしない

        # 環境変数が継承されただけの別ターミナル（VSCode等）での誤動作を防ぐ
        if not is_valid_tmux_context(pane_id):
            return

        # ペインが属するウィンドウIDを取得
        result = subprocess.run(
            ["tmux", "display-message", "-p", "-t", pane_id, "#I"],
            capture_output=True,
            text=True,
            check=True,
        )
        window_id = result.stdout.strip()

        # 特定のウィンドウの現在の名前を取得
        result = subprocess.run(
            ["tmux", "display-message", "-p", "-t", window_id, "#W"],
            capture_output=True,
            text=True,
            check=True,
        )
        current_name = result.stdout.strip()

        emoji = f"{IDENTIFIER}{status.value}"
        # 既存の絵文字を置き換え（または追加）
        emoji_pattern = HookStatus.get_emoji_pattern()
        new_name = re.sub(rf"^[{emoji_pattern}]*", f"{emoji}", current_name)
        if not new_name.startswith(emoji):
            new_name = f"{emoji}{current_name}"

        # 特定のウィンドウに対して名前を更新
        subprocess.run(["tmux", "rename-window", "-t", window_id, new_name], check=True)
    except Exception:
        pass  # tmux環境外やエラーは無視


def remove_tmux_window_icon():
    """tmuxウィンドウ名から状態アイコンを削除"""
    try:
        pane_id = os.environ.get("TMUX_PANE")
        if not pane_id:
            return

        # 環境変数が継承されただけの別ターミナル（VSCode等）での誤動作を防ぐ
        if not is_valid_tmux_context(pane_id):
            return

        # ウィンドウIDを取得
        result = subprocess.run(
            ["tmux", "display-message", "-p", "-t", pane_id, "#I"],
            capture_output=True,
            text=True,
            check=True,
        )
        window_id = result.stdout.strip()

        # 現在のウィンドウ名を取得
        result = subprocess.run(
            ["tmux", "display-message", "-p", "-t", window_id, "#W"],
            capture_output=True,
            text=True,
            check=True,
        )
        current_name = result.stdout.strip()

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
