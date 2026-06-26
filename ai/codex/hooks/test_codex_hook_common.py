import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from codex_hook_common import analyze_hook_input, assistant_response_needs_user_input, extract_context_usage


def write_jsonl(path: Path, events: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output:
        for event in events:
            output.write(json.dumps(event, ensure_ascii=False) + "\n")


class AssistantResponseNeedsUserInputTest(unittest.TestCase):
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


class AnalyzeHookInputFallbackTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
