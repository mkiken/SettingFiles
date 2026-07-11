import os
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
    ]

    def test_keyword_classification(self):
        for message, expected in self.CASES:
            with self.subTest(message=message):
                result = run_fn(f'guess_task_type_emoji "{message}"')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), expected)


if __name__ == "__main__":
    unittest.main()
