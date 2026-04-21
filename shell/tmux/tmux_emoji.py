"""tmuxウィンドウ名の絵文字アイコン定義（共通モジュール）

tmux_emoji.conf を Single Source of Truth として読み込み、
Python スクリプトに EMOJI_PATTERN と strip_emoji_prefix() を提供する。
"""
import re
from pathlib import Path

# Unicode絵文字を先頭から除去する汎用パターン（confに依存しない全絵文字対応）
_EMOJI_PREFIX_RE = re.compile(
    r"^["
    r"\U0001F600-\U0001F64F"  # Emoticons
    r"\U0001F300-\U0001F5FF"  # Misc Symbols and Pictographs
    r"\U0001F680-\U0001F6FF"  # Transport and Map
    r"\U0001F1E0-\U0001F1FF"  # Flags
    r"\U00002702-\U000027B0"  # Dingbats
    r"\U0000FE00-\U0000FE0F"  # Variation Selectors
    r"\U0000200D"             # ZWJ
    r"\U00002600-\U000026FF"  # Misc symbols (✅✴️ etc.)
    r"\U0001F900-\U0001F9FF"  # Supplemental Symbols
    r"\U0001FA00-\U0001FA6F"  # Extended Pictographic A
    r"\U0001FA70-\U0001FAFF"  # Extended Pictographic B
    r"\U00002B50"             # Star
    r"\U0000203C-\U00003299"  # CJK Symbols etc.
    r"\s]+"
)

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
EMOJI_ID_CODEX = _conf["EMOJI_ID_CODEX"]
EMOJI_STATUS_COMPLETED = _conf["EMOJI_STATUS_COMPLETED"]
EMOJI_STATUS_NOTIFICATION = _conf["EMOJI_STATUS_NOTIFICATION"]
EMOJI_STATUS_ONGOING = _conf["EMOJI_STATUS_ONGOING"]

EMOJI_PATTERN = "".join([
    EMOJI_STATUS_COMPLETED,
    EMOJI_STATUS_NOTIFICATION,
    EMOJI_STATUS_ONGOING,
    EMOJI_ID_CLAUDE,
    EMOJI_ID_GEMINI,
    EMOJI_ID_CODEX,
])


def strip_emoji_prefix(name: str) -> str:
    """ウィンドウ名から先頭の絵文字アイコンを除去（全Unicode絵文字対応）"""
    return _EMOJI_PREFIX_RE.sub("", name)


if __name__ == "__main__":
    # CLI用エントリポイント: シェルスクリプトからウィンドウ名の絵文字除去に使用
    # 使い方: python3 tmux_emoji.py "✴️🤖main" → "main"
    import sys
    print(strip_emoji_prefix(sys.argv[1]) if len(sys.argv) > 1 else "")
