import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


from support import REPO_ROOT
SYSTEM_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

DEFAULT_NOTIFY_COMMAND = "source shell/zsh/alias/notification.zsh; notify title message default group"

ICON_COMMAND = (
    "source shell/tmux/tmux_window_name.sh; "
    "_get_tmux_pane_id_for_window_name() { "
    'echo "$TMUX_PANE" > "$PANE_CHECK_LOG"; '
    '[[ -z "${TMUX_PANE}" || "${TERM_PROGRAM:-}" != "tmux" ]] && return 1; '
    'echo "${TMUX_PANE}"; '
    "}; "
    'update_tmux_window_name "✋"'
)


class NotificationSilentModeTest(unittest.TestCase):
    """NOTIFY_SILENT=1 が Mac 通知と tmux アイコン変更の両方を抑止することを検証する。

    tests/manual/notification_hook_smoke.sh --silent が実際にこの変数を export するため、
    ここではその2つのゲート（notify のサプレス判定 / update_tmux_window_name）を
    直接叩いて検証する。tests/shell/zsh/alias/test_notification_zsh__notification_suppression.py と同じ偽terminal-notifier方式。
    """

    def run_notify(
        self,
        extra_env: dict[str, str],
        zsh_command: str = DEFAULT_NOTIFY_COMMAND,
    ) -> tuple[subprocess.CompletedProcess[str], Path]:
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
            ["zsh", "-fc", zsh_command],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        return result, log_path

    def run_update_tmux_window_name(self, extra_env: dict[str, str]) -> tuple[subprocess.CompletedProcess[str], Path]:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)

        root = Path(temp_dir.name)
        pane_check_log = root / "pane-check.log"

        env = {
            "HOME": str(root),
            "PATH": SYSTEM_PATH,
            "PANE_CHECK_LOG": str(pane_check_log),
            # TMUX_PANE を未設定にすると _get_tmux_pane_id_for_window_name が
            # NOTIFY_SILENT の判定を待たずに早期returnしてしまい、
            # 「NOTIFY_SILENTガードがpane判定より先に効いている」ことを検証できない。
            # よってpane相当の値とTERM_PROGRAM=tmuxを明示的に与える。
            "TMUX_PANE": "%0",
            "TERM_PROGRAM": "tmux",
        }
        env.update(extra_env)

        result = subprocess.run(
            ["bash", "-c", ICON_COMMAND],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        return result, pane_check_log

    # --- notify (Mac通知) 抑止 ---

    def test_notify_silent_suppresses_even_with_force(self):
        # NOTIFY_FORCE より優先して抑止されることが本機能の要点
        result, log_path = self.run_notify({"NOTIFY_SILENT": "1", "NOTIFY_FORCE": "1"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(log_path.exists())

    def test_notify_silent_suppresses_without_force(self):
        result, log_path = self.run_notify({"NOTIFY_SILENT": "1"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(log_path.exists())

    def test_notify_without_silent_still_notifies_with_force(self):
        # fail-safeデフォルト: NOTIFY_SILENT未指定なら従来どおりNOTIFY_FORCEが効く
        result, log_path = self.run_notify({"NOTIFY_FORCE": "1"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(log_path.read_text(encoding="utf-8"), "called\n")

    def test_notify_empty_silent_value_is_treated_as_unset(self):
        # 境界値: NOTIFY_SILENT="" は [[ -n ]] 判定で「未設定」と同じ扱いになる
        result, log_path = self.run_notify({"NOTIFY_SILENT": "", "NOTIFY_FORCE": "1"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(log_path.read_text(encoding="utf-8"), "called\n")

    # --- tmux アイコン抑止 ---

    def test_update_tmux_window_name_silent_skips_icon(self):
        result, pane_check_log = self.run_update_tmux_window_name({"NOTIFY_SILENT": "1"})

        self.assertEqual(result.returncode, 0, result.stderr)
        # NOTIFY_SILENTガードがpane判定より前でreturnしているなら、
        # pane判定以降のコードは実行されずログファイルは作られない
        self.assertFalse(pane_check_log.exists())

    def test_update_tmux_window_name_without_silent_runs_pane_check(self):
        result, pane_check_log = self.run_update_tmux_window_name({})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(pane_check_log.exists())
        self.assertEqual(pane_check_log.read_text(encoding="utf-8"), "%0\n")


if __name__ == "__main__":
    unittest.main()
