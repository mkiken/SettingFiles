import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AI_ALIASES = REPO_ROOT / "shell/zsh/alias/ai/ai.zsh"


def run_herdr_run_in_new_tab(
    args: str,
    *,
    tab_create_exit: int = 0,
    tab_create_json: str = '{"result":{"root_pane":{"pane_id":"w1:p2"}}}',
    wait_output_exit: int = 0,
) -> tuple[subprocess.CompletedProcess, list[str]]:
    """_herdr_run_in_new_tab を stub herdr/jq 付きで実行し、(結果, herdr呼び出しログ) を返す。"""
    with tempfile.TemporaryDirectory() as temp_dir:
        log_path = Path(temp_dir) / "herdr_calls.log"
        script = f'''
LOG="{log_path}"
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
            ;;
        wait)
            [[ "$2" == "output" ]] && return {wait_output_exit}
            ;;
    esac
}}
jq() {{
    python3 -c 'import json,sys; d=json.load(sys.stdin); v=d.get("result",{{}}).get("root_pane",{{}}).get("pane_id"); print(v if v is not None else "null")'
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


class HerdrRunInNewTabTest(unittest.TestCase):
    def test_calls_happen_in_order_tab_create_marker_wait_then_command(self):
        result, calls = run_herdr_run_in_new_tab(
            '_herdr_run_in_new_tab "" "/tmp/work" "label" "gm-pr-review 123"'
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(calls), 4, calls)

        self.assertTrue(calls[0].startswith("tab create"))
        self.assertTrue(calls[1].startswith("pane run w1:p2 print -r -- __herdr_ready_"))
        self.assertTrue(calls[2].startswith("wait output w1:p2 --match __herdr_ready_"))
        self.assertEqual(calls[3], "pane run w1:p2 gm-pr-review 123")

        # marker文字列がpane runとwait outputで一致していること
        marker_in_run = calls[1].split("print -r -- ", 1)[1]
        marker_in_wait = calls[2].split("--match ", 1)[1].split(" --source", 1)[0]
        self.assertEqual(marker_in_run, marker_in_wait)

    def test_wait_output_timeout_prevents_final_command(self):
        result, calls = run_herdr_run_in_new_tab(
            '_herdr_run_in_new_tab "" "/tmp/work" "label" "gm-pr-review 123"',
            wait_output_exit=1,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("タイムアウトしました", result.stderr)
        # marker echoまでは呼ばれるが、本命コマンドのpane runは呼ばれない
        self.assertEqual(len(calls), 3, calls)
        self.assertEqual(calls[2], "wait output w1:p2 --match " + calls[1].split("print -r -- ", 1)[1] + " --source recent --timeout 15000")
        self.assertFalse(any(c == "pane run w1:p2 gm-pr-review 123" for c in calls))

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
        markers = [c.split("print -r -- ", 1)[1] for c in calls if "print -r --" in c]
        self.assertEqual(len(markers), 2)
        self.assertNotEqual(markers[0], markers[1])

    def test_noop_command_from_fgwtc_is_still_sent_after_ready(self):
        # fgwtc(git.zsh) は command に no-op ':' を渡す。ready待ち後もスキップされず投入されること。
        result, calls = run_herdr_run_in_new_tab(
            '_herdr_run_in_new_tab "" "/tmp/work" "label" ":"'
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls[-1], "pane run w1:p2 :")


if __name__ == "__main__":
    unittest.main()
