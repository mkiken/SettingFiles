import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_SCRIPT = REPO_ROOT / "terminal/herdr/plugins/notify-rich/notify-on-agent-status.sh"
PLUGIN_MANIFEST = REPO_ROOT / "terminal/herdr/plugins/notify-rich/herdr-plugin.toml"


class HerdrPluginManifestTest(unittest.TestCase):
    def test_subscribes_to_supported_tab_refresh_events(self):
        manifest = PLUGIN_MANIFEST.read_text(encoding="utf-8")

        for event_name in (
            "pane.agent_status_changed",
            "pane.agent_detected",
            "pane.focused",
        ):
            with self.subTest(event_name=event_name):
                self.assertIn(f'on = "{event_name}"', manifest)

        self.assertNotIn('on = "pane.updated"', manifest)


class HerdrPluginNotifyTest(unittest.TestCase):
    """notify-on-agent-status.sh のロジック単体テスト。

    実herdr CLI/terminal-notifierには依存せず、fake_bin/herdrとnotify()スタブで
    引数を記録し、done/blocked判定・絵文字出し分け・workspace番号/tab index整形・
    screen_label省略(indexが取れない時)を検証する。
    """

    def run_plugin(
        self,
        *,
        agent: str = "claude",
        agent_status: str = "done",
        pane_id: str = "w1:p7",
        tab_id: str = "w1:t4",
        workspace_id: str = "w1",
        tab_label: str = "4",
        ws_label: str = "ai-work",
        title_text: str = "Herdr通知をカスタマイズしてworkspace情報を表示",
        session_id: str = "session-abc",
        herdr_present: bool = True,
        pane_get_empty: bool = False,
        include_tab_id: bool = True,
        jq_present: bool = True,
        event_name: str = "pane.agent_status_changed",
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
                    # screen_labelがbase_label経由でtmux_emoji.py/tmux_window_name.pyを
                    # 呼ぶため、未使用でも_load_conf()がKeyErrorしないよう全キーを埋める。
                    "EMOJI_STATUS_ONGOING=ONGOING\n"
                    "EMOJI_STATUS_ERROR=ERROR\n"
                    "EMOJI_CONTEXT_ALERT=ALERT\n"
                ),
            }
            for relative_path, content in dependencies.items():
                file_path = fake_repo / relative_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding="utf-8")

            # screen_labelはタブ処理ブロックが確定させるbase_labelに依存するため、
            # is-herdr-default-label判定(tmux_window_name.py)とstrip_emoji_prefix
            # (tmux_emoji.py)の実体が必要。ASCIIスタブのtmux_emoji.conf(上記)には
            # 絵文字が無く、strip_emoji_prefixは絵文字を含まない文字列に対しては
            # 恒等関数なのでtitleのASCII識別子アサーションと衝突しない。
            fake_tmux_dir = fake_repo / "shell/tmux"
            fake_tmux_dir.mkdir(parents=True, exist_ok=True)
            for name in ("tmux_emoji.py", "tmux_window_name.py", "herdr_status_icon.sh"):
                real_file = REPO_ROOT / "shell/tmux" / name
                (fake_tmux_dir / name).write_text(
                    real_file.read_text(encoding="utf-8"), encoding="utf-8"
                )

            if herdr_present:
                pane_fields = {
                    "agent": agent,
                    "agent_status": agent_status,
                    "terminal_title_stripped": title_text,
                    "agent_session": {"value": session_id},
                }
                if include_tab_id:
                    pane_fields["tab_id"] = tab_id
                pane_result = (
                    {"result": {"pane": {}}}
                    if pane_get_empty
                    else {"result": {"pane": pane_fields}}
                )
                tab_fields = {"agent_status": agent_status, "label": tab_label}
                tab_result = {"result": {"tab": tab_fields}}
                workspace_result = {
                    "result": {
                        "workspaces": [
                            {"workspace_id": workspace_id, "label": ws_label}
                            if ws_label
                            else {"workspace_id": workspace_id}
                        ]
                    }
                }
                fake_herdr = fake_bin / "herdr"
                fake_herdr.write_text(
                    "#!/bin/bash\n"
                    'if [[ "$1" == "pane" && "$2" == "get" ]]; then\n'
                    f"  echo '{json.dumps(pane_result)}'\n"
                    'elif [[ "$1" == "tab" && "$2" == "get" ]]; then\n'
                    f"  echo '{json.dumps(tab_result)}'\n"
                    'elif [[ "$1" == "tab" && "$2" == "rename" ]]; then\n'
                    '  :\n'
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
            if event_name == "pane.agent_status_changed":
                event_data = {
                    "pane_id": pane_id,
                    "workspace_id": workspace_id,
                    "agent_status": agent_status,
                    "agent": agent,
                }
            elif event_name == "pane.agent_detected":
                event_data = {
                    "pane_id": pane_id,
                    "workspace_id": workspace_id,
                    "agent": agent,
                }
            else:
                event_data = {
                    "pane_id": pane_id,
                    "workspace_id": workspace_id,
                }
            env.update(
                {
                    "HERDR_TEST_EVENTS": str(events),
                    "SET": str(fake_repo) + "/",
                    "HERDR_PLUGIN_EVENT_JSON": json.dumps(
                        {
                            "event": event_name.replace(".", "_"),
                            "data": event_data,
                        }
                    ),
                    "HERDR_PLUGIN_EVENT": event_name,
                    "HERDR_PLUGIN_CONTEXT_JSON": json.dumps({"workspace_id": workspace_id}),
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
        # tab名はclaudeの会話概要（title_text）先頭10文字にtruncateされたもの。
        self.assertTrue(
            title_line.startswith("title=CLAUDE_IDDONE Claude完了 🖥️ai-work:Herdr通知をカス.. 🕰️"),
            title_line,
        )
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
        self.assertTrue(
            any(
                line.startswith("title=CLAUDE_IDWAIT Claude入力待ち 🖥️ai-work:Herdr通知をカス.. 🕰️")
                for line in events
            )
        )

    def test_idle_working_unknown_do_not_notify(self):
        for agent_status in ("idle", "working", "unknown", ""):
            with self.subTest(agent_status=agent_status):
                result, events = self.run_plugin(agent_status=agent_status)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(events, [])

    def test_non_status_events_do_not_notify(self):
        for event_name in ("pane.agent_detected", "pane.focused"):
            with self.subTest(event_name=event_name):
                result, events = self.run_plugin(
                    agent_status="done",
                    event_name=event_name,
                )

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

    def test_missing_tab_id_omits_screen_label(self):
        # tab_id が取れない -> tab get 自体が呼ばれず base_label が未設定 -> screen_label 省略。
        result, events = self.run_plugin(agent_status="done", include_tab_id=False)

        self.assertEqual(result.returncode, 0, result.stderr)
        title_line = next(line for line in events if line.startswith("title="))
        self.assertNotIn("🖥️", title_line)

    def test_missing_tab_label_omits_screen_label(self):
        # tab get は成功するが応答の label が空 -> base_label も空 -> screen_label 省略
        # （会話概要へはフォールバックしない。title_text は概要置換を避けるため無効化）。
        result, events = self.run_plugin(agent_status="done", tab_label="", title_text="")

        self.assertEqual(result.returncode, 0, result.stderr)
        title_line = next(line for line in events if line.startswith("title="))
        self.assertNotIn("🖥️", title_line)

    def test_missing_workspace_label_omits_screen_label(self):
        result, events = self.run_plugin(agent_status="done", ws_label="")

        self.assertEqual(result.returncode, 0, result.stderr)
        title_line = next(line for line in events if line.startswith("title="))
        self.assertNotIn("🖥️", title_line)

    def test_screen_label_format_is_colon_separated(self):
        # 会話概要への置換を避けるため title_text を無効化し、素のタブ名(tab_label)を使う。
        result, events = self.run_plugin(
            agent_status="done", ws_label="ws2", tab_label="tab7", title_text=""
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        title_line = next(line for line in events if line.startswith("title="))
        self.assertIn("🖥️ws2:tab7", title_line)

    def test_screen_label_truncates_long_names(self):
        # space名・tab名は10文字を超えると先頭10文字+".."に丸められる（超えなければそのまま）。
        # 日本語もzshの ${str[1,10]} が1文字=1カウントで切るため境界は文字数ベース。
        cases = (
            ("ascii_ws_9_chars_kept", "a" * 9, "tab", "🖥️" + "a" * 9 + ":tab"),
            ("ascii_ws_10_chars_kept", "a" * 10, "tab", "🖥️" + "a" * 10 + ":tab"),
            ("ascii_ws_11_chars_truncated", "a" * 11, "tab", "🖥️" + "a" * 10 + "..:tab"),
            ("japanese_tab_10_chars_kept", "ws", "あ" * 10, "🖥️ws:" + "あ" * 10),
            ("japanese_tab_11_chars_truncated", "ws", "あ" * 11, "🖥️ws:" + "あ" * 10 + ".."),
        )
        for name, ws_label, tab_label, expected in cases:
            with self.subTest(name=name):
                result, events = self.run_plugin(
                    agent_status="done",
                    ws_label=ws_label,
                    tab_label=tab_label,
                    title_text="",
                )

                self.assertEqual(result.returncode, 0, result.stderr)
                title_line = next(line for line in events if line.startswith("title="))
                self.assertIn(expected, title_line)

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
        event_name: str = "pane.agent_status_changed",
        initial_managed_label: str | None = None,
        state_observer: list[str | None] | None = None,
        socket_path: str = "/tmp/herdr.sock",
        include_pane_agent_key: bool | None = None,
        input_wait_marker: str | None = None,
        marker_age_seconds: int = 0,
        marker_observer: list[str | None] | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fake_repo = root / "repo"
            fake_bin = root / "bin"
            fake_bin.mkdir()
            rename_calls = root / "rename_calls"
            state_root = root / "state"
            cache_dir = root / "cache"

            def state_key(value: str) -> str:
                return "".join(
                    char if char.isascii() and (char.isalnum() or char in "._-") else "_"
                    for char in value
                )

            state_file = (
                state_root
                / "tab-labels"
                / state_key(socket_path)
                / state_key(tab_id)
            )
            if initial_managed_label is not None:
                state_file.parent.mkdir(parents=True)
                state_file.write_text(initial_managed_label + "\n", encoding="utf-8")

            # シェル所有✋マーカー（herdr_status_icon.shと同じキー式）。存在中は
            # プラグインが状態グリフを✋にピン留めすることを検証する
            marker_file = (
                cache_dir
                / "herdr-shell-status"
                / state_key(socket_path)
                / state_key(tab_id)
            )
            if input_wait_marker is not None:
                marker_file.parent.mkdir(parents=True)
                marker_file.write_text(input_wait_marker + "\n", encoding="utf-8")
                if marker_age_seconds:
                    past = marker_file.stat().st_mtime - marker_age_seconds
                    os.utime(marker_file, (past, past))

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
            # herdr_status_icon.sh はプラグインが✋マーカーreadヘルパーとしてsourceする。
            # コピーし忘れるとsource失敗がfail-safeで握り潰されピンが動かないまま
            # テストが緑になるため、ピン発火を直接アサートするテストと対で守る。
            for name in (
                "tmux_emoji.conf",
                "tmux_emoji.py",
                "tmux_window_name.py",
                "herdr_status_icon.sh",
            ):
                real_file = REPO_ROOT / "shell/tmux" / name
                (fake_tmux_dir / name).write_text(
                    real_file.read_text(encoding="utf-8"), encoding="utf-8"
                )

            # 実環境ではagent未検出paneのpane getにagent/agent_sessionキー自体が
            # 存在しない。include_pane_agent_key=None（既定）はその実挙動に合わせ、
            # agentが空ならキーを省略する。Trueで空文字キー明示の境界も再現できる。
            if include_pane_agent_key is None:
                include_pane_agent_key = bool(agent)
            pane_result = {
                "result": {
                    "pane": {
                        **({"agent": agent} if include_pane_agent_key else {}),
                        "agent_status": agent_status,
                        "terminal_title_stripped": title_text,
                        **(
                            {"agent_session": {"value": "session-abc"}}
                            if agent
                            else {}
                        ),
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
            if event_name == "pane.agent_status_changed":
                event_data = {
                    "pane_id": pane_id,
                    "workspace_id": workspace_id,
                    "agent_status": agent_status,
                    "agent": agent,
                }
            elif event_name == "pane.agent_detected":
                event_data = {
                    "pane_id": pane_id,
                    "workspace_id": workspace_id,
                    "agent": agent,
                }
            else:
                event_data = {
                    "pane_id": pane_id,
                    "workspace_id": workspace_id,
                }
            env.update(
                {
                    "HERDR_TEST_EVENTS": str(root / "events"),
                    "HERDR_TEST_RENAME_CALLS": str(rename_calls),
                    "SET": str(fake_repo) + "/",
                    "HERDR_PLUGIN_EVENT_JSON": json.dumps(
                        {
                            "event": event_name.replace(".", "_"),
                            "data": event_data,
                        }
                    ),
                    "HERDR_PLUGIN_EVENT": event_name,
                    "HERDR_PLUGIN_CONTEXT_JSON": json.dumps(
                        {"workspace_id": workspace_id, "tab_label": "2"}
                    ),
                    "HERDR_PLUGIN_STATE_DIR": str(state_root),
                    "HERDR_SOCKET_PATH": socket_path,
                    "HERDR_PANE_ID": pane_id,
                    "HERDR_WORKSPACE_ID": workspace_id,
                    "PATH": ":".join(path_entries),
                    # 実環境 ~/.cache のマーカーがテストへ漏れ込まないよう必ず隔離する
                    "XDG_CACHE_HOME": str(cache_dir),
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
            if state_observer is not None:
                state_observer.append(
                    state_file.read_text(encoding="utf-8").rstrip("\n")
                    if state_file.exists()
                    else None
                )
            if marker_observer is not None:
                marker_observer.append(
                    marker_file.read_text(encoding="utf-8").rstrip("\n")
                    if marker_file.exists()
                    else None
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

    def test_codex_numeric_label_is_not_replaced_by_conversation_title(self):
        # Conversation-title labeling is claude-only; codex keeps its identifier
        # emoji + status icon but the numeric label is left untouched even though
        # codex also sets terminal_title_stripped to a conversation summary.
        state = []
        result, calls = self.run_plugin(
            agent="codex",
            agent_status="working",
            tab_status="working",
            current_label="1",
            title_text="ここに会話概要が入る",
            state_observer=state,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 🪷🤖1"])
        self.assertEqual(state, [None])

    def test_codex_custom_label_survives_conversation_title(self):
        result, calls = self.run_plugin(
            agent="codex",
            agent_status="done",
            tab_status="done",
            current_label="gm",
            title_text="ここに会話概要が入る",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 🪷✅gm"])

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
        state = []
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="working",
            tab_status="working",
            current_label="1",
            title_text="ここに会話概要が入る",
            state_observer=state,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 ✴️🤖ここに会話概要が入る"])
        self.assertEqual(state, ["ここに会話概要が入る"])

    def test_conversation_title_length_boundary(self):
        cases = (
            (19, 19),
            (20, 20),
            (21, 20),
        )
        for input_length, expected_length in cases:
            with self.subTest(input_length=input_length):
                title_text = "あ" * input_length
                result, calls = self.run_plugin(
                    agent="claude",
                    agent_status="working",
                    tab_status="working",
                    current_label="1",
                    title_text=title_text,
                )

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(calls, ["w1:t1 ✴️🤖" + "あ" * expected_length])

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

    def test_placeholder_conversation_title_falls_back_to_current_label(self):
        for title_text in ("", "Claude Code", "Codex", "Gemini"):
            with self.subTest(title_text=title_text):
                state = []
                result, calls = self.run_plugin(
                    agent="claude",
                    agent_status="working",
                    tab_status="working",
                    current_label="1",
                    title_text=title_text,
                    event_name="pane.focused",
                    state_observer=state,
                )

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(calls, ["w1:t1 ✴️🤖1"])
                self.assertEqual(state, [None])

    def test_placeholder_title_restores_last_managed_label(self):
        for title_text in ("", "Claude Code", "Codex", "Gemini"):
            with self.subTest(title_text=title_text):
                state = []
                result, calls = self.run_plugin(
                    agent="claude",
                    agent_status="working",
                    tab_status="working",
                    current_label="Claude Code",
                    title_text=title_text,
                    event_name="pane.focused",
                    initial_managed_label="直前の概要",
                    state_observer=state,
                )

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(calls, ["w1:t1 ✴️🤖直前の概要"])
                self.assertEqual(state, ["直前の概要"])

    def test_known_agent_default_label_is_replaced_by_conversation_title(self):
        # HerdrがAI検出タブに自動命名する既知ラベル（'Claude Code'等）も、
        # 連番数字と同様に会話概要へ差し替える対象。
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="done",
            tab_status="done",
            current_label="Claude Code",
            title_text="タブ名の修正作業",
            event_name="pane.agent_detected",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 ✴️✅タブ名の修正作業"])

    def test_known_agent_default_label_working_icon(self):
        # 会話概要でのラベル差し替えはclaude限定。codexのHerdrデフォルトラベル
        # （"Codex"）は概要へは差し替わらず、識別絵文字＋状態アイコンのみ付く。
        result, calls = self.run_plugin(
            agent="codex",
            agent_status="working",
            tab_status="working",
            current_label="Codex",
            title_text="バグ調査",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 🪷🤖Codex"])

    def test_cwd_path_title_is_not_adopted_as_label(self):
        # AI起動直後などterminal_titleがcwdフルパスになっている瞬間にプラグインが
        # 発火しても、フルパスは会話概要とみなさずタブ名に採用しない
        # （ai-all/review実行時にタブ名がフルパス化する回帰のガード）。
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="working",
            tab_status="working",
            current_label="Claude Code",
            title_text="/Users/a13596/Desktop/repository/SettingFiles",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 ✴️🤖Claude Code"])

    def test_cwd_path_title_codex(self):
        # 先頭20文字で切れたフルパス断片（実バグ再現形）でも同様に採用しない。
        result, calls = self.run_plugin(
            agent="codex",
            agent_status="working",
            tab_status="working",
            current_label="Codex",
            title_text="/Users/a13596/Deskt",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 🪷🤖Codex"])

    def test_legit_slash_title_still_adopted(self):
        # スラッシュを含む正当な会話概要（スペースを伴う）まで誤って弾かないことの
        # 回帰防止（is_herdr_default_labelのパス判定はスペース無しに限定している）。
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="working",
            tab_status="working",
            current_label="Claude Code",
            title_text="feat/x を実装",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 ✴️🤖feat/x を実装"])

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

    def test_pane_focus_refreshes_managed_conversation_title(self):
        state = []
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="working",
            tab_status="working",
            current_label="✴️🤖古い概要",
            title_text="新しい概要",
            event_name="pane.focused",
            initial_managed_label="古い概要",
            state_observer=state,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 ✴️🤖新しい概要"])
        self.assertEqual(state, ["新しい概要"])

    def test_pane_focus_preserves_manual_label_after_managed_label(self):
        state = []
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="working",
            tab_status="working",
            current_label="✴️🤖手動名",
            title_text="新しい概要",
            event_name="pane.focused",
            initial_managed_label="古い概要",
            state_observer=state,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, [])
        self.assertEqual(state, ["古い概要"])

    def test_non_agent_pane_title_is_not_adopted(self):
        # 非AI pane（Nvim等）のターミナルタイトルは会話概要ではないため、
        # デフォルト連番ラベルでもタブ名に採用しない
        # （git commit時のCOMMIT_EDITMSG乗っ取りの回帰ガード）。
        # agentキー欠落（実環境の非agent pane）と空文字キーの両境界を検証する。
        for include_pane_agent_key in (False, True):
            with self.subTest(include_pane_agent_key=include_pane_agent_key):
                state = []
                result, calls = self.run_plugin(
                    agent="",
                    tab_status="unknown",
                    current_label="3",
                    title_text="COMMIT_EDITMSG + (~/repos/x/.git) - Nvim",
                    event_name="pane.focused",
                    include_pane_agent_key=include_pane_agent_key,
                    state_observer=state,
                )

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(calls, [])
                self.assertEqual(state, [None])

    def test_non_agent_pane_does_not_readopt_via_state_file(self):
        # 過去に自動管理されたタブ（ラベル==状態ファイル値）でも、非AI paneの
        # タイトルでは再差し替えせずラベルと状態ファイルを温存する。
        state = []
        result, calls = self.run_plugin(
            agent="",
            tab_status="unknown",
            current_label="eternal-generate",
            title_text="COMMIT_EDITMSG + (~/repos/x/.git) - Nvim",
            event_name="pane.focused",
            initial_managed_label="eternal-generate",
            state_observer=state,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, [])
        self.assertEqual(state, ["eternal-generate"])

    def test_replaced_label_is_stable_on_next_fire(self):
        state = []
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="done",
            tab_status="done",
            current_label="✴️✅タブ名の修正作業",
            title_text="タブ名の修正作業",
            event_name="pane.focused",
            initial_managed_label="タブ名の修正作業",
            state_observer=state,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, [])
        self.assertEqual(state, ["タブ名の修正作業"])

    # --- シェル所有✋マーカー存在中のグリフピン留め検証 ---
    # プラグインのラベル再構築（agent_status由来アイコン＋会話概要追従）が、シェルが
    # 設置した入力待ち✋を潰さないこと（優先度 ✋>❌>🤖>✅ の維持）を検証する。

    def test_marker_pins_wait_over_working_icon(self):
        # ピンが実際に発火したことをrename引数で直接アサートする（fake repoへの
        # herdr_status_icon.shコピー漏れはこのテストが検出する）
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="working",
            tab_status="working",
            current_label="✴️✋1",
            title_text="",
            input_wait_marker="✋",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, [])

    def test_marker_pins_wait_over_completed_icon(self):
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="done",
            tab_status="done",
            current_label="✴️✋1",
            title_text="",
            input_wait_marker="✋",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, [])

    def test_marker_pin_updates_icon_when_label_lacks_it(self):
        # 現ラベルに✋が無い（プラグインが一度潰した後など）場合はピンで復元する
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="working",
            tab_status="working",
            current_label="✴️🤖1",
            title_text="",
            input_wait_marker="✋",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 ✴️✋1"])

    def test_marker_preserves_wait_on_agentless_pane_focus(self):
        # AI未検出タブ（tab_status空）のpane.focusedは従来アイコンを全部剥がして
        # いた。マーカー存在中は✋を維持し、renameも発生しない
        result, calls = self.run_plugin(
            agent="",
            agent_status="",
            tab_status="",
            current_label="✋main",
            title_text="",
            event_name="pane.focused",
            input_wait_marker="✋",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, [])

    def test_marker_pin_keeps_conversation_title_follow(self):
        # ピンはグリフだけ差し替え、会話概要へのベース名追従とstate file記録は
        # そのまま活きる（state fileには素のタイトルが入る）
        state = []
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="working",
            tab_status="working",
            current_label="1",
            title_text="タブ名の修正作業",
            input_wait_marker="✋",
            state_observer=state,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 ✴️✋タブ名の修正作業"])
        self.assertEqual(state, ["タブ名の修正作業"])

    def test_stale_marker_is_ignored_and_deleted(self):
        markers = []
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="working",
            tab_status="working",
            current_label="✴️✋1",
            title_text="",
            input_wait_marker="✋",
            marker_age_seconds=86400 + 60,
            marker_observer=markers,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 ✴️🤖1"])
        self.assertEqual(markers, [None])

    def test_garbage_marker_is_ignored_and_deleted(self):
        markers = []
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="working",
            tab_status="working",
            current_label="✴️✋1",
            title_text="",
            input_wait_marker="not-an-emoji",
            marker_observer=markers,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 ✴️🤖1"])
        self.assertEqual(markers, [None])

    def test_no_marker_keeps_existing_rebuild_behavior(self):
        result, calls = self.run_plugin(
            agent="claude",
            agent_status="working",
            tab_status="working",
            current_label="✴️✋1",
            title_text="",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["w1:t1 ✴️🤖1"])


if __name__ == "__main__":
    unittest.main()
