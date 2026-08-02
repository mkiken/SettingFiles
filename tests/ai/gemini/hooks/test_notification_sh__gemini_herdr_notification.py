import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


from support import REPO_ROOT
HOOK_SCRIPT = REPO_ROOT / "ai/gemini/hooks/notification.sh"


class GeminiHerdrNotificationTest(unittest.TestCase):
    """ai/gemini/hooks/notification.sh のHerdr下ガード緩和ロジックの単体テスト。

    Geminiはnotify-richプラグイン(terminal/herdr/plugins/notify-rich)から完全に
    opt-outし、Herdr環境でもこのフックのAfterAgent/Notificationイベントで通知する
    (see terminal/herdr/plugins/notify-rich/notify-on-agent-status.sh の
    agent=="gemini" ガード)。tmuxアイコンだけはHerdr下では無意味なので抑止される。
    """

    def run_hook(
        self,
        *,
        event: str,
        hook_input: dict,
        in_herdr: bool,
    ) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fake_repo = root / "repo"
            fake_home = root / "home"
            fake_home.mkdir(parents=True)
            events = root / "events"

            dependencies = {
                "shell/zsh/alias/notification.zsh": 'notify() { echo notify >> "$HERDR_TEST_EVENTS"; }\n',
                "shell/tmux/tmux_emoji.conf": (
                    "EMOJI_ID_GEMINI=gemini\n"
                    "EMOJI_STATUS_NOTIFICATION=wait\n"
                    "EMOJI_STATUS_COMPLETED=done\n"
                ),
                "shell/tmux/tmux_window_info.sh": "",
                "shell/tmux/tmux_notification_title.sh": (
                    'build_notification_title() { echo title >> "$HERDR_TEST_EVENTS"; echo "$2"; }\n'
                    "format_duration() { :; }\n"
                ),
                "shell/tmux/tmux_window_name.sh": (
                    'update_tmux_window_name() { echo "icon:$1" >> "$HERDR_TEST_EVENTS"; }\n'
                ),
            }
            for relative_path, content in dependencies.items():
                file_path = fake_repo / relative_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding="utf-8")

            for relative_path in (
                "shell/tmux/ai_notification_hook_common.sh",
                "shell/tmux/ai_notification_summary.sh",
                # 共通ヘッダが source する音マップ（イベント種別→音名）。
                "shell/tmux/ai_notification_sound.sh",
                "shell/tmux/gemini_context_usage.py",
                "shell/tmux/gemini_transcript_summary.jq",
            ):
                destination = fake_repo / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(REPO_ROOT / relative_path, destination)

            env = os.environ.copy()
            env.update(
                {
                    "HERDR_TEST_EVENTS": str(events),
                    "SET": str(fake_repo) + "/",
                    "HOME": str(fake_home),
                    "TERM_PROGRAM": "",
                    "TMUX_PANE": "",
                }
            )
            if in_herdr:
                env["HERDR_ENV"] = "1"
            else:
                env.pop("HERDR_ENV", None)

            result = subprocess.run(
                ["bash", str(HOOK_SCRIPT), "--event", event],
                cwd=REPO_ROOT,
                env=env,
                input=json.dumps(hook_input),
                text=True,
                capture_output=True,
                check=False,
            )
            event_lines = events.read_text(encoding="utf-8").splitlines() if events.exists() else []
            return result, event_lines

    def test_after_agent_notifies_under_herdr(self):
        result, events = self.run_hook(
            event="after_agent",
            hook_input={"session_id": "abcdefgh-session"},
            in_herdr=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("notify", events)
        # tmux icon is meaningless under Herdr (no tmux window) and must be skipped.
        self.assertFalse(any(line.startswith("icon:") for line in events))

    def test_after_agent_notifies_and_sets_icon_outside_herdr(self):
        result, events = self.run_hook(
            event="after_agent",
            hook_input={"session_id": "abcdefgh-session"},
            in_herdr=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("notify", events)
        self.assertIn("icon:done", events)

    def test_notification_toolpermission_notifies_under_herdr(self):
        result, events = self.run_hook(
            event="notification",
            hook_input={"notification_type": "ToolPermission", "session_id": "abcdefgh-session"},
            in_herdr=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("notify", events)
        self.assertFalse(any(line.startswith("icon:") for line in events))

    def test_notification_non_toolpermission_suppressed_under_herdr(self):
        # The ToolPermission filter must still gate notifications even though the
        # IN_HERDR guard around it was relaxed.
        result, events = self.run_hook(
            event="notification",
            hook_input={"notification_type": "AgentIdle", "session_id": "abcdefgh-session"},
            in_herdr=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(events, [])


if __name__ == "__main__":
    unittest.main()
