import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_SCRIPT = REPO_ROOT / "terminal/herdr/plugins/notify-rich/notify-on-agent-status.sh"


class HerdrPluginNotifyTest(unittest.TestCase):
    """notify-on-agent-status.sh のロジック単体テスト。

    実herdr CLI/terminal-notifierには依存せず、fake_bin/herdrとnotify()スタブで
    引数を記録し、done/blocked判定・絵文字出し分け・workspace/tabラベル整形・
    フォールバックを検証する。
    """

    def run_plugin(
        self,
        *,
        agent: str = "claude",
        agent_status: str = "done",
        pane_id: str = "w1:p7",
        workspace_id: str = "w1",
        tab_label: str = "2",
        ws_number: str = "1",
        title_text: str = "Herdr通知をカスタマイズしてworkspace情報を表示",
        session_id: str = "session-abc",
        herdr_present: bool = True,
        pane_get_empty: bool = False,
        jq_present: bool = True,
    ) -> tuple[subprocess.CompletedProcess[str], Path]:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fake_repo = root / "repo"
            fake_bin = root / "bin"
            fake_bin.mkdir()
            events = root / "events"

            dependencies = {
                "shell/zsh/alias/notification.zsh": (
                    'function notify() {\n'
                    '  {\n'
                    '    print -r -- "title=$1"\n'
                    '    print -r -- "message=$2"\n'
                    '    print -r -- "sound=$3"\n'
                    '    print -r -- "group=$4"\n'
                    '  } >> "$HERDR_TEST_EVENTS"\n'
                    '}\n'
                ),
                "shell/tmux/tmux_emoji.conf": (
                    "EMOJI_ID_CLAUDE=CLAUDE_ID\n"
                    "EMOJI_ID_GEMINI=GEMINI_ID\n"
                    "EMOJI_ID_CODEX=CODEX_ID\n"
                    "EMOJI_STATUS_COMPLETED=DONE\n"
                    "EMOJI_STATUS_NOTIFICATION=WAIT\n"
                ),
            }
            for relative_path, content in dependencies.items():
                file_path = fake_repo / relative_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding="utf-8")

            if herdr_present:
                pane_result = (
                    {"result": {"pane": {}}}
                    if pane_get_empty
                    else {
                        "result": {
                            "pane": {
                                "terminal_title_stripped": title_text,
                                "agent_session": {"value": session_id},
                            }
                        }
                    }
                )
                workspace_result = {
                    "result": {
                        "workspaces": [
                            {"workspace_id": workspace_id, "number": int(ws_number)}
                            if ws_number
                            else {"workspace_id": workspace_id}
                        ]
                    }
                }
                fake_herdr = fake_bin / "herdr"
                fake_herdr.write_text(
                    "#!/bin/bash\n"
                    'if [[ "$1" == "pane" && "$2" == "get" ]]; then\n'
                    f"  echo '{json.dumps(pane_result)}'\n"
                    'elif [[ "$1" == "workspace" && "$2" == "list" ]]; then\n'
                    f"  echo '{json.dumps(workspace_result)}'\n"
                    "fi\n",
                    encoding="utf-8",
                )
                fake_herdr.chmod(0o755)

            env = os.environ.copy()
            path_entries = [str(fake_bin)]
            if jq_present:
                real_jq = shutil.which("jq")
                self.assertIsNotNone(real_jq)
                path_entries.append(os.path.dirname(real_jq))
            path_entries.append("/usr/bin:/bin")
            env.update(
                {
                    "HERDR_TEST_EVENTS": str(events),
                    "SET": str(fake_repo) + "/",
                    "HERDR_PLUGIN_EVENT_JSON": json.dumps(
                        {
                            "event": "pane_agent_status_changed",
                            "data": {
                                "pane_id": pane_id,
                                "workspace_id": workspace_id,
                                "agent_status": agent_status,
                                "agent": agent,
                            },
                        }
                    ),
                    "HERDR_PLUGIN_CONTEXT_JSON": json.dumps(
                        {"workspace_id": workspace_id, "tab_label": tab_label}
                        if tab_label
                        else {"workspace_id": workspace_id}
                    ),
                    "HERDR_PANE_ID": pane_id,
                    "HERDR_WORKSPACE_ID": workspace_id,
                    "PATH": ":".join(path_entries),
                }
            )

            result = subprocess.run(
                ["zsh", str(PLUGIN_SCRIPT)],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            event_lines = events.read_text(encoding="utf-8").splitlines() if events.exists() else []
            return result, event_lines

    def test_done_status_notifies_with_completion_title(self):
        result, events = self.run_plugin(agent="claude", agent_status="done")

        self.assertEqual(result.returncode, 0, result.stderr)
        title_line = next(line for line in events if line.startswith("title="))
        # 時刻(🕰️HH:MM:SS)は非決定的なため、プレフィックス一致のみ検証する。
        self.assertTrue(title_line.startswith("title=CLAUDE_IDDONE Claude完了 🖥️1-2 🕰️"), title_line)
        self.assertEqual(
            events[1:],
            [
                "message=Herdr通知をカスタマイズしてworkspace情報を表示",
                "sound=Hero",
                "group=claude-session-abc",
            ],
        )

    def test_blocked_status_notifies_with_waiting_title(self):
        result, events = self.run_plugin(agent="claude", agent_status="blocked")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("message=Herdr通知をカスタマイズしてworkspace情報を表示", events)
        self.assertTrue(any(line.startswith("title=CLAUDE_IDWAIT Claude入力待ち 🖥️1-2 🕰️") for line in events))

    def test_idle_working_unknown_do_not_notify(self):
        for agent_status in ("idle", "working", "unknown", ""):
            with self.subTest(agent_status=agent_status):
                result, events = self.run_plugin(agent_status=agent_status)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(events, [])

    def test_codex_and_gemini_use_their_own_id_emoji(self):
        cases = (("codex", "CODEX_ID"), ("gemini", "GEMINI_ID"))
        for agent, expected_id in cases:
            with self.subTest(agent=agent):
                result, events = self.run_plugin(agent=agent, agent_status="done")

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(any(line.startswith(f"title={expected_id}DONE") for line in events))

    def test_unrecognized_agent_falls_back_to_robot_emoji(self):
        result, events = self.run_plugin(agent="unknown-agent", agent_status="done")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(any(line.startswith("title=🤖DONE") for line in events))

    def test_missing_tab_label_omits_screen_label(self):
        result, events = self.run_plugin(agent_status="done", tab_label="")

        self.assertEqual(result.returncode, 0, result.stderr)
        title_line = next(line for line in events if line.startswith("title="))
        self.assertNotIn("🖥️", title_line)

    def test_missing_workspace_number_omits_screen_label(self):
        result, events = self.run_plugin(agent_status="done", ws_number="")

        self.assertEqual(result.returncode, 0, result.stderr)
        title_line = next(line for line in events if line.startswith("title="))
        self.assertNotIn("🖥️", title_line)

    def test_empty_conversation_title_uses_placeholder(self):
        result, events = self.run_plugin(agent_status="done", title_text="")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("message=(no title)", events)

    def test_pane_get_failure_skips_notification(self):
        result, events = self.run_plugin(agent_status="done", herdr_present=False)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(events, [])

    def test_empty_pane_result_skips_notification(self):
        # pane get succeeds but returns no usable pane fields (empty title -> placeholder,
        # but no session id -> no group). Should still notify, just without a group.
        result, events = self.run_plugin(agent_status="done", pane_get_empty=True)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("message=(no title)", events)
        self.assertIn("group=", events)


if __name__ == "__main__":
    unittest.main()
