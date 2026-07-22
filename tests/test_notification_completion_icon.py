"""shell/zsh/notification.zsh の完了✅/失敗❌アイコン化テスト。

(b) 長時間コマンドの完了/失敗はこれまでMac通知の文字だけで、tmux/Herdrの
window/tabアイコンには反映されていなかった。_notification_precmdが
`notify --tmux-icon`を使うようになったこと、および次コマンド開始時
（_notification_preexec）でアイコンが外れることを、notify()スタブへの
呼び出し記録で検証する。
"""
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

STUBS = (
    'notify() { echo "notify:$*" >> "$CALL_LOG"; }\n'
    'remove_tmux_window_icon() { echo "remove_tmux" >> "$CALL_LOG"; }\n'
    'remove_herdr_status_icon() { echo "remove_herdr" >> "$CALL_LOG"; }\n'
)

EXIT_CODE_SIGINT_DEF = "EXIT_CODE_SIGINT=130\nEXIT_CODE_SIGPIPE=141\n"


class NotificationCompletionIconTest(unittest.TestCase):
    def run_script(self, body: str) -> list[str]:
        call_log = REPO_ROOT / "tests" / "__scratch_completion_call_log__"
        try:
            script = (
                f"{STUBS}"
                f"{EXIT_CODE_SIGINT_DEF}"
                "add-zsh-hook() { :; }\n"  # 実フック登録は無効化し、関数呼び出しだけ検証
                'source shell/zsh/notification.zsh; '
                f"{body}"
            )
            result = subprocess.run(
                ["zsh", "-fc", script],
                cwd=REPO_ROOT,
                # SECONDSはzshの特殊パラメータで環境変数からは初期化できないため
                # ここでは渡さない（各テストがスクリプト内でSECONDS=100として設定する）。
                env={"HOME": "/nonexistent", "CALL_LOG": str(call_log)},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            return call_log.read_text(encoding="utf-8").splitlines() if call_log.exists() else []
        finally:
            call_log.unlink(missing_ok=True)

    def test_completed_command_uses_tmux_icon_flag(self):
        # SECONDSはzshの特殊パラメータでシェル起動時0から始まるため、まず経過させて
        # から_cmd_start_timeを記録させる（_cmd_start_time<=0の早期returnを避ける）。
        calls = self.run_script(
            "SECONDS=100; "
            "_notification_preexec 'sleep 12'; "
            "SECONDS=$((SECONDS + 12)); "
            "_notification_precmd"
        )
        self.assertTrue(
            any(line.startswith("notify:--tmux-icon ✅") for line in calls), calls
        )

    def test_failed_command_uses_tmux_icon_flag_with_error_emoji(self):
        calls = self.run_script(
            "SECONDS=100; "
            "_notification_preexec 'false'; "
            "SECONDS=$((SECONDS + 12)); "
            "false; "
            "_notification_precmd"
        )
        self.assertTrue(
            any(line.startswith("notify:--tmux-icon ❌") for line in calls), calls
        )

    def test_short_command_does_not_notify_or_set_icon(self):
        calls = self.run_script(
            "SECONDS=100; "
            "_notification_preexec 'echo hi'; "
            "SECONDS=$((SECONDS + 1)); "
            "_notification_precmd"
        )
        self.assertEqual(calls, [])

    def test_next_preexec_removes_previous_completion_icon(self):
        calls = self.run_script(
            "SECONDS=100; "
            "_notification_preexec 'sleep 12'; "
            "SECONDS=$((SECONDS + 12)); "
            "_notification_precmd; "
            "_notification_preexec 'echo next'"
        )
        self.assertIn("remove_tmux", calls)
        self.assertIn("remove_herdr", calls)

    def test_preexec_does_not_remove_when_no_icon_was_set(self):
        # 短時間コマンド（アイコン未設定）の直後は remove を呼ばない
        calls = self.run_script(
            "SECONDS=100; "
            "_notification_preexec 'echo hi'; "
            "SECONDS=$((SECONDS + 1)); "
            "_notification_precmd; "
            "_notification_preexec 'echo next'"
        )
        self.assertNotIn("remove_tmux", calls)
        self.assertNotIn("remove_herdr", calls)


if __name__ == "__main__":
    unittest.main()
