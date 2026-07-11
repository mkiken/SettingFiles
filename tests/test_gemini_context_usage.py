"""shell/tmux/gemini_context_usage.py の単体テスト。

bash旧実装（notification.sh の find|stat|sort|head|cut 連鎖 + インラインpython +
jq3回 + bc）とのパリティを固定する。特に `find -path "*/chats/*<prefix>*.jsonl"` が
ディレクトリ名にもマッチする点と、`bc "scale=1"` の切り捨て（四捨五入しない）を含む。
"""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "shell" / "tmux"))

import gemini_context_usage as gcu

MODULE = REPO_ROOT / "shell" / "tmux" / "gemini_context_usage.py"

PREFIX = "abcdef12"


def write_jsonl_lines(path: Path, lines: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def gemini_line(tokens, model="gemini-3.5-flash", **extra):
    return json.dumps({"type": "gemini", "tokens": tokens, "model": model, **extra})


class TestFindLatestChatJsonl(unittest.TestCase):
    def test_missing_and_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            missing = Path(tmpdir) / "nonexistent"
            self.assertIsNone(gcu.find_latest_chat_jsonl(missing, PREFIX))
            self.assertIsNone(gcu.find_latest_chat_jsonl(tmpdir, PREFIX))

    def test_path_matching(self):
        cases = [
            # (説明, chats以下の相対パス, 期待: マッチするか)
            ("prefixがファイル名に含まれる", f"project/chats/session-{PREFIX}.jsonl", True),
            ("prefixがディレクトリ名のみ（find -pathパリティ）", f"project/chats/{PREFIX}-3456/latest.jsonl", True),
            ("prefixがどこにも無い", "project/chats/other-session.jsonl", False),
            ("chatsディレクトリ外はprefix一致でも非マッチ", f"project/logs/{PREFIX}.jsonl", False),
        ]
        for desc, rel_path, expected in cases:
            with self.subTest(desc=desc):
                with tempfile.TemporaryDirectory() as tmpdir:
                    write_jsonl_lines(Path(tmpdir) / rel_path, [gemini_line({"input": 1})])
                    found = gcu.find_latest_chat_jsonl(tmpdir, PREFIX)
                    if expected:
                        self.assertIsNotNone(found)
                        self.assertEqual(found, Path(tmpdir) / rel_path)
                    else:
                        self.assertIsNone(found)

    def test_prefix_before_chats_component_does_not_match(self):
        # 旧find実装のパターンは "*/chats/*<prefix>*.jsonl" — prefixは /chats/ より後ろ限定
        with tempfile.TemporaryDirectory() as tmpdir:
            write_jsonl_lines(
                Path(tmpdir) / f"{PREFIX}-project" / "chats" / "session.jsonl",
                [gemini_line({"input": 1})],
            )
            self.assertIsNone(gcu.find_latest_chat_jsonl(tmpdir, PREFIX))

    def test_newest_mtime_wins(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            older = Path(tmpdir) / "project" / "chats" / f"session-{PREFIX}.jsonl"
            newer = Path(tmpdir) / "project" / "chats" / PREFIX / "latest.jsonl"
            write_jsonl_lines(older, [gemini_line({"input": 1})])
            write_jsonl_lines(newer, [gemini_line({"input": 2})])
            os.utime(older, (1000, 1000))
            os.utime(newer, (2000, 2000))
            self.assertEqual(gcu.find_latest_chat_jsonl(tmpdir, PREFIX), newer)
            # mtimeを逆転させると選択も逆転する（ファイル名順ではないことの確認）
            os.utime(older, (3000, 3000))
            self.assertEqual(gcu.find_latest_chat_jsonl(tmpdir, PREFIX), older)


class TestExtractLastGeminiRecord(unittest.TestCase):
    def test_extraction(self):
        cases = [
            # (説明, JSONL行リスト, 期待: 抽出レコードのtokens or None)
            ("gemini行なし", [json.dumps({"type": "user", "content": "hi"})], None),
            ("tokensキーの無いgemini行はスキップ", [json.dumps({"type": "gemini", "model": "m"})], None),
            (
                "不正JSON・空行混在でも最後の有効gemini行",
                ["{broken", "", gemini_line({"input": 10}), "not json", gemini_line({"input": 20})],
                {"input": 20},
            ),
            (
                "gemini行が複数なら最後の1件",
                [gemini_line({"input": 100}), gemini_line({"input": 200})],
                {"input": 200},
            ),
        ]
        for desc, lines, expected_tokens in cases:
            with self.subTest(desc=desc):
                with tempfile.TemporaryDirectory() as tmpdir:
                    path = Path(tmpdir) / "chat.jsonl"
                    write_jsonl_lines(path, lines)
                    record = gcu.extract_last_gemini_record(path)
                    if expected_tokens is None:
                        self.assertIsNone(record)
                    else:
                        self.assertEqual(record["tokens"], expected_tokens)

    def test_unreadable_file_returns_none(self):
        self.assertIsNone(gcu.extract_last_gemini_record("/nonexistent/chat.jsonl"))


class TestComputeUsage(unittest.TestCase):
    def test_token_fallback(self):
        cases = [
            # (説明, tokens, 期待(context, total))
            ("inputが正の数値ならそのまま", {"input": 100000, "total": 900000}, (100000, 900000)),
            ("input欠落はtotalへフォールバック", {"total": 5000}, (5000, 5000)),
            ("input=0はtotalへフォールバック（境界）", {"input": 0, "total": 5000}, (5000, 5000)),
            ("input負数はtotalへフォールバック", {"input": -5, "total": 5000}, (5000, 5000)),
            ("input非数値はtotalへフォールバック", {"input": "abc", "total": 5000}, (5000, 5000)),
            ("input・total両方欠落は0", {}, (0, 0)),
            ("total非数値は0に丸める", {"input": 0, "total": "abc"}, (0, 0)),
            ("float入力はint切り捨て", {"input": 99.9, "total": 100.9}, (99, 100)),
        ]
        for desc, tokens, expected in cases:
            with self.subTest(desc=desc):
                context, total, _ = gcu.compute_usage({"type": "gemini", "tokens": tokens, "model": "m"})
                self.assertEqual((context, total), expected)

    def test_model_extraction(self):
        cases = [
            ("model文字列はそのまま", {"model": "gemini-3.5-pro"}, "gemini-3.5-pro"),
            ("model欠落は空文字列", {}, ""),
            ("model非文字列は空文字列", {"model": {"name": "x"}}, ""),
        ]
        for desc, extra, expected in cases:
            with self.subTest(desc=desc):
                _, _, model = gcu.compute_usage({"type": "gemini", "tokens": {"input": 1}, **extra})
                self.assertEqual(model, expected)


class TestFormatUsedPct(unittest.TestCase):
    def test_bc_truncation_parity(self):
        window = gcu.GEMINI_CONTEXT_WINDOW
        cases = [
            # (説明, tokens, 期待文字列)
            ("e2eパリティ: 9.536...は9.5", 100000, "9.5"),
            ("85.83...は85.8", 900000, "85.8"),
            ("切り捨て≠四捨五入の境界: 9.989...は9.9（roundなら10.0）", 104752, "9.9"),
            ("WARN閾値ちょうど70.0", 734004, "70.0"),
            ("CRIT閾値ちょうど85.0", 891290, "85.0"),
            ("tokens=0は0.0", 0, "0.0"),
            ("負数は0.0", -100, "0.0"),
            ("window全量は100.0", window, "100.0"),
        ]
        for desc, tokens, expected in cases:
            with self.subTest(desc=desc):
                self.assertEqual(gcu.format_used_pct(tokens, window), expected)

    def test_zero_window_returns_zero(self):
        self.assertEqual(gcu.format_used_pct(100, 0), "0.0")


class TestMain(unittest.TestCase):
    def run_main(self, argv):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = gcu.main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def parse_vars(self, output):
        return dict(line.split("=", 1) for line in output.strip().splitlines())

    def test_wrong_argc_exits_1_with_usage(self):
        code, _, stderr = self.run_main(["gemini_context_usage.py"])
        self.assertEqual(code, 1)
        self.assertIn("Usage:", stderr)

    def test_no_match_prints_defaults_and_exits_0(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            code, stdout, _ = self.run_main(["prog", tmpdir, PREFIX])
        self.assertEqual(code, 0)
        variables = self.parse_vars(stdout)
        self.assertEqual(variables["GEMINI_CONTEXT_TOKENS"], "0")
        self.assertEqual(variables["GEMINI_TOTAL_TOKENS"], "0")
        # shlex.quoteは安全な文字列に引用符を付けないためそのまま
        self.assertEqual(variables["GEMINI_USED_PCT"], "0.0")
        self.assertEqual(variables["GEMINI_WINDOW"], "1048576")

    def test_output_roundtrips_through_bash_eval(self):
        # 引用符・空白入りmodelがevalを壊さないこと（shlex.quoteの検証）
        with tempfile.TemporaryDirectory() as tmpdir:
            chat = Path(tmpdir) / "project" / "chats" / f"session-{PREFIX}.jsonl"
            write_jsonl_lines(
                chat,
                [gemini_line({"input": 100000, "total": 900000}, model='it\'s "flash" v2')],
            )
            script = (
                'eval "$(python3 "$1" "$2" "$3")" || exit 1\n'
                'printf "%s\\n" "${GEMINI_CONTEXT_TOKENS}" "${GEMINI_USED_PCT}" '
                '"${GEMINI_MODEL}" "${GEMINI_WINDOW}"\n'
            )
            result = subprocess.run(
                ["bash", "-c", script, "bash", str(MODULE), tmpdir, PREFIX],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            ["100000", "9.5", 'it\'s "flash" v2', "1048576"],
        )


if __name__ == "__main__":
    unittest.main()
