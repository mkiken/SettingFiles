import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
HOOK = REPO_ROOT / "ai" / "codex" / "hooks" / "codex-context-alert.sh"


def write_jsonl(path: Path, events: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output:
        for event in events:
            output.write(json.dumps(event) + "\n")


class CodexContextAlertHookTest(unittest.TestCase):
    def test_low_context_usage_clears_existing_alert_state(self):
        session_id = "test-session"

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            transcript_path = tmp_path / "sessions" / f"rollout-{session_id}.jsonl"
            write_jsonl(
                transcript_path,
                [
                    {
                        "type": "event_msg",
                        "payload": {
                            "type": "token_count",
                            "info": {
                                "total_token_usage": {"total_tokens": 774025},
                                "last_token_usage": {"total_tokens": 46950},
                                "model_context_window": 258400,
                            },
                        },
                    }
                ],
            )

            state_dir = tmp_path / "ai-context-alert"
            state_dir.mkdir()
            state_path = state_dir / f"codex-{session_id}.state"
            state_path.write_text("70 78\n", encoding="utf-8")

            env = os.environ.copy()
            env.update(
                {
                    "SET": str(REPO_ROOT) + "/",
                    "TMPDIR": str(tmp_path),
                    "TERM_PROGRAM": "",
                    "TMUX_PANE": "",
                }
            )
            hook_input = {
                "hook_event_name": "PostToolUse",
                "session_id": session_id,
                "transcript_path": str(transcript_path),
            }

            result = subprocess.run(
                ["bash", str(HOOK)],
                input=json.dumps(hook_input),
                text=True,
                env=env,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(state_path.read_text(encoding="utf-8").strip(), "0 14")


if __name__ == "__main__":
    unittest.main()
