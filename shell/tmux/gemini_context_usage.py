#!/usr/bin/env python3
"""Gemini CLIのchat JSONLからcontext window使用量を単一プロセスで抽出する。

ai/gemini/hooks/notification.sh のcontext逼迫アラートから呼ばれ、
最新chat JSONLの探索（旧実装のfind|stat|sort|head|cut連鎖）と
トークン抽出（旧インラインpython + jq3回 + bc）を1回のpython起動に集約し、
shlex-quote済みの VAR=... 行として出力する（フック側で eval する）。

旧bash実装とのパリティ仕様は tests/test_gemini_context_usage.py と
ai/gemini/hooks/tests/test_notification_context.py が固定する。
"""

import json
import shlex
import sys
from pathlib import Path

# 現行のgeminiモデルは flash/pro とも context window 1Mトークンで共通
# （旧フックのモデル別case文も全分岐この値だった）。モデル別に分ける場合はここに表を戻す。
GEMINI_CONTEXT_WINDOW = 1048576


def find_latest_chat_jsonl(chat_dir, prefix):
    """`find -path "*/chats/*<prefix>*.jsonl"` 相当で最新（mtime最大）の1件を返す。

    パリティ: prefixは `/chats/` より後ろであればディレクトリ名でもファイル名でもマッチする。
    mtimeはfloat秒で比較し、同時刻はパス文字列の降順で決定的にタイブレークする
    （旧実装の整数秒stat + sortでは同秒タイが非決定的だった）。
    """
    root = Path(chat_dir)
    if not root.is_dir():
        return None
    best = None
    best_key = None
    for path in root.rglob("*.jsonl"):
        tail = str(path).partition("/chats/")
        if not tail[1] or prefix not in tail[2]:
            continue
        try:
            if not path.is_file():
                continue
            key = (path.stat().st_mtime, str(path))
        except OSError:
            continue
        if best_key is None or key > best_key:
            best, best_key = path, key
    return best


def extract_last_gemini_record(path):
    """`type=="gemini"` かつ `tokens` キーを持つ最後のJSONL行を返す。"""
    last = None
    try:
        with open(path, encoding="utf-8", errors="replace") as jsonl:
            for line in jsonl:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if (
                    isinstance(record, dict)
                    and record.get("type") == "gemini"
                    and "tokens" in record
                ):
                    last = record
    except OSError:
        return None
    return last


def _coerce_int(value):
    # boolはintのサブクラスだがトークン数として無効扱いにする
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return int(value)


def compute_usage(record):
    """(context_tokens, total_tokens, model) を返す。

    tokens.input が正の数値ならそれを、でなければ tokens.total にフォールバックする
    （旧インラインpython実装と同じ判定）。
    """
    tokens = record.get("tokens")
    if not isinstance(tokens, dict):
        tokens = {}
    context = tokens.get("input")
    if isinstance(context, bool) or not isinstance(context, (int, float)) or context <= 0:
        context = tokens.get("total", 0)
    model = record.get("model", "")
    if not isinstance(model, str):
        model = ""
    return _coerce_int(context), _coerce_int(tokens.get("total", context)), model


def format_used_pct(tokens, window):
    """使用率を小数1桁の文字列で返す。旧実装 `bc "scale=1"` と同じ切り捨て（四捨五入しない）。"""
    if tokens <= 0 or window <= 0:
        return "0.0"
    permille = tokens * 1000 // window
    return f"{permille // 10}.{permille % 10}"


def main(argv):
    if len(argv) != 3:
        print(f"Usage: {argv[0]} <chat_dir> <session_prefix>", file=sys.stderr)
        return 1
    context_tokens = 0
    total_tokens = 0
    model = ""
    used_pct = "0.0"
    chat_jsonl = find_latest_chat_jsonl(argv[1], argv[2])
    record = extract_last_gemini_record(chat_jsonl) if chat_jsonl else None
    if record:
        context_tokens, total_tokens, model = compute_usage(record)
        used_pct = format_used_pct(context_tokens, GEMINI_CONTEXT_WINDOW)
    print(f"GEMINI_CONTEXT_TOKENS={context_tokens}")
    print(f"GEMINI_TOTAL_TOKENS={total_tokens}")
    print(f"GEMINI_MODEL={shlex.quote(model)}")
    print(f"GEMINI_USED_PCT={shlex.quote(used_pct)}")
    print(f"GEMINI_WINDOW={GEMINI_CONTEXT_WINDOW}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
