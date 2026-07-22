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

    def test_codex_uses_its_own_id_emoji(self):
        result, events = self.run_plugin(agent="codex", agent_status="done")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(any(line.startswith("title=CODEX_IDDONE") for line in events))

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

    def test_gemini_done_does_not_notify(self):
        # Gemini has no Herdr installer integration; its agent_status is derived solely
        # from screen-manifest detection and oscillates, firing this gate many times per
        # response. Gemini opts out of notify-rich entirely (see the agent=="gemini"
        # guard) and notifies via its own hooks instead (ai/gemini/hooks/notification.sh).
        result, events = self.run_plugin(agent="gemini", agent_status="done")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(events, [])

    def test_gemini_blocked_does_not_notify(self):
        result, events = self.run_plugin(agent="gemini", agent_status="blocked")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(events, [])


class HerdrPluginTabIconTest(unittest.TestCase):
    """notify-on-agent-status.sh のタブ名アイコン付与ロジック単体テスト。

    fake herdr に `tab get` / `tab rename` の応答を追加し、agent_status→絵文字
    マッピング・スタック防止・idle/unknown時の除去・カスタムラベル保持を検証する。
    """

    def run_plugin(
        self,
        *,
        agent: str = "claude",
        agent_status: str = "done",
        tab_status: str = "done",
        current_label: str = "1",
        pane_id: str = "w1:p7",
        tab_id: str = "w1:t1",
        workspace_id: str = "w1",
        include_tab_id: bool = True,
        title_text: str = "title",
    ) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fake_repo = root / "repo"
            fake_bin = root / "bin"
            fake_bin.mkdir()
            rename_calls = root / "rename_calls"

            dependencies = {
                "shell/zsh/alias/notification.zsh": (
                    'function notify() { :; }\n'
                ),
            }
            for relative_path, content in dependencies.items():
                file_path = fake_repo / relative_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding="utf-8")
            # tmux_emoji.conf / tmux_emoji.py / tmux_window_name.py はリポジトリの実物を
            # そのまま使う。strip_emoji_prefixはUnicode絵文字専用のパターンなので、ASCII
            # スタブ絵文字では剥がれず、スタック防止・idle除去のテストが検証できない。
            # tmux_window_name.py はプラグインが is-herdr-default-label CLI サブコマンドで
            # 呼び出す（既知agentラベル→会話概要への差し替え判定）。
            fake_tmux_dir = fake_repo / "shell/tmux"
            fake_tmux_dir.mkdir(parents=True, exist_ok=True)
            for name in ("tmux_emoji.conf", "tmux_emoji.py", "tmux_window_name.py"):
                real_file = REPO_ROOT / "shell/tmux" / name
                (fake_tmux_dir / name).write_text(
                    real_file.read_text(encoding="utf-8"), encoding="utf-8"
                )

            pane_result = {
                "result": {
                    "pane": {
                        "terminal_title_stripped": title_text,
                        "agent_session": {"value": "session-abc"},
                        **({"tab_id": tab_id} if include_tab_id else {}),
                    }
                }
            }
            tab_result = {
                "result": {
                    "tab": {
                        "agent_status": tab_status,
                        "label": current_label,
                    }
                }
            }
            workspace_result = {
                "result": {"workspaces": [{"workspace_id": workspace_id, "number": 1}]}
            }
            fake_herdr = fake_bin / "herdr"
            fake_herdr.write_text(
                "#!/bin/bash\n"
                'if [[ "$1" == "pane" && "$2" == "get" ]]; then\n'
                f"  echo '{json.dumps(pane_result)}'\n"
                'elif [[ "$1" == "tab" && "$2" == "get" ]]; then\n'
                f"  echo '{json.dumps(tab_result)}'\n"
                'elif [[ "$1" == "tab" && "$2" == "rename" ]]; then\n'
                '  echo "$3 $4" >> "$HERDR_TEST_RENAME_CALLS"\n'
                'elif [[ "$1" == "workspace" && "$2" == "list" ]]; then\n'
                f"  echo '{json.dumps(workspace_result)}'\n"
                "fi\n",
                encoding="utf-8",
            )
            fake_herdr.chmod(0o755)

            env = os.environ.copy()
            real_jq = shutil.which("jq")
            self.assertIsNotNone(real_jq)
            path_entries = [str(fake_bin), os.path.dirname(real_jq), "/usr/bin:/bin"]
            env.update(
                {
                    "HERDR_TEST_EVENTS": str(root / "events"),
                    "HERDR_TEST_RENAME_CALLS": str(rename_calls),
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
                        {"workspace_id": workspace_id, "tab_label": "2"}
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
            calls = (
                rename_calls.read_text(encoding="utf-8").splitlines()
                if rename_calls.exists()
                else []
            )
            return result, calls

    def test_working_status_renames_tab_with_ongoing_icon(self):
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="working",
            tab_status="working",
            current_label="1",
            title_text="",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 ✴️🤖1"])

    def test_blocked_status_renames_tab_with_waiting_icon(self):
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="blocked",
            tab_status="blocked",
            current_label="1",
            title_text="",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 ✴️✋1"])

    def test_done_status_renames_tab_with_completed_icon(self):
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="done",
            tab_status="done",
            current_label="1",
            title_text="",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 ✴️✅1"])

    def test_idle_status_strips_icon_back_to_base_label(self):
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="idle",
            tab_status="idle",
            current_label="✴️🤖1",
            title_text="",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 1"])

    def test_unknown_status_strips_icon_back_to_base_label(self):
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="unknown",
            tab_status="unknown",
            current_label="✴️✅1",
            title_text="",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 1"])

    def test_existing_icon_is_replaced_not_stacked(self):
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="working",
            tab_status="working",
            current_label="✴️✅1",
            title_text="",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 ✴️🤖1"])

    def test_codex_uses_its_own_id_emoji(self):
        result, calls = self.run_plugin(
            agent="codex",
            agent_status="working",
            tab_status="working",
            current_label="1",
            title_text="",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 🪷🤖1"])

    def test_gemini_working_does_not_rename_tab(self):
        # Gemini opts out of notify-rich entirely (tab renaming included), not just
        # notifications — see the agent=="gemini" guard near the top of the script.
        result, calls = self.run_plugin(
            agent="gemini",
            agent_status="working",
            tab_status="working",
            current_label="1",
            title_text="",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, [])

    def test_unrecognized_agent_falls_back_to_robot_emoji(self):
        result, calls = self.run_plugin(
            agent="unknown-agent",
            agent_status="working",
            tab_status="working",
            current_label="1",
            title_text="",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 🤖🤖1"])

    def test_custom_label_is_preserved_across_status_changes(self):
        result, calls = self.run_plugin(
            agent="claude", agent_status="working", tab_status="working", current_label="gm"
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 ✴️🤖gm"])

    def test_no_rename_when_label_already_matches(self):
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="working",
            tab_status="working",
            current_label="✴️🤖1",
            title_text="",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, [])

    def test_missing_tab_id_skips_rename(self):
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="working",
            tab_status="working",
            current_label="1",
            include_tab_id=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, [])

    def test_default_numeric_label_is_replaced_by_conversation_title(self):
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="working",
            tab_status="working",
            current_label="1",
            title_text="ここに会話概要が入る",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 ✴️🤖ここに会話概要が入る"])

    def test_long_conversation_title_is_truncated_to_20_chars(self):
        title_text = "あ" * 25
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="working",
            tab_status="working",
            current_label="1",
            title_text=title_text,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 ✴️🤖" + "あ" * 20])

    def test_conversation_title_exactly_20_chars_is_not_truncated(self):
        title_text = "あ" * 20
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="working",
            tab_status="working",
            current_label="1",
            title_text=title_text,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 ✴️🤖" + "あ" * 20])

    def test_custom_label_is_not_replaced_by_conversation_title(self):
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="working",
            tab_status="working",
            current_label="gm",
            title_text="ここに会話概要が入る",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 ✴️🤖gm"])

    def test_multi_digit_numeric_label_is_replaced_by_conversation_title(self):
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="working",
            tab_status="working",
            current_label="42",
            title_text="概要テキスト",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 ✴️🤖概要テキスト"])

    def test_empty_conversation_title_falls_back_to_numeric_label(self):
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="working",
            tab_status="working",
            current_label="1",
            title_text="",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 ✴️🤖1"])

    def test_known_agent_default_label_is_replaced_by_conversation_title(self):
        # HerdrがAI検出タブに自動命名する既知ラベル（'Claude Code'等）も、
        # 連番数字と同様に会話概要へ差し替える対象。
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="done",
            tab_status="done",
            current_label="Claude Code",
            title_text="タブ名の修正作業",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 ✴️✅タブ名の修正作業"])

    def test_known_agent_default_label_working_icon(self):
        result, calls = self.run_plugin(
            agent="codex",
            agent_status="working",
            tab_status="working",
            current_label="Codex",
            title_text="バグ調査",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 🪷🤖バグ調査"])

    def test_known_agent_default_label_without_title_keeps_label(self):
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="done",
            tab_status="done",
            current_label="Claude Code",
            title_text="",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 ✴️✅Claude Code"])

    def test_manual_label_is_not_replaced_by_conversation_title(self):
        # 数字でも既知agent自動命名名でもないラベルは、ユーザーが手動で付けた
        # 名前とみなし温存する（差し替え対象外）。
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="done",
            tab_status="done",
            current_label="My Task",
            title_text="概要文",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 ✴️✅My Task"])

    def test_replaced_label_is_stable_on_next_fire(self):
        # 一度会話概要に差し替わったラベルは、数字でも既知agent自動命名名でもない
        # ため次回発火時は再判定されても温存され、rename が呼ばれない（不動点）。
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="done",
            tab_status="done",
            current_label="✴️✅タブ名の修正作業",
            title_text="タブ名の修正作業",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
