"""terminal/herdr/plugins/notify-rich/notify-on-agent-status.sh のフル実行テスト。

claude+doneイベントで、transcript末尾がAPIエラーの場合に通常の「✅完了」ではなく
エラー用の見た目（絵文字/ラベル/音/本文）で通知されることを固定する。
herdr CLI（pane get/tab get/workspace list/tab rename/notification show）は
フェイクスクリプトでスタブし、システム通知引数を捕捉する。
"""

import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK = REPO_ROOT / "terminal/herdr/plugins/notify-rich/notify-on-agent-status.sh"
SYSTEM_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"


class NotifyOnAgentStatusFullTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

        fake_bin = self.root / "bin"
        fake_bin.mkdir()

        self.notifier_log = self.root / "terminal-notifier.log"
        notifier = fake_bin / "terminal-notifier"
        notifier.write_text(
            '#!/bin/sh\nprintf "%s\\n" "$@" >> "$NOTIFY_TEST_LOG"\nexit 0\n', encoding="utf-8"
        )
        notifier.chmod(notifier.stat().st_mode | stat.S_IXUSR)

        # herdr CLIスタブ: 参照、tab rename、システム通知に応答する。
        self.herdr_stub = fake_bin / "herdr"
        self.herdr_stub.write_text(
            "#!/bin/sh\n"
            'case "$1 $2" in\n'
            '  "pane get") cat "$HERDR_STUB_PANE_JSON" ;;\n'
            '  "tab get") cat "$HERDR_STUB_TAB_JSON" ;;\n'
            '  "workspace list") echo \'{"result":{"workspaces":[]}}\' ;;\n'
            '  "tab rename") exit 0 ;;\n'
            '  "notification show") {\n'
            '    printf "%s\\n" "$3" "$5" "$7" >> "$NOTIFY_TEST_LOG"\n'
            '  } ;;\n'
            "  *) exit 0 ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        self.herdr_stub.chmod(self.herdr_stub.stat().st_mode | stat.S_IXUSR)

    def run_hook(
        self, transcript_lines: list[str], session_id: str = "s1", agent_status: str = "done"
    ) -> subprocess.CompletedProcess:
        projects_dir = self.root / "projects" / "proj"
        projects_dir.mkdir(parents=True, exist_ok=True)
        (projects_dir / f"{session_id}.jsonl").write_text(
            "\n".join(transcript_lines) + "\n", encoding="utf-8"
        )

        pane_json = self.root / "pane.json"
        pane_json.write_text(
            json.dumps(
                {
                    "result": {
                        "pane": {
                            "agent": "claude",
                            "pane_id": "pane-1",
                            "tab_id": "tab-1",
                            "terminal_title_stripped": "会話の概要タイトル",
                            "agent_session": {"value": session_id},
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        tab_json = self.root / "tab.json"
        tab_json.write_text(
            json.dumps(
                {"result": {"tab": {"agent_status": agent_status, "label": "tab-label"}}}
            ),
            encoding="utf-8",
        )

        event_json = json.dumps(
            {
                "event": "pane.agent_status_changed",
                "data": {
                    "agent": "claude",
                    "agent_status": agent_status,
                    "pane_id": "pane-1",
                },
            }
        )

        env = {
            "HOME": str(self.root),
            "PATH": f"{self.root / 'bin'}:{SYSTEM_PATH}",
            "NOTIFY_TEST_LOG": str(self.notifier_log),
            "AI_NOTIFICATION_BURST_STATE_DIR": str(self.root / "burst-state"),
            "SET": f"{REPO_ROOT}/",
            "TZ": "UTC",
            "HERDR_PLUGIN_EVENT_JSON": event_json,
            "HERDR_PANE_ID": "pane-1",
            "HERDR_BIN_PATH": str(self.herdr_stub),
            "HERDR_STUB_PANE_JSON": str(pane_json),
            "HERDR_STUB_TAB_JSON": str(tab_json),
            "CLAUDE_CONFIG_DIR": str(self.root),
        }
        return subprocess.run(
            ["zsh", str(HOOK)], env=env, text=True, capture_output=True, check=False
        )

    def test_api_error_done_sends_error_notification(self):
        result = self.run_hook(
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
                )
            ]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        log = self.notifier_log.read_text(encoding="utf-8")
        self.assertIn("API Error: Connection closed mid-response.", log)
        self.assertIn("request", log)
        self.assertIn("❌", log)

    def test_unresolvable_transcript_falls_back_to_normal_completion(self):
        # projects配下にtranscriptファイルが存在しない（解決不能）場合、
        # fail-safeで従来どおりの完了通知にフォールバックする
        # （通知が完全に死ぬ事故を避ける既存方針）
        result = self.run_hook([], session_id="session-with-no-transcript-file")
        # run_hookは常にtranscriptファイルを作るため、ここでは直接該当ファイルを消す
        transcript_file = self.root / "projects" / "proj" / "session-with-no-transcript-file.jsonl"
        transcript_file.unlink()
        # 再実行（transcript不在の状態で）
        pane_json = self.root / "pane.json"
        env = {
            "HOME": str(self.root),
            "PATH": f"{self.root / 'bin'}:{SYSTEM_PATH}",
            "NOTIFY_TEST_LOG": str(self.notifier_log),
            "AI_NOTIFICATION_BURST_STATE_DIR": str(self.root / "burst-state"),
            "SET": f"{REPO_ROOT}/",
            "TZ": "UTC",
            "HERDR_PLUGIN_EVENT_JSON": json.dumps(
                {
                    "event": "pane.agent_status_changed",
                    "data": {"agent": "claude", "agent_status": "done", "pane_id": "pane-1"},
                }
            ),
            "HERDR_PANE_ID": "pane-1",
            "HERDR_BIN_PATH": str(self.herdr_stub),
            "HERDR_STUB_PANE_JSON": str(pane_json),
            "HERDR_STUB_TAB_JSON": str(self.root / "tab.json"),
            "CLAUDE_CONFIG_DIR": str(self.root),
        }
        result = subprocess.run(
            ["zsh", str(HOOK)], env=env, text=True, capture_output=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        log = self.notifier_log.read_text(encoding="utf-8")
        self.assertIn("done", log)
        self.assertIn("✅", log)

    def _sync_agent_launch(self, tool_use_id, timestamp):
        return json.dumps(
            {
                "timestamp": timestamp,
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": tool_use_id,
                            "name": "Agent",
                            "input": {"subagent_type": "Explore", "description": "test"},
                        }
                    ],
                },
            }
        )

    def _sync_agent_result(self, tool_use_id, timestamp):
        return json.dumps(
            {
                "timestamp": timestamp,
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": [{"type": "text", "text": "Agent finished"}],
                        }
                    ],
                },
            }
        )

    def test_sync_subagent_tail_suppresses_notification(self):
        # 同期サブエージェントのtool_resultがtranscript末尾（メインエージェント未再開）
        # の場合、Herdrがスピナー消失をdoneと誤認してもシステム通知は呼ばれない。
        result = self.run_hook(
            [
                json.dumps(
                    {
                        "timestamp": "2026-07-11T12:00:00.000Z",
                        "message": {"role": "user", "content": "herdrの通知バグを直して"},
                    }
                ),
                self._sync_agent_launch("toolu_sync1", "2026-07-11T12:01:00.000Z"),
                self._sync_agent_result("toolu_sync1", "2026-07-11T12:01:05.000Z"),
            ]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(
            self.notifier_log.exists() and self.notifier_log.read_text(encoding="utf-8"),
            "同期サブエージェント完了直後は通知が送られてはならない",
        )

    def test_sync_subagent_followed_by_real_completion_notifies(self):
        # 同じtranscriptに本物の完了（後続assistantテキスト）が続けば通常どおり通知される
        result = self.run_hook(
            [
                json.dumps(
                    {
                        "timestamp": "2026-07-11T12:00:00.000Z",
                        "message": {"role": "user", "content": "herdrの通知バグを直して"},
                    }
                ),
                self._sync_agent_launch("toolu_sync1", "2026-07-11T12:01:00.000Z"),
                self._sync_agent_result("toolu_sync1", "2026-07-11T12:01:05.000Z"),
                json.dumps(
                    {
                        "timestamp": "2026-07-11T12:01:10.000Z",
                        "message": {
                            "role": "assistant",
                            "content": [{"type": "text", "text": "修正しました"}],
                        },
                    }
                ),
            ]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        log = self.notifier_log.read_text(encoding="utf-8")
        self.assertIn("done", log)
        self.assertIn("✅", log)

    def test_sync_subagent_tail_with_blocked_status_still_notifies(self):
        # ガードはagent_status=doneのみを対象とする（claude_transcript_analyze.pyの
        # PENDING_BACKGROUND_WORK抑止はプラグイン側でdone判定の後にしか参照されない）。
        # blocked（入力待ち）では同期サブエージェント末尾でも通知は抑止されない。
        result = self.run_hook(
            [
                json.dumps(
                    {
                        "timestamp": "2026-07-11T12:00:00.000Z",
                        "message": {"role": "user", "content": "herdrの通知バグを直して"},
                    }
                ),
                self._sync_agent_launch("toolu_sync1", "2026-07-11T12:01:00.000Z"),
                self._sync_agent_result("toolu_sync1", "2026-07-11T12:01:05.000Z"),
            ],
            agent_status="blocked",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        log = self.notifier_log.read_text(encoding="utf-8")
        self.assertIn("request", log)

    def test_normal_done_sends_completion_notification(self):
        result = self.run_hook(
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
            ]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        log = self.notifier_log.read_text(encoding="utf-8")
        self.assertIn("done", log)
        self.assertIn("✅", log)
        self.assertNotIn("❌", log)


if __name__ == "__main__":
    unittest.main()
