"""ai/claude/hooks/stop-send-notification.sh のAPIエラー停止通知。

Stopイベントでtranscript末尾がAPIエラーの場合、通常の「✅終了」ではなく
「❌エラー停止」通知が出ることを固定する（PC スリープ復帰時の接続断等で
止まったことに気づけるようにする機能）。実際のterminal-notifier呼び出しは
フェイクバイナリで捕捉し、tmuxアイコン更新はスタブ関数で捕捉する。
"""

import json
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK = REPO_ROOT / "ai/claude/hooks/stop-send-notification.sh"
SYSTEM_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"


class StopSendNotificationApiErrorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

        fake_bin = self.root / "bin"
        fake_bin.mkdir()
        self.notifier_log = self.root / "terminal-notifier.log"
        notifier = fake_bin / "terminal-notifier"
        # 引数を1行ずつログに残す（-title/-message等の値を後で検証する）
        notifier.write_text(
            "#!/bin/sh\n"
            'printf "%s\\n" "$@" >> "$NOTIFY_TEST_LOG"\n'
            "exit 0\n",
            encoding="utf-8",
        )
        notifier.chmod(notifier.stat().st_mode | stat.S_IXUSR)

        # BURST_STATE_DIRはテストごとに独立させ、burst抑止の副作用を切り離す
        self.burst_state_dir = self.root / "burst-state"

    def run_hook(self, hook_input: dict, transcript_lines: list[str]) -> subprocess.CompletedProcess:
        transcript_path = self.root / "transcript.jsonl"
        transcript_path.write_text("\n".join(transcript_lines) + "\n", encoding="utf-8")
        payload = {"transcript_path": str(transcript_path), **hook_input}

        # tmuxセッション外（TMUX_PANE未設定）のためupdate_tmux_window_nameは実質no-opになる
        # （tmux_window_name.shの_get_tmux_pane_id_for_window_nameがreturn 1する）。
        # アイコン自体の検証はここでは行わず、通知タイトルに含まれる絵文字で区別する。
        env = {
            "HOME": str(self.root),
            "PATH": f"{self.root / 'bin'}:{SYSTEM_PATH}",
            "NOTIFY_TEST_LOG": str(self.notifier_log),
            "AI_NOTIFICATION_BURST_STATE_DIR": str(self.burst_state_dir),
            "SET": f"{REPO_ROOT}/",
            "TZ": "UTC",
        }
        return subprocess.run(
            ["bash", str(HOOK)],
            input=json.dumps(payload),
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_stop_with_server_error_sends_error_notification_not_completed(self):
        result = self.run_hook(
            {"hook_event_name": "Stop", "session_id": "s1"},
            [
                json.dumps(
                    {
                        "type": "assistant",
                        "isApiErrorMessage": True,
                        "error": "server_error",
                        "timestamp": "2026-07-11T12:00:00.000Z",
                        "message": {
                            "role": "assistant",
                            "stop_reason": "stop_sequence",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "API Error: Connection closed mid-response.",
                                }
                            ],
                        },
                    }
                ),
                json.dumps(
                    {"type": "system", "subtype": "turn_duration", "timestamp": "2026-07-11T12:00:01.000Z"}
                ),
            ],
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        log = self.notifier_log.read_text(encoding="utf-8")
        self.assertIn("API Error: Connection closed mid-response.", log)
        self.assertIn("Basso", log)
        self.assertIn("❌", log)
        self.assertIn("エラー停止", log)
        self.assertNotIn("✅", log)

    def test_stop_without_api_error_sends_normal_completion_notification(self):
        result = self.run_hook(
            {"hook_event_name": "Stop", "session_id": "s2"},
            [
                json.dumps(
                    {
                        "timestamp": "2026-07-11T12:00:00.000Z",
                        "message": {"role": "user", "content": "テストして"},
                    }
                ),
                json.dumps(
                    {
                        "timestamp": "2026-07-11T12:01:00.000Z",
                        "message": {
                            "role": "assistant",
                            "content": [{"type": "text", "text": "完了しました"}],
                        },
                    }
                ),
            ],
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        log = self.notifier_log.read_text(encoding="utf-8")
        self.assertIn("終了", log)
        self.assertIn("Hero", log)
        self.assertIn("✅", log)
        self.assertNotIn("❌", log)

    def test_api_error_takes_priority_over_pending_background_work(self):
        # async Agent起動中（未完了）+ APIエラーの複合。エラーで止まっている以上、
        # バックグラウンド作業の完了を待っても会話は再開しないためAPIエラーを優先する。
        result = self.run_hook(
            {"hook_event_name": "Stop", "session_id": "s3"},
            [
                json.dumps(
                    {
                        "timestamp": "2026-07-11T12:00:00.000Z",
                        "message": {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": "toolu_x",
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": (
                                                "Async agent launched successfully. "
                                                "(This tool result is internal metadata)\n"
                                                "agentId: a0f4c886c975458d3 "
                                                "(internal ID - do not mention to user)"
                                            ),
                                        }
                                    ],
                                }
                            ],
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "assistant",
                        "isApiErrorMessage": True,
                        "error": "server_error",
                        "timestamp": "2026-07-11T12:00:01.000Z",
                        "message": {
                            "role": "assistant",
                            "stop_reason": "stop_sequence",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "API Error: Connection closed mid-response.",
                                }
                            ],
                        },
                    }
                ),
            ],
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        log = self.notifier_log.read_text(encoding="utf-8")
        self.assertIn("エラー停止", log)
        self.assertIn("API Error: Connection closed mid-response.", log)

    def test_burst_suppression_skips_second_immediate_error_notification(self):
        lines = [
            json.dumps(
                {
                    "type": "assistant",
                    "isApiErrorMessage": True,
                    "error": "rate_limit",
                    "timestamp": "2026-07-11T12:00:00.000Z",
                    "message": {
                        "role": "assistant",
                        "stop_reason": "stop_sequence",
                        "content": [
                            {"type": "text", "text": "You've hit your session limit"}
                        ],
                    },
                }
            )
        ]
        first = self.run_hook({"hook_event_name": "Stop", "session_id": "burst-1"}, lines)
        self.assertEqual(first.returncode, 0, first.stderr)
        first_log_lines = self.notifier_log.read_text(encoding="utf-8").count("called_marker")

        second = self.run_hook({"hook_event_name": "Stop", "session_id": "burst-1"}, lines)
        self.assertEqual(second.returncode, 0, second.stderr)
        # 1回目は通知され、2回目（直後・同一session_id+error種別）は抑止されて
        # terminal-notifier呼び出しログが増えない
        occurrences = self.notifier_log.read_text(encoding="utf-8").count(
            "You've hit your session limit"
        )
        self.assertEqual(occurrences, 1)


if __name__ == "__main__":
    unittest.main()
