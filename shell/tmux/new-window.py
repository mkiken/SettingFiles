#!/usr/bin/env python3
"""tmux new-window: 現在のウィンドウ名をコピーしAIアイコンを除去して新ウィンドウを作成"""
import subprocess
import re


def tmux_display(fmt):
    return subprocess.check_output(
        ["tmux", "display-message", "-p", fmt], text=True
    ).strip()


current_name = tmux_display("#W")
current_path = tmux_display("#{pane_current_path}")

# claude-hook.py / gemini-hook.py の HookStatus.get_emoji_pattern() と同じパターン
EMOJI_PATTERN = "✅✋🤖💎✴️"
clean_name = re.sub(rf"^[{EMOJI_PATTERN}]+", "", current_name)

subprocess.run(
    ["tmux", "new-window", "-c", current_path, "-n", clean_name],
    check=True,
)
