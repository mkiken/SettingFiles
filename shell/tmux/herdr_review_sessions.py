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


def register(agent, session_id, review, output_file=None):
    target = state_path(agent, session_id)
    if target is None:
        return
    try:
        if review:
            target.parent.mkdir(parents=True, exist_ok=True)
            record = [agent, session_id]
            if output_file:
                record.append(os.path.abspath(output_file))
            target.write_text(json.dumps(record), encoding="utf-8")
        else:
            target.unlink(missing_ok=True)
    except OSError:
        pass


def matches(agent, session_id):
    target = state_path(agent, session_id)
    if target is None:
        return False
    try:
        record = json.loads(target.read_text(encoding="utf-8"))
        return isinstance(record, list) and record[:2] == [agent, session_id] and len(record) in (2, 3)
    except (OSError, ValueError):
        return False


def output_matches(agent, session_id, message):
    target = state_path(agent, session_id)
    if target is None:
        return False
    try:
        record = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(record, list) or len(record) != 3 or record[:2] != [agent, session_id]:
            return False
        output = Path(record[2])
        if not output.is_absolute() or output.stat().st_mtime_ns <= target.stat().st_mtime_ns:
            return False
        content = output.read_text(encoding="utf-8").split()
        return bool(content) and content == message.split()
    except (OSError, ValueError, TypeError):
        return False


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "output-matches":
        sys.exit(0 if output_matches(sys.argv[2], sys.argv[3], sys.stdin.read()) else 1)
    sys.exit(0 if len(sys.argv) == 3 and matches(sys.argv[1], sys.argv[2]) else 1)
