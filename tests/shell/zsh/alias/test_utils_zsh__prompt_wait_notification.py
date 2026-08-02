"""shell/zsh/alias/utils.zsh の _start/_finish_prompt_wait_notification 単体テスト。

対話プロンプト（smart_copy/smart_merge_json/confirm等）が入力待ちになる直前に
✋を付け、入力完了で外す仕組み。tmux版remove_tmux_window_iconに加えてHerdr版
remove_herdr_status_iconも呼ぶことを、スタブ関数への記録で検証する。
"""
import subprocess
import unittest
from pathlib import Path

from support import REPO_ROOT

STUBS = (
    'notify() { echo "notify:$*" >> "$CALL_LOG"; }\n'
    'remove_tmux_window_icon() { echo "remove_tmux" >> "$CALL_LOG"; }\n'
    'remove_herdr_status_icon() { echo "remove_herdr" >> "$CALL_LOG"; }\n'
    '_ensure_prompt_notify_available() { :; }\n'
)


class FinishPromptWaitNotificationTest(unittest.TestCase):
    def run_finish(self, extra_prelude: str = "") -> list[str]:
        call_log = REPO_ROOT / "tests" / "__scratch_call_log__"
        try:
            script = (
                f"{extra_prelude}"
                f"{STUBS}"
                'source shell/zsh/alias/utils.zsh; '
                "_finish_prompt_wait_notification"
            )
            result = subprocess.run(
                ["zsh", "-fc", script],
                cwd=REPO_ROOT,
                env={"HOME": "/nonexistent", "CALL_LOG": str(call_log)},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            return call_log.read_text(encoding="utf-8").splitlines() if call_log.exists() else []
        finally:
            call_log.unlink(missing_ok=True)

    def test_calls_both_tmux_and_herdr_remove(self):
        calls = self.run_finish()
        self.assertIn("remove_tmux", calls)
        self.assertIn("remove_herdr", calls)

    def test_missing_functions_do_not_error(self):
        # remove_tmux_window_icon/remove_herdr_status_icon が未定義（tmux外・Herdr外
        # かつsourceフォールバックも失敗する環境）でもエラーにならない
        script = (
            'notify() { :; }\n'
            '_ensure_prompt_notify_available() { :; }\n'
            'source shell/zsh/alias/utils.zsh; '
            "_finish_prompt_wait_notification"
        )
        result = subprocess.run(
            ["zsh", "-fc", script],
            cwd=REPO_ROOT,
            env={"HOME": "/nonexistent"},
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
