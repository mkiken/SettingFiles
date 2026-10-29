#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ai/codex/hooks"))
from codex_hook_common import find_session_transcript_path


def session(pane):
    value = pane.get("agent_session") or {}
    return value.get("value") if pane.get("agent") == "codex" and isinstance(value, dict) else None


def last_completion(session_id):
    path = find_session_transcript_path(session_id)
    if not path:
        return None
    try:
        with open(path, "rb") as log:
            log.seek(0, 2)
            position = log.tell()
            pending = b""
            first = True
            while position:
                size = min(position, 65536)
                position -= size
                log.seek(position)
                parts = (log.read(size) + pending).split(b"\n")
                pending = parts.pop(0) if position else b""
                if first:
                    parts.pop()  # A non-terminated final record may still be written.
                    first = False
                for line in reversed(parts):
                    try:
                        record = json.loads(line)
                        payload = record.get("payload", {})
                        if record.get("type") == "event_msg" and payload.get("type") == "task_complete":
                            value = payload.get("completed_at")
                            if isinstance(value, (int, float)) and not isinstance(value, bool):
                                datetime.fromtimestamp(value)
                                return value
                    except (ValueError, TypeError, AttributeError, OverflowError, OSError):
                        continue
    except OSError:
        return None
    return None


def main():
    cli = os.environ.get("HERDR_BIN_PATH") or "herdr"

    def call(*args):
        result = subprocess.run([cli, *args], capture_output=True, check=True, timeout=1)
        return json.loads(result.stdout) if result.stdout.strip() else {}

    panes = call("pane", "list")["result"]["panes"]
    now = time.time()
    selected = os.environ.get("HERDR_PANE_ID")
    output = ""
    for pane in panes:
        sid = session(pane)
        pane_id = pane.get("pane_id")
        if not sid or not pane_id:
            continue
        completed = last_completion(sid)
        if completed is None:
            if pane.get("tokens", {}).get("codex_last_response"):
                current = call("pane", "get", pane_id)["result"]["pane"]
                if session(current) == sid:
                    call("pane", "report-metadata", pane_id, "--source", "codex-response-time", "--clear-token", "codex_last_response")
            continue
        value = "📩" + datetime.fromtimestamp(completed).strftime("%m/%d %H:%M")
        needs_report = pane.get("tokens", {}).get("codex_last_response") != value or int(now) % 10 == 0
        is_selected = pane_id == selected or (not selected and pane.get("focused"))
        if needs_report or is_selected:
            current = call("pane", "get", pane_id)["result"]["pane"]
            if session(current) != sid:
                continue
        if needs_report:
            call("pane", "report-metadata", pane_id, "--source", "codex-response-time", "--agent", "codex", "--token", "codex_last_response=" + value, "--ttl-ms", "30000")
        if is_selected:
            elapsed = max(0, int(now - completed))
            hours, rest = divmod(elapsed, 3600)
            minutes, seconds = divmod(rest, 60)
            output = "📩" + (f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}")
    print(output)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, AttributeError, subprocess.SubprocessError):
        print("")
