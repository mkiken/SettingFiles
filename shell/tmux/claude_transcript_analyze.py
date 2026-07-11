#!/usr/bin/env python3
"""Claude Codeトランスクリプト(JSONL)の単一パス解析。

stop-send-notification.sh から呼ばれ、通知要約に必要な値だけを
shlex-quote済みの VAR=... 行として出力する（フック側で eval する）。
旧実装の1行ごとのjq起動（行数×最大10プロセス）とタイムスタンプ用の
全ファイル再走査を、1回のストリーミングパスに置き換える。

bash旧実装とのパリティ仕様は tests/test_claude_transcript_analyze.py が固定する。
"""

import json
import re
import shlex
import sys

# 旧bash実装 `sed 's/  */ /g'` と同じ「スペースのみ」を詰める（タブは温存）
_SQUEEZE_RE = re.compile(r" +")

# Claude Codeの既知システムタグ（メッセージ先頭のみ、先頭の空白/タブを許容）
_SYSTEM_TAG_RE = re.compile(
    r"^[ \t]*<(?:command-message|command-name|command-args|local-command-caveat"
    r"|local-command-stdout|system-reminder|user-prompt-submit-hook|tool-result|antml)"
)
# コマンド説明パターン（例: "# /command - Command Reference"）
_COMMAND_DOC_RE = re.compile(r"^#[ \t]*/[a-z:-]+[ \t]*-")
_ARGUMENTS_RE = re.compile(r"^ARGUMENTS:[ \t]")

_COMMAND_NAME_RE = re.compile(r"<command-name>([^<]*)</command-name>")
_COMMAND_ARGS_RE = re.compile(r"<command-args>([^<]*)</command-args>")


def squeeze_spaces(text):
    return _SQUEEZE_RE.sub(" ", text)


def extract_string_content(raw):
    # 旧実装 `echo | tr '\n' ' ' | sed` はechoの末尾改行が末尾スペースとして残る。
    # 長さ<4フィルタの挙動パリティのため同じ痕跡を再現する。
    return squeeze_spaces(raw.replace("\n", " ") + " ")


def extract_array_content(items):
    texts = [
        item.get("text", "")
        for item in items
        if isinstance(item, dict) and item.get("type") == "text"
    ]
    return squeeze_spaces("\n".join(texts).replace("\n", " ")).strip()


def apply_command_tags(content):
    """スラッシュコマンド展開: command-nameタグをコマンド名(+引数)に置き換える。"""
    name_match = _COMMAND_NAME_RE.search(content)
    if not name_match:
        return content
    command_name = name_match.group(1)
    args_match = _COMMAND_ARGS_RE.search(content)
    if args_match and args_match.group(1):
        args = squeeze_spaces(args_match.group(1).replace("\n", " "))
        return f"{command_name} {args}"
    return command_name


def is_system_message(msg):
    # スラッシュコマンド（/で始まる）はユーザーの意図的な入力として扱う
    if msg.startswith("/"):
        return False
    if _SYSTEM_TAG_RE.match(msg):
        return True
    if msg.startswith("Caveat:"):
        return True
    if _COMMAND_DOC_RE.match(msg):
        return True
    if _ARGUMENTS_RE.match(msg):
        return True
    # 日本語の短い指示を許容（4文字未満はシステム扱い）
    return len(msg) < 4


def _is_valid_timestamp(value):
    return isinstance(value, str) and value not in ("", "null")


def analyze_lines(lines):
    result = {
        "last_user_message": "",
        "user_count": 0,
        "assistant_count": 0,
        "first_timestamp": "",
        "last_timestamp": "",
    }
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue

        # タイムスタンプはsidechain/metaスキップの前に収集する
        # （旧実装の第2パスは全行を対象にしていたため。summary行のみ除外）
        if obj.get("type") != "summary":
            timestamp = obj.get("timestamp")
            if _is_valid_timestamp(timestamp):
                if not result["first_timestamp"]:
                    result["first_timestamp"] = timestamp
                result["last_timestamp"] = timestamp

        # サイドチェーン（Warmupなど）とisMeta（スラッシュコマンド展開テキスト）はスキップ
        if obj.get("isSidechain") in (True, "true"):
            continue
        if obj.get("isMeta") in (True, "true"):
            continue

        message = obj.get("message")
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        raw_content = message.get("content")
        if isinstance(raw_content, str):
            content = apply_command_tags(extract_string_content(raw_content))
        elif isinstance(raw_content, list):
            content = extract_array_content(raw_content)
        else:
            content = ""

        stripped = content.strip()
        if not stripped or stripped == "null":
            continue
        if role == "user":
            # フィルタには経路ごとの痕跡込みのcontentを渡す（旧実装パリティ）
            if not is_system_message(content):
                result["last_user_message"] = stripped
                result["user_count"] += 1
        elif role == "assistant":
            result["assistant_count"] += 1
    return result


def main(argv):
    if len(argv) != 2:
        print(f"Usage: {argv[0]} <transcript_path>", file=sys.stderr)
        return 1
    try:
        with open(argv[1], encoding="utf-8", errors="replace") as transcript:
            result = analyze_lines(transcript)
    except OSError:
        # フック側でファイル存在を確認済み。読めない場合はゼロ値で劣化させる
        result = analyze_lines([])
    print(f"LAST_USER_MESSAGE={shlex.quote(result['last_user_message'])}")
    print(f"USER_MESSAGE_COUNT={result['user_count']}")
    print(f"ASSISTANT_MESSAGE_COUNT={result['assistant_count']}")
    print(f"FIRST_TIMESTAMP={shlex.quote(result['first_timestamp'])}")
    print(f"LAST_TIMESTAMP={shlex.quote(result['last_timestamp'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
