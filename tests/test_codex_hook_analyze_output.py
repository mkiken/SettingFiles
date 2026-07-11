"""ai/codex/hooks/codex_hook_common.py の shell-eval 出力契約の単体テスト。

analyze サブコマンドは shlex 引用済みの VAR=値 行を出力し、フックが
eval 1回で取り込む（tests/test_claude_transcript_analyze.py と同じ契約）。
context-usage サブコマンドの JSON 契約は不変であることも固定する。
"""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "ai" / "codex" / "hooks"))

import codex_hook_common as chc

MODULE = REPO_ROOT / "ai" / "codex" / "hooks" / "codex_hook_common.py"

TS1 = "2026-07-11T12:00:00.000Z"
TS2 = "2026-07-11T12:05:00.000Z"

EVAL_VAR_NAMES = [
    "IS_SUBAGENT_SESSION",
    "WAITING_FOR_USER_RESPONSE",
    "LAST_USER_MESSAGE",
    "LAST_ASSISTANT_MESSAGE",
    "USER_MESSAGE_COUNT",
    "ASSISTANT_MESSAGE_COUNT",
    "FIRST_TIMESTAMP",
    "LAST_TIMESTAMP",
    "SESSION_DURATION_FORMATTED",
    "COMPLETION_TIME_JST",
]


def analysis_dict(**overrides):
    base = {
        "is_subagent_session": False,
        "waiting_for_user_response": False,
        "last_user_message": "",
        "last_assistant_message": "",
        "user_message_count": 0,
        "assistant_message_count": 0,
        "first_timestamp": "",
        "last_timestamp": "",
    }
    base.update(overrides)
    return base


def eval_roundtrip(eval_lines, var_name):
    """出力をbashでevalし、指定変数の値をNUL区切りで正確に取り出す。"""
    proc = subprocess.run(
        ["bash", "-c", f'eval "$1"; printf "%s" "${{{var_name}}}"', "bash", eval_lines],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def response_item_line(role, text_type, text, timestamp):
    return json.dumps(
        {
            "timestamp": timestamp,
            "type": "response_item",
            "payload": {"type": "message", "role": role, "content": [{"type": text_type, "text": text}]},
        },
        ensure_ascii=False,
    )


def run_module(subcommand, stdin_text, codex_home):
    # CODEX_HOME を隔離しつつ、フック実行時と同じPython系列で走らせる
    return subprocess.run(
        [sys.executable, str(MODULE), subcommand],
        input=stdin_text,
        capture_output=True,
        text=True,
        env={**os.environ, "CODEX_HOME": codex_home},
    )


class TestFormatAnalysisForEval(unittest.TestCase):
    def test_bool_fields_lowercase_unquoted(self):
        cases = [
            # (説明, is_subagent, waiting)
            ("両方False", False, False),
            ("subagentのみTrue", True, False),
            ("waitingのみTrue", False, True),
            ("両方True", True, True),
        ]
        for desc, subagent, waiting in cases:
            with self.subTest(desc=desc):
                output = chc.format_analysis_for_eval(
                    analysis_dict(is_subagent_session=subagent, waiting_for_user_response=waiting)
                )
                self.assertIn(f"IS_SUBAGENT_SESSION={str(subagent).lower()}", output)
                self.assertIn(f"WAITING_FOR_USER_RESPONSE={str(waiting).lower()}", output)

    def test_message_quoting_roundtrips_through_bash_eval(self):
        cases = [
            # (説明, メッセージ)
            ("シングルクォート", "it's a test"),
            ("ダブルクォート", 'say "hello" now'),
            ("改行を含む", "line1\nline2"),
            ("連続スペース", "a  b   c"),
            ("日本語+記号混在", "実装して。'途中'の\"確認\"もお願い"),
        ]
        for desc, message in cases:
            with self.subTest(desc=desc):
                output = chc.format_analysis_for_eval(analysis_dict(last_user_message=message))
                self.assertEqual(eval_roundtrip(output, "LAST_USER_MESSAGE"), message)

    def test_injection_boundary_stays_literal(self):
        cases = [
            ("コマンド置換", "$(echo pwn)"),
            ("バッククォート", "`echo pwn`"),
            ("変数展開+セミコロン", "$HOME; rm -rf /"),
        ]
        for desc, message in cases:
            with self.subTest(desc=desc):
                output = chc.format_analysis_for_eval(analysis_dict(last_assistant_message=message))
                self.assertEqual(eval_roundtrip(output, "LAST_ASSISTANT_MESSAGE"), message)

    def test_empty_analysis_emits_exactly_default_lines(self):
        output = chc.format_analysis_for_eval(analysis_dict())
        lines = output.split("\n")
        self.assertEqual(len(lines), len(EVAL_VAR_NAMES))
        self.assertEqual([line.split("=", 1)[0] for line in lines], EVAL_VAR_NAMES)
        self.assertIn("LAST_USER_MESSAGE=''", output)
        self.assertIn("USER_MESSAGE_COUNT=0", output)
        self.assertIn("FIRST_TIMESTAMP=''", output)

    def test_count_and_timestamp_boundaries(self):
        cases = [
            # (説明, count, timestamp, 期待count行, 期待TS値)
            ("count 0 / TS空", 0, "", "USER_MESSAGE_COUNT=0", ""),
            ("count 1 / ISO値", 1, TS1, "USER_MESSAGE_COUNT=1", TS1),
        ]
        for desc, count, ts, expected_count_line, expected_ts in cases:
            with self.subTest(desc=desc):
                output = chc.format_analysis_for_eval(
                    analysis_dict(user_message_count=count, first_timestamp=ts)
                )
                self.assertIn(expected_count_line, output)
                self.assertEqual(eval_roundtrip(output, "FIRST_TIMESTAMP"), expected_ts)


class TestMainSubprocess(unittest.TestCase):
    def setUp(self):
        # 実環境の ~/.codex（history.jsonl 等）へのフォールバックを遮断する
        self._codex_home = tempfile.TemporaryDirectory()
        self.codex_home = self._codex_home.name
        self.addCleanup(self._codex_home.cleanup)

    def test_analyze_empty_input_outputs_defaults(self):
        proc = run_module("analyze", "{}", self.codex_home)
        self.assertEqual(proc.returncode, 0)
        lines = proc.stdout.strip().split("\n")
        self.assertEqual([line.split("=", 1)[0] for line in lines], EVAL_VAR_NAMES)
        self.assertIn("USER_MESSAGE_COUNT=0", proc.stdout)
        self.assertIn("IS_SUBAGENT_SESSION=false", proc.stdout)

    def test_analyze_invalid_json_exits_1_with_empty_stdout(self):
        proc = run_module("analyze", "{broken", self.codex_home)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(proc.stdout, "")
        self.assertIn("invalid hook input JSON", proc.stderr)

    def test_analyze_transcript_fixture_roundtrips_through_bash_eval(self):
        user_message = "通知フックの'性能'を\"改善\"して"
        assistant_message = "この方針で進めてよいですか？"
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
            f.write(response_item_line("user", "input_text", user_message, TS1) + "\n")
            f.write(response_item_line("assistant", "output_text", assistant_message, TS2) + "\n")
            path = f.name
        self.addCleanup(Path(path).unlink)

        proc = run_module("analyze", json.dumps({"transcript_path": path}), self.codex_home)
        self.assertEqual(proc.returncode, 0)
        evaluated = {name: eval_roundtrip(proc.stdout, name) for name in EVAL_VAR_NAMES}
        self.assertEqual(evaluated["LAST_USER_MESSAGE"], user_message)
        self.assertEqual(evaluated["LAST_ASSISTANT_MESSAGE"], assistant_message)
        self.assertEqual(evaluated["USER_MESSAGE_COUNT"], "1")
        self.assertEqual(evaluated["ASSISTANT_MESSAGE_COUNT"], "1")
        self.assertEqual(evaluated["WAITING_FOR_USER_RESPONSE"], "true")
        self.assertEqual(evaluated["FIRST_TIMESTAMP"], TS1)
        self.assertEqual(evaluated["LAST_TIMESTAMP"], TS2)

    def test_context_usage_json_contract_unchanged(self):
        token_count_line = json.dumps(
            {
                "type": "event_msg",
                "payload": {
                    "type": "token_count",
                    "info": {
                        "total_token_usage": {"total_tokens": 50000},
                        "last_token_usage": {"total_tokens": 50000},
                        "model_context_window": 200000,
                    },
                },
            }
        )
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
            f.write(token_count_line + "\n")
            path = f.name
        self.addCleanup(Path(path).unlink)

        proc = run_module("context-usage", json.dumps({"transcript_path": path}), self.codex_home)
        self.assertEqual(proc.returncode, 0)
        result = json.loads(proc.stdout)
        self.assertEqual(result["context_window_tokens"], 50000)
        self.assertEqual(result["model_context_window"], 200000)


if __name__ == "__main__":
    unittest.main()
