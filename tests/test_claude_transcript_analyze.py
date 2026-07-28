"""shell/tmux/claude_transcript_analyze.py の単体テスト。

bash旧実装（stop-send-notification.sh の行ごとjqループ）とのパリティを固定する。
特にstring content経路の末尾スペース痕跡（長さ<4フィルタが実質<3で動く）を含む。
"""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "shell" / "tmux"))

import claude_transcript_analyze as cta

ANALYZER = REPO_ROOT / "shell" / "tmux" / "claude_transcript_analyze.py"

TS1 = "2026-07-11T12:00:00.000Z"
TS2 = "2026-07-11T12:05:00.000Z"
TS3 = "2026-07-11T12:10:00.000Z"


def user_line(content, **extra):
    return json.dumps({"message": {"role": "user", "content": content}, **extra}, ensure_ascii=False)


def assistant_line(content, **extra):
    return json.dumps({"message": {"role": "assistant", "content": content}, **extra}, ensure_ascii=False)


class TestIsSystemMessage(unittest.TestCase):
    def test_patterns(self):
        cases = [
            # (説明, 入力, 期待: システムメッセージか)
            ("スラッシュコマンドは早期にユーザー入力扱い", "/plan check this", False),
            ("先頭空白付きsystem-reminderタグ", "  <system-reminder>context", True),
            ("local-command-stdoutタグ", "<local-command-stdout>x", True),
            ("command-messageタグ", "<command-message>x", True),
            ("Caveat開始", "Caveat: the messages below are generated", True),
            ("コマンド説明パターン", "# /review - Command Reference", True),
            ("スラッシュなしの見出しは非システム", "# review - reference text", False),
            ("ARGUMENTS:+スペース", "ARGUMENTS: foo", True),
            ("ARGUMENTS:直後スペースなしは非システム（境界）", "ARGUMENTS:foo", False),
            ("4文字ちょうどは非システム（境界）", "abcd", False),
            ("日本語4文字は非システム（境界）", "あいうえ", False),
            ("3文字はシステム扱い", "あいう", True),
            ("task-notificationタグ", "<task-notification><task-id>abc</task-id>", True),
            ("先頭空白付きtask-notificationタグ", "  <task-notification>x", True),
            (
                "task-notification改行潰れ形",
                "<task-notification> <task-id>abc</task-id> <tool-use-id>toolu_x</tool-use-id>",
                True,
            ),
            ("task-で始まる別タグはマッチ対象外", "<task-summary>x", False),
        ]
        for desc, msg, expected in cases:
            with self.subTest(desc=desc):
                self.assertEqual(cta.is_system_message(msg), expected)


class TestContentExtraction(unittest.TestCase):
    def test_string_path_trailing_space_artifact(self):
        # 旧実装のecho|tr|sedは末尾スペースを残すため、3文字メッセージは
        # フィルタ上len 4となり保持される（bashパリティ）
        cases = [
            ("3文字string contentは保持", "続けて", False),
            ("2文字string contentは除外", "はい", True),
        ]
        for desc, raw, expected_system in cases:
            with self.subTest(desc=desc):
                content = cta.extract_string_content(raw)
                self.assertTrue(content.endswith(" "))
                self.assertEqual(cta.is_system_message(content), expected_system)

    def test_array_path_true_length_check(self):
        # array経路は旧実装でもstrip済みのため真の<4判定
        content = cta.extract_array_content([{"type": "text", "text": "続けて"}])
        self.assertEqual(content, "続けて")
        self.assertTrue(cta.is_system_message(content))

    def test_multiline_and_squeeze(self):
        cases = [
            # (説明, 入力, 期待)
            ("改行→スペース+連続スペース詰め", "a\n\nb  c", "a b c "),
            ("タブは温存", "a  \t  b", "a \t b "),
        ]
        for desc, raw, expected in cases:
            with self.subTest(desc=desc):
                self.assertEqual(cta.extract_string_content(raw), expected)

    def test_array_content_joins_text_items_only(self):
        content = cta.extract_array_content(
            [
                {"type": "text", "text": "行1\n行2"},
                {"type": "tool_use", "id": "x"},
                {"type": "text", "text": "行3"},
            ]
        )
        self.assertEqual(content, "行1 行2 行3")


class TestApplyCommandTags(unittest.TestCase):
    def test_cases(self):
        cases = [
            # (説明, 入力, 期待)
            (
                "name+args（args内の連続スペースは詰める）",
                "<command-name>/plan</command-name><command-args>a  b</command-args>",
                "/plan a b",
            ),
            (
                "空のcommand-argsはコマンド名のみ",
                "<command-name>/plan</command-name><command-args></command-args>",
                "/plan",
            ),
            ("タグなしは変更なし", "普通のメッセージです", "普通のメッセージです"),
        ]
        for desc, content, expected in cases:
            with self.subTest(desc=desc):
                self.assertEqual(cta.apply_command_tags(content), expected)


class TestAnalyzeLines(unittest.TestCase):
    def test_empty_input(self):
        for desc, lines in [("空入力", []), ("空行のみ", ["", "   ", "\n"])]:
            with self.subTest(desc=desc):
                result = cta.analyze_lines(lines)
                self.assertEqual(result["last_user_message"], "")
                self.assertEqual(result["user_count"], 0)
                self.assertEqual(result["assistant_count"], 0)
                self.assertEqual(result["first_timestamp"], "")
                self.assertEqual(result["last_timestamp"], "")

    def test_sidechain_and_meta_excluded_from_messages_but_kept_in_timestamps(self):
        result = cta.analyze_lines(
            [
                user_line("サイドチェーンのメッセージ", timestamp=TS1, isSidechain=True),
                user_line("メタ展開のメッセージ", timestamp=TS2, isMeta=True),
            ]
        )
        self.assertEqual(result["user_count"], 0)
        self.assertEqual(result["first_timestamp"], TS1)
        self.assertEqual(result["last_timestamp"], TS2)

    def test_summary_line_excluded_from_timestamps(self):
        result = cta.analyze_lines(
            [
                json.dumps({"type": "summary", "summary": "要約", "timestamp": TS1}),
                user_line("テストを実行してほしい", timestamp=TS2),
            ]
        )
        self.assertEqual(result["first_timestamp"], TS2)
        self.assertEqual(result["last_timestamp"], TS2)

    def test_invalid_timestamps_skipped(self):
        result = cta.analyze_lines(
            [
                json.dumps({"timestamp": None}),
                json.dumps({"timestamp": "null"}),
                json.dumps({"timestamp": ""}),
                user_line("有効なメッセージです", timestamp=TS1),
                json.dumps({"timestamp": "null"}),
                assistant_line([{"type": "text", "text": "了解しました"}], timestamp=TS2),
            ]
        )
        self.assertEqual(result["first_timestamp"], TS1)
        self.assertEqual(result["last_timestamp"], TS2)

    def test_invalid_json_line_skipped(self):
        result = cta.analyze_lines(
            [
                "{broken json",
                user_line("壊れた行の後も処理する", timestamp=TS1),
            ]
        )
        self.assertEqual(result["user_count"], 1)
        self.assertEqual(result["last_user_message"], "壊れた行の後も処理する")

    def test_assistant_array_content_counted_not_leaked(self):
        result = cta.analyze_lines(
            [
                user_line("依頼メッセージです", timestamp=TS1),
                assistant_line(
                    [{"type": "text", "text": "完了しました"}, {"type": "tool_use", "id": "t1"}],
                    timestamp=TS2,
                ),
            ]
        )
        self.assertEqual(result["assistant_count"], 1)
        self.assertEqual(result["last_user_message"], "依頼メッセージです")

    def test_null_string_content_treated_as_empty(self):
        result = cta.analyze_lines([user_line("null")])
        self.assertEqual(result["user_count"], 0)
        self.assertEqual(result["last_user_message"], "")

    def test_last_non_system_user_message_and_count(self):
        result = cta.analyze_lines(
            [
                user_line("最初の依頼メッセージ", timestamp=TS1),
                user_line("<system-reminder>injected context", timestamp=TS2),
                user_line("最後の依頼メッセージ", timestamp=TS3),
            ]
        )
        self.assertEqual(result["user_count"], 2)
        self.assertEqual(result["last_user_message"], "最後の依頼メッセージ")

    def test_task_notification_not_adopted_as_last_user_message(self):
        # 実データ相当: role=user / string content / isMeta・isSidechainなしで記録される
        # サブエージェント完了通知（task-notification）は last_user_message に採用されない
        tn = (
            "<task-notification>\n<task-id>abc123</task-id>\n"
            "<tool-use-id>toolu_x</tool-use-id>\n<status>completed</status>\n"
            "<summary>Agent finished</summary>\n</task-notification>"
        )
        result = cta.analyze_lines(
            [
                user_line("本当のユーザー依頼です", timestamp=TS1),
                user_line(tn, timestamp=TS2),
            ]
        )
        self.assertEqual(result["last_user_message"], "本当のユーザー依頼です")
        self.assertEqual(result["user_count"], 1)

    def test_multiline_user_string_normalized(self):
        result = cta.analyze_lines([user_line("a\n\nb  c teststring")])
        self.assertEqual(result["last_user_message"], "a b c teststring")

    def test_command_tags_expanded_before_filter(self):
        result = cta.analyze_lines(
            [
                user_line(
                    "<command-name>/plan</command-name>"
                    "<command-args>foo  bar</command-args>"
                )
            ]
        )
        self.assertEqual(result["user_count"], 1)
        self.assertEqual(result["last_user_message"], "/plan foo bar")


class TestBuildTimeFields(unittest.TestCase):
    def test_duration_boundaries(self):
        base = "2026-07-11T00:00:00.000Z"
        cases = [
            # (説明, last, 期待duration)
            ("0秒", "2026-07-11T00:00:00.000Z", "0s"),
            ("59秒（分繰り上げ境界の下）", "2026-07-11T00:00:59.000Z", "59s"),
            ("60秒（分表記へ切り替わる境界）", "2026-07-11T00:01:00.000Z", "1m0s"),
            ("3599秒（時繰り上げ境界の下）", "2026-07-11T00:59:59.000Z", "59m59s"),
            ("3600秒（時表記へ切り替わる境界）", "2026-07-11T01:00:00.000Z", "1h0m"),
            ("3661秒", "2026-07-11T01:01:01.000Z", "1h1m"),
        ]
        for desc, last, expected in cases:
            with self.subTest(desc=desc):
                duration, _ = cta.build_time_fields(base, last)
                self.assertEqual(duration, expected)

    def test_completion_time_jst(self):
        cases = [
            # (説明, last, 期待completion)
            ("+9h変換と小数秒除去", "2026-07-11T16:30:05.123Z", "01:30:05"),
            ("小数秒なし・末尾Zは無視（BSD dateパリティ）", "2026-07-11T00:01:00Z", "09:01:00"),
        ]
        for desc, last, expected in cases:
            with self.subTest(desc=desc):
                _, completion = cta.build_time_fields("", last)
                self.assertEqual(completion, expected)

    def test_missing_or_invalid_timestamps(self):
        cases = [
            # (説明, first, last, 期待duration, 期待completion)
            ("両方欠落", "", "", "", ""),
            ("first欠落はdurationのみ空", "", TS1, "", "21:00:00"),
            ("last欠落は両方空", TS1, "", "", ""),
            ("last=nullは両方空", TS1, "null", "", ""),
            ("first不正はdurationのみ空", "garbage", TS1, "", "21:00:00"),
            ("last不正は両方空", TS1, "garbage", "", ""),
        ]
        for desc, first, last, expected_duration, expected_completion in cases:
            with self.subTest(desc=desc):
                duration, completion = cta.build_time_fields(first, last)
                self.assertEqual(duration, expected_duration)
                self.assertEqual(completion, expected_completion)


@unittest.skipUnless(sys.platform == "darwin", "BSD date (-j -f / -r) required")
class TestBashHelperParity(unittest.TestCase):
    """置き換え元のbashヘルパー（format_session_duration / format_completion_time_jst）と
    同一入力で出力が一致することを固定する。"""

    def _run_bash_helpers(self, first, last):
        script = (
            f'source "{REPO_ROOT}/shell/tmux/tmux_notification_title.sh"; '
            f'source "{REPO_ROOT}/shell/tmux/ai_notification_summary.sh"; '
            f'printf "%s\\n%s\\n" '
            f'"$(format_session_duration "{first}" "{last}")" '
            f'"$(format_completion_time_jst "{last}")"'
        )
        proc = subprocess.run(
            ["bash", "-c", script], capture_output=True, text=True, check=True
        )
        duration, completion, _ = proc.stdout.split("\n")
        return duration, completion

    def test_parity_with_bash_helpers(self):
        cases = [
            # (説明, first, last)
            ("時間スケール", "2026-06-27T00:00:00.000Z", "2026-06-27T01:01:01.000Z"),
            ("秒スケール", "2026-06-27T00:00:00.000Z", "2026-06-27T00:00:30.000Z"),
            ("日またぎのJST変換", "2026-07-11T16:00:00.000Z", "2026-07-11T23:59:59.000Z"),
            ("first欠落", "", TS1),
            ("first不正", "garbage", TS1),
        ]
        for desc, first, last in cases:
            with self.subTest(desc=desc):
                self.assertEqual(
                    cta.build_time_fields(first, last),
                    self._run_bash_helpers(first, last),
                )


def launch_result_line(*agent_ids, **extra):
    """async Agent起動のtool_result（実transcriptの形状を再現）を持つuser行。"""
    items = []
    for agent_id in agent_ids:
        text = (
            "Async agent launched successfully. (This tool result is internal metadata)\n"
            f"agentId: {agent_id} (internal ID - do not mention to user)"
        )
        items.append(
            {
                "type": "tool_result",
                "tool_use_id": "toolu_x",
                "content": [{"type": "text", "text": text}],
            }
        )
    return user_line(items, **extra)


def task_notification_line(task_id, **extra):
    return user_line(
        f"<task-notification>\n<task-id>{task_id}</task-id>\n"
        "<status>completed</status>\n</task-notification>",
        **extra,
    )


def schedule_wakeup_line(tool_input, **extra):
    return assistant_line(
        [{"type": "tool_use", "id": "t1", "name": "ScheduleWakeup", "input": tool_input}],
        **extra,
    )


def task_stop_line(task_id, **extra):
    return assistant_line(
        [{"type": "tool_use", "id": "t2", "name": "TaskStop", "input": {"taskId": task_id}}],
        **extra,
    )


def api_error_line(text, error="server_error", **extra):
    """APIエラー行（実transcriptの形状を再現）。isApiErrorMessage/errorはトップレベル。"""
    return json.dumps(
        {
            "type": "assistant",
            "isApiErrorMessage": True,
            "error": error,
            "message": {
                "role": "assistant",
                "stop_reason": "stop_sequence",
                "content": [{"type": "text", "text": text}],
            },
            **extra,
        },
        ensure_ascii=False,
    )


class TestLastTurnApiError(unittest.TestCase):
    def test_cases(self):
        cases = [
            # (説明, 行リスト, 期待LAST_TURN_API_ERROR)
            (
                "エラーが実質末尾（turn_durationのみ後続）",
                [
                    api_error_line("API Error: Connection closed mid-response.", timestamp=TS1),
                    json.dumps({"type": "system", "subtype": "turn_duration", "timestamp": TS2}),
                ],
                "server_error",
            ),
            (
                "物理的な末尾がエラー行",
                [api_error_line("API Error: Connection closed mid-response.", timestamp=TS1)],
                "server_error",
            ),
            (
                "会話継続で復帰（userの会話行でリセット）",
                [
                    api_error_line("API Error: Connection closed mid-response.", timestamp=TS1),
                    user_line("続きをお願い", timestamp=TS2),
                ],
                "",
            ),
            (
                "非会話行のみ後続（リセットしない）",
                [
                    api_error_line("API Error: Connection closed mid-response.", timestamp=TS1),
                    json.dumps({"type": "last-prompt", "leafUuid": "x", "sessionId": "s"}),
                    json.dumps({"type": "ai-title"}),
                    json.dumps(
                        {"type": "queue-operation", "operation": "enqueue", "timestamp": TS2}
                    ),
                ],
                "server_error",
            ),
            (
                "エラーなしの通常セッション",
                [
                    user_line("普通の依頼メッセージ", timestamp=TS1),
                    assistant_line([{"type": "text", "text": "完了しました"}], timestamp=TS2),
                ],
                "",
            ),
            (
                "複数エラー・最後は復帰",
                [
                    api_error_line("1回目のエラー", timestamp=TS1),
                    user_line("続きをお願い", timestamp=TS2),
                    api_error_line("2回目のエラー", timestamp=TS3),
                    user_line("また続きをお願い", timestamp=TS3),
                ],
                "",
            ),
            (
                "複数エラー・最後は停止",
                [
                    api_error_line("1回目のエラー", timestamp=TS1),
                    user_line("続きをお願い", timestamp=TS2),
                    api_error_line("2回目のエラー", timestamp=TS3),
                ],
                "server_error",
            ),
            (
                "errorフィールド欠落はunknown扱い",
                [
                    json.dumps(
                        {
                            "type": "assistant",
                            "isApiErrorMessage": True,
                            "message": {
                                "role": "assistant",
                                "stop_reason": "stop_sequence",
                                "content": [{"type": "text", "text": "何かのエラー"}],
                            },
                            "timestamp": TS1,
                        }
                    )
                ],
                "unknown",
            ),
            (
                "task-notificationでリセットしない（システム扱いuser行）",
                [
                    api_error_line("API Error: Connection closed mid-response.", timestamp=TS1),
                    task_notification_line("abc123", timestamp=TS2),
                ],
                "server_error",
            ),
            (
                "rate_limit種別も検知する",
                [
                    api_error_line(
                        "You've hit your session limit · resets 2:30pm (Asia/Tokyo)",
                        error="rate_limit",
                        timestamp=TS1,
                    )
                ],
                "rate_limit",
            ),
            (
                "invalid_request種別も検知する",
                [
                    api_error_line("Prompt is too long", error="invalid_request", timestamp=TS1)
                ],
                "invalid_request",
            ),
            (
                "サイドチェーン内のエラーも検知する（サブエージェント含む方針）",
                [
                    api_error_line(
                        "API Error: Connection closed mid-response.",
                        timestamp=TS1,
                        isSidechain=True,
                    )
                ],
                "server_error",
            ),
            (
                "isMeta内のエラーも検知する",
                [
                    api_error_line(
                        "API Error: Connection closed mid-response.", timestamp=TS1, isMeta=True
                    )
                ],
                "server_error",
            ),
        ]
        for desc, lines, expected in cases:
            with self.subTest(desc=desc):
                result = cta.analyze_lines(lines)
                self.assertEqual(result["last_turn_api_error"], expected)

    def test_pending_background_work_coexists_with_api_error(self):
        result = cta.analyze_lines(
            [
                launch_result_line("a0f4c886c975458d3", timestamp=TS1),
                api_error_line("API Error: Connection closed mid-response.", timestamp=TS2),
            ]
        )
        self.assertEqual(result["pending_background_work"], 1)
        self.assertEqual(result["last_turn_api_error"], "server_error")

    def test_error_text_extracted(self):
        text = "You've hit your session limit · resets 2:30pm (Asia/Tokyo)"
        result = cta.analyze_lines(
            [api_error_line(text, error="rate_limit", timestamp=TS1)]
        )
        self.assertEqual(result["last_turn_api_error_text"], text)

    def test_error_line_excluded_from_assistant_count(self):
        # APIエラー行は既存の会話行集計（assistant_count）に含めない。
        # エラー行自身がassistant_countを通過してしまうと、後続の会話行検出と
        # 同じ分岐でリセット判定が誤発火する（エラー行が自分自身をリセットする）ため、
        # エラー行はメッセージ集計そのものから除外する設計とする。
        result = cta.analyze_lines(
            [
                user_line("普通の依頼メッセージ", timestamp=TS1),
                assistant_line([{"type": "text", "text": "完了しました"}], timestamp=TS2),
                api_error_line("API Error: Connection closed mid-response.", timestamp=TS3),
            ]
        )
        self.assertEqual(result["assistant_count"], 1)
        self.assertEqual(result["user_count"], 1)
        self.assertEqual(result["last_turn_api_error"], "server_error")


class TestPendingBackgroundWork(unittest.TestCase):
    def test_cases(self):
        armed = {"delaySeconds": 1200, "prompt": "<<autonomous-loop-dynamic>>", "reason": "待機"}
        cases = [
            # (説明, 行リスト, 期待値)
            (
                "起動あり・全IDに通知あり",
                [
                    launch_result_line("a0f4c886c975458d3", timestamp=TS1),
                    task_notification_line("a0f4c886c975458d3", timestamp=TS2),
                ],
                0,
            ),
            (
                "起動あり・一部ID未通知",
                [
                    launch_result_line("a0f4c886c975458d3", "a7f5fbcb58a095e87", timestamp=TS1),
                    task_notification_line("a0f4c886c975458d3", timestamp=TS2),
                ],
                1,
            ),
            (
                "同一IDに重複通知・他に未通知なし（集合判定の境界）",
                [
                    launch_result_line("a0f4c886c975458d3", timestamp=TS1),
                    task_notification_line("a0f4c886c975458d3", timestamp=TS2),
                    task_notification_line("a0f4c886c975856d3", timestamp=TS3),
                    task_notification_line("a0f4c886c975458d3", timestamp=TS3),
                ],
                0,
            ),
            (
                "TaskStopで停止済みの起動IDは未完了扱いしない",
                [
                    launch_result_line("a0f4c886c975458d3", timestamp=TS1),
                    task_stop_line("a0f4c886c975458d3", timestamp=TS2),
                ],
                0,
            ),
            (
                "末尾ターンがScheduleWakeup武装で終了（発火予定が未来）",
                [
                    user_line("調査を続けて", timestamp=TS1),
                    schedule_wakeup_line(armed, timestamp=TS2),
                ],
                1,
            ),
            (
                "最後のScheduleWakeupがstop:true",
                [
                    schedule_wakeup_line(armed, timestamp=TS1),
                    schedule_wakeup_line({"stop": True}, timestamp=TS2),
                ],
                0,
            ),
            (
                "武装wakeupの発火予定を過ぎている（発火済み残骸で抑止しない境界）",
                [
                    schedule_wakeup_line({"delaySeconds": 60, "reason": "待機"}, timestamp=TS1),
                    user_line("その後の実ユーザー入力です", timestamp=TS3),
                ],
                0,
            ),
            (
                "async活動なしの通常セッション",
                [
                    user_line("普通の依頼メッセージ", timestamp=TS1),
                    assistant_line([{"type": "text", "text": "完了しました"}], timestamp=TS2),
                ],
                0,
            ),
            (
                "ターン途中着の通知はqueue-operationのみで記録される（userメッセージなし）",
                [
                    launch_result_line("aefc7d35e7d4178fb", timestamp=TS1),
                    json.dumps(
                        {
                            "type": "queue-operation",
                            "operation": "enqueue",
                            "timestamp": TS2,
                            "content": "<task-notification>\n"
                            "<task-id>aefc7d35e7d4178fb</task-id>\n</task-notification>",
                        }
                    ),
                ],
                0,
            ),
            (
                "ターン途中着の通知がattachment(queued_command)で記録される",
                [
                    launch_result_line("aefc7d35e7d4178fb", timestamp=TS1),
                    json.dumps(
                        {
                            "type": "attachment",
                            "isSidechain": False,
                            "attachment": {
                                "type": "queued_command",
                                "prompt": "<task-notification>\n"
                                "<task-id>aefc7d35e7d4178fb</task-id>\n</task-notification>",
                            },
                        }
                    ),
                ],
                0,
            ),
            (
                "未通知エージェントとstop済みwakeupの複合（エージェント側で1）",
                [
                    launch_result_line("a7f5fbcb58a095e87", timestamp=TS1),
                    schedule_wakeup_line({"stop": True}, timestamp=TS2),
                ],
                1,
            ),
        ]
        for desc, lines, expected in cases:
            with self.subTest(desc=desc):
                result = cta.analyze_lines(lines)
                self.assertEqual(result["pending_background_work"], expected)


class TestMain(unittest.TestCase):
    def test_wrong_argc_exits_1(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(cta.main(["prog"]), 1)
        self.assertIn("Usage:", stderr.getvalue())

    def test_missing_file_outputs_defaults(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(cta.main(["prog", "/nonexistent/path/to/transcript.jsonl"]), 0)
        output = stdout.getvalue()
        self.assertIn("LAST_USER_MESSAGE=''", output)
        self.assertIn("USER_MESSAGE_COUNT=0", output)
        self.assertIn("FIRST_TIMESTAMP=''", output)
        self.assertIn("SESSION_DURATION_FORMATTED=''", output)
        self.assertIn("COMPLETION_TIME_JST=''", output)
        self.assertIn("PENDING_BACKGROUND_WORK=0", output)
        self.assertIn("LAST_TURN_API_ERROR=''", output)
        self.assertIn("LAST_TURN_API_ERROR_TEXT=''", output)

    def test_output_roundtrips_through_bash_eval(self):
        message = "it's a \"quoted\"  message\nwith 'newline' and  spaces"
        expected = "it's a \"quoted\" message with 'newline' and spaces"
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
            f.write(user_line(message, timestamp=TS1) + "\n")
            path = f.name
        try:
            proc = subprocess.run(
                [
                    "bash",
                    "-c",
                    f'eval "$(python3 "$1" "$2")"; '
                    f'printf "%s\\n%s\\n%s\\n%s\\n" "${{LAST_USER_MESSAGE}}" '
                    f'"${{USER_MESSAGE_COUNT}}" "${{SESSION_DURATION_FORMATTED}}" '
                    f'"${{COMPLETION_TIME_JST}}"',
                    "bash",
                    str(ANALYZER),
                    path,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
        finally:
            Path(path).unlink()
        # 単一行transcriptのためfirst==last: duration=0s, TS1(12:00Z)+9h=21:00:00
        self.assertEqual(proc.stdout, f"{expected}\n1\n0s\n21:00:00\n")


if __name__ == "__main__":
    unittest.main()
