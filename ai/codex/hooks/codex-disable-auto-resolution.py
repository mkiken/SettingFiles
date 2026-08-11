#!/usr/bin/env python3
"""Keep Codex structured questions open until the user explicitly answers."""

import json
import sys


def remove_auto_resolution(payload: object) -> dict | None:
    if not isinstance(payload, dict):
        return None

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict) or "autoResolutionMs" not in tool_input:
        return None

    updated_input = dict(tool_input)
    del updated_input["autoResolutionMs"]
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": updated_input,
        }
    }


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return 0

    output = remove_auto_resolution(payload)
    if output is not None:
        print(json.dumps(output, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
