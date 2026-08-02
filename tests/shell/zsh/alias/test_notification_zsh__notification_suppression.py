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


from support import REPO_ROOT
SYSTEM_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"


DEFAULT_NOTIFY_COMMAND = "source shell/zsh/alias/notification.zsh; notify title message default group"

ICON_STUB = 'update_tmux_window_name() { echo "icon:$1" >> "$ICON_TEST_LOG"; }'
HERDR_ICON_STUB = 'update_herdr_status_icon() { echo "herdr-icon:$1" >> "$HERDR_ICON_TEST_LOG"; }'


class NotificationSuppressionTest(unittest.TestCase):
    def run_notify(
        self,
        extra_env: dict[str, str],
        zsh_command: str = DEFAULT_NOTIFY_COMMAND,
    ) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
        result, log_path, icon_log_path, _herdr_icon_log_path = self.run_notify_full(
            extra_env, zsh_command
        )
        return result, log_path, icon_log_path

    def run_notify_full(
        self,
        extra_env: dict[str, str],
        zsh_command: str = DEFAULT_NOTIFY_COMMAND,
    ) -> tuple[subprocess.CompletedProcess[str], Path, Path, Path]:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)

        root = Path(temp_dir.name)
        fake_bin = root / "bin"
        fake_bin.mkdir()
        log_path = root / "terminal-notifier.log"
        icon_log_path = root / "tmux-icon.log"
        herdr_icon_log_path = root / "herdr-icon.log"
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
            "ICON_TEST_LOG": str(icon_log_path),
            "HERDR_ICON_TEST_LOG": str(herdr_icon_log_path),
        }
        env.update(extra_env)

        result = subprocess.run(
            ["zsh", "-fc", zsh_command],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        return result, log_path, icon_log_path, herdr_icon_log_path

    def assert_notify_suppressed(self, extra_env: dict[str, str]) -> None:
        result, log_path, _ = self.run_notify(extra_env)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(log_path.exists())

    def test_notify_suppresses_when_disable_notify_is_set(self):
        self.assert_notify_suppressed({"DISABLE_NOTIFY": "1"})

    def test_notify_suppresses_during_codex_sessions(self):
        self.assert_notify_suppressed({"CODEX_CI": "1"})
        self.assert_notify_suppressed({"CODEX_THREAD_ID": "session-id"})

    def test_notify_calls_terminal_notifier_without_suppression_context(self):
        result, log_path, _ = self.run_notify({})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(log_path.read_text(encoding="utf-8"), "called\n")

    def test_notify_force_bypasses_ai_suppression(self):
        result, log_path, _ = self.run_notify(
            {
                "NOTIFY_FORCE": "1",
                "DISABLE_NOTIFY": "1",
                "_DISABLE_NOTIFY_FOR_CURRENT_CMD": "1",
                "CODEX_THREAD_ID": "session-id",
            }
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(log_path.read_text(encoding="utf-8"), "called\n")

    def test_notify_tmux_icon_sets_icon_and_notifies(self):
        result, log_path, icon_log_path = self.run_notify(
            {},
            "source shell/zsh/alias/notification.zsh; "
            f"{ICON_STUB}; "
            "notify --tmux-icon ✋ title message default group",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(icon_log_path.read_text(encoding="utf-8"), "icon:✋\n")
        self.assertEqual(log_path.read_text(encoding="utf-8"), "called\n")

    def test_notify_tmux_icon_sets_icon_even_when_suppressed(self):
        result, log_path, icon_log_path = self.run_notify(
            {"DISABLE_NOTIFY": "1"},
            "source shell/zsh/alias/notification.zsh; "
            f"{ICON_STUB}; "
            "notify --tmux-icon ✋ title message default group",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(icon_log_path.read_text(encoding="utf-8"), "icon:✋\n")
        self.assertFalse(log_path.exists())

    def test_notify_without_icon_option_skips_icon(self):
        result, log_path, icon_log_path = self.run_notify(
            {},
            "source shell/zsh/alias/notification.zsh; "
            f"{ICON_STUB}; "
            "notify title message default group",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(icon_log_path.exists())
        self.assertEqual(log_path.read_text(encoding="utf-8"), "called\n")

    def test_notify_tmux_icon_also_sets_herdr_icon_under_herdr(self):
        # HERDR_ENV=1でTMUX未設定ならHerdr反映も行う（tmuxとHerdrは排他だが、
        # notify()呼び出し側は環境を意識せず同じ--tmux-iconを渡すだけでよい）。
        result, log_path, icon_log_path, herdr_icon_log_path = self.run_notify_full(
            {"HERDR_ENV": "1"},
            "source shell/zsh/alias/notification.zsh; "
            f"{ICON_STUB}; {HERDR_ICON_STUB}; "
            "notify --tmux-icon ✋ title message default group",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(herdr_icon_log_path.read_text(encoding="utf-8"), "herdr-icon:✋\n")
        self.assertEqual(log_path.read_text(encoding="utf-8"), "called\n")

    def test_notify_tmux_icon_herdr_also_fires_when_suppressed(self):
        result, _log_path, _icon_log_path, herdr_icon_log_path = self.run_notify_full(
            {"HERDR_ENV": "1", "DISABLE_NOTIFY": "1"},
            "source shell/zsh/alias/notification.zsh; "
            f"{ICON_STUB}; {HERDR_ICON_STUB}; "
            "notify --tmux-icon ✋ title message default group",
        )

        self.assertEqual(herdr_icon_log_path.read_text(encoding="utf-8"), "herdr-icon:✋\n")

    def test_notify_tmux_icon_skips_herdr_without_herdr_env(self):
        # HERDR_ENV/HERDR_PANE_IDともに未設定なら（=tmux環境やその他）Herdr側は呼ばない
        result, _log_path, _icon_log_path, herdr_icon_log_path = self.run_notify_full(
            {},
            "source shell/zsh/alias/notification.zsh; "
            f"{ICON_STUB}; {HERDR_ICON_STUB}; "
            "notify --tmux-icon ✋ title message default group",
        )

        self.assertFalse(herdr_icon_log_path.exists())

    def test_notify_tmux_icon_herdr_without_helper_still_notifies(self):
        # herdr_status_icon.sh フォールバックパスが存在しない（HOMEがtemp root）
        result, log_path, _icon_log_path, herdr_icon_log_path = self.run_notify_full(
            {"HERDR_ENV": "1"},
            "source shell/zsh/alias/notification.zsh; "
            "notify --tmux-icon ✋ title message default group",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(herdr_icon_log_path.exists())
        self.assertEqual(log_path.read_text(encoding="utf-8"), "called\n")

    def test_notify_tmux_icon_without_helper_still_notifies(self):
        # HOME is the temp root, so the tmux_window_name.sh fallback path does not exist
        result, log_path, icon_log_path = self.run_notify(
            {},
            "source shell/zsh/alias/notification.zsh; "
            "notify --tmux-icon ✋ title message default group",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(icon_log_path.exists())
        self.assertEqual(log_path.read_text(encoding="utf-8"), "called\n")

    def test_notification_hooks_force_intentional_notifications(self):
        # NOTIFY_FORCE の export は共通ヘッダに集約されており、各フックはそれを source する
        common_header = (REPO_ROOT / "shell/tmux/ai_notification_hook_common.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("export NOTIFY_FORCE=1", common_header)

        for script_path in (
            "ai/claude/hooks/stop-send-notification.sh",
            "ai/codex/hooks/codex-stop-notification.sh",
            "ai/gemini/hooks/notification.sh",
        ):
            with self.subTest(script=script_path):
                script = (REPO_ROOT / script_path).read_text(encoding="utf-8")
                self.assertIn("shell/tmux/ai_notification_hook_common.sh", script)

    @unittest.skipIf(tomllib is None, "tomllib requires Python 3.11+")
    def test_codex_subprocesses_inherit_notification_suppression(self):
        config = tomllib.loads((REPO_ROOT / "ai/codex/config.toml").read_text(encoding="utf-8"))

        self.assertEqual(
            config["shell_environment_policy"]["set"]["DISABLE_NOTIFY"],
            "1",
        )

    @unittest.skipIf(tomllib is None, "tomllib requires Python 3.11+")
    def test_codex_tui_notifications_are_disabled_for_herdr(self):
        config = tomllib.loads((REPO_ROOT / "ai/codex/config.toml").read_text(encoding="utf-8"))

        self.assertFalse(config["tui"]["notifications"])

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
                self.assertIn("sync_gemini_env_repo_to_home", script)


if __name__ == "__main__":
    unittest.main()
