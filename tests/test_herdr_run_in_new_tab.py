import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AI_ALIASES = REPO_ROOT / "shell/zsh/alias/ai/ai.zsh"

# _herdr_wait_shell_ready の1attemptあたりのwaitタイムアウト（ai.zshのattempt_timeout_msと一致させる）
ATTEMPT_TIMEOUT_MS = 800
# デフォルト総予算24000msでの最大attempt数
DEFAULT_MAX_ATTEMPTS = 30


def run_herdr_run_in_new_tab(
    args: str,
    *,
    tab_create_exit: int = 0,
    tab_create_json: str = '{"result":{"tab":{"tab_id":"w1:t3"},"root_pane":{"pane_id":"w1:p2"}}}',
    wait_output_exit: int = 0,
    wait_output_failures: int = 0,
    wait_output_stderr: str = "",
) -> tuple[subprocess.CompletedProcess, list[str]]:
    """stub herdr/jq 付きでai.zshの関数を実行し、(結果, herdr呼び出しログ) を返す。

    pane wait-output stubは最初の wait_output_failures 回は exit 1（タイムアウト）を返し、
    それ以降は wait_output_exit を返す（リトライループの検証用）。
    wait_output_stderr を指定すると失敗時にstderrへ出力する（エラー表面化の検証用）。
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        log_path = Path(temp_dir) / "herdr_calls.log"
        wait_count_path = Path(temp_dir) / "wait_count"
        script = f'''
LOG="{log_path}"
WAIT_COUNT_FILE="{wait_count_path}"
herdr() {{
    printf '%s\\n' "$*" >> "$LOG"
    case "$1" in
        tab)
            if [[ "$2" == "create" ]]; then
                if [[ {tab_create_exit} -eq 0 ]]; then
                    printf '%s' '{tab_create_json}'
                fi
                return {tab_create_exit}
            fi
            ;;
        pane)
            [[ "$2" == "run" ]] && return 0
            if [[ "$2" == "wait-output" ]]; then
                local wait_count=$(( $(cat "$WAIT_COUNT_FILE" 2>/dev/null || echo 0) + 1 ))
                printf '%s' "$wait_count" > "$WAIT_COUNT_FILE"
                if (( wait_count <= {wait_output_failures} )); then
                    [[ -n "{wait_output_stderr}" ]] && printf '%s\\n' "{wait_output_stderr}" >&2
                    return 1
                fi
                if [[ {wait_output_exit} -ne 0 ]]; then
                    [[ -n "{wait_output_stderr}" ]] && printf '%s\\n' "{wait_output_stderr}" >&2
                fi
                return {wait_output_exit}
            fi
            ;;
    esac
}}
jq() {{
    # ai.zshが使う2種類のフィルタを引数でディスパッチする（$2がフィルタ文字列）
    if [[ "$2" == *tab.tab_id* ]]; then
        python3 -c 'import json,sys; d=json.load(sys.stdin); v=d.get("result",{{}}).get("tab",{{}}).get("tab_id"); print(v if v is not None else "")'
    else
        python3 -c 'import json,sys; d=json.load(sys.stdin); v=d.get("result",{{}}).get("root_pane",{{}}).get("pane_id"); print(v if v is not None else "null")'
    fi
}}
source "{AI_ALIASES}"
{args}
'''
        result = subprocess.run(
            ["zsh", "-fc", script],
            cwd=REPO_ROOT,
            env={"PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"},
            text=True,
            capture_output=True,
            check=False,
        )
        calls = log_path.read_text().splitlines() if log_path.exists() else []
        return result, calls


def marker_from_run_call(call: str) -> str:
    """pane run呼び出しログから送信マーカー（分割形、`""`入り）を取り出す。"""
    return call.split("print -r -- ", 1)[1]


class HerdrRunInNewTabTest(unittest.TestCase):
    def test_calls_happen_in_order_tab_create_marker_wait_then_command(self):
        result, calls = run_herdr_run_in_new_tab(
            '_herdr_run_in_new_tab "" "/tmp/work" "label" "gm-pr-review 123"'
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(calls), 4, calls)

        self.assertTrue(calls[0].startswith("tab create"))
        self.assertIn("--no-focus", calls[0])
        self.assertTrue(calls[1].startswith("pane run w1:p2 print -r -- __herdr_ready_"))
        self.assertTrue(calls[2].startswith("pane wait-output w1:p2 --match __herdr_ready_"))
        self.assertEqual(calls[3], "pane run w1:p2 gm-pr-review 123")

    def test_focus_on_create_uses_focus_instead_of_no_focus(self):
        result, calls = run_herdr_run_in_new_tab(
            '_herdr_run_in_new_tab "" "/tmp/work" "label" ":" "" 1'
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--focus", calls[0])
        self.assertNotIn("--no-focus", calls[0])
        self.assertTrue(calls[1].startswith("pane run w1:p2 print -r -- __herdr_ready_"))
        self.assertTrue(calls[2].startswith("pane wait-output w1:p2"))
        self.assertEqual(calls[3], "pane run w1:p2 :")

    def test_marker_sent_split_but_waited_concatenated(self):
        # 入力エコーには分割形しか現れないよう、送信は `head""tail`、
        # wait --match は実行出力にしか現れない連結形でなければならない
        _, calls = run_herdr_run_in_new_tab(
            '_herdr_run_in_new_tab "" "/tmp/work" "label" "gm-pr-review 123"'
        )
        marker_in_run = marker_from_run_call(calls[1])
        marker_in_wait = calls[2].split("--match ", 1)[1].split(" --source", 1)[0]

        self.assertIn('""', marker_in_run)
        self.assertNotIn('""', marker_in_wait)
        self.assertEqual(marker_in_run.replace('""', ""), marker_in_wait)

    def test_retry_resends_marker_until_wait_succeeds(self):
        # 1回目のwaitがタイムアウト→マーカー再送→2回目で成功。本命コマンドは成功後に1回だけ。
        result, calls = run_herdr_run_in_new_tab(
            '_herdr_run_in_new_tab "" "/tmp/work" "label" "gm-pr-review 123"',
            wait_output_failures=1,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(calls), 6, calls)

        marker_runs = [c for c in calls if c.startswith("pane run w1:p2 print -r -- __herdr_ready_")]
        wait_calls = [c for c in calls if c.startswith("pane wait-output ")]
        real_runs = [c for c in calls if c == "pane run w1:p2 gm-pr-review 123"]
        self.assertEqual(len(marker_runs), 2)
        self.assertEqual(len(wait_calls), 2)
        self.assertEqual(len(real_runs), 1)
        self.assertEqual(calls[-1], "pane run w1:p2 gm-pr-review 123")
        # 同一呼び出し内のリトライは同じマーカーを再送する
        self.assertEqual(marker_from_run_call(marker_runs[0]), marker_from_run_call(marker_runs[1]))

    def test_wait_output_timeout_prevents_final_command(self):
        result, calls = run_herdr_run_in_new_tab(
            '_herdr_run_in_new_tab "" "/tmp/work" "label" "gm-pr-review 123"',
            wait_output_exit=1,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("タイムアウトしました", result.stderr)

        marker_runs = [c for c in calls if c.startswith("pane run w1:p2 print -r -- __herdr_ready_")]
        wait_calls = [c for c in calls if c.startswith("pane wait-output ")]
        self.assertEqual(len(marker_runs), DEFAULT_MAX_ATTEMPTS)
        self.assertEqual(len(wait_calls), DEFAULT_MAX_ATTEMPTS)
        self.assertTrue(
            wait_calls[0].endswith(f"--source recent --timeout {ATTEMPT_TIMEOUT_MS}"),
            wait_calls[0],
        )
        self.assertFalse(any(c == "pane run w1:p2 gm-pr-review 123" for c in calls))

    def test_wait_output_stderr_is_surfaced_on_timeout(self):
        # herdr CLIのエラー（例: 0.7.5でのサブコマンド改名による unknown command）が
        # 全attempt破棄されて「タイムアウト」だけが報告される再発を防ぐ
        result, _ = run_herdr_run_in_new_tab(
            '_herdr_run_in_new_tab "" "/tmp/work" "label" "gm-pr-review 123"',
            wait_output_exit=1,
            wait_output_stderr="unknown command: wait",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("タイムアウトしました", result.stderr)
        self.assertIn("unknown command: wait", result.stderr)

    def test_timeout_budget_bounds_attempts(self):
        # attempt数 = ceil(timeout_ms / 800) の境界値検証
        cases = [
            (800, 1),
            (801, 2),
            (1600, 2),
            (1601, 3),
        ]
        for timeout_ms, expected_attempts in cases:
            with self.subTest(timeout_ms=timeout_ms):
                result, calls = run_herdr_run_in_new_tab(
                    f'_herdr_wait_shell_ready w1:p2 {timeout_ms}',
                    wait_output_exit=1,
                )
                self.assertEqual(result.returncode, 1)
                marker_runs = [c for c in calls if c.startswith("pane run w1:p2 print -r -- __herdr_ready_")]
                self.assertEqual(len(marker_runs), expected_attempts, calls)

    def test_tab_create_failure_skips_pane_run(self):
        result, calls = run_herdr_run_in_new_tab(
            '_herdr_run_in_new_tab "" "/tmp/work" "label" "gm-pr-review 123"',
            tab_create_exit=1,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("herdr tab createに失敗しました", result.stderr)
        self.assertEqual(len(calls), 1, calls)
        self.assertTrue(calls[0].startswith("tab create"))

    def test_null_pane_id_skips_wait_and_final_command(self):
        result, calls = run_herdr_run_in_new_tab(
            '_herdr_run_in_new_tab "" "/tmp/work" "label" "gm-pr-review 123"',
            tab_create_json='{"result":{"root_pane":{"pane_id":null}}}',
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("pane_idを取得できませんでした", result.stderr)
        self.assertEqual(len(calls), 1, calls)

    def test_marker_is_unique_across_calls(self):
        _, calls = run_herdr_run_in_new_tab(
            '_herdr_run_in_new_tab "" "/tmp/work" "label" "gm-pr-review 1"; '
            '_herdr_run_in_new_tab "" "/tmp/work" "label" "gm-pr-review 2"'
        )
        markers = [marker_from_run_call(c) for c in calls if "print -r --" in c]
        self.assertEqual(len(markers), 2)
        self.assertNotEqual(markers[0], markers[1])

    def test_tab_id_out_var_receives_created_tab_id(self):
        result, calls = run_herdr_run_in_new_tab(
            'local out=""; '
            '_herdr_run_in_new_tab "" "/tmp/work" "label" "gm-pr-review 123" out '
            '&& print -r -- "got:${out}"'
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "got:w1:t3")
        # 出力変数の追加で呼び出し列(tab create→marker→wait→本命)が変わらないこと
        self.assertEqual(len(calls), 4, calls)

    def test_missing_tab_id_warns_and_continues_with_empty_var(self):
        result, calls = run_herdr_run_in_new_tab(
            'local out="stale"; '
            '_herdr_run_in_new_tab "" "/tmp/work" "label" "gm-pr-review 123" out '
            '&& print -r -- "got:${out}"',
            tab_create_json='{"result":{"root_pane":{"pane_id":"w1:p2"}}}',
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "got:")
        self.assertIn("tab_idを取得できませんでした", result.stderr)
        self.assertEqual(len(calls), 4, calls)

    def test_invalid_out_var_name_fails_before_pane_run(self):
        result, calls = run_herdr_run_in_new_tab(
            '_herdr_run_in_new_tab "" "/tmp/work" "label" "gm-pr-review 123" bad-name'
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(calls), 1, calls)
        self.assertTrue(calls[0].startswith("tab create"))

    def test_noop_command_from_fgwtc_is_still_sent_after_ready(self):
        # fgwtc(git.zsh) は command に no-op ':' を渡す。ready待ち後もスキップされず投入されること。
        result, calls = run_herdr_run_in_new_tab(
            '_herdr_run_in_new_tab "" "/tmp/work" "label" ":"'
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls[-1], "pane run w1:p2 :")


if __name__ == "__main__":
    unittest.main()
