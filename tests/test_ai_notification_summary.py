import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_fn(fn_and_args: str, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    script = (
        f'source "{REPO_ROOT}/shell/tmux/tmux_notification_title.sh"; '
        f'source "{REPO_ROOT}/shell/tmux/ai_notification_summary.sh"; '
        + fn_and_args
    )
    env = {**os.environ, "TZ": "UTC", **(env_extra or {})}
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env)


@unittest.skipUnless(sys.platform == "darwin", "BSD date (-j -f / -r) required")
class Iso8601ToEpochTest(unittest.TestCase):
    def test_strips_milliseconds_and_returns_epoch(self):
        result = run_fn('iso8601_to_epoch "2026-06-27T00:01:00.000Z"')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.strip().isdigit())

    def test_unparsable_input_outputs_nothing(self):
        result = run_fn('iso8601_to_epoch "garbage"')
        self.assertEqual(result.stdout.strip(), "")


@unittest.skipUnless(sys.platform == "darwin", "BSD date (-j -f / -r) required")
class FormatSessionDurationTest(unittest.TestCase):
    def test_hour_scale_duration(self):
        result = run_fn(
            'format_session_duration "2026-06-27T00:00:00.000Z" "2026-06-27T01:01:01.000Z"'
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "1h1m")

    def test_seconds_scale_duration(self):
        result = run_fn(
            'format_session_duration "2026-06-27T00:00:00.000Z" "2026-06-27T00:00:30.000Z"'
        )
        self.assertEqual(result.stdout.strip(), "30s")

    def test_null_first_timestamp_outputs_nothing(self):
        result = run_fn('format_session_duration "null" "2026-06-27T00:00:30.000Z"')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def test_unparsable_timestamp_outputs_nothing(self):
        result = run_fn('format_session_duration "garbage" "2026-06-27T00:00:30.000Z"')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")


@unittest.skipUnless(sys.platform == "darwin", "BSD date (-j -f / -r) required")
class FormatCompletionTimeJstTest(unittest.TestCase):
    def test_converts_utc_to_jst(self):
        result = run_fn('format_completion_time_jst "2026-06-27T00:01:00.000Z"')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "09:01:00")

    def test_null_timestamp_outputs_nothing(self):
        result = run_fn('format_completion_time_jst "null"')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")


class GuessTaskTypeEmojiTest(unittest.TestCase):
    CASES = [
        ("バグを修正して", "💻"),
        ("原因を調べて", "🔍"),
        ("なぜ動くのか", "📚"),
        ("testを実行", "🧪"),
        ("こんにちは", "💬"),
        # 「テスト」より先に「追加」（コーディング分岐）がマッチする既存優先順位を固定
        ("テストを追加", "💻"),
        # スラッシュコマンドは内容キーワードより優先して⚡（先頭空白も許容）
        ("/pr-review 123", "⚡"),
        ("  /修正コマンド", "⚡"),
    ]

    def test_keyword_classification(self):
        for message, expected in self.CASES:
            with self.subTest(message=message):
                result = run_fn(f'guess_task_type_emoji "{message}"')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), expected)


class BuildStatsLineTest(unittest.TestCase):
    def test_with_duration(self):
        result = run_fn('build_stats_line 3 "5m2s"')
        self.assertEqual(result.stdout.strip(), "🔄3 ⏳5m2s")

    def test_without_duration(self):
        result = run_fn('build_stats_line 3 ""')
        self.assertEqual(result.stdout.strip(), "🔄3")


class BuildSummaryMsgLineTest(unittest.TestCase):
    def test_short_message_unchanged(self):
        result = run_fn('build_summary_msg_line "💻" "short message"')
        self.assertEqual(result.stdout.strip(), "💻 short message")

    def test_long_message_truncated_with_ellipsis(self):
        long_message = "a" * 100
        result = run_fn(f'build_summary_msg_line "💻" "{long_message}"')
        line = result.stdout.strip()
        self.assertLessEqual(len(line), 80)
        self.assertTrue(line.endswith("..."))

    def test_boundary_exactly_80_chars_unchanged(self):
        # 絵文字1文字 + 空白 + 78文字 = ちょうど80文字（bashの${#}基準）は短縮しない
        message = "b" * 78
        result = run_fn(f'build_summary_msg_line "💻" "{message}"')
        self.assertEqual(result.stdout.strip(), f"💻 {message}")

    def test_newlines_collapsed_to_single_line(self):
        result = run_fn("build_summary_msg_line '💬' 'line1\nline2   line3'")
        self.assertEqual(result.stdout.strip(), "💬 line1 line2 line3")


@unittest.skipUnless(shutil.which("jq"), "jq required")
class DeriveSessionIdTest(unittest.TestCase):
    def test_prefers_session_id_from_hook_input(self):
        result = run_fn(
            "derive_session_id '{\"session_id\": \"abc-123\"}' '/tmp/whatever.jsonl'"
        )
        self.assertEqual(result.stdout.strip(), "abc-123")

    def test_falls_back_to_transcript_basename(self):
        result = run_fn("derive_session_id '{}' '/tmp/session-xyz.jsonl'")
        self.assertEqual(result.stdout.strip(), "session-xyz")

    def test_parent_dir_style_uses_directory_name(self):
        result = run_fn(
            "derive_session_id '{}' '/tmp/chats/uuid-777/transcript.json' parent-dir"
        )
        self.assertEqual(result.stdout.strip(), "uuid-777")

    def test_session_id_from_hook_input_ignores_style(self):
        result = run_fn(
            "derive_session_id '{\"session_id\": \"abc-123\"}' "
            "'/tmp/uuid-777/transcript.json' parent-dir"
        )
        self.assertEqual(result.stdout.strip(), "abc-123")

    def test_empty_inputs_fall_back_to_default(self):
        result = run_fn("derive_session_id '{}' ''")
        self.assertEqual(result.stdout.strip(), "default")

    def test_null_transcript_path_falls_back_to_default(self):
        result = run_fn("derive_session_id '{}' 'null'")
        self.assertEqual(result.stdout.strip(), "default")


class NormalizeOnelineTest(unittest.TestCase):
    CASES = [
        ("line1\\nline2   line3", "line1 line2 line3"),
        ("  padded  ", "padded"),
        ("", ""),
        ("single", "single"),
        # 連続改行はスペース化後に1個へ圧縮される
        ("a\\n\\nb", "a b"),
        # スペースのみは空になる
        ("   ", ""),
    ]

    def test_normalization(self):
        for raw, expected in self.CASES:
            with self.subTest(raw=raw):
                result = run_fn(f"normalize_oneline $'{raw}'")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), expected)

    def test_tabs_preserved_and_only_spaces_trimmed(self):
        # 旧 tr|sed 実装とのパリティ: 圧縮・前後トリムはスペースのみでタブは温存する。
        # .strip()はタブも落とすため、stdoutを生のまま比較する
        cases = [
            ("タブ周りのスペースのみ圧縮", "a  \\t  b", "a \t b\n"),
            ("前後トリムはタブに触れない", " \\tx\\t ", "\tx\t\n"),
        ]
        for desc, raw, expected in cases:
            with self.subTest(desc=desc):
                result = run_fn(f"normalize_oneline $'{raw}'")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, expected)


class TruncateLineTest(unittest.TestCase):
    def test_under_max_unchanged(self):
        result = run_fn('truncate_line "abc" 5')
        self.assertEqual(result.stdout.strip(), "abc")

    def test_boundary_exactly_max_unchanged(self):
        result = run_fn(f'truncate_line "{"a" * 5}" 5')
        self.assertEqual(result.stdout.strip(), "a" * 5)

    def test_over_max_truncated_with_ellipsis(self):
        result = run_fn(f'truncate_line "{"a" * 10}" 5')
        self.assertEqual(result.stdout.strip(), "a" * 5 + "...")


class BuildSessionSummaryTest(unittest.TestCase):
    def test_with_duration(self):
        result = run_fn('build_session_summary "💻" "fix the bug" 3 "5m2s"')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "💻 fix the bug\n🔄3 ⏳5m2s\n")

    def test_without_duration(self):
        result = run_fn('build_session_summary "💬" "hello" 1 ""')
        self.assertEqual(result.stdout, "💬 hello\n🔄1\n")

    def test_zero_user_count_outputs_nothing(self):
        result = run_fn('build_session_summary "💬" "" 0 ""')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_non_numeric_user_count_outputs_nothing(self):
        result = run_fn('build_session_summary "💬" "msg" "" ""')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
