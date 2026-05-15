#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path
from typing import Any


def normalize_message(message: str) -> str:
    return re.sub(r"\s+", " ", message).strip()


def assistant_response_needs_user_input(message: str) -> bool:
    normalized = normalize_message(message)
    if not normalized:
        return False

    if re.search(r"[？?]\s*$", normalized):
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


def analyze_hook_input(input_data: dict[str, Any]) -> dict[str, Any]:
    transcript_path = input_data.get("transcript_path")
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
