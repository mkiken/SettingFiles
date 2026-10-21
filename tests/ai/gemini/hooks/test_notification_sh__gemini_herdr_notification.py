import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


from support import REPO_ROOT, sanitized_env
HOOK_SCRIPT = REPO_ROOT / "ai/gemini/hooks/notification.sh"


class GeminiHerdrNotificationTest(unittest.TestCase):
    """ai/gemini/hooks/notification.sh のHerdr下ガード緩和ロジックの単体テスト。

    Geminiはnotify-richプラグイン(terminal/herdr/plugins/notify-rich)から完全に
    opt-outし、Herdr環境でもこのフックのAfterAgent/Notificationイベントで通知する
    (see terminal/herdr/plugins/notify-rich/notify-on-agent-status.sh の
    agent=="gemini" ガード)。タブ名のアイコンもnotify-richが書かないため、Herdr下では
    tmux版の代わりにupdate_herdr_tab_icon（Herdrタブ名）をこのフックが呼ぶ。
    """

    def run_hook(
        self,
        *,
        event: str,
        hook_input: dict,
        in_herdr: bool,
        review_output: str | None = None,
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
                    'update_herdr_tab_icon() { echo "herdr-icon:$1:$2" >> "$HERDR_TEST_EVENTS"; }\n'
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

            env = sanitized_env(
                {
                    "HERDR_TEST_EVENTS": str(events),
                    "SET": str(fake_repo) + "/",
                    "HOME": str(fake_home),
                    "TERM_PROGRAM": "",
                    "TMUX_PANE": "",
                }
            )
            env.pop("AI_REVIEW_OUTPUT_FILE", None)
            if review_output is not None:
                env["AI_REVIEW_OUTPUT_FILE"] = review_output
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
        for review_output in (None, ""):
            with self.subTest(review_output=review_output):
                result, events = self.run_hook(
                    event="after_agent",
                    hook_input={"session_id": "abcdefgh-session"},
                    in_herdr=True,
                    review_output=review_output,
                )

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("notify", events)
                # tmux icon is meaningless under Herdr; the Herdr tab icon is set instead.
                self.assertFalse(any(line.startswith("icon:") for line in events))
                self.assertIn("herdr-icon:done:gemini", events)

    def test_review_after_agent_skips_notification_under_herdr(self):
        for review_output in ("/tmp/review.json", "/tmp/review output/result.json"):
            with self.subTest(review_output=review_output):
                result, events = self.run_hook(
                    event="after_agent",
                    hook_input={"session_id": "abcdefgh-session"},
                    in_herdr=True,
                    review_output=review_output,
                )

                self.assertEqual(result.returncode, 0, result.stderr)
                # Review completion belongs to the caller, so no title or notification is built.
                self.assertEqual(events, [])

    def test_after_agent_notifies_and_sets_icon_outside_herdr(self):
        result, events = self.run_hook(
            event="after_agent",
            hook_input={"session_id": "abcdefgh-session"},
            in_herdr=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("notify", events)
        self.assertIn("icon:done", events)
        self.assertFalse(any(line.startswith("herdr-icon:") for line in events))

    def test_notification_toolpermission_notifies_under_herdr(self):
        result, events = self.run_hook(
            event="notification",
            hook_input={"notification_type": "ToolPermission", "session_id": "abcdefgh-session"},
            in_herdr=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("notify", events)
        self.assertFalse(any(line.startswith("icon:") for line in events))
        self.assertIn("herdr-icon:wait:gemini", events)

    def test_review_toolpermission_notifies_under_herdr(self):
        result, events = self.run_hook(
            event="notification",
            hook_input={"notification_type": "ToolPermission", "session_id": "abcdefgh-session"},
            in_herdr=True,
            review_output="/tmp/review.json",
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

    def test_toolpermission_sets_tmux_icon_not_herdr_icon_outside_herdr(self):
        result, events = self.run_hook(
            event="notification",
            hook_input={"notification_type": "ToolPermission", "session_id": "abcdefgh-session"},
            in_herdr=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("icon:wait", events)
        self.assertFalse(any(line.startswith("herdr-icon:") for line in events))


if __name__ == "__main__":
    unittest.main()
