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
from datetime import datetime, timedelta

# 旧bash実装 `sed 's/  */ /g'` と同じ「スペースのみ」を詰める（タブは温存）
_SQUEEZE_RE = re.compile(r" +")

# Claude Codeの既知システムタグ（メッセージ先頭のみ、先頭の空白/タブを許容）
# task-notificationはサブエージェント完了通知（Task tool）がrole:userで記録されたもの
_SYSTEM_TAG_RE = re.compile(
    r"^[ \t]*<(?:command-message|command-name|command-args|local-command-caveat"
    r"|local-command-stdout|system-reminder|user-prompt-submit-hook|tool-result"
    r"|task-notification|antml)"
)
# コマンド説明パターン（例: "# /command - Command Reference"）
_COMMAND_DOC_RE = re.compile(r"^#[ \t]*/[a-z:-]+[ \t]*-")
_ARGUMENTS_RE = re.compile(r"^ARGUMENTS:[ \t]")

_COMMAND_NAME_RE = re.compile(r"<command-name>([^<]*)</command-name>")
_COMMAND_ARGS_RE = re.compile(r"<command-args>([^<]*)</command-args>")

# バックグラウンド作業の検出（PENDING_BACKGROUND_WORK）:
# Stop hook入力にはbackground_tasks等のフィールドが存在しない（公式スキーマ・実入力とも確認済み）ため、
# transcriptから「async Agent起動済み・完了通知未着」「ScheduleWakeup武装中」を判定する。
# 対象はAgentツールのasync起動とScheduleWakeupのみ（Bash run_in_background / Workflowは対象外）。
_AGENT_LAUNCH_MARKER = "Async agent launched successfully"
_AGENT_ID_RE = re.compile(r"agentId: ([0-9a-z]+)")
_TASK_ID_RE = re.compile(r"<task-id>([0-9a-z]+)</task-id>")
# TaskStopのinputスキーマは未固定のため、ID形状の文字列値だけを停止対象として拾う
_TASK_STOP_ID_RE = re.compile(r"^[0-9a-z_-]{6,}$")


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


# bashヘルパー iso8601_to_epoch は `date -j -f "%Y-%m-%dT%H:%M:%S"` で
# 先頭が一致すれば末尾の余剰文字（Z等）を無視する。先頭マッチで同じ挙動を再現する。
_TS_NAIVE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


def parse_naive_timestamp(value):
    """小数秒（最後の`.`以降）を捨ててnaiveにパースする。失敗時はNone。"""
    if not _is_valid_timestamp(value):
        return None
    match = _TS_NAIVE_RE.match(value.rsplit(".", 1)[0])
    if not match:
        return None
    try:
        return datetime.strptime(match.group(0), "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None


def format_duration(total_seconds):
    """tmux_notification_title.sh の format_duration と同一フォーマット（1h1m / 1m2s / 5s）。"""
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours > 0:
        return f"{hours}h{minutes}m"
    if minutes > 0:
        return f"{minutes}m{seconds}s"
    return f"{seconds}s"


def build_time_fields(first_timestamp, last_timestamp):
    """(セッション時間, JST完了時刻) を返す。計算不能な要素は空文字。

    bashヘルパー format_session_duration / format_completion_time_jst の置き換え
    （dateサブプロセス×4の削減）。両者はTZなしパース→+9h表示のため、マシンTZが
    パースと表示で相殺され、naive演算で出力が完全一致する。
    """
    duration = ""
    completion = ""
    end = parse_naive_timestamp(last_timestamp)
    if end is None:
        return duration, completion
    completion = (end + timedelta(hours=9)).strftime("%H:%M:%S")
    start = parse_naive_timestamp(first_timestamp)
    if start is not None:
        duration = format_duration(int((end - start).total_seconds()))
    return duration, completion


def _tool_result_text(item):
    """tool_result要素からテキストを連結して返す（content: str | [{type:text}] 両対応）。"""
    inner = item.get("content")
    if isinstance(inner, str):
        return inner
    if isinstance(inner, list):
        return " ".join(
            part.get("text", "")
            for part in inner
            if isinstance(part, dict) and part.get("type") == "text"
        )
    return ""


def _collect_background_signals(obj, role, raw_content, state):
    """1メッセージ分のバックグラウンド作業シグナルをstateへ蓄積する。

    - launched: async Agent起動結果(tool_result)のagentId
    - completed: task-notificationのtask-id、およびTaskStop対象ID
    - wakeup_deadline: 武装中ScheduleWakeupの発火予定時刻（stop:trueでリセット）
    """
    if role == "user":
        if isinstance(raw_content, list):
            for item in raw_content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "tool_result":
                    text = _tool_result_text(item)
                    if _AGENT_LAUNCH_MARKER in text:
                        state["launched"].update(_AGENT_ID_RE.findall(text))
                elif item.get("type") == "text":
                    state["completed"].update(_TASK_ID_RE.findall(item.get("text", "")))
        elif isinstance(raw_content, str):
            state["completed"].update(_TASK_ID_RE.findall(raw_content))
    elif role == "assistant" and isinstance(raw_content, list):
        for item in raw_content:
            if not isinstance(item, dict) or item.get("type") != "tool_use":
                continue
            name = item.get("name")
            tool_input = item.get("input")
            if not isinstance(tool_input, dict):
                tool_input = {}
            if name == "ScheduleWakeup":
                if tool_input.get("stop") is True:
                    state["wakeup_deadline"] = None
                else:
                    armed_at = parse_naive_timestamp(obj.get("timestamp"))
                    delay = tool_input.get("delaySeconds")
                    if armed_at is not None and isinstance(delay, (int, float)):
                        deadline = armed_at + timedelta(seconds=delay)
                        current = state["wakeup_deadline"]
                        if current is None or deadline > current:
                            state["wakeup_deadline"] = deadline
            elif name == "TaskStop":
                state["completed"].update(
                    value
                    for value in tool_input.values()
                    if isinstance(value, str) and _TASK_STOP_ID_RE.match(value)
                )


def _resolve_pending_background_work(state, last_timestamp):
    """蓄積シグナルからPENDING_BACKGROUND_WORK(0/1)を決定する。

    武装中wakeupは発火予定時刻がtranscript末尾時刻より未来の場合のみ有効
    （発火済みwakeupの残骸で完了通知を抑止し続けないため）。
    """
    if state["launched"] - state["completed"]:
        return 1
    deadline = state["wakeup_deadline"]
    if deadline is not None:
        end = parse_naive_timestamp(last_timestamp)
        if end is None or end < deadline:
            return 1
    return 0


def analyze_lines(lines):
    result = {
        "last_user_message": "",
        "user_count": 0,
        "assistant_count": 0,
        "first_timestamp": "",
        "last_timestamp": "",
        "last_turn_api_error": "",
        "last_turn_api_error_text": "",
    }
    background_state = {"launched": set(), "completed": set(), "wakeup_deadline": None}
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

        # APIエラー行の検知はisSidechain/isMetaスキップより前に置く
        # （サブエージェント内のエラーも拾う方針。stop-send-notification.shの
        # agent_idガードでサブエージェント自身のイベントは通知されないが、
        # メインエージェントのStop時にtranscript解析経由でまとめて報じるため）。
        # エラー行自身はcontinueして後段の会話行集計・リセット判定を通過させない
        # （通過させるとエラー行自身がassistant_countに乗り、後続の会話行検出と
        # 同じ分岐でリセットが誤発火する）。
        if obj.get("isApiErrorMessage") and obj.get("type") == "assistant":
            result["last_turn_api_error"] = str(obj.get("error") or "unknown")
            error_message = obj.get("message")
            if isinstance(error_message, dict):
                result["last_turn_api_error_text"] = extract_array_content(
                    error_message.get("content") or []
                )
            continue

        # サイドチェーン（Warmupなど）とisMeta（スラッシュコマンド展開テキスト）はスキップ
        if obj.get("isSidechain") in (True, "true"):
            continue
        if obj.get("isMeta") in (True, "true"):
            continue

        # ターン途中に届いたtask-notificationはuserメッセージにならず、
        # queue-operation（enqueue時点でエージェント完了が確定）や
        # attachment（queued_commandとしてターンへ添付）としてのみ記録されるため、
        # message以外の経路からも完了task-idを収集する
        entry_type = obj.get("type")
        if entry_type == "queue-operation":
            queue_content = obj.get("content")
            if isinstance(queue_content, str):
                background_state["completed"].update(_TASK_ID_RE.findall(queue_content))
        elif entry_type == "attachment":
            attachment = obj.get("attachment")
            if isinstance(attachment, dict):
                attachment_prompt = attachment.get("prompt")
                if isinstance(attachment_prompt, str):
                    background_state["completed"].update(
                        _TASK_ID_RE.findall(attachment_prompt)
                    )

        message = obj.get("message")
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        raw_content = message.get("content")
        # tool_resultのみのメッセージは後段のcontent空チェックでスキップされるため、
        # バックグラウンド作業シグナルはここで収集する
        _collect_background_signals(obj, role, raw_content, background_state)
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
                # 真の会話行（システム扱いでないuser行）でAPIエラー状態をリセットする。
                # <task-notification>はrole=user・非空テキストで到来しis_system_message
                # が真になるため、このガードの内側でリセットしないと復帰済みセッション
                # （エラー後にサブエージェント完了通知だけが続く場合）を誤って
                # 「継続中」のまま扱ってしまう。assistant側はAPIエラー行を上のcontinueで
                # 除外済みなので、ここに到達するassistant行は常に真の会話行でありガード不要。
                result["last_turn_api_error"] = ""
                result["last_turn_api_error_text"] = ""
        elif role == "assistant":
            result["assistant_count"] += 1
            result["last_turn_api_error"] = ""
            result["last_turn_api_error_text"] = ""
    result["pending_background_work"] = _resolve_pending_background_work(
        background_state, result["last_timestamp"]
    )
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
    duration, completion = build_time_fields(
        result["first_timestamp"], result["last_timestamp"]
    )
    print(f"LAST_USER_MESSAGE={shlex.quote(result['last_user_message'])}")
    print(f"USER_MESSAGE_COUNT={result['user_count']}")
    print(f"ASSISTANT_MESSAGE_COUNT={result['assistant_count']}")
    print(f"FIRST_TIMESTAMP={shlex.quote(result['first_timestamp'])}")
    print(f"LAST_TIMESTAMP={shlex.quote(result['last_timestamp'])}")
    print(f"SESSION_DURATION_FORMATTED={shlex.quote(duration)}")
    print(f"COMPLETION_TIME_JST={shlex.quote(completion)}")
    print(f"PENDING_BACKGROUND_WORK={result['pending_background_work']}")
    print(f"LAST_TURN_API_ERROR={shlex.quote(result['last_turn_api_error'])}")
    print(f"LAST_TURN_API_ERROR_TEXT={shlex.quote(result['last_turn_api_error_text'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
