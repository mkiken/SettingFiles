import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
HOOK = REPO_ROOT / "ai" / "gemini" / "hooks" / "notification.sh"


def write_executable(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def write_jsonl(path: Path, events: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output:
        for event in events:
            output.write(json.dumps(event) + "\n")


class GeminiNotificationContextTest(unittest.TestCase):
    def test_context_alert_uses_latest_chat_jsonl_and_input_tokens(self):
        session_id = "abcdef12-3456-7890-abcd-ef1234567890"

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            fake_repo = tmp_path / "repo"
            fake_home = tmp_path / "home"

            write_executable(
                fake_repo / "shell" / "zsh" / "alias" / "notification.zsh",
                "notify() { :; }\n",
            )
            write_executable(
                fake_repo / "shell" / "tmux" / "tmux_notification_title.sh",
                "build_notification_title() { echo \"$3$1 $2\"; }\nformat_duration() { echo \"0s\"; }\n",
            )
            write_executable(fake_repo / "shell" / "tmux" / "tmux_window_info.sh", "")
            write_executable(
                fake_repo / "shell" / "tmux" / "tmux_emoji.conf",
                "EMOJI_ID_GEMINI=💎\n",
            )
            write_executable(
                fake_repo / "shell" / "zsh" / "alias" / "context-alert.zsh",
                "ctx_alert_evaluate() { printf '%s\\n' \"$*\" > \"${TMPDIR}/gemini-context-args\"; }\n",
            )

            older_chat = fake_home / ".gemini" / "tmp" / "project" / "chats" / f"session-{session_id[:8]}.jsonl"
            newer_chat = (
                fake_home
                / ".gemini"
                / "tmp"
                / "project"
                / "chats"
                / session_id
                / "latest.jsonl"
            )
            write_jsonl(
                older_chat,
                [
                    {
                        "type": "gemini",
                        "timestamp": "2026-06-27T00:00:00.000Z",
                        "model": "gemini-3.5-flash",
                        "tokens": {"input": 900000, "total": 900100},
                    }
                ],
            )
            write_jsonl(
                newer_chat,
                [
                    {
                        "type": "gemini",
                        "timestamp": "2026-06-27T00:01:00.000Z",
                        "model": "gemini-3.5-flash",
                        "tokens": {"input": 100000, "total": 900000},
                    }
                ],
            )
            os.utime(older_chat, (1000, 1000))
            os.utime(newer_chat, (2000, 2000))

            env = os.environ.copy()
            env.update(
                {
                    "SET": str(fake_repo) + "/",
                    "HOME": str(fake_home),
                    "TMPDIR": str(tmp_path),
                    "TERM_PROGRAM": "",
                    "TMUX_PANE": "",
                }
            )
            hook_input = {"session_id": session_id, "transcript_path": ""}

            result = subprocess.run(
                ["bash", str(HOOK), "--event", "after_agent"],
                input=json.dumps(hook_input),
                text=True,
                env=env,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            args = (tmp_path / "gemini-context-args").read_text(encoding="utf-8").strip().split()
            self.assertEqual(args[0], "gemini")
            self.assertEqual(args[1], session_id)
            self.assertEqual(args[2], "9.5")
            self.assertEqual(args[4], "1048576")
            self.assertEqual(args[5], "100000")


if __name__ == "__main__":
    unittest.main()
