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
                    f'printf "%s\\n%s\\n" "${{LAST_USER_MESSAGE}}" "${{USER_MESSAGE_COUNT}}"',
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
        self.assertEqual(proc.stdout, f"{expected}\n1\n")


if __name__ == "__main__":
    unittest.main()
