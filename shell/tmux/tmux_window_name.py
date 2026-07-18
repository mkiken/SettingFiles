#!/usr/bin/env python3
"""tmuxウィンドウ名の絵文字プレフィックス操作（共通実装）

AIフック（claude/gemini/codex）からはimportで、
シェル（tmux_window_name.sh）からはCLIサブコマンドで利用する。
"""
import os
import subprocess
import sys
from enum import Enum

from tmux_emoji import (
    EMOJI_CONTEXT_ALERT,
    EMOJI_STATUS_COMPLETED,
    EMOJI_STATUS_NOTIFICATION,
    EMOJI_STATUS_ONGOING,
    strip_emoji_prefix,
)


class HookStatus(Enum):
    COMPLETED = EMOJI_STATUS_COMPLETED
    NOTIFICATION = EMOJI_STATUS_NOTIFICATION
    ONGOING = EMOJI_STATUS_ONGOING


# remove_tmux_window_icon の戻り値（シェル版remove_tmux_window_iconの終了コード契約と互換）
CLEANUP_OK = 0
CLEANUP_NO_ICON = 1
CLEANUP_NOT_TMUX = 2
CLEANUP_NAME_READ_FAILED = 3
CLEANUP_WINDOW_ID_FAILED = 4
CLEANUP_STRIP_FAILED = 5
CLEANUP_RENAME_FAILED = 6

CLEANUP_MESSAGES = {
    CLEANUP_NOT_TMUX: "tmux window icon cleanup skipped: TMUX_PANE is unset or TERM_PROGRAM is not tmux",
    CLEANUP_NAME_READ_FAILED: "tmux window icon cleanup failed: could not read current tmux window name",
    CLEANUP_WINDOW_ID_FAILED: "tmux window icon cleanup failed: could not resolve tmux window id",
    CLEANUP_STRIP_FAILED: "tmux window icon cleanup failed: could not strip emoji prefix",
    CLEANUP_RENAME_FAILED: "tmux window icon cleanup failed: could not rename tmux window",
}

# updateはcleanupと同じ失敗段階の終了コードを使い、tmux外は成功扱いにする。
UPDATE_OK = CLEANUP_OK
UPDATE_NAME_READ_FAILED = CLEANUP_NAME_READ_FAILED
UPDATE_WINDOW_ID_FAILED = CLEANUP_WINDOW_ID_FAILED
UPDATE_NAME_BUILD_FAILED = CLEANUP_STRIP_FAILED
UPDATE_RENAME_FAILED = CLEANUP_RENAME_FAILED

UPDATE_MESSAGES = {
    UPDATE_NAME_READ_FAILED: "tmux window icon update failed: could not read current tmux window name",
    UPDATE_WINDOW_ID_FAILED: "tmux window icon update failed: could not resolve tmux window id",
    UPDATE_NAME_BUILD_FAILED: "tmux window icon update failed: could not build tmux window name",
    UPDATE_RENAME_FAILED: "tmux window icon update failed: could not rename tmux window",
}


def get_tmux_pane_id(env=None) -> str | None:
    """tmuxセッション内の場合のみpane_idを返す。それ以外はNone。
    VSCode等からtmuxを起動した際にTMUX_PANEが継承されるケースを除外するため、
    TERM_PROGRAM=="tmux"も確認する。
    """
    if env is None:
        env = os.environ
    pane_id = env.get("TMUX_PANE")
    if not pane_id or env.get("TERM_PROGRAM", "") != "tmux":
        return None
    return pane_id


def _split_emoji_prefix(current: str) -> tuple[str, str]:
    """名前を(絵文字プレフィックス, 残り)に分割する。"""
    stripped = strip_emoji_prefix(current)
    return current[: len(current) - len(stripped)], stripped


def build_updated_name(current: str, status_emoji: str, identifier: str = "") -> str:
    """既存の絵文字プレフィックスを新しい状態アイコンへ置き換えた名前を返す。
    contextアラートバッジは状態アイコンとは独立なので保持する。
    """
    prefix, stripped = _split_emoji_prefix(current)
    badge = EMOJI_CONTEXT_ALERT if EMOJI_CONTEXT_ALERT in prefix else ""
    return f"{identifier}{status_emoji}{badge}{stripped}"


def build_cleaned_name(current: str) -> str:
    """先頭の絵文字プレフィックス（バッジ含む）を除去した名前を返す。"""
    return strip_emoji_prefix(current)


def _read_current_name(pane_id: str, run) -> str:
    result = run(
        ["tmux", "display-message", "-p", "-t", pane_id, "#W"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _read_window_id(pane_id: str, run) -> str:
    # pane_idからグローバルにユニークなwindow_idを取得（renameの対象指定に使う）
    result = run(
        ["tmux", "display-message", "-p", "-t", pane_id, "#{window_id}"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _rename_window(window_id: str, new_name: str, run):
    run(["tmux", "rename-window", "-t", window_id, new_name], check=True)


def update_tmux_window_name(
    status: HookStatus | str,
    identifier: str = "",
    *,
    report_error: bool = False,
    run=subprocess.run,
    env=None,
) -> int:
    """指定された状態アイコンをtmuxウィンドウ名のプレフィックスに設定する。
    statusはHookStatusまたは絵文字文字列。tmux環境外は成功扱いにする。
    戻り値はUPDATE_*。report_error時は失敗理由をstderrに出力する。
    """

    def fail(code: int) -> int:
        if report_error:
            message = UPDATE_MESSAGES.get(
                code, f"tmux window icon update failed: unexpected status {code}"
            )
            print(message, file=sys.stderr)
        return code

    emoji = status.value if isinstance(status, HookStatus) else status
    pane_id = get_tmux_pane_id(env)
    if not pane_id:
        return UPDATE_OK
    try:
        current_name = _read_current_name(pane_id, run)
    except Exception:
        return fail(UPDATE_NAME_READ_FAILED)
    try:
        window_id = _read_window_id(pane_id, run)
    except Exception:
        return fail(UPDATE_WINDOW_ID_FAILED)
    try:
        new_name = build_updated_name(current_name, emoji, identifier)
    except Exception:
        return fail(UPDATE_NAME_BUILD_FAILED)
    try:
        _rename_window(window_id, new_name, run)
    except Exception:
        return fail(UPDATE_RENAME_FAILED)
    return UPDATE_OK


def remove_tmux_window_icon(report_error: bool = False, *, run=subprocess.run, env=None) -> int:
    """tmuxウィンドウ名から絵文字プレフィックスを除去して元の名前に戻す。
    戻り値はCLEANUP_*。report_error時はコード2以上でCLEANUP_MESSAGESをstderrに出力する。
    """

    def fail(code: int) -> int:
        if report_error:
            message = CLEANUP_MESSAGES.get(
                code, f"tmux window icon cleanup failed: unexpected status {code}"
            )
            print(message, file=sys.stderr)
        return code

    pane_id = get_tmux_pane_id(env)
    if not pane_id:
        return fail(CLEANUP_NOT_TMUX)
    try:
        current_name = _read_current_name(pane_id, run)
    except Exception:
        return fail(CLEANUP_NAME_READ_FAILED)
    try:
        window_id = _read_window_id(pane_id, run)
    except Exception:
        return fail(CLEANUP_WINDOW_ID_FAILED)
    try:
        new_name = build_cleaned_name(current_name)
    except Exception:
        return fail(CLEANUP_STRIP_FAILED)
    if new_name == current_name:
        return CLEANUP_NO_ICON
    try:
        _rename_window(window_id, new_name, run)
    except Exception:
        return fail(CLEANUP_RENAME_FAILED)
    return CLEANUP_OK


def add_context_alert_badge(*, run=subprocess.run, env=None):
    """context逼迫バッジを状態アイコンとは独立して追加する。"""
    try:
        pane_id = get_tmux_pane_id(env)
        if not pane_id:
            return
        current_name = _read_current_name(pane_id, run)
        window_id = _read_window_id(pane_id, run)
        prefix, stripped = _split_emoji_prefix(current_name)
        if EMOJI_CONTEXT_ALERT in prefix:
            return
        _rename_window(window_id, f"{prefix}{EMOJI_CONTEXT_ALERT}{stripped}", run)
    except Exception:
        pass


def remove_context_alert_badge(*, run=subprocess.run, env=None) -> int:
    """context逼迫バッジだけを外し、状態アイコンは残す。バッジ不在時は1を返す。"""
    try:
        pane_id = get_tmux_pane_id(env)
        if not pane_id:
            return 0
        current_name = _read_current_name(pane_id, run)
        window_id = _read_window_id(pane_id, run)
        prefix, stripped = _split_emoji_prefix(current_name)
        if EMOJI_CONTEXT_ALERT not in prefix:
            return 1
        new_prefix = prefix.replace(EMOJI_CONTEXT_ALERT, "", 1)
        _rename_window(window_id, f"{new_prefix}{stripped}", run)
        return 0
    except Exception:
        return 0


_USAGE = (
    "usage: tmux_window_name.py"
    " {update <emoji-prefix> [identifier] [--report-error]"
    " | remove [--report-error] | add-badge | remove-badge}"
)
_EX_USAGE = 64


def main(argv: list[str]) -> int:
    if not argv:
        print(_USAGE, file=sys.stderr)
        return _EX_USAGE
    command, args = argv[0], argv[1:]
    if command == "update":
        report_error = bool(args) and args[-1] == "--report-error"
        update_args = args[:-1] if report_error else args
        if len(update_args) in (1, 2) and "--report-error" not in update_args:
            code = update_tmux_window_name(
                update_args[0],
                update_args[1] if len(update_args) == 2 else "",
                report_error=report_error,
            )
            return code if report_error else UPDATE_OK
    if command == "remove" and args in ([], ["--report-error"]):
        return remove_tmux_window_icon(report_error=bool(args))
    if command == "add-badge" and not args:
        add_context_alert_badge()
        return 0
    if command == "remove-badge" and not args:
        return remove_context_alert_badge()
    print(_USAGE, file=sys.stderr)
    return _EX_USAGE


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
