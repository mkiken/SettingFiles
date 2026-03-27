"""tmuxウィンドウ名の絵文字アイコン定義（共通モジュール）

tmux_emoji.conf を Single Source of Truth として読み込み、
Python スクリプトに EMOJI_PATTERN と strip_emoji_prefix() を提供する。
"""
import re
from pathlib import Path

_CONF = Path(__file__).resolve().parent / "tmux_emoji.conf"


def _load_conf() -> dict[str, str]:
    conf = {}
    for line in _CONF.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            key, _, value = line.partition("=")
            conf[key.strip()] = value.strip()
    return conf


_conf = _load_conf()

EMOJI_ID_CLAUDE = _conf["EMOJI_ID_CLAUDE"]
EMOJI_ID_GEMINI = _conf["EMOJI_ID_GEMINI"]
EMOJI_STATUS_COMPLETED = _conf["EMOJI_STATUS_COMPLETED"]
EMOJI_STATUS_NOTIFICATION = _conf["EMOJI_STATUS_NOTIFICATION"]
EMOJI_STATUS_ONGOING = _conf["EMOJI_STATUS_ONGOING"]

EMOJI_PATTERN = "".join([
    EMOJI_STATUS_COMPLETED,
    EMOJI_STATUS_NOTIFICATION,
    EMOJI_STATUS_ONGOING,
    EMOJI_ID_CLAUDE,
    EMOJI_ID_GEMINI,
])


def strip_emoji_prefix(name: str) -> str:
    """ウィンドウ名から先頭の絵文字アイコンを除去"""
    return re.sub(rf"^[{EMOJI_PATTERN}]+", "", name)


if __name__ == "__main__":
    # CLI用エントリポイント: シェルスクリプトからウィンドウ名の絵文字除去に使用
    # 使い方: python3 tmux_emoji.py "✴️🤖main" → "main"
    import sys
    print(strip_emoji_prefix(sys.argv[1]) if len(sys.argv) > 1 else "")
