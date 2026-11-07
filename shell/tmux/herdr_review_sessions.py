import hashlib
import json
import os
import sys
from pathlib import Path


def state_path(agent, session_id):
    if agent not in ("claude", "codex") or not isinstance(session_id, str) or not session_id:
        return None
    key = hashlib.sha256(f"{agent}\0{session_id}".encode()).hexdigest()
    return Path.home() / ".cache" / "herdr-review-sessions" / key


def register(agent, session_id, review):
    target = state_path(agent, session_id)
    if target is None:
        return
    try:
        if review:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps([agent, session_id]), encoding="utf-8")
        else:
            target.unlink(missing_ok=True)
    except OSError:
        pass


def matches(agent, session_id):
    target = state_path(agent, session_id)
    if target is None:
        return False
    try:
        return json.loads(target.read_text(encoding="utf-8")) == [agent, session_id]
    except (OSError, ValueError):
        return False


if __name__ == "__main__":
    sys.exit(0 if len(sys.argv) == 3 and matches(sys.argv[1], sys.argv[2]) else 1)
