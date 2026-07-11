"""shell/tmux/gemini_transcript_summary.jq の単体テスト。

旧実装（notification.sh内のインラインjq + bashヘルパー
format_session_duration / format_completion_time_jst の date 起動×4）との
パリティを固定する。時間計算はjq内の strptime/mktime/gmtime（UTCパース→UTC表示で
TZ相殺）へ移したため、bashヘルパーとの出力一致テストを含む。
"""
import json
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
QUERY = REPO_ROOT / "shell" / "tmux" / "gemini_transcript_summary.jq"

TS_START = "2026-07-11T12:00:00.000Z"
TS_END = "2026-07-11T12:02:30.000Z"


def run_query_raw(transcript_text):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        f.write(transcript_text)
        path = f.name
    try:
        return subprocess.run(
            ["jq", "-s", "-r", "-f", str(QUERY), path],
            capture_output=True,
            text=True,
        )
    finally:
        Path(path).unlink()


def run_query(transcript_text):
    """@sh 形式の1行出力を dict に展開する。"""
    proc = run_query_raw(transcript_text)
    if proc.returncode != 0:
        raise AssertionError(f"jq failed: {proc.stderr}")
    result = {}
    for token in shlex.split(proc.stdout):
        key, _, value = token.partition("=")
        result[key] = value
    return result


def single_object(messages, start=TS_START, end=TS_END):
    doc = {"messages": messages}
    if start is not None:
        doc["startTime"] = start
    if end is not None:
        doc["lastUpdated"] = end
    return json.dumps(doc, ensure_ascii=False)


@unittest.skipUnless(shutil.which("jq"), "jq required")
class TestUserMessageExtraction(unittest.TestCase):
    def test_single_object_form(self):
        cases = [
            # (説明, messages, 期待count, 期待last_msg)
            (
                "displayContent優先（content配列と両方あり）",
                [
                    {"type": "user", "content": "最初の依頼"},
                    {"type": "gemini", "content": "了解"},
                    {
                        "type": "user",
                        "content": [{"text": "内部表現"}],
                        "displayContent": [{"text": "表示用テキスト"}],
                    },
                ],
                2,
                "表示用テキスト",
            ),
            ("content文字列のみ", [{"type": "user", "content": "文字列の依頼"}], 1, "文字列の依頼"),
            (
                "content配列のみ（末尾要素のtext）",
                [{"type": "user", "content": [{"text": "前半"}, {"text": "配列の依頼"}]}],
                1,
                "配列の依頼",
            ),
            (
                "text無し末尾要素のcontent配列はuser扱いされない",
                [{"type": "user", "content": [{"toolCall": "x"}]}],
                0,
                "",
            ),
            ("userなし（geminiのみ）", [{"type": "gemini", "content": "応答"}], 0, ""),
            ("messages空", [], 0, ""),
        ]
        for desc, messages, expected_count, expected_last in cases:
            with self.subTest(desc=desc):
                result = run_query(single_object(messages))
                self.assertEqual(result["USER_COUNT"], str(expected_count))
                self.assertEqual(result["LAST_MSG"], expected_last)

    def test_passthrough_timestamps(self):
        result = run_query(single_object([{"type": "user", "content": "依頼"}]))
        self.assertEqual(result["START_TIME"], TS_START)
        self.assertEqual(result["END_TIME"], TS_END)


@unittest.skipUnless(shutil.which("jq"), "jq required")
class TestJsonlSetForm(unittest.TestCase):
    def test_end_time_resolution(self):
        user = {"type": "user", "content": "JSONL形式の依頼", "startTime": TS_START}
        set1 = {"$set": {"lastUpdated": "2026-07-11T12:01:00.000Z"}}
        set2 = {"$set": {"lastUpdated": TS_END}}
        first_with_end = {
            "type": "user",
            "content": "JSONL形式の依頼",
            "startTime": TS_START,
            "lastUpdated": "2026-07-11T12:09:00.000Z",
        }
        cases = [
            # (説明, レコード列, 期待END_TIME)
            ("最後の$set.lastUpdatedを採用", [user, set1, set2], TS_END),
            ("$setなしは先頭レコードのlastUpdated", [first_with_end], "2026-07-11T12:09:00.000Z"),
        ]
        for desc, records, expected_end in cases:
            with self.subTest(desc=desc):
                text = "\n".join(json.dumps(r, ensure_ascii=False) for r in records)
                result = run_query(text)
                self.assertEqual(result["END_TIME"], expected_end)
                self.assertEqual(result["USER_COUNT"], "1")
                self.assertEqual(result["LAST_MSG"], "JSONL形式の依頼")
                self.assertEqual(result["START_TIME"], TS_START)


@unittest.skipUnless(shutil.which("jq"), "jq required")
class TestTimeFields(unittest.TestCase):
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
                result = run_query(single_object([], start=base, end=last))
                self.assertEqual(result["SESSION_DURATION_FORMATTED"], expected)

    def test_completion_time_jst(self):
        cases = [
            # (説明, last, 期待completion)
            ("+9h変換と小数秒除去（日またぎ）", "2026-07-11T16:30:05.123Z", "01:30:05"),
            ("小数秒なし・末尾Zは無視（BSD dateパリティ）", "2026-07-11T00:01:00Z", "09:01:00"),
        ]
        for desc, last, expected in cases:
            with self.subTest(desc=desc):
                result = run_query(single_object([], end=last))
                self.assertEqual(result["COMPLETION_TIME_JST"], expected)

    def test_missing_or_invalid_timestamps(self):
        cases = [
            # (説明, start, end, 期待duration, 期待completion)
            ("両方欠落", None, None, "", ""),
            ("start欠落はdurationのみ空", None, TS_END, "", "21:02:30"),
            ("end欠落は両方空", TS_START, None, "", ""),
            ("start不正はdurationのみ空", "garbage", TS_END, "", "21:02:30"),
            ("end不正は両方空", TS_START, "garbage", "", ""),
        ]
        for desc, start, end, expected_duration, expected_completion in cases:
            with self.subTest(desc=desc):
                result = run_query(single_object([], start=start, end=end))
                self.assertEqual(result["SESSION_DURATION_FORMATTED"], expected_duration)
                self.assertEqual(result["COMPLETION_TIME_JST"], expected_completion)


@unittest.skipUnless(shutil.which("jq"), "jq required")
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
            ("first空文字", "", TS_END),
            ("first不正", "garbage", TS_END),
        ]
        for desc, first, last in cases:
            with self.subTest(desc=desc):
                result = run_query(single_object([], start=first, end=last))
                duration, completion = self._run_bash_helpers(first, last)
                self.assertEqual(result["SESSION_DURATION_FORMATTED"], duration)
                self.assertEqual(result["COMPLETION_TIME_JST"], completion)


@unittest.skipUnless(shutil.which("jq"), "jq required")
class TestQuotingAndDegradation(unittest.TestCase):
    def test_output_roundtrips_through_bash_eval(self):
        message = "it's a \"quoted\" message\nwith $VAR and `backticks`"
        transcript = single_object([{"type": "user", "content": message}])
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write(transcript)
            path = f.name
        try:
            proc = subprocess.run(
                [
                    "bash",
                    "-c",
                    'eval "$(jq -s -r -f "$1" "$2")"; '
                    'printf "%s\\n---\\n%s\\n%s\\n" '
                    '"${LAST_MSG}" "${USER_COUNT}" "${SESSION_DURATION_FORMATTED}"',
                    "bash",
                    str(QUERY),
                    path,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
        finally:
            Path(path).unlink()
        self.assertEqual(proc.stdout, f"{message}\n---\n1\n2m30s\n")

    def test_broken_json_fails_whole_query(self):
        # フック側は 2>/dev/null + 空eval で既定値へ劣化する前提（jq -s は全体失敗）
        proc = run_query_raw('{"messages": [broken')
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")

    def test_empty_file_yields_zero_values(self):
        result = run_query("")
        self.assertEqual(result["USER_COUNT"], "0")
        self.assertEqual(result["LAST_MSG"], "")
        self.assertEqual(result["SESSION_DURATION_FORMATTED"], "")
        self.assertEqual(result["COMPLETION_TIME_JST"], "")


if __name__ == "__main__":
    unittest.main()
