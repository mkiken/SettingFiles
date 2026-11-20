import subprocess
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT

LAUNCH_SCRIPT = REPO_ROOT / "shell/herdr/herdr-ai-launch.sh"

SPLIT_CALL = "pane split --pane w1:p1 --direction right --ratio 0.5 --focus --cwd /work"
AGENT_WAIT_CALL = "agent wait w1:p9 --until idle --timeout 60000"

HERDR_STUB = """#!/bin/bash
printf '%s\\n' "$*" >> "$HERDR_LOG"
case "$1 $2" in
  "pane split")
    if [[ "${SPLIT_EXIT:-0}" -ne 0 ]]; then
      exit "$SPLIT_EXIT"
    fi
    printf '%s' "$SPLIT_JSON"
    ;;
  "agent wait")
    exit "${AGENT_WAIT_EXIT:-0}"
    ;;
  "pane run"|"pane wait-output"|"pane send-keys")
    exit 0
    ;;
esac
"""


def run_launch_script(
    args: list[str],
    *,
    split_exit: int = 0,
    split_json: str = '{"result":{"pane":{"pane_id":"w1:p9"}}}',
    agent_wait_exit: int = 0,
) -> tuple[subprocess.CompletedProcess, list[str]]:
    """PATH先頭にスタブherdrを置いてスクリプトを実行し、(結果, herdr呼び出しログ) を返す。"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        log_path = temp_path / "herdr_calls.log"
        fake_bin = temp_path / "fake_bin"
        fake_bin.mkdir()
        stub = fake_bin / "herdr"
        stub.write_text(HERDR_STUB)
        stub.chmod(0o755)

        env = {
            "PATH": f"{fake_bin}:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
            "HOME": temp_dir,
            "HERDR_LOG": str(log_path),
            "SPLIT_EXIT": str(split_exit),
            "SPLIT_JSON": split_json,
            "AGENT_WAIT_EXIT": str(agent_wait_exit),
        }
        result = subprocess.run(
            ["bash", str(LAUNCH_SCRIPT), *args],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        calls = log_path.read_text().splitlines() if log_path.exists() else []
        return result, calls


class HerdrAiLaunchTest(unittest.TestCase):
    def test_success_splits_runs_command_waits_idle_and_prints_pane_id(self):
        result, calls = run_launch_script(["w1:p1", "/work", "cxs"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "w1:p9\n")
        self.assertEqual(calls[0], SPLIT_CALL)
        # 共有ヘルパーの ctrl+u で行バッファを空にしてから本命コマンドを投入する
        self.assertLess(calls.index("pane send-keys w1:p9 ctrl+u"), calls.index("pane run w1:p9 cxs"))
        self.assertEqual(calls[-2:], ["pane run w1:p9 cxs", AGENT_WAIT_CALL])

    def test_command_with_quoted_effort_argument_is_passed_as_one_line(self):
        command = """cxa -c 'model_reasoning_effort="high"'"""
        result, calls = run_launch_script(["w1:p1", "/work", command])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"pane run w1:p9 {command}", calls)

    def test_split_failure_does_not_run_command(self):
        result, calls = run_launch_script(["w1:p1", "/work", "cxs"], split_exit=1)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertFalse(any(c.startswith("pane run") for c in calls), calls)

    def test_split_result_without_pane_id_does_not_run_command(self):
        result, calls = run_launch_script(["w1:p1", "/work", "cxs"], split_json='{"result":{"pane":{}}}')

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("pane_id", result.stderr)
        self.assertFalse(any(c.startswith("pane run") for c in calls), calls)

    def test_agent_wait_failure_reports_pane_and_prints_nothing(self):
        result, calls = run_launch_script(["w1:p1", "/work", "cxs"], agent_wait_exit=1)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("w1:p9", result.stderr)
        self.assertEqual(calls[-1], AGENT_WAIT_CALL)

    def test_wrong_argument_count_is_usage_error_without_herdr_calls(self):
        result, calls = run_launch_script(["w1:p1", "/work"])

        self.assertEqual(result.returncode, 2)
        self.assertIn("usage", result.stderr)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
