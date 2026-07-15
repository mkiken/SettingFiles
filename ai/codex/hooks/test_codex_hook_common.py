import json
import os
import shlex
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from codex_hook_common import (
    analyze_hook_input,
    assistant_response_needs_user_input,
    extract_context_usage,
    format_analysis_for_eval,
    is_system_user_message,
)


def write_jsonl(path: Path, events: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output:
        for event in events:
            output.write(json.dumps(event, ensure_ascii=False) + "\n")


class AssistantResponseNeedsUserInputTest(unittest.TestCase):
    def test_detects_only_recent_plain_text_requests(self):
        cases = [
            (
                "implementation design regression",
                "この設計で進める場合、JenkinsジョブのURLと利用可能な起動方法を教えてください。"
                "あるいは、両ビルドURLを共有してください。承認と情報受領後に実装へ進みます。",
                True,
            ),
            (
                "input request followed by next step",
                "必要な値を入力してください。受領後に処理を再開します。",
                True,
            ),
            ("request at end", "利用方法を教えてください。", True),
            ("request outside scan tail", "利用方法を教えてください。" + (" 完了。" * 200), False),
            (
                "reported request",
                "ユーザーから利用方法を教えてくださいと依頼された。対応は完了した。",
                False,
            ),
            (
                "inline code request",
                "表示文言は `利用方法を教えてください。` です。実装済み。",
                False,
            ),
            ("completion summary", "実装した。テストも通過した。変更はコミットしていない。", False),
        ]

        for name, message, expected in cases:
            with self.subTest(name=name):
                self.assertEqual(assistant_response_needs_user_input(message), expected)

    def test_detects_approval_question_followed_by_revision_request(self):
        message = """
        ## 実装設計

        ### 変更方針

        - 変更する振る舞い: なし。テスト網羅性のみ追加
        - 変更しない範囲: validator 本体、エラーメッセージ、既存ケースの期待値

        この設計で実装を進めてよろしいですか？修正点があればお知らせください。
        """

        self.assertTrue(assistant_response_needs_user_input(message))

    def test_detects_question_in_tail_even_when_not_at_end(self):
        message = "実装方針は上記の通り。この設計で進めてよろしいですか？修正点があればお知らせください。"

        self.assertTrue(assistant_response_needs_user_input(message))

    def test_detects_proposed_plan_with_intro_text(self):
        message = """
        修正した。

        <proposed_plan>
        # Codex Hook Notification Fix

        ## Summary
        - Plan Mode の設計確認は応答待ち通知にする。
        </proposed_plan>
        """

        self.assertTrue(assistant_response_needs_user_input(message))

    def test_detects_compacted_proposed_plan_with_intro_text(self):
        message = "修正した。 <proposed_plan> # Codex Hook Notification Fix ## Summary - Plan Mode の設計確認は応答待ち通知にする。 </proposed_plan>"

        self.assertTrue(assistant_response_needs_user_input(message))

    def test_ignores_url_query_in_tail(self):
        message = "確認した。詳細は https://example.com/search?q=codex を参照。"

        self.assertFalse(assistant_response_needs_user_input(message))

    def test_ignores_inline_code_question_mark_in_tail(self):
        message = "原因は lazy quantifier の `.+?` にある。修正済み。"

        self.assertFalse(assistant_response_needs_user_input(message))

    def test_ignores_fenced_code_question_mark_in_tail(self):
        message = """
        修正した。

        ```python
        pattern = r".+?"
        ```

        テストも通過した。
        """

        self.assertFalse(assistant_response_needs_user_input(message))

    def test_ignores_fenced_code_proposed_plan_example(self):
        message = """
        形式は次の通り。

        ```markdown
        <proposed_plan>
        # Example
        </proposed_plan>
        ```

        説明は以上。
        """

        self.assertFalse(assistant_response_needs_user_input(message))

    def test_ignores_inline_code_proposed_plan_example(self):
        message = "タグは `<proposed_plan>...</proposed_plan>` を使う。説明は以上。"

        self.assertFalse(assistant_response_needs_user_input(message))

    def test_ignores_old_question_outside_tail(self):
        message = "この方針で進めてよろしいですか？" + (" 完了。" * 200)

        self.assertFalse(assistant_response_needs_user_input(message))

    def test_ignores_completion_summary(self):
        message = "実装した。テストも通過した。変更はコミットしていない。"

        self.assertFalse(assistant_response_needs_user_input(message))


class IsSystemUserMessageTest(unittest.TestCase):
    def test_internal_injections_and_user_message_boundaries(self):
        cases = [
            (
                "path-qualified AGENTS injection",
                "# AGENTS.md instructions for /repo\n\n<INSTRUCTIONS>rules</INSTRUCTIONS>",
                True,
            ),
            (
                "path-qualified AGENTS injection with environment context",
                "# AGENTS.md instructions for /repo <INSTRUCTIONS>rules</INSTRUCTIONS> "
                "<environment_context><cwd>/repo</cwd></environment_context>",
                True,
            ),
            (
                "path-qualified AGENTS injection with missing scope",
                "# AGENTS.md instructions for <INSTRUCTIONS>rules</INSTRUCTIONS>",
                False,
            ),
            (
                "incomplete path-qualified AGENTS injection",
                "# AGENTS.md instructions for /repo <INSTRUCTIONS>rules",
                False,
            ),
            (
                "path-qualified AGENTS injection with trailing user text",
                "# AGENTS.md instructions for /repo <INSTRUCTIONS>rules</INSTRUCTIONS> please help",
                False,
            ),
            (
                "path-qualified AGENTS injection with sibling blocks",
                "# AGENTS.md instructions for /repo <INSTRUCTIONS>one</INSTRUCTIONS> "
                "<INSTRUCTIONS>two</INSTRUCTIONS>",
                False,
            ),
            (
                "AGENTS instructions format user text",
                "# AGENTS.md instructions format this response",
                False,
            ),
            (
                "normalized AGENTS injection",
                "# AGENTS.md instructions <INSTRUCTIONS>rules</INSTRUCTIONS>",
                True,
            ),
            (
                "normalized AGENTS injection with environment context",
                "# AGENTS.md instructions <INSTRUCTIONS>rules</INSTRUCTIONS> "
                "<environment_context><cwd>/repo</cwd></environment_context>",
                True,
            ),
            (
                "incomplete normalized AGENTS injection",
                "# AGENTS.md instructions <INSTRUCTIONS>rules",
                False,
            ),
            (
                "normalized AGENTS injection with trailing user text",
                "# AGENTS.md instructions <INSTRUCTIONS>rules</INSTRUCTIONS> please help",
                False,
            ),
            (
                "normalized AGENTS injection with incomplete environment context",
                "# AGENTS.md instructions <INSTRUCTIONS>rules</INSTRUCTIONS> "
                "<environment_context><cwd>/repo</cwd>",
                False,
            ),
            ("skill block", "<skill>skill instructions</skill>", True),
            (
                "subagent notification block with surrounding whitespace",
                "  <subagent_notification>done</subagent_notification>\n",
                True,
            ),
            ("empty turn aborted block", "<turn_aborted></turn_aborted>", True),
            (
                "multiline shell command block",
                "<user_shell_command>\necho hello\n</user_shell_command>",
                True,
            ),
            ("ordinary request", "通知内容を直して", False),
            ("skill command", "$pr-comment-implement", False),
            (
                "skill tag mentioned in ordinary text",
                "通知に `<skill>` と表示されるのを直して",
                False,
            ),
            ("similar tag", "<skills>skill instructions</skills>", False),
            ("incomplete block", "<skill>skill instructions", False),
            (
                "mismatched closing tag",
                "<skill>skill instructions</subagent_notification>",
                False,
            ),
            ("block with leading user text", "explain <skill>instructions</skill>", False),
            ("block with trailing user text", "<skill>instructions</skill> please", False),
            (
                "sibling blocks with user text between them",
                "<skill>one</skill> please help <skill>two</skill>",
                False,
            ),
        ]

        for label, message, expected in cases:
            with self.subTest(label):
                self.assertEqual(is_system_user_message(message), expected)


class AnalyzeHookInputFallbackTest(unittest.TestCase):
    def test_ignores_internal_injections_when_selecting_last_user_message(self):
        real_command = "$pr-comment-implement https://github.com/example/repo/pull/123#discussion_r456"

        with tempfile.TemporaryDirectory() as codex_home:
            transcript_path = Path(codex_home) / "sessions" / "internal-injections.jsonl"
            user_messages = [
                "# AGENTS.md instructions for /repo\n\n<INSTRUCTIONS>rules</INSTRUCTIONS>",
                "# AGENTS.md instructions\n\n<INSTRUCTIONS>normalized rules</INSTRUCTIONS>\n"
                "<environment_context><cwd>/repo</cwd></environment_context>",
                real_command,
                "<skill>skill instructions</skill>",
                "<subagent_notification>subagent finished</subagent_notification>",
                "<turn_aborted>the previous turn was aborted</turn_aborted>",
                "<user_shell_command>echo hello</user_shell_command>",
            ]
            events = [
                {
                    "timestamp": f"2026-07-15T14:00:0{index}.000Z",
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": message}],
                    },
                }
                for index, message in enumerate(user_messages)
            ]
            events.append(
                {
                    "timestamp": "2026-07-15T14:00:10.000Z",
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "対応しました。"}],
                    },
                }
            )
            write_jsonl(transcript_path, events)

            result = analyze_hook_input({"transcript_path": str(transcript_path)})

        self.assertEqual(result["last_user_message"], real_command)
        self.assertEqual(result["user_message_count"], 1)

    def test_detects_proposed_plan_from_transcript_without_normalizing_detection_text(self):
        session_id = "019ea532-60d3-7c03-a1d5-09e8778c32a5"

        with tempfile.TemporaryDirectory() as codex_home:
            transcript_path = (
                Path(codex_home)
                / "sessions"
                / "2026"
                / "06"
                / "08"
                / f"rollout-2026-06-08T12-06-42-{session_id}.jsonl"
            )
            write_jsonl(
                transcript_path,
                [
                    {
                        "timestamp": "2026-06-08T03:06:42.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": "user",
                            "content": [{"type": "input_text", "text": "設計を確認したい"}],
                        },
                    },
                    {
                        "timestamp": "2026-06-08T03:08:23.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": "修正した。\n\n<proposed_plan>\n# Codex Hook Notification Fix\n\n## Summary\n- Plan Mode の設計確認は応答待ち通知にする。\n</proposed_plan>",
                                }
                            ],
                        },
                    },
                ],
            )

            with patch.dict(os.environ, {"CODEX_HOME": codex_home}):
                result = analyze_hook_input(
                    {"hook_event_name": "Stop", "session_id": session_id, "transcript_path": str(transcript_path)}
                )

        self.assertTrue(result["waiting_for_user_response"])
        self.assertEqual(
            result["last_assistant_message"],
            "修正した。 <proposed_plan> # Codex Hook Notification Fix ## Summary - Plan Mode の設計確認は応答待ち通知にする。 </proposed_plan>",
        )

    def test_resolves_transcript_by_session_id(self):
        session_id = "019e68fe-273e-7592-8fbe-135395cf1c9f"

        with tempfile.TemporaryDirectory() as codex_home:
            transcript_path = (
                Path(codex_home)
                / "sessions"
                / "2026"
                / "05"
                / "27"
                / f"rollout-2026-05-27T19-32-27-{session_id}.jsonl"
            )
            write_jsonl(
                transcript_path,
                [
                    {
                        "timestamp": "2026-05-27T10:00:00.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": "user",
                            "content": [{"type": "input_text", "text": "通常会話の内容"}],
                        },
                    },
                    {
                        "timestamp": "2026-05-27T10:00:10.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": "assistant",
                            "content": [{"type": "output_text", "text": "通常会話への返答"}],
                        },
                    },
                ],
            )

            with patch.dict(os.environ, {"CODEX_HOME": codex_home}):
                result = analyze_hook_input({"hook_event_name": "Stop", "session_id": session_id})

        self.assertEqual(result["last_user_message"], "通常会話の内容")
        self.assertEqual(result["last_assistant_message"], "通常会話への返答")
        self.assertEqual(result["user_message_count"], 1)
        self.assertEqual(result["assistant_message_count"], 1)
        self.assertEqual(result["first_timestamp"], "2026-05-27T10:00:00.000Z")
        self.assertEqual(result["last_timestamp"], "2026-05-27T10:00:10.000Z")

    def test_recovers_side_session_from_history_and_logs(self):
        session_id = "019e68f4-5ce6-7bd2-a35d-2146d0be8019"

        with tempfile.TemporaryDirectory() as codex_home:
            codex_home_path = Path(codex_home)
            write_jsonl(
                codex_home_path / "history.jsonl",
                [
                    {"session_id": "other-session", "ts": 1779877300, "text": "別の会話"},
                    {"session_id": session_id, "ts": 1779877390, "text": "spawn_agentってなに？"},
                ],
            )

            logs_path = codex_home_path / "logs_2.sqlite"
            connection = sqlite3.connect(logs_path)
            try:
                connection.execute(
                    """
                    CREATE TABLE logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ts INTEGER NOT NULL,
                        ts_nanos INTEGER NOT NULL,
                        feedback_log_body TEXT,
                        thread_id TEXT
                    )
                    """
                )
                event = {
                    "type": "response.output_text.done",
                    "text": "spawn_agent は別の AI サブエージェントを起動する内部ツールです。",
                }
                connection.execute(
                    "INSERT INTO logs (ts, ts_nanos, feedback_log_body, thread_id) VALUES (?, ?, ?, ?)",
                    (
                        1779877397,
                        0,
                        "prefix websocket event: " + json.dumps(event, ensure_ascii=False),
                        session_id,
                    ),
                )
                connection.commit()
            finally:
                connection.close()

            with patch.dict(os.environ, {"CODEX_HOME": codex_home}):
                result = analyze_hook_input(
                    {"hook_event_name": "Stop", "session_id": session_id, "transcript_path": None}
                )

        self.assertEqual(result["last_user_message"], "spawn_agentってなに？")
        self.assertEqual(
            result["last_assistant_message"],
            "spawn_agent は別の AI サブエージェントを起動する内部ツールです。",
        )
        self.assertEqual(result["user_message_count"], 1)
        self.assertEqual(result["assistant_message_count"], 1)
        self.assertTrue(result["first_timestamp"])
        self.assertTrue(result["last_timestamp"])


class ExtractContextUsageTest(unittest.TestCase):
    def test_uses_last_token_usage_for_context_window_percent(self):
        with tempfile.TemporaryDirectory() as codex_home:
            transcript_path = Path(codex_home) / "sessions" / "context.jsonl"
            write_jsonl(
                transcript_path,
                [
                    {
                        "type": "event_msg",
                        "payload": {
                            "type": "token_count",
                            "info": {
                                "total_token_usage": {"total_tokens": 774025},
                                "last_token_usage": {"total_tokens": 46950},
                                "model_context_window": 258400,
                            },
                        },
                    }
                ],
            )

            result = extract_context_usage({"transcript_path": str(transcript_path)})

        self.assertEqual(result["used_pct"], 14)
        self.assertEqual(result["remaining_pct"], 86)
        self.assertEqual(result["total_tokens"], 774025)
        self.assertEqual(result["context_window_tokens"], 46950)
        self.assertEqual(result["model_context_window"], 258400)

    def test_baseline_tokens_are_zero_percent_used(self):
        with tempfile.TemporaryDirectory() as codex_home:
            transcript_path = Path(codex_home) / "sessions" / "context.jsonl"
            write_jsonl(
                transcript_path,
                [
                    {
                        "type": "event_msg",
                        "payload": {
                            "type": "token_count",
                            "info": {
                                "total_token_usage": {"total_tokens": 12000},
                                "last_token_usage": {"total_tokens": 12000},
                                "model_context_window": 258400,
                            },
                        },
                    }
                ],
            )

            result = extract_context_usage({"transcript_path": str(transcript_path)})

        self.assertEqual(result["used_pct"], 0)
        self.assertEqual(result["remaining_pct"], 100)

    def test_missing_last_token_usage_returns_empty_result(self):
        with tempfile.TemporaryDirectory() as codex_home:
            transcript_path = Path(codex_home) / "sessions" / "context.jsonl"
            write_jsonl(
                transcript_path,
                [
                    {
                        "type": "event_msg",
                        "payload": {
                            "type": "token_count",
                            "info": {
                                "total_token_usage": {"total_tokens": 774025},
                                "model_context_window": 258400,
                            },
                        },
                    }
                ],
            )

            result = extract_context_usage({"transcript_path": str(transcript_path)})

        self.assertEqual(result, {})


class FormatAnalysisForEvalTimeFieldsTest(unittest.TestCase):
    @staticmethod
    def build_result(first_timestamp, last_timestamp):
        return {
            "is_subagent_session": False,
            "waiting_for_user_response": False,
            "last_user_message": "hello",
            "last_assistant_message": "done",
            "user_message_count": 1,
            "assistant_message_count": 1,
            "first_timestamp": first_timestamp,
            "last_timestamp": last_timestamp,
        }

    @staticmethod
    def parse_fields(output):
        return dict(line.split("=", 1) for line in output.splitlines())

    def test_time_fields(self):
        cases = [
            ("both timestamps", "2026-07-12T00:00:00.000Z", "2026-07-12T01:23:45.000Z", "1h23m", "10:23:45"),
            ("first missing keeps completion", "", "2026-07-12T01:23:45.000Z", "", "10:23:45"),
            ("last missing", "2026-07-12T00:00:00.000Z", "", "", ""),
            ("both missing", "", "", "", ""),
            ("invalid last", "2026-07-12T00:00:00.000Z", "not-a-timestamp", "", ""),
            ("no fractional seconds", "2026-07-12T00:00:00Z", "2026-07-12T00:00:05Z", "5s", "09:00:05"),
        ]
        for label, first, last, duration, completion in cases:
            with self.subTest(label):
                fields = self.parse_fields(format_analysis_for_eval(self.build_result(first, last)))
                self.assertEqual(fields["SESSION_DURATION_FORMATTED"], shlex.quote(duration))
                self.assertEqual(fields["COMPLETION_TIME_JST"], shlex.quote(completion))

    def test_analyze_output_round_trips_through_bash_eval(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            transcript_path = Path(tmp_dir) / "rollout-test.jsonl"
            write_jsonl(
                transcript_path,
                [
                    {
                        "timestamp": "2026-07-12T00:00:00.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": "user",
                            "content": [{"type": "input_text", "text": "it's a \"test\" $var `cmd`"}],
                        },
                    },
                    {
                        "timestamp": "2026-07-12T01:23:45.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": "assistant",
                            "content": [{"type": "output_text", "text": "done"}],
                        },
                    },
                ],
            )

            analysis = format_analysis_for_eval(analyze_hook_input({"transcript_path": str(transcript_path)}))

        script = 'eval "$1"; printf "%s|%s|%s" "$SESSION_DURATION_FORMATTED" "$COMPLETION_TIME_JST" "$LAST_USER_MESSAGE"'
        completed = subprocess.run(
            ["bash", "-c", script, "_", analysis],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(completed.stdout, '1h23m|10:23:45|it\'s a "test" $var `cmd`')


if __name__ == "__main__":
    unittest.main()
