import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class HerdrNotificationTest(unittest.TestCase):
    def run_hook(self, command: list[str], hook_input: str = "{") -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["HERDR_ENV"] = "1"
        return subprocess.run(
            command,
            cwd=REPO_ROOT,
            env=env,
            input=hook_input,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_claude_and_codex_completion_hooks_exit_early_in_herdr(self) -> None:
        hooks = (
            ["bash", str(REPO_ROOT / "ai/claude/hooks/stop-send-notification.sh")],
            ["bash", str(REPO_ROOT / "ai/codex/hooks/codex-stop-notification.sh")],
        )
        for command in hooks:
            with self.subTest(hook=command[-1]):
                result = self.run_hook(command)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "")

    def test_tmux_icon_hooks_exit_early_in_herdr(self) -> None:
        hooks = (
            REPO_ROOT / "ai/claude/hooks/claude-hook.py",
            REPO_ROOT / "ai/gemini/hooks/gemini-hook.py",
            REPO_ROOT / "ai/codex/hooks/codex-hook.py",
        )
        for hook in hooks:
            with self.subTest(hook=hook):
                result = self.run_hook([sys.executable, str(hook)])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, "")

    def test_codex_icon_hook_still_processes_input_outside_herdr(self) -> None:
        env = os.environ.copy()
        env.pop("HERDR_ENV", None)
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "ai/codex/hooks/codex-hook.py")],
            cwd=REPO_ROOT,
            env=env,
            input="{",
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid hook input JSON", result.stderr)

    def test_gemini_keeps_context_alert_but_skips_native_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fake_repo = root / "repo"
            fake_home = root / "home"
            chat_dir = fake_home / ".gemini/tmp/project/chats/session-abcdefgh"
            chat_dir.mkdir(parents=True)
            chat_path = chat_dir / "latest.jsonl"
            chat_path.write_text(
                json.dumps(
                    {
                        "type": "gemini",
                        "timestamp": "2026-07-20T00:00:00Z",
                        "model": "gemini-3.5-flash",
                        "tokens": {"input": 100000, "total": 100100},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            transcript_path = root / "transcript.jsonl"
            transcript_path.write_text(
                json.dumps(
                    {
                        "type": "user",
                        "timestamp": "2026-07-20T00:00:00Z",
                        "content": "heavy summary must not run",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            dependencies = {
                "shell/zsh/alias/notification.zsh": 'notify() { echo notify >> "$HERDR_TEST_EVENTS"; }\n',
                "shell/tmux/tmux_emoji.conf": "EMOJI_ID_GEMINI=gemini\nEMOJI_STATUS_NOTIFICATION=wait\nEMOJI_STATUS_COMPLETED=done\n",
                "shell/tmux/tmux_window_info.sh": "",
                "shell/tmux/tmux_notification_title.sh": 'build_notification_title() { echo title >> "$HERDR_TEST_EVENTS"; echo "$2"; }\nformat_duration() { :; }\n',
                "shell/tmux/tmux_window_name.sh": 'update_tmux_window_name() { echo icon >> "$HERDR_TEST_EVENTS"; }\n',
                "shell/zsh/alias/context-alert.zsh": 'ctx_alert_evaluate() { echo context >> "$HERDR_TEST_EVENTS"; }\n',
            }
            for relative_path, content in dependencies.items():
                file_path = fake_repo / relative_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding="utf-8")

            for relative_path in (
                "shell/tmux/ai_notification_hook_common.sh",
                "shell/tmux/ai_notification_summary.sh",
                "shell/tmux/gemini_context_usage.py",
                "shell/tmux/gemini_transcript_summary.jq",
            ):
                destination = fake_repo / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(REPO_ROOT / relative_path, destination)

            events = root / "events"
            fake_bin = root / "bin"
            fake_bin.mkdir()
            real_jq = shutil.which("jq")
            self.assertIsNotNone(real_jq)
            fake_jq = fake_bin / "jq"
            fake_jq.write_text(
                "#!/bin/bash\n"
                "for arg in \"$@\"; do\n"
                "  case \"$arg\" in\n"
                "    *gemini_transcript_summary.jq) echo summary >> \"$HERDR_TEST_EVENTS\" ;;\n"
                "  esac\n"
                "done\n"
                f'exec "{real_jq}" "$@"\n',
                encoding="utf-8",
            )
            fake_jq.chmod(0o755)
            env = os.environ.copy()
            env.update(
                {
                    "HERDR_ENV": "1",
                    "HERDR_TEST_EVENTS": str(events),
                    "SET": str(fake_repo) + "/",
                    "HOME": str(fake_home),
                    "PATH": f"{fake_bin}:{env['PATH']}",
                    "TERM_PROGRAM": "",
                    "TMUX_PANE": "",
                }
            )
            result = subprocess.run(
                ["bash", str(REPO_ROOT / "ai/gemini/hooks/notification.sh"), "--event", "after_agent"],
                cwd=REPO_ROOT,
                env=env,
                input=json.dumps(
                    {
                        "session_id": "abcdefgh-session",
                        "transcript_path": str(transcript_path),
                    }
                ),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(events.read_text(encoding="utf-8").splitlines(), ["context"])


if __name__ == "__main__":
    unittest.main()
