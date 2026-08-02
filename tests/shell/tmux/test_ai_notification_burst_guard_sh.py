"""shell/tmux/ai_notification_burst_guard.sh の単体テスト。

同一セッションでの短時間再通知を抑止する共有ヘルパー。tmux経路(stop-send-notification.sh)
とHerdr経路(notify-on-agent-status.sh)の両方から使われるため、Herdr専用の状態ディレクトリ
（HERDR_PLUGIN_STATE_DIR）には依存しない。
"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT


def run_fn(fn_and_args: str, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    script = f'source "{REPO_ROOT}/shell/tmux/ai_notification_burst_guard.sh"; ' + fn_and_args
    env = {**os.environ, **(env_extra or {})}
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env)


class ApiErrorBurstGuardTest(unittest.TestCase):
    def setUp(self):
        self.state_dir = tempfile.mkdtemp()
        self.env = {"AI_NOTIFICATION_BURST_STATE_DIR": self.state_dir}

    def tearDown(self):
        subprocess.run(["rm", "-rf", self.state_dir])

    def test_first_call_is_not_suppressed(self):
        result = run_fn(
            'api_error_burst_should_suppress "session-a" "server_error" 100 60; echo "rc=$?"',
            self.env,
        )
        self.assertEqual(result.stdout.strip(), "rc=1")

    def test_immediate_second_call_is_suppressed(self):
        run_fn('api_error_burst_should_suppress "session-a" "server_error" 100 60', self.env)
        result = run_fn(
            'api_error_burst_should_suppress "session-a" "server_error" 105 60; echo "rc=$?"',
            self.env,
        )
        self.assertEqual(result.stdout.strip(), "rc=0")

    def test_call_after_threshold_is_not_suppressed(self):
        run_fn('api_error_burst_should_suppress "session-a" "server_error" 100 60', self.env)
        result = run_fn(
            'api_error_burst_should_suppress "session-a" "server_error" 161 60; echo "rc=$?"',
            self.env,
        )
        self.assertEqual(result.stdout.strip(), "rc=1")

    def test_different_sessions_do_not_interfere(self):
        run_fn('api_error_burst_should_suppress "session-a" "server_error" 100 60', self.env)
        result = run_fn(
            'api_error_burst_should_suppress "session-b" "server_error" 105 60; echo "rc=$?"',
            self.env,
        )
        self.assertEqual(result.stdout.strip(), "rc=1")

    def test_unwritable_state_dir_fails_open_to_notify(self):
        # fail-safe: 状態ファイルが読めない/書けない場合は「抑止しない」= 通知する側に倒す
        result = run_fn(
            'api_error_burst_should_suppress "session-a" "server_error" 100 60; echo "rc=$?"',
            {"AI_NOTIFICATION_BURST_STATE_DIR": "/nonexistent/dir/that/cannot/be/created"},
        )
        self.assertEqual(result.stdout.strip(), "rc=1")


if __name__ == "__main__":
    unittest.main()
