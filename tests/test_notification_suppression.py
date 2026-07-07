import json
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


REPO_ROOT = Path(__file__).resolve().parents[1]
SYSTEM_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"


class NotificationSuppressionTest(unittest.TestCase):
    def run_notify(self, extra_env: dict[str, str]) -> tuple[subprocess.CompletedProcess[str], Path]:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)

        root = Path(temp_dir.name)
        fake_bin = root / "bin"
        fake_bin.mkdir()
        log_path = root / "terminal-notifier.log"
        notifier = fake_bin / "terminal-notifier"
        notifier.write_text(
            "#!/bin/sh\n"
            'echo called >> "$NOTIFY_TEST_LOG"\n'
            "exit 0\n",
            encoding="utf-8",
        )
        notifier.chmod(notifier.stat().st_mode | stat.S_IXUSR)

        env = {
            "HOME": str(root),
            "PATH": f"{fake_bin}:{SYSTEM_PATH}",
            "NOTIFY_TEST_LOG": str(log_path),
        }
        env.update(extra_env)

        result = subprocess.run(
            [
                "zsh",
                "-fc",
                "source shell/zsh/alias/notification.zsh; notify title message default group",
            ],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        return result, log_path

    def assert_notify_suppressed(self, extra_env: dict[str, str]) -> None:
        result, log_path = self.run_notify(extra_env)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(log_path.exists())

    def test_notify_suppresses_when_disable_notify_is_set(self):
        self.assert_notify_suppressed({"DISABLE_NOTIFY": "1"})

    def test_notify_suppresses_during_codex_sessions(self):
        self.assert_notify_suppressed({"CODEX_CI": "1"})
        self.assert_notify_suppressed({"CODEX_THREAD_ID": "session-id"})

    def test_notify_calls_terminal_notifier_without_suppression_context(self):
        result, log_path = self.run_notify({})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(log_path.read_text(encoding="utf-8"), "called\n")

    def test_notify_force_bypasses_ai_suppression(self):
        result, log_path = self.run_notify(
            {
                "NOTIFY_FORCE": "1",
                "DISABLE_NOTIFY": "1",
                "_DISABLE_NOTIFY_FOR_CURRENT_CMD": "1",
                "CODEX_THREAD_ID": "session-id",
            }
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(log_path.read_text(encoding="utf-8"), "called\n")

    def test_notification_hooks_force_intentional_notifications(self):
        for script_path in (
            "ai/claude/hooks/stop-send-notification.sh",
            "ai/codex/hooks/codex-stop-notification.sh",
            "ai/gemini/hooks/notification.sh",
        ):
            with self.subTest(script=script_path):
                script = (REPO_ROOT / script_path).read_text(encoding="utf-8")
                self.assertIn("export NOTIFY_FORCE=1", script)

    @unittest.skipIf(tomllib is None, "tomllib requires Python 3.11+")
    def test_codex_subprocesses_inherit_notification_suppression(self):
        config = tomllib.loads((REPO_ROOT / "ai/codex/config.toml").read_text(encoding="utf-8"))

        self.assertEqual(
            config["shell_environment_policy"]["set"]["DISABLE_NOTIFY"],
            "1",
        )

    def test_claude_settings_disable_notifications_for_ai_processes(self):
        settings = json.loads((REPO_ROOT / "ai/claude/settings.json").read_text(encoding="utf-8"))

        self.assertEqual(settings["env"]["DISABLE_NOTIFY"], "1")

    def test_gemini_settings_disable_notifications_for_ai_processes(self):
        settings = json.loads((REPO_ROOT / "ai/gemini/settings.json").read_text(encoding="utf-8"))

        self.assertTrue(settings["general"]["enableNotifications"])
        self.assertIn("DISABLE_NOTIFY=1", (REPO_ROOT / "ai/gemini/.env").read_text(encoding="utf-8"))

        for script_path in (
            "mac/initialization/ai/gemini.sh",
            "mac/updates/gemini.sh",
        ):
            with self.subTest(script=script_path):
                script = (REPO_ROOT / script_path).read_text(encoding="utf-8")
                self.assertIn('make_symlink "${Repo}ai/gemini/.env" ~/.gemini/.env', script)


if __name__ == "__main__":
    unittest.main()
