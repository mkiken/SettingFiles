"""Tests for the Codex question auto-resolution suppression hook."""

import json
import subprocess
import sys
import unittest

from support import REPO_ROOT


HOOK = REPO_ROOT / "ai" / "codex" / "hooks" / "codex-disable-auto-resolution.py"
HOOK_CONFIG = REPO_ROOT / "ai" / "codex" / "hooks.json"


def run_hook(payload: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        check=False,
    )


class TestCodexDisableAutoResolution(unittest.TestCase):
    def test_removes_auto_resolution_and_preserves_question_input(self):
        payload = {
            "tool_input": {
                "autoResolutionMs": 60_000,
                "questions": [{"id": "scope", "header": "対象", "options": []}],
                "isBlocking": True,
            }
        }

        result = run_hook(json.dumps(payload))

        self.assertEqual(result.returncode, 0)
        output = json.loads(result.stdout)
        self.assertEqual(
            output["hookSpecificOutput"],
            {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "updatedInput": {
                    "questions": payload["tool_input"]["questions"],
                    "isBlocking": True,
                },
            },
        )

    def test_without_auto_resolution_emits_no_rewrite(self):
        result = run_hook(json.dumps({"tool_input": {"questions": []}}))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_invalid_json_is_a_noop(self):
        result = run_hook("{invalid")

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_hook_registration_matches_only_structured_questions(self):
        config = json.loads(HOOK_CONFIG.read_text(encoding="utf-8"))
        groups = config["hooks"]["PreToolUse"]
        group = next(group for group in groups if group.get("matcher") == "request_user_input")

        self.assertEqual(
            group["hooks"],
            [
                {
                    "command": "python3 ~/.codex/hooks/codex-disable-auto-resolution.py",
                    "timeout": 5,
                    "type": "command",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
