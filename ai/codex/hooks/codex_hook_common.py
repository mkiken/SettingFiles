#!/usr/bin/env python3
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


QUESTION_SCAN_TAIL_LENGTH = 500
WEBSOCKET_EVENT_MARKER = "websocket event: "


def normalize_message(message: str) -> str:
    return re.sub(r"\s+", " ", message).strip()


def assistant_response_question_scan_text(message: str) -> str:
    stripped = re.sub(r"(?s)(```.*?```|~~~.*?~~~)", " ", message)
    stripped = re.sub(r"`[^`\n]*`", " ", stripped)
    stripped = re.sub(r"\b(?:https?://|www\.)\S+", " ", stripped)
    return normalize_message(stripped)[-QUESTION_SCAN_TAIL_LENGTH:]


def assistant_response_contains_proposed_plan(message: str) -> bool:
    has_line_bounded_block = (
        re.search(r"(?m)^\s*<proposed_plan>\s*$", message) is not None
        and re.search(r"(?m)^\s*</proposed_plan>\s*$", message) is not None
    )
    if has_line_bounded_block:
        return True

    normalized = normalize_message(message)
    return normalized.startswith("<proposed_plan>") and normalized.endswith("</proposed_plan>")


def assistant_response_needs_user_input(message: str) -> bool:
    normalized = normalize_message(message)
    if not normalized:
        return False

    if assistant_response_contains_proposed_plan(message):
        return True

    if re.search(r"[？?]", assistant_response_question_scan_text(message)):
        return True

    if "コミット操作を選択して" in normalized or "コミット方針を指示して" in normalized:
        return True

    if all(option in normalized for option in ("コミットしてプッシュ", "コミットのみ", "コミットしない")):
        return True

    if all(option in normalized for option in ("すべて削除", "個別に選択", "削除しない")):
        return True

    if re.search(r"(選択|指定|指示|返信|返答|回答|入力)して(ください)?[。.!！]*$", normalized):
        return True

    if re.search(r"教えて(ください)?[。.!！]*$", normalized):
        return True

    if re.search(
        r"\d+[.．]\s+\S[^.]{0,80}?\s+[—–]\s+\S.*?\d+[.．]\s+\S[^.]{0,80}?\s+[—–]\s+\S.*?\s*$",
        normalized,
    ):
        return True

    if re.search(
        r"(確認|選択|お選び|選んで|どれ|いずれ)[:：]\s*1[.．]\s+\S.*?\s+2[.．]\s+\S",
        normalized,
    ):
        return True

    if re.search(r"(どうする|どうします|どれにする|どちらにする|続行するか|実行するか|作成するか|削除するか|コミットするか)", normalized):
        return True

    return False


def is_subagent_metadata(data: dict[str, Any]) -> bool:
    source = data.get("source")
    has_subagent_source = isinstance(source, dict) and source.get("subagent") is not None
    return has_subagent_source or bool(data.get("agent_role")) or bool(data.get("agent_nickname"))


def is_system_user_message(message: str) -> bool:
    if message.startswith("# AGENTS.md instructions for"):
        return True
    if message.startswith("<environment_context>"):
        return True
    if message.startswith("<command-message>"):
        return True
    if message.startswith("/"):
        return False
    if re.match(r"\s*<(system-reminder|user-prompt-submit-hook|tool-result|antml)", message):
        return True
    if message.startswith("Caveat:"):
        return True
    return len(message) < 4


def iter_transcript_events(transcript_path: str | None):
    if not transcript_path or transcript_path == "null":
        return

    path = Path(transcript_path)
    if not path.is_file():
        return

    try:
        with path.open(encoding="utf-8") as transcript:
            for line in transcript:
                if not line.strip():
                    continue

                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    except Exception:
        return


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def format_epoch_timestamp(epoch_seconds: int | float | None) -> str:
    if epoch_seconds is None:
        return ""

    try:
        return datetime.fromtimestamp(epoch_seconds, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    except (OSError, OverflowError, ValueError, TypeError):
        return ""


def find_session_transcript_path(session_id: str | None) -> str | None:
    if not session_id:
        return None

    sessions_dir = codex_home() / "sessions"
    if not sessions_dir.is_dir():
        return None

    try:
        candidates = [path for path in sessions_dir.rglob(f"*{session_id}.jsonl") if path.is_file()]
    except OSError:
        return None

    if not candidates:
        return None

    try:
        candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    except OSError:
        candidates.sort()

    return str(candidates[0])


def resolve_transcript_path(input_data: dict[str, Any]) -> str | None:
    transcript_path = input_data.get("transcript_path")
    if transcript_path and transcript_path != "null" and Path(str(transcript_path)).is_file():
        return str(transcript_path)

    return find_session_transcript_path(input_data.get("session_id"))


def extract_message_text(payload: dict[str, Any]) -> str:
    content = payload.get("content")
    if not isinstance(content, list):
        return ""

    parts = [
        item.get("text", "")
        for item in content
        if isinstance(item, dict) and item.get("type") in {"input_text", "output_text"}
    ]
    return normalize_message(" ".join(parts))


def iter_history_user_messages(session_id: str | None):
    if not session_id:
        return

    history_path = codex_home() / "history.jsonl"
    if not history_path.is_file():
        return

    try:
        with history_path.open(encoding="utf-8") as history:
            for line in history:
                if not line.strip():
                    continue

                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if event.get("session_id") != session_id:
                    continue

                text = normalize_message(str(event.get("text") or ""))
                if text and not is_system_user_message(text):
                    yield format_epoch_timestamp(event.get("ts")), text
    except Exception:
        return


def decode_websocket_event(log_body: str) -> dict[str, Any] | None:
    marker_index = log_body.find(WEBSOCKET_EVENT_MARKER)
    if marker_index < 0:
        return None

    json_text = log_body[marker_index + len(WEBSOCKET_EVENT_MARKER) :]
    try:
        event, _ = json.JSONDecoder().raw_decode(json_text)
    except json.JSONDecodeError:
        return None

    return event if isinstance(event, dict) else None


def iter_log_assistant_messages(session_id: str | None):
    if not session_id:
        return

    logs_path = codex_home() / "logs_2.sqlite"
    if not logs_path.is_file():
        return

    try:
        connection = sqlite3.connect(f"file:{logs_path}?mode=ro", uri=True, timeout=0.2)
    except sqlite3.Error:
        return

    try:
        cursor = connection.execute(
            """
            SELECT ts, feedback_log_body
            FROM logs
            WHERE thread_id = ?
              AND feedback_log_body LIKE ?
            ORDER BY ts, ts_nanos, id
            """,
            (session_id, f"%{WEBSOCKET_EVENT_MARKER}%response.output_text.done%"),
        )

        for ts, log_body in cursor:
            if not isinstance(log_body, str):
                continue

            event = decode_websocket_event(log_body)
            if not event or event.get("type") != "response.output_text.done":
                continue

            text = normalize_message(str(event.get("text") or ""))
            if text:
                yield format_epoch_timestamp(ts), text
    except sqlite3.Error:
        return
    finally:
        connection.close()


def analyze_hook_input(input_data: dict[str, Any]) -> dict[str, Any]:
    session_id = input_data.get("session_id")
    transcript_path = resolve_transcript_path(input_data)
    user_messages: list[str] = []
    assistant_messages: list[str] = []
    first_timestamp = ""
    last_timestamp = ""
    has_subagent_session_meta = False

    for event in iter_transcript_events(transcript_path):
        if event.get("type") != "session_meta":
            timestamp = event.get("timestamp")
            if timestamp:
                if not first_timestamp:
                    first_timestamp = timestamp
                last_timestamp = timestamp

        if event.get("type") == "session_meta":
            payload = event.get("payload")
            if isinstance(payload, dict) and is_subagent_metadata(payload):
                has_subagent_session_meta = True
            continue

        if event.get("type") != "response_item":
            continue

        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        if payload.get("type") != "message":
            continue

        role = payload.get("role")
        if role == "developer":
            continue

        message_text = extract_message_text(payload)
        if not message_text:
            continue

        if role == "user":
            if not is_system_user_message(message_text):
                user_messages.append(message_text)
        elif role == "assistant":
            assistant_messages.append(message_text)

    if not user_messages and not assistant_messages:
        for timestamp, message_text in iter_history_user_messages(session_id):
            if timestamp:
                if not first_timestamp:
                    first_timestamp = timestamp
                last_timestamp = timestamp
            user_messages.append(message_text)

        for timestamp, message_text in iter_log_assistant_messages(session_id):
            if timestamp:
                if not first_timestamp:
                    first_timestamp = timestamp
                last_timestamp = timestamp
            assistant_messages.append(message_text)

    last_assistant_message = assistant_messages[-1] if assistant_messages else ""
    is_subagent = is_subagent_metadata(input_data) or has_subagent_session_meta

    return {
        "is_subagent_session": is_subagent,
        "waiting_for_user_response": assistant_response_needs_user_input(last_assistant_message),
        "last_user_message": user_messages[-1] if user_messages else "",
        "last_assistant_message": last_assistant_message,
        "user_message_count": len(user_messages),
        "assistant_message_count": len(assistant_messages),
        "first_timestamp": first_timestamp,
        "last_timestamp": last_timestamp,
    }


def is_subagent_session(input_data: dict[str, Any]) -> bool:
    return bool(analyze_hook_input(input_data)["is_subagent_session"])


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] != "analyze":
        print("usage: codex_hook_common.py analyze", file=sys.stderr)
        return 2

    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"invalid hook input JSON: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(analyze_hook_input(input_data), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
